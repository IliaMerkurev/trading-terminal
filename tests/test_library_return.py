import unittest
from decimal import Decimal
from terminal.graph import GraphEvaluator, GraphError
from terminal.library import prepare
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class HistoricalReturnTests(unittest.TestCase):
    def test_independent_fraction_warmup_future_and_forming_state(self):
        graph=prepare('historical-return',1,1,{'lookback':2})['document']['graph']
        def evaluate(prices):
            evaluator=GraphEvaluator(graph);bars=[];outputs=[]
            for i,p in enumerate(prices):
                bars.append(Candle(i*60,p,p+.1,p-.1,p,100))
                outputs.append(evaluator(bars,(i+1)*60,True))
            return outputs
        outputs=evaluate([10,11,12,10])
        self.assertEqual([r['values']['return.value'] for r in outputs[:2]],[None,None])
        self.assertAlmostEqual(outputs[2]['values']['return.value'],.2)
        self.assertAlmostEqual(outputs[3]['values']['return.value'],-1/11)
        self.assertTrue(outputs[2]['signals']['entry_long']);self.assertTrue(outputs[3]['signals']['exit_long'])
        self.assertEqual(outputs[:3],evaluate([10,11,12,200])[:3])
        e=GraphEvaluator(graph)
        e([Candle(0,10,10,10,10,1)],60,True)
        e([Candle(60,20,20,20,20,1)],90,False)
        e([Candle(60,11,11,11,11,1)],120,True)
        r=e([Candle(120,12,12,12,12,1)],180,True)
        self.assertAlmostEqual(r['values']['return.value'],.2)
        graph['nodes'][0]=dict(id='close',type='constant',inputs={},params={'value':0})
        with self.assertRaisesRegex(GraphError,'denominator'):evaluate([1,1,1])

    def test_nontrivial_trade_and_alternate_timeframe(self):
        for minutes in (1,3):
            prepared=prepare('historical-return',1,minutes,{'lookback':2})
            prices=[p for p in [10,11,12,10,9] for _ in range(minutes)]
            bars=[Candle(i*60,p,p+.1,p-.1,p,100) for i,p in enumerate(prices)]
            result=run_backtest(bars,Profile(**{**prepared['profile'],'fee_rate':'0','allocation':'120'}),GraphEvaluator(prepared['document']['graph']))
            self.assertEqual(len(result['trades']),1)
            self.assertEqual(Decimal(result['trades'][0]['entry']['price']),12)
            self.assertEqual(Decimal(result['trades'][0]['exit']['price']),10)
            self.assertEqual(Decimal(result['metrics']['net_pnl']),-20)


if __name__=='__main__':unittest.main()
