"""Independent arithmetic and causal/cache contracts for six advanced kinds."""
import copy
import math
import threading
import unittest
from terminal import display_formula_catalog as formulas
from terminal.display_indicators import calculate, validate_instances, FIELDS, DisplayIndicators
from tests.test_display_indicators import instance, candles
from tests import test_display_indicators as infrastructure

ITEMS = [instance('dmi', period=2, adx_period=2),
         instance('supertrend', period=2, multiplier=1),
         instance('stochrsi', period=2, stochastic_period=2, smooth=2, signal=2),
         instance('hma', period=4), instance('bbpercentb', period=2, deviations=2),
         instance('bbwidth', period=2, deviations=2)]


def replay(rows, items=ITEMS):
    return calculate(rows, items, 1, 0, rows[-1]['time'])['columns']


class AdvancedArithmeticTests(unittest.TestCase):
    def assert_values(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for got, wanted in zip(actual, expected):
            if wanted is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, wanted, places=10)

    def test_dmi_independent_changes_seed_and_adx(self):
        out = replay(candles([10,12,11,14,10]), [ITEMS[0]])['dmi']
        self.assert_values(out['plus_di'], [None,None,40,800/13,800/33])
        self.assert_values(out['minus_di'], [None,None,20,100/13,1700/33])
        self.assert_values(out['adx'], [None,None,None,500/9,412/9])
        # An outside candle has equal positive changes: both DM must be zero.
        rows = candles([10,10,10])
        rows[1].update(high=13, low=7)
        rows[2].update(high=12, low=8)  # Both changes negative: also zero.
        out = replay(rows, [instance('dmi',period=1,adx_period=1)])['dmi']
        for values in out.values(): self.assertEqual(values, [None,0,0])
        for row in rows: row.update(high=10,low=10)
        self.assertEqual(replay(rows,[instance('dmi',period=1,adx_period=1)])['dmi'], out)

    def test_supertrend_carried_bands_flips_and_line_breaks(self):
        out = replay(candles([10,12,11,7,8,13,12]), [ITEMS[1]])['supertrend']
        self.assert_values(out['up'], [None,9.5,9.5,None,None,8.59375,8.796875])
        self.assert_values(out['down'], [None,None,None,10.625,10.625,None,None])
        self.assertEqual(out['direction'], [None,1,1,-1,-1,1,1])
        rows = candles([10,8,7,9,10])
        out = replay(rows,[instance('supertrend',period=1,multiplier=1)])['supertrend']
        # Equality with carried lower at close 8 retains up; close 9 equals
        # carried upper after the down flip and retains down.
        self.assertEqual(out['direction'], [1,1,-1,-1,1])
        self.assertEqual(out['up'], [8,8,None,None,8])
        self.assertEqual(out['down'], [None,None,9,9,None])

    def test_stochrsi_exact_existing_seed_and_port_warmup(self):
        rows = candles([10,12,11,14,10,13])
        rsi = replay(rows,[instance('rsi',period=2)])['rsi']['value']
        # First-close zero delta; gains/losses Wilder-smoothed from zero.
        self.assert_values(rsi,[None,None,50,87.5,175/6,775/12])
        out = replay(rows,[ITEMS[2]])['stochrsi']
        self.assertEqual(out['k'],[None,None,None,None,50,50])
        self.assertEqual(out['d'],[None,None,None,None,None,50])
        item = instance('stochrsi',period=2,stochastic_period=3,smooth=1,signal=1)
        for values in replay(rows,[item])['stochrsi'].values():
            self.assert_values(values,[None,None,None,None,0,425/7])
        self.assertEqual(formulas.metadata(ITEMS[2])['port_warmup_bars'],dict(k=5,d=6))
        flat = replay(candles([10]*6),[ITEMS[2]])['stochrsi']
        self.assertEqual(flat['k'],[None]*4+[0,0]); self.assertEqual(flat['d'],[None]*5+[0])

    def test_hma_independent_weighted_windows_and_floor_rounding(self):
        # N=4: full WMA 29/5,39/5,33/5; half WMA 20/3,26/3,6;
        # inner 113/15,143/15,27/5; root WMA 133/15,61/9.
        out = replay(candles([2,4,8,6,10,4]),[ITEMS[3]])['hma']['value']
        self.assert_values(out,[None,None,None,None,133/15,61/9])
        # N=3 floors half to 1 and sqrt to 1, so no added warmup.
        item = instance('hma',period=3)
        self.assert_values(replay(candles([2,4,8,6]),[item])['hma']['value'],[None,None,31/3,17/3])
        self.assertEqual(replay(candles([2,4,8]),[instance('hma',period=1)])['hma']['value'],[2,4,8])

    def test_bollinger_ratios_population_unclipped_and_zero_policies(self):
        rows = candles([10,12,14,10])
        out = replay(rows,ITEMS[4:])
        self.assert_values(out['bbpercentb']['value'],[None,.75,.75,.25])
        self.assert_values(out['bbwidth']['value'],[None,400/11,400/13,200/3])
        # Narrow deviations deliberately put %B above 1 / below 0.
        item = instance('bbpercentb',period=2,deviations=.5)
        self.assert_values(replay(rows,[item])['bbpercentb']['value'],[None,1.5,1.5,-.5])
        out = replay(candles([2,2]),ITEMS[4:])
        self.assertIsNone(out['bbpercentb']['value'][-1]); self.assertEqual(out['bbwidth']['value'][-1],0)
        out = replay(candles([-1,1]),ITEMS[4:])
        self.assertEqual(out['bbpercentb']['value'][-1],.75); self.assertIsNone(out['bbwidth']['value'][-1])
        for kind in ('bbpercentb','bbwidth'):
            self.assertEqual(replay(candles([2,4]),[instance(kind,period=1,deviations=2)])[kind]['value'],[None,None] if kind=='bbpercentb' else [0,0])

    def test_period_one_maximum_and_parameter_validation(self):
        for item in ITEMS:
            validate_instances([item])
            for key in item['params']:
                fractional = key in ('multiplier','deviations')
                for bad in (True,False,0,-1,1001,math.inf,math.nan,'2') + (() if fractional else (1.5,)):
                    changed=copy.deepcopy(item); changed['params'][key]=bad
                    with self.assertRaises(ValueError): validate_instances([changed])
                for good in ((.01,10) if fractional else (1,1000)):
                    changed=copy.deepcopy(item); changed['params'][key]=good
                    validate_instances([changed])
            for operation in ('missing','extra'):
                changed=copy.deepcopy(item)
                if operation=='missing': changed['params'].pop('period')
                else: changed['params']['extra']=1
                with self.assertRaises(ValueError): validate_instances([changed])
        items=[dict(ITEMS[0],id='i'+str(i)) for i in range(9)]
        self.assertEqual(len(validate_instances(items)),9)
        tiny=instance('stochrsi',period=1,stochastic_period=1,smooth=1,signal=1)
        self.assertEqual(replay(candles([10,11]),[tiny])['stochrsi'],dict(k=[None,0],d=[None,0]))
        large=instance('stochrsi',period=1000,stochastic_period=1000,smooth=1000,signal=1000)
        out=replay(candles([10]*3998),[large])['stochrsi']
        self.assertEqual(out['k'][:2998],[None]*2998); self.assertEqual(out['k'][2998],0)
        self.assertEqual(out['d'],[None]*3997+[0])
        self.assertEqual(formulas.metadata(large)['warmup_bars'],3998)
        for item, count, port in [(instance('dmi',period=1000,adx_period=1000),2000,'adx'),
                                  (instance('hma',period=1000),1030,'value'),
                                  (instance('supertrend',period=1000,multiplier=1),1000,'up')]:
            values=replay(candles([10]*count),[item])[item['type']][port]
            self.assertEqual(values[:-1],[None]*(count-1))
            self.assertIsNotNone(values[-1])
            self.assertEqual(formulas.metadata(item)['warmup_bars'],count)

    def test_future_perturbation_unknown_gap_conflict_and_cancel(self):
        rows=candles([10,12,11,14,10,13]*3)
        base=replay(rows)
        changed=copy.deepcopy(rows); changed[-1].update(high=120,low=50,close=100)
        future=replay(changed)
        for kind,ports in base.items():
            for port,values in ports.items(): self.assertEqual(values[:-1],future[kind][port][:-1])
        suffix=replay(rows[7:])
        for confirmation in ('forming','legacy_unknown'):
            changed=copy.deepcopy(rows); changed[6]['confirmation']=confirmation
            out=replay(changed)
            for kind,ports in out.items():
                for port,values in ports.items():
                    self.assertIsNone(values[6]); self.assertEqual(values[7:],suffix[kind][port])
        out=replay(rows[:6]+rows[7:])
        for kind,ports in out.items():
            for port,values in ports.items():
                self.assertIsNone(values[6]); self.assertEqual(values[7:],suffix[kind][port])
        changed[6]['confirmation']='conflict'
        with self.assertRaisesRegex(ValueError,'conflict'): replay(changed)
        cancel=threading.Event(); cancel.set()
        with self.assertRaises(InterruptedError): calculate(rows,ITEMS,1,0,1020,cancel)


