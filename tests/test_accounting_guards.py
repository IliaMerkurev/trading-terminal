"""Independent tiny goldens for conservative financial eligibility gates."""
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from terminal.data import DatasetStore, run_manifest
from terminal.graph import example_graph
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


def bars(times):
    return [Candle(t, 100, 100, 100, 100, 100) for t in times]


def signal(side):
    return lambda b, t, c: {'signals': {f'entry_{side}': True} if t == 60 else {}, 'values': {}}


def profile(**changes):
    return replace(Profile(market='linear', primary_minutes=1, capital='1000', allocation='100',
                           fee_rate='0', slippage='0', gap_policy='skip'), **changes)


class AccountingGuardTests(unittest.TestCase):
    def test_funding_goldens_and_gap_refusal_both_profiles_directions_and_rates(self):
        complete = bars([0, 60, 120]); marks = {c.time: c for c in complete}
        with tempfile.TemporaryDirectory() as root:
            store = DatasetStore(Path(root) / 'datasets')
            for version in (1, 2):
                for side in ('long', 'short'):
                    for rate in ('0.01', '-0.01'):
                        with self.subTest(version=version, side=side, rate=rate):
                            p = profile(version=version)
                            funding = {0: '0', 60: rate, 120: '0'}
                            result = run_backtest(complete, p, signal(side), marks=marks, funding=funding)
                            expected = D(1000) + (-1 if side == 'long' else 1) * D(100) * D(rate)
                            self.assertEqual(D(result['metrics']['final_equity']), expected)
                            self.assertEqual(D(result['fills'][0]['quantity']), 1)
                            self.assertEqual(sum(D(e['amount']) for e in result['events'] if e['type'] == 'funding'), expected - 1000)
                            for times in ([0, 120], [60, 120], [0, 60]):
                                missing = bars(times)
                                manifest = store.save('linear', 'BTCUSDT', 0, 180, missing, complete, funding,
                                                      metadata={'instrument': {'fundingInterval': 1}}, provenance=['Synthetic golden'])
                                # Stored legacy profiles remain parseable, but cannot execute unsafe inputs.
                                self.assertEqual(Profile(**p.snapshot()), p)
                                with self.assertRaisesRegex(ValueError, 'requires continuous trade history'):
                                    store.for_run(manifest['id'], p)
                                with patch('terminal.simulation.make_instrument') as make:
                                    with self.assertRaisesRegex(ValueError, 'requires continuous trade history'):
                                        run_backtest(missing, p, signal(side), marks=marks, funding=funding)
                                    make.assert_not_called()

    def test_position_management_and_explicit_alternative_controls(self):
        complete = bars([0, 60, 120]); missing = bars([0, 120]); marks = {c.time: c for c in complete}
        p = profile(version=2, position_management={})
        with self.assertRaisesRegex(ValueError, 'requires continuous trade history'):
            run_backtest(missing, p, signal('long'), marks=marks, funding={60: '.01'})
        result = run_backtest(complete, p, signal('long'), marks=marks, funding={60: '.01'})
        self.assertEqual(D(result['metrics']['final_equity']), D(999))
        for p in (profile(funding_mode='assumed_zero'), profile(market='spot')):
            with self.subTest(market=p.market):
                result = run_backtest(missing, p, signal('long'), marks=marks)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(D(result['metrics']['final_equity']), 1000)
                with tempfile.TemporaryDirectory() as root:
                    store = DatasetStore(Path(root))
                    manifest = store.save(p.market, 'BTCUSDT', 0, 180, missing, complete, {},
                                          metadata={'instrument': {'fundingInterval': 1}}, provenance=[])
                    store.check_profile(manifest, p)
        # Even an empty declared funding mapping must not permit an internal gap.
        with self.assertRaisesRegex(ValueError, 'requires continuous trade history'):
            run_backtest(missing, profile(), signal('long'), marks=marks, funding={})

    def wait_job(self, jobs, ident):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = jobs.status(ident)
            if state['status'] in ('completed', 'failed', 'cancelled'):
                return state
            time.sleep(.03)
        self.fail('Worker exceeded bounded deadline')

    def test_managed_worker_refuses_and_legacy_result_reopens_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = JobManager(root)
            try:
                complete = bars([0, 60, 120]); missing = bars([0, 120]); funding = {0: '0', 60: '.01', 120: '0'}
                data = jobs.datasets.save('linear', 'BTCUSDT', 0, 180, missing, complete, funding,
                                          metadata={'instrument': {'fundingInterval': 1}}, provenance=[])
                p = profile()
                # A saved legacy report can still be viewed without rerunning its now-ineligible inputs.
                manifest = run_manifest(example_graph(), p, data)
                old = jobs.store.create(manifest)
                jobs.store.status(old, 'running')
                saved = run_backtest(missing, replace(p, funding_mode='assumed_zero'), signal('long'),
                                     marks={c.time: c for c in complete})
                saved['manifest_sha256'] = manifest['snapshot_sha256']
                jobs.store.complete(old, saved)
                persisted_before = jobs.store.result(old)
                before = (jobs.store.directory(old) / 'result.json').read_bytes()
                with self.assertRaisesRegex(ValueError, 'requires continuous trade history'):
                    jobs.start(example_graph(), p, data['id'])
                self.assertEqual(len(jobs.store.recent()), 1)
                # Bypass only parent preflight to exercise the real independent worker defense.
                with patch.object(jobs.datasets, 'check_profile'):
                    bad = jobs.start(example_graph(), p, data['id'])
                state = self.wait_job(jobs, bad)
                self.assertEqual(state['status'], 'failed', state)
                self.assertIn('requires continuous trade history', state['error'])
                self.assertFalse((jobs.store.directory(bad) / 'worker-result.json').exists())
                self.assertFalse((jobs.store.directory(bad) / 'result.json').exists())
                with self.assertRaisesRegex(ValueError, 'not completed'):
                    jobs.store.result(bad)
                jobs.close(); jobs = JobManager(root)
                self.assertEqual(jobs.store.result(old), persisted_before)
                self.assertEqual((jobs.store.directory(old) / 'result.json').read_bytes(), before)
            finally:
                jobs.close()

    def test_linear_benchmarks_unavailable_and_spot_contract_retained(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = JobManager(root); manager = LibraryBatchManager(jobs)
            try:
                candles = bars(range(0, 1800, 60))
                spot_metadata = {'instrument': {'priceFilter': {'tickSize': '.01'}, 'lotSizeFilter': {
                    'minOrderQty': '.01', 'basePrecision': '.01', 'minOrderAmt': '1',
                    'maxOrderQty': '100', 'maxOrderAmt': '10000'}}}
                spot = jobs.datasets.save('spot', 'BTCUSDT', 0, 1800, candles, [], {}, metadata=spot_metadata, provenance=[])
                linear = jobs.datasets.save('linear', 'BTCUSDT', 0, 1800, candles, candles,
                    {t: '0' for t in range(0, 1800, 60)}, metadata={'instrument': {'fundingInterval': 1}}, provenance=[])
                p = profile(capital='180', fee_rate='.002', tick_size='1', quantity_step='1', min_quantity='1',
                            max_quantity='10', min_notional='150', max_notional='1000', tier_assumption='Synthetic linear tier')
                params = dict(selections=[dict(entry_id='rsi-threshold', version=1, minutes=1, parameters={'period': 2})],
                              dataset_id=linear['id'], profile=p.snapshot(), start=720, end=1800,
                              interval='daily', spot_dataset_id=spot['id'])
                for spot_id in (spot['id'], None, linear['id']):
                    preview = manager.preview(**{**params, 'spot_dataset_id': spot_id})
                    self.assertEqual(sum(not r['error'] for r in preview['rows']), 1)
                    self.assertEqual(preview['modeled_minutes'], 30)
                    for row in preview['rows'][1:]:
                        self.assertIn('independently specified spot execution profile', row['error'])
                        self.assertIn('explicit spot fee assumption', row['error'])
                        self.assertIsNone(row['contract'])
                frozen = manager.prepare(**params)
                self.assertTrue(all('profile' not in r for r in frozen['rows'][1:]))
                ident = manager.start(expected_contract=frozen['contract_sha256'], **params)['batch_id']
                deadline = time.monotonic() + 20
                while manager.active is not None and time.monotonic() < deadline:
                    time.sleep(.03)
                self.assertIsNone(manager.active)
                report = manager.get(ident)
                self.assertEqual(report['status'], 'completed_with_errors', report)
                self.assertEqual([r['status'] for r in report['rows']], ['completed', 'incompatible', 'incompatible'])
                self.assertTrue(all(r['run_id'] is None and r['metrics'] is None for r in report['rows'][1:]))
                self.assertEqual(len(jobs.store.recent()), 1)
                spot_profile = replace(p, market='spot', fee_rate='.001', tick_size='.01', quantity_step='.01',
                                       min_quantity='.01', max_quantity='100', min_notional='1', max_notional='10000')
                spot_params = {**params, 'dataset_id': spot['id'], 'profile': spot_profile.snapshot(), 'spot_dataset_id': None}
                first = manager.prepare(**spot_params); second = manager.prepare(**spot_params)
                self.assertEqual(first, second)
                self.assertTrue(all(not r['error'] for r in first['rows']))
                self.assertEqual(first['modeled_minutes'], 66)  # 30 strategy prefix+evaluation + 18 per passive row.
                altered = manager.prepare(**{**spot_params, 'profile': replace(spot_profile, fee_rate='.003').snapshot()})
                for index in (1, 2):
                    self.assertEqual(first['rows'][index]['profile']['fee_rate'], '.001')
                    self.assertNotEqual(first['rows'][index]['contract']['contract_sha256'], altered['rows'][index]['contract']['contract_sha256'])
                self.assertEqual(manager.get(ident)['snapshot'], report['snapshot'])
            finally:
                manager.close(); jobs.close()

    def test_linear_later_period_preserves_na_benchmarks_and_strategy_preflight(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = JobManager(root); manager = LibraryBatchManager(jobs)
            try:
                candles = bars(range(0, 3600, 60))
                def save(candles, start):
                    return jobs.datasets.save('linear', 'BTCUSDT', start, 3600, candles, candles,
                        {c.time: '0' for c in candles}, metadata={'instrument': {'fundingInterval': 1}}, provenance=[])
                data = save(candles, 0)
                params = dict(selections=[dict(entry_id='rsi-threshold', version=1, minutes=1, parameters={'period': 2})],
                              dataset_id=data['id'], profile=profile().snapshot(), start=720, end=1800,
                              interval='daily', spot_dataset_id=None)
                def wait(ident):
                    thread = manager.active['thread']; thread.join(20)
                    self.assertFalse(thread.is_alive(), 'Batch exceeded bounded deadline')
                    return manager.get(ident)
                first = wait(manager.start(expected_contract=manager.preview(**params)['contract_sha256'], **params)['batch_id'])
                self.assertEqual(first['status'], 'completed_with_errors')
                run_id = first['rows'][0]['run_id']
                original = jobs.store.result(run_id)
                original_bytes = (jobs.store.directory(run_id) / 'result.json').read_bytes()
                request = dict(batch_id=first['id'], ordinal=0, dataset_id=data['id'], start=1800, end=3600, spot_dataset_id=None)
                no_warmup = save(candles[30:], 1800)
                with self.assertRaisesRegex(ValueError, 'Validation preflight: Insufficient preceding indicator warmup'):
                    manager.freeze_validation(**{**request, 'dataset_id': no_warmup['id']})
                self.assertEqual(len(manager.recent()), 1)
                frozen = manager.freeze_validation(**request)
                before = manager.get(frozen['batch_id'])
                self.assertEqual([r['status'] for r in before['rows']], ['pending', 'incompatible', 'incompatible'])
                self.assertEqual(before['snapshot']['rows'][0]['profile'], first['snapshot']['rows'][0]['profile'])
                self.assertTrue(all(r['metrics'] is None for r in before['rows']))
                manager.start_validation(frozen['batch_id']); later = wait(frozen['batch_id'])
                self.assertEqual(later['status'], 'completed_with_errors', later)
                self.assertEqual([r['status'] for r in later['rows']], ['completed', 'incompatible', 'incompatible'])
                self.assertNotEqual(later['rows'][0]['run_id'], run_id)
                self.assertIsNotNone(later['rows'][0]['metrics'])
                self.assertTrue(all(r['metrics'] is None and r['run_id'] is None for r in later['rows'][1:]))
                self.assertEqual(jobs.store.result(run_id), original)
                self.assertEqual((jobs.store.directory(run_id) / 'result.json').read_bytes(), original_bytes)
                self.assertEqual(manager.get(first['id'])['snapshot'], first['snapshot'])
            finally:
                manager.close(); jobs.close()
