"""Single managed verified-read lane, independent of the calculation reservation.

Chart requests are launch-local and latest-generation wins. Explicit note saves
have separate durable receipts and are never revoked by subsequent chart reads.
Workers read only; the service commits verified notes and issues display refs.
"""
from collections import OrderedDict
from types import SimpleNamespace
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import uuid

from terminal.data import DatasetStore,canonical,digest,write_new
from terminal.storage import RunStore,identifier
from terminal.observations import Observations,source_identity,validate_window
from terminal.process_lifecycle import worker_job,worker_options
from terminal.verified_chart import file_identity,unchanged

MAX_PAGE=960*1024  # Internal guard envelope; public report page stays 900 KiB.
TERMINAL=('ready','completed','cancelled','superseded','failed','interrupted')


def busy(exc):
    return isinstance(exc,sqlite3.OperationalError) and getattr(exc,'sqlite_errorcode',0)&255 in (5,6)


class ReadStore(RunStore):
    def connect(self,*,timeout=.05):
        return super().connect(timeout=timeout)


class ChartReads:
    def __init__(self,service):
        self.service=service;self.jobs=service.jobs
        self.store=object.__new__(ReadStore);self.store.root=service.store.root;self.store.database=service.store.database
        self.observations=Observations(self.store,service.datasets)
        if not hasattr(service,'display_pages'):service.display_pages=OrderedDict()
        self.display_service=SimpleNamespace(store=self.store,datasets=service.datasets,display_pages=service.display_pages)
        self.lock=threading.RLock();self.active=None;self.queue=[];self.records=OrderedDict();self.views=OrderedDict()
        self.closed=False;self.session=uuid.uuid4().hex
        self.directory=self.store.root/'chart-reads'/self.session
        with self.store.connect() as db:
            db.execute("UPDATE observation_save_requests SET state='interrupted',error='Service stopped before the note was saved; no automatic retry' WHERE state='pending'")

    def _receipt(self,request_id):
        with self.store.connect(timeout=.05) as db:
            row=db.execute('SELECT * FROM observation_save_requests WHERE id=?',(request_id,)).fetchone()
        if not row:return None
        row=dict(row)
        return dict(request_id=request_id,status=row['state'],phase='terminal' if row['state']!='pending' else 'verifying',
                    error=row['error'],result=self.observations.get(row['observation_id'],row['revision']) if row['state']=='completed' else None,
                    request_hash=row['request_hash'],kind='save')

    def _room(self):
        while len(self.records)>=128:
            key=next((k for k,v in self.records.items() if v['status'] in TERMINAL),None)
            if key is None:raise ValueError('Verified-read request history is full')
            del self.records[key]

    def start(self,request_id,view_id,generation,surface,query):
        identifier(request_id);identifier(view_id)
        if type(generation) is not int or not 1<=generation<=2**53-1:raise ValueError('Invalid chart generation')
        fields={'run':{'run_id','start','minutes'},'observation':{'dataset_id','start','end'}}
        if surface not in fields or not isinstance(query,dict) or set(query)!=fields[surface]:raise ValueError('Invalid chart read request')
        request_hash=digest([view_id,generation,surface,query])
        with self.lock:
            if self.closed:raise ValueError('Verified reader is stopping')
            old=self.records.get(request_id)
            if old:
                if old['request_hash']!=request_hash:raise ValueError('Read request identity was reused with different inputs')
                return self.status(request_id)
            previous=self.views.get(view_id)
            if previous and generation<=previous[0]:raise ValueError('Chart generation is obsolete')
            if surface=='observation':
                manifest=self.service.datasets.describe(query['dataset_id']);validate_window(manifest,query['start'],query['end'])
                if (query['end']-query['start'])//manifest.get('interval_seconds',60)>500:raise ValueError('Local chart page exceeds 500 source candles')
                expected=source_identity(manifest)
            else:
                if type(query['minutes']) is not int or not 30<=query['minutes']<=480 or (query['start'] is not None and (type(query['start']) is not int or query['start']%60)):
                    raise ValueError('Chart requests require aligned start and 30–480 minutes')
                run=self.store.get(query['run_id'])
                if run['status']!='completed':raise ValueError('No completed result available')
                expected={'manifest':digest(run['manifest']),'result_hash':run['result_hash']}
            self._room()
            self.views[view_id]=(generation,request_id);self.views.move_to_end(view_id)
            while len(self.views)>128:self.views.popitem(last=False)
            # One latest queued chart globally; note saves have a separate intent.
            for record in list(self.records.values()):
                if record['kind']=='chart' and record['status'] not in TERMINAL and (record.get('view_id')==view_id or record in self.queue):
                    self._cancel(record,'superseded')
            record=dict(request_id=request_id,request_hash=request_hash,kind='chart',surface=surface,query=copy.deepcopy(query),
                        expected=expected,view_id=view_id,generation=generation,status='pending',phase='queued',error=None,result=None)
            self.records[request_id]=record;self.queue.append(record);self._kick()
            return self.status(request_id)

    def save(self,request_id,expected_source,**query):
        identifier(request_id)
        request_hash=digest([expected_source,query])
        if len(canonical(query))>16*1024:raise ValueError('Observation note exceeds request budget')
        with self.lock:
            if self.closed:raise ValueError('Verified reader is stopping')
            old=self.records.get(request_id) or self._receipt(request_id)
            if old:
                if old['request_hash']!=request_hash:raise ValueError('Save request identity was reused with different inputs')
                return self.status(request_id)
            if any(r['kind']=='save' and r['status'] not in TERMINAL for r in self.records.values()):
                raise ValueError('A note save is already pending; inspect its request before saving again')
            manifest=self.service.datasets.describe(query['dataset_id']);validate_window(manifest,query['start'],query['end'])
            if source_identity(manifest)!=expected_source:raise ValueError('Exact observation source changed before save')
            if query['observation_id'] is not None:identifier(query['observation_id'])
            if type(query['expected_revision']) is not int or query['expected_revision']<0:raise ValueError('Invalid observation revision')
            if not isinstance(query['hypothesis'],str) or not query['hypothesis'].strip() or len(query['hypothesis'])>2000:raise ValueError('Enter a hypothesis of 1–2000 characters')
            if not isinstance(query['falsification'],str) or len(query['falsification'])>2000:raise ValueError('Optional falsification condition must be at most 2000 characters')
            self._room()
            with self.store.connect(timeout=.05) as db:
                db.execute("INSERT INTO observation_save_requests(id,request_hash,state) VALUES(?,?,'pending')",(request_id,request_hash))
            record=dict(request_id=request_id,request_hash=request_hash,kind='save',surface='observation',query=copy.deepcopy(query),
                        expected=copy.deepcopy(expected_source),status='pending',phase='queued',error=None,result=None)
            self.records[request_id]=record
            # Explicit saves get the next turn; they never become latest-read work.
            self.queue.insert(0,record)
            try:self._kick()
            except Exception as exc:
                record.update(error='Save launch could not be confirmed; inspect this request before retrying',phase='launch_blocked')
            return dict(request_id=request_id,status=record['status'],phase=record['phase'],error=record['error'],result=record['result'],kind='save')

    def _kick(self):
        if self.active or self.closed:return
        self.queue=[r for r in self.queue if r['status']=='pending']
        if not self.queue:return
        record=self.queue.pop(0);record.update(status='running',phase='starting')
        active={'record':record,'process':None,'job':None,'anchor':None};self.active=active
        thread=threading.Thread(target=self._run,args=(active,),daemon=True);active['thread']=thread
        try:thread.start()
        except Exception:
            active['thread']=None;active['startup_error']='Verified reader could not start; no note was saved'
            record.update(status='cancel_requested',cancel_outcome='failed',phase='launch_failed',error=active['startup_error'])
            self._finish_failed_start(active)

    def _finish_failed_start(self,active):
        try:self._settle(active['record'],active['record'].get('cancel_outcome','failed'),None,active['startup_error'])
        except Exception as exc:
            if busy(exc):return
            active['record']['error']='Save receipt settlement unavailable; workspace ownership retained'
            return
        if self.active is active:self.active=None

    def _run(self,active):
        record=active['record'];work=self.directory/record['request_id'];page=None;error=None
        try:
            work.mkdir(parents=True,exist_ok=False)
            request={k:record[k] for k in ('request_id','kind','surface','query','expected')}
            raw=canonical(request);write_new(work/'request.json',raw)
            anchor=sqlite3.connect(self.store.database,timeout=.05,check_same_thread=False)
            active['anchor']=anchor;anchor.execute('SELECT count(*) FROM sqlite_master').fetchone()
            job=worker_job(self.jobs.instance_file);active['job']=job
            process=subprocess.Popen([sys.executable,'-m','terminal.worker'],cwd=Path(__file__).resolve().parents[1],
                stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**worker_options(job))
            active['process']=process;job.assign(process)
            process.stdin.write(canonical(dict(version=1,command='chart_read',root=str(self.store.root),session=self.session,
                request_id=record['request_id'],request_hash=digest(request)))+b'\n');process.stdin.close()
            while process.poll() is None:
                with self.lock:
                    if record['status']=='cancel_requested':job.terminate()
                try:
                    with (work/'phase').open('r') as stream:phase=stream.read(40)
                    if phase in ('verifying','decoding','reading_series','ready'):
                        with self.lock:record['phase']=phase
                except OSError:pass
                try:process.wait(timeout=.05)
                except subprocess.TimeoutExpired:pass
            if process.returncode==0:
                with (work/'result.json').open('rb') as stream:raw=stream.read(MAX_PAGE+1)
                if len(raw)>MAX_PAGE:raise ValueError('Chart result exceeds payload budget')
                page=json.loads(raw)
            else:
                try:
                    with (work/'error.json').open('rb') as stream:raw=stream.read(4096)
                    error=json.loads(raw)['error']
                except (OSError,ValueError,KeyError):error='Verified reader failed or was interrupted'
        except Exception as exc:error=str(exc)[:2000]
        finally:
            try:
                if active['job']:active['job'].close()
                process=active['process']
                if process:
                    if process.stdin and not process.stdin.closed:process.stdin.close()
                    process.wait(timeout=5)
                if active['anchor']:active['anchor'].close()
            except Exception:
                with self.lock:record['error']='Reader cleanup incomplete; workspace ownership retained'
                return
        # Process is reaped before terminal settlement. Bounded BUSY retry does
        # not monopolize service dispatch or the read-lane lock.
        while True:
            try:
                with self.lock:
                    if record['status']=='cancel_requested':
                        outcome=record.get('cancel_outcome','cancelled')
                        self._settle(record,outcome,None,None)
                    elif error:self._settle(record,'failed',None,error)
                    else:
                        self._verify_guard(page)
                        if record['kind']=='save':
                            record['phase']='saving'
                            result=self.observations.save(**record['query'],verified_source=record['expected'],save_request=record['request_id'])
                            self._settle(record,'completed',result,None)
                        else:self._settle(record,'ready',page,None)
                break
            except Exception as exc:
                if busy(exc):
                    threading.Event().wait(.05);continue
                # A committed note wins even if postcommit get/response failed.
                try:
                    receipt=self._receipt(record['request_id']) if record['kind']=='save' else None
                    if receipt and receipt['status']=='completed':
                        with self.lock:record.update(status='completed',phase='terminal',result=receipt['result'],error=None)
                        break
                    error=str(exc)[:2000]
                except Exception:threading.Event().wait(.05)
        try:shutil.rmtree(work)
        except OSError:pass
        with self.lock:
            if self.active is active:self.active=None
            self._kick()

    def _settle(self,record,state,result,error):
        if record['kind']=='save' and state!='completed':
            with self.store.connect(timeout=.05) as db:
                db.execute('BEGIN IMMEDIATE')
                receipt=db.execute('SELECT * FROM observation_save_requests WHERE id=?',(record['request_id'],)).fetchone()
                if receipt is None:raise ValueError('Observation save receipt is missing')
                receipt=dict(receipt)
                if receipt['state']=='pending':
                    db.execute("UPDATE observation_save_requests SET state=?,error=? WHERE id=? AND state='pending'",(state,error,record['request_id']))
                elif receipt['state']=='completed':state='completed';error=None
                else:state=receipt['state'];error=receipt['error']
            if state=='completed':result=self.observations.get(receipt['observation_id'],receipt['revision'])
        record.update(status=state,phase='terminal',result=result,error=error)

    def _verify_guard(self,page):
        if not isinstance(page,dict) or set(page)!={'page','guard'}:raise ValueError('Invalid verified reader response')
        guard=page['guard']
        if guard:
            manifest=self.service.datasets.describe(guard['dataset_id'])
            if source_identity(manifest)!=guard['source']:raise ValueError('Exact local history changed before delivery')
            unchanged(self.service.datasets.root/guard['dataset_id']/'trade.parquet',guard['file_identity'])

    def status(self,request_id):
        identifier(request_id)
        with self.lock:
            if self.active is None and self.queue:self._kick()
            record=self.records.get(request_id)
            if record is None:
                receipt=self._receipt(request_id)
                if receipt:return {k:receipt[k] for k in ('request_id','status','phase','error','result','kind')}
                raise ValueError('Verified request expired or belongs to another service session')
            if self.active and self.active['record'] is record and self.active.get('startup_error'):
                self._finish_failed_start(self.active)
                if not self.active:self._kick()
            result=record['result']
            if record['kind']=='chart' and record['status']=='ready':
                if self.views.get(record['view_id'])!=(record['generation'],request_id):
                    record.update(status='superseded',result=None);result=None
                else:
                    try:
                        self._verify_guard(result)
                        from terminal.displayed_evidence import chart_page
                        owner=record['query']['run_id' if record['surface']=='run' else 'dataset_id']
                        result=chart_page(self.display_service,'run_chart' if record['surface']=='run' else 'observation_chart',result['page'],owner)
                    except Exception as exc:
                        record.update(status='failed',result=None,error=str(exc)[:2000]);result=None
            return copy.deepcopy(dict(request_id=request_id,status=record['status'],phase=record['phase'],error=record['error'],result=result,
                                      kind=record['kind'],generation=record.get('generation')))

    def _cancel(self,record,outcome='cancelled'):
        if record['status'] in TERMINAL:return
        if record in self.queue:
            self._settle(record,outcome,None,None);self.queue.remove(record)
        else:
            record.update(status='cancel_requested',cancel_outcome=outcome)
            if self.active and self.active['record'] is record and self.active['job']:self.active['job'].terminate()

    def cancel(self,request_id):
        identifier(request_id)
        with self.lock:
            record=self.records.get(request_id)
            if record:self._cancel(record)
            return self.status(request_id)

    def save_history(self):
        with self.store.connect(timeout=.05) as db:
            return [dict(request_id=r['id'],status=r['state'],observation_id=r['observation_id'],revision=r['revision'],error=r['error'])
                    for r in db.execute('SELECT * FROM observation_save_requests ORDER BY rowid DESC LIMIT 20')]

    def activity(self):
        with self.lock:
            return [dict(request_id=r['request_id'],kind=r['kind'],status=r['status']) for r in self.records.values() if r['status'] not in TERMINAL]

    def close(self):
        with self.lock:
            self.closed=True
            for record in list(self.records.values()):
                if record['status'] not in TERMINAL:self._cancel(record)
            active=self.active
        if active:
            if active.get('startup_error'):
                with self.lock:self._finish_failed_start(active)
            elif active['thread']:active['thread'].join(5)
        if self.active:raise RuntimeError('Verified reader cleanup incomplete; workspace ownership retained')


