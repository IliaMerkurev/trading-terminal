"""Independently invented pages and races; no exchange or native execution."""
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from terminal.service import AppService
from terminal.series import Candle
from terminal.observations import source_identity
from terminal.chart_reads import TERMINAL


def ident():return uuid.uuid4().hex


class ChartReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=AppService(self.tmp.name);self.addCleanup(self.service.close)
        self.data=self.service.datasets.save('spot','BTCUSDT',0,900*60,
            [Candle(i*60,100+i%20,102+i%20,99+i%20,101+i%20,2) for i in range(900) if i!=24],[],{},
            metadata={},provenance=[],source='Independently invented read test')
        self.reads=self.service.chart_reads

    def start(self,start=0,end=500*60,**extra):
        return self.reads.start(**dict(request_id=ident(),view_id=ident(),generation=1,surface='observation',
            query=dict(dataset_id=self.data['id'],start=start,end=end),**extra))

    def wait(self,request_id):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            value=self.reads.status(request_id)
            if value['status'] in TERMINAL:return value
            time.sleep(.02)
        self.fail('Read did not settle within the bounded test deadline')

    def save_params(self):
        return dict(request_id=ident(),expected_source=source_identity(self.data),observation_id=None,expected_revision=0,
            dataset_id=self.data['id'],start=600,end=1200,hypothesis='Independent draft',falsification='Lower close')

    def test_first_middle_last_expected_pages_no_exposure_and_independent_slot(self):
        self.service.jobs.reservation='batch:synthetic-held-slot'
        self.addCleanup(setattr,self.service.jobs,'reservation',None)
        for start,end in [(0,500*60),(300*60,800*60),(400*60,900*60)]:
            result=self.wait(self.start(start,end)['request_id'])
            self.assertEqual(result['status'],'ready',result)
            page=result['result'];expected=[i for i in range(start//60,end//60) if i!=24]
            self.assertEqual([r['time'] for r in page['candles']],[i*60 for i in expected])
            self.assertEqual([r['close'] for r in page['candles']],[101+i%20 for i in expected])
            self.assertEqual(page['missing'],[1440] if start<=1440<end else [])
        with self.service.store.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM research_evidence WHERE kind='viewed'").fetchone()[0],0)
        self.assertEqual(self.service.jobs.reservation,'batch:synthetic-held-slot')

    def test_duplicate_identity_and_stale_ready_do_not_register_new_reference(self):
        request=dict(request_id=ident(),view_id=ident(),generation=1,surface='observation',query=dict(dataset_id=self.data['id'],start=0,end=600))
        first=self.reads.start(**request);self.assertEqual(self.reads.start(**request)['request_id'],first['request_id'])
        self.assertEqual(self.wait(first['request_id'])['status'],'ready')
        with self.assertRaisesRegex(ValueError,'reused'):self.reads.start(**{**request,'query':{**request['query'],'end':1200}})
        newer=self.reads.start(**{**request,'request_id':ident(),'generation':2,'query':{**request['query'],'start':600,'end':1200}})
        before=len(self.service.display_pages)
        self.assertEqual(self.reads.status(first['request_id'])['status'],'superseded')
        self.assertEqual(len(self.service.display_pages),before)
        self.assertEqual(self.wait(newer['request_id'])['status'],'ready')

    def test_replacement_after_read_fails_before_delivery(self):
        operation=self.start();request_id=operation['request_id']
        deadline=time.monotonic()+10
        while self.reads.records[request_id]['status'] not in TERMINAL and time.monotonic()<deadline:time.sleep(.02)
        path=self.service.datasets.root/self.data['id']/'trade.parquet'
        replacement=path.with_suffix('.replacement');replacement.write_bytes(path.read_bytes());os.replace(replacement,path)
        result=self.reads.status(request_id);self.assertEqual(result['status'],'failed');self.assertIn('changed',result['error'])
        self.assertEqual(len(self.service.display_pages),0)

    def test_checksum_failure_never_becomes_empty_page(self):
        path=self.service.datasets.root/self.data['id']/'trade.parquet';raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        result=self.wait(self.start()['request_id']);self.assertEqual(result['status'],'failed');self.assertIn('checksum',result['error']);self.assertIsNone(result['result'])

    def test_full_suffix_values_order_and_gap_checked(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        path=self.service.datasets.root/self.data['id']/'trade.parquet';original=path.read_bytes()
        rows=pq.read_table(path).to_pylist();manifest_path=path.parent/'manifest.json'
        for category in ('order','values','gaps'):
            changed=[dict(r) for r in rows]
            if category=='order':changed[-1]['time']=changed[-2]['time']
            if category=='values':changed[-1]['low']=-1
            if category=='gaps':changed.pop()
            pq.write_table(pa.Table.from_pylist(changed,schema=pq.read_schema(path)),path)
            manifest=json.loads(manifest_path.read_text());manifest['files_sha256']['trade']=hashlib.sha256(path.read_bytes()).hexdigest();manifest_path.write_text(json.dumps(manifest))
            result=self.wait(self.start(0,600)['request_id'])
            self.assertEqual(result['status'],'failed',category)
            path.write_bytes(original)

    def test_exact_same_descriptor_is_decoded_and_replacement_rejected(self):
        from terminal import source_limits
        original=source_limits.checked_parquet
        path=self.service.datasets.root/self.data['id']/'trade.parquet'
        def replace(stream,*args,**kwargs):
            result=original(stream,*args,**kwargs)
            candidate=path.with_suffix('.new');candidate.write_bytes(path.read_bytes());os.replace(candidate,path)
            return result
        with patch('terminal.source_limits.checked_parquet',replace):
            with self.assertRaisesRegex(ValueError,'changed'):self.service.observations.window(self.data['id'],0,600)

    def test_note_receipt_is_exactly_once_persistent_and_never_views(self):
        params=self.save_params();operation=self.reads.save(**params);self.assertEqual(operation['kind'],'save')
        result=self.wait(operation['request_id']);self.assertEqual(result['status'],'completed',result)
        self.assertEqual(self.reads.save(**params)['result']['id'],result['result']['id'])
        with self.assertRaisesRegex(ValueError,'reused'):self.reads.save(**{**params,'hypothesis':'Different'})
        with self.service.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM observation_revisions').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM research_evidence WHERE kind='viewed'").fetchone()[0],0)
        self.service.close();self.service=AppService(self.tmp.name);self.reads=self.service.chart_reads
        self.addCleanup(self.service.close)
        self.assertEqual(self.reads.status(params['request_id'])['status'],'completed')
        self.assertEqual(self.reads.save_history()[0]['request_id'],params['request_id'])

    def test_rejected_save_has_no_receipt_and_postcommit_exception_keeps_completion(self):
        params=self.save_params()
        with self.assertRaises(ValueError):self.reads.save(**{**params,'hypothesis':''})
        self.assertEqual(self.reads.save_history(),[])
        original=self.reads.observations.save
        def after(**kwargs):
            original(**kwargs);raise RuntimeError('Injected lost postcommit acknowledgement')
        with patch.object(self.reads.observations,'save',after):
            result=self.wait(self.reads.save(**params)['request_id'])
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(len(self.service.observations.history()['rows']),1)

    def test_small_save_commit_defers_for_writer_without_blocking_cancel(self):
        params=self.save_params()
        db=self.service.store.connect().__enter__() if False else None
        import sqlite3
        connection=sqlite3.connect(self.service.store.database);self.addCleanup(connection.close)
        # Receipt exists before holding the independent writer.
        operation=self.reads.save(**params);connection.execute('BEGIN IMMEDIATE')
        try:
            time.sleep(.4);begin=time.monotonic();value=self.reads.cancel(operation['request_id'])
            self.assertLess(time.monotonic()-begin,2);self.assertEqual(value['status'],'cancel_requested')
        finally:connection.rollback()
        self.assertEqual(self.wait(operation['request_id'])['status'],'cancelled')
        self.assertEqual(self.service.observations.history()['rows'],[])

    def test_new_chart_does_not_cancel_explicit_save(self):
        params=self.save_params();save=self.reads.save(**params)
        chart=self.start(0,600)
        self.assertEqual(self.wait(save['request_id'])['status'],'completed')
        self.assertEqual(self.wait(chart['request_id'])['status'],'ready')

    def test_restart_marks_pending_receipt_interrupted_without_note(self):
        request_id=ident()
        with self.service.store.connect() as db:db.execute("INSERT INTO observation_save_requests(id,request_hash,state) VALUES(?,?,'pending')",(request_id,'a'*64))
        self.service.close();self.service=AppService(self.tmp.name);self.reads=self.service.chart_reads;self.addCleanup(self.service.close)
        self.assertEqual(self.reads.status(request_id)['status'],'interrupted')
        self.assertEqual(self.service.observations.history()['rows'],[])

    def test_service_api_has_only_asynchronous_chart_routes(self):
        for command,params in [('chart_window',dict(run_id=ident(),start=None,minutes=30)),('local_history_window',dict(dataset_id=self.data['id'],start=0,end=600))]:
            result=self.service.handle(dict(version=1,id='bounded',command=command,params=params))
            self.assertEqual(result['type'],'error')
        result=self.service.handle(dict(version=1,id='bounded',command='chart_read_start',params=dict(request_id=ident(),view_id=ident(),generation=1,surface='observation',query=dict(dataset_id=self.data['id'],start=0,end=600))))
        self.assertEqual(result['type'],'result');self.assertEqual(self.wait(result['result']['request_id'])['status'],'ready')

    def test_run_chart_preserves_nanoseconds_availability_equity_and_unavailable_history(self):
        from terminal.data import canonical
        run_id=ident();manifest=dict(dataset=self.data,profile={'execution_minutes':1},research={'library':True,'window':{'start':600,'end':3600}})
        fills=[{'time_ns':600_000_000_000,'price':'101','side':'buy'},
               {'time_ns':2_399_999_999_999,'price':'102','side':'sell'},
               {'time_ns':2_400_000_000_000,'price':'103','side':'sell'}]
        indicators=[{'time':600,'values':{'test':1}},{'time':660,'values':{'test':2}},{'time':2400,'values':{'test':3}}]
        equity=[{'time_ns':660_000_000_000,'equity':'10001'}]
        with self.service.store.connect() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?,NULL,?,?)',(run_id,'synthetic','completed',canonical(manifest).decode(),'a'*64,'{"origin":"local"}'))
            for kind,values in [('fills',fills),('indicators',indicators),('equity',equity)]:
                for i,value in enumerate(values):db.execute('INSERT INTO series VALUES(?,?,?,?)',(run_id,kind,i,canonical(value).decode()))
        request=dict(request_id=ident(),view_id=ident(),generation=1,surface='run',query=dict(run_id=run_id,start=600,minutes=30))
        result=self.wait(self.reads.start(**request)['request_id']);self.assertEqual(result['status'],'ready',result)
        page=result['result'];self.assertEqual(page['missing'],[1440])
        self.assertEqual([f['time_ns'] for f in page['series']['fills']],[600_000_000_000,2_399_999_999_999])
        self.assertEqual([f['chart_time'] for f in page['series']['fills']],[660,2400])
        self.assertEqual(page['series']['indicators'],indicators[1:]);self.assertEqual(page['series']['equity'],equity)
        path=self.service.datasets.root/self.data['id']/'trade.parquet';path.unlink()
        missing=self.wait(self.reads.start(**{**request,'request_id':ident(),'generation':2})['request_id'])
        self.assertEqual(missing['status'],'ready',missing);self.assertIn('unavailable',missing['result']['history_note']);self.assertEqual(missing['result']['series']['candles'],[])

    @unittest.skipUnless(os.name=='posix','Linux managed supervisor gate')
    def test_cancel_supersede_and_close_reap_worker_keep_bounded_queue(self):
        first=self.start();deadline=time.monotonic()+5
        while (not self.reads.active or not self.reads.active['process']) and time.monotonic()<deadline:time.sleep(.005)
        active=self.reads.active;process=active['process'];os.kill(process.pid,signal.SIGSTOP)
        try:
            for i in range(6):last=self.start(600,1200)
            self.assertLessEqual(len(self.reads.queue),1)
            before=time.monotonic();self.reads.cancel(first['request_id'])
            self.assertLess(time.monotonic()-before,2)
            self.assertEqual(self.reads.status(first['request_id'])['status'],'cancel_requested')
        finally:os.kill(process.pid,signal.SIGCONT)
        self.assertEqual(self.wait(first['request_id'])['status'],'cancelled')
        self.assertEqual(self.wait(last['request_id'])['status'],'ready')
        again=self.start(0,600);self.service.close()
        self.assertIsNone(self.reads.active)
        self.assertIn(self.reads.status(again['request_id'])['status'],('cancelled','ready'))

    def test_postcommit_busy_then_cancel_reports_committed_note(self):
        import sqlite3
        import threading
        params=self.save_params();committed=threading.Event();release=threading.Event()
        original=self.reads.observations.get;first=True
        def delayed(*args,**kwargs):
            nonlocal first
            if first:
                first=False;committed.set()
                error=sqlite3.OperationalError('Injected postcommit busy');error.sqlite_errorcode=sqlite3.SQLITE_BUSY
                raise error
            return original(*args,**kwargs)
        with patch.object(self.reads.observations,'get',delayed):
            operation=self.reads.save(**params);self.assertTrue(committed.wait(5))
            self.reads.cancel(operation['request_id'])
            result=self.wait(operation['request_id'])
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(self.reads.save_history()[0]['status'],'completed')
        self.assertEqual(len(self.service.observations.history()['rows']),1)

    def test_thread_start_failure_is_inspectable_and_never_saves(self):
        params=self.save_params()
        with patch('terminal.chart_reads.threading.Thread.start',side_effect=RuntimeError('Injected thread failure')):
            result=self.reads.save(**params)
        self.assertEqual(result['status'],'failed',result)
        self.assertEqual(self.reads.status(params['request_id'])['status'],'failed')
        self.assertEqual(self.reads.save_history()[0]['status'],'failed')
        self.assertEqual(self.service.observations.history()['rows'],[])
        self.assertIsNone(self.reads.active)

    def test_failed_launch_does_not_strand_next_queued_chart(self):
        original=self.reads._kick
        with patch.object(self.reads,'_kick'):
            save=self.reads.save(**self.save_params());chart=self.start(0,600)
        with patch('terminal.chart_reads.threading.Thread.start',side_effect=RuntimeError('One launch fails')):
            original()
        self.assertIsNone(self.reads.active)
        self.assertEqual(self.wait(chart['request_id'])['status'],'ready')
        self.assertEqual(self.reads.status(save['request_id'])['status'],'failed')

    def test_additive_receipt_migration_preserves_existing_notes_and_series(self):
        from terminal.storage import RunStore
        note=self.service.observations.save(None,0,self.data['id'],600,1200,'Existing immutable note','')
        with self.service.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM observation_revisions')]
            db.execute('DROP TABLE observation_save_requests')
        self.service.close();self.service=AppService(self.tmp.name);self.reads=self.service.chart_reads;self.addCleanup(self.service.close)
        with self.service.store.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM observation_revisions')],before)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT count(*) FROM native_trust').fetchone()[0],0)
        self.assertEqual(self.service.observations.get(note['id'])['hypothesis'],'Existing immutable note')
