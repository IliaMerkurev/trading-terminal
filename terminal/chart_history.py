"""Native-interval public chart pages, independent of strategy warmup journals."""
from dataclasses import asdict
import json
import queue
import threading
import time

from terminal.data import BybitClient, DataError, canonical, validate_symbol, digest
from terminal.series import Candle
from terminal.market_sources import cache_market, safe_error
from terminal.okx_market import OKXHistory

INTERVALS={1:'1',5:'5',15:'15',60:'60',240:'240',1440:'D'}
PAGE=300


class ChartHistory:
    def __init__(self,store,hub,client_factory=BybitClient):
        self.store,self.hub=store,hub
        self.stop=threading.Event();self.lock=threading.RLock()
        self.client=client_factory(store.root/'chart-http-cache',cancel=self.stop)
        self.okx=OKXHistory(self.stop)
        self.epoch=0
        self.pending=set();self.errors={};self.last_fetch={};self.jobs=queue.Queue(maxsize=12)
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS chart_candles_v1(
                  market TEXT NOT NULL,symbol TEXT NOT NULL,minutes INTEGER NOT NULL,time INTEGER NOT NULL,
                  candle TEXT NOT NULL,PRIMARY KEY(market,symbol,minutes,time));
                CREATE TABLE IF NOT EXISTS chart_confirmation_v1(
                  market TEXT NOT NULL,symbol TEXT NOT NULL,minutes INTEGER NOT NULL,time INTEGER NOT NULL,
                  content_hash TEXT NOT NULL,provenance TEXT NOT NULL,conflict INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(market,symbol,minutes,time));
                CREATE TABLE IF NOT EXISTS chart_pages_v1(
                  market TEXT NOT NULL,symbol TEXT NOT NULL,minutes INTEGER NOT NULL,before_time INTEGER NOT NULL,
                  oldest INTEGER,exhausted INTEGER NOT NULL,PRIMARY KEY(market,symbol,minutes,before_time));
            ''')
        self.thread=threading.Thread(target=self._run,daemon=True,name='chart-history')
        self.thread.start()

    def supersede(self):
        """Cancel queued old-view pages and invalidate in-flight publication."""
        with self.lock:
            self.epoch+=1
            self.pending.clear()
            while True:
                try:key=self.jobs.get_nowait()
                except queue.Empty:break
                self.pending.discard(key);self.jobs.task_done()

    def request(self,market,symbol,minutes,before=None,source='bybit'):
        stored=cache_market(market,source)
        if market not in ('spot','linear'):raise ValueError('Unsupported chart market')
        validate_symbol(symbol)
        if type(minutes) is not int or minutes not in INTERVALS:raise ValueError('Unsupported chart interval')
        if before is not None and (type(before) is not int or before<0 or before%(minutes*60)):raise ValueError('Invalid chart page cursor')
        self.capture_hub(market,symbol,minutes,source)
        width=minutes*60;now=int(time.time());boundary=now//width*width
        key=(stored,symbol,minutes,before)
        with self.store.connect() as db:
            page=db.execute('SELECT * FROM chart_pages_v1 WHERE market=? AND symbol=? AND minutes=? AND before_time=?',(*key[:3],before)).fetchone() if before is not None else None
            rows=db.execute('SELECT c.candle,p.provenance,p.content_hash,p.conflict FROM chart_candles_v1 c LEFT JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) WHERE c.market=? AND c.symbol=? AND c.minutes=? AND c.time<? ORDER BY c.time DESC LIMIT ?',(*key[:3],before if before is not None else boundary,PAGE)).fetchall()
        candles=[self.annotate(r) for r in reversed(rows)]
        # Current and immediately preceding observed intervals survive finalization
        # before the background REST refresh. Never aggregate M1 into coarse history.
        if before is None and (source,market,symbol)==(getattr(self.hub,'source','bybit'),self.hub.market,self.hub.symbol):
            merged={r['time']:r for r in candles}
            for row in self.hub.latest(INTERVALS[minutes]):
                if row['time']<=boundary and row['time'] not in merged:
                    merged[row['time']]={**self.payload(row),'confirmation':'conflict' if row.get('conflict') else 'provider_confirmed' if row.get('confirmed') is True else 'forming'}
            candles=[merged[t] for t in sorted(merged)][-PAGE:]
        with self.lock:
            token=(self.epoch,key)
            # Complete prior pages are immutable cache hits; recent data refreshes
            # once per minute, independent of client polling frequency.
            due=page is None if before is not None else time.monotonic()-self.last_fetch.get(key,-1e12)>=60
            if due and time.monotonic()-self.last_fetch.get(key,-1e12)>=5 and token not in self.pending and not self.stop.is_set():
                try:self.jobs.put_nowait(token);self.pending.add(token)
                except queue.Full:pass
            return {'source':source,'market':market,'symbol':symbol,'minutes':minutes,'candles':candles,
                    'page_status':('loading' if token in self.pending else 'error' if self.errors.get(key)
                                   else 'end' if page and page['exhausted'] else 'ready' if page else 'idle'),
                    'loading':token in self.pending,'error':self.errors.get(key),'cached':bool(rows),
                    'oldest':candles[0]['time'] if candles else None,
                    'exhausted':bool(page and page['exhausted']),
                    'note':f'{source.upper()} public native-interval candles; available exchange coverage only.'}

    def fetch(self,market,symbol,minutes,before,epoch=None):
        source='okx' if market.startswith('okx:') else 'bybit'
        physical=market.split(':')[-1]
        width=minutes*60;boundary=int(time.time())//width*width
        end=boundary if before is None else min(before,boundary)
        # Reuse prior complete rows and fetch only the missing/recent suffix.
        with self.store.connect() as db:
            last=db.execute('SELECT MAX(time) FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=?',(market,symbol,minutes)).fetchone()[0]
        limit=PAGE if before is not None or last is None else min(PAGE,max(1,(end-last)//width))
        if source=='okx':
            values=self.okx.candles(physical,symbol,INTERVALS[minutes],end,limit)
            rows={}
            for value in values:
                if value['time'] in rows and rows[value['time']]!=value:raise DataError('Conflicting OKX candle')
                rows[value['time']]=value
        else:
            result=self.client.get('/v5/market/kline',{'category':physical,'symbol':symbol,'interval':INTERVALS[minutes],'end':end*1000-1,'limit':limit},cache=False)
            self.client.requests=self.client.requests[-1:]
            raw=result.get('list')
            if not isinstance(raw,list) or len(raw)>limit:raise DataError('Invalid native chart page')
            rows={}
            for row in raw:
                if not isinstance(row,list) or len(row)<6:raise DataError('Invalid chart candle')
                stamp=int(row[0])
                if stamp%(width*1000):raise DataError('Misaligned chart candle')
                stamp//=1000
                if stamp>=end:raise DataError('Chart page did not advance')
                candle=asdict(Candle(stamp,*(float(v) for v in row[1:6])))
                if stamp in rows and rows[stamp]!=candle:raise DataError('Conflicting chart candle')
                rows[stamp]=candle
        conflict=False
        with self.lock,self.store.connect() as db:
            if self.stop.is_set() or (epoch is not None and epoch!=self.epoch):return
            for stamp,candle in rows.items():
                existing=db.execute('SELECT candle FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time=?',(market,symbol,minutes,stamp)).fetchone()
                if existing and json.loads(existing[0])!=candle:
                    key=(market,symbol,minutes,stamp)
                    db.execute('INSERT OR IGNORE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,1)',(*key,digest(json.loads(existing[0])),'legacy_unknown'))
                    db.execute('UPDATE chart_confirmation_v1 SET conflict=1 WHERE market=? AND symbol=? AND minutes=? AND time=?',key)
                    conflict=True;break
                db.execute('INSERT OR IGNORE INTO chart_candles_v1 VALUES(?,?,?,?,?)',(market,symbol,minutes,stamp,canonical(candle).decode()))
                db.execute('INSERT OR IGNORE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)',(market,symbol,minutes,stamp,digest(json.loads(existing[0])) if existing else digest(candle),'closed_rest'))
            if before is not None and not conflict:
                db.execute('INSERT OR REPLACE INTO chart_pages_v1 VALUES(?,?,?,?,?,?)',(market,symbol,minutes,before,min(rows) if rows else None,int(len(rows)<limit)))

        if conflict:raise DataError('Confirmed chart history changed; review required')

    @staticmethod
    def payload(row):
        return {k:row.get(k) for k in ('time','open','high','low','close','volume')}

    @staticmethod
    def annotate(row):
        candle=json.loads(row['candle'])
        provenance=row['provenance']
        state=('conflict' if row['conflict'] or (row['content_hash'] and digest(candle)!=row['content_hash'])
               else provenance or 'legacy_unknown')
        return {**candle,'confirmation':state}

    def capture_hub(self,market,symbol,minutes,source='bybit'):
        """Persist only explicit provider confirmations, never age a forming row."""
        if (source,market,symbol)!=(getattr(self.hub,'source','bybit'),self.hub.market,self.hub.symbol):return
        market=cache_market(market,source)
        rows=self.hub.latest(INTERVALS[minutes])
        with self.store.connect() as db:
            for row in rows:
                if row.get('confirmed') is not True:continue
                candle=self.payload(row);key=(market,symbol,minutes,candle['time'])
                old=db.execute('SELECT candle FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time=?',key).fetchone()
                conflict=bool(row.get('conflict') or (old and json.loads(old[0])!=candle))
                if old is None:db.execute('INSERT INTO chart_candles_v1 VALUES(?,?,?,?,?)',(*key,canonical(candle).decode()))
                db.execute('INSERT OR IGNORE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,?)',(*key,digest(json.loads(old[0])) if old else digest(candle),'provider_confirmed',int(conflict)))
                if conflict:db.execute('UPDATE chart_confirmation_v1 SET conflict=1 WHERE market=? AND symbol=? AND minutes=? AND time=?',key)

    def _run(self):
        while not self.stop.is_set():
            try:token=self.jobs.get(timeout=.25)
            except queue.Empty:continue
            epoch,key=token
            try:
                with self.lock:current=epoch==self.epoch
                if current:self.fetch(*key,epoch=epoch)
                with self.lock:
                    if epoch==self.epoch:self.errors.pop(key,None)
            except Exception as exc:
                with self.lock:
                    if epoch==self.epoch:self.errors[key]=f'Chart history unavailable or inconsistent ({safe_error(exc)}); retry later.'
            finally:
                with self.lock:
                    self.pending.discard(token)
                    if epoch==self.epoch:self.last_fetch[key]=time.monotonic()
                    while len(self.last_fetch)>128:self.last_fetch.pop(next(iter(self.last_fetch)))
                    while len(self.errors)>128:self.errors.pop(next(iter(self.errors)))
                self.jobs.task_done()

    def close(self):
        self.stop.set();self.thread.join(timeout=2)
