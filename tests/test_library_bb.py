from decimal import Decimal
import unittest
from terminal.graph import GraphEvaluator
from terminal.library import prepare
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class BollingerLibraryTests(unittest.TestCase):
    def test_independent_confluence_middle_exit_and_future_perturbation(self):
        prepared=prepare('bb-rsi-reversion',1,1,{'bb_period':3,'deviations':1,'rsi_period':2})
        def evaluate(prices):
            evaluator=GraphEvaluator(prepared['document']['graph']);bars=[];outputs=[]
            for i,p in enumerate(prices):
                bars.append(Candle(i*60,p,p+.1,p-.1,p,100))
                outputs.append(evaluator(bars,(i+1)*60,True))
            return outputs
        outputs=evaluate([10,10,10,6,10,11])
        self.assertFalse(outputs[2]['signals']['entry_long'])
        self.assertTrue(outputs[3]['signals']['entry_long'])
        self.assertTrue(outputs[4]['signals']['exit_long'])
        self.assertEqual(outputs[:4],evaluate([10,10,10,6,2,3])[:4])
        self.assertAlmostEqual(outputs[3]['values']['bands.middle'],26/3)

    def test_nontrivial_trade_golden_and_alternate_timeframe(self):
        for minutes in (1,3):
            prices=[p for p in [10,10,10,6,10,11] for _ in range(minutes)]
            bars=[Candle(i*60,p,p+.1,p-.1,p,100) for i,p in enumerate(prices)]
            prepared=prepare('bb-rsi-reversion',1,minutes,{'bb_period':3,'deviations':1,'rsi_period':2})
            profile=Profile(**{**prepared['profile'],'fee_rate':'0','allocation':'100'})
            result=run_backtest(bars,profile,GraphEvaluator(prepared['document']['graph']))
            self.assertEqual(len(result['trades']),1)
            self.assertEqual(Decimal(result['trades'][0]['entry']['price']),6)
            self.assertEqual(Decimal(result['trades'][0]['exit']['price']),10)
            self.assertEqual(Decimal(result['metrics']['net_pnl']),Decimal('66.664'))


if __name__=='__main__':unittest.main()
