# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the Mozilla Public License, v. 2.0.
# https://mozilla.org/MPL/2.0/
"""Independent small synthetic fixtures; no market fetch or runtime parity claim."""
import copy
import math
import unittest
from fractions import Fraction
from terminal.vumanchu_indicators import (
    DEFAULTS, VumanchuState, calculate_vumanchu, _Average, _RSI,
    _Divergences, _cross, ports, validate_params,
)


def bars(closes):
    return [dict(time=i*60, open=c-0.25, high=c+1, low=c-1, close=c,
                 confirmation='synthetic_closed') for i, c in enumerate(closes)]


def state(kind, **params):
    return VumanchuState(dict(type=kind, params=dict(DEFAULTS[kind], **params)))


class PinePrimitivesTests(unittest.TestCase):
    def test_first_non_na_ema_and_sma_skip_na(self):
        ema = _Average(3)
        self.assertEqual([ema.update(x) for x in [None, 2, 4, None, 8]], [None, 2, 3, 3, 5.5])
        sma = _Average(3, 'sma')
        self.assertEqual([sma.update(x) for x in [None, 2, None, 4, 6, None, 8]],
                         [None, None, None, None, 4, 4, 6])

    def test_wilder_seed_and_exact_known_rsi(self):
        rsi = _RSI(3)
        values = [rsi.update(v) for v in [10, 12, 11, 14, 13]]
        self.assertEqual(values[:3], [None]*3)
        self.assertAlmostEqual(values[3], 100*5/6)
        self.assertAlmostEqual(values[4], 100*10/15)
        flat = _RSI(2)
        self.assertEqual([flat.update(5) for _ in range(9)], [None]*9)
        up = _RSI(2)
        self.assertEqual([up.update(x) for x in [1, 2, 3]], [None, None, 100])
        down = _RSI(2)
        self.assertEqual([down.update(x) for x in [3, 2, 1]], [None, None, 0])

    def test_rsi_one_sided_endpoint_is_exact_no_phantom_stoch_range(self):
        rows = bars([100 + i * 0.1 for i in range(100)])
        out = calculate_vumanchu(rows, 'vmc_cipher_b',
            dict(stoch_rsi_period=4, stoch_period=4, stoch_k=2, stoch_d=2))['series']
        self.assertEqual(out['stoch_k'], [None]*100)
        self.assertEqual(out['stoch_d'], [None]*100)

    def test_strict_current_cross_and_previous_equality(self):
        self.assertEqual(_cross(3, 2, 2, 2), 1)
        self.assertEqual(_cross(1, 2, 2, 2), -1)
        self.assertEqual(_cross(2, 2, 1, 2), 0)
        self.assertEqual(_cross(2, 2, 3, 2), 0)
        self.assertEqual(_cross(3, 2, None, 2), 0)


