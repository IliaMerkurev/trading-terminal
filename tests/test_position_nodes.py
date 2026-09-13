import tempfile
from pathlib import Path
from dataclasses import replace
import unittest

from terminal.graph import GraphEvaluator, GraphError, POSITION_FIELDS
from terminal.position_management import position_context
from terminal.profile import Profile
from terminal.live_store import LiveSession, LiveStore
from terminal.storage import RunStore
from terminal.simulation import run_backtest
from test_graph import node, graph
from test_simulation import flat


def position_graph():
    return graph([*[node(k,k) for k in POSITION_FIELDS],node('zero','constant',value=0),node('one','constant',value=1),
                  node('flat','compare',{'left':'position_side.value','right':'zero.value'},operator='=='),
                  node('later','compare',{'left':'bars_since_entry.value','right':'one.value'},operator='>=')],
                 entry_long='flat.value',exit_long='later.value')


class PositionNodeTests(unittest.TestCase):
    def test_historical_position_nodes_observe_before_signal_orders(self):
        result=run_backtest(flat([100,110,120]),Profile(primary_minutes=1,fee_rate='0'),GraphEvaluator(position_graph()))
        values=[r['values'] for r in result['indicators']]
        self.assertEqual([r['position_side.value'] for r in values],[0,1,0])
        self.assertIsNone(values[0]['position_avg_entry.value'])
        self.assertEqual(values[1]['position_avg_entry.value'],100)
        self.assertEqual(values[1]['position_size.value'],1)
        self.assertEqual(values[1]['position_unrealized_pnl_pct.value'],10)
        self.assertEqual(values[1]['bars_since_entry.value'],1)
        self.assertEqual(result['metrics']['trade_count'],2)

    def test_missing_context_fails_instead_of_assuming_flat(self):
        with self.assertRaisesRegex(GraphError,'explicit recorded position context'):
            GraphEvaluator(position_graph())(flat([100]),60,True)

    def test_live_restart_replay_uses_recorded_context_not_current_position(self):
        with tempfile.TemporaryDirectory() as directory:
            store=LiveStore(RunStore(Path(directory)))
            sid=store.create(position_graph(),Profile(primary_minutes=1),'synthetic','Position context fixture')
            session=LiveSession(store,sid)
            session.ingest(flat([100])[0],60000,'warmup')
            session.position_provider=lambda candle:position_context(1,2,100,candle.close,59*10**9,(candle.time+60)*10**9-1,1)
            store.state(sid,'CONNECTED','Synthetic fixture')
            session.ingest(flat([100,110])[1],120000)
            saved=session.latest
            self.assertEqual(saved['values']['position_size.value'],2)
            session.position_provider=lambda _:position_context()
            session.ingest(flat([100,110,120])[2],180000)
            restored=LiveSession(store,sid)
            self.assertTrue(restored.verify_replay()['match'])
            with store.store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM live_position_contexts WHERE session_id=?',(sid,)).fetchone()[0],3)
            self.assertEqual(saved['values']['position_unrealized_pnl_pct.value'],10)

    def test_paper_position_context_does_not_include_later_fill(self):
        from terminal.paper_journal import PaperJournal
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            store=RunStore(Path(directory))
            with store.connect() as db:db.execute('CREATE TABLE paper_observations(session_id TEXT,sequence INTEGER,observation TEXT,result TEXT,PRIMARY KEY(session_id,sequence))')
            profile=Profile(primary_minutes=1,position_management={})
            paper=PaperJournal(store,'fixture',profile,Mock())
            try:
                event={'observed_ms':65000,'provider_ms':65000,'price':'100','mark':'100','next_funding_ms':None}
                paper.append(event,{'entry_long':True});paper.process()
                self.assertEqual(paper.position_context(flat([100])[0])['position_side'],0)
                self.assertEqual(paper.position_context(flat([100,110])[1])['position_side'],1)
                self.assertEqual(paper.position_context(flat([100,110])[1])['position_unrealized_pnl_pct'],10)
            finally:paper.close()

    def test_confirmed_primary_atr_is_restored_for_managed_live_session(self):
        from terminal.graph import example_graph
        with tempfile.TemporaryDirectory() as directory:
            store=LiveStore(RunStore(Path(directory)))
            profile=Profile(primary_minutes=1,position_management={'atr_period':2})
            sid=store.create(example_graph(),profile,'fixture','ATR fixture')
            session=LiveSession(store,sid)
            for candle in flat([100,104,106]):session.ingest(candle,(candle.time+60)*1000,'warmup')
            self.assertEqual(session.atr_manager.atr,2)
            restored=LiveSession(store,sid)
            self.assertEqual(restored.atr_manager.atr,2)
            self.assertEqual(restored.latest,session.latest)