def execute(request):
    root=Path(request['root']).resolve();session=identifier(request['session']);request_id=identifier(request['request_id'])
    work=root/'chart-reads'/session/request_id
    try:
        with (work/'request.json').open('rb') as stream:raw=stream.read(1024*1024+1)
        value=json.loads(raw)
        if len(raw)>1024*1024 or digest(value)!=request['request_hash'] or value['request_id']!=request_id:raise ValueError('Verified read request changed')
        store=object.__new__(RunStore);store.root=root;store.database=root/'terminal.sqlite3'
        datasets=DatasetStore(root/'datasets');query=value['query']
        def phase(name):(work/'phase').write_text(name)
        phase('verifying');guard=None
        if value['surface']=='observation':
            manifest=datasets.describe(query['dataset_id'])
            if source_identity(manifest)!=value['expected']:raise ValueError('Exact local history changed after request')
            path=datasets.root/query['dataset_id']/'trade.parquet';identity=file_identity(path.lstat())
            start,end=query['start'],query['end']
            if value['kind']=='save':end=min(end,start+manifest.get('interval_seconds',60))
            page=Observations(store,datasets).window(query['dataset_id'],start,end)
            guard=dict(dataset_id=manifest['id'],source=source_identity(manifest),file_identity=identity)
        else:
            run=store.get(query['run_id'])
            if {'manifest':digest(run['manifest']),'result_hash':run['result_hash']}!=value['expected']:raise ValueError('Saved report identity changed after request')
            def capture_guard(value):
                nonlocal guard
                guard=value
            phase('reading_series');page=store.chart_window(**query,verified=capture_guard)
        if guard:unchanged(datasets.root/guard['dataset_id']/'trade.parquet',guard['file_identity'])
        raw=canonical(dict(page=page,guard=guard))
        if len(raw)>MAX_PAGE:raise ValueError('Chart result exceeds payload budget')
        write_new(work/'result.json',raw);phase('ready')
    except Exception as exc:
        write_new(work/'error.json',canonical({'error':str(exc)[:2000]}));raise