class FormulaTests(unittest.TestCase):
    def test_changed_wt_parameters_rational_reference(self):
        # Independent Fraction arithmetic: channel=2 average=2 signal=2.
        closes = [10, 12, 11, 14, 10, 9, 13]
        rows = bars(closes)
        out = calculate_vumanchu(rows, 'vmc_cipher_b', dict(channel=2, average=2, signal=2))['series']
        esa = Fraction(closes[0]); dev = Fraction(0); wt = None; expected = []
        for close in closes:
            esa = Fraction(2, 3)*close + Fraction(1, 3)*esa
            dev = Fraction(2, 3)*abs(close-esa) + Fraction(1, 3)*dev
            if dev:
                ci = (close-esa)/(Fraction(15, 1000)*dev)
                wt = ci if wt is None else Fraction(2, 3)*ci + Fraction(1, 3)*wt
            expected.append(None if wt is None else float(wt))
        for actual, target in zip(out['wt1'], expected):
            if target is None:
                self.assertIsNone(actual)
            else:
                self.assertAlmostEqual(actual, target, places=10)
        self.assertIsNone(out['wt2'][1])
        for i in range(2, len(closes)):
            self.assertAlmostEqual(out['wt2'][i], (expected[i]+expected[i-1])/2, places=10)

    def test_a_b_lengths_flow_and_ribbon_reference(self):
        rows = bars([100+math.sin(i/5)*8+i/25 for i in range(100)])
        a = state('vmc_cipher_a'); b = state('vmc_cipher_b')
        for row in rows:
            av = a.update(row); bv = b.update(row)
        self.assertNotAlmostEqual(a.prev_values['wt1'], bv['wt1'])
        self.assertAlmostEqual(a.prev_values['flow'] - bv['flow'], 2.5)
        self.assertAlmostEqual(a.prev_values['flow'], 18.75)
        ema = rows[0]['close']
        for row in rows[1:]:
            ema = (row['close']+2*ema)/3
        self.assertAlmostEqual(av['ema1'], ema)
        self.assertEqual(set(av), set(ports('vmc_cipher_a')))

    def test_flat_and_zero_range_have_no_invented_wt_or_flow(self):
        rows = [dict(time=i*60, open=10, high=10, low=10, close=10,
                     confirmation='synthetic_closed') for i in range(90)]
        result = calculate_vumanchu(rows, 'vmc_cipher_b')
        for key in ports('vmc_cipher_b'):
            self.assertEqual(result['series'][key], [None]*90)
        self.assertEqual(result['events'], [])

    def test_zero_range_flow_skips_observation_not_zero_fill(self):
        rows = bars([10, 11, 12, 13])
        rows[1].update(open=11, high=11, low=11)
        out = calculate_vumanchu(rows, 'vmc_cipher_b', dict(flow_period=2))['series']['flow']
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 16.25)
        self.assertAlmostEqual(out[3], 16.25)

    def test_log_rejected_before_state_mutation_and_disable_supported(self):
        s = state('vmc_cipher_b')
        before = copy.deepcopy(s.__dict__)
        with self.assertRaisesRegex(ValueError, 'positive close'):
            s.update(bars([0])[0])
        self.assertEqual(s.index, before['index'])
        calculate_vumanchu(bars([-1, 0, 1]), 'vmc_cipher_b', dict(stoch_log=False))

    def test_stoch_average_only_changes_k(self):
        rows = bars([100+math.sin(i/3)*5 for i in range(80)])
        raw = calculate_vumanchu(rows, 'vmc_cipher_b')['series']
        avg = calculate_vumanchu(rows, 'vmc_cipher_b', dict(stoch_average=True))['series']
        self.assertEqual(raw['stoch_d'], avg['stoch_d'])
        for k, d, averaged in zip(raw['stoch_k'], raw['stoch_d'], avg['stoch_k']):
            self.assertEqual(averaged, (k+d)/2 if k is not None and d is not None else None)

    def test_a_original_marker_conditions_and_strict_yellow_edges(self):
        class Fixed:
            def __init__(self, value):
                self.value = value
            def update(self, _):
                return self.value
        s = state('vmc_cipher_a')
        s.index = 1
        s.emas = [Fixed(v) for v in [8, 9, 10, 11, 12, 13, 14, 15]]
        s.prev_values = dict(ema1=10, ema2=9, ema3=10, ema8=8)
        row = bars([20, 21])[1]
        s.previous = bars([20])[0]
        s._cipher_a(row, dict(wt2=-60, rsi=20, flow=-6), -1)
        self.assertEqual({e['kind'] for e in s.events},
                         {'short_ema', 'red_cross', 'red_diamond', 'blood_diamond', 'yellow_cross'})
        for wave, rsi, flow in [(-80, 20, -6), (45, 20, -6), (-60, 15, -6),
                               (-60, 30, -6), (-60, 20, -5)]:
            s.events = []
            s._cipher_a(row, dict(wt2=wave, rsi=rsi, flow=flow), -1)
            self.assertFalse(any(e['kind'] == 'yellow_cross' for e in s.events))
        s.emas = [Fixed(v) for v in [12, 11, 10, 12, 13, 14, 15, 9]]
        s.prev_values = dict(ema1=10, ema2=9, ema3=10, ema8=10)
        s.events = []
        s._cipher_a(row, dict(wt2=0, rsi=50, flow=0), 0)
        self.assertEqual({e['kind'] for e in s.events}, {'long_ema', 'blue_triangle', 'bull_candle'})

    def test_changed_stoch_parameters_independent_wilder_reference(self):
        closes = [10, 12, 11, 14, 12, 15, 11, 16, 13]
        out = calculate_vumanchu(bars(closes), 'vmc_cipher_b',
            dict(stoch_log=False, stoch_rsi_period=2, stoch_period=3, stoch_k=1, stoch_d=1))['series']
        rsis = [None, None]
        up = Fraction(2, 2); down = Fraction(1, 2)
        rsis.append(100*up/(up+down))
        for previous, current in zip(closes[2:-1], closes[3:]):
            up = (up+max(current-previous, 0))/2
            down = (down+max(previous-current, 0))/2
            rsis.append(100*up/(up+down))
        expected = []
        last = None
        for i, rsi in enumerate(rsis):
            window = [v for v in rsis[max(0, i-2):i+1] if v is not None]
            if rsi is not None and max(window) != min(window):
                last = float(100*(rsi-min(window))/(max(window)-min(window)))
            expected.append(last)
        for actual, target in zip(out['stoch_k'], expected):
            if target is None:
                self.assertIsNone(actual)
            else:
                self.assertAlmostEqual(actual, target, places=10)

    def test_swing_hand_calculated_reversals_and_first_entry_suppression(self):
        result = calculate_vumanchu(bars([10, 12, 14, 10, 8, 12]), 'vmc_swing',
                                    dict(period=1, multiplier=0.5))
        self.assertEqual(result['series']['filter'], [10, 11, 13, 12, 9, 10])
        self.assertEqual(result['series']['upper'], [None, 12, 14, 14, 10, 12])
        self.assertEqual(result['series']['lower'], [None, 10, 12, 10, 8, 8])
        self.assertEqual([(e['kind'], e['confirmed_at']) for e in result['events']],
                         [('swing_short', 180), ('swing_long', 300)])

    def test_gap_and_unconfirmed_reset_no_synthetic_values(self):
        rows = bars([10, 12, 14, 16, 18, 20])
        rows[3]['time'] += 60
        rows[4]['time'] += 60
        rows[5]['time'] += 60
        out = calculate_vumanchu(rows, 'vmc_cipher_b', interval_seconds=60)
        self.assertIsNone(out['series']['wt1'][3])
        rows[2]['confirmation'] = 'forming'
        out = calculate_vumanchu(rows, 'vmc_cipher_a', interval_seconds=60)
        self.assertIsNone(out['series']['ema1'][2])
        self.assertEqual(out['series']['ema1'][3], 16)
        self.assertFalse(any(e['confirmed_at'] == rows[2]['time'] for e in out['events']))

    def test_bad_parameters_and_unknown_fields_fail(self):
        for changes in [dict(channel=True), dict(stoch_log=1), dict(source='volume'),
                        dict(channel=0), dict(flow_offset=float('nan'))]:
            with self.assertRaises(ValueError):
                validate_params('vmc_cipher_b', dict(DEFAULTS['vmc_cipher_b'], **changes))
        with self.assertRaises(ValueError):
            validate_params('vmc_swing', {'period': 20})


