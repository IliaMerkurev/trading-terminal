import copy
import tempfile
import time
import unittest
from unittest.mock import patch

from terminal.archives import validate_snapshot
from terminal.benchmarks import metrics
from terminal.graph import GraphEvaluator
from terminal.jobs import JobManager
from terminal.library import prepare
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class LibraryBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.jobs=JobManager(self.tmp.name)
        self.manager=LibraryBatchManager(self.jobs)
        prices=[30,28,26,24,22,20,18,16,18,20,24,30,35,40,35,30,25,20,15,12,15,20,25,30]*2
        self.bars=[Candle(i*60,p,p+1,p-1,p,100) for i,p in enumerate(prices)]
        data=self.jobs.datasets.save('spot','BTCUSDT',0,len(prices)*60,self.bars,[],{},metadata={},provenance=[])
        self.params=dict(selections=[dict(entry_id='rsi-threshold',version=1,minutes=m,parameters={'period':2}) for m in (1,3)],
            dataset_id=data['id'],profile=Profile(capital='180',primary_minutes=1,allocation='100').snapshot(),
            start=12*60,end=len(prices)*60,interval='daily',spot_dataset_id=None)

    def tearDown(self):
        self.manager.close();self.jobs.close();self.tmp.cleanup()

    def start(self):
        expected=self.manager.preview(**self.params)['contract_sha256']
        return self.manager.start(expected_contract=expected,**self.params)['batch_id']

    def wait(self, ident):
        limit=time.monotonic()+40
        while time.monotonic()<limit:
            if self.manager.active is None:return self.manager.get(ident)
            time.sleep(.03)
        self.fail('Batch exceeded bounded deadline')

    def test_window_parity_benchmarks_archive_and_exact_cache(self):
        report=self.wait(self.start())
        self.assertEqual(report['status'],'completed',report)
        self.assertEqual(len(report['rows']),4)
        for row in report['rows'][:2]:
            spec=report['snapshot']['rows'][row['ordinal']]
            standalone=run_backtest(self.bars,Profile(**spec['profile']),GraphEvaluator(spec['document']['graph']),trade_start=self.params['start'])
            result=self.jobs.store.result(row['run_id'])
            self.assertEqual(result['metrics'],standalone['metrics'])
            self.assertEqual(result['trades'],standalone['trades'])
            self.assertGreater(len(result['trades']),0)
            self.assertEqual(row['metrics'],metrics(standalone,self.params['start'],self.params['end']))
            validate_snapshot(self.jobs.store.get(row['run_id'])['manifest'])
        previous=[r['run_id'] for r in report['rows'][2:]]
        second=self.wait(self.start())
        self.assertEqual([r['run_id'] for r in second['rows'][2:]],previous)
        self.assertTrue(all(r['reused'] for r in second['rows'][2:]))

    def test_cancel_restart_resume_pending_only_and_global_reservation(self):
        original=self.manager._run
        def finish_one(active,*args):
            with self.assertRaisesRegex(ValueError,'owns the calculation slot'):
                self.jobs.start(prepare('rsi-threshold',1,1,{'period':2})['document']['graph'],self.params['profile'],self.params['dataset_id'])
            result=original(active,*args)
            active['stop'].set()
            return result
        with patch.object(self.manager,'_run',side_effect=finish_one):report=self.wait(self.start())
        self.assertEqual(report['status'],'cancelled')
        self.assertEqual([r['status'] for r in report['rows']],['completed','pending','pending','pending'])
        completed=report['rows'][0]['run_id'];immutable=self.jobs.store.result(completed)
        self.manager.close();self.jobs.close()
        self.jobs=JobManager(self.tmp.name);self.manager=LibraryBatchManager(self.jobs)
        self.assertIsNone(self.manager.active)
        with patch('terminal.library_batches.runtime_snapshot',return_value={}):
            with self.assertRaisesRegex(ValueError,'Runtime changed'):self.manager.resume(report['id'])
        self.manager.resume(report['id']);resumed=self.wait(report['id'])
        self.assertEqual(resumed['status'],'completed',resumed)
        self.assertEqual(resumed['rows'][0]['run_id'],completed)
        self.assertEqual(self.jobs.store.result(completed),immutable)
        with self.assertRaisesRegex(ValueError,'Only stopped'):self.manager.resume(report['id'])

    def test_preflight_preview_guards_no_native_load_and_async_corruption(self):
        params=copy.deepcopy(self.params)
        params['selections'].append(dict(entry_id='native-ema-cross',version=1,minutes=1,parameters={}))
        preview=self.manager.preview(**params)
        self.assertIn('market',preview['rows'][2]['error'])
        params['start']=60
        self.assertIn('warmup',self.manager.preview(**params)['rows'][0]['error'])
        params=copy.deepcopy(self.params);params['selections'].append(params['selections'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.manager.preview(**params)
        expected=self.manager.preview(**self.params)['contract_sha256']
        with self.assertRaisesRegex(ValueError,'Preview changed'):
            self.manager.start(expected_contract='0'*64,**self.params)
        # Corrupt only an isolated synthetic immutable file, never owner data.
        (self.jobs.datasets.root/self.params['dataset_id']/'trade.parquet').write_bytes(b'corrupt')
        ident=self.manager.start(expected_contract=expected,**self.params)['batch_id']
        report=self.wait(ident)
        self.assertEqual(report['status'],'failed')
        self.assertIn('checksum',report['error'])
        self.assertTrue(all(r['run_id'] is None for r in report['rows']))
        self.assertIsNone(self.jobs.reservation)


if __name__=='__main__':unittest.main()
