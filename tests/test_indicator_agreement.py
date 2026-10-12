"""Independent synthetic expectations; none are recorded formula outputs."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from terminal.indicator_agreement import (MANIFEST_HASH, evaluate_agreement, manifest,
    normalize_params, prepare_agreement, threshold_evidence, variant_key)

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/indicator_agreement_v1.json').read_text())
CASES = {case['name']: case for case in FIXTURES['cases']}
DIRECTIONS = ('up', 'down', 'neutral')


def single(kind='sma', params=None, ports=None, raw=None):
    candles = raw if raw is not None else [dict(time=i*60, open=100+i, close=100+i, high=101+i, low=99+i, confirmation='synthetic_closed') for i in range(5)]
    return dict(instances=[dict(id='x', type=kind, params={'period': 2} if params is None else params, visible=True)],
                candles=candles, display=dict(times=[(i+1)*60 for i in range(5)],
                columns={'x': {key: [value]*5 for key, value in (ports or {'value': 100}).items()}}), interval_seconds=60, close_time=300)


def status(snapshot):
    return evaluate_agreement(snapshot)['members'][0]['status']


def assert_case(test, case):
    result, expected = evaluate_agreement(case['input']), case['expected']
    if expected.get('overall') is None:
        test.assertIsNone(result['overall'])
    else:
        test.assertEqual(result['overall']['exact'], {key: list(map(str, value)) for key, value in expected['overall'].items()})
        test.assertEqual(sum(result['overall']['percentages'].values()), 100)
    if 'trend' in expected:
        test.assertEqual(next(row for row in result['groups'] if row['group'] == 'trend')['distribution']['exact'],
                         {key: list(map(str, value)) for key, value in expected['trend'].items()})
    for key in ('group_conflict',):
        if key in expected:
            test.assertEqual(result[key], expected[key])
    for expected_key, result_key in [('fully_available_types', 'fully_covered_types'), ('total_supported_types', 'total_types'), ('available_variants', 'available_variants'), ('total_variants', 'total_variants')]:
        if expected_key in expected:
            test.assertEqual(result['coverage'][result_key], expected[expected_key])
    if 'percentages' in expected:
        test.assertEqual(result['overall']['percentages'], expected['percentages'])
    members = {row['id']: row for row in result['members']}
    for ident, direction in expected.get('member_direction', {}).items():
        test.assertEqual(members[ident]['status'], direction)
    for ident in expected.get('member_unavailable', []):
        test.assertEqual(members[ident]['status'], 'unavailable')
    # Every emitted value is ordinary strict JSON, with exact integers as strings.
    json.dumps(result, allow_nan=False)


class SharedAgreementVectors(unittest.TestCase):
    pass


for index, case in enumerate(FIXTURES['cases']):
    def run(self, case=case):
        assert_case(self, case)
    setattr(SharedAgreementVectors, f'test_{index:02d}_{case["name"].replace(".", "_").replace("-", "minus")}', run)
for index, case in enumerate(FIXTURES['threshold_cases']):
    def run(self, case=case):
        result = evaluate_agreement(CASES[case['result_case']]['input'])
        self.assertIs(threshold_evidence(result, case['direction'], case['threshold'], case['required_groups'])['truth'], case['expected'])
    setattr(SharedAgreementVectors, f'test_threshold_{index}_{case["name"]}', run)


class AgreementCoreTests(unittest.TestCase):
    def test_manifest_hash_and_catalog(self):
        self.assertEqual(MANIFEST_HASH, '74cc8337a2e60f56719fc584decb79427609be58450c582d3c72f512355651ff')
        raw = json.dumps(manifest(), sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), MANIFEST_HASH)
        self.assertEqual(len(manifest()['rules']), 33)
        changed = manifest(); changed['rules']['sma']['group'] = 'volume'
        self.assertEqual(manifest()['rules']['sma']['group'], 'trend')

    def test_all_price_comparison_ports_and_equality(self):
        parameters = {kind: {'period': 2} for kind in ['sma','ema','wma','rma','vwma','hma','donchian']}
        parameters.update(vwap={'mode': 0, 'anchor': 0}, sar={'step': .02, 'max': .2}, bb={'period': 2, 'deviations': 2}, keltner={'period': 2, 'atr_period': 2, 'multiplier': 2})
        for kind, params in parameters.items():
            port = 'middle' if kind in ('bb', 'donchian', 'keltner') else 'value'
            for value, expected in [(103, 'up'), (104, 'neutral'), (105, 'down'), (None, 'unavailable'), (float('nan'), 'unavailable'), (float('inf'), 'unavailable')]:
                with self.subTest(kind=kind, value=value):
                    self.assertEqual(status(single(kind, params, {port: value})), expected)

    def test_supertrend_dmi_and_sign_rules(self):
        for value, expected in [(1, 'up'), (-1, 'down'), (0, 'unavailable'), (2, 'unavailable'), (None, 'unavailable')]:
            self.assertEqual(status(single('supertrend', {'period': 2, 'multiplier': 2}, {'direction': value})), expected)
        for adx, plus, minus, expected in [(19.999, None, None, 'neutral'), (20, 3, 2, 'up'), (20, 2, 2, 'neutral'), (20.001, 1, 2, 'down'), (20, None, 2, 'unavailable')]:
            self.assertEqual(status(single('dmi', {'period': 2, 'adx_period': 2}, {'adx': adx, 'plus_di': plus, 'minus_di': minus})), expected)
        for kind in ('macd', 'roc', 'momentum'):
            params = {'fast': 1, 'slow': 2, 'signal': 1} if kind == 'macd' else {'period': 2}
            for value, expected in [(-.01, 'down'), (0, 'neutral'), (.01, 'up')]:
                self.assertEqual(status(single(kind, params, {'histogram' if kind == 'macd' else 'value': value})), expected)

    def test_context_and_unsupported_have_no_coverage_weight(self):
        for kind in ('atr', 'volume', 'stddev', 'bbwidth', 'ichimoku', 'stochrsi', 'vmc_cipher_a', 'vmc_cipher_b', 'vmc_swing', 'future_kind'):
            result = evaluate_agreement(single(kind, {}))
            self.assertEqual(result['members'][0]['status'], 'context' if kind in ('atr','volume','stddev','bbwidth') else 'unsupported')
            self.assertEqual(result['coverage']['total_types'], 0)
            self.assertIsNone(result['overall'])

    def test_normalization_and_appearance_duplicate_conflict(self):
        self.assertEqual(variant_key('bb', {'period': 20, 'deviations': 2.0}), variant_key('bb', {'deviations': 2, 'period': 20.0}))
        self.assertEqual(variant_key('vwap', {'mode': 0, 'anchor': -0.0}), variant_key('vwap', {'anchor': 0, 'mode': 0}))
        self.assertNotEqual(variant_key('sar', {'step': 1e-7, 'max': .2}), variant_key('sar', {'step': 2e-7, 'max': .2}))
        snapshot = single(); snapshot['instances'].append(dict(snapshot['instances'][0], id='z', params={'period': 2.0}, color='different', placement='different'))
        snapshot['display']['columns']['z'] = {'value': [100]*5}
        self.assertEqual(evaluate_agreement(snapshot)['coverage']['total_variants'], 1)
        snapshot['display']['columns']['z']['value'][-1] = 105
        result = evaluate_agreement(snapshot)
        self.assertEqual(result['variants'][0]['status'], 'unavailable')
        self.assertEqual(result['variants'][0]['reason'], 'duplicate_variant_conflict')
        self.assertEqual(result['coverage']['fully_covered_types'], 0)

    def test_flat_guards_require_whole_smoothing_window_and_real_predecessors(self):
        for kind, params, port, endpoint in [('rsi', {'period': 2}, 'value', 100), ('stochastic', {'period': 2, 'smooth': 3, 'signal': 1}, 'k', 0), ('williamsr', {'period': 2}, 'value', 0)]:
            snapshot = single(kind, params, {port: endpoint})
            for row in snapshot['candles']:
                row.update(open=42, high=42, low=42, close=42)
            self.assertEqual(status(snapshot), 'neutral')
            needed = params['period'] + (1 if kind == 'rsi' else params['smooth']-1 if kind == 'stochastic' else 0)
            snapshot['candles'] = snapshot['candles'][-needed+1:]
            self.assertEqual(status(snapshot), 'unavailable')
        snapshot = single('stochastic', {'period': 2, 'smooth': 3, 'signal': 1}, {'k': 0})
        for row in snapshot['candles'][2:]: row.update(open=42, high=42, low=42, close=42)
        self.assertEqual(status(snapshot), 'down')  # Earlier smoothing input has a real range.
        snapshot['candles'].pop(-2)
        self.assertEqual(status(snapshot), 'unavailable')
        snapshot = single('mfi', {'period': 2}, {'value': None})
        for row in snapshot['candles']: row.update(open=42, high=42, low=42, close=42)
        self.assertEqual(status(snapshot), 'unavailable')

    def test_obv_requires_exact_raw_and_output_neighbors(self):
        snapshot = single('obv', {}, {'value': 10})
        for value, expected in [(11,'up'), (9,'down'), (10,'neutral')]:
            snapshot['display']['columns']['x']['value'][-1] = value
            self.assertEqual(status(snapshot), expected)
        for mutation in ('raw_missing', 'forming', 'conflict', 'output_missing'):
            changed = copy.deepcopy(snapshot)
            if mutation == 'raw_missing': changed['candles'].pop(-2)
            elif mutation == 'forming': changed['candles'][-2]['confirmation'] = 'forming'
            elif mutation == 'conflict': changed['candles'][-2]['conflict'] = True
            else: changed['display']['columns']['x']['value'][-2] = None
            self.assertEqual(status(changed), 'unavailable')

    def test_requested_close_never_falls_back_and_future_has_no_influence(self):
        snapshot = copy.deepcopy(CASES['three_groups_up_up_down']['input'])
        snapshot['close_time'] = snapshot['display']['times'][-2]
        baseline = evaluate_agreement(snapshot)
        for row in snapshot['candles']:
            if row['time'] + 60 > snapshot['close_time']: row.update(close=100000, high=100001, low=-100000)
        for columns in snapshot['display']['columns'].values():
            for values in columns.values(): values[-1] = -10000
        self.assertEqual(evaluate_agreement(snapshot), baseline)
        snapshot['close_time'] += 60
        for columns in snapshot['display']['columns'].values():
            for values in columns.values(): values[-1] = None
        self.assertIsNone(evaluate_agreement(snapshot)['overall'])
        self.assertEqual(evaluate_agreement(snapshot)['close_time'], snapshot['close_time'])

    def test_invalid_or_conflicting_raw_rows_fail_closed(self):
        for update in [dict(conflict=True), dict(confirmation='forming'), dict(high=0), dict(close=float('inf')), dict(open=None), dict(close=10**10000)]:
            snapshot = single(); snapshot['candles'][-1].update(update)
            self.assertEqual(status(snapshot), 'unavailable')
        snapshot = single(); snapshot['display']['columns']['x']['value'][-1] = 10**10000
        self.assertEqual(status(snapshot), 'unavailable')
        with self.assertRaises(ValueError): normalize_params({'period': 10**10000})
        for bad in (True, 0, 1.5, None):
            snapshot = single(); snapshot['interval_seconds'] = bad
            with self.assertRaises(ValueError): evaluate_agreement(snapshot)
        snapshot = single(); snapshot['candles'][1]['time'] = 0
        with self.assertRaises(ValueError): evaluate_agreement(snapshot)
        snapshot = single(); snapshot['display']['times'][1] = 60
        with self.assertRaises(ValueError): evaluate_agreement(snapshot)

    def test_prepared_snapshot_detaches_and_reuses_indexes(self):
        snapshot = copy.deepcopy(CASES['three_groups_up_up_down']['input'])
        prepared = prepare_agreement(snapshot)
        expected = prepared.evaluate(snapshot['close_time'])
        snapshot['instances'][0]['params']['period'] = 999
        snapshot['candles'][-1]['close'] = -999
        snapshot['display']['columns']['s']['value'][-1] = None
        self.assertEqual(prepared.evaluate(snapshot['close_time']), expected)
        for close_time in snapshot['display']['times']:
            self.assertEqual(prepared.evaluate(close_time)['close_time'], close_time)
        returned = prepared.evaluate(snapshot['close_time']); returned['members'][0]['params']['period'] = 900
        self.assertEqual(prepared.evaluate(snapshot['close_time']), expected)

    def test_required_missing_group_unknown_and_threshold_validation(self):
        snapshot = copy.deepcopy(CASES['hidden_down_group_excluded']['input'])
        result = evaluate_agreement(snapshot)
        self.assertIsNone(threshold_evidence(result, 'up', .1, ['volume'])['truth'])
        self.assertTrue(threshold_evidence(result, 'up', 1, [])['truth'])
        for value in (-.1, 1.01, float('nan'), True):
            with self.assertRaises(ValueError): threshold_evidence(result, 'up', value)
        with self.assertRaises(ValueError): threshold_evidence(result, 'up', .5, ['trend','trend'])
        with self.assertRaises(ValueError): threshold_evidence(dict(result, manifest_hash='old'), 'up', .5)

    def test_three_way_largest_remainder_tie_is_deterministic(self):
        snapshot = copy.deepcopy(CASES['three_groups_up_up_down']['input'])
        snapshot['display']['columns']['r']['value'][-1] = 50
        result = evaluate_agreement(snapshot)
        self.assertEqual(result['overall']['exact'], {d: ['1','3'] for d in DIRECTIONS})
        self.assertEqual(result['overall']['percentages'], {'up': 34, 'down': 33, 'neutral': 33})


if __name__ == '__main__':
    unittest.main()