class DivergenceTests(unittest.TestCase):
    def replay(self, oscillator, highs=None, lows=None, top=None, bottom=None):
        tracker = _Divergences(top, bottom)
        highs = highs or [100]*len(oscillator)
        lows = lows or [90]*len(oscillator)
        outputs = []
        for i, value in enumerate(oscillator):
            outputs.append(tracker.update(value, dict(high=highs[i], low=lows[i], time=i*60), i, 20))
        return outputs

    def test_regular_and_hidden_all_directions_two_bar_latency(self):
        highs = [100]*9; highs[2] = 101; highs[6] = 102
        output = self.replay([0, 2, 6, 2, 0, 1, 5, 1, 0], highs=highs)
        self.assertTrue(all(not x['events'] for x in output[:8]))
        e = output[8]['events'][0]
        self.assertEqual((e['kind'], e['pivot_time'], e['confirmed_at'], e['previous_pivot_time']),
                         ('regular_bearish', 360, 480, 120))
        highs[6] = 100
        self.assertEqual(self.replay([0, 2, 5, 2, 0, 1, 6, 1, 0], highs=highs)[8]['events'][0]['kind'], 'hidden_bearish')
        lows = [90]*9; lows[2] = 89; lows[6] = 88
        self.assertEqual(self.replay([0, -2, -6, -2, 0, -1, -5, -1, 0], lows=lows)[8]['events'][0]['kind'], 'regular_bullish')
        lows[6] = 90
        self.assertEqual(self.replay([0, -2, -5, -2, 0, -1, -6, -1, 0], lows=lows)[8]['events'][0]['kind'], 'hidden_bullish')

    def test_equal_plateaus_and_zero_fractals_are_not_events(self):
        output = self.replay([0, 1, 4, 4, 0, 1, 3, 1, 0], highs=list(range(9)))
        self.assertEqual([e for o in output for e in o['events']], [])
        output = self.replay([-3, -2, 0, -2, -3, -2, -1, -2, -3], highs=list(range(9)))
        self.assertEqual([e for o in output for e in o['events']], [])

    def test_threshold_filter_applies_before_history_and_close_pivots(self):
        osc = [0, 1, 8, 1, 0, 5, 0, 1, 7, 1, 0]
        highs = [100]*11; highs[2]=101; highs[5]=200; highs[8]=102
        out = self.replay(osc, highs=highs, top=6)
        e = out[-1]['events'][0]
        self.assertEqual(e['previous_pivot_time'], 120)
        self.assertEqual(e['kind'], 'regular_bearish')
        # Pivots only three bars apart: use historical valuewhen series at t-2.
        osc = [0, 1, 6, 1, 0, 5, 0, 1]
        highs = [100]*8; highs[2]=101; highs[5]=102
        e = self.replay(osc, highs=highs)[7]['events'][0]
        self.assertEqual((e['pivot_time'], e['previous_pivot_time']), (300, 120))

    def test_gold_uses_previous_wt_rsi_and_current_wave_not_pivot_wave(self):
        # Drive the signal combiner with independently specified oscillator tape.
        s = state('vmc_cipher_b', wt_div_bottom=-40, wt_secondary=False)
        waves = [0, -20, -85, -20, 0, -20, -70, -20, 0]
        rows = bars([100]*9); rows[2]['low']=90; rows[6]['low']=89
        for i, (row, wave) in enumerate(zip(rows, waves)):
            s.index = i
            s.events = []
            s._cipher_b(row, dict(wt1=wave, wt2=wave, flow=0, rsi=20), 0)
            if i < 8:
                self.assertFalse(any(e['kind']=='gold_buy_dot' for e in s.events))
        gold = [e for e in s.events if e['kind']=='gold_buy_dot']
        self.assertEqual(len(gold), 1)
        self.assertEqual((gold[0]['pivot_time'], gold[0]['confirmed_at'], gold[0]['value']), (360, 480, 0))


