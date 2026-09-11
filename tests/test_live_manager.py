import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch,Mock

from terminal.live import LiveManager, PendingSignals
from terminal.storage import RunStore
from terminal.paper import PaperEngine
from terminal.profile import Profile
from terminal.live_data import LiveHistory
from terminal.live_store import LiveSession
from terminal.graph import example_graph
from terminal.series import Candle
from terminal.data import canonical


class LiveManagerTests(unittest.TestCase):
    def test_transport_reconnect_recovers_minutes_and_suppresses_old_events(self):
        clock=[120.0];opened=[];closed=[]
        prices={0:100,60:100,120:110,180:90,240:110,300:120}
        class History(LiveHistory):
            def candles(self,market,symbol,start,end):
                return [Candle(t,prices[t],prices[t],prices[t],prices[t],1) for t in range(start,end,60)]
        def price():return {'kind':'price','provider_ms':int(clock[0]*1000),'observed_ms':int(clock[0]*1000),'price':'110','mark':None}
        def candle(t):return {'kind':'candle','observed_ms':int(clock[0]*1000),'candle':{'time':t,'open':prices[t],'high':prices[t],'low':prices[t],'close':prices[t],'volume':1}}
        class Stream:
            subscribed=True
            def __init__(self,*args):self.number=len(opened);self.step=0
            def open(self):opened.append(self.number)
            def close(self):closed.append(self.number)
            def read(self):
                self.step+=1
                if self.number==0:
                    if self.step==1:return [price()]
                    if self.step==2:clock[0]=180.;return [candle(120),candle(120)]
                    clock[0]=300.;raise ConnectionError('Synthetic socket interruption')
                if self.step==1:return [price(),candle(240)]
                if self.step==2:clock[0]=360.;return [candle(300)]
                manager.stop.set();return []
        with tempfile.TemporaryDirectory() as directory,patch('terminal.live.WindowsCredentials'),patch('terminal.live.time.time',side_effect=lambda:clock[0]),patch('terminal.live.reconnect_delay',return_value=0):
            manager=LiveManager(RunStore(Path(directory)),stream_factory=Stream,history_factory=History)
            try:
                sid=manager.journal.create(example_graph(),Profile(primary_minutes=1),'fixture','Synthetic reconnect')
                with manager.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(sid,canonical({'paper':False,'channels':[],'warmup_minutes':2}).decode()))
                manager.session_id=sid;manager._run(sid)
                events=manager.journal.events(sid)
                self.assertEqual(opened,[0,1]);self.assertEqual(closed,[0,1])
                self.assertEqual([(e['time'],e['type'],e['delivery']) for e in reversed(events)],[(180,'entry_long','disabled'),(240,'exit_long','suppressed'),(300,'entry_long','suppressed')])
                self.assertEqual(manager.journal.get(sid)['last_minute'],300)
                self.assertEqual(manager.replay(sid),{'match':True,'checked_events':3})
                self.assertTrue(any('Recovered 2 missing' in e['message'] for e in manager.log))
                self.assertEqual(LiveSession(manager.journal,sid).verify_replay(),{'match':True,'checked_events':3})
            finally:manager.close()

    def test_signal_waits_for_an_observation_after_its_availability(self):
        pending=PendingSignals()
        pending.offer({'time':120,'signals':{'entry_long':True}},120500)
        self.assertIsNone(pending.take({'observed_ms':120400,'provider_ms':120200}))
        self.assertIsNone(pending.take({'observed_ms':120600,'provider_ms':119999}))
        self.assertEqual(pending.take({'observed_ms':120700,'provider_ms':120650}),{'entry_long':True})
        self.assertIsNone(pending.take({'observed_ms':120800,'provider_ms':120750}))

    def test_single_session_and_notification_error_isolation(self):
        with tempfile.TemporaryDirectory() as directory,patch('terminal.live.WindowsCredentials') as credentials:
            credentials.return_value.load.return_value=None
            manager=LiveManager(RunStore(Path(directory)))
            try:
                manager.thread=Mock();manager.thread.is_alive.return_value=True
                with self.assertRaisesRegex(ValueError,'Only one'):manager.start('test',{},False,[])
                manager.thread=None
                manager.test_notification('telegram')
                manager.delivery_queue.join()
                self.assertIn('Telegram delivery failed',manager.status()['log'][-1]['message'])
                for _ in range(250):manager._log('Bounded fixture')
                self.assertEqual(len(manager.status()['log']),200)
            finally:manager.close()
