"""One public connection, independent from optional strategy consumers."""
from collections import deque
import copy
import queue
import threading
import time

from terminal.data import validate_symbol
from terminal.live_data import PublicStream, reconnect_delay
from terminal.market_state import MarketState
from terminal.market_sources import validate_source, safe_error
from terminal.okx_market import OKXPublicStream


class MarketFeed:
    """A bounded consumer; overflow/generation changes demand strategy recovery."""
    def __init__(self,hub):
        self.hub=hub;self.events=queue.Queue(maxsize=2048)
        self.failed=False;self.subscribed=False;self.state=hub.state

    def open(self):
        with self.hub.lock:
            self.hub.consumers.add(self)
            self.subscribed=self.hub.subscribed

    def read(self):
        if self.failed:raise ConnectionError('Market consumer needs history recovery')
        self.subscribed=self.hub.subscribed
        try:return [self.events.get(timeout=.5)]
        except queue.Empty:return []

    def close(self):
        with self.hub.lock:self.hub.consumers.discard(self)


class MarketObserver:
    """Passive bounded confirmation tap, never a strategy connection owner.

    Receipts are detached copies. A failed queue is never silently resumed.
    Construction and consumption cannot open/acquire a public source.
    """
    def __init__(self, hub, interval, capacity=3):
        self.hub, self.interval = hub, interval
        self.events = queue.Queue(maxsize=capacity)
        self.failed = False
        self.sequence = 0
        self.epoch = hub.observation_epoch
        self.generation = hub.state.generation
        self.initial = copy.deepcopy(hub.confirmations.get(interval))
        self.last_receipt = self.initial

    def offer(self, receipt):
        if self.failed or receipt['interval'] != self.interval:
            return
        prior = self.last_receipt
        if prior and not receipt['conflict'] and not prior['conflict'] and all(receipt[key] == prior[key] for key in ('candle', 'epoch', 'generation', 'source', 'market', 'symbol')):
            return
        self.sequence += 1
        value = copy.deepcopy(receipt)
        self.last_receipt = copy.deepcopy(receipt)
        value['sequence'] = self.sequence
        try:
            self.events.put_nowait(value)
        except queue.Full:
            self.failed = True

    def close(self):
        with self.hub.lock:
            self.hub.observers.discard(self)



