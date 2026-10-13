"""Independent offline protocol/source-boundary fixtures. No public requests."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from terminal.okx_market import OKXPublicStream, OKXHistory, candle, instrument
from terminal.live_data import LiveProtocolError
from terminal.market_hub import MarketHub
from terminal.market_sources import safe_error
from terminal.chart_history import ChartHistory
from terminal.display_indicators import DisplayIndicators
from terminal.storage import RunStore
from terminal.data import BybitClient
from terminal.live import LiveManager

class OKXTests(unittest.TestCase):
    def test_native_confirmations_utc_and_instrument(self):
        self.assertEqual(instrument('spot','BTCUSDT'),'BTC-USDT')
        self.assertEqual(instrument('linear','BTCUSDT'),'BTC-USDT-SWAP')
        stream=OKXPublicStream('spot','BTCUSDT');stream.intervals=('1','D')
        packet={'arg':{'channel':'candle1m','instId':'BTC-USDT'},'data':[['60000','100','110','90','105','3','3','315','0']]}
        forming=stream.parse(json.dumps(packet),90000,'business')[0]
        self.assertEqual((forming['kind'],forming['candle']['time'],forming['candle']['volume']),('forming',60,3))
        packet['data'][0][8]='1'
        with self.assertRaises(LiveProtocolError):stream.parse(json.dumps(packet),90000,'business')
        closed=stream.parse(json.dumps(packet),120000,'business')[0]
        self.assertEqual(closed['kind'],'candle')
        hub=MarketHub();hub._observe_candle(closed);hub._observe_candle(forming)
        self.assertTrue(hub.latest('1')[0]['confirmed'])
        packet['arg']['channel']='candle1Dutc';packet['data'][0][0]='0'
        self.assertEqual(stream.parse(json.dumps(packet),86400000,'business')[0]['interval'],'D')
        for field,value in [(1,'NaN'),(2,'Inf'),(5,'-1'),(2,'80'),(3,'120')]:
            invalid=['0','100','110','90','105','2','2','210','1'];invalid[field]=value
            with self.assertRaises(ValueError):candle(invalid,'1',120000)
        packet['arg']['instId']='ETH-USDT'
        with self.assertRaises(LiveProtocolError):stream.parse(json.dumps(packet),86400000,'business')

    def test_public_quotes_book_snapshots_and_trade_dedupe(self):
        stream=OKXPublicStream('spot','BTCUSDT')
        def feed(channel,rows):return stream.parse(json.dumps({'arg':{'channel':channel,'instId':'BTC-USDT'},'data':rows}),120000)
        ticker=dict(instId='BTC-USDT',ts='120000',last='110',open24h='100',high24h='115',low24h='90',vol24h='12')
        self.assertEqual(feed('tickers',[ticker])[0]['price'],'110')
        self.assertEqual(feed('tickers',[ticker]),[])
        feed('books5',[dict(ts='120000',bids=[['109','2','0','1']],asks=[['111','3','0','1']])])
        self.assertTrue(stream.state.snapshot()['fresh'])
        feed('books5',[dict(ts='120001',bids=[['108','4','0','1']],asks=[['112','1','0','1']])])
        self.assertEqual(stream.state.snapshot()['book']['bids'],[['108','4']])
        trade=dict(instId='BTC-USDT',ts='120000',tradeId='one',side='buy',px='110',sz='2')
        feed('trades',[trade]);feed('trades',[trade])
        self.assertEqual(len(stream.state.snapshot()['trades']),1)
        with self.assertRaises(LiveProtocolError):feed('tickers',[{**ticker,'ts':'100000'}])

    def test_documented_two_sockets_ack_heartbeat_and_cleanup(self):
        opened=[]
        class Socket:
            def __init__(self,url):self.url=url;self.sent=[];self.closed=False
            def send(self,value):self.sent.append(value)
            def close(self):self.closed=True
        def connect(url,**kwargs):
            socket=Socket(url);opened.append(socket);return socket
        stream=OKXPublicStream('spot','BTCUSDT',connect);stream.intervals=('1','D');stream.open()
        self.assertEqual([s.url for s in opened],['wss://ws.okx.com/ws/v5/public','wss://ws.okx.com/ws/v5/business'])
        for socket in opened:
            for arg in json.loads(socket.sent[0])['args']:
                stream.parse(json.dumps(dict(event='subscribe',arg=arg)),120000,socket.url.rsplit('/',1)[1])
        self.assertTrue(stream.subscribed);self.assertEqual(stream.parse('pong',120000),[])
        stream.close();self.assertTrue(all(s.closed for s in opened))

    def test_source_cache_confirmation_settings_origins_and_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            store=RunStore(Path(directory));hub=MarketHub()
            history=ChartHistory(store,hub,lambda p,**kw:BybitClient(p,transport=lambda *_: {'retCode':0,'result':{'list':[['0','10','11','9','10','1']]}},**kw))
            display=DisplayIndicators(history)
            try:
                history.okx.candles=lambda *args:[dict(time=0,open=100.,high=101.,low=99.,close=100.,volume=2.)]
                history.fetch('spot','BTCUSDT',1,60);history.fetch('okx:spot','BTCUSDT',1,60)
                history.stop.set() # All subsequent reads are strictly cache-only.
                for source,close in [('bybit',10),('okx',100)]:
                    page=history.request('spot','BTCUSDT',1,60,source)
                    self.assertEqual(page['source'],source);self.assertEqual(page['candles'][0]['close'],close)
                    self.assertEqual(page['candles'][0]['confirmation'],'closed_rest')
                    instances=[dict(id='ema',type='ema',params={'period':1},color='#ffffff',visible=True)]
                    display.save('spot','BTCUSDT',instances,0,source)
                    result=display.read('spot','BTCUSDT',1,0,0,1,source=source)
                    deadline=time.monotonic()+2
                    while result['status']=='calculating' and time.monotonic()<deadline:
                        time.sleep(.005);result=display.read('spot','BTCUSDT',1,0,0,1,source=source)
                    self.assertEqual(result['columns']['ema']['value'],[close])
                    if source=='okx':self.assertTrue(result['volume_unit'].startswith('base currency (OKX native)'))
                display.save('spot','BTCUSDT',[],1,'okx')
                self.assertEqual(display.settings('spot','BTCUSDT')['revision'],1)
                self.assertEqual(display.settings('spot','BTCUSDT','okx')['revision'],2)
                with store.connect() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM chart_confirmation_v1').fetchone()[0],2)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM chart_presentation_v1').fetchone()[0],2)
                history.stop.clear();epoch=history.epoch;history.supersede()
                history.okx.candles=lambda *args:[dict(time=60,open=200.,high=201.,low=199.,close=200.,volume=3.)]
                history.fetch('okx:spot','BTCUSDT',1,120,epoch=epoch)
                with store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM chart_candles_v1').fetchone()[0],2)
            finally:display.close();history.close()

    def test_safe_error_exposes_status_not_remote_body(self):
        self.assertEqual(safe_error(HTTPError('https://private.invalid?secret=hidden',403,'private body',{},None)),'HTTP 403')
        self.assertEqual(safe_error(ValueError('sensitive response')),'ValueError')

    def test_display_preference_persists_and_guards_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            store=RunStore(Path(directory));live=LiveManager(store)
            try:
                with patch.object(live.hub,'open'):
                    live.market_open('spot','BTCUSDT','okx')
                self.assertEqual(live.market_preferences(),{'source':'okx'})
                for call in (lambda:live.start(None,{},False,[]),lambda:live.start_manual({}),lambda:live.resume('missing',False)):
                    with self.assertRaisesRegex(ValueError,'OKX is chart-only'):call()
                with store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM live_sessions').fetchone()[0],0)
            finally:live.close()

    def test_ipc_source_is_additive_and_legacy_calls_remain_valid(self):
        from terminal.service import AppService
        with tempfile.TemporaryDirectory() as directory:
            service=AppService(Path(directory))
            try:
                service.live.chart_history.stop.set()
                with patch.object(service.live.hub,'open'):
                    for source in ({}, {'source':'bybit'}, {'source':'okx'}):
                        for command,params in [
                            ('market_open',dict(market='spot',symbol='BTCUSDT')),
                            ('market_chart',dict(market='spot',symbol='BTCUSDT',minutes=1,before=None)),
                            ('chart_indicator_settings',dict(market='spot',symbol='BTCUSDT'))]:
                            result=service.handle(dict(version=1,id='test',command=command,params={**params,**source}))
                            self.assertEqual(result.get('type'),'result',result)
                    invalid=service.handle(dict(version=1,id='test',command='market_chart',params=dict(market='spot',symbol='BTCUSDT',minutes=1,before=None,source='other')))
                    self.assertEqual(invalid.get('type'),'error')
            finally:service.close()

    def test_busy_public_lane_is_drained_without_waiting_for_quiet_candles(self):
        from collections import deque
        observed=120000
        ticker=dict(instId='BTC-USDT',last='110',open24h='100',high24h='115',low24h='90',vol24h='12')
        class Socket:
            def __init__(self,frames):self.frames=deque(frames);self.timeouts=[]
            def recv(self,timeout):
                self.timeouts.append(timeout)
                if not self.frames:raise TimeoutError()
                return self.frames.popleft()
        public=Socket([json.dumps({'arg':{'channel':'tickers','instId':'BTC-USDT'},'data':[{**ticker,'ts':str(observed+i)}]}) for i in range(40)])
        business=Socket([]);stream=OKXPublicStream('spot','BTCUSDT')
        stream.sockets={'public':public,'business':business}
        stream.received=stream.ping={'public':time.monotonic(),'business':time.monotonic()}
        with patch('terminal.okx_market.time.time',return_value=120):events=stream.read()
        self.assertEqual(len(events),40);self.assertEqual(set(public.timeouts+business.timeouts),{0})

    def test_rest_contract_and_unconfirmed_history_rejection_without_network(self):
        from urllib.parse import urlparse,parse_qs
        from terminal.data import DataError
        urls=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return json.dumps(payload).encode()
        class Opener:
            def open(self,req,timeout):urls.append(req.full_url);return Response()
        payload={'code':'0','data':[['60000','100','110','90','105','2','2','210','1']]}
        with patch('terminal.okx_market.request.build_opener',return_value=Opener()),patch('terminal.okx_market.time.time',return_value=120):
            history=OKXHistory();rows=history.candles('spot','BTCUSDT','1',120,300)
            self.assertEqual(rows[0]['time'],60)
            parsed=urlparse(urls[0]);self.assertEqual(parsed.netloc,'openapi.okx.com')
            self.assertEqual(parsed.path,'/api/v5/market/history-candles')
            self.assertEqual(parse_qs(parsed.query),{'instId':['BTC-USDT'],'bar':['1m'],'after':['120000'],'limit':['300']})
            payload['data'][0][8]='0'
            with self.assertRaises(DataError):history.candles('spot','BTCUSDT','1',120,300)
            payload={'code':'50011','data':[]}
            with self.assertRaises(DataError):history.candles('spot','BTCUSDT','1',120,300)

    def test_superseded_inflight_failure_cannot_throttle_or_poison_new_request(self):
        import threading
        started=threading.Event();release=threading.Event();calls=[]
        def transport(*args):
            calls.append(1)
            if len(calls)==1:
                started.set();release.wait(2);raise RuntimeError('Old view failure')
            return {'retCode':0,'result':{'list':[['0','10','11','9','10','1']]}}
        with tempfile.TemporaryDirectory() as directory:
            history=ChartHistory(RunStore(Path(directory)),MarketHub(),lambda p,**kw:BybitClient(p,transport=transport,**kw))
            try:
                history.request('spot','BTCUSDT',1,60);self.assertTrue(started.wait(2))
                history.supersede();history.request('spot','BTCUSDT',1,60)
                release.set();history.jobs.join()
                page=history.request('spot','BTCUSDT',1,60)
                self.assertEqual(len(calls),2);self.assertIsNone(page['error'])
                self.assertEqual(page['candles'][0]['close'],10)
            finally:release.set();history.close()

    def test_partial_socket_failure_closes_other_lane_and_heartbeat_expires(self):
        opened=[]
        class Socket:
            closed=False
            def send(self,value):pass
            def close(self):self.closed=True
        def connect(url,**kwargs):
            if url.endswith('business'):raise ConnectionError('Fixture business disconnect')
            socket=Socket();opened.append(socket);return socket
        stream=OKXPublicStream('spot','BTCUSDT',connect)
        with self.assertRaises(ConnectionError):stream.open()
        self.assertTrue(opened[0].closed);self.assertEqual(stream.sockets,{})
        stream.sockets={'public':Socket()};stream.received={'public':time.monotonic()-31};stream.ping={'public':time.monotonic()}
        with self.assertRaisesRegex(LiveProtocolError,'heartbeat stale'):stream.read()
        stream.close()

    def test_safe_network_reasons_cover_nested_and_dual_stack_failures(self):
        import errno,socket,ssl
        from urllib.error import URLError
        self.assertEqual(safe_error(OSError(errno.ECONNREFUSED,'https://secret.invalid/token')),f'connection refused (errno {errno.ECONNREFUSED})')
        self.assertEqual(safe_error(URLError(socket.gaierror(socket.EAI_NONAME,'private host'))),'DNS lookup failed')
        self.assertEqual(safe_error(TimeoutError('private address')),'Timeout')
        self.assertEqual(safe_error(ssl.SSLCertVerificationError('private certificate')),'TLS certificate verification failed')
        combined=OSError(f"Multiple exceptions: [Errno {errno.ECONNREFUSED}] Connect call failed ('private', 443), [Errno {errno.ENETUNREACH}] Network is unreachable; token=hidden")
        self.assertEqual(safe_error(combined),f'connection refused (errno {errno.ECONNREFUSED}); network unreachable (errno {errno.ENETUNREACH})')
        wrapper=ValueError('private response');wrapper.__cause__=OSError(errno.ENETUNREACH,'private route')
        self.assertEqual(safe_error(wrapper),f'network unreachable (errno {errno.ENETUNREACH})')
        unknown=OSError('Private URL https://secret.invalid?token=hidden')
        self.assertEqual(safe_error(unknown),'OSError')
        self.assertEqual(safe_error(ExceptionGroup('private group',[OSError(errno.ECONNRESET,'private peer')])),f'connection reset (errno {errno.ECONNRESET})')
