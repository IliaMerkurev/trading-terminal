"""Independent small offline expectations for frozen alert semantics."""
import copy
import itertools
import math
import threading
import unittest
from unittest.mock import patch

from terminal import indicator_alerts as alerts
from terminal import vumanchu_indicators as vmc
from terminal.display_indicators import CONTRACT


def settings(kind='sma', params=None, ident='signal'):
    params = params if params is not None else {'period': 2}
    return dict(version=1, revision=3, origins={'1': dict(time=0, generation=1, contract=CONTRACT)},
        instances=[dict(id=ident, type=kind, params=params, color='#42cda8', visible=True)])


def condition(predicate='cross_above', *, unit='price', level=10):
    return dict(predicate=predicate, left=dict(kind='series', instance_id='signal', port='value'),
                right=dict(kind='level', unit=unit, value=level))


def definition(predicate='cross_above', *, config=None, conditions=None, combine='ALL'):
    return alerts.freeze_rule(config or settings(), 'bybit', 'spot', 'BTCUSDT', 1,
                              conditions or [condition(predicate)], combine)


def candles(values):
    return [dict(time=i*60, open=value, high=value+1, low=value-1, close=value,
                 volume=2, confirmation='synthetic_closed') for i, value in enumerate(values)]


class FrozenDefinitionTests(unittest.TestCase):
    def test_capture_is_independent_and_strict_roundtrip(self):
        config = settings(); frozen = definition(config=config)
        config['instances'][0]['params']['period'] = 9
        self.assertEqual(frozen['instances'][0]['params'], {'period': 2})
        self.assertEqual(frozen, alerts.validate_definition(alerts.decode(alerts.encode(frozen))))
        self.assertEqual(frozen['context'], dict(source='bybit', market='spot', symbol='BTCUSDT', minutes=1))
        self.assertEqual(frozen['origin']['time'], 0)
        self.assertNotIn('visible', frozen['instances'][0])

    def test_unknown_keys_ports_versions_contracts_and_nonfinite_rejected(self):
        valid = definition()
        variants = []
        for key, value in [('version', 2), ('version', True), ('contract', 'future'), ('event_contract', 'future')]:
            item = copy.deepcopy(valid); item[key] = value; variants.append(item)
        item = copy.deepcopy(valid); item['python'] = 'not executable'; variants.append(item)
        item = copy.deepcopy(valid); item['instances'][0]['contract']['display'] = 'future'; variants.append(item)
        item = copy.deepcopy(valid); item['conditions'][0]['left']['port'] = 'made_up'; variants.append(item)
        item = copy.deepcopy(valid); item['conditions'][0]['right']['value'] = math.nan; variants.append(item)
        item = copy.deepcopy(valid); item['origin']['time'] = 1; variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError):
                alerts.validate_definition(item)
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError): alerts.decode(raw)
        with self.assertRaises(ValueError): alerts.encode({1: 'non-string key'})
        with self.assertRaises(ValueError): alerts.encode({'tuple': (1, 2)})

    def test_huge_numeric_inputs_fail_explicitly_before_formula_validation(self):
        huge = 10**400
        config = settings('bb', {'period': 2, 'deviations': huge})
        with self.assertRaises(ValueError): definition(config=config)
        with self.assertRaises(ValueError): definition(conditions=[condition(level=huge)])
        rows = candles([10, 11]); rows[1]['close'] = huge
        with self.assertRaises(ValueError): alerts.replay(definition(), rows)
        with self.assertRaises(ValueError): alerts.decode('{"number":' + str(huge) + '}')

    def test_missing_origin_and_complexity_and_work_contracts(self):
        config = settings(); config['origins'] = {}
        with self.assertRaisesRegex(ValueError, 'origin'): definition(config=config)
        for conditions in ([], [condition()]*17):
            with self.assertRaises(ValueError):
                alerts.freeze_rule(settings(), 'bybit', 'spot', 'BTCUSDT', 1, conditions)
        self.assertEqual(len(definition(conditions=[condition()]*16)['conditions']), 16)
        item = definition(); item['unused'] = 'x' * alerts.MAX_DEFINITION_BYTES
        with self.assertRaisesRegex(ValueError, 'budget'): alerts.validate_definition(item)

    def test_semantic_units_prevent_incompatible_series_and_levels(self):
        for kind, unit in [('rsi', 'price'), ('atr', 'price'), ('momentum', 'price'), ('roc', 'bounded_0_100')]:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'compatible'):
                definition(config=settings(kind), conditions=[condition(unit=unit)])
        self.assertEqual(alerts.port_units('rsi')['value'], alerts.port_units('stochastic')['k'])
        self.assertNotEqual(alerts.port_units('rsi')['value'], alerts.port_units('williamsr')['value'])
        self.assertNotEqual(alerts.port_units('rsi')['value'], alerts.port_units('roc')['value'])
        self.assertNotIn('chikou', alerts.port_units('ichimoku'))

    def test_hidden_removed_or_recolored_original_does_not_change_frozen_rule(self):
        config = settings(); frozen = definition(config=config)
        config['instances'][0].update(visible=False, color='#ffffff')
        self.assertEqual(alerts.changed_dependencies(frozen, config), [])
        config['instances'][0]['params']['period'] = 3
        self.assertEqual(alerts.changed_dependencies(frozen, config), ['signal'])
        config['instances'] = []
        self.assertEqual(alerts.changed_dependencies(frozen, config), [])
        self.assertEqual(alerts.replay(frozen, candles([8, 12, 10]))['events'][0]['confirmed_at'], 180)

    def test_active_set_is_byte_budget_not_rule_count(self):
        frozen = definition()
        self.assertEqual(len(alerts.validate_active_set([frozen]*129)), 129)
        count = alerts.MAX_ACTIVE_BYTES // len(alerts.encode(frozen)) + 1
        with self.assertRaisesRegex(ValueError, 'budget'): alerts.validate_active_set([frozen]*count)


