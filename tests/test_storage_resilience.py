"""Deterministic storage-failure injections; no market downloads or engine runs."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

from terminal.jobs import JobManager
from terminal.experiments import ExperimentManager
from terminal.library_batches import LibraryBatchManager
from terminal.service import AppService
from terminal.storage import RunStore
from scripts.verify_migration import verify_results


@contextmanager
def fail_update(store, prefix, message='disk is full'):
    original=store.connect
    attempts=[]
    class Connection:
        def __init__(self,db):self.db=db
        def execute(self,sql,*args):
            if sql.startswith(prefix):
                attempts.append(sql)
                raise sqlite3.OperationalError(message)
            return self.db.execute(sql,*args)
        def __getattr__(self,name):return getattr(self.db,name)
    @contextmanager
    def connect():
        with original() as db:yield Connection(db)
    with patch.object(store,'connect',connect):yield attempts


class StorageFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.jobs=JobManager(self.tmp.name);self.addCleanup(self.jobs.close)
        self.experiments=ExperimentManager(self.jobs)
        self.library=LibraryBatchManager(self.jobs)
        self.store=self.jobs.store
        self.ident='a'*32

    def assert_blocked(self,kind):
        self.assertIsNone(self.jobs.active)
        self.assertIsNone(self.jobs.reservation)
        latch=self.jobs.storage_diagnostic()
        self.assertEqual((latch['id'],latch['kind'],latch['durable']),(self.ident,kind,False))
        self.assertNotIn('/private',latch['message'])
        # Gate before inspecting or starting any supplied calculation.
        with patch('terminal.jobs.subprocess.Popen') as launch:
            for action in (lambda:self.jobs.start({}, {}, 'missing'),
                           lambda:self.jobs.start_replay('missing'),
                           lambda:self.experiments._reserve('b'*32,lambda _:None),
                           lambda:self.library._reserve('b'*32,lambda _:None)):
                with self.assertRaisesRegex(ValueError,'blocked by storage finalization'):action()
            launch.assert_not_called()
        latch['message']='changed externally'
        self.assertNotEqual(self.jobs.storage_diagnostic()['message'],'changed externally')

    def test_three_scheduler_finalizers_release_and_recover_without_retry(self):
        for kind,table,manager,target in (
            ('experiment','experiments',self.experiments,self.experiments._grid),
            ('validation','validations',self.experiments,self.experiments._validation),
            ('library_batch','library_batches',self.library,self.library._batch)):
            for fault in ('disk is full','attempt to write a readonly database','database is locked'):
                with self.subTest(kind=kind,fault=fault):
                    manager.jobs=self.jobs;manager.store=self.store
                    self.jobs.storage_failure=None  # Each injection represents a fresh process.
                    snapshot={'graph':{},'profile':{},'oos_range':[60,120],'is_range':[0,60],
                              'warmup_start':0,'candidate_sha256':'fixture','candidate_run_id':'b'*32,
                              'candidate_ordinal':0,'parameters':{},'axes':[]}
                    with self.store.connect() as db:
                        db.execute(f'DELETE FROM {table}')
                        if kind=='validation':
                            db.execute('INSERT INTO validations VALUES(?,?,?,?,?,NULL,NULL)',(self.ident,'c'*32,'2026-01-01','running',json.dumps(snapshot)))
                        else:db.execute(f'INSERT INTO {table} VALUES(?,?,?,?,NULL)',(self.ident,'2026-01-01','running',json.dumps(snapshot)))
                    manager._reserve(self.ident,target)
                    with patch.object(manager,'_run',return_value={'status':'completed','error':None}), \
                         patch.object(self.library,'_unchanged'),patch.object(self.library,'_preflight_data'), \
                         fail_update(self.store,f'UPDATE {table} SET status=?,error=?',fault) as attempts:
                        target(manager.active)
                    self.assertEqual(len(attempts),1)
                    self.assertIsNone(manager.active)
                    self.assert_blocked(kind)
                    with self.store.connect() as db:
                        self.assertEqual(db.execute(f'SELECT status FROM {table} WHERE id=?',(self.ident,)).fetchone()[0],'running')
                    if kind!='validation':
                        status=manager.get(self.ident)
                        self.assertEqual(status['status'],'running')
                        self.assertEqual(status['storage_failure']['kind'],kind)
                    # Reopen the actual workspace: no thread or automatic work begins.
                    self.jobs.close()
                    self.jobs=JobManager(self.tmp.name);self.addCleanup(self.jobs.close)
                    self.store=self.jobs.store
                    self.experiments=ExperimentManager(self.jobs);self.library=LibraryBatchManager(self.jobs)
                    with self.store.connect() as db:
                        self.assertEqual(db.execute(f'SELECT status FROM {table} WHERE id=?',(self.ident,)).fetchone()[0],'interrupted')
                    self.assertIsNone(self.jobs.storage_diagnostic())
                    self.assertIsNone(self.jobs.active)
                    self.assertIsNone(self.experiments.active)
                    self.assertIsNone(self.library.active)
                    # The loop's manager instances must now use the fresh ownership.
                    manager.jobs=self.jobs;manager.store=self.store

    def test_run_storage_failure_has_no_fallback_write_and_retains_saved_state(self):
        self.ident=self.store.create({'snapshot_sha256':'fixture'})
        self.store.status(self.ident,'running')
        (self.store.directory(self.ident)/'worker-result.json').write_text('{}')
        self.jobs.active={'id':self.ident,'generation':'d'*32,'cancelled':False}
        with patch('terminal.result_finalization.claim',side_effect=OSError('disk full /private/path')) as complete, \
             patch.object(self.store,'status',wraps=self.store.status) as status:
            self.jobs._monitor(self.ident,Mock(wait=Mock(return_value=0)),Mock(),Mock(is_alive=Mock(return_value=False)))
        complete.assert_called_once();status.assert_not_called()
        self.assert_blocked('run')
        report=self.jobs.status(self.ident)
        self.assertEqual(report['status'],'running')
        self.assertIsNone(report['summary'])
        self.assertEqual(report['storage_failure']['id'],self.ident)

    def test_invalid_worker_output_then_failed_error_persistence_is_quarantined(self):
        self.ident=self.store.create({'snapshot_sha256':'fixture'});self.store.status(self.ident,'running')
        (self.store.directory(self.ident)/'worker-result.json').write_text('{}')
        self.jobs.active={'id':self.ident,'generation':'d'*32,'cancelled':False}
        with patch('terminal.result_finalization.claim',side_effect=ValueError('invalid result')), \
             patch('terminal.result_finalization.settle',side_effect=sqlite3.OperationalError('read only')) as status:
            self.jobs._monitor(self.ident,Mock(wait=Mock(return_value=0)),Mock(),Mock(is_alive=Mock(return_value=False)))
        status.assert_called_once()
        self.assert_blocked('run')

    def test_replay_finalization_releases_worker_and_anchor(self):
        with self.store.connect() as db:db.execute('INSERT INTO replay_jobs VALUES(?,?,?,NULL,NULL)',(self.ident,'b'*32,'running'))
        self.jobs.active={'id':self.ident,'kind':'replay','cancelled':True}
        anchor=Mock()
        with fail_update(self.store,'UPDATE replay_jobs SET status=?,error=?,result=?') as attempts:
            self.jobs._monitor_replay(self.ident,'b'*32,Mock(wait=Mock(return_value=1)),Mock(),Mock(),anchor)
        self.assertEqual(len(attempts),1);anchor.close.assert_called_once()
        self.assert_blocked('replay')
        self.assertEqual(self.jobs.replay_status(self.ident)['status'],'running')
        self.assertFalse(self.jobs.replay_status(self.ident)['worker_active'])
        self.assertEqual(self.jobs.replay_status(self.ident)['storage_failure']['kind'],'replay')

    def test_child_storage_latch_stops_grid_before_next_row(self):
        graph={'nodes':[],'edges':[]}
        snapshot={'graph':graph,'profile':{},'is_range':[0,60],'oos_range':[60,120],
                  'warmup_start':0,'axes':[]}
        with self.store.connect() as db:
            db.execute('INSERT INTO experiments VALUES(?,?,?,?,NULL)',(self.ident,'2026-01-01','running',json.dumps(snapshot)))
            for ordinal in range(2):db.execute('INSERT INTO experiment_rows VALUES(?,?,?,?,NULL,NULL)',(self.ident,ordinal,'{}','pending'))
        def child(*args):
            self.jobs.latch_storage_failure('b'*32,'run')
            self.jobs.require_storage_ready()
        self.experiments._reserve(self.ident,self.experiments._grid)
        with patch('terminal.experiments.apply_parameters',return_value=(graph,{})),patch.object(self.experiments,'_run',side_effect=child) as run:
            self.experiments._grid(self.experiments.active)
        run.assert_called_once()
        report=self.experiments.get(self.ident)
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['rows'][1]['status'],'pending')
        self.assertIsNone(self.jobs.reservation)
        self.assertIsNone(self.experiments.active)
        self.assertEqual(report['storage_failure']['id'],'b'*32)

    def test_scheduler_status_remains_readable_without_storage(self):
        service=object.__new__(AppService);service.jobs=self.jobs
        self.jobs.latch_storage_failure(self.ident,'run')
        with patch.object(self.store,'connect',side_effect=sqlite3.OperationalError('unavailable')):
            response=service.handle({'version':1,'id':'test','command':'scheduler_status','params':{}})
        self.assertEqual(response['type'],'result',response)
        self.assertEqual(response['result']['storage_failure']['id'],self.ident)
        self.assertIsNone(response['result']['active'])
        self.assertIsNone(response['result']['reservation'])
        self.jobs.reservation='c'*32
        self.assertEqual(self.jobs.scheduler_status()['reservation'],'c'*32)
        self.jobs.reservation=None


class MigrationArtifactTraversalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=RunStore(self.tmp.name)
        raw=b'{"independent_fixture":true}'
        with self.store.connect() as db:
            for i in range(101):
                ident=f'{i:032x}';directory=self.store.directory(ident);directory.mkdir(parents=True)
                (directory/'result.json').write_bytes(raw)
                db.execute('INSERT INTO runs VALUES(?,?,?,?,NULL,?,NULL)',
                           (ident,'2026-01-01T00:00:00+00:00','completed','{}',hashlib.sha256(raw).hexdigest()))

    def test_checks_all_101_results_in_bounded_pages_and_detects_oldest_corruption(self):
        with patch.object(self.store,'history_page',wraps=self.store.history_page) as page, \
             patch.object(self.store,'result',wraps=self.store.result) as result:
            self.assertEqual(verify_results(self.store),101)
        self.assertEqual(page.call_count,2)
        self.assertTrue(all(call.kwargs['limit']==100 for call in page.call_args_list))
        self.assertEqual(result.call_count,101)
        self.assertEqual(result.call_args_list[-1].args[0],'0'*32)
        (self.store.directory('0'*32)/'result.json').write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):verify_results(self.store)

    def test_count_guard_rejects_truncated_history(self):
        with patch.object(self.store,'history_page',return_value={'rows':[],'next':None}):
            with self.assertRaisesRegex(RuntimeError,'count mismatch'):verify_results(self.store)

    def test_zero_completed_results_is_valid(self):
        with self.store.connect() as db:db.execute("UPDATE runs SET status='failed'")
        self.assertEqual(verify_results(self.store),0)


if __name__=='__main__':unittest.main()
