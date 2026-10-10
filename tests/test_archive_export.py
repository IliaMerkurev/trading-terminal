"""Independent export identities, publication cutoff and bounded HTTP transfer."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from terminal.archive_export import ExportManager,execute,CHUNK_BYTES,MAX_OPERATIONS
from terminal.archives import read_archive
from terminal.data import canonical
from terminal.jobs import JobManager
from terminal.service import AppService
from tests.archive_receipt_fixtures import documents,sentinels


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=AppService(self.root/'workspace');self.addCleanup(self.service.close)
        self.manager=self.service.exports;self.project,self.docs=documents(1);self.run,_=sentinels(self.service.store)
    def start(self,**changes):
        args={'request_id':uuid.uuid4().hex,'strategy':self.project['strategy'],'profile':self.project['profile'],'run_ids':[self.run]};args.update(changes)
        return self.manager.start(**args)
    def wait(self,ident):
        deadline=time.monotonic()+8
        while self.manager.active and time.monotonic()<deadline:time.sleep(.02)
        self.assertIsNone(self.manager.active);return self.manager.status(ident)
    def prepared(self,**changes):
        with patch.object(self.manager,'_launch') as launch:receipt=self.start(**changes)
        record,work,owner=launch.call_args.args
        return record,work,owner
    def execute(self,record):
        execute({'root':str(self.service.store.root),'session':self.manager.session,'export_id':record['export_id'],'request_sha256':record['frozen_sha256']})
    def publish(self,record,work):
        self.execute(record);self.manager._publish(record,work);self.service.jobs.reservation=None
        return self.manager.status(record['export_id'])
    def test_real_process_duplicate_and_exact_roundtrip_preserve_store(self):
        before={p:p.read_bytes() for p in (self.service.store.root/'runs').glob('*/*.json')}
        key=uuid.uuid4().hex;first=self.start(request_id=key)
        second=self.start(request_id=key);self.assertEqual(first['export_id'],second['export_id'])
        result=self.wait(key);self.assertEqual(result['status'],'completed',result)
        descriptor=result['descriptor'];raw=b''.join(self.manager.chunk(key,descriptor['filename'],offset,min(CHUNK_BYTES,descriptor['bytes']-offset)) for offset in range(0,descriptor['bytes'],CHUNK_BYTES))
        self.assertEqual(hashlib.sha256(raw).hexdigest(),descriptor['sha256'])
        project,docs=read_archive(raw);self.assertEqual(project['strategy'],self.project['strategy'])
        self.assertEqual(docs[f'runs/{self.run}/snapshot.json'],self.docs['runs/'+self.project['runs'][0]+'/snapshot.json'])
        self.assertEqual(docs[f'runs/{self.run}/result.json'],self.docs['runs/'+self.project['runs'][0]+'/result.json'])
        self.assertEqual(self.start(request_id=key),result);self.assertEqual(len(list(self.manager.directory.glob('*.zip'))),1)
        for path,value in before.items():self.assertEqual(path.read_bytes(),value)
        with self.service.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM native_trust').fetchone()[0],0)
        self.assertEqual(self.manager.cancel(key)['status'],'too_late')
    def test_request_conflicts_capacity_and_frozen_inputs(self):
        strategy=copy.deepcopy(self.project['strategy']);record,work,_=self.prepared(strategy=strategy)
        strategy['name']='Changed after start';frozen=json.loads((work/'request.json').read_bytes());self.assertNotEqual(frozen['strategy']['name'],strategy['name'])
        with self.assertRaisesRegex(ValueError,'reused'):self.start(request_id=record['export_id'],strategy=strategy)
        with patch('terminal.archive_export.MAX_OPERATIONS',1):
            with self.assertRaisesRegex(ValueError,'history is full'):self.start()
            self.assertEqual(self.start(request_id=record['export_id'])['export_id'],record['export_id'])
        self.service.jobs.reservation=None
    def test_frozen_request_checksum_rejects_disk_substitution(self):
        record,work,_=self.prepared();path=work/'request.json';frozen=json.loads(path.read_bytes());frozen['strategy']['name']='Replaced request';path.write_bytes(canonical(frozen))
        with self.assertRaisesRegex(ValueError,'request checksum'):self.execute(record)
        self.assertIsNone(record['descriptor']);self.service.jobs.reservation=None
    def test_intermediate_and_final_chunk_offsets_have_independent_hashes(self):
        from terminal.archive_export import NOTE,identity
        ident=uuid.uuid4().hex;raw=bytes(range(256))*(CHUNK_BYTES//256+1)+b'last'
        path=self.manager.directory/(ident+'.ttproject.zip');path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
        descriptor={'export_id':ident,'filename':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'chunk_bytes':CHUNK_BYTES,'chunk_sha256':[hashlib.sha256(raw[:CHUNK_BYTES]).hexdigest(),hashlib.sha256(raw[CHUNK_BYTES:]).hexdigest()],'history_included':False,'note':NOTE}
        self.manager.records[ident]={'status':'completed','descriptor':descriptor,'file_identity':identity(path.stat())}
        self.assertEqual(self.manager.chunk(ident,path.name,0,CHUNK_BYTES),raw[:CHUNK_BYTES])
        self.assertEqual(self.manager.chunk(ident,path.name,CHUNK_BYTES,len(raw)-CHUNK_BYTES),raw[CHUNK_BYTES:])
        with self.assertRaises(ValueError):self.manager.chunk(ident,path.name,CHUNK_BYTES,CHUNK_BYTES)
    def test_source_mutations_after_freeze_reject(self):
        for field in ('artifact','result_hash','manifest','symlink'):
            with self.subTest(field=field):
                source=self.service.store.directory(self.run)/'result.json';original=source.read_bytes()
                with self.service.store.connect() as db:row=dict(db.execute('SELECT * FROM runs WHERE id=?',(self.run,)).fetchone())
                record,_,_=self.prepared()
                try:
                    if field=='artifact':source.write_bytes(original.replace(b'1000',b'1001'))
                    elif field=='symlink':source.unlink();target=source.with_name('copy.json');target.write_bytes(original);source.symlink_to(target)
                    else:
                        with self.service.store.connect() as db:
                            if field=='result_hash':db.execute('UPDATE runs SET result_hash=? WHERE id=?',('a'*64,self.run))
                            else:
                                manifest=json.loads(row['manifest']);manifest['dataset']['source']='Changed source';db.execute('UPDATE runs SET manifest=? WHERE id=?',(canonical(manifest).decode(),self.run))
                    with self.assertRaises(ValueError):self.execute(record)
                    self.assertEqual(list(self.manager.directory.glob('*.zip')),[])
                finally:
                    if source.is_symlink():source.unlink()
                    source.write_bytes(original)
                    with self.service.store.connect() as db:db.execute('UPDATE runs SET result_hash=?,manifest=? WHERE id=?',(row['result_hash'],row['manifest'],self.run))
                    self.service.jobs.reservation=None
    def test_privacy_rejection_and_zero_eight_run_bounds(self):
        strategy=copy.deepcopy(self.project['strategy']);strategy['name']='Research /home/private-user/report'
        record,_,_=self.prepared(strategy=strategy)
        with self.assertRaisesRegex(ValueError,'local path'):self.execute(record)
        self.service.jobs.reservation=None
        for count in (0,8):
            ids=[]
            for _ in range(count):ident,_=sentinels(self.service.store);ids.append(ident)
            record,work,_=self.prepared(run_ids=ids);result=self.publish(record,work)
            project,docs=read_archive((self.manager.directory/result['descriptor']['filename']).read_bytes())
            self.assertEqual(project['runs'],ids);self.assertEqual(len(docs),1+2*count)
        with self.assertRaisesRegex(ValueError,'eight'):self.start(run_ids=ids+[self.run])
    def test_publication_cancels_before_cutoff_and_completion_wins_after(self):
        receipt=self.start();ident=receipt['export_id'];response=self.manager.cancel(ident)
        self.assertEqual(response['status'],'cancel_requested')
        result=self.wait(ident);self.assertEqual(result['status'],'cancelled');self.assertIsNone(result['descriptor']);self.assertIsNone(self.service.jobs.reservation)
        with self.assertRaises(ValueError):self.manager.chunk(ident,ident+'.ttproject.zip',0,1)
        next_id=self.start()['export_id'];self.assertEqual(self.wait(next_id)['status'],'completed');self.assertEqual(self.manager.cancel(next_id)['status'],'too_late')
    def test_pre_and_post_publication_failures_never_invent_grant_or_erase_completion(self):
        for after in (False,True):
            publish=self.manager._publish
            def fault(*args):
                if after:publish(*args)
                raise OSError('synthetic publication fault')
            with patch.object(self.manager,'_publish',side_effect=fault):
                ident=self.start()['export_id'];result=self.wait(ident)
            self.assertEqual(result['status'],'completed' if after else 'failed')
            self.assertEqual(bool(result['descriptor']),after)
    def test_stage_change_and_existing_destination_are_never_published(self):
        for changed in ('bytes','target','symlink'):
            record,work,_=self.prepared();self.execute(record);stage=work/'archive.partial';target=self.manager.directory/(record['export_id']+'.ttproject.zip')
            if changed=='bytes':raw=stage.read_bytes();stage.write_bytes(bytes([raw[0]^1])+raw[1:])
            elif changed=='target':target.write_bytes(b'prior user file')
            else:stage.unlink();stage.symlink_to(self.service.store.directory(self.run)/'result.json')
            with self.assertRaises((ValueError,FileExistsError)):self.manager._publish(record,work)
            self.assertIsNone(record['descriptor'])
            if changed=='target':self.assertEqual(target.read_bytes(),b'prior user file')
            self.service.jobs.reservation=None
    def test_chunk_validation_and_identity_substitution(self):
        ident=self.start()['export_id'];d=self.wait(ident)['descriptor'];args=dict(export_id=ident,filename=d['filename'],offset=0,size=d['bytes'])
        for change in ({'export_id':'0'*32},{'filename':'../private'},{'filename':'1'*32+'.ttproject.zip'},{'offset':-1},{'offset':True},{'offset':1},{'offset':d['bytes']},{'size':True},{'size':1.0},{'size':d['bytes']+1}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.manager.chunk(**(args|change))
        path=self.manager.directory/d['filename'];raw=path.read_bytes();stamp=path.stat()
        path.write_bytes(bytes([raw[0]^1])+raw[1:]);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        with self.assertRaises(ValueError):self.manager.chunk(**args)
        path.unlink();path.write_bytes(raw)
        with self.assertRaises(ValueError):self.manager.chunk(**args)
        path.unlink();target=path.with_suffix('.copy');target.write_bytes(raw);path.symlink_to(target)
        with self.assertRaises(ValueError):self.manager.chunk(**args)
    def test_chunk_hash_catches_same_fingerprint_mismatch(self):
        ident=self.start()['export_id'];d=self.wait(ident)['descriptor'];record=self.manager.records[ident];record['descriptor']['chunk_sha256'][0]='a'*64
        with self.assertRaisesRegex(ValueError,'checksum'):self.manager.chunk(ident,d['filename'],0,d['bytes'])
    def test_bootstrap_failure_and_cleanup_exception_keep_monitor_and_ownership(self):
        from unittest.mock import Mock
        import io
        gate=threading.Event();entered=threading.Event()
        class Input(io.BytesIO):
            def write(self,_):raise BrokenPipeError('synthetic bootstrap failure')
        process=Mock();process.stdin=Input();process.poll.side_effect=lambda:1 if gate.is_set() else None;process.returncode=1
        def wait(timeout=None):
            entered.set()
            if not gate.wait(timeout):raise __import__('subprocess').TimeoutExpired('synthetic worker',timeout)
            return 1
        process.wait.side_effect=wait
        job=Mock();job.popen_options.return_value={};job.close.side_effect=[OSError('synthetic cleanup failure'),None]
        with patch('terminal.archive_export.worker_job',return_value=job),patch('terminal.archive_export.subprocess.Popen',return_value=process):
            try:
                with self.assertRaises(OSError):self.start()
                self.assertTrue(entered.wait(2));active=self.manager.active;ident=active['record']['export_id']
                self.assertTrue(active['monitor'].is_alive());self.assertTrue(process.stdin.closed)
                self.assertEqual(self.service.jobs.reservation,'export:'+ident)
                self.assertEqual(self.manager.status(ident)['status'],'running')
            finally:gate.set()
            self.assertEqual(self.wait(ident)['status'],'failed');self.assertIsNone(self.service.jobs.reservation)
    def test_anchor_cleanup_retry_preserves_committed_completion(self):
        from unittest.mock import Mock
        record,work,owner=self.prepared();self.execute(record)
        process=Mock();process.poll.return_value=0;process.returncode=0
        anchor=Mock();anchor.close.side_effect=[OSError('synthetic anchor close failure'),None]
        active={'record':record,'work':work,'owner':owner,'process':process,'job':Mock(),'anchor':anchor}
        active['monitor']=threading.Thread(target=self.manager._monitor,args=(active,));self.manager.active=active;active['monitor'].start();active['monitor'].join(5)
        self.assertFalse(active['monitor'].is_alive());self.assertIs(self.manager.active,active)
        before=self.manager.status(record['export_id']);self.assertEqual(before['status'],'completed');self.assertIsNotNone(before['descriptor'])
        self.manager.close();after=self.manager.status(record['export_id'])
        self.assertEqual(after['status'],'completed');self.assertEqual(after['descriptor'],before['descriptor']);self.assertIsNone(after['error']);self.assertIsNone(self.manager.active);self.assertIsNone(self.service.jobs.reservation)
    def test_stage_unlink_failure_has_no_grant_and_does_not_promote_on_restart(self):
        record,work,_=self.prepared();self.execute(record);unlink=Path.unlink
        def fault(path,*args,**kwargs):
            if path==work/'archive.partial':raise OSError('synthetic unlink failure')
            return unlink(path,*args,**kwargs)
        with patch.object(Path,'unlink',new=fault),self.assertRaises(OSError):self.manager._publish(record,work)
        self.assertIsNone(record['descriptor']);self.assertTrue((self.manager.directory/(record['export_id']+'.ttproject.zip')).is_file());self.service.jobs.reservation=None
        with self.assertRaises(ValueError):self.manager.chunk(record['export_id'],record['export_id']+'.ttproject.zip',0,1)
    @unittest.skipUnless(os.name=='posix','Linux owner-death acceptance')
    def test_owner_death_retains_lock_until_reaping_then_discards_session(self):
        import subprocess,sys
        root=self.root/'crash';process=subprocess.Popen([sys.executable,'-m','tests.archive_export_crash_probe',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);supervisor=None
        try:
            ready=root/'probe-ready.json';deadline=time.monotonic()+8
            while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(ready.exists());data=json.loads(ready.read_text());supervisor=data['supervisor_pid'];process.kill();process.wait(timeout=5)
            with self.assertRaisesRegex(ValueError,'already owns'):JobManager(root)
            os.kill(supervisor,signal.SIGCONT);supervisor=None;restored=None;deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                try:restored=AppService(root);break
                except ValueError:time.sleep(.02)
            self.assertIsNotNone(restored)
            try:
                self.assertEqual(restored.exports.recent(),[]);self.assertIsNone(restored.exports.active);self.assertIsNone(restored.jobs.reservation)
                with self.assertRaises(ValueError):restored.exports.status(data['export_id'])
                self.assertEqual(list((root/'exports').glob('*.zip')),[])
            finally:restored.close()
        finally:
            if supervisor:os.kill(supervisor,signal.SIGCONT)
            if process.poll() is None:process.kill();process.wait(timeout=5)
            process.stderr.close()
    def test_close_and_restart_revoke_grants_without_deleting_completed_zip(self):
        ident=self.start()['export_id'];d=self.wait(ident)['descriptor'];path=self.manager.directory/d['filename'];before=path.read_bytes()
        self.start();self.service.close()
        self.assertIsNone(self.manager.active)
        with self.assertRaises(ValueError):self.manager.chunk(ident,d['filename'],0,d['bytes'])
        restored=AppService(self.service.store.root)
        try:
            self.assertEqual(restored.exports.recent(),[]);self.assertIsNone(restored.jobs.reservation);self.assertEqual(path.read_bytes(),before)
            with self.assertRaises(ValueError):restored.exports.status(ident)
        finally:restored.close()


@unittest.skipUnless(os.name=='posix','Linux supervisor barrier')
class ExportHttpTests(unittest.TestCase):
    def test_real_http_lost_response_barrier_status_write_cancel_and_restart(self):
        from terminal.browser_host import BrowserServer,BrowserHandler
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dist=root/'dist';dist.mkdir();(dist/'index.html').write_text('synthetic')
            server=BrowserServer(root/'workspace',dist);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01});thread.start()
            headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':server.token}
            def call(command,params={}):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);began=time.monotonic()
                try:
                    conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params}),headers);value=json.loads(conn.getresponse().read());self.assertLess(time.monotonic()-began,2);return value
                finally:conn.close()
            manager=server.service.exports;launch=manager._launch;supervisor=None;project,_=documents();ident=uuid.uuid4().hex
            def barrier(*args):
                nonlocal supervisor
                with patch('terminal.archive_export.worker_job',side_effect=paused_job):launch(*args)
            from terminal.process_lifecycle import worker_job
            def paused_job(*args):
                job=worker_job(*args);assign=job.assign
                def pause(process):
                    nonlocal supervisor
                    assign(process);supervisor=process.pid;os.kill(supervisor,signal.SIGSTOP)
                job.assign=pause;return job
            original_reply=BrowserHandler.reply
            def drop(handler,status,body,*args,**kwargs):
                if handler.path=='/api/request' and json.loads(body).get('id')=='archive_export_start':handler.close_connection=True;return
                return original_reply(handler,status,body,*args,**kwargs)
            try:
                params={'request_id':ident,'strategy':project['strategy'],'profile':project['profile'],'run_ids':[]}
                with patch.object(manager,'_launch',side_effect=barrier),patch.object(BrowserHandler,'reply',new=drop):
                    with self.assertRaises(http.client.RemoteDisconnected):call('archive_export_start',params)
                self.assertEqual(call('archive_export_start',params)['result']['export_id'],ident)
                self.assertEqual(call('scheduler_status')['result']['reservation'],'export:'+ident)
                self.assertEqual(call('archive_export_status',{'export_id':ident})['result']['status'],'running')
                self.assertEqual(call('save_graph',{'name':'Foreground writer','graph':project['strategy']['document']['graph'],'layout':{},'strategy_id':None,'profile':project['profile']})['type'],'result')
                self.assertEqual(call('archive_export_cancel',{'export_id':ident})['result']['status'],'cancel_requested')
                self.assertEqual(call('archive_export_status',{'export_id':ident})['result']['status'],'cancel_requested')
                self.assertEqual(call('scheduler_status')['result']['reservation'],'export:'+ident)
                began=time.monotonic();os.kill(supervisor,signal.SIGCONT);supervisor=None
                while manager.active and time.monotonic()-began<5:time.sleep(.02)
                self.assertIsNone(manager.active);self.assertLess(time.monotonic()-began,5)
                self.assertEqual(call('archive_export_status',{'export_id':ident})['result']['status'],'cancelled')
                self.assertEqual(call('archive_export',{'strategy':project['strategy'],'profile':project['profile'],'run_ids':[]})['type'],'error')
            finally:
                if supervisor:os.kill(supervisor,signal.SIGCONT)
                server.shutdown();thread.join();server.server_close()