class TruthTests(unittest.TestCase):
    def test_full_kleene_two_condition_truth_table(self):
        expected_all = [True, False, None, False, False, False, None, False, None]
        expected_any = [True, True, True, True, False, None, True, None, None]
        pairs = list(itertools.product((True, False, None), repeat=2))
        self.assertEqual([alerts.combine_truth(pair, 'ALL') for pair in pairs], expected_all)
        self.assertEqual([alerts.combine_truth(pair, 'ANY') for pair in pairs], expected_any)

    def test_known_false_true_only_state_edges(self):
        prior = state_prior = None; hits = []
        for index, truth in enumerate([False, True, True, None, True, False, True]):
            row = alerts.transition([dict(kind='state', truth=truth)], 'ALL', prior, state_prior)
            if row['hit']: hits.append(index)
            prior, state_prior = row['truth'], row['state_truth']
        self.assertEqual(hits, [1, 6])
        self.assertFalse(alerts.transition([dict(kind='state', truth=True)], 'ALL')['hit'])

    def test_mixed_same_close_pulses_and_state_edges(self):
        pulse = lambda value: dict(kind='impulse', truth=value)
        state = lambda value: dict(kind='state', truth=value)
        self.assertTrue(alerts.transition([pulse(True), state(True)], 'ALL')['hit'])
        self.assertFalse(alerts.transition([pulse(False), state(True)], 'ALL', False, False)['hit'])
        self.assertFalse(alerts.transition([pulse(True), state(None)], 'ALL')['hit'])
        self.assertTrue(alerts.transition([pulse(True), state(None)], 'ANY')['hit'])
        self.assertTrue(alerts.transition([pulse(False), state(True)], 'ANY', True, False)['hit'])
        self.assertFalse(alerts.transition([pulse(False), state(True)], 'ANY', None, None)['hit'])
        self.assertTrue(alerts.transition([pulse(True), state(True)], 'ANY', True, True)['hit'])
        self.assertFalse(alerts.transition([pulse(False), state(True)], 'ANY', True, True)['hit'])
        self.assertFalse(alerts.transition([pulse(True), pulse(False)], 'ALL')['hit'])