class MarketHub:
    """Socket lifecycle never waits for SQLite strategy warmup or a UI render."""
    def __init__(self,stream_factory=PublicStream):
        self.stream_factory=stream_factory;self.state=MarketState()
        self.lock=threading.RLock();self.stop=threading.Event();self.thread=None
        self.source='bybit';self.market=None;self.symbol=None;self.consumers=set();self.subscribed=False
        self.phase='PAUSED';self.detail='Market view is not open'
        self.observers=set();self.observation_epoch=0;self.confirmations={}
        self.candles={};self.started=None;self.first={};self.errors=deque(maxlen=50)

    def open(self,market,symbol,source='bybit'):
        validate_source(source)
        if market not in ('spot','linear'):raise ValueError('Unsupported public market')
        validate_symbol(symbol)
        if self.thread and self.thread.is_alive():
            if (source,market,symbol)==(self.source,self.market,self.symbol):return
            with self.lock:
                if self.consumers:raise ValueError('Pause strategy monitoring before changing the market')
            self.close()
        with self.lock:self._invalidate_observers()
        self.source=source;self.market,self.symbol=market,symbol;self.stop.clear()
        self.state=MarketState();self.candles={};self.first={};self.started=time.monotonic()
        self.phase='CONNECTING';self.detail='Opening public market data'
        self.thread=threading.Thread(target=self._run,daemon=True,name='public-market')
        self.thread.start()

    def feed(self,market,symbol):
        self.open(market,symbol)
        return MarketFeed(self)

    def snapshot(self):
        result=self.state.snapshot()
        with self.lock:
            active=bool(self.thread and self.thread.is_alive() and not self.stop.is_set())
            phase=('CONNECTED' if result['fresh'] else 'DEGRADED') if self.phase=='CONNECTED' else self.phase
            return {**result,'source':self.source,'market':self.market,'symbol':self.symbol,'active':active,
                    'status':phase,'detail':self.detail,'first':self.first.copy(),
                    'errors':list(self.errors),'observation_epoch':self.observation_epoch}

    def latest(self,interval):
        with self.lock:return [dict(row) for row in self.candles.get(interval,{}).values()]

    def observe(self, interval):
        """Subscribe only to an already open Hub. Does not count as a consumer."""
        with self.lock:
            observer = MarketObserver(self, interval)
            self.observers.add(observer)
            return observer

    def _invalidate_observers(self):
        self.observation_epoch += 1
        self.confirmations.clear()
        for observer in self.observers:
            observer.failed = True

    def _observe_candle(self, event):
        with self.lock:
            self._observe_candle_locked(event)

    def _observe_candle_locked(self,event):
        interval=event.get('interval','1');candle=event['candle']
        row={**candle,'confirmed':event['kind']=='candle' or event.get('confirmed',False),'provider_ms':event.get('provider_ms',0)}
        table=self.candles.setdefault(interval,{})
        old=table.get(candle['time'])
        if old and old['confirmed'] and row['provider_ms']>=old['provider_ms']:
            if row['confirmed'] and any(old[k]!=row[k] for k in ('open','high','low','close','volume')):
                old['conflict']=True
            # Exact duplicates advance the provider watermark, not indicator state.
            old['provider_ms']=row['provider_ms']
        if old is None or (not old['confirmed'] and row['provider_ms']>=old['provider_ms']):table[candle['time']]=row
        for key in sorted(table)[:-3]:del table[key]
        if row['confirmed'] and event['kind'] in ('candle', 'display_candle'):
            receipt = dict(interval=interval, source=self.source, market=self.market,
                symbol=self.symbol, epoch=self.observation_epoch, generation=self.state.generation,
                observed_at=int(time.time()), observed_monotonic=time.monotonic(),
                candle={**candle, 'confirmation':'provider_confirmed'},
                conflict=bool(row.get('conflict') or (old and old.get('conflict'))))
            current = self.confirmations.get(interval)
            if current is None or candle['time'] >= current['candle']['time']:
                self.confirmations[interval] = copy.deepcopy(receipt)
            for observer in self.observers:
                observer.offer(receipt)

    def _run(self):
        attempts=0
        while not self.stop.is_set():
            stream=None
            try:
                stream=(OKXPublicStream if self.source=='okx' else self.stream_factory)(self.market,self.symbol)
                stream.intervals=('1','5','15','60','240','D')
                stream.state=self.state;stream.open();connected=time.monotonic()
                last_price=connected
                while not self.stop.is_set():
                    events=stream.read()
                    with self.lock:
                        self.subscribed=stream.subscribed
                        for event in events:
                            kind=event['kind']
                            if kind=='price':last_price=time.monotonic()
                            if kind in ('candle','forming','display_candle'):
                                self._observe_candle(event)
                            if kind!='display_candle':
                                for feed in self.consumers:
                                    if feed.failed:continue
                                    try:feed.events.put_nowait(event)
                                    except queue.Full:feed.failed=True
                        current=self.state.snapshot()
                        for key in ('ticker','book','trades','forming','candles'):
                            if current['counts'][key] and key not in self.first:self.first[key]=round(time.monotonic()-self.started,3)
                        if self.subscribed:self.phase='CONNECTED';self.detail='Public market subscribed; strategy readiness is separate'
                    if time.monotonic()-last_price>30:raise ConnectionError('Public ticker stale')
                    if time.monotonic()-connected>60 and current['fresh']:attempts=0
            except Exception as exc:
                if self.stop.is_set():break
                with self.lock:
                    self.subscribed=False;self.phase='RECONNECTING';self.detail=f'{self.source.upper()} public connection interrupted ({safe_error(exc)}); waiting for new snapshots'
                    self.errors.append({'time':int(time.time()),'message':self.detail})
                    for feed in self.consumers:feed.failed=True
                    self._invalidate_observers();self.candles={};self.state.reset()
                if self.stop.wait(reconnect_delay(attempts)):break
                attempts+=1
                if attempts>=8:self.phase='ERROR';self.detail='Market retries exhausted; reopen Live to retry';break
            finally:
                if stream:stream.close()
        self.subscribed=False

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=16)
        if self.thread and self.thread.is_alive():raise RuntimeError('Public market shutdown still pending')
        with self.lock:
            for feed in self.consumers:feed.failed=True
            self._invalidate_observers()
            self.phase='PAUSED';self.detail='Market view closed';self.state.reset()
