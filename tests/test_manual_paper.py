import json
from dataclasses import replace
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from terminal.live import LiveManager
from terminal.storage import RunStore
from terminal.profile import Profile,dec
from terminal.graph import example_graph
from terminal.paper_journal import PaperJournal


class ManualPaperTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.credentials=patch('terminal.live.WindowsCredentials');self.credentials.start();self.addCleanup(self.credentials.stop)
        self.manager=LiveManager(RunStore(Path(self.temp.name)));self.addCleanup(self.manager.close)
        self.profile=Profile(primary_minutes=1,allocation='100',fee_rate='.001',stop_loss='.05',take_profit='.2')
        self.sid=self.manager.journal.create(example_graph(),self.profile,'fixture','Synthetic manual PAPER')
        self.manager.session_id=self.sid;self.manager.thread=Mock();self.manager.thread.is_alive.return_value=True
        self.manager.journal.state(self.sid,'CONNECTED','Fixture synchronized')
        with self.manager.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(self.sid,json.dumps({'paper':True,'channels':[],'execution_source':'manual'})))
        self.manager.market.ticker_update({'lastPrice':'100'},100000)
        self.manager.market.book_update('snapshot',{'u':1,'seq':1,'b':[['99','1']],'a':[['101','1']]},100000)
        self.paper=PaperJournal(self.manager.store,self.sid,self.profile,None);self.addCleanup(self.paper.close)
        self.manager._set(paper=self.paper.snapshot(),paper_paused=False)

    def execute(self,action,identity,price,now):
        with patch('terminal.live.time.time',return_value=now):self.manager.manual(self.sid,action,identity)
        observed={'observed_ms':int(now*1000)+1,'provider_ms':int(now*1000)+1,'price':price,'mark':None}
        signals,request=self.manager._take_manual(observed)
        self.paper.append(observed,signals,manual_id=request);self.paper.process()
        self.manager._set(paper=self.paper.snapshot())

    def test_buy_close_costs_and_duplicate_request_do_not_duplicate_fills(self):
        self.execute('buy','1'*32,'100',100)
        self.assertEqual(self.paper.snapshot()['position']['quantity'],'1.000')
        self.assertEqual(self.paper.snapshot()['position']['stop'],'95.000')
        self.assertEqual(self.manager.manual(self.sid,'buy','1'*32)['status'],'applied')
        self.execute('close','2'*32,'110',160)
        self.assertEqual(self.paper.snapshot()['equity'],'1009.79')
        self.assertEqual(self.paper.snapshot()['fees'],'0.21')
        self.assertIsNone(self.paper.snapshot()['position'])
        self.assertEqual(self.paper.snapshot()['fills'][0]['reason'],'signal')

    def test_source_position_spot_and_stale_guards(self):
        with self.assertRaisesRegex(ValueError,'Spot'):self.manager.manual(self.sid,'sell','3'*32)
        with self.assertRaisesRegex(ValueError,'one-position'):self.manager.manual(self.sid,'close','4'*32)
        self.execute('buy','5'*32,'100',100)
        with self.assertRaisesRegex(ValueError,'one-position'):self.manager.manual(self.sid,'buy','6'*32)
        self.manager.market.reset()
        with self.assertRaisesRegex(ValueError,'synchronized'):self.manager.manual(self.sid,'close','7'*32)
        with self.manager.store.connect() as db:db.execute('UPDATE live_options SET options=?',(json.dumps({'paper':True,'execution_source':'strategy'}),))
        with self.assertRaisesRegex(ValueError,'Manual'):self.manager.manual(self.sid,'close','8'*32)

    def test_pending_requires_future_quote_and_cancels_on_pause(self):
        with patch('terminal.live.time.time',return_value=100):self.manager.manual(self.sid,'buy','9'*32)
        self.assertEqual(self.manager._take_manual({'observed_ms':100000,'provider_ms':100000}),(None,None))
        self.manager.pause()
        self.assertEqual(self.manager.manual(self.sid,'buy','9'*32)['status'],'cancelled_pause')
        self.assertEqual(self.manager._take_manual({'observed_ms':100001,'provider_ms':100001}),(None,None))

    def test_pending_expires_without_fill(self):
        with patch('terminal.live.time.time',return_value=100):self.manager.manual(self.sid,'buy','a'*32)
        self.assertEqual(self.manager._take_manual({'observed_ms':106000,'provider_ms':106000}),(None,None))
        self.assertEqual(self.manager.manual(self.sid,'buy','a'*32)['status'],'expired')
        self.assertEqual(self.paper.sequence,0)

    def test_request_and_paper_reconstruction_after_restart(self):
        self.execute('buy','b'*32,'100',100);before=self.paper.snapshot();self.paper.close()
        restored=PaperJournal(self.manager.store,self.sid,self.profile,None)
        self.addCleanup(restored.close)
        self.assertEqual(restored.snapshot(),before)
        self.assertEqual(restored.process(),[])
        self.assertEqual(self.manager.manual(self.sid,'buy','b'*32)['status'],'applied')

    def test_manual_perpetual_short_uses_shared_margin_account(self):
        self.paper.close()
        self.profile=replace(self.profile,market='linear',leverage='2',funding_mode='assumed_zero',mark_mode='last_proxy',stop_loss='0',take_profit='0')
        with self.manager.store.connect() as db:
            snapshot=json.loads(db.execute('SELECT snapshot FROM live_sessions WHERE id=?',(self.sid,)).fetchone()[0])
            snapshot['profile']=self.profile.snapshot()
            db.execute('UPDATE live_sessions SET snapshot=? WHERE id=?',(json.dumps(snapshot),self.sid))
        self.paper=PaperJournal(self.manager.store,self.sid,self.profile,None);self.addCleanup(self.paper.close)
        self.manager._set(paper=self.paper.snapshot())
        self.execute('sell','c'*32,'100',100)
        opened=self.paper.snapshot()
        self.assertEqual(opened['position']['side'],'short')
        self.assertEqual(opened['position']['quantity'],'2.000')
        self.assertEqual(dec(opened['position']['initial_margin']),dec('100'))
        self.execute('close','d'*32,'90',160)
        # Two units gain 20; fees are .20 + .18, without synthetic leverage PnL.
        self.assertEqual(self.paper.snapshot()['equity'],'1019.62')
        self.assertEqual(self.paper.snapshot()['fees'],'0.38')
        self.assertEqual(self.paper.snapshot()['realized_net_pnl'],'19.62')

    def test_restart_cancels_unobserved_request_without_filling(self):
        self.manager.manual(self.sid,'buy','e'*32)
        restored=LiveManager(self.manager.store);self.addCleanup(restored.close)
        self.assertEqual(restored.manual(self.sid,'buy','e'*32)['status'],'cancelled_restart')
        self.assertEqual(restored.journal.get(self.sid)['status'],'PAUSED')
        self.assertEqual(self.paper.sequence,0)

    def test_manual_position_still_uses_observed_price_protections(self):
        self.execute('buy','a1'*16,'100',100)
        self.paper.append({'observed_ms':160000,'provider_ms':160000,'price':'90','mark':None})
        self.paper.process()
        self.assertIsNone(self.paper.snapshot()['position'])
        self.assertEqual(self.paper.snapshot()['fills'][0]['reason'],'stop_loss')
        self.assertEqual(self.paper.snapshot()['fills'][0]['price'],'90.00')
        self.assertEqual(self.paper.snapshot()['equity'],'989.81')
