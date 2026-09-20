from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from terminal.benchmarks import run, schedule, metrics, contract
from terminal.profile import Profile
from terminal.series import Candle


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.profile=Profile(capital='180',fee_rate='0',quantity_step='0.001',min_notional='0.01',gap_policy='skip',primary_minutes=1)

    def test_independent_lump_sum_and_equal_capital_dca(self):
        bars=[Candle(t,p,p,p,p,100) for t,p in [(0,10),(86400,20),(172800,30),(259140,30)]]
        dca=run(bars,self.profile,0,259200,'daily'); hold=run(bars,self.profile,0,259200,'once')
        self.assertEqual([Decimal(f['quantity']) for f in dca['fills'][:-1]],[6,3,2])
        self.assertEqual(Decimal(dca['metrics']['final_equity']),330)
        self.assertEqual(Decimal(hold['metrics']['final_equity']),540)
        self.assertEqual(dca['metrics']['trade_count'],1)
        self.assertEqual(Decimal(dca['equity'][0]['equity']),180)
        self.assertEqual(Decimal(dca['equity'][0]['cash']),120)
        self.assertIsNone(dca['research_metrics']['annualized_geometric_return'])

    def test_flat_fees_rounding_cash_and_terminal_costs(self):
        bars=[Candle(0,10,10,10,10,100),Candle(60,10,10,10,10,100)]
        result=run(bars,replace(self.profile,fee_rate='0.001'),0,120,'once')
        # Floor(180 / 10.01 / .001)*.001=17.982; each fee .17982; residual entry cash .00018.
        self.assertEqual(Decimal(result['fills'][0]['quantity']),Decimal('17.982'))
        self.assertEqual(Decimal(result['metrics']['final_equity']),Decimal('179.64036'))
        self.assertEqual(Decimal(result['metrics']['fees']),Decimal('.35964'))
        self.assertEqual(Decimal(result['metrics']['net_pnl']),Decimal('-.35964'))

    def test_bearish_no_deposits_and_no_end_boundary_purchase(self):
        bars=[Candle(t,p,p,p,p,100) for t,p in [(0,30),(86400,20),(172740,10)]]
        result=run(bars,self.profile,0,172800,'daily')
        self.assertEqual([Decimal(f['quantity']) for f in result['fills'][:-1]],[3,Decimal('4.5')])
        self.assertEqual(Decimal(result['metrics']['final_equity']),75)
        self.assertEqual(result['benchmark']['purchases'],[0,86400])

    def test_actual_quote_slippage_changes_fills_and_equity(self):
        bars=[Candle(0,10,10,10,10,100),Candle(60,10,10,10,10,100)]
        result=run(bars,replace(self.profile,slippage='.1'),0,120,'once')
        self.assertEqual([Decimal(f['price']) for f in result['fills']],[11,9])
        self.assertEqual(Decimal(result['metrics']['final_equity']),Decimal('147.274'))

    def test_gaps_and_minimum_rejections_are_visible(self):
        bars=[Candle(60,10,10,10,10,100),Candle(120,10,10,10,10,100)]
        result=run(bars,replace(self.profile,min_quantity='100'),0,180,'once')
        self.assertEqual(result['metrics']['trade_count'],0)
        self.assertIsNone(result['metrics']['win_rate'])
        self.assertEqual(Decimal(result['metrics']['final_equity']),180)
        self.assertTrue(any('delayed' in d['message'] for d in result['diagnostics']))
        self.assertTrue(any('rejected' in d['message'] for d in result['diagnostics']))

    def test_calendar_contract_hash_and_annualization(self):
        stamp=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
        self.assertEqual(schedule(stamp('2024-01-31'),stamp('2024-04-01'),'monthly'),[stamp(x) for x in ['2024-01-31','2024-02-29','2024-03-31']])
        dataset={'market':'spot','symbol':'BTCUSDT','range':[0,365*86400],'id':'data','content_sha256':'content','source':'Bybit'}
        one=contract(self.profile,dataset,0,86400)
        self.assertNotEqual(one['contract_sha256'],contract(replace(self.profile,capital='181'),dataset,0,86400)['contract_sha256'])
        result={'status':'completed','profile':self.profile.snapshot(),'metrics':{'final_equity':'360','max_drawdown':'0','trade_count':1,'win_rate':1,'fees':'0','funding':'0'}}
        self.assertAlmostEqual(metrics(result,0,365*86400)['annualized_geometric_return'],1)
        self.assertIsNone(metrics(result,0,364*86400)['annualized_geometric_return'])
        with self.assertRaisesRegex(ValueError,'spot history'):contract(self.profile,{**dataset,'market':'linear'},0,86400)
        with self.assertRaises(ValueError):run([Candle(0,10,10,10,10,1)],replace(self.profile,stop_loss='.1'),0,60,'once')


if __name__=='__main__':unittest.main()