class AdvancedTransportTests(unittest.TestCase):
    setUp=infrastructure.DisplayCacheTests.setUp
    tearDown=infrastructure.DisplayCacheTests.tearDown
    seed=infrastructure.DisplayCacheTests.seed
    read=infrastructure.DisplayCacheTests.read

    def test_metadata_origin_reopen_and_raw_ha_independence(self):
        self.assertEqual(len(FIELDS),33)
        rows=candles([10+i%7 for i in range(40)])
        self.seed(rows[10:])
        self.settings=self.display.save('spot','BTCUSDT',ITEMS,0)
        original=self.read(600,2340)
        self.assertEqual(original['status'],'ready')
        self.seed(rows[:10]); full=self.read(0,2340)
        self.assertEqual(full['origin']['time'],600)
        for item in ITEMS:
            kind=item['type']; meta=full['formula_metadata'][kind]
            self.assertEqual(meta,formulas.metadata(item))
            self.assertEqual(meta['ports'],list(formulas.ports(kind)))
            self.assertEqual(meta['before_origin'],'unavailable')
            for port,values in full['columns'][kind].items():
                self.assertEqual(values[:10],[None]*10)
                self.assertEqual(values[10:],original['columns'][kind][port])
        ha=self.read(0,2340,price_style='heikin_ashi')
        self.assertEqual(ha['columns'],full['columns'])
        self.assertEqual(ha['formula_metadata'],full['formula_metadata'])
        self.assertEqual(self.display.settings('spot','BTCUSDT',source='okx')['revision'],0)
        self.display.close(); self.display=DisplayIndicators(self.chart)
        self.assertEqual(self.read(600,2340)['columns'],original['columns'])
