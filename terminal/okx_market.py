"""Credential-free OKX display transport, independent of execution/history research."""
from dataclasses import asdict
import json
import threading
import time
from urllib import request, parse
from websockets.sync.client import connect
from terminal.data import DataError, NoRedirect, validate_symbol
from terminal.live_data import LiveProtocolError
from terminal.market_state import MarketState, number
from terminal.series import Candle

BARS={'1':'1m','5':'5m','15':'15m','60':'1H','240':'4H','D':'1Dutc'}

def instrument(market,symbol):
    validate_symbol(symbol)
    if market not in ('spot','linear') or not symbol.endswith('USDT') or len(symbol)<=4:
        raise ValueError('OKX display supports USDT spot and USDT perpetual instruments')
    return symbol[:-4]+'-USDT'+('-SWAP' if market=='linear' else '')

def candle(row,interval,observed_ms):
    if not isinstance(row,list) or len(row)!=9 or row[8] not in ('0','1'):
        raise LiveProtocolError('Invalid OKX candle/confirmation')
    stamp=int(row[0]);width=(1440 if interval=='D' else int(interval))*60000
    if stamp<0 or stamp%width or stamp>observed_ms or (row[8]=='1' and stamp+width>observed_ms):
        raise LiveProtocolError('Invalid OKX candle boundary')
    return asdict(Candle(stamp//1000,*(float(v) for v in row[1:6])))

class OKXHistory:
    def __init__(self,cancel=None):self.cancel=cancel or threading.Event()
    def candles(self,market,symbol,interval,end,limit):
        if self.cancel.is_set():raise DataError('Chart acquisition cancelled')
        params={'instId':instrument(market,symbol),'bar':BARS[interval],'after':str(end*1000),'limit':str(limit)}
        url='https://openapi.okx.com/api/v5/market/history-candles?'+parse.urlencode(params)
        with request.build_opener(NoRedirect).open(request.Request(url,headers={'User-Agent':'TradingTerminal public display'}),timeout=12) as response:
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise DataError('OKX chart page exceeds budget')
        payload=json.loads(raw)
        if not isinstance(payload,dict) or payload.get('code')!='0':raise DataError('OKX chart request rejected')
        rows=payload.get('data')
        if not isinstance(rows,list) or len(rows)>limit:raise DataError('Invalid OKX chart page')
        result=[]
        for row in rows:
            value=candle(row,interval,int(time.time()*1000))
            if row[8]!='1':raise DataError('OKX history returned an unconfirmed candle')
            if value['time']>=end:raise DataError('OKX chart page did not advance')
            result.append(value)
        return result

class OKXPublicStream:
    """Two documented sockets: public quotes/depth/trades and business candles."""
    def __init__(self,market,symbol,connector=connect):
        self.market,self.symbol,self.inst=market,symbol,instrument(market,symbol)
        self.connector=connector;self.sockets={};self.state=MarketState();self.intervals=('1',)
        self.subscribed=False;self.acks=set();self.expected=set();self.received={};self.ping={}
        self.ticker_ms=-1;self.book_sequence=0
    def open(self):
        try:
            for lane,channels in (('public',('tickers','books5','trades')),('business',tuple('candle'+BARS[i] for i in self.intervals))):
                socket=self.connector('wss://ws.okx.com/ws/v5/'+lane,open_timeout=12,close_timeout=2,max_size=1024*1024,max_queue=32,compression=None,ping_interval=None)
                self.sockets[lane]=socket;self.received[lane]=self.ping[lane]=time.monotonic()
                args=[{'channel':c,'instId':self.inst} for c in channels]
                self.expected.update(channels);socket.send(json.dumps({'op':'subscribe','args':args}))
            self.state.connected()
        except Exception:
            self.close();raise
    def read(self,timeout=.01):
        # Drain each lane fairly without blocking a busy public feed behind a
        # quiet candle lane. Frame work is bounded; the hub owns the next turn.
        output=[];received=False
        for lane,socket in self.sockets.items():
            now=time.monotonic()
            if now-self.received[lane]>30:raise LiveProtocolError('OKX heartbeat stale')
            if now-self.ping[lane]>=15:socket.send('ping');self.ping[lane]=now
            for _ in range(64):
                try:raw=socket.recv(timeout=0)
                except TimeoutError:break
                received=True;self.received[lane]=time.monotonic()
                output.extend(self.parse(raw,int(time.time()*1000),lane))
        if not received:time.sleep(min(timeout,.01))
        return output
    def parse(self,raw,observed_ms,lane='public'):
        if raw=='pong':return []
        if not isinstance(raw,str) or len(raw)>1024*1024:raise LiveProtocolError('Invalid OKX frame')
        payload=json.loads(raw)
        if not isinstance(payload,dict):raise LiveProtocolError('Invalid OKX envelope')
        if payload.get('event')=='error':raise LiveProtocolError('OKX subscription refused')
        arg=payload.get('arg',{});channel=arg.get('channel')
        expected=('tickers','books5','trades') if lane=='public' else tuple('candle'+BARS[i] for i in self.intervals)
        if arg.get('instId')!=self.inst or channel not in expected:raise LiveProtocolError('Unexpected OKX instrument/channel')
        if payload.get('event')=='subscribe':
            self.acks.add(channel);self.subscribed=self.acks>=self.expected;return []
        rows=payload.get('data')
        if not isinstance(rows,list) or not 1<=len(rows)<=1024:raise LiveProtocolError('Invalid OKX data batch')
        events=[]
        for row in rows:
            if lane=='business':
                interval=next(i for i in self.intervals if channel=='candle'+BARS[i])
                value=candle(row,interval,observed_ms);confirmed=row[8]=='1'
                kind=('candle' if confirmed else 'forming') if interval=='1' else 'display_candle'
                if interval=='1':self.state.count('candles' if confirmed else 'forming')
                events.append(dict(kind=kind,interval=interval,candle=value,confirmed=confirmed,provider_ms=observed_ms,observed_ms=observed_ms))
                continue
            if not isinstance(row,dict):raise LiveProtocolError('Invalid OKX quote')
            stamp=int(row['ts'])
            if stamp>observed_ms+5000 or observed_ms-stamp>90000:raise LiveProtocolError('Stale OKX quote')
            if channel=='tickers':
                if row.get('instId')!=self.inst or observed_ms-stamp>15000:raise LiveProtocolError('Invalid OKX ticker')
                if stamp<=self.ticker_ms:continue
                last=number(row['last']);opening=number(row['open24h'],zero=True)
                self.ticker_ms=stamp
                self.state.ticker_update(dict(lastPrice=str(last),prevPrice24h=str(opening),price24hPcnt=str(last/opening-1) if opening else None,highPrice24h=row['high24h'],lowPrice24h=row['low24h'],volume24h=row['vol24h']),stamp)
                events.append(dict(kind='price',provider_ms=stamp,observed_ms=observed_ms,price=str(last),mark=None))
            elif channel=='books5':
                if observed_ms-stamp>15000:raise LiveProtocolError('Stale OKX book')
                self.book_sequence+=1
                self.state.book_update('snapshot',dict(b=[r[:2] for r in row['bids']],a=[r[:2] for r in row['asks']],u=self.book_sequence,seq=self.book_sequence),stamp)
            else:
                if row.get('instId')!=self.inst or row.get('side') not in ('buy','sell'):raise LiveProtocolError('Invalid OKX trade')
                self.state.trade_update([dict(s=self.symbol,S=row['side'].title(),i=row['tradeId'],T=stamp,p=row['px'],v=row['sz'])],self.symbol,observed_ms)
        return events
    def close(self):
        sockets,self.sockets=self.sockets,{}
        for socket in sockets.values():socket.close()
