import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from terminal.live import LiveManager
from terminal.live_data import LiveHistory
from terminal.profile import Profile
from terminal.graph import example_graph
from terminal.series import Candle
from terminal.storage import RunStore
from terminal.data import canonical


class Stream:
    subscribed=True
    def __init__(self,*args):pass
    def open(self):self.state.connected()
    def close(self):pass
    def read(self):
        time.sleep(.02);stamp=int(time.time()*1000)
        self.state.ticker_update({'lastPrice':'100'},stamp)
        self.state.book_update('snapshot',{'u':1,'seq':1,'b':[['99','1']],'a':[['101','1']]},stamp)
        return [{'kind':'price','provider_ms':stamp,'observed_ms':stamp,'price':'100','mark':None}]


class IndependentPaperTests(unittest.TestCase):
    def wait(self,predicate):
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.02)
        self.fail('Independent paper fixture deadline exceeded')

    def test_manual_paper_needs_no_strategy_or_historical_warmup(self):
        class History(LiveHistory):
            def recover(self,*args,**kwargs):raise AssertionError('No strategy/ATR history should be requested')
        with tempfile.TemporaryDirectory() as directory,patch('terminal.live.WindowsCredentials'):
            manager=LiveManager(RunStore(Path(directory)),stream_factory=Stream,history_factory=History)
            try:
                sid=manager.start_manual(Profile(primary_minutes=60,position_management={'max_entries':3}).snapshot())['session_id']
                self.wait(lambda:manager.status()['paper_ready'])
                self.assertEqual(manager.status()['strategy_state'],'NOT SELECTED')
                manager.manual(sid,'buy','1'*32)
                self.wait(lambda:bool(manager.status()['paper']['position']))
                manager.manual(sid,'reduce_25','2'*32)
                self.wait(lambda:manager.status()['paper']['position']['quantity']=='0.750')
                self.assertEqual(manager.status()['paper']['position']['quantity'],'0.750')
                self.assertEqual(manager.journal.events(sid),[])
                first=manager.journal.paper_lifecycle(sid,limit=1)
                self.assertEqual(first['rows'][0]['type'],'reduction')
                second=manager.journal.paper_lifecycle(sid,before=first['next'],limit=1)
                self.assertEqual(second['rows'][0]['type'],'entry')
                self.assertIsNone(second['next'])
                self.assertEqual(manager.status()['market']['counts']['connections'],1)
            finally:manager.close()

    def test_manual_paper_runs_while_strategy_history_is_blocked(self):
        entered=threading.Event();release=threading.Event()
        class History(LiveHistory):
            def candles(self,market,symbol,start,end):
                entered.set()
                if not release.wait(6):raise TimeoutError('Fixture history deadline')
                return [Candle(t,100,100,100,100,1) for t in range(start,end,60)]
        with tempfile.TemporaryDirectory() as directory,patch('terminal.live.WindowsCredentials'):
            manager=LiveManager(RunStore(Path(directory)),stream_factory=Stream,history_factory=History)
            try:
                sid=manager.journal.create(example_graph(),Profile(primary_minutes=1,position_management={}), 'fixture','Synthetic warming strategy')
                with manager.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(sid,canonical({'paper':True,'channels':[],'warmup_minutes':2,'execution_source':'manual'}).decode()))
                manager.resume(sid,False);self.assertTrue(entered.wait(2))
                self.wait(lambda:manager.status()['paper_ready'])
                self.assertEqual(manager.status()['strategy_state'],'WARMING UP')
                manager.manual(sid,'buy','3'*32)
                self.wait(lambda:bool(manager.status()['paper']['position']))
                self.assertEqual(manager.status()['events'],[])
                self.assertEqual(manager.status()['strategy_state'],'WARMING UP')
                release.set();self.wait(lambda:manager.status()['strategy_state']=='READY')
                self.assertEqual(manager.status()['market']['counts']['connections'],1)
            finally:release.set();manager.close()
