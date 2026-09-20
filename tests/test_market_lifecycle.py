import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from terminal.chart_history import ChartHistory, PAGE
from terminal.data import BybitClient
from terminal.live_data import PublicStream
from terminal.market_hub import MarketHub
from terminal.storage import RunStore


class MarketLifecycleTests(unittest.TestCase):
    def test_failed_page_is_retryable_and_only_success_proves_end(self):
        calls=[]
        def transport(path,params):
            calls.append(1)
            if len(calls)==1:raise RuntimeError('Synthetic temporary failure')
            return {'retCode':0,'result':{'list':[]}}
        with tempfile.TemporaryDirectory() as d:
            chart=ChartHistory(RunStore(Path(d)),MarketHub(),lambda p,**kw:BybitClient(p,transport=transport,**kw))
            try:
                chart.request('spot','BTCUSDT',1,600);chart.jobs.join()
                failed=chart.request('spot','BTCUSDT',1,600)
                self.assertEqual(failed['page_status'],'error');self.assertFalse(failed['exhausted'])
                with chart.lock:chart.last_fetch.clear()
                chart.request('spot','BTCUSDT',1,600);chart.jobs.join()
                ended=chart.request('spot','BTCUSDT',1,600)
                self.assertEqual(ended['page_status'],'end');self.assertTrue(ended['exhausted'])
                self.assertIsNone(ended['error'])
            finally:chart.close()

    def test_native_pages_cache_order_overlap_and_realtime(self):
        for minutes in (5,60,240,1440):
            with self.subTest(minutes=minutes),tempfile.TemporaryDirectory() as d:
                width=minutes*60;now=width*1000;calls=[]
                def transport(path,params):
                    calls.append((path,params.copy()))
                    end=(params['end']+1)//1000
                    rows=[[str(t*1000),'100','110','90','105','1','105'] for t in range(end-width,max(-width,end-width*(params['limit']+1)),-width)]
                    return {'retCode':0,'result':{'list':rows},'time':now*1000}
                hub=MarketHub();hub.market='spot';hub.symbol='BTCUSDT'
                chart=ChartHistory(RunStore(Path(d)),hub,lambda p,**kw:BybitClient(p,transport=transport,**kw))
                try:
                    with patch('terminal.chart_history.time.time',return_value=now):
                        chart.fetch('spot','BTCUSDT',minutes,None)
                        self.assertEqual(calls[-1][1]['interval'],'D' if minutes==1440 else str(minutes))
                        result=chart.request('spot','BTCUSDT',minutes,None);chart.jobs.join()
                        self.assertEqual(len(result['candles']),PAGE)
                        self.assertEqual(result['candles'][0]['time'],700*width)
                        cursor=result['oldest'];chart.request('spot','BTCUSDT',minutes,cursor);chart.jobs.join()
                        older=chart.request('spot','BTCUSDT',minutes,cursor)
                        count=len(calls);again=chart.request('spot','BTCUSDT',minutes,cursor)
                        self.assertFalse(again['loading']);self.assertEqual(len(calls),count)
                        self.assertEqual(older['candles'][0]['time'],400*width)
                        self.assertEqual(len({r['time'] for r in older['candles']}),PAGE)
                        hub.candles['D' if minutes==1440 else str(minutes)]={now:{'time':now,'open':105.,'high':108.,'low':104.,'close':107.,'volume':2.,'confirmed':False,'provider_ms':now*1000}}
                        current=chart.request('spot','BTCUSDT',minutes,None)
                        self.assertEqual(current['candles'][-1]['close'],107)
                        self.assertEqual(current['candles'][-1]['time'],now)
                finally:chart.close()

    def test_hub_keeps_market_without_consumers_and_detach_does_not_reconnect(self):
        opened=[]
        class Stream:
            subscribed=True
            def __init__(self,*args):pass
            def open(self):opened.append(1);self.state.connected()
            def close(self):pass
            def read(self):
                time.sleep(.005);stamp=int(time.time()*1000)
                self.state.ticker_update({'lastPrice':'100'},stamp)
                self.state.book_update('snapshot',{'u':1,'seq':1,'b':[['99','1']],'a':[['101','1']]},stamp)
                return [{'kind':'price','provider_ms':stamp,'observed_ms':stamp,'price':'100','mark':None}]
        hub=MarketHub(Stream)
        try:
            hub.open('spot','BTCUSDT')
            deadline=time.monotonic()+2
            while not hub.snapshot()['fresh'] and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(hub.snapshot()['status'],'CONNECTED')
            feed=hub.feed('spot','BTCUSDT');feed.open()
            self.assertEqual(feed.read()[0]['kind'],'price');feed.close()
            count=hub.snapshot()['counts']['ticker'];time.sleep(.03)
            self.assertGreater(hub.snapshot()['counts']['ticker'],count)
            self.assertEqual(opened,[1]);self.assertEqual(len(hub.consumers),0)
        finally:hub.close()

    def test_native_interval_stream_does_not_feed_coarse_bars_to_strategy(self):
        stream=PublicStream('spot','BTCUSDT');stream.intervals=('1','60')
        packet={'topic':'kline.60.BTCUSDT','ts':3600000,'data':[{'interval':'60','confirm':True,'start':0,'end':3599999,'open':'100','high':'110','low':'90','close':'105','volume':'2'}]}
        events=stream.parse(json.dumps(packet),3600000)
        self.assertEqual(events[0]['kind'],'display_candle');self.assertEqual(events[0]['interval'],'60')
        self.assertEqual(stream.parse(json.dumps(packet),3600000),[])
        self.assertEqual(stream.state.snapshot()['counts']['candles'],0)

    def test_reconnect_invalidates_consumers_and_resets_book_before_new_snapshot(self):
        interrupt=threading.Event();opened=[];resets=[]
        class Stream:
            subscribed=True
            def __init__(self,*args):self.index=len(opened)
            def open(self):
                resets.append(self.state.snapshot()['book']['valid']);opened.append(1);self.state.connected()
            def close(self):pass
            def read(self):
                if self.index==0 and interrupt.is_set():raise ConnectionError('Fixture disconnect')
                time.sleep(.005);stamp=int(time.time()*1000)
                self.state.ticker_update({'lastPrice':'100'},stamp)
                self.state.book_update('snapshot',{'u':1,'seq':1,'b':[['99','1']],'a':[['101','1']]},stamp)
                return [{'kind':'price','provider_ms':stamp,'observed_ms':stamp,'price':'100','mark':None}]
        hub=MarketHub(Stream)
        try:
            with patch('terminal.market_hub.reconnect_delay',return_value=0):
                hub.open('spot','BTCUSDT');feed=hub.feed('spot','BTCUSDT');feed.open()
                self.assertEqual(feed.read()[0]['kind'],'price');interrupt.set()
                deadline=time.monotonic()+2
                while len(opened)<2 and time.monotonic()<deadline:time.sleep(.01)
                self.assertEqual(resets,[False,False]);self.assertEqual(len(opened),2)
                with self.assertRaises(ConnectionError):feed.read()
                feed.close()
        finally:hub.close()

    def test_market_ready_during_blocked_warmup_and_continues_after_pause(self):
        from terminal.live import LiveManager
        from terminal.live_data import LiveHistory
        from terminal.graph import example_graph
        from terminal.profile import Profile
        from terminal.series import Candle
        from terminal.data import canonical
        release=threading.Event();entered=threading.Event()
        class History(LiveHistory):
            def candles(self,market,symbol,start,end):
                entered.set()
                if not release.wait(3):raise TimeoutError('Fixture warmup timeout')
                return [Candle(t,100,100,100,100,1) for t in range(start,end,60)]
        class Stream:
            subscribed=True
            def __init__(self,*args):pass
            def open(self):self.state.connected()
            def close(self):pass
            def read(self):
                time.sleep(.005);stamp=int(time.time()*1000)
                self.state.ticker_update({'lastPrice':'100'},stamp)
                self.state.book_update('snapshot',{'u':1,'seq':1,'b':[['99','1']],'a':[['101','1']]},stamp)
                return [{'kind':'price','provider_ms':stamp,'observed_ms':stamp,'price':'100','mark':None}]
        with tempfile.TemporaryDirectory() as d,patch('terminal.live.WindowsCredentials'):
            manager=LiveManager(RunStore(Path(d)),stream_factory=Stream,history_factory=History)
            try:
                sid=manager.journal.create(example_graph(),Profile(primary_minutes=1),'fixture','Synthetic lifecycle')
                with manager.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(sid,canonical({'paper':False,'channels':[],'warmup_minutes':2}).decode()))
                manager.resume(sid,False);self.assertTrue(entered.wait(2))
                deadline=time.monotonic()+2
                while not manager.hub.snapshot()['fresh'] and time.monotonic()<deadline:time.sleep(.01)
                view=manager.status();self.assertEqual(view['terminal_state'],'CONNECTED')
                self.assertEqual(view['strategy_state'],'WARMING UP');self.assertFalse(view['paper_ready']);self.assertEqual(view['events'],[])
                release.set();deadline=time.monotonic()+3
                while manager.status()['strategy_state']!='READY' and time.monotonic()<deadline:time.sleep(.01)
                self.assertEqual(manager.status()['strategy_state'],'READY')
                manager.pause();manager.thread.join(2)
                count=manager.hub.snapshot()['counts']['ticker'];time.sleep(.03)
                self.assertGreater(manager.hub.snapshot()['counts']['ticker'],count)
                self.assertEqual(manager.hub.snapshot()['counts']['connections'],1)
                self.assertFalse(manager.status()['active'])
            finally:release.set();manager.close()
