import unittest
from dataclasses import replace

from terminal.graph import GraphEvaluator, example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.signals import SignalStream, replay_signals
from terminal.simulation import run_backtest


def candles(prices):
    return [Candle(i*60, p, p, p, p, 1) for i, p in enumerate(prices)]


class SharedSignalTests(unittest.TestCase):
    def test_transition_dedup_reset_and_independent_times(self):
        # SMA2: 100,110 =>105 (true); 110,120=>115 (still true);
        # 120,90=>105 (false); 90,100=>95 (true again).
        rows = list(replay_signals(example_graph(), 1, 'closed', candles([100,110,120,90,100])))
        entries = [r['time'] for r in rows if 'entry_long' in r['transitions']]
        self.assertEqual(entries, [120,300])
        self.assertEqual([r['time'] for r in rows if 'exit_long' in r['transitions']], [240])
        self.assertEqual(rows[1]['values']['mean.value'], 105)

    def test_closed_forming_and_historical_use_identical_values(self):
        bars = candles([100]*60+[130]*30+[90]*30)
        for mode, expected_entries in [('intrabar',[3660]),('closed',[])]:
            rows = list(replay_signals(example_graph(),60,mode,bars))
            self.assertEqual([r['time'] for r in rows if 'entry_long' in r['transitions']], expected_entries)
            result = run_backtest(bars,Profile(primary_minutes=60,evaluation=mode),GraphEvaluator(example_graph()))
            self.assertEqual(result['indicators'],[{k:r[k] for k in ('time','values','signals')} for r in rows])
            changed = bars[:90]+[replace(b,open=800,high=800,low=800,close=800) for b in bars[90:]]
            future = list(replay_signals(example_graph(),60,mode,changed))
            self.assertEqual([r for r in rows if r['time']<=5400],[r for r in future if r['time']<=5400])

    def test_crossing_equality_and_restart_reconstruction(self):
        graph=example_graph();graph['nodes'][2]['type']='cross_above';graph['nodes'][2]['params']={}
        bars=candles([100,100,110,120,90,100])
        rows=list(replay_signals(graph,1,'closed',bars))
        self.assertEqual([r['time'] for r in rows if 'entry_long' in r['transitions']],[180,360])
        first=SignalStream(GraphEvaluator(graph),1,'closed')
        for b in bars[:4]:first.update(b)
        resumed=SignalStream(GraphEvaluator(graph),1,'closed')
        for b in bars[:4]:resumed.update(b)  # reconstruction, never dispatch old events
        self.assertEqual([first.update(b) for b in bars[4:]],[resumed.update(b) for b in bars[4:]])

    def test_ir_memory_is_bounded_and_out_of_order_is_rejected(self):
        stream=SignalStream(GraphEvaluator(example_graph()),1,'closed')
        for bar in candles([100]*2000):stream.update(bar)
        self.assertEqual(len(stream.frames.closed),2)
        with self.assertRaises(ValueError):stream.update(Candle(0,100,100,100,100,1))