class CausalityTests(unittest.TestCase):
    def test_every_prefix_and_future_perturbation(self):
        rows = bars([100+math.sin(i/3)*10+math.sin(i/11)*4 for i in range(100)])
        for kind in DEFAULTS:
            full = calculate_vumanchu(rows, kind)
            for n in range(1, len(rows)+1):
                prefix = calculate_vumanchu(rows[:n], kind)
                self.assertEqual(prefix['series'], {k:v[:n] for k,v in full['series'].items()})
                self.assertEqual(prefix['events'], [e for e in full['events'] if e['confirmed_at'] <= rows[n-1]['time']])
            changed = rows[:60] + bars([200+i for i in range(40)])
            for i, row in enumerate(changed[60:], 60):
                row['time'] = i*60
            future = calculate_vumanchu(changed, kind)
            self.assertEqual({k:v[:60] for k,v in full['series'].items()}, {k:v[:60] for k,v in future['series'].items()})

    def test_snapshot_restore_and_bounded_histories(self):
        rows = bars([100+math.sin(i/3)*10 for i in range(120)])
        for kind in DEFAULTS:
            live = state(kind)
            for row in rows[:70]:
                live.update(row)
            restored = copy.deepcopy(live)
            for row in rows[70:]:
                self.assertEqual(live.update(row), restored.update(row))
                self.assertEqual(live.events, restored.events)
            if kind == 'vmc_cipher_b':
                for tracker in live.divs.values():
                    self.assertLessEqual(len(tracker.window), 5)
                    self.assertLessEqual(len(tracker.history), 2)


if __name__ == '__main__':
    unittest.main()
