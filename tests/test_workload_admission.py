"""Independent modeled-work arithmetic; large cases use manifests, not huge candles."""
import copy
import unittest
from unittest.mock import patch

from tests import test_library_batches as fixtures


class WorkloadAdmissionTests(unittest.TestCase):
    setUp = fixtures.LibraryBatchTests.setUp
    tearDown = fixtures.LibraryBatchTests.tearDown

    def test_small_arithmetic_and_no_cache_discount(self):
        params=copy.deepcopy(self.params)
        params.update(selections=params['selections'][:1],start=12*60,end=30*60)
        preview=self.manager.preview(**params)
        self.assertEqual(preview['modeled_source_candles'],66)  # 30 + 18 + 18, formerly 90
        self.assertEqual(preview['modeled_minutes'],66)
        self.assertEqual(preview['workload_version'],2)
        self.assertEqual([r['prefix_source_candles'] for r in preview['workload_breakdown']],[12,0,0])
        self.assertEqual([r['evaluation_source_candles'] for r in preview['workload_breakdown']],[18]*3)
        self.assertEqual(self.manager.preview(**params),preview)

    def test_exact_large_cases_and_limit_plus_one(self):
        params=copy.deepcopy(self.params)
        manifest=copy.deepcopy(self.jobs.datasets.describe(params['dataset_id']))
        manifest['range']=[0,800000*60]
        params.update(start=600000*60,end=700000*60)
        with patch.object(self.jobs.datasets,'describe',return_value=manifest):
            for count,total in [(1,900000),(2,1600000)]:
                params['selections']=[dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':p}) for p in range(2,2+count)]
                self.assertEqual(self.manager.preview(**params)['modeled_source_candles'],total)
            params['selections'].append(dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':4}))
            with self.assertRaisesRegex(ValueError,'2,000,000 modeled'):self.manager.preview(**params)
            params['selections']=params['selections'][:1]
            # One strategy: prefix + 3*evaluation = 2,000,000; then prefix +1.
            params.update(start=500000*60,end=1000000*60);manifest['range']=[0,1000001*60]
            self.assertEqual(self.manager.preview(**params)['modeled_source_candles'],2000000)
            params.update(start=500001*60,end=1000001*60)
            with self.assertRaisesRegex(ValueError,'2,000,000 modeled'):self.manager.preview(**params)

    def test_coarse_units_and_stale_preview(self):
        params=copy.deepcopy(self.params)
        params['selections']=[dict(entry_id='rsi-threshold',version=1,minutes=60,parameters={'period':2})]
        params['profile'].update(primary_minutes=60,execution_minutes=60)
        params.update(start=12*3600,end=30*3600)
        manifest=copy.deepcopy(self.jobs.datasets.describe(params['dataset_id']))
        manifest.update(range=[0,48*3600],interval_seconds=3600)
        with patch.object(self.jobs.datasets,'describe',return_value=manifest):
            preview=self.manager.preview(**params)
            self.assertEqual(preview['modeled_source_candles'],66)
            self.assertEqual([r['execution_minutes'] for r in preview['workload_breakdown']],[60]*3)
            with patch('threading.Thread.start') as launch:
                params['end']+=3600
                with self.assertRaisesRegex(ValueError,'Preview changed'):
                    self.manager.start(expected_contract=preview['contract_sha256'],**params)
                launch.assert_not_called()

    def test_unavailable_rows_zero_and_old_snapshot_unchanged(self):
        params=copy.deepcopy(self.params);params['start']=60
        frozen=self.manager.prepare(**params)
        self.assertTrue(all(r['modeled_source_candles']==0 for r in frozen['workload_breakdown'][:2]))
        legacy=copy.deepcopy(frozen)
        for key in ('workload_version','workload_breakdown','modeled_source_candles'):legacy.pop(key)
        legacy['modeled_minutes']=999
        self.manager._save('b'*32,legacy,'completed')
        self.assertEqual(self.manager.get('b'*32)['snapshot'],legacy)

    def test_h4_and_daily_units_count_candles_not_minutes(self):
        for minutes in (240,1440):
            params=copy.deepcopy(self.params)
            params['selections']=[dict(entry_id='rsi-threshold',version=1,minutes=minutes,parameters={'period':2})]
            params['profile'].update(primary_minutes=minutes,execution_minutes=minutes)
            params.update(start=12*minutes*60,end=30*minutes*60)
            manifest=copy.deepcopy(self.jobs.datasets.describe(params['dataset_id']))
            manifest.update(range=[0,48*minutes*60],interval_seconds=minutes*60)
            with self.subTest(minutes=minutes),patch.object(self.jobs.datasets,'describe',return_value=manifest):
                preview=self.manager.preview(**params)
                self.assertEqual(preview['modeled_source_candles'],66)
                self.assertEqual([r['execution_minutes'] for r in preview['workload_breakdown']],[minutes]*3)
