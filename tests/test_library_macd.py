import copy
from decimal import Decimal
import unittest
from terminal.graph import GraphEvaluator,GraphError
from terminal.library import prepare
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class MacdLibraryTests(unittest.TestCase):
    def test_source_tolerance_independent_values_warmup_and_future(self):
        graph=prepare('macd-tolerance',1,1,{'fast':2,'slow':3,'signal':2})['document']['graph']
        def evaluate(prices):
            evaluator=GraphEvaluator(graph);bars=[];outputs=[]
            for i,p in enumerate(prices):
                bars.append(Candle(i*60,p,p+.1,p-.1,p,100))
                outputs.append(evaluator(bars,(i+1)*60,True))
            return outputs
        outputs=evaluate([10,12,14,16,8,7])
        self.assertTrue(all(not r['signals']['entry_long'] for r in outputs[:3]))
        self.assertAlmostEqual(outputs[3]['values']['entryThreshold.value'],203/5400)
        self.assertAlmostEqual(outputs[3]['values']['macd.histogram'],19/324)
        self.assertTrue(outputs[3]['signals']['entry_long'])
        self.assertTrue(outputs[4]['signals']['exit_long'])
        self.assertEqual(outputs[:4],evaluate([10,12,14,16,25,30])[:4])
        bad=copy.deepcopy(graph)
        bad['nodes']=[dict(id='a',type='constant',inputs={},params={'value':1e308}),dict(id='b',type='multiply',inputs={'left':'a.value','right':'a.value'},params={})]
        bad['outputs']={k:None for k in bad['outputs']}
        with self.assertRaisesRegex(GraphError,'non-finite'):GraphEvaluator(bad)([Candle(0,10,11,9,10,1)],60,True)

    def test_nontrivial_losing_trade_and_alternate_timeframe(self):
        for minutes in (1,3):
            prepared=prepare('macd-tolerance',1,minutes,{'fast':2,'slow':3,'signal':2})
            prices=[p for p in [10,12,14,16,8,7] for _ in range(minutes)]
            bars=[Candle(i*60,p,p+.1,p-.1,p,100) for i,p in enumerate(prices)]
            result=run_backtest(bars,Profile(**{**prepared['profile'],'fee_rate':'0','allocation':'100'}),GraphEvaluator(prepared['document']['graph']))
            self.assertEqual(len(result['trades']),1)
            self.assertEqual(Decimal(result['trades'][0]['entry']['price']),16)
            self.assertEqual(Decimal(result['trades'][0]['exit']['price']),8)
            self.assertEqual(Decimal(result['metrics']['net_pnl']),-50)


if __name__=='__main__':unittest.main()
