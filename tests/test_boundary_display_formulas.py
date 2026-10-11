"""Independent local SAR goldens and exact-boundary VWAP coverage contracts."""
import copy
import threading
import unittest
from terminal import display_formula_catalog as formulas
from terminal.display_indicators import calculate, validate_instances, DisplayIndicators, FIELDS
from tests.test_display_indicators import instance, candles
from tests import test_display_indicators as infrastructure

SAR = instance('sar', step=.02, max=.2)
VWAP = instance('vwap', mode=0, anchor=0)


def replay(rows, items=None, minutes=1):
    return calculate(rows, items or [SAR, VWAP], minutes, 0, rows[-1]['time'])


class BoundaryArithmeticTests(unittest.TestCase):
    def test_sar_independent_golden_reversals_and_mirror(self):
        rows = candles([9,10,11,12,8,7,9])
        for row, (high, low) in zip(rows, [(10,8),(11,9),(12,10),(13,11),(12,7),(9,6),(10,7)]):
            row.update(high=high, low=low)
        expected = [None,8,8,8.16,13,13,12.72]
        for value, want in zip(replay(rows)['columns']['sar']['value'], expected):
            if want is None: self.assertIsNone(value)
            else: self.assertAlmostEqual(value, want)
        mirrored = copy.deepcopy(rows)
        for row in mirrored:
            row.update(high=30-row['low'], low=30-row['high'], close=30-row['close'])
        for value, want in zip(replay(mirrored)['columns']['sar']['value'], expected):
            if want is None: self.assertIsNone(value)
            else: self.assertAlmostEqual(value, 30-want)

    def test_sar_ties_clamps_strict_extremes_and_cap(self):
        state = formulas.FormulaState(instance('sar', step=.1, max=.2))
        rows = candles([10,10,10,11,12,13,14])
        self.assertIsNone(state.update(rows[0])['value'])
        self.assertEqual(state.update(rows[1])['value'], 9)  # Close tie chooses up.
        self.assertEqual(state.direction, 1)
        self.assertEqual(state.update(rows[2])['value'], 9)  # Equality retains.
        self.assertEqual(state.af, .1)  # Equal high is not a new extreme.
        state.update(rows[3]); self.assertEqual(state.af, .2)
        state.update(rows[4]); self.assertEqual(state.af, .2)
        self.assertAlmostEqual(state.update(rows[5])['value'], 9.8)
        self.assertAlmostEqual(state.update(rows[6])['value'], 10.64)
        # Reversal takes current extreme when beyond previous EP.
        state.update(dict(high=20, low=1, close=2))
        self.assertEqual((state.value, state.ep, state.direction, state.af), (20,1,-1,.1))
        state.update(dict(high=21, low=0, close=20))
        self.assertEqual((state.value, state.ep, state.direction, state.af), (0,21,1,.1))

    def test_vwap_hlc3_independent_weighted_zero_and_status(self):
        rows = candles([10,20,30,40])
        rows[0].update(high=15, low=8, volume=0)
        rows[1].update(high=24, low=16, volume=2)
        rows[2].update(high=36, low=27, volume=3)
        rows[3].update(volume=0)
        out = replay(rows)
        self.assertEqual(out['columns']['vwap']['value'], [None,20,133/5,133/5])
        self.assertEqual(out['formula_status']['vwap'],dict(status='ready',reason=None))
        zero = replay(rows[:1])
        self.assertEqual(zero['formula_status']['vwap']['reason'], 'zero_total_volume')
        self.assertEqual(formulas.metadata(SAR)['plot_style'], 'dots')
        self.assertIn('source-native', formulas.metadata(VWAP)['volume_basis'])

    def test_vwap_midnight_open_timestamp_and_exact_day_recovery(self):
        rows = candles([10,20,30,40], minutes=1)
        for row in rows: row['time'] += 86340; row['volume'] = 1
        out = replay(rows)
        self.assertEqual(out['times'], [86400,86460,86520,86580])
        self.assertEqual(out['columns']['vwap']['value'], [None,20,25,30])
        # 23:59 is labelled midnight but cannot seed the next session.
        self.assertEqual(replay(rows[:1])['formula_status']['vwap']['reason'], 'missing_session_start')
        del rows[1]
        out = replay(rows)
        self.assertTrue(all(v is None for v in out['columns']['vwap']['value']))
        self.assertEqual(out['formula_status']['vwap']['reason'], 'missing_session_start')

    def test_vwap_gap_unknown_invalid_volume_poison_without_restart(self):
        rows = candles([10,20,30,40,50])
        for row in rows: row['volume'] = 1
        for volume in (None, -1, True, float('nan'), float('inf')):
            changed = copy.deepcopy(rows); changed[2]['volume'] = volume
            out = replay(changed)
            self.assertEqual(out['columns']['vwap']['value'], [10,15,None,None,None])
            self.assertEqual(out['formula_status']['vwap']['reason'], 'incomplete_coverage')
        for confirmation in ('legacy_unknown','forming'):
            changed = copy.deepcopy(rows); changed[2]['confirmation'] = confirmation
            out = replay(changed)
            self.assertEqual(out['columns']['vwap']['value'], [10,15,None,None,None])
            self.assertEqual(out['columns']['sar']['value'][2:4], [None,None])
        out = replay(rows[:2]+rows[3:])
        self.assertEqual(out['columns']['vwap']['value'], [10,15,None,None,None])
        self.assertEqual(out['formula_status']['vwap']['reason'], 'incomplete_coverage')
        later = dict(rows[-1], time=86400, volume=1)
        self.assertEqual(replay(rows[:2]+rows[3:]+[later])['columns']['vwap']['value'][-1],50)

    def test_fixed_anchor_requires_boundary_and_never_midnight_recovery(self):
        item = instance('vwap', mode=1, anchor=60)
        rows = candles([10,20,30,40]); [row.update(volume=1) for row in rows]
        self.assertEqual(replay(rows,[item])['columns']['vwap']['value'], [None,20,25,30])
        self.assertEqual(replay(rows[:1],[item])['formula_status']['vwap']['reason'], 'before_anchor')
        self.assertEqual(replay(rows[2:],[item])['formula_status']['vwap']['reason'], 'missing_session_start')
        changed = rows[:2]+rows[3:]+[dict(rows[-1],time=86400)]
        out = replay(changed,[item])
        self.assertEqual(out['formula_status']['vwap']['reason'], 'incomplete_coverage')
        self.assertIsNone(out['columns']['vwap']['value'][-1])

    def test_validation_boundaries_no_rounding_and_no_coercion(self):
        self.assertEqual(len(FIELDS),33)
        for params in ({},dict(step=.02),dict(step=.02,max=.2,extra=1),dict(step=True,max=.2),dict(step=0,max=.2),dict(step=.3,max=.2),dict(step=.1,max=1.1),dict(step=float('nan'),max=.2),dict(step=.02,max=float('inf')),dict(step=10**1000,max=.2)):
            with self.subTest(params=params), self.assertRaises(ValueError): validate_instances([instance('sar',**params)])
        for params in ({},dict(mode=0),dict(mode=True,anchor=0),dict(mode=1,anchor=True),dict(mode=1.,anchor=0),dict(mode=2,anchor=0),dict(mode=0,anchor=60),dict(mode=1,anchor=-1),dict(mode=1,anchor=253402300800),dict(mode=1,anchor=1.5),dict(mode=1,anchor=float('inf')),dict(mode=1,anchor=0,extra=1)):
            with self.subTest(params=params), self.assertRaises(ValueError): validate_instances([instance('vwap',**params)])
        for step, maximum in ((.02,.2),(1,1),(1e-12,.2)):
            validate_instances([instance('sar',step=step,max=maximum)])
        validate_instances([instance('vwap',mode=1,anchor=253402300799)])
        for minutes in (1,5,15,60,240,1440):
            with self.assertRaisesRegex(ValueError,'anchor.*align'):
                replay(candles([1]),[instance('vwap',mode=1,anchor=1)],minutes)
            aligned = (253402300799//(minutes*60))*(minutes*60)
            formulas.validate_timeframe([instance('vwap',mode=1,anchor=aligned)],minutes)

    def test_causal_prefix_conflicts_and_cancel(self):
        rows = candles([10,12,11,14,10,13]*3)
        base = replay(rows)
        changed = copy.deepcopy(rows); changed[-1].update(high=120,low=50,close=100,volume=100)
        future = replay(changed)
        for kind in ('sar','vwap'):
            self.assertEqual(base['columns'][kind]['value'][:-1],future['columns'][kind]['value'][:-1])
        changed[2]['confirmation']='conflict'
        with self.assertRaisesRegex(ValueError,'conflict'): replay(changed)
        cancel=threading.Event();cancel.set()
        with self.assertRaises(InterruptedError): calculate(rows,[SAR,VWAP],1,0,1020,cancel)


class BoundaryCacheTests(unittest.TestCase):
    setUp = infrastructure.DisplayCacheTests.setUp
    tearDown = infrastructure.DisplayCacheTests.tearDown
    seed = infrastructure.DisplayCacheTests.seed
    read = infrastructure.DisplayCacheTests.read

    def test_origin_reopen_explicit_reanchor_ha_and_source_isolation(self):
        rows = candles([10,20,30,40]); [row.update(volume=1) for row in rows]
        self.seed(rows[1:])
        self.settings = self.display.save('spot','BTCUSDT',[SAR,VWAP],0)
        first = self.read(60,180)
        self.assertEqual(first['formula_status']['vwap']['reason'],'missing_session_start')
        self.seed(rows[:1]); earlier = self.read(0,180)
        self.assertEqual(earlier['columns']['sar']['value'][:2],[None,None])
        self.assertEqual(earlier['columns']['vwap']['value'],[None]*4)
        self.display.close(); self.display=DisplayIndicators(self.chart)
        self.assertEqual(self.read(0,180)['columns'],earlier['columns'])
        restored=self.read(0,180,reanchor=True)
        self.assertEqual(restored['columns']['vwap']['value'],[10,15,20,25])
        self.assertEqual(self.read(0,180,price_style='heikin_ashi')['columns'],restored['columns'])
        self.assertEqual(self.display.settings('spot','BTCUSDT',source='okx')['revision'],0)
        self.assertEqual(restored['formula_metadata']['sar']['unit'],'price')
        self.settings=self.display.save('spot','BTCUSDT',[instance('vwap',mode=1,anchor=1)],self.settings['revision'])
        with self.assertRaisesRegex(ValueError,'anchor.*align'): self.read(0,180)

    def test_fixed_anchor_origin_cannot_silently_prepend_and_forming_does_not_commit(self):
        rows = candles([10,20,30,40]); [row.update(volume=1) for row in rows]
        self.seed(rows[1:])
        self.settings = self.display.save('spot','BTCUSDT',[instance('vwap',mode=1,anchor=0)],0)
        self.assertEqual(self.read(60,180)['formula_status']['vwap']['reason'],'missing_session_start')
        self.seed(rows[:1])
        self.assertEqual(self.read(0,180)['columns']['vwap']['value'],[None]*4)
        self.assertEqual(self.read(0,180,reanchor=True)['columns']['vwap']['value'],[10,15,20,25])
        state = formulas.FormulaState(VWAP)
        state.observe(rows[0],60,True)
        state.observe(rows[1],60,False)
        self.assertEqual((state.weighted,state.volume),(10,1))
        state.observe(rows[2],60,True)
        self.assertEqual((state.weighted,state.volume),(10,1))
        self.assertEqual(state.status()['reason'],'incomplete_coverage')
