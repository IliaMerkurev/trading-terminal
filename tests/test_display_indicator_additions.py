"""Independent short arithmetic; no runtime-generated expected indicator values."""
import copy
import unittest
from terminal.display_indicators import calculate, validate_instances
from terminal.graph import indicator_for
from tests.test_display_indicators import instance, candles
from tests import test_display_indicators as infrastructure

ITEMS = [instance('atr',period=3), instance('stochastic',period=3,smooth=2,signal=2), instance('obv')]

class AdditionArithmeticTests(unittest.TestCase):
    def test_atr_true_range_mean_seed_and_unchanged_graph_seed(self):
        rows=candles([10,13,11,10.5])
        for row,(high,low) in zip(rows,[(11,9),(14,13),(12,10),(11,10)]):row.update(high=high,low=low)
        values=calculate(rows,[ITEMS[0]],1,0,180)['columns']['atr']['value']
        self.assertEqual(values[:3],[None,None,3]);self.assertAlmostEqual(values[3],7/3)
        graph=indicator_for(ITEMS[0])
        for row in rows[:3]:graph.update_raw(row['high'],row['low'],row['close'])
        self.assertAlmostEqual(graph.value,25/9) # Engine seed is deliberately unchanged.
        self.assertEqual(calculate(rows,[instance('atr',period=1)],1,0,180)['columns']['atr']['value'],[2,4,3,1])

    def test_stochastic_independent_smoothed_ports_and_flat_window(self):
        rows=candles([2,4,6,8,10,0])
        for row in rows:row.update(high=10,low=0)
        out=calculate(rows,[ITEMS[1]],1,0,300)['columns']['stochastic']
        self.assertEqual(out,{'k':[None,None,None,70,90,50],'d':[None,None,None,None,80,70]})
        for row in rows:row.update(high=4,low=4,close=4)
        out=calculate(rows,[ITEMS[1]],1,0,300)['columns']['stochastic']
        self.assertEqual(out['k'],[None,None,None,0,0,0]);self.assertEqual(out['d'],[None,None,None,None,0,0])

    def test_stochastic_finite_large_and_tiny_price_ranges(self):
        item=instance('stochastic',period=1,smooth=1,signal=1)
        for magnitude in (1e307,1e-310):
            rows=[dict(time=0,open=magnitude/2,high=magnitude,low=0,close=magnitude/2,volume=1,confirmation='synthetic_closed')]
            out=calculate(rows,[item],1,0,0)['columns']['stochastic']
            self.assertAlmostEqual(out['k'][0],50.0,places=10)
            self.assertAlmostEqual(out['d'][0],50.0,places=10)

    def test_obv_equal_close_zero_volume_missing_and_negative_values(self):
        rows=candles([10,11,11,9,12])
        for row,volume in zip(rows,[100,20,30,40,0]):row['volume']=volume
        self.assertEqual(calculate(rows,[ITEMS[2]],1,0,240)['columns']['obv']['value'],[0,20,20,-20,-20])
        for bad in (None,True,-1,float('nan'),float('inf')):
            changed=copy.deepcopy(rows);changed[2]['volume']=bad
            self.assertEqual(calculate(changed,[ITEMS[2]],1,0,240)['columns']['obv']['value'],[0,20,None,0,0])

    def test_future_perturbation_confirmation_and_gap_restart_all_new_kinds(self):
        rows=candles([10,11,12,10,15,12,13,14,16,12,14,15])
        base=calculate(rows,ITEMS,1,0,660)
        changed=copy.deepcopy(rows);changed[-1].update(high=800,low=1,close=500,volume=9000)
        future=calculate(changed,ITEMS,1,0,660)
        for ident,ports in base['columns'].items():
            for port,values in ports.items():self.assertEqual(values[:-1],future['columns'][ident][port][:-1])
        for confirmation in ('forming','legacy_unknown'):
            changed=copy.deepcopy(rows);changed[5]['confirmation']=confirmation
            output=calculate(changed,ITEMS,1,0,660)
            suffix=calculate(rows[6:],ITEMS,1,360,660)
            for ident,ports in output['columns'].items():
                for port,values in ports.items():
                    self.assertIsNone(values[5]);self.assertEqual(values[6:],suffix['columns'][ident][port])
        gapped=calculate(rows[:5]+rows[6:],ITEMS,1,0,660)
        self.assertEqual(gapped['times'][5],360)
        for ident,ports in gapped['columns'].items():
            for port,values in ports.items():
                self.assertIsNone(values[5]);self.assertEqual(values[6:],suffix['columns'][ident][port])
        changed=copy.deepcopy(rows);changed[5]['confirmation']='conflict'
        with self.assertRaises(ValueError):calculate(changed,ITEMS,1,0,660)

    def test_parameter_bounds_and_maximum_stochastic_warmup(self):
        for item in ITEMS:validate_instances([item])
        for kind,params in [('atr',{'period':True}),('stochastic',{'period':14,'smooth':0,'signal':3}),('obv',{'period':14})]:
            with self.assertRaises(ValueError):validate_instances([instance(kind,**params)])
        rows=candles([10]*2998)
        out=calculate(rows,[instance('stochastic',period=1000,smooth=1000,signal=1000)],1,0,2997*60)['columns']['stochastic']
        self.assertIsNone(out['k'][1997]);self.assertEqual(out['k'][1998],50)
        self.assertTrue(all(value is None for value in out['d'][:-1]));self.assertEqual(out['d'][-1],50)

class AdditionCacheTests(unittest.TestCase):
    setUp = infrastructure.DisplayCacheTests.setUp
    tearDown = infrastructure.DisplayCacheTests.tearDown
    seed = infrastructure.DisplayCacheTests.seed
    read = infrastructure.DisplayCacheTests.read
    # Inherit infrastructure, not unrelated existing test cases.
    def test_new_instances_persist_origin_and_stay_unavailable_before_origin(self):
        rows=candles([100+i%7 for i in range(30)]);self.seed(rows[10:])
        self.settings=self.display.save('spot','BTCUSDT',ITEMS,0)
        original=self.read(start=600,end=1740)
        self.seed(rows[:10])
        full=self.read(start=0,end=1740)
        for ident,ports in full['columns'].items():
            for port,values in ports.items():
                self.assertEqual(values[:10],[None]*10)
                self.assertEqual(values[10:],original['columns'][ident][port])
        self.assertEqual(self.display.settings('spot','BTCUSDT')['instances'],ITEMS)
        self.assertEqual(self.display.settings('spot','BTCUSDT',source='okx')['revision'],0)
        self.display.close()
        from terminal.display_indicators import DisplayIndicators
        self.display=DisplayIndicators(self.chart)
        self.assertEqual(self.read(start=600,end=1740)['columns'],original['columns'])
