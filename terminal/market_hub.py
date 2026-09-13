"""One public connection, independent from optional strategy consumers."""
from collections import deque
import queue
import threading
import time

from terminal.data import validate_symbol
from terminal.live_data import PublicStream, reconnect_delay
from terminal.market_state import MarketState


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


class MarketHub:
    """Socket lifecycle never waits for SQLite strategy warmup or a UI render."""
    def __init__(self,stream_factory=PublicStream):
        self.stream_factory=stream_factory;self.state=MarketState()
        self.lock=threading.RLock();self.stop=threading.Event();self.thread=None
        self.market=None;self.symbol=None;self.consumers=set();self.subscribed=False
        self.phase='PAUSED';self.detail='Market view is not open'
        self.candles={};self.started=None;self.first={};self.errors=deque(maxlen=50)

    def open(self,market,symbol):
        if market not in ('spot','linear'):raise ValueError('Unsupported public market')
        validate_symbol(symbol)
        if self.thread and self.thread.is_alive():
            if (market,symbol)==(self.market,self.symbol):return
            with self.lock:
                if self.consumers:raise ValueError('Pause strategy monitoring before changing the market')
            self.close()
        self.market,self.symbol=market,symbol;self.stop.clear()
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
            return {**result,'market':self.market,'symbol':self.symbol,'active':active,
                    'status':phase,'detail':self.detail,'first':self.first.copy(),
                    'errors':list(self.errors)}

    def latest(self,interval):
        with self.lock:return [dict(row) for row in self.candles.get(interval,{}).values()]

    def _run(self):
        attempts=0
        while not self.stop.is_set():
            stream=None
            try:
                stream=self.stream_factory(self.market,self.symbol)
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
                                interval=event.get('interval','1');candle=event['candle']
                                row={**candle,'confirmed':kind=='candle' or event.get('confirmed',False),'provider_ms':event.get('provider_ms',0)}
                                table=self.candles.setdefault(interval,{})
                                old=table.get(candle['time'])
                                if old is None or (not old['confirmed'] and row['provider_ms']>=old['provider_ms']):table[candle['time']]=row
                                for key in sorted(table)[:-3]:del table[key]
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
            except Exception:
                if self.stop.is_set():break
                with self.lock:
                    self.subscribed=False;self.phase='RECONNECTING';self.detail='Public connection interrupted; waiting for new snapshots'
                    self.errors.append({'time':int(time.time()),'message':self.detail})
                    for feed in self.consumers:feed.failed=True
                    self.candles={};self.state.reset()
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
            self.phase='PAUSED';self.detail='Market view closed';self.state.reset()
