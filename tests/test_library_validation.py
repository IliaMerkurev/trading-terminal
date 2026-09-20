import copy
import tempfile
import unittest
from terminal.archives import validate_snapshot
from terminal.graph import GraphEvaluator
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class LibraryValidationTests(unittest.TestCase):
    def test_frozen_later_parity_attempts_and_immutable_selection(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                prices=[30,28,26,24,22,20,18,16,18,20,24,30,35,40,35,30,25,20,15,12,15,20,25,30]*2
                bars=[Candle(i*60,p,p+1,p-1,p,100) for i,p in enumerate(prices)]
                data=jobs.datasets.save('spot','BTCUSDT',0,len(prices)*60,bars,[],{},metadata={},provenance=[])
                params=dict(selections=[dict(entry_id='rsi-threshold',version=1,minutes=m,parameters={'period':2}) for m in (1,3)],
                    dataset_id=data['id'],profile=Profile(capital='180',primary_minutes=1,allocation='100').snapshot(),start=600,end=1440,interval='daily',spot_dataset_id=None)
                def wait(ident):
                    thread=manager.active['thread'];thread.join(40)
                    self.assertFalse(thread.is_alive());return manager.get(ident)
                report=wait(manager.start(expected_contract=manager.preview(**params)['contract_sha256'],**params)['batch_id'])
                self.assertEqual(report['status'],'completed',report)
                original=jobs.store.result(report['rows'][0]['run_id'])
                request=dict(batch_id=report['id'],ordinal=0,dataset_id=data['id'],start=1800,end=2880,spot_dataset_id=None)
                with self.assertRaisesRegex(ValueError,'after the selection'):manager.freeze_validation(**{**request,'start':1200})
                frozen=manager.freeze_validation(**request);snap=manager.get(frozen['batch_id'])['snapshot']
                self.assertEqual(manager.get(frozen['batch_id'])['status'],'frozen');self.assertIsNone(manager.active)
                self.assertEqual(snap['validation']['holdout_attempt'],1)
                self.assertEqual(snap['validation']['selection_attempted_variants'],2)
                self.assertEqual(snap['rows'][0]['profile'],report['snapshot']['rows'][0]['profile'])
                self.assertEqual(snap['rows'][0]['contract'],report['snapshot']['rows'][0]['contract'])
                self.assertTrue(snap['validation']['source_version_date'])
                manager.start_validation(frozen['batch_id']);later=wait(frozen['batch_id'])
                self.assertEqual(later['status'],'completed',later)
                self.assertTrue(all(r['run_id'] not in [a['run_id'] for a in report['rows']] for r in later['rows']))
                spec=snap['rows'][0];actual=jobs.store.result(later['rows'][0]['run_id'])
                standalone=run_backtest(bars,Profile(**spec['profile']),GraphEvaluator(spec['document']['graph']),trade_start=1800)
                for field in ('metrics','fills','trades'):self.assertEqual(actual[field],standalone[field],field)
                self.assertGreater(len(actual['trades']),0)
                self.assertTrue(all(int(f['time_ns'])>=1800*10**9 for f in actual['fills']))
                validate_snapshot(jobs.store.get(later['rows'][0]['run_id'])['manifest'])
                with self.assertRaisesRegex(ValueError,'only once'):manager.start_validation(frozen['batch_id'])
                with self.assertRaisesRegex(ValueError,'not a holdout'):manager.freeze_validation(**{**request,'batch_id':later['id'],'start':2880})
                changed=[Candle(b.time,50,100,20,80,b.volume) if b.time>=1800 else b for b in bars]
                altered=jobs.datasets.save('spot','BTCUSDT',0,2880,changed,[],{},metadata={},provenance=[])
                repeat=manager.freeze_validation(**{**request,'dataset_id':altered['id']})
                other=manager.get(repeat['batch_id'])['snapshot']
                self.assertEqual(other['validation']['holdout_attempt'],2)
                self.assertEqual(other['rows'][0]['contract'],snap['rows'][0]['contract'])
                self.assertEqual(other['validation']['selection_metrics'],snap['validation']['selection_metrics'])
                self.assertEqual(jobs.store.result(report['rows'][0]['run_id']),original)
            finally:manager.close();jobs.close()


if __name__=='__main__':unittest.main()