class ReplayTests(unittest.TestCase):
    def test_sma_equality_cross_close_clock_and_exact_evidence(self):
        result = alerts.replay(definition(), candles([8, 12, 10, 14]))
        self.assertEqual([row['truth'] for row in result['rows']], [None, None, True, False])
        self.assertEqual(len(result['events']), 1)
        hit = result['events'][0]
        self.assertEqual((hit['raw_open_time'], hit['confirmed_at']), (120, 180))
        self.assertEqual({key: hit['conditions'][0][key] for key in ('left', 'right', 'previous_left', 'previous_right')},
                         dict(left=11, right=10, previous_left=10, previous_right=10))
        self.assertNotIn('observed_at', hit)

    def test_cross_below_previous_equality_but_current_equality_never_hits(self):
        config = settings(params={'period': 1})
        result = alerts.replay(definition('cross_below', config=config), candles([11, 10, 9, 10, 9]))
        self.assertEqual([row['confirmed_at'] for row in result['events']], [180, 300])
        self.assertEqual([row['truth'] for row in result['rows']], [None, False, True, False, True])

    def test_state_warmup_initial_true_and_persistent_true_do_not_hit(self):
        result = alerts.replay(definition('above'), candles([12, 12, 12, 6, 6, 16, 18]))
        self.assertEqual([row['truth'] for row in result['rows']], [None, True, True, False, False, True, True])
        self.assertEqual([row['confirmed_at'] for row in result['events']], [360])

    def test_full_origin_confirmed_contiguous_tape_is_mandatory(self):
        for change in ('origin', 'gap', 'forming', 'conflict', 'nan'):
            rows = candles([8, 12, 10, 14])
            if change == 'origin': rows = rows[1:]
            if change == 'gap': rows.pop(1)
            if change == 'forming': rows[1]['confirmation'] = 'forming'
            if change == 'conflict': rows[1]['conflict'] = True
            if change == 'nan': rows[1]['close'] = math.nan
            with self.subTest(change=change), self.assertRaises(ValueError): alerts.replay(definition(), rows)

    def test_missing_volume_is_unknown_and_does_not_invent_an_edge(self):
        config = settings(kind='volume', params={})
        rule = definition('above', config=config, conditions=[condition('above', unit='volume_native', level=1)])
        rows = candles([10]*5)
        for row, volume in zip(rows, [0, None, 2, 0, 2]): row['volume'] = volume
        result = alerts.replay(rule, rows)
        self.assertEqual([row['truth'] for row in result['rows']], [False, None, True, False, True])
        self.assertEqual([row['confirmed_at'] for row in result['events']], [300])

    def test_future_perturbation_and_single_existing_formula_pass(self):
        rule = definition(); rows = candles([8, 12, 10, 14, 8, 2, 20, 25])
        original = alerts.display.calculate
        with patch.object(alerts.display, 'calculate', wraps=original) as calculate:
            whole = alerts.replay(rule, rows)
            self.assertEqual(calculate.call_count, 1)
        future = copy.deepcopy(rows)
        for row in future[4:]:
            for field in ('open', 'high', 'low', 'close'): row[field] += 1000
        self.assertEqual(whole['rows'][:4], alerts.replay(rule, future)['rows'][:4])
        self.assertEqual(whole['rows'][:4], alerts.replay(rule, rows[:4])['rows'])

    def test_vmc_confirmed_divergence_keeps_later_availability_and_pivot_clock(self):
        # A smooth synthetic rising-baseline wave yields regular bullish WT
        # divergences; the independent oracle here is the two-bar clock delay.
        rows = candles([100+10*math.sin(i*.4)+i*.01 for i in range(100)])
        config = settings('vmc_cipher_b', dict(vmc.DEFAULTS['vmc_cipher_b'], wt_div_bottom=-10, wt_div_top=10))
        conditions = [dict(predicate='divergence', instance_id='signal', event_kind='regular_bullish', oscillator='wt')]
        rule = definition(config=config, conditions=conditions)
        whole = alerts.replay(rule, rows)
        self.assertTrue(whole['events'])
        for hit in whole['events']:
            for event in hit['conditions'][0]['events']:
                self.assertEqual(event['confirmed_at'], hit['confirmed_at'])
                self.assertEqual(event['confirmed_at'] - event['pivot_time'], 120)
                self.assertLess(event['previous_pivot_time'], event['pivot_time'])
                prefix = alerts.replay(rule, rows[:hit['confirmed_at']//60-1])
                self.assertNotIn(hit, prefix['events'])

    def test_cancel_and_evidence_resource_budget_are_explicit(self):
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(InterruptedError): alerts.replay(definition(), candles([8, 12]), cancel)
        with self.assertRaisesRegex(ValueError, '256 MiB'):
            alerts.replay(definition(conditions=[condition()]*16), candles([10]*5000))
