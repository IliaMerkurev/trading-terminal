"""Independent async import ownership, immutable continuation and visibility gates."""
import base64
import hashlib
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from terminal.archive_execution import execute, settle, Conflict, publish_run
from terminal.archives import ArchiveManager, CHUNK
from terminal.data import canonical
from terminal.jobs import JobManager
from terminal.storage import SERIES
from tests.archive_receipt_fixtures import archive, sentinels


class AsyncImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.jobs=JobManager(self.root);self.manager=ArchiveManager(self.jobs.store,self.jobs)
        self.addCleanup(self.close)
        self.raw,self.project,self.docs=archive();self.before=sentinels(self.jobs.store)
    def close(self):
        self.manager.close();self.jobs.close()
    def upload(self):
        op=self.manager.begin(len(self.raw))['operation_id']
        for i in range(0,len(self.raw),CHUNK):self.manager.append(op,i,base64.b64encode(self.raw[i:i+CHUNK]).decode())
        return op
    def cancel(self,op):
        return self.manager.cancel(op,self.manager.status(op)['execution']['attempt_key'])
    def wait(self,op):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            result=self.manager.status(op)
            if result['execution']['state']=='terminal' and self.manager.worker.active is None:return result
            time.sleep(.02)
        self.fail('Worker did not settle')
    def claim(self,op,revision=None,key=None):
        with patch.object(self.manager.worker,'_launch'):
            return self.manager.start(op) if key is None else self.manager.resume(op,revision,key)
    def run_inline(self,op,*,reason='worker_interrupted'):
        record=self.manager.status(op)
        try:execute({'root':str(self.root),'operation_id':op,'attempt_key':record['execution']['attempt_key']})
        finally:
            settle(self.jobs.store,op,reason)
            self.jobs.reservation=None
    def assert_output(self,op):
        status=self.manager.status(op);self.assertEqual(status['outcome'],'completed')
        for item in status['items']:
            if item['kind']!='run':continue
            source=item['source_run_id'];ident=item['destination_id'];expected=self.docs[f'runs/{source}/result.json']
            self.assertEqual((self.jobs.store.directory(ident)/'result.json').read_bytes(),canonical(expected))
            for kind in SERIES:
                self.assertEqual(self.jobs.store.page(ident,kind,0,100)['rows'],expected[kind])
        with self.jobs.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM native_trust').fetchone()[0],0)
        self.assertEqual(len(self.jobs.store.recent()),3);self.assertEqual(len(self.jobs.store.strategies()),2)
        return [item['destination_id'] for item in status['items']]
    def test_process_start_lost_reply_repeat_and_terminal_noop(self):
        op=self.upload();start=self.manager.start(op)
        self.assertEqual(self.manager.start(op)['execution']['attempt_key'],start['execution']['attempt_key'])
        self.wait(op);ids=self.assert_output(op)
        self.assertEqual(self.manager.start(op)['revision'],1)
        self.assertEqual([i['destination_id'] for i in self.manager.resume(op,0,uuid.uuid4().hex)['items']],ids)
    def test_partial_legacy_resume_same_ids_and_repeated_key(self):
        op=self.upload();self.manager.receipts.claim(op);self.manager.receipts.reserve(op,self.raw,self.project,self.docs)
        source=self.project['runs'][0]
        self.manager.receipts.publish_run(op,0,self.docs[f'runs/{source}/snapshot.json'],self.docs[f'runs/{source}/result.json'])
        self.manager.receipts.stop(op,'process_restart');self.manager.upload=None
        ids=[i['destination_id'] for i in self.manager.status(op)['items']];key=uuid.uuid4().hex
        result=self.manager.resume(op,0,key);self.manager.resume(op,0,key);self.wait(op)
        self.assertEqual(self.assert_output(op),ids)
        self.assertEqual(self.manager.resume(op,0,key)['revision'],1)
    def test_staged_rows_hidden_and_explicit_continuation_checks_every_value(self):
        op=self.upload();self.claim(op)
        original=publish_run
        def interrupt(store,operation,key,item,snapshot,result,*args):
            if item['ordinal']==1:raise OSError('simulated interruption')
            return original(store,operation,key,item,snapshot,result,*args)
        with patch('terminal.archive_execution.publish_run',side_effect=interrupt),self.assertRaises(OSError):self.run_inline(op)
        before=self.manager.status(op);self.assertEqual(before['outcome'],'partial')
        pending=next(i for i in before['items'] if i['kind']=='run' and i['ordinal']==1)
        with self.jobs.store.connect() as db:db.execute('INSERT INTO series VALUES(?,?,?,?)',(pending['destination_id'],'equity',0,canonical(self.docs[f"runs/{pending['source_run_id']}/result.json"]['equity'][0]).decode()))
        with self.assertRaises(ValueError):self.jobs.store.page(pending['destination_id'],'equity',0,10)
        key=uuid.uuid4().hex;self.manager.resume(op,1,key);self.wait(op)
        self.assertEqual(self.assert_output(op),[i['destination_id'] for i in before['items']])
    def test_changed_published_artifact_blocks_all_continuation(self):
        op=self.upload();self.claim(op)
        def interrupt(*args):
            if args[3]['ordinal']==1:raise Conflict('interruption')
            return publish_run(*args)
        with patch('terminal.archive_execution.publish_run',side_effect=interrupt),self.assertRaises(Conflict):self.run_inline(op)
        before=self.manager.status(op);first=next(i for i in before['items'] if i['kind']=='run' and i['ordinal']==0)
        path=self.jobs.store.directory(first['destination_id'])/'result.json';path.write_bytes(b'changed')
        self.manager.resume(op,1,uuid.uuid4().hex);result=self.wait(op)
        self.assertEqual(result['outcome'],'partial');self.assertEqual(result['execution']['termination_reason'],'input_conflict');self.assertEqual(path.read_bytes(),b'changed')
        self.assertEqual(len(self.jobs.store.strategies()),1)
    def test_cancel_reaped_then_same_id_resume(self):
        op=self.upload();self.manager.start(op);response=self.cancel(op)
        self.assertEqual(response['status'],'cancel_requested');cancelled=self.wait(op)
        self.assertEqual(cancelled['outcome'],'cancelled');self.assertIsNotNone(cancelled['execution']['cancel_acknowledged_at'])
        self.assertIsNone(self.jobs.reservation)
        self.manager.resume(op,1,uuid.uuid4().hex);self.wait(op);self.assert_output(op)
    def test_concurrent_start_and_resume_have_one_claim(self):
        op=self.upload();results=[]
        with patch.object(self.manager.worker,'_launch') as launch:
            threads=[threading.Thread(target=lambda:results.append(self.manager.start(op))) for _ in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(launch.call_count,1)
        self.run_inline(op);self.assertEqual(len({r['execution']['attempt_key'] for r in results}),1);self.assert_output(op)
    def test_missing_original_exact_recovery_upload(self):
        op=self.upload();self.claim(op)
        self.manager.receipts.reserve(op,self.raw,self.project,self.docs)
        settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        (self.root/'imports'/f'{op}.partial').unlink()
        recovery=self.manager.recovery_begin(op,len(self.raw))
        self.manager.append(recovery['upload_id'],0,base64.b64encode(self.raw).decode());self.manager.recovery_finish(recovery['upload_id'])
        self.manager.resume(op,1,uuid.uuid4().hex);self.wait(op);self.assert_output(op)
    def test_restart_never_promotes_staged_files(self):
        op=self.upload();self.claim(op);self.manager.receipts.reserve(op,self.raw,self.project,self.docs)
        ids=[i['destination_id'] for i in self.manager.status(op)['items']]
        self.jobs.reservation=None;self.close();self.jobs=JobManager(self.root);self.manager=ArchiveManager(self.jobs.store,self.jobs)
        result=self.manager.status(op);self.assertEqual(result['outcome'],'interrupted');self.assertEqual(result['execution']['state'],'terminal');self.assertEqual([i['destination_id'] for i in result['items']],ids)
        self.manager.resume(op,1,uuid.uuid4().hex);self.wait(op);self.assertEqual(self.assert_output(op),ids)

    @unittest.skipUnless(os.name=='posix' and Path('/proc').exists(),'Linux supervisor barrier')
    def test_real_http_status_and_cancel_return_before_worker_barrier_release(self):
        import http.client,json
        from terminal.browser_host import BrowserServer
        dist=self.root/'dist';dist.mkdir();(dist/'index.html').write_text('<title>Fixture</title>')
        server=BrowserServer(self.root/'http-workspace',dist);thread=threading.Thread(target=server.serve_forever);thread.start()
        supervisor=None
        def call(command,params):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params}),headers)
                return json.loads(conn.getresponse().read())['result']
            finally:conn.close()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            conn.request('GET','/api/session',headers={'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1'})
            token=json.loads(conn.getresponse().read())['token'];conn.close()
            headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':token}
            op=call('archive_begin',{'size':len(self.raw)})['operation_id'];call('archive_append',{'upload_id':op,'offset':0,'data':base64.b64encode(self.raw).decode()})
            worker=server.service.archives.worker;launch=worker._launch
            def barrier(*args):
                nonlocal supervisor
                launch(*args);supervisor=worker.active['process'].pid;os.kill(supervisor,signal.SIGSTOP)
            with patch.object(worker,'_launch',side_effect=barrier):
                started=time.monotonic();ack=call('archive_import_start',{'operation_id':op});self.assertLess(time.monotonic()-started,2)
            # Deterministic slow-write injection: a separate SQLite owner holds
            # the write slot for 250 ms while the HTTP requests are issued.
            locked=threading.Event()
            def slow_storage():
                with server.service.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE');locked.set();time.sleep(.25)
            slow=threading.Thread(target=slow_storage);slow.start();self.assertTrue(locked.wait(2))
            replies={};latencies={}
            def request(name,command,params):
                started=time.monotonic();replies[name]=call(command,params);latencies[name]=time.monotonic()-started
            threads=[threading.Thread(target=request,args=('status','archive_import_status',{'operation_id':op})),threading.Thread(target=request,args=('cancel','archive_import_cancel',{'operation_id':op,'attempt_key':ack['execution']['attempt_key']})),threading.Thread(target=request,args=('write','save_graph',{'name':'Ordinary write','graph':self.project['strategy']['document']['graph'],'layout':{},'strategy_id':None,'profile':self.project['profile']}))]
            for t in threads:t.start()
            for t in threads:t.join(3)
            slow.join(2)
            self.assertEqual(set(replies),{'status','cancel','write'});self.assertGreater(max(latencies.values()),.15);self.assertLess(max(latencies.values()),2)
            self.assertEqual(replies['cancel']['status'],'cancel_requested');self.assertEqual(worker.active['process'].poll(),None)
            self.assertIsNotNone(server.service.jobs.reservation)
            released=time.monotonic();os.kill(supervisor,signal.SIGCONT);supervisor=None
            while worker.active and time.monotonic()-released<5:time.sleep(.02)
            self.assertIsNone(worker.active);self.assertLess(time.monotonic()-released,5)
            terminal=call('archive_import_status',{'operation_id':op});self.assertEqual(terminal['outcome'],'cancelled')
        finally:
            if supervisor:os.kill(supervisor,signal.SIGCONT)
            server.shutdown();thread.join(10);server.server_close()

    def test_old_resume_key_acknowledges_original_attempt_after_new_attempt(self):
        op=self.upload();self.claim(op);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        first=uuid.uuid4().hex;self.claim(op,1,first);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        second=uuid.uuid4().hex;self.claim(op,2,second)
        reply=self.manager.resume(op,1,first)
        self.assertEqual(reply['acknowledged_attempt']['attempt_key'],first);self.assertEqual(reply['execution']['attempt_key'],second)
        self.run_inline(op);self.assert_output(op)

    def test_concurrent_different_resume_keys_have_one_revision_winner(self):
        op=self.upload();self.claim(op);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        responses=[];errors=[]
        def resume():
            try:responses.append(self.manager.resume(op,1,uuid.uuid4().hex))
            except ValueError as exc:errors.append(str(exc))
        with patch.object(self.manager.worker,'_launch') as launch:
            threads=[threading.Thread(target=resume) for _ in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(launch.call_count,1);self.assertEqual(len(responses),1);self.assertEqual(len(errors),3)
        self.run_inline(op);self.assert_output(op)

    def test_changed_staged_row_and_unknown_kind_refuse_without_overwrite(self):
        for kind,value in [('equity','{"equity":"999","time_ns":60000000000}'),('foreign','{}')]:
            with self.subTest(kind=kind):
                op=self.upload();self.claim(op);self.manager.receipts.reserve(op,self.raw,self.project,self.docs)
                pending=next(i for i in self.manager.status(op)['items'] if i['kind']=='run')
                with self.jobs.store.connect() as db:db.execute('INSERT INTO series VALUES(?,?,?,?)',(pending['destination_id'],kind,0,value))
                settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
                self.manager.resume(op,1,uuid.uuid4().hex);result=self.wait(op)
                self.assertEqual(result['execution']['termination_reason'],'input_conflict')
                with self.jobs.store.connect() as db:self.assertEqual(db.execute('SELECT value FROM series WHERE run_id=?',(pending['destination_id'],)).fetchone()[0],value)
                self.assertEqual(len(self.jobs.store.strategies()),1)

    def test_zero_run_archive_and_completed_cancellation_cutoff(self):
        self.raw,self.project,self.docs=archive(0);op=self.upload();self.manager.start(op);result=self.wait(op)
        self.assertEqual(result['outcome'],'completed');self.assertEqual(len(result['items']),1)
        self.assertEqual(self.cancel(op)['status'],'too_late');self.assertEqual(self.manager.status(op)['outcome'],'completed')

    def test_failed_bootstrap_keeps_process_owned_until_reaped(self):
        from unittest.mock import Mock
        import io
        gate=threading.Event();entered=threading.Event()
        class Input(io.BytesIO):
            def write(self,_):raise BrokenPipeError('test bootstrap failure')
        process=Mock();process.stdin=Input();process.poll.side_effect=lambda:0 if gate.is_set() else None
        def wait():entered.set();gate.wait(5);return 1
        process.wait.side_effect=wait
        job=Mock();job.popen_options.return_value={}
        op=self.upload()
        with patch('terminal.archive_execution.worker_job',return_value=job),patch('terminal.archive_execution.subprocess.Popen',return_value=process):
            try:
                with self.assertRaises(BrokenPipeError):self.manager.start(op)
                self.assertTrue(entered.wait(2));self.assertIsNotNone(self.manager.worker.active);self.assertEqual(self.jobs.reservation,'archive:'+op)
                self.assertNotEqual(self.manager.status(op)['execution']['state'],'terminal')
            finally:gate.set()
            result=self.wait(op);self.assertEqual(result['outcome'],'failed');self.assertIsNone(self.jobs.reservation)

    def test_storage_failure_is_latched_even_if_cancel_claim_wins_at_reaping(self):
        from unittest.mock import Mock
        op=self.upload();record=self.claim(op)
        with self.jobs.store.connect() as db:db.execute("UPDATE archive_execution SET termination_reason='storage_failure' WHERE operation_id=?",(op,))
        self.cancel(op)
        active={'operation_id':op,'key':record['execution']['attempt_key'],'process':Mock(),'job':Mock(),'anchor':Mock(),'owner':'archive:'+op}
        self.manager.worker.active=active;self.manager.worker._monitor(active)
        self.assertIsNotNone(self.jobs.storage_failure)
        with self.assertRaisesRegex(ValueError,'blocked'):self.manager.resume(op,record['revision'],uuid.uuid4().hex)

    def test_recovery_upload_cancellation_retains_original_receipt(self):
        op=self.upload();self.claim(op);self.manager.receipts.reserve(op,self.raw,self.project,self.docs)
        settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        (self.root/'imports'/f'{op}.partial').unlink();before=self.manager.status(op)
        transfer=self.manager.recovery_begin(op,len(self.raw));self.manager.append(transfer['upload_id'],0,base64.b64encode(self.raw[:20]).decode())
        self.assertEqual(self.manager.recovery_cancel(transfer['upload_id'])['status'],'cancelled')
        self.assertEqual(self.manager.status(op),before);self.assertIsNone(self.manager.upload)
        self.manager.recovery_begin(op,len(self.raw))

    def test_closed_copy_preserves_all_prior_rows_files_and_attempts(self):
        import shutil,sqlite3
        op=self.upload();self.manager.start(op);self.wait(op);self.assert_output(op)
        self.close()
        from tests.test_archive_receipt_backup import files
        before_files=files(self.root)
        with sqlite3.connect(self.root/'terminal.sqlite3') as db:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            rows={name:list(db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')) for name in tables}
        copy=self.root.parent/(self.root.name+'-copy');self.addCleanup(lambda:shutil.rmtree(copy));shutil.copytree(self.root,copy)
        restored=JobManager(copy)
        try:
            with restored.store.connect() as db:
                for name in tables:self.assertEqual([tuple(r) for r in db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')],rows[name])
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(files(copy),before_files)
        finally:restored.close()


    def test_cancel_for_prior_attempt_cannot_stop_continuation(self):
        op=self.upload();initial=self.claim(op);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        latest=self.claim(op,1,uuid.uuid4().hex)
        self.assertEqual(self.manager.cancel(op,initial['execution']['attempt_key'])['status'],'stale_attempt')
        self.assertEqual(self.manager.status(op)['execution']['state'],'running')
        self.run_inline(op);self.assert_output(op)

    def test_pre_extension_full_copy_adds_only_empty_companion_tables(self):
        import shutil,sqlite3
        self.close()
        with sqlite3.connect(self.root/'terminal.sqlite3') as db:
            for table in ('archive_execution','archive_attempts','archive_recovery_sources'):db.execute('DROP TABLE '+table)
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            before={name:list(db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')) for name in names}
        copy=self.root.parent/(self.root.name+'-legacy');self.addCleanup(lambda:shutil.rmtree(copy));shutil.copytree(self.root,copy)
        restored=JobManager(copy)
        try:
            with restored.store.connect() as db:
                for name in names:self.assertEqual([tuple(r) for r in db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')],before[name])
                for name in ('archive_execution','archive_attempts','archive_recovery_sources'):self.assertEqual(db.execute('SELECT count(*) FROM '+name).fetchone()[0],0)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        finally:restored.close()

    def test_resume_preserves_another_receiving_upload(self):
        op=self.upload();self.claim(op);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        other=self.manager.begin(len(self.raw));upload=self.manager.upload
        with self.assertRaisesRegex(ValueError,'receiving transfer'):self.manager.resume(op,1,uuid.uuid4().hex)
        self.assertIs(self.manager.upload,upload);self.assertEqual(upload['id'],other['operation_id'])


    def test_failed_resume_claim_preserves_prior_attempt_metadata(self):
        from tests.test_archive_receipts import transaction_fault
        import sqlite3
        op=self.upload();first=self.claim(op);settle(self.jobs.store,op,'process_restart');self.jobs.reservation=None
        before=self.manager.status(op)
        with transaction_fault(self.jobs.store,'INSERT INTO archive_attempts'),self.assertRaises(sqlite3.OperationalError):self.manager.resume(op,1,uuid.uuid4().hex)
        after=self.manager.status(op)
        self.assertEqual(after['execution'],before['execution']);self.assertEqual(after['attempts'],before['attempts'])
        self.assertIsNotNone(self.jobs.storage_failure);self.assertIsNone(self.jobs.reservation)


    def test_invalid_source_is_rejected_without_destinations_or_trust(self):
        self.raw=b'not an archive';op=self.upload();self.manager.start(op);result=self.wait(op)
        self.assertEqual(result['outcome'],'rejected');self.assertEqual(result['items'],[])
        self.assertEqual(result['execution']['termination_reason'],'validation_rejected')
        self.assertEqual(len(self.jobs.store.recent()),1)

    def test_each_run_boundary_recovers_without_extra_ids_or_rewriting_prior_runs(self):
        for ordinal,after in [(0,False),(0,True),(1,False),(1,True)]:
            with self.subTest(ordinal=ordinal,after=after):
                op=self.upload();self.claim(op)
                def fault(*args):
                    if args[3]['ordinal']==ordinal and not after:raise Conflict('before publication')
                    result=publish_run(*args)
                    if args[3]['ordinal']==ordinal and after:raise Conflict('after publication')
                    return result
                with patch('terminal.archive_execution.publish_run',side_effect=fault),self.assertRaises(Conflict):self.run_inline(op)
                status=self.manager.status(op);ids=[item['destination_id'] for item in status['items']]
                prior={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'runs').glob('*/*.json')}
                self.manager.resume(op,1,uuid.uuid4().hex);result=self.wait(op)
                self.assertEqual(result['outcome'],'completed');self.assertEqual([item['destination_id'] for item in result['items']],ids)
                for path,value in prior.items():self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),value)
                for item in result['items']:
                    if item['kind']=='run':self.assertEqual(self.jobs.store.page(item['destination_id'],'equity',0,10)['rows'],self.docs[f"runs/{item['source_run_id']}/result.json"]['equity'])

    @unittest.skipUnless(os.name=='posix','Linux owner-death acceptance')
    def test_service_death_retains_workspace_until_supervisor_reaps_then_no_auto_resume(self):
        import subprocess,sys,json
        crash_root=self.root/'crash-workspace'
        process=subprocess.Popen([sys.executable,'-m','tests.archive_async_crash_probe',str(crash_root)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        supervisor=None
        try:
            deadline=time.monotonic()+8;ready=crash_root/'probe-ready.json'
            while not ready.exists() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(ready.exists());data=json.loads(ready.read_text());supervisor=data['supervisor_pid']
            process.kill();process.wait(timeout=5)
            with self.assertRaisesRegex(ValueError,'already owns'):JobManager(crash_root)
            os.kill(supervisor,signal.SIGCONT);supervisor=None
            restored=None;deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                try:restored=JobManager(crash_root);break
                except ValueError:time.sleep(.02)
            self.assertIsNotNone(restored)
            manager=ArchiveManager(restored.store,restored)
            try:
                receipt=manager.status(data['operation_id']);self.assertEqual(receipt['outcome'],'interrupted');self.assertEqual(receipt['items'],[])
                self.assertIsNone(manager.worker.active);self.assertEqual(restored.store.recent(),[])
                manager.resume(data['operation_id'],1,uuid.uuid4().hex)
                deadline=time.monotonic()+8
                while manager.worker.active and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(manager.status(data['operation_id'])['outcome'],'completed')
            finally:manager.close();restored.close()
        finally:
            if supervisor:os.kill(supervisor,signal.SIGCONT)
            if process.poll() is None:process.kill();process.wait(timeout=5)
            process.stderr.close()

    def test_final_strategy_commit_faults_preserve_partial_or_completed_truth(self):
        from contextlib import contextmanager
        import sqlite3
        from terminal.storage import RunStore
        for after in (False,True):
            with self.subTest(after_commit=after):
                op=self.upload();self.claim(op);original=RunStore.connect
                class Proxy:
                    def __init__(self,db):self.db=db;self.hit=False
                    def execute(self,sql,*args):
                        if sql.startswith("UPDATE archive_imports SET phase='terminal',outcome='completed'"):
                            self.hit=True
                            if not after:raise sqlite3.OperationalError('before final commit')
                        return self.db.execute(sql,*args)
                    def __getattr__(self,name):return getattr(self.db,name)
                @contextmanager
                def faulty(store):
                    with original(store) as db:
                        proxy=Proxy(db);yield proxy
                    if proxy.hit and after:raise sqlite3.OperationalError('after final commit')
                with patch.object(RunStore,'connect',faulty),self.assertRaises(sqlite3.OperationalError):self.run_inline(op)
                status=self.manager.status(op);ids=[i['destination_id'] for i in status['items']]
                self.assertEqual(status['outcome'],'completed' if after else 'partial')
                if not after:
                    self.manager.resume(op,1,uuid.uuid4().hex);status=self.wait(op)
                else:self.manager.start(op)
                self.assertEqual(status['outcome'],'completed');self.assertEqual([i['destination_id'] for i in status['items']],ids)

    def test_cancellation_before_strategy_publication_retains_all_reports(self):
        op=self.upload();record=self.claim(op);entered=threading.Event();release=threading.Event();errors=[]
        def barrier(*args):
            result=publish_run(*args)
            if args[3]['ordinal']==1:entered.set();release.wait(5)
            return result
        def run():
            try:self.run_inline(op,reason='user_cancelled')
            except Exception as exc:errors.append(exc)
        with patch('terminal.archive_execution.publish_run',side_effect=barrier):
            thread=threading.Thread(target=run);thread.start()
            try:
                self.assertTrue(entered.wait(3));self.assertEqual(self.cancel(op)['status'],'cancel_requested')
                self.assertEqual(len(self.jobs.store.strategies()),1)
            finally:release.set();thread.join(5)
        self.assertEqual(errors,[]);status=self.manager.status(op);self.assertEqual(status['outcome'],'partial')
        self.assertEqual(sum(i['publication_state']=='published' for i in status['items']),2)
        self.manager.resume(op,1,uuid.uuid4().hex);self.wait(op);self.assert_output(op)
