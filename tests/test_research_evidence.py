import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from terminal import research_evidence as evidence
from terminal.experiments import ExperimentManager
from terminal.graph import example_graph
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.storage import RunStore


class ResearchEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.jobs=JobManager(self.temp.name);self.addCleanup(self.jobs.close)
        self.profile=Profile(primary_minutes=1,capital='180',allocation='100')
        self.data=self.jobs.datasets.save('spot','BTCUSDT',0,2880,
            [Candle(i*60,100+i%6,102+i%6,98+i%6,100+i%6,100) for i in range(48)],[],{},
            metadata={'synthetic':True},provenance=[],source='Synthetic evidence fixture')

    def wait(self,manager):
        thread=(manager.active['monitor'] if isinstance(manager,JobManager) else manager.active['thread'])
        thread.join(40);self.assertFalse(thread.is_alive())

    def rows(self):
        with self.jobs.store.connect() as db:return [dict(r) for r in db.execute("SELECT * FROM research_evidence WHERE kind!='coverage'")]

    def test_atomic_admission_failure_prevents_process_and_quarantines(self):
        with self.jobs.store.connect() as db:db.execute("CREATE TRIGGER reject_evidence BEFORE INSERT ON research_evidence WHEN NEW.kind='started' BEGIN SELECT RAISE(ABORT,'injected admission failure'); END")
        with patch('terminal.jobs.subprocess.Popen') as launch:
            with self.assertRaises(sqlite3.Error):self.jobs.start(example_graph(),self.profile,self.data['id'])
        launch.assert_not_called();self.assertIsNone(self.jobs.active);self.assertIsNone(self.jobs.reservation)
        self.assertIsNotNone(self.jobs.storage_diagnostic());self.assertEqual(self.jobs.store.recent(),[])
        self.assertEqual(self.rows(),[])

    def test_admitted_launch_failure_is_not_completion_or_duplicate(self):
        with patch('terminal.jobs.worker_job',side_effect=OSError('controlled launch failure')):
            with self.assertRaises(OSError):self.jobs.start(example_graph(),self.profile,self.data['id'])
        rows=self.rows();self.assertEqual(len(rows),1);row=rows[0]
        self.assertEqual((row['kind'],row['route'],row['role']),('started','custom','strategy'))
        self.assertEqual(row['owner_id'],row['run_id']);self.assertEqual(self.jobs.store.get(row['run_id'])['status'],'failed')
        with self.jobs.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE research_evidence SET kind=? WHERE event_id=?',('frozen',row['event_id']))
        original=(Path(self.temp.name)/'runs'/row['run_id']/'snapshot.json').read_bytes()
        self.jobs.close();self.jobs=JobManager(self.temp.name);self.addCleanup(self.jobs.close)
        self.assertEqual(self.rows(),rows);self.assertEqual((Path(self.temp.name)/'runs'/row['run_id']/'snapshot.json').read_bytes(),original)

    def test_half_open_warmup_real_cross_market_and_synthetic_isolation(self):
        real={**self.data,'source':'Bybit public API','metadata':{},'provenance':[{'endpoint':'/v5/market/kline','response_sha256':'a'*64,'retrieved_at':'2026-01-01'}]}
        unknown={**real,'provenance':[]}
        self.assertEqual(evidence.provenance(unknown)[1],'unknown')
        self.assertEqual(evidence.provenance({**real,'metadata':{'synthetic':True}})[1],'synthetic')
        with self.jobs.store.connect() as db:
            for i,(dataset,market) in enumerate([(real,'spot'),(real,'linear'),(unknown,'spot'),(self.data,'spot')]):
                value=evidence.event(dataset,{**self.profile.snapshot(),'market':market},1440,1800,route='custom',owner_id=str(i),input_start=0)
                evidence.append(db,str(i),'started',value)
            summary=evidence.overlaps(db,real,1440,1800)
            self.assertEqual(summary['total'],3);self.assertEqual({g['market'] for g in summary['groups']},{'spot','linear'})
            self.assertEqual(evidence.overlaps(db,self.data,1440,1800)['total'],1)
            self.assertEqual(evidence.overlaps(db,{**self.data,'source':'Synthetic other fixture'},1440,1800)['total'],0)
            self.assertEqual(evidence.overlaps(db,real,600,1440)['total'],0)
            self.assertEqual(evidence.overlaps(db,real,1800,2160)['total'],0)
            self.assertIn('unrecorded',summary['limitation']);self.assertIn('does not establish',summary['limitation'])

    def test_cross_route_freezes_and_atomic_rollback_preserve_reports(self):
        library=LibraryBatchManager(self.jobs);experiment=ExperimentManager(self.jobs)
        self.addCleanup(library.close);self.addCleanup(experiment.close)
        selections=[dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':2})]
        params=dict(selections=selections,dataset_id=self.data['id'],profile=self.profile.snapshot(),start=600,end=1200,interval='daily',spot_dataset_id=None)
        batch=library.start(expected_contract=library.preview(**params)['contract_sha256'],**params)['batch_id'];self.wait(library)
        strategy=self.jobs.store.save_strategy('Synthetic experiment','graph',{'graph':example_graph(),'layout':{}},profile=self.profile.snapshot())
        exp=experiment.start(strategy_id=strategy,dataset_id=self.data['id'],profile=self.profile.snapshot(),is_range=[1440,1800],oos_range=[2160,2880],axes=[{'key':'node.mean.period','values':[2]}])['experiment_id'];self.wait(experiment)
        run=self.jobs.start(example_graph(),self.profile,self.data['id'],research={'window':{'start':2160,'end':2880,'warmup_start':0}});self.wait(self.jobs)
        before={p:p.read_bytes() for p in Path(self.temp.name).glob('runs/*/*.json')}
        request=dict(batch_id=batch,ordinal=0,dataset_id=self.data['id'],start=1440,end=2880,spot_dataset_id=None)
        frozen=library.freeze_validation(**request)['batch_id']
        review=library.get(frozen)['research_evidence']
        self.assertEqual({g['route'] for g in review['groups']},{'custom','experiment'})
        self.assertEqual(review['total'],2)
        self.assertEqual(library.get(frozen)['status'],'frozen');self.assertIsNone(library.active)
        other=experiment.freeze(exp,0)['validation_id']
        report=experiment.get(exp)['validations'][0]
        self.assertEqual(report['id'],other)
        self.assertIn('library',{g['route'] for g in report['research_evidence']['groups']})
        frozen_rows=[r for r in self.rows() if r['kind']=='frozen']
        self.assertEqual(len(frozen_rows),2);self.assertTrue(all(r['run_id'] is None for r in frozen_rows))
        self.assertEqual(sum(r['role']=='passive' for r in self.rows()),2)
        with self.jobs.store.connect() as db:
            count=db.execute('SELECT count(*) FROM library_batches').fetchone()[0]
            db.execute("CREATE TRIGGER reject_freeze BEFORE INSERT ON research_evidence WHEN NEW.kind='frozen' BEGIN SELECT RAISE(ABORT,'injected freeze failure'); END")
        with self.assertRaises(sqlite3.Error):library.freeze_validation(**request)
        with self.jobs.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM library_batches').fetchone()[0],count)
        self.assertIsNone(self.jobs.reservation);self.assertIsNotNone(self.jobs.storage_diagnostic())
        self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))

    def test_repeated_identical_admissions_and_migration_failure_release_lock(self):
        with patch('terminal.jobs.worker_job',side_effect=OSError('controlled launch failure')):
            for _ in range(2):
                with self.assertRaises(OSError):self.jobs.start(example_graph(),self.profile,self.data['id'])
        self.assertEqual(len(self.rows()),2)
        self.assertEqual(len({r['run_id'] for r in self.rows()}),2)
        with tempfile.TemporaryDirectory() as root:
            with patch('terminal.research_evidence.initialize',side_effect=sqlite3.OperationalError('controlled migration failure')):
                with self.assertRaises(sqlite3.OperationalError):JobManager(root)
            reopened=JobManager(root);reopened.close()

    def test_existing_database_migration_has_marker_not_fabricated_history(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'terminal.sqlite3'
            db=sqlite3.connect(path);db.execute('CREATE TABLE legacy(value TEXT)');db.execute("INSERT INTO legacy VALUES('unchanged')");db.commit();db.close()
            store=RunStore(root)
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT value FROM legacy').fetchone()[0],'unchanged')
                self.assertEqual([r[0] for r in db.execute('SELECT kind FROM research_evidence')],['coverage'])
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
