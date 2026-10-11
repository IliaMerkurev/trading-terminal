"""VMC transport/replay tests, independent from formula numerical goldens."""
import copy
import math
import unittest
from terminal import vumanchu_indicators as vmc
from terminal.display_indicators import calculate, validate_instances


def instance(kind='vmc_cipher_b', ident=None, **params):
    return dict(id=ident or kind, type=kind, params=dict(vmc.DEFAULTS[kind], **params), color='#7eabff', visible=True)


def rows(count=180):
    result = []
    for i in range(count):
        close = 100 + 12*math.sin(i*.4) + i*.01
        opening = close + 1.5*math.sin(i*.7)
        result.append(dict(time=i*60, open=opening, high=max(opening, close)+2,
            low=min(opening, close)-2, close=close, volume=5., confirmation='synthetic_closed'))
    return result


class VmcIntegrationTests(unittest.TestCase):
    def test_canonical_defaults_typed_and_unlimited_instances(self):
        items = [instance(kind) for kind in vmc.DEFAULTS]
        self.assertEqual(validate_instances(items), items)
        many = [instance(ident=f'cipher{i}') for i in range(101)]
        self.assertEqual(len(validate_instances(many)), 101)
        for key, value in (('stoch_log', 1), ('source', 3), ('channel', True),
                           ('flow_offset', float('nan')), ('oversold', 53.)):
            with self.assertRaises(ValueError):
                validate_instances([instance(**{key: value})])
        validate_instances([instance(source='ohlc4', flow_offset=-2.25)])

    def test_numeric_ports_events_and_regimes_match_origin_replay(self):
        candles = rows()
        for kind in vmc.DEFAULTS:
            item = instance(kind)
            actual = calculate(candles, [item], 1, 0, candles[-1]['time'])
            state = vmc.VumanchuState(item)
            expected = {port: [] for port in vmc.ports(kind)}
            expected_events, regimes = [], []
            for row in candles:
                values = state.update(row)
                for port, value in values.items(): expected[port].append(value)
                expected_events.extend(dict(e) for e in state.events)
                regimes.append(state.regime)
            self.assertEqual(actual['columns'][kind], expected)
            self.assertEqual(actual['regimes'].get(kind), regimes if kind != 'vmc_cipher_b' else None)
            wire = actual['indicator_events']['instances'][kind]
            self.assertTrue(wire)
            identities = {(e['kind'], e.get('oscillator'), e['pivot_time']-60, e['confirmed_at']-60,
                           e.get('previous_pivot_time', 60)-60) for e in wire}
            wanted = {(e['kind'], e.get('oscillator'), e['pivot_time'], e['confirmed_at'],
                       e.get('previous_pivot_time', 0)) for e in expected_events}
            self.assertEqual(identities, wanted)

    def test_prefix_invariance_cutoff_and_future_perturbation(self):
        candles = rows(90); item = instance(wt_div_top=-100., wt_div_bottom=-101.)
        whole = calculate(candles, [item], 1, 0, candles[-1]['time'])
        for end in (25, 49, 70):
            prefix = calculate(candles, [item], 1, 0, candles[end]['time'])
            self.assertEqual(prefix['columns'][item['id']], {k:v[:end+1] for k,v in whole['columns'][item['id']].items()})
            self.assertEqual(prefix['indicator_events']['instances'][item['id']],
                [e for e in whole['indicator_events']['instances'][item['id']] if e['confirmed_at'] <= (end+1)*60])
        changed = copy.deepcopy(candles)
        for row in changed[71:]:
            for key in ('open', 'high', 'low', 'close'): row[key] += 1000
        self.assertEqual(calculate(changed, [item], 1, 0, 70*60), calculate(candles, [item], 1, 0, 70*60))

    def test_missing_unknown_reset_does_not_bridge_events(self):
        candles = rows(100); item = instance('vmc_swing', period=2, multiplier=.5)
        candles[39]['confirmation'] = 'legacy_unknown'
        del candles[59]
        whole = calculate(candles, [item], 1, 0, 99*60)
        after = calculate(candles[59:], [item], 1, 60*60, 99*60)
        by_time = dict(zip(whole['times'], whole['columns'][item['id']]['filter']))
        self.assertEqual([by_time[t] for t in after['times']], after['columns'][item['id']]['filter'])
        for e in whole['indicator_events']['instances'][item['id']]:
            self.assertGreaterEqual(e['pivot_time']-60, e['segment'])
            self.assertGreaterEqual(e.get('previous_pivot_time', e['pivot_time'])-60, e['segment'])


class VmcSnapshotTests(unittest.TestCase):
    def test_dense_uncapped_instances_snapshot_checksum_and_budget(self):
        import hashlib
        import json
        from terminal.data import canonical
        from terminal.indicator_transport import IndicatorTransport
        candles = rows(320)
        items = [instance(ident=f'cipher{i}') for i in range(48)]
        output = calculate(candles, items, 1, 0, candles[-1]['time'])
        output['settings'] = dict(instances=items)
        self.assertEqual(len(output['columns']), 48)
        self.assertEqual(len(output['indicator_events']['instances']), 48)
        transport = IndicatorTransport(); self.addCleanup(transport.close)
        descriptor = transport.pack(output)
        self.assertEqual(descriptor['status'], 'paged')
        pages = [transport.page(descriptor['snapshot_id'], i) for i in range(descriptor['pages'])]
        self.assertTrue(all(len(canonical(page)) < 900*1024 for page in pages))
        raw = ''.join(page['text'] for page in pages).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), descriptor['sha256'])
        self.assertEqual(len(raw), descriptor['bytes'])
        self.assertEqual(json.loads(raw), output)
        # Transport chunks do not replay/reseed any indicator state.
        self.assertEqual(output['columns']['cipher0'], output['columns']['cipher47'])
        self.assertEqual(len(output['indicator_events']['instances']['cipher0']),
                         len(output['indicator_events']['instances']['cipher47']))

    def test_event_memory_preflight_is_explicit_and_not_an_instance_quota(self):
        items = [instance(ident=f'cipher{i}') for i in range(30)]
        self.assertEqual(len(validate_instances(items)),30)
        with self.assertRaisesRegex(ValueError, '256 MiB working resource budget'):
            calculate(rows(1800),items,1,0,1799*60)
        # The same complete settings fit a smaller viewport; nothing is dropped.
        output = calculate(rows(12),items,1,0,11*60)
        self.assertEqual(set(output['columns']),{item['id'] for item in items})

    def test_hidden_instances_preserved_in_settings_but_not_calculated(self):
        item = instance(); item['visible'] = False
        actual = calculate(rows(), [item], 1, 0, 1000)
        self.assertEqual(actual['columns'], {})
        self.assertEqual(actual['indicator_events']['instances'], {})
        self.assertEqual(validate_instances([item])[0], item)
