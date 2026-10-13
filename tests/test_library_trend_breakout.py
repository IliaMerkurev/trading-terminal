from decimal import Decimal as D
import unittest
from terminal.graph import GraphEvaluator, GraphError, validate_graph
from terminal.library import prepare
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class TrendBreakoutTests(unittest.TestCase):
    def graph(self,entry,params):return prepare(entry,1,1440,params)['document']['graph']

    def test_prior_channel_excludes_current_extrema_and_partial_updates_do_not_commit(self):
        graph=self.graph('donchian-breakout',{'upper_period':2,'lower_period':2})
        evaluator=GraphEvaluator(graph)
        for i,p in enumerate([10,11]):
            result=evaluator([Candle(i*60,p,p+1,p-1,p,1)],(i+1)*60,True)
            self.assertIsNone(result['values']['channel.upper'])
        for at,price in [(140,12),(160,99),(180,12)]:
            result=evaluator([Candle(120,price,price+1,price-1,price,1)],at,at==180)
            self.assertEqual(result['values']['channel.upper'],12)
            self.assertEqual(result['values']['channel.lower'],9)
            self.assertEqual(result['signals']['entry_long'],price>12)
        next_value=evaluator([Candle(180,14,15,13,14,1)],240,True)
        self.assertEqual(next_value['values']['channel.upper'],13)
        self.assertEqual(next_value['values']['channel.lower'],10)
        self.assertTrue(next_value['signals']['entry_long'])
        bad=self.graph('donchian-breakout',{'upper_period':2,'lower_period':2})
        bad['nodes'][1]['params']['upper_period']=1.5
        with self.assertRaises(GraphError):validate_graph(bad)

    def test_donchian_daily_exact_costed_lifecycle_and_future_perturbation(self):
        graph=self.graph('donchian-breakout',{'upper_period':2,'lower_period':2})
        bars=[Candle(i*86400,p,p+1,p-1,p,100) for i,p in enumerate([10,11,12,14,9,10])]
        profile=Profile(primary_minutes=1440,execution_minutes=1440,version=2,fee_rate='.001')
        result=run_backtest(bars,profile,GraphEvaluator(graph))
        self.assertEqual([D(f['price']) for f in result['fills']],[14,9])
        self.assertEqual(D(result['metrics']['fees']),D('.164266'))
        self.assertEqual(D(result['metrics']['net_pnl']),D('-35.874266'))
        self.assertEqual(result['fills'][0]['time_ns'],4*86400*10**9-1)
        changed=run_backtest(bars[:4]+[Candle(c.time,100,101,99,100,100) for c in bars[4:]],profile,GraphEvaluator(graph))
        self.assertEqual(result['indicators'][:4],changed['indicators'][:4])
        self.assertEqual(result['fills'][0],changed['fills'][0])

    def test_ema_trend_independent_recursions_and_costed_trade(self):
        graph=self.graph('ema-trend',{'fast':2,'slow':3,'tolerance':0})
        bars=[Candle(i*14400,p,p,p,p,100) for i,p in enumerate([10,12,14,16,12,10])]
        result=run_backtest(bars,Profile(primary_minutes=240,execution_minutes=240,version=2,fee_rate='.001'),GraphEvaluator(graph))
        self.assertAlmostEqual(result['indicators'][2]['values']['fast.value'],118/9)
        self.assertEqual(result['indicators'][2]['values']['slow.value'],12.5)
        self.assertEqual([D(f['price']) for f in result['fills']],[14,12])
        self.assertEqual(D(result['metrics']['fees']),D('.185692'))
        self.assertEqual(D(result['metrics']['net_pnl']),D('-14.469692'))
        with self.assertRaisesRegex(ValueError,'Fast EMA'):self.graph('ema-trend',{'fast':30,'slow':15})

    def test_bounded_prior_state_and_graph_warmup_contract(self):
        from terminal.experiments import warmup_bars
        graph=self.graph('donchian-breakout',{'upper_period':3,'lower_period':2})
        self.assertEqual(warmup_bars(graph),4)
        evaluator=GraphEvaluator(graph)
        for i in range(100):evaluator([Candle(i*60,10,11,9,10,1)],(i+1)*60,True)
        self.assertEqual([len(q) for q in evaluator.states['channel']],[3,2])
