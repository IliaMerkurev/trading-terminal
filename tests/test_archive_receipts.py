"""Receipt transaction/fault proof on disposable, independently authored workspaces."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from terminal.archive_receipts import ArchiveReceipts
from terminal.data import canonical, digest
from terminal.jobs import JobManager
from terminal.storage import RunStore, SERIES
from tests.archive_receipt_fixtures import archive, sentinels


@contextmanager
def transaction_fault(store, sql_prefix, *, after_commit=False, after_rows=False):
    original = store.connect
    class Connection:
        def __init__(self,db):self.db=db;self.hit=False
        def execute(self,sql,*args):
            if sql.startswith(sql_prefix):
                self.hit=True
                if not after_commit:raise sqlite3.OperationalError('private failure text')
            return self.db.execute(sql,*args)
        def executemany(self,sql,rows):
            rows=list(rows)
            if after_rows and sql.startswith(sql_prefix) and len(rows)>=2:
                self.hit=True
                iterator=iter(rows)
                self.db.execute(sql,next(iterator));self.db.execute(sql,next(iterator))
                raise sqlite3.OperationalError('private row failure')
            return self.db.executemany(sql,rows)
        def __getattr__(self,name):return getattr(self.db,name)
    @contextmanager
    def connect():
        with original() as db:
            proxy=Connection(db);yield proxy
        if proxy.hit and after_commit:raise sqlite3.OperationalError('private postcommit failure')
    with patch.object(store,'connect',connect):yield


class ReceiptStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=RunStore(self.root/'workspace');self.ledger=ArchiveReceipts(self.store)
        self.sentinel_run,self.sentinel_strategy=sentinels(self.store)
        self.before=self.prior()
        self.raw,self.project,self.docs=archive();self.op='a'*32
        self.ledger.begin(self.op,len(self.raw));self.ledger.claim(self.op)

    def prior(self):
        return {'run':self.store.get(self.sentinel_run),'strategy':self.store.strategy(self.sentinel_strategy),
            'files':{p.name:p.read_bytes() for p in self.store.directory(self.sentinel_run).iterdir()}}

    def reserve(self):self.ledger.reserve(self.op,self.raw,self.project,self.docs)
    def publish(self,index=0):
        source=self.project['runs'][index]
        self.ledger.publish_run(self.op,index,self.docs[f'runs/{source}/snapshot.json'],self.docs[f'runs/{source}/result.json'])
    def finish(self):self.ledger.publish_strategy(self.op,self.project['strategy'],self.project['profile'])
    def items(self):return self.ledger.status(self.op)['items']
    def assert_prior(self):self.assertEqual(self.prior(),self.before)

    def test_reservations_are_complete_before_any_output_file(self):
        self.reserve();items=self.items()
        self.assertEqual(len(items),3);self.assertEqual(len(self.store.recent()),3)
        self.assertEqual([i['source_run_id'] for i in items if i['kind']=='run'],self.project['runs'])
        for item in items:self.assertFalse(self.store.directory(item['destination_id']).exists())
        self.assertEqual(len(self.store.strategies()),1)
        self.assertNotEqual(items[0]['expected_snapshot_sha256'],self.docs[f"runs/{self.project['runs'][0]}/snapshot.json"]['snapshot_sha256'])
        self.assertNotEqual(items[0]['expected_result_sha256'],items[1]['expected_result_sha256'])
        self.assert_prior()

    def test_reservation_rolls_back_all_rows_then_postcommit_is_inspectable(self):
        with transaction_fault(self.store,'UPDATE archive_imports SET archive_sha256='),self.assertRaises(sqlite3.OperationalError):self.reserve()
        self.assertEqual(self.items(),[]);self.assertEqual(len(self.store.recent()),1)
        with transaction_fault(self.store,'UPDATE archive_imports SET archive_sha256=',after_commit=True),self.assertRaises(sqlite3.OperationalError):self.reserve()
        self.assertEqual(len(self.items()),3);self.assertEqual(self.ledger.status(self.op)['phase'],'publishing')
        self.assert_prior()

    def test_duplicate_existing_row_and_orphan_collisions_fail_without_adoption(self):
        for ids in ([self.sentinel_run,'b'*32,'c'*32],['b'*32,'b'*32,'c'*32],['d'*32,'e'*32,self.sentinel_strategy],['0'*32,'b'*32,'c'*32]):
            self.store.directory('0'*32).mkdir(exist_ok=True)
            (self.store.directory('0'*32)/'snapshot.json').write_bytes(b'legacy orphan')
            with patch('terminal.archive_receipts.uuid.uuid4',side_effect=[type('ID',(),{'hex':i})() for i in ids]),self.assertRaises(ValueError):self.reserve()
            self.assertEqual(self.items(),[]);self.assertEqual(len(self.store.recent()),1)
        self.assertEqual((self.store.directory('0'*32)/'snapshot.json').read_bytes(),b'legacy orphan');self.assert_prior()

    def test_file_and_series_failures_never_publish_and_keep_all_ids(self):
        self.reserve()
        from terminal.data import write_new
        calls=[]
        def second_file(path,data):
            calls.append(path.name)
            if path.name=='result.json':raise OSError('private')
            write_new(path,data)
        with patch('terminal.archive_receipts.write_new',side_effect=second_file),self.assertRaises(OSError):self.publish()
        self.assertEqual(calls,['snapshot.json','result.json']);self.assertEqual(self.items()[0]['publication_state'],'writing')
        self.ledger.stop(self.op,'storage_failure')
        self.assertEqual(self.ledger.status(self.op)['outcome'],'failed');self.assertEqual(self.items()[0]['publication_state'],'incomplete')
        self.assertEqual(len(self.items()),3);self.assert_prior()

    def test_series_rollback_includes_run_and_receipt_then_postcommit_is_joint(self):
        self.reserve()
        with transaction_fault(self.store,'INSERT INTO series',after_rows=True),self.assertRaises(sqlite3.OperationalError):self.publish()
        item=self.items()[0]
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM series WHERE run_id=?',(item['destination_id'],)).fetchone()[0],0)
        self.assertEqual(self.store.get(item['destination_id'])['status'],'importing');self.assertEqual(item['publication_state'],'writing')
        # A separate reservation is necessary: failed publication is not retryable.
        self.op='b'*32;self.ledger.begin(self.op,len(self.raw));self.ledger.claim(self.op);self.reserve()
        with transaction_fault(self.store,"UPDATE archive_import_items SET publication_state='published'",after_commit=True),self.assertRaises(sqlite3.OperationalError):self.publish()
        item=self.items()[0]
        self.assertEqual(item['publication_state'],'published');self.assertEqual(self.store.get(item['destination_id'])['status'],'completed')
        self.assertEqual(self.store.result(item['destination_id'])['metrics']['net_pnl'],'0')
        self.assertEqual(self.items()[1]['publication_state'],'reserved');self.assert_prior()

    def test_strategy_terminal_atomicity_and_postcommit_failure_cannot_downgrade(self):
        self.reserve();self.publish(0);self.publish(1)
        with transaction_fault(self.store,"UPDATE archive_imports SET phase='terminal',outcome='completed'"),self.assertRaises(sqlite3.OperationalError):self.finish()
        self.assertEqual(len(self.store.strategies()),1);self.assertEqual(self.items()[2]['publication_state'],'reserved')
        with transaction_fault(self.store,"UPDATE archive_imports SET phase='terminal',outcome='completed'",after_commit=True),self.assertRaises(sqlite3.OperationalError):self.finish()
        self.ledger.stop(self.op,'storage_failure')
        self.assertEqual(self.ledger.status(self.op)['outcome'],'completed');self.assertEqual(len(self.store.strategies()),2)
        self.assertTrue(all(i['publication_state']=='published' for i in self.items()));self.assert_prior()

    def test_strategy_collision_after_reservation_is_insert_only(self):
        self.reserve();self.publish(0);self.publish(1)
        ident=self.items()[2]['destination_id']
        self.store.save_strategy('Concurrent saved value','graph',{},strategy_id=ident)
        with self.assertRaises(sqlite3.IntegrityError):self.finish()
        self.ledger.stop(self.op,'storage_failure')
        self.assertEqual(self.ledger.status(self.op)['outcome'],'partial')
        self.assertEqual(self.store.strategy(ident)['name'],'Concurrent saved value');self.assert_prior()

    def test_inspection_is_read_only_and_strategy_edits_do_not_rewrite_history(self):
        self.reserve();self.publish(0);self.publish(1);self.finish()
        before=self.store.database.read_bytes()
        with self.store.connect() as db:rows=list(db.execute('SELECT * FROM archive_imports'))
        original=self.store.connect
        @contextmanager
        def read_only():
            with original() as db:
                db.execute('PRAGMA query_only=ON')
                yield db
        inventory={str(p.relative_to(self.store.root)):p.read_bytes() for p in self.store.root.rglob('*') if p.is_file() and not p.name.startswith('terminal.sqlite3')}
        with patch.object(self.store,'connect',read_only):
            for _ in range(3):self.assertEqual(self.ledger.status(self.op)['outcome'],'completed');self.ledger.list()
        self.assertEqual({str(p.relative_to(self.store.root)):p.read_bytes() for p in self.store.root.rglob('*') if p.is_file() and not p.name.startswith('terminal.sqlite3')},inventory)
        self.assertEqual(self.store.database.read_bytes(),before)
        ident=self.items()[2]['destination_id'];self.store.save_strategy('Edited','graph',{},strategy_id=ident)
        status=self.ledger.status(self.op)
        self.assertTrue(status['items'][2]['modified_since_import']);self.assertEqual(status['outcome'],'completed')
        (self.store.directory(status['items'][0]['destination_id'])/'result.json').unlink()
        self.assertEqual(self.ledger.status(self.op)['artifact_verification'],'not_checked')
        self.assertEqual(self.ledger.status(self.op)['outcome'],'completed')

    def test_inconsistent_ledgers_and_malformed_manifest_are_unknown(self):
        self.reserve();self.publish(0);self.publish(1)
        with self.store.connect() as db:
            db.execute("UPDATE archive_import_items SET publication_state='published' WHERE operation_id=? AND kind='strategy'",(self.op,))
        self.ledger.stop(self.op,'process_restart')
        self.assertEqual(self.ledger.status(self.op)['outcome'],'unknown')
        with self.store.connect() as db:
            db.execute("UPDATE archive_imports SET outcome='completed' WHERE operation_id=?",(self.op,))
            db.execute("UPDATE archive_import_items SET publication_state='reserved' WHERE operation_id=? AND kind='strategy'",(self.op,))
        status=self.ledger.status(self.op);self.assertEqual(status['outcome'],'completed');self.assertEqual(status['inspection_state'],'unknown')
        self.op='b'*32;self.ledger.begin(self.op,len(self.raw));self.ledger.claim(self.op);self.reserve()
        ident=self.items()[0]['destination_id']
        with self.store.connect() as db:db.execute("UPDATE runs SET manifest='malformed' WHERE id=?",(ident,))
        self.ledger.reconcile()
        self.assertEqual(self.ledger.status(self.op)['outcome'],'unknown')
        self.assertEqual(self.ledger.status(self.op)['termination_reason'],'metadata_inconsistent')

    def test_cancel_cutoff_and_duplicate_claim_do_not_mutate(self):
        self.assertEqual(self.ledger.cancel(self.op)['status'],'too_late')
        with self.assertRaises(ValueError):self.ledger.claim(self.op)
        other='c'*32;self.ledger.begin(other,len(self.raw))
        self.assertEqual(self.ledger.cancel(other)['status'],'cancelled')
        with self.assertRaises(ValueError):self.ledger.claim(other)
        self.assertEqual(self.items(),[])

    def test_real_process_termination_at_durable_boundaries(self):
        for stage,count,outcome in [('reserved',0,'interrupted'),('snapshot',0,'interrupted'),('first_run',1,'partial'),('completed',2,'completed')]:
            with self.subTest(stage=stage):
                root=self.root/stage;store=RunStore(root);prior_run,prior_strategy=sentinels(store)
                old_files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'runs').rglob('*.json')}
                prior_record=store.get(prior_run);prior_strategy_record=store.strategy(prior_strategy)
                with store.connect() as db:
                    prior_series=[tuple(row) for row in db.execute('SELECT * FROM series WHERE run_id=? ORDER BY kind,row_index',(prior_run,))]
                    prior_evidence=[tuple(row) for row in db.execute('SELECT * FROM research_evidence ORDER BY event_id')]
                process=subprocess.Popen([sys.executable,'-m','tests.archive_receipt_probe',str(root),stage],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                events=queue.Queue()
                reader=threading.Thread(target=lambda:events.put(process.stdout.readline()),daemon=True);reader.start()
                try:
                    line=events.get(timeout=30);barrier=json.loads(line);self.assertEqual(barrier['stage'],stage)
                    process.kill();process.wait(timeout=10)
                finally:
                    if process.poll() is None:process.kill();process.wait(timeout=10)
                    process.stdin.close();process.stdout.close();process.stderr.close();reader.join(2)
                jobs=JobManager(root)
                try:
                    receipt=ArchiveReceipts(jobs.store).status('f'*32)
                    self.assertEqual(receipt['outcome'],outcome);self.assertEqual(len(receipt['items']),3)
                    self.assertEqual(sum(i['kind']=='run' and i['publication_state']=='published' for i in receipt['items']),count)
                    self.assertEqual(len(jobs.store.recent()),3);self.assertIsNone(jobs.active)
                    expected_keys=('kind','ordinal','destination_id','source_run_id','expected_snapshot_sha256','expected_result_sha256','expected_strategy_sha256','expected_series_counts')
                    self.assertEqual([{key:item[key] for key in expected_keys} for item in receipt['items']],
                                     [{key:item[key] for key in expected_keys} for item in barrier['receipt']['items']])
                    raw,project,docs=archive()
                    self.assertEqual(receipt['archive_sha256'],barrier['receipt']['archive_sha256'])
                    self.assertEqual(receipt['validated_content_sha256'],digest({'version':1,'entries':[[name,digest(docs[name])] for name in sorted(docs)]}))
                    for item in receipt['items']:
                        if item['kind']=='run':
                            snapshot=docs[f"runs/{item['source_run_id']}/snapshot.json"];result=docs[f"runs/{item['source_run_id']}/result.json"]
                            self.assertEqual(item['expected_snapshot_sha256'],digest(snapshot));self.assertEqual(item['expected_result_sha256'],digest(result))
                            self.assertEqual(jobs.store.get(item['destination_id'])['manifest'],snapshot)
                            directory=jobs.store.directory(item['destination_id'])
                            snapshot_present=stage=='completed' or item['ordinal']==0 and stage in ('snapshot','first_run')
                            result_present=stage=='completed' or item['ordinal']==0 and stage=='first_run'
                            self.assertEqual((directory/'snapshot.json').exists(),snapshot_present)
                            self.assertEqual((directory/'result.json').exists(),result_present)
                            if snapshot_present:self.assertEqual((directory/'snapshot.json').read_bytes(),canonical(snapshot))
                            if result_present:self.assertEqual((directory/'result.json').read_bytes(),canonical(result))
                            if item['publication_state']=='published':
                                self.assertEqual(jobs.store.result(item['destination_id']),result)
                                self.assertEqual(jobs.store.get(item['destination_id'])['summary']['origin'],'imported')
                                for kind in SERIES:
                                    page=jobs.store.page(item['destination_id'],kind)
                                    self.assertEqual(page['rows'],result[kind]);self.assertEqual(page['total'],len(result[kind]))
                            else:
                                with jobs.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM series WHERE run_id=?',(item['destination_id'],)).fetchone()[0],0)
                        elif item['publication_state']=='published':
                            saved=jobs.store.strategy(item['destination_id'])
                            self.assertEqual({key:saved[key] for key in ('name','kind','document','profile')},{**project['strategy'],'profile':project['profile']})
                    self.assertEqual(jobs.store.get(prior_run),prior_record);self.assertEqual(jobs.store.strategy(prior_strategy),prior_strategy_record)
                    with jobs.store.connect() as db:
                        self.assertEqual([tuple(row) for row in db.execute('SELECT * FROM series WHERE run_id=? ORDER BY kind,row_index',(prior_run,))],prior_series)
                        self.assertEqual([tuple(row) for row in db.execute('SELECT * FROM research_evidence ORDER BY event_id')],prior_evidence)
                        self.assertEqual(db.execute('SELECT count(*) FROM native_trust').fetchone()[0],0)
                    for item in receipt['items']:
                        if item['kind']=='run':self.assertEqual(jobs.store.get(item['destination_id'])['status'],'completed' if item['publication_state']=='published' else 'interrupted')
                    for name,checksum in old_files.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),checksum)
                    self.assertEqual(jobs.store.strategy(prior_strategy)['name'],'Prior saved strategy')
                finally:jobs.close()



class ReceiptManagerTests(unittest.TestCase):
    def setUp(self):
        from terminal.archives import ArchiveManager
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=RunStore(Path(self.tmp.name)/'workspace');self.manager=ArchiveManager(self.store)
        self.raw,self.project,self.docs=archive()

    def upload(self,raw=None,finish=True):
        import base64
        raw=self.raw if raw is None else raw
        transfer=self.manager.begin(len(raw));self.op=transfer['operation_id']
        for offset in range(0,len(raw),transfer['chunk_bytes']):self.manager.append(self.op,offset,base64.b64encode(raw[offset:offset+transfer['chunk_bytes']]).decode())
        return self.manager.finish(self.op) if finish else self.op

    def test_zero_eight_and_identical_deliberate_imports_have_fresh_ids(self):
        for count in (0,8,2,2):
            raw,_,_=archive(count);result=self.upload(raw)
            self.assertEqual(result['receipt']['outcome'],'completed');self.assertEqual(len(result['run_ids']),count)
            self.assertEqual(result['receipt']['artifact_verification'],'not_checked')
        rows=self.manager.recent()['rows'];self.assertEqual(len(rows),4)
        self.assertNotEqual(rows[0]['operation_id'],rows[1]['operation_id']);self.assertEqual(rows[0]['validated_content_sha256'],rows[1]['validated_content_sha256'])
        first=self.manager.status(rows[0]['operation_id']);second=self.manager.status(rows[1]['operation_id'])
        self.assertFalse({i['destination_id'] for i in first['items']} & {i['destination_id'] for i in second['items']})
        self.assertEqual(len(self.store.recent()),12)

    def test_zip_bytes_and_canonical_content_identities_are_distinct(self):
        import zipfile
        left=self.upload()['receipt'];raw,_,_=archive(compression=zipfile.ZIP_DEFLATED);right=self.upload(raw)['receipt']
        self.assertNotEqual(left['archive_sha256'],right['archive_sha256']);self.assertEqual(left['validated_content_sha256'],right['validated_content_sha256'])
        raw,_,_=archive(1);changed=self.upload(raw)['receipt'];self.assertNotEqual(left['validated_content_sha256'],changed['validated_content_sha256'])

    def test_lost_begin_reply_leaves_receipt_without_content_claim(self):
        with transaction_fault(self.store,'INSERT INTO archive_imports(',after_commit=True),self.assertRaisesRegex(ValueError,'Operation'):self.manager.begin(5)
        receipt=self.manager.recent()['rows'][0]
        self.assertIsNone(receipt['archive_sha256']);self.assertFalse((self.store.root/'imports').exists())
        self.assertEqual(self.manager.status(receipt['operation_id'])['items'],[])

    def test_begin_rollback_creates_neither_receipt_nor_upload(self):
        with transaction_fault(self.store,'INSERT INTO archive_imports('),self.assertRaises(ValueError):self.manager.begin(5)
        self.assertEqual(self.manager.recent()['rows'],[]);self.assertFalse((self.store.root/'imports').exists())

    def test_targeted_stale_cancel_and_duplicate_finish_have_no_new_effects(self):
        old=self.upload(finish=False);self.assertEqual(self.manager.cancel(old)['status'],'cancelled')
        new=self.upload(finish=False);self.assertEqual(self.manager.cancel(old)['status'],'cancelled');self.assertEqual(self.manager.upload['id'],new)
        result=self.manager.finish(new)
        self.assertEqual(self.manager.cancel(new)['status'],'too_late')
        before=self.manager.status(new)
        with self.assertRaisesRegex(ValueError,'cannot be finished again'):self.manager.finish(new)
        self.assertEqual(self.manager.status(new),before);self.assertEqual(len(self.store.recent()),2)

    def test_final_commit_then_error_remains_completed_and_latches_new_imports(self):
        self.upload(finish=False)
        with transaction_fault(self.store,"UPDATE archive_imports SET phase='terminal',outcome='completed'",after_commit=True),self.assertRaises(ValueError) as error:self.manager.finish(self.op)
        self.assertIn(self.op,str(error.exception));self.assertNotIn('private',str(error.exception));self.assertLess(len(str(error.exception)),2000)
        self.assertEqual(self.manager.status(self.op)['outcome'],'completed')
        with self.assertRaisesRegex(ValueError,'blocked'):self.manager.begin(5)

    def test_failure_record_itself_fails_then_restart_reconciles_without_resume(self):
        self.upload(finish=False)
        original=self.manager.receipts.publish_run
        def fail_second(op,ordinal,*args):
            if ordinal==1:raise OSError('private')
            return original(op,ordinal,*args)
        with patch.object(self.manager.receipts,'publish_run',side_effect=fail_second),patch.object(self.manager.receipts,'stop',side_effect=sqlite3.OperationalError('private')),self.assertRaises(ValueError):self.manager.finish(self.op)
        self.assertEqual(self.manager.status(self.op)['phase'],'publishing')
        jobs=JobManager(self.store.root)
        try:
            receipt=ArchiveReceipts(jobs.store).status(self.op)
            self.assertEqual(receipt['outcome'],'partial');self.assertEqual(receipt['items'][1]['publication_state'],'reserved');self.assertIsNone(jobs.active)
        finally:jobs.close()

    def test_status_database_failure_is_unavailable_not_empty_or_success(self):
        self.upload()
        with patch.object(self.store,'connect',side_effect=sqlite3.OperationalError('private')):
            with self.assertRaisesRegex(ValueError,'inspection unavailable'):self.manager.status(self.op)
            with self.assertRaisesRegex(ValueError,'inspection unavailable'):self.manager.recent()

    def test_dataset_lookup_failure_does_not_change_completion(self):
        with patch('terminal.archives.DatasetStore.describe',side_effect=sqlite3.OperationalError('private')):result=self.upload()
        self.assertIsNone(result['datasets_found']);self.assertEqual(result['dataset_availability'],'unchecked');self.assertEqual(result['receipt']['outcome'],'completed')

    def test_list_paginates_and_bound_errors_never_include_documents(self):
        for _ in range(3):self.upload(archive(0)[0])
        page=self.manager.recent(limit=2);self.assertEqual(len(page['rows']),2)
        following=self.manager.recent(before=page['next'],limit=2);self.assertEqual(len(following['rows']),1);self.assertIsNone(following['next'])
        self.assertNotIn('document',canonical(page).decode())
        with self.assertRaises(ValueError):self.manager.recent(limit=101)

    def test_real_snapshot_and_result_publish_boundaries_remain_incomplete(self):
        from terminal.data import write_new
        for name,after in [('snapshot.json',False),('snapshot.json',True),('result.json',False),('result.json',True)]:
            with self.subTest(name=name,after=after):
                from terminal.archives import ArchiveManager
                store=RunStore(Path(self.tmp.name)/(name+str(after)));self.store=store;self.manager=ArchiveManager(store)
                def fault(path,data):
                    if path.name==name:
                        if after:write_new(path,data)
                        raise OSError('private')
                    write_new(path,data)
                with patch('terminal.archive_receipts.write_new',side_effect=fault),self.assertRaises(ValueError):self.upload()
                receipt=self.manager.status(self.op)
                self.assertEqual(receipt['outcome'],'failed');self.assertEqual(len(receipt['items']),3)
                self.assertEqual(receipt['items'][0]['publication_state'],'incomplete')
                self.assertTrue(all(row['status']=='importing' for row in store.recent()))

    def test_duplicate_finish_claim_and_begin_collision_never_change_existing_receipt(self):
        self.upload(finish=False);self.manager.receipts.claim(self.op)
        before=self.manager.status(self.op)
        with self.assertRaisesRegex(ValueError,'already claimed'):self.manager.finish(self.op)
        self.assertEqual(self.manager.status(self.op),before)
        from terminal.archives import ArchiveManager
        other=ArchiveManager(self.store)
        with patch('terminal.archives.uuid.uuid4',return_value=type('ID',(),{'hex':self.op})()),self.assertRaisesRegex(ValueError,'collision'):other.begin(len(self.raw))
        self.assertEqual(self.manager.status(self.op),before)

    def test_targeted_cancel_command_rejects_null_empty_and_stale_targets(self):
        from terminal.service import AppService
        service=AppService(Path(self.tmp.name)/'service')
        try:
            old=service.archives.begin(5)['operation_id'];service.archives.cancel(old)
            current=service.archives.begin(5)['operation_id']
            for invalid in (None,'',False,'not-an-id'):
                response=service.handle({'version':1,'id':'cancel','command':'archive_import_cancel','params':{'operation_id':invalid}})
                self.assertEqual(response['type'],'error');self.assertEqual(service.archives.upload['id'],current)
                self.assertEqual(service.archives.status(current)['phase'],'receiving')
            service.handle({'version':1,'id':'cancel','command':'archive_import_cancel','params':{'operation_id':old}})
            self.assertEqual(service.archives.upload['id'],current);self.assertEqual(service.archives.status(current)['phase'],'receiving')
        finally:service.close()

    def test_service_quarantine_preserves_active_work_and_read_routes(self):
        from terminal.service import AppService
        service=AppService(Path(self.tmp.name)/'service')
        try:
            service.jobs.active={'id':'b'*32,'kind':'run'}
            service.jobs.latch_storage_failure('a'*32,'archive_import')
            state=service.jobs.scheduler_status()
            self.assertEqual(state['active']['id'],'b'*32);self.assertNotIn('worker has stopped',state['storage_failure']['message'])
            response=service.handle({'version':1,'id':'test','command':'archive_begin','params':{'size':5}})
            self.assertEqual(response['type'],'error')
            response=service.handle({'version':1,'id':'test','command':'archive_import_list','params':{'before':None,'limit':25}})
            self.assertEqual(response['result']['rows'],[])
        finally:service.jobs.active=None;service.close()


if __name__=='__main__':unittest.main()
