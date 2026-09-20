from dataclasses import replace
from decimal import Decimal
import tempfile
import time
import unittest

from terminal.benchmarks import start_or_reuse
from terminal.jobs import JobManager
from terminal.profile import Profile
from terminal.series import Candle


class BenchmarkJobTests(unittest.TestCase):
    def test_managed_persistence_cache_and_capital_invalidation(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root)
            try:
                bars=[Candle(i*60,10,10,10,10,100) for i in range(3)]
                dataset=jobs.datasets.save('spot','BTCUSDT',0,180,bars,[],{},metadata={},provenance=[])
                profile=Profile(capital='180',fee_rate='.001',primary_minutes=1)
                with self.assertRaisesRegex(ValueError,'frozen contract'):
                    jobs.start({'benchmark':'passive','version':1,'start':0,'end':180,'interval':'once'},profile,dataset['id'])
                def wait(ident):
                    limit=time.monotonic()+20
                    while time.monotonic()<limit:
                        state=jobs.status(ident)
                        if state['status'] in ('completed','failed'):return state
                        time.sleep(.03)
                    self.fail('Benchmark worker exceeded bounded deadline')
                first=start_or_reuse(jobs,profile,dataset['id'],0,180,'once')
                self.assertFalse(first['reused'])
                self.assertEqual(wait(first['run_id'])['status'],'completed')
                result=jobs.store.result(first['run_id'])
                self.assertEqual(Decimal(result['metrics']['final_equity']),Decimal('179.64036'))
                second=start_or_reuse(jobs,profile,dataset['id'],0,180,'once')
                self.assertTrue(second['reused']);self.assertEqual(second['run_id'],first['run_id'])
                import json
                with jobs.store.connect() as db:
                    summary=jobs.store.get(first['run_id'])['summary'];summary['origin']='imported'
                    db.execute('UPDATE runs SET summary=? WHERE id=?',(json.dumps(summary),first['run_id']))
                imported=start_or_reuse(jobs,profile,dataset['id'],0,180,'once')
                self.assertFalse(imported['reused'])
                self.assertEqual(wait(imported['run_id'])['status'],'completed')
                altered=start_or_reuse(jobs,replace(profile,capital='181'),dataset['id'],0,180,'once')
                self.assertNotEqual(altered['run_id'],first['run_id'])
                self.assertEqual(wait(altered['run_id'])['status'],'completed')
                self.assertEqual(jobs.store.result(first['run_id']),result)
            finally:jobs.close()


if __name__=='__main__':unittest.main()
