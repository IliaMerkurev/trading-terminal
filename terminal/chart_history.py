"""Native-interval public chart pages, independent of strategy warmup journals."""
from dataclasses import asdict
import json
import queue
import threading
import time

from terminal.data import BybitClient, DataError, canonical, validate_symbol
from terminal.series import Candle

INTERVALS={1:'1',5:'5',15:'15',60:'60',240:'240',1440:'D'}
PAGE=300


class ChartHistory:
    def __init__(self,store,hub,client_factory=BybitClient):
        self.store,self.hub=store,hub
        self.stop=threading.Event();self.lock=threading.RLock()
        self.client=client_factory(store.root/'chart-http-cache',cancel=self.stop)
        self.pending=set();self.errors={};self.last_fetch={};self.jobs=queue.Queue(maxsize=12)
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS chart_candles_v1(
                  market TEXT NOT NULL,symbol TEXT NOT NULL,minutes INTEGER NOT NULL,time INTEGER NOT NULL,
                  candle TEXT NOT NULL,PRIMARY KEY(market,symbol,minutes,time));
                CREATE TABLE IF NOT EXISTS chart_pages_v1(
                  market TEXT NOT NULL,symbol TEXT NOT NULL,minutes INTEGER NOT NULL,before_time INTEGER NOT NULL,
                  oldest INTEGER,exhausted INTEGER NOT NULL,PRIMARY KEY(market,symbol,minutes,before_time));
            ''')
        self.thread=threading.Thread(target=self._run,daemon=True,name='chart-history')
        self.thread.start()

    def request(self,market,symbol,minutes,before=None):
        if market not in ('spot','linear'):raise ValueError('Unsupported chart market')
        validate_symbol(symbol)
        if type(minutes) is not int or minutes not in INTERVALS:raise ValueError('Unsupported chart interval')
        if before is not None and (type(before) is not int or before<0 or before%(minutes*60)):raise ValueError('Invalid chart page cursor')
        width=minutes*60;now=int(time.time());boundary=now//width*width
        key=(market,symbol,minutes,before)
        with self.store.connect() as db:
            page=db.execute('SELECT * FROM chart_pages_v1 WHERE market=? AND symbol=? AND minutes=? AND before_time=?',(*key[:3],before)).fetchone() if before is not None else None
            rows=db.execute('SELECT candle FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time<? ORDER BY time DESC LIMIT ?',(*key[:3],before if before is not None else boundary,PAGE)).fetchall()
        candles=[json.loads(r['candle']) for r in reversed(rows)]
        # Current and immediately preceding observed intervals survive finalization
        # before the background REST refresh. Never aggregate M1 into coarse history.
        if candles and before is None and (market,symbol)==(self.hub.market,self.hub.symbol):
            merged={r['time']:r for r in candles}
            for row in self.hub.latest(INTERVALS[minutes]):
                if row['time']<=boundary:merged[row['time']]={k:row[k] for k in ('time','open','high','low','close','volume')}
            candles=[merged[t] for t in sorted(merged)][-PAGE:]
        with self.lock:
            # Complete prior pages are immutable cache hits; recent data refreshes
            # once per minute, independent of client polling frequency.
            due=page is None if before is not None else time.monotonic()-self.last_fetch.get(key,-1e12)>=60
            if due and time.monotonic()-self.last_fetch.get(key,-1e12)>=5 and key not in self.pending and not self.stop.is_set():
                try:self.jobs.put_nowait(key);self.pending.add(key)
                except queue.Full:pass
            return {'market':market,'symbol':symbol,'minutes':minutes,'candles':candles,
                    'loading':key in self.pending,'error':self.errors.get(key),'cached':bool(rows),
                    'oldest':candles[0]['time'] if candles else None,
                    'exhausted':bool(page and page['exhausted']),
                    'note':'Bybit public native-interval candles; available exchange coverage only.'}

    def fetch(self,market,symbol,minutes,before):
        width=minutes*60;boundary=int(time.time())//width*width
        end=boundary if before is None else min(before,boundary)
        # Reuse prior complete rows and fetch only the missing/recent suffix.
        with self.store.connect() as db:
            last=db.execute('SELECT MAX(time) FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=?',(market,symbol,minutes)).fetchone()[0]
        limit=PAGE if before is not None or last is None else min(PAGE,max(1,(end-last)//width))
        result=self.client.get('/v5/market/kline',{'category':market,'symbol':symbol,'interval':INTERVALS[minutes],'end':end*1000-1,'limit':limit},cache=False)
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
        with self.store.connect() as db:
            if self.stop.is_set():return
            for stamp,candle in rows.items():
                existing=db.execute('SELECT candle FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time=?',(market,symbol,minutes,stamp)).fetchone()
                if existing and json.loads(existing[0])!=candle:raise DataError('Confirmed chart history changed; review required')
                db.execute('INSERT OR IGNORE INTO chart_candles_v1 VALUES(?,?,?,?,?)',(market,symbol,minutes,stamp,canonical(candle).decode()))
            if before is not None:
                db.execute('INSERT OR REPLACE INTO chart_pages_v1 VALUES(?,?,?,?,?,?)',(market,symbol,minutes,before,min(rows) if rows else None,int(len(rows)<limit)))

    def _run(self):
        while not self.stop.is_set():
            try:key=self.jobs.get(timeout=.25)
            except queue.Empty:continue
            try:
                self.fetch(*key)
                with self.lock:self.errors.pop(key,None)
            except Exception:
                with self.lock:self.errors[key]='Chart history unavailable or inconsistent; retry later.'
            finally:
                with self.lock:
                    self.pending.discard(key);self.last_fetch[key]=time.monotonic()
                    # Page identities are durable in SQLite, not unbounded RAM.
                    while len(self.last_fetch)>128:self.last_fetch.pop(next(iter(self.last_fetch)))
                    while len(self.errors)>128:self.errors.pop(next(iter(self.errors)))
                self.jobs.task_done()

    def close(self):
        self.stop.set();self.thread.join(timeout=2)
