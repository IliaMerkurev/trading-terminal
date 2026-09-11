"""Public-only Bybit transport and deterministic validation/recovery helpers."""
from dataclasses import asdict
import json
import time

from websockets.sync.client import connect

from terminal.data import BybitClient, DataError, coverage, validate_symbol
from terminal.series import Candle


class LiveProtocolError(ValueError):
    pass


class PublicStream:
    def __init__(self,market,symbol,connector=connect):
        if market not in ('spot','linear'):
            raise ValueError('Unsupported public market')
        validate_symbol(symbol)
        self.market,self.symbol,self.connector=market,symbol,connector
        self.socket=None
        self.ticker={}
        self.ticker_ms=-1
        self.candle_ms=-1
        self.forming_start=-1
        self.last_receive=None
        self.last_ping=0
        self.subscribed=False

    def open(self):
        if self.socket is not None:
            raise LiveProtocolError('A subscription is already open')
        self.socket=self.connector(f'wss://stream.bybit.com/v5/public/{self.market}',
            open_timeout=12,close_timeout=3,max_size=1024*1024,max_queue=32,compression=None,
            ping_interval=20,ping_timeout=20)
        self.socket.send(json.dumps({'op':'subscribe','args':[f'tickers.{self.symbol}',f'kline.1.{self.symbol}']}))
        self.last_receive=time.monotonic()
        self.last_ping=self.last_receive
        self.ticker={};self.ticker_ms=-1;self.candle_ms=-1;self.forming_start=-1;self.subscribed=False

    def read(self,timeout=1):
        if self.socket is None:
            raise LiveProtocolError('Public stream is closed')
        now=time.monotonic()
        if now-self.last_ping>=20:
            self.socket.send('{"op":"ping"}')
            self.last_ping=now
        try:
            raw=self.socket.recv(timeout=timeout)
        except TimeoutError:
            if now-(self.last_receive or now)>30:
                raise LiveProtocolError('Public stream heartbeat is stale')
            return []
        self.last_receive=time.monotonic()
        return self.parse(raw,int(time.time()*1000))

    def parse(self,raw,observed_ms):
        if not isinstance(raw,str) or len(raw)>1024*1024:
            raise LiveProtocolError('Invalid or oversized stream message')
        payload=json.loads(raw)
        if not isinstance(payload,dict):
            raise LiveProtocolError('Invalid stream envelope')
        if payload.get('op')=='subscribe':
            if payload.get('success') is not True:
                raise LiveProtocolError('Public subscription was refused')
            self.subscribed=True
            return []
        if payload.get('op') in ('ping','pong') or payload.get('ret_msg')=='pong':
            return []
        topic=payload.get('topic')
        if topic not in (f'tickers.{self.symbol}',f'kline.1.{self.symbol}'):
            raise LiveProtocolError('Unexpected public stream topic')
        timestamp=payload.get('ts')
        if type(timestamp) is not int or timestamp>observed_ms+5000 or observed_ms-timestamp>90000:
            raise LiveProtocolError('Stale data or clock disagreement')
        data=payload.get('data')
        if topic.startswith('tickers.'):
            if observed_ms-timestamp>15000:raise LiveProtocolError('Observed ticker is stale')
            if not isinstance(data,dict) or data.get('symbol')!=self.symbol:
                raise LiveProtocolError('Ticker instrument mismatch')
            if timestamp<=self.ticker_ms:
                return []
            if payload.get('type')=='snapshot':
                self.ticker={}
            self.ticker.update(data)
            self.ticker_ms=timestamp
            from terminal.profile import dec
            price=dec(self.ticker.get('lastPrice','0'))
            mark=dec(self.ticker['markPrice']) if self.ticker.get('markPrice') else None
            if price<=0 or (mark is not None and mark<=0):
                raise LiveProtocolError('Invalid public observed price')
            return [{'kind':'price','provider_ms':timestamp,'observed_ms':observed_ms,
                     'price':str(price),'mark':str(mark) if mark is not None else None,
                     'funding_rate':self.ticker.get('fundingRate'),
                     'next_funding_ms':int(self.ticker['nextFundingTime']) if self.ticker.get('nextFundingTime') else None}]
        if not isinstance(data,list) or not 1<=len(data)<=10:
            raise LiveProtocolError('Invalid candle message size')
        events=[]
        for row in data:
            if row.get('interval')!='1' or type(row.get('confirm')) is not bool:
                raise LiveProtocolError('Unexpected candle interval or confirmation')
            start=row.get('start')
            if type(start) is not int or start%60000 or row.get('end')!=start+59999:
                raise LiveProtocolError('Invalid candle interval boundaries')
            if start>timestamp:raise LiveProtocolError('Candle starts in the future')
            if row['confirm'] and timestamp<start+59999:
                raise LiveProtocolError('Candle confirmed before its close')
            if not row['confirm']:
                if timestamp<=self.candle_ms or start<self.forming_start:continue
                self.candle_ms=timestamp;self.forming_start=start
            candle=Candle(start//1000,*(float(row[key]) for key in ('open','high','low','close','volume')))
            events.append({'kind':'candle' if row['confirm'] else 'forming','candle':asdict(candle),
                           'provider_ms':timestamp,'observed_ms':max(observed_ms,start+60000) if row['confirm'] else observed_ms})
        return events

    def close(self):
        socket,self.socket=self.socket,None
        if socket is not None:
            socket.close()


class LiveHistory(BybitClient):
    def get(self,path,params=None,*,cache=True):
        result=super().get(path,params,cache=cache)
        self.requests=self.requests[-1:]  # Only the current page provenance is needed here.
        return result

    def recover(self,session,end,*,warmup_start=None):
        start=session.last+60 if session.last is not None else warmup_start
        if start is None or start%60 or end%60:
            raise DataError('Aligned initialization history required')
        if start>=end:
            return 0
        session.store.state(session.id,'RECOVERING DATA','Reconstructing confirmed minute history')
        count=0
        # Page by bounded ranges rather than loading an arbitrarily long gap.
        while start<end:
            stop=min(start+1000*60,end)
            rows=self.candles(session.profile.market,session.profile.symbol,start,stop)
            if not coverage(rows,start,stop)['complete']:
                raise DataError('Recovery history has missing minutes; session remains paused')
            source='warmup' if warmup_start is not None else 'recovered'
            for candle in rows:
                session.ingest(candle,int(time.time()*1000),source)
            count+=len(rows);start=stop
        return count


def reconnect_delay(attempt):
    return min(30,2**min(max(0,attempt),5))
