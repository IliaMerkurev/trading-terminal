"""Independent local publication, mutation, cancellation and restore gates."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock,patch
import uuid

from terminal import result_finalization as f
from terminal.data import canonical
from terminal.jobs import JobManager
from terminal.storage import RunStore
from tests.archive_receipt_fixtures import documents,sentinels
from tests.test_archive_receipt_backup import copy_closed,files,tables,check_database


def fixture(store, count=350):
    project,docs=documents(1);source=project['runs'][0]
    snapshot=docs[f'runs/{source}/snapshot.json'];result=docs[f'runs/{source}/result.json']
    result['indicators']=[{'time':60*(i+1),'values':{'independent':i-37}} for i in range(count)]
    ident=store.create(snapshot);generation=uuid.uuid4().hex
    with store.connect() as db:f.register(db,ident,generation,snapshot['snapshot_sha256'])
    store.status(ident,'running')
    (store.directory(ident)/'worker-result.json').write_bytes(canonical(result))
    return ident,generation,result


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=RunStore(self.tmp.name)

    def test_exact_hash_rows_provenance_and_bounded_receipts(self):
        ident,key,result=fixture(self.store);f.claim(self.store,ident,key)
        phases=[]
        def checkpoint(phase):
            phases.append(phase)
            if phase!='committed':
                with self.assertRaises(ValueError):self.store.result(ident)
                with self.assertRaises(ValueError):self.store.page(ident,'indicators')
        f.finalize(self.store,ident,key,checkpoint)
        self.assertEqual(f.settle(self.store,ident,key),'completed')
        self.assertEqual(self.store.result(ident),result)
        self.assertEqual(self.store.get(ident)['result_hash'],hashlib.sha256(canonical(result)).hexdigest())
        self.assertEqual(self.store.get(ident)['summary']['origin'],'local')
        self.assertEqual(self.store.page(ident,'indicators',0,1000)['rows'],result['indicators'])
        with self.store.connect() as db:
            receipts=db.execute('SELECT * FROM local_finalization_batches').fetchall()
            self.assertTrue(all(r['row_count']<=f.BATCH_ROWS and r['encoded_bytes']<=f.BATCH_BYTES for r in receipts))
        self.assertIn('batch:3',phases);self.assertIn('verified',phases)

    def test_old_valid_nonobject_and_oversized_rows_remain_valid(self):
        ident,key,result=fixture(self.store,0)
        result['indicators']=[list(range(60000)),9,None]
        (self.store.directory(ident)/'worker-result.json').write_bytes(canonical(result))
        f.claim(self.store,ident,key);f.finalize(self.store,ident,key);f.settle(self.store,ident,key)
        self.assertEqual(self.store.result(ident),result)
        with self.store.connect() as db:
            large=db.execute('SELECT row_count,encoded_bytes FROM local_finalization_batches WHERE encoded_bytes>?',(f.BATCH_BYTES,)).fetchall()
        self.assertEqual(len(large),1);self.assertEqual(large[0]['row_count'],1)
        self.assertEqual(f.status(self.store,ident)['oversized_rows'],1)

    def test_cancel_at_each_stage_never_exposes_success_and_reaps_before_settlement(self):
        for phase in ('decoding','artifact','artifact_written','batch:1','batch:2','batch:3','verified'):
            with self.subTest(phase=phase):
                ident,key,result=fixture(self.store);f.claim(self.store,ident,key)
                def checkpoint(current):
                    if current==phase:self.assertEqual(f.cancel(self.store,ident,key),'cancel_requested')
                with self.assertRaises(f.Stopped):f.finalize(self.store,ident,key,checkpoint)
                self.assertEqual(self.store.get(ident)['status'],'cancel_requested')
                with self.assertRaises(ValueError):self.store.result(ident)
                self.assertEqual(f.settle(self.store,ident,key),'cancelled')

    def test_completed_wins_cancellation_and_postcommit_failure(self):
        ident,key,result=fixture(self.store);f.claim(self.store,ident,key)
        def fault(phase):
            if phase=='committed':raise OSError('postcommit fault')
        with self.assertRaises(OSError):f.finalize(self.store,ident,key,fault)
        self.assertEqual(f.cancel(self.store,ident,key),'too_late')
        self.assertEqual(f.settle(self.store,ident,key,code=f.STORAGE_EXIT),'completed')
        self.assertEqual(self.store.result(ident),result)

    def test_independent_verification_detects_content_order_counts_and_receipt_damage(self):
        changes=["UPDATE series SET value='{}' WHERE kind='equity'", "DELETE FROM series WHERE kind='equity'", "UPDATE series SET row_index=row_index+99 WHERE kind='equity'", "INSERT INTO series SELECT run_id,'foreign',0,'{}' FROM series LIMIT 1", "UPDATE local_finalization_batches SET content_hash='changed' WHERE ordinal=0"]
        for sql in changes:
            with self.subTest(sql=sql):
                ident,key,_=fixture(self.store);f.claim(self.store,ident,key)
                def fault(phase):
                    if phase=='verifying':
                        with self.store.connect() as db:
                            if sql.startswith('INSERT INTO series SELECT'):db.execute("INSERT INTO series VALUES(?,'foreign',0,'{}')",(ident,))
                            else:db.execute(sql)
                with self.assertRaisesRegex(ValueError,'changed|Unexpected'):f.finalize(self.store,ident,key,fault)
                self.assertNotEqual(self.store.get(ident)['status'],'completed')

    def test_epoch_rejects_mutation_after_verification_including_row_relocation_and_receipts(self):
        for kind in ('value','move','receipt'):
            with self.subTest(kind=kind):
                ident,key,_=fixture(self.store);other,otherkey,_=fixture(self.store);f.claim(self.store,ident,key)
                def fault(phase):
                    if phase=='verified':
                        with self.store.connect() as db:
                            if kind=='value':db.execute("UPDATE series SET value='{}' WHERE run_id=? AND kind='equity'",(ident,))
                            elif kind=='move':db.execute("UPDATE series SET run_id=? WHERE run_id=? AND kind='equity'",(other,ident))
                            else:db.execute('DELETE FROM local_finalization_batches WHERE run_id=? AND ordinal=0',(ident,))
                with self.assertRaisesRegex(ValueError,'after verification'):f.finalize(self.store,ident,key,fault)
                if kind=='move':
                    with self.store.connect() as db:self.assertGreater(db.execute('SELECT mutation_epoch FROM local_finalization WHERE run_id=?',(other,)).fetchone()[0],0)

    def test_orphan_foreign_generation_and_preexisting_content_are_rejected(self):
        ident,key,result=fixture(self.store)
        with self.assertRaisesRegex(ValueError,'ownership'):f.claim(self.store,ident,'f'*32)
        with self.store.connect() as db:db.execute('DELETE FROM local_finalization WHERE run_id=?',(ident,))
        with self.assertRaisesRegex(ValueError,'ownership'):f.claim(self.store,ident,key)
        ident,key,result=fixture(self.store)
        (self.store.directory(ident)/'result.json').write_bytes(canonical(result))
        with self.assertRaisesRegex(ValueError,'Unexpected result artifact'):f.claim(self.store,ident,key)
        ident,key,result=fixture(self.store)
        with self.store.connect() as db:db.execute('INSERT INTO series VALUES(?,?,?,?)',(ident,'equity',0,'{}'))
        with self.assertRaisesRegex(ValueError,'Unexpected staged'):f.claim(self.store,ident,key)

    def test_imported_reservation_cannot_acquire_local_provenance(self):
        ident,key,result=fixture(self.store)
        with self.store.connect() as db:
            db.execute("INSERT INTO archive_import_items(operation_id,kind,ordinal,destination_id,source_run_id,expected_snapshot_sha256,expected_result_sha256,expected_series_counts,publication_state,reserved_at) VALUES(?,'run',0,?,?,?,?,?,'reserved','fixture')",('b'*32,ident,'c'*32,'d'*64,'e'*64,'{}'))
        with self.assertRaisesRegex(ValueError,'imported destination'):f.claim(self.store,ident,key)
        self.assertIsNone(self.store.get(ident)['summary'])

    def test_populated_controls_and_receipts_restore_without_upgrade(self):
        source=self.store.root/'populated';jobs=JobManager(source);sentinels(jobs.store)
        import base64
        from terminal.archives import ArchiveManager
        from tests.archive_receipt_fixtures import archive
        imports=ArchiveManager(jobs.store,jobs);raw,_,_=archive(1)
        operation=imports.begin(len(raw))['operation_id'];imports.append(operation,0,base64.b64encode(raw).decode());imports.start(operation)
        deadline=time.monotonic()+8
        while imports.worker.active and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(imports.status(operation)['outcome'],'completed');imports.close()
        completed,key,result=fixture(jobs.store);f.claim(jobs.store,completed,key);f.finalize(jobs.store,completed,key);f.settle(jobs.store,completed,key)
        partial,pkey,_=fixture(jobs.store);f.claim(jobs.store,partial,pkey)
        with self.assertRaises(OSError):f.finalize(jobs.store,partial,pkey,lambda phase:(_ for _ in ()).throw(OSError('fixture stop')) if phase=='batch:1' else None)
        jobs.close();before=tables(source);artifacts=files(source);destination=self.store.root/'populated-copy';copy_closed(source,destination)
        reopened=JobManager(destination)
        try:
            self.assertEqual(reopened.store.result(completed),result)
            self.assertEqual(reopened.store.get(partial)['status'],'interrupted')
            after=tables(destination)
            for name in before:
                if name not in ('runs','local_finalization'):self.assertEqual(before[name],after[name])
            self.assertEqual(files(destination),artifacts);check_database(reopened.store)
            with reopened.store.connect() as db:
                self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'local_%'").fetchone()[0],6)
                self.assertEqual(db.execute('SELECT count(*) FROM native_trust').fetchone()[0],0)
        finally:reopened.close()
        stable=tables(destination);reopened=JobManager(destination);reopened.close();self.assertEqual(tables(destination),stable)

    def test_storage_exit_survives_failed_error_marker(self):
        ident,key,_=fixture(self.store);f.claim(self.store,ident,key)
        request={'root':str(self.store.root),'run_id':ident,'generation':key}
        with patch.object(f,'finalize',side_effect=OSError('disk full')),patch.object(RunStore,'connect',side_effect=sqlite3.OperationalError('read only')):
            self.assertEqual(f.execute(request),f.STORAGE_EXIT)

    def test_restart_interrupts_without_promoting_or_retrying(self):
        ident,key,_=fixture(self.store);f.claim(self.store,ident,key)
        with self.assertRaises(OSError):
            f.finalize(self.store,ident,key,lambda phase:(_ for _ in ()).throw(OSError('stop')) if phase=='batch:1' else None)
        before=files(self.store.root)
        jobs=JobManager(self.store.root)
        try:
            self.assertEqual(jobs.status(ident)['status'],'interrupted')
            self.assertEqual(jobs.status(ident)['finalization']['phase'],'interrupted')
            self.assertIsNone(jobs.active);self.assertEqual(files(self.store.root),{**before,'instance.lock':hashlib.sha256(b'0').hexdigest()})
        finally:jobs.close()

    def test_additive_closed_copy_preserves_historical_imported_tables_and_files(self):
        source=self.store.root/'source';jobs=JobManager(source);sentinels(jobs.store);jobs.close()
        with sqlite3.connect(source/'terminal.sqlite3') as db:
            for name in ('local_series_insert','local_series_delete','local_series_update','local_batch_insert','local_batch_delete','local_batch_update'):db.execute('DROP TRIGGER '+name)
            db.execute('DROP TABLE local_finalization_batches');db.execute('DROP TABLE local_finalization')
        before=tables(source);artifacts=files(source);dest=self.store.root/'restored';copy_closed(source,dest)
        for _ in range(2):
            jobs=JobManager(dest)
            try:
                check_database(jobs.store);after=tables(dest)
                self.assertEqual({k:after[k] for k in before},before)
                self.assertEqual(set(after)-set(before),{'local_finalization','local_finalization_batches'})
            finally:jobs.close()
            self.assertEqual(files(dest),artifacts)


class ManagedFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.jobs=JobManager(self.tmp.name);self.addCleanup(self.jobs.close)
    def active(self):
        ident,key,result=fixture(self.jobs.store)
        process=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0))
        active={'id':ident,'generation':key,'process':process,'job':Mock(),'cancelled':False}
        monitor=threading.Thread(target=self.jobs._monitor,args=(ident,process,active['job'],Mock(is_alive=Mock(return_value=False))),daemon=True)
        active['monitor']=monitor;self.jobs.active=active
        return ident,key,result,active

    def test_same_monitor_waits_through_managed_completion_and_cleanup(self):
        ident,key,result,active=self.active();active['monitor'].start();active['monitor'].join(10)
        self.assertFalse(active['monitor'].is_alive());self.assertIsNone(self.jobs.active)
        self.assertEqual(self.jobs.store.result(ident),result)
        self.assertFalse(self.jobs.status(ident)['worker_active'])

    @unittest.skipUnless(os.name=='posix','Linux supervisor gate')
    def test_status_cancel_and_foreground_write_remain_responsive_during_stopped_finalizer(self):
        ident,key,result,active=self.active();original=subprocess.Popen;ready=threading.Event();pid=[]
        def stopped(*args,**kwargs):
            process=original(*args,**kwargs);os.kill(process.pid,signal.SIGSTOP);pid.append(process.pid);ready.set();return process
        try:
            with patch('terminal.jobs.subprocess.Popen',side_effect=stopped):
                active['monitor'].start();self.assertTrue(ready.wait(5))
                began=time.monotonic();self.assertEqual(self.jobs.status(ident)['status'],'finalizing')
                self.assertEqual(self.jobs.scheduler_status()['active']['id'],ident)
                with self.jobs.store.connect() as db:db.execute("INSERT INTO strategies(id,name,kind,document,updated_at) VALUES(?,'ordinary','graph','{}','now')",('e'*32,))
                self.assertEqual(self.jobs.cancel(ident)['status'],'cancel_requested')
                self.assertLess(time.monotonic()-began,2)
                self.assertTrue(active['monitor'].is_alive());self.assertIs(self.jobs.active,active)
                self.assertEqual(self.jobs.store.get(ident)['status'],'cancel_requested')
                began=time.monotonic();os.kill(pid.pop(),signal.SIGCONT);active['monitor'].join(5)
                self.assertFalse(active['monitor'].is_alive());self.assertLess(time.monotonic()-began,5)
                self.assertEqual(self.jobs.status(ident)['status'],'cancelled')
        finally:
            if pid:os.kill(pid[0],signal.SIGCONT)
            active['monitor'].join(8)

    @unittest.skipUnless(os.name=='posix','Serialized HTTP Linux finalizer gate')
    def test_http_status_cancel_and_writer_before_stalled_finalizer_release(self):
        import http.client
        from terminal.browser_host import BrowserServer
        root=Path(self.tmp.name)/'http';dist=root/'dist';dist.mkdir(parents=True);(dist/'index.html').write_text('<title>Fixture</title>')
        server=BrowserServer(root/'workspace',dist);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01});thread.start()
        jobs=server.service.jobs;ident,key,result=fixture(jobs.store);project,_=documents(1)
        process=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0));active={'id':ident,'generation':key,'process':process,'job':Mock(),'cancelled':False}
        monitor=threading.Thread(target=jobs._monitor,args=(ident,process,active['job'],Mock(is_alive=Mock(return_value=False))),daemon=True);active['monitor']=monitor;jobs.active=active
        ready=threading.Event();pids=[];original=subprocess.Popen
        headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':server.token}
        def call(command,params):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params}),headers)
                value=json.loads(conn.getresponse().read());self.assertEqual(value['type'],'result',value);return value['result']
            finally:conn.close()
        def stopped(*args,**kwargs):
            child=original(*args,**kwargs);os.kill(child.pid,signal.SIGSTOP);pids.append(child.pid);ready.set();return child
        try:
            with patch('terminal.jobs.subprocess.Popen',side_effect=stopped):
                monitor.start();self.assertTrue(ready.wait(5))
                locked=threading.Event()
                def hold():
                    with jobs.store.connect() as db:db.execute('BEGIN IMMEDIATE');locked.set();time.sleep(.25)
                holder=threading.Thread(target=hold);holder.start();self.assertTrue(locked.wait(2))
                latencies=[];replies={}
                def invoke(command,params):
                    start=time.monotonic();replies[command]=call(command,params);latencies.append(time.monotonic()-start)
                requests=[threading.Thread(target=invoke,args=('run_status',{'run_id':ident})),threading.Thread(target=invoke,args=('cancel_run',{'run_id':ident})),threading.Thread(target=invoke,args=('save_graph',{'name':'Foreground fixture','graph':project['strategy']['document']['graph'],'layout':{},'strategy_id':None,'profile':project['profile']}))]
                for request in requests:request.start()
                for request in requests:request.join(3)
                holder.join(2);self.assertEqual(len(replies),3);self.assertLess(max(latencies),2)
                self.assertEqual(replies['cancel_run']['status'],'cancel_requested');self.assertIs(jobs.active,active);self.assertTrue(monitor.is_alive())
                tick=time.monotonic();os.kill(pids.pop(),signal.SIGCONT);monitor.join(5)
                self.assertFalse(monitor.is_alive());self.assertLess(time.monotonic()-tick,5)
                self.measurement={'request_seconds':latencies,'quiescence_after_forced_release_seconds':time.monotonic()-tick,'forced_stall_retained_ownership':True}
                self.assertEqual(call('run_status',{'run_id':ident})['status'],'cancelled')
        finally:
            if pids:os.kill(pids[0],signal.SIGCONT)
            monitor.join(8);server.shutdown();thread.join(10);server.server_close()

    def test_cleanup_failure_retains_ownership_and_quarantine(self):
        ident,key,result,active=self.active();active['job'].close.side_effect=OSError('cleanup failed')
        active['monitor'].start();active['monitor'].join(5)
        self.assertIs(self.jobs.active,active);self.assertIsNotNone(self.jobs.storage_diagnostic())
        with self.assertRaises(ExceptionGroup):self.jobs.close()
        active['job'].close.side_effect=None;self.jobs.active=None

    def test_cancel_during_go_broken_pipe_is_not_storage_failure(self):
        ident,key,result,active=self.active();candidate=Mock(wait=Mock(return_value=130),poll=Mock(return_value=130))
        candidate.stdin.closed=False;job=Mock();job.popen_options.return_value={}
        def broken(data):
            self.jobs.cancel(ident)
            raise BrokenPipeError('cancelled during bootstrap')
        candidate.stdin.write.side_effect=broken
        with patch('terminal.jobs.worker_job',return_value=job),patch('terminal.jobs.subprocess.Popen',return_value=candidate):
            active['monitor'].start();active['monitor'].join(5)
        self.assertIsNone(self.jobs.storage_diagnostic());self.assertIsNone(self.jobs.active)
        self.assertEqual(self.jobs.store.get(ident)['status'],'cancelled')
        job.close.assert_called();candidate.wait.assert_called()

    def test_durable_storage_fault_survives_cancellation_exit_code(self):
        ident,key,result,active=self.active();active['cancelled']=True
        with self.jobs.store.connect() as db:
            db.execute("UPDATE local_finalization SET state='cancel_requested',phase='staging',error_code='storage_failure' WHERE run_id=?",(ident,))
            db.execute("UPDATE runs SET status='cancel_requested' WHERE id=?",(ident,))
        active['process'].wait.return_value=130
        active['monitor'].start();active['monitor'].join(5)
        self.assertIsNotNone(self.jobs.storage_diagnostic());self.assertIsNone(self.jobs.active)
        self.assertEqual(self.jobs.store.get(ident)['status'],'cancel_requested')

    def test_failed_cancel_persistence_never_attempts_fallback_terminal_writes(self):
        ident,key,result,active=self.active()
        with patch.object(f,'cancel',side_effect=sqlite3.OperationalError('read only')) as cancel,patch.object(f,'settle') as settle:
            with self.assertRaises(sqlite3.OperationalError):self.jobs.cancel(ident)
            active['monitor'].start();active['monitor'].join(5)
            cancel.assert_called_once();settle.assert_not_called()
        self.assertIsNotNone(self.jobs.storage_diagnostic());self.assertIsNone(self.jobs.active)
        self.assertEqual(self.jobs.store.get(ident)['status'],'running')

    def test_busy_cancel_is_bounded_requested_overlay_then_durable_after_reaping(self):
        ident,key,result,active=self.active();locked=threading.Event();release=threading.Event()
        def hold():
            with self.jobs.store.connect() as db:
                db.execute('BEGIN IMMEDIATE');locked.set();release.wait(5)
        holder=threading.Thread(target=hold);holder.start();self.assertTrue(locked.wait(2))
        try:
            began=time.monotonic();self.assertEqual(self.jobs.cancel(ident)['status'],'cancel_requested')
            self.assertLess(time.monotonic()-began,1)
            self.assertEqual(self.jobs.status(ident)['status'],'cancel_requested')
            self.assertEqual(self.jobs.status(ident)['durable_status'],'running')
            self.assertIsNone(self.jobs.storage_diagnostic());self.assertIs(self.jobs.active,active)
        finally:release.set();holder.join(5)
        active['monitor'].start();active['monitor'].join(5)
        self.assertEqual(self.jobs.status(ident)['status'],'cancelled');self.assertIsNone(self.jobs.active)

    @unittest.skipUnless(os.name=='posix','Managed Linux fault process')
    def test_real_finalizer_postcommit_exit_and_marker_cancel_keep_completed_and_quarantine(self):
        for mode in ('postcommit','marker_cancel'):
            with self.subTest(mode=mode):
                if self.jobs.storage_failure:self.jobs.close();self.jobs=JobManager(self.tmp.name);self.addCleanup(self.jobs.close)
                ident,key,result,active=self.active();control=Path(self.tmp.name)/mode;control.mkdir()
                original=subprocess.Popen
                def launch(args,**kwargs):return original([args[0],'-m','tests.finalization_worker_probe',mode,str(control)],**kwargs)
                with patch('terminal.jobs.subprocess.Popen',side_effect=launch):
                    active['monitor'].start()
                    if mode=='marker_cancel':
                        deadline=time.monotonic()+8
                        while not (control/'ready').exists() and time.monotonic()<deadline:time.sleep(.01)
                        self.assertTrue((control/'ready').exists())
                        # Completed wins, so this low-level kill models service
                        # cleanup arriving after storage-marker persistence.
                        self.assertEqual(self.jobs.cancel(ident)['status'],'too_late')
                        active['job'].terminate()
                    active['monitor'].join(8)
                self.assertFalse(active['monitor'].is_alive());self.assertIsNone(self.jobs.active)
                self.assertIsNotNone(self.jobs.storage_diagnostic());self.assertEqual(self.jobs.store.result(ident),result)

    @unittest.skipUnless(os.name=='posix','Managed Linux write-stall process')
    def test_real_write_owner_is_killed_before_deferred_cancel_settles(self):
        ident,key,result,active=self.active();control=Path(self.tmp.name)/'write-stall';control.mkdir();original=subprocess.Popen
        def launch(args,**kwargs):return original([args[0],'-m','tests.finalization_worker_probe','write_stall',str(control)],**kwargs)
        try:
            with patch('terminal.jobs.subprocess.Popen',side_effect=launch):
                active['monitor'].start();deadline=time.monotonic()+8
                while not (control/'ready').exists() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue((control/'ready').exists())
                began=time.monotonic();self.assertEqual(self.jobs.cancel(ident)['status'],'cancel_requested')
                acknowledgement=time.monotonic()-began;self.assertLess(acknowledgement,1)
                active['monitor'].join(5);self.assertFalse(active['monitor'].is_alive())
                self.measurement={'cancel_acknowledgement_seconds':acknowledgement,'cancel_to_quiescence_seconds':time.monotonic()-began,'write_owner_killed':True}
                self.assertLess(time.monotonic()-began,5)
            self.assertEqual(self.jobs.status(ident)['status'],'cancelled');self.assertIsNone(self.jobs.storage_diagnostic())
        finally:
            (control/'release').touch();active['job'].terminate();active['monitor'].join(8)

    def test_postcommit_fault_is_completed_and_quarantined(self):
        ident,key,result,active=self.active();f.claim(self.jobs.store,ident,key);f.finalize(self.jobs.store,ident,key)
        with patch.object(f,'claim',side_effect=OSError('hidden completed commit')):
            active['monitor'].start();active['monitor'].join(5)
        self.assertEqual(self.jobs.store.result(ident),result)
        self.assertIsNotNone(self.jobs.storage_diagnostic());self.assertIsNone(self.jobs.active)


if __name__=='__main__':unittest.main()
