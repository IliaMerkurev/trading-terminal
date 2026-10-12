import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from terminal.chart_history import ChartHistory
from terminal.chart_panes import validate_layout
from terminal.chart_presets import ChartPresets
from terminal.data import canonical, digest
from terminal.display_indicators import DisplayIndicators
from terminal.market_hub import MarketHub
from terminal.service import AppService
from terminal.storage import RunStore
from terminal.vumanchu_indicators import DEFAULTS


def item(kind, ident=None, visible=True):
    params = dict(DEFAULTS[kind]) if kind in DEFAULTS else {'rsi': {'period': 3}, 'stochastic': {'period': 3, 'smooth': 2, 'signal': 2}, 'macd': {'fast': 2, 'slow': 4, 'signal': 2}, 'momentum': {'period': 3}, 'atr': {'period': 3}, 'stddev': {'period': 3}, 'ema': {'period': 3}, 'volume': {}}[kind]
    return dict(id=ident or kind, type=kind, params=params, visible=visible, color='#abcdef')


def layout(*groups):
    return dict(version=1, price_weight=400, recorded_weight=150,
                panes=[dict(id=f'pane_{i}', weight=240 if 'vmc_cipher_b' in ids else 130, instance_ids=list(ids)) for i, ids in enumerate(groups)])


class PaneValidationTests(unittest.TestCase):
    def test_compatible_units_and_exclusive_vmc_all_ports(self):
        items = [item(k) for k in ('rsi', 'stochastic', 'macd', 'momentum', 'atr', 'stddev', 'vmc_cipher_b')]
        value = layout(('rsi', 'stochastic'), ('macd', 'momentum'), ('atr', 'stddev'), ('vmc_cipher_b',))
        self.assertEqual(validate_layout(value, items), value)
        for left, right in [('rsi', 'macd'), ('macd', 'atr'), ('momentum', 'stddev'), ('vmc_cipher_b', 'rsi'), ('vmc_cipher_b', 'macd')]:
            with self.subTest(left=left, right=right), self.assertRaisesRegex(ValueError, 'pane layout'):
                validate_layout(layout((left, right)), [item(left), item(right)])

    def test_strict_membership_version_ids_and_weights(self):
        items = [item('rsi'), item('stochastic', visible=False), item('ema'), item('volume')]
        valid = layout(('rsi', 'stochastic'))
        changes = [dict(version=2), dict(price_weight=True), dict(price_weight=float('nan')), dict(price_weight=10**500), dict(recorded_weight=0), dict(extra=1), dict(panes=[])]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_layout(dict(valid, **change), items)
        for members in (['rsi'], ['rsi', 'rsi', 'stochastic'], ['rsi', 'stochastic', 'ema'], ['rsi', 'stochastic', 'volume'], ['unknown']):
            with self.subTest(members=members), self.assertRaises(ValueError):
                validate_layout(layout(members), items)
        for pane_id in ('price', 'recorded', '', 'x'*65):
            broken = copy.deepcopy(valid); broken['panes'][0]['id'] = pane_id
            with self.assertRaises(ValueError): validate_layout(broken, items)
        self.assertEqual(validate_layout(valid, items), valid)

    def test_no_fixed_instance_or_pane_quota(self):
        items = [item('rsi', f'rsi_{i}', visible=False) for i in range(400)]
        doc = layout(*[(i['id'],) for i in items])
        self.assertEqual(len(validate_layout(doc, items)['panes']), 400)


class PaneStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RunStore(Path(self.temp.name))
        self.history = ChartHistory(self.store, MarketHub()); self.history.close()
        self.display = DisplayIndicators(self.history)
        self.presets = ChartPresets(self.display)
        self.items = [item(k) for k in ('ema', 'rsi', 'stochastic', 'macd', 'vmc_cipher_b')]
        self.layout = layout(('macd',), ('vmc_cipher_b',), ('rsi', 'stochastic'))

    def tearDown(self):
        self.display.close(); self.temp.cleanup()

    def save(self, revision=0, **kwargs):
        return self.display.save('spot', 'BTCUSDT', self.items, revision, **kwargs)

    def seed(self):
        with self.store.connect() as db:
            for i in range(100):
                value = 20 + i % 11
                row = dict(time=i*60, open=value-1, high=value+2, low=value-2, close=value, volume=i+1)
                payload = ChartHistory.payload(row); key = ('spot', 'BTCUSDT', 1, i*60)
                db.execute('INSERT INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(payload).decode()))
                db.execute('INSERT INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key, digest(payload), 'synthetic_closed'))

    def read(self, revision, reanchor=False):
        for _ in range(300):
            result = self.display.read('spot', 'BTCUSDT', 1, 0, 5940, revision, reanchor=reanchor)
            reanchor = False
            if result['status'] != 'calculating': return result
            time.sleep(.01)
        self.fail('Display did not finish')

    def test_atomic_roundtrip_restart_stale_revision_and_legacy_client_rejection(self):
        old = self.save()
        self.assertNotIn('pane_layout', old)
        saved = self.save(1, pane_layout=self.layout)
        for kwargs in (dict(revision=1, pane_layout=self.layout), dict(revision=2), dict(revision=2, pane_layout=layout(('rsi', 'macd')))):
            with self.assertRaises(ValueError): self.save(**kwargs)
            self.assertEqual(self.display.settings('spot', 'BTCUSDT'), saved)
        self.display.close(); self.display = DisplayIndicators(self.history)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT'), saved)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT', 'okx')['revision'], 0)
        self.assertNotIn('pane_layout', self.save(2, pane_layout=None))

    def test_layout_only_change_preserves_exact_formula_outputs_and_origins(self):
        self.seed(); self.save(); first = self.read(1)
        self.assertEqual(first['status'], 'ready')
        original = self.display.settings('spot', 'BTCUSDT')
        saved = self.save(1, pane_layout=self.layout)
        second = self.read(2)
        self.assertEqual(saved['origins'], original['origins'])
        for field in ('columns', 'times', 'directions', 'regimes', 'origin', 'price_candles'):
            self.assertEqual(canonical(first.get(field)), canonical(second.get(field)), field)
        for field in ('indicator_events', 'projections'):
            before, after = copy.deepcopy(first[field]), copy.deepcopy(second[field])
            self.assertEqual(before['context'].pop('settings_revision'), 1)
            self.assertEqual(after['context'].pop('settings_revision'), 2)
            self.assertEqual(canonical(before), canonical(after), field)
        self.assertEqual(len(second['columns']['vmc_cipher_b']), 7)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT')['pane_layout'], self.layout)
        self.read(2, reanchor=True)
        after = self.display.settings('spot', 'BTCUSDT')
        self.assertEqual(after['pane_layout'], self.layout)
        self.assertEqual(after['origins']['1']['generation'], original['origins']['1']['generation']+1)

    def test_presets_capture_layout_only_and_keep_destination_origins(self):
        self.seed(); self.save(pane_layout=self.layout); self.read(1)
        meta = self.presets.save_current('Panes', 'bybit', 'spot', 'BTCUSDT', 1)
        content = self.presets.get(meta['id'], 1)['content']
        self.assertEqual(content, dict(version=1, instances=self.items, extensions={'pane_layout': self.layout}))
        self.assertNotIn('origins', content)
        destination = self.display.save('linear', 'ETHUSDT', [], 0, 'okx')
        destination['origins'] = copy.deepcopy(self.display.settings('spot', 'BTCUSDT')['origins'])
        destination['origins']['1']['generation'] = 7
        self.display._write(*self.display.key('linear', 'ETHUSDT', 'okx'), destination)
        applied = self.display.save('linear', 'ETHUSDT', content['instances'], 1, 'okx', pane_layout=content['extensions']['pane_layout'])
        self.assertEqual(applied['origins'], destination['origins'])
        self.assertEqual(applied['pane_layout'], self.layout)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT')['revision'], 1)

    def test_invalid_stored_layout_cannot_be_captured_as_fallback(self):
        saved = self.save(pane_layout=self.layout)
        saved['pane_layout']['version'] = 2
        self.display._write('spot', 'BTCUSDT', saved)
        self.assertIn('warning', self.display.settings('spot', 'BTCUSDT'))
        with self.assertRaisesRegex(ValueError, 'cannot save a preset'):
            self.presets.save_current('Wrong fallback', 'bybit', 'spot', 'BTCUSDT', 0)
        with self.store.connect() as db:
            self.assertEqual(json.loads(db.execute('SELECT document FROM chart_presentation_v1').fetchone()[0]), saved)

    def test_service_legacy_save_and_explicit_reset_are_optional_layout_contracts(self):
        with tempfile.TemporaryDirectory() as root:
            service = AppService(Path(root))
            def save(revision, **extra):
                return service.handle(dict(version=1, id='legacy-panes', command='chart_indicator_save',
                    params=dict(market='spot', symbol='BTCUSDT', revision=revision, instances=self.items, **extra)))
            try:
                legacy = save(0)
                self.assertEqual(legacy['type'], 'result')
                self.assertNotIn('pane_layout', legacy['result'])
                custom = save(1, pane_layout=self.layout)
                self.assertEqual(custom['result']['pane_layout'], self.layout)
                rejected = save(2)
                self.assertEqual(rejected['type'], 'error')
                self.assertIn('Pane layout must be included', rejected['error']['message'])
                self.assertEqual(service.display_indicators.settings('spot', 'BTCUSDT')['revision'], 2)
                reset = save(2, pane_layout=None)
                self.assertEqual(reset['result']['revision'], 3)
                self.assertNotIn('pane_layout', reset['result'])
            finally: service.close()

    def test_service_inline_and_checksum_upload_keep_layout(self):
        with tempfile.TemporaryDirectory() as root:
            service = AppService(Path(root))
            def call(command, **params): return service.handle(dict(version=1, id='panes', command=command, params=params))
            try:
                params = dict(source='bybit', market='spot', symbol='BTCUSDT', revision=0, instances=self.items, pane_layout=self.layout)
                first = call('chart_indicator_save', **params)
                self.assertEqual(first['result']['pane_layout'], self.layout)
                params['revision'] = 1; params['pane_layout']['price_weight'] = 500
                raw = canonical(params)
                upload = call('chart_indicator_upload_begin', size=len(raw), sha256=hashlib.sha256(raw).hexdigest())['result']['upload_id']
                call('chart_indicator_upload_append', upload_id=upload, offset=0, text=raw.decode())
                self.assertEqual(service.display_indicators.settings('spot', 'BTCUSDT')['pane_layout']['price_weight'], 400)
                finished = call('chart_indicator_upload_finish', upload_id=upload)
                self.assertEqual(finished['result']['pane_layout']['price_weight'], 500)
                self.assertEqual(finished['result']['revision'], 2)
            finally: service.close()
