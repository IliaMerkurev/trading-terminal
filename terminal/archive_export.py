"""Launch-local managed project exports and immutable bounded transfer grants.

No export queue or automatic recovery. Completed ZIPs remain on disk, but all
operation/download authority expires with this service. Import receipts are
independent and unchanged. The owned worker never loads strategy code.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import threading
import uuid

from terminal.data import canonical, digest, write_new
from terminal.storage import RunStore, identifier
from terminal.process_lifecycle import worker_job, worker_options

CHUNK_BYTES = 256 * 1024
MAX_OPERATIONS = 128
MAX_REQUEST = 1024 * 1024
MAX_DESCRIPTOR = 32 * 1024
HASH = re.compile(r'[a-f0-9]{64}')
NOTE = ('Saved in the local exports folder. Dataset descriptions do not guarantee a rerun; '
        'worker logs, consent records and raw candles are excluded. Download access expires when the service stops.')


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def open_regular(path):
    """Check the opened descriptor, not just a path before opening it."""
    if path.parent.is_symlink():raise ValueError('Export directory changed')
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ValueError('Export is not a regular file')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
    stream=os.fdopen(fd,'rb')
    try:
        actual=os.fstat(stream.fileno())
        if not stat.S_ISREG(actual.st_mode) or identity(actual)!=identity(before):raise ValueError('Export changed while opening')
        return stream
    except BaseException:
        stream.close();raise


def validate_descriptor(value,export_id):
    from terminal.archives import MAX_ARCHIVE
    required={'export_id','filename','bytes','sha256','chunk_bytes','chunk_sha256','history_included','note'}
    if not isinstance(value,dict) or set(value)!=required:raise ValueError('Invalid export descriptor')
    if value['export_id']!=export_id or value['filename']!=f'{export_id}.ttproject.zip' or value['history_included'] is not False or value['note']!=NOTE:raise ValueError('Invalid export identity')
    if type(value['bytes']) is not int or not 1<=value['bytes']<=MAX_ARCHIVE or value['chunk_bytes']!=CHUNK_BYTES:raise ValueError('Invalid export bounds')
    hashes=value['chunk_sha256']
    if not isinstance(hashes,list) or len(hashes)!=(value['bytes']+CHUNK_BYTES-1)//CHUNK_BYTES:raise ValueError('Invalid export chunk count')
    if any(not isinstance(h,str) or not HASH.fullmatch(h) for h in [value['sha256'],*hashes]):raise ValueError('Invalid export checksum')
    return value


class ExportManager:
    def __init__(self,jobs):
        self.jobs=jobs;self.store=jobs.store
        self.lock=threading.RLock();self.records={};self.active=None
        self.session=uuid.uuid4().hex
        self.directory=self.store.root/'exports'
        self.staging=self.directory/('.pending-'+self.session)
        self.closed=False

    def start(self,request_id,strategy,profile,run_ids):
        from terminal.archives import validate_strategy
        from terminal.profile import Profile
        identifier(request_id)
        raw=canonical({'strategy':strategy,'profile':profile,'run_ids':run_ids})
        if len(raw)>MAX_REQUEST:raise ValueError('Export request exceeds 1 MiB')
        request=json.loads(raw);request_hash=hashlib.sha256(raw).hexdigest()
        with self.lock:
            if self.closed:raise ValueError('Export service is stopping')
            previous=self.records.get(request_id)
            if previous:
                if previous['request_sha256']!=request_hash:raise ValueError('Export request identity was reused with different inputs')
                return self.status(request_id)
            if len(self.records)>=MAX_OPERATIONS:raise ValueError('Export session history is full; inspect existing exports or restart the service')
            validate_strategy(request['strategy']);Profile(**request['profile'])
            ids=request['run_ids']
            if not isinstance(ids,list) or len(ids)>8 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):raise ValueError('Choose up to eight different saved runs')
            for ident in ids:identifier(ident)
            expected={}
            # Small completion metadata only. The worker verifies full immutable
            # content and manifest digest against these frozen identities.
            with self.store.connect() as db:
                for ident in ids:
                    row=db.execute("SELECT status,result_hash,json_extract(summary,'$.snapshot') AS snapshot_sha256 FROM runs WHERE id=?",(ident,)).fetchone()
                    if not row or row['status']!='completed' or not row['result_hash'] or not row['snapshot_sha256']:raise ValueError('Select completed saved runs')
                    expected[ident]={'result_hash':row['result_hash'],'snapshot_sha256':row['snapshot_sha256']}
            owner='export:'+request_id
            with self.jobs.lock:
                self.jobs.require_storage_ready()
                if self.jobs.active or self.jobs.reservation or self.active:raise ValueError('One calculation, batch or archive operation is already active')
                self.jobs.reservation=owner
            record={'export_id':request_id,'request_sha256':request_hash,'status':'running','phase':'starting','descriptor':None,'error':None}
            self.records[request_id]=record
            try:
                if self.directory.is_symlink() or self.staging.is_symlink():raise ValueError('Export directories cannot be symbolic links')
                work=self.staging/request_id;work.mkdir(parents=True,exist_ok=False)
                frozen={**request,'expected':expected}
                frozen_raw=canonical(frozen);record['frozen_sha256']=hashlib.sha256(frozen_raw).hexdigest()
                write_new(work/'request.json',frozen_raw)
                self._launch(record,work,owner)
            except Exception:
                if not self.active:
                    record.update(status='failed',phase='terminal',error='Export could not start; no download was granted')
                    with self.jobs.lock:
                        if self.jobs.reservation==owner:self.jobs.reservation=None
                raise
            return self.status(request_id)

    def _launch(self,record,work,owner):
        job=None;process=None;anchor=None;active=None
        try:
            anchor=sqlite3.connect(self.store.database,timeout=15,check_same_thread=False)
            anchor.execute('SELECT count(*) FROM sqlite_master').fetchone()
            job=worker_job(self.jobs.instance_file)
            process=subprocess.Popen([sys.executable,'-m','terminal.worker'],cwd=Path(__file__).resolve().parents[1],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**worker_options(job))
            active={'record':record,'work':work,'owner':owner,'process':process,'job':job,'anchor':anchor}
            monitor=threading.Thread(target=self._monitor,args=(active,),daemon=True);active['monitor']=monitor;self.active=active
            job.assign(process)
            # The potentially large frozen request is already on disk. The
            # supervised stdin gate receives only fixed-size generated IDs.
            process.stdin.write(canonical({'version':1,'command':'archive_export','root':str(self.store.root),'session':self.session,'export_id':record['export_id'],'request_sha256':record['frozen_sha256']})+b'\n')
            process.stdin.close();monitor.start()
        except Exception:
            record['error']='Export process could not start'
            try:
                if job:job.close()
            finally:
                if process:
                    if process.stdin and not process.stdin.closed:
                        try:process.stdin.close()
                        except OSError:pass
                    if active and active['monitor'].ident is None:active['monitor'].start()
                elif anchor:anchor.close()
            raise

    def _monitor(self,active):
        record=active['record'];work=active['work']
        try:
            while active['process'].poll() is None:
                try:
                    path=work/'progress.jsonl'
                    if path.exists():
                        with path.open('rb') as stream:
                            stream.seek(max(0,path.stat().st_size-4096));lines=stream.read(4096).splitlines()
                        phase=json.loads(lines[-1])['phase'] if lines else 'starting'
                        if phase in ('read_verify','encode_privacy','compress_validate','publish'):
                            with self.lock:record['phase']=phase
                except (OSError,ValueError,KeyError):pass
                try:active['process'].wait(timeout=.05)
                except subprocess.TimeoutExpired:pass
            active['process'].wait();active['job'].close()
        except Exception:
            with self.lock:record['error']='Export process cleanup is incomplete; workspace ownership retained'
            return
        try:
            with self.lock:
                if record['status'] in ('completed','failed','cancelled'):pass  # Cleanup retry never re-settles a terminal outcome.
                elif record['status']=='cancel_requested':record.update(status='cancelled',phase='terminal')
                elif active['process'].returncode==0 and (work/'descriptor.json').is_file():self._publish(record,work)
                else:
                    error='Export worker failed or was interrupted; no download was granted'
                    path=work/'error.json'
                    if path.is_file() and path.stat().st_size<=4096:
                        try:error=json.loads(path.read_bytes())['error']
                        except (OSError,ValueError,KeyError):pass
                    record.update(status='failed',phase='terminal',error=error)
        except Exception:
            with self.lock:
                # Never erase a completion-winning publication after an
                # acknowledgement/cleanup failure.
                if record['status']!='completed':record.update(status='failed',phase='terminal',error='Export publication failed; no download was granted')
        finally:
            try:shutil.rmtree(work)
            except OSError:pass  # Abandoned staging is never a download grant.
            try:active['anchor'].close()
            except Exception:
                with self.lock:
                    if record['error'] is None:record['error']='Export cleanup incomplete; workspace ownership retained'
                return
            with self.lock:
                if record['error']=='Export cleanup incomplete; workspace ownership retained':record['error']=None
                if self.active is active:
                    with self.jobs.lock:
                        if self.jobs.reservation==active['owner']:self.jobs.reservation=None
                    self.active=None

    def _publish(self,record,work):
        path=work/'descriptor.json'
        with open_regular(path) as stream:
            raw=stream.read(MAX_DESCRIPTOR+1)
        if len(raw)>MAX_DESCRIPTOR:raise ValueError('Export descriptor exceeds budget')
        payload=json.loads(raw);descriptor=validate_descriptor(payload['descriptor'],record['export_id'])
        stage=work/'archive.partial';target=self.directory/descriptor['filename']
        if self.directory.is_symlink():raise ValueError('Export directory changed')
        with open_regular(stage) as stream:
            original=identity(os.fstat(stream.fileno()))
            if original!=payload['file_identity'] or original[2]!=descriptor['bytes']:raise ValueError('Staged export changed')
        # Close before unlink/rename: Windows ordinary file handles do not
        # grant FILE_SHARE_DELETE. The target descriptor is checked afterward.
        if identity(stage.lstat())!=original:raise ValueError('Staged export changed')
        if os.name=='nt':os.rename(stage,target)  # Atomic, no replace on Windows.
        else:
            os.link(stage,target,follow_symlinks=False)
            stage.unlink()
        with open_regular(target) as stream:
            fingerprint=identity(os.fstat(stream.fileno()))
            if fingerprint[:4]!=original[:4] or identity(target.lstat())!=fingerprint:raise ValueError('Published export changed')
        record.update(status='completed',phase='terminal',descriptor=descriptor,file_identity=fingerprint,error=None)

    def status(self,export_id):
        identifier(export_id)
        with self.lock:
            record=self.records.get(export_id)
            if record is None:raise ValueError('Export is unavailable in this service session; unfinished exports never resume after restart')
            return copy.deepcopy({k:record[k] for k in ('export_id','status','phase','descriptor','error')})

    def recent(self):
        with self.lock:
            return [{'export_id':r['export_id'],'status':r['status'],'phase':r['phase']} for r in reversed(list(self.records.values()))]

    def cancel(self,export_id):
        identifier(export_id)
        with self.lock:
            record=self.records.get(export_id)
            if record is None:raise ValueError('Export is unavailable in this service session')
            if record['status'] in ('completed','failed','cancelled'):return {'export_id':export_id,'status':'too_late' if record['status']=='completed' else record['status']}
            record['status']='cancel_requested'
            if self.active and self.active['record'] is record:self.active['job'].terminate()
            return {'export_id':export_id,'status':'cancel_requested'}

    def chunk(self,export_id,filename,offset,size):
        identifier(export_id)
        with self.lock:
            record=self.records.get(export_id)
            if self.closed or not record or record['status']!='completed':raise ValueError('Export is not available in this session')
            descriptor=record['descriptor'];fingerprint=record['file_identity']
        if filename!=descriptor['filename'] or type(offset) is not int or type(size) is not int or offset<0 or offset%CHUNK_BYTES or offset>=descriptor['bytes'] or size!=min(CHUNK_BYTES,descriptor['bytes']-offset):raise ValueError('Invalid bounded export chunk')
        path=self.directory/filename
        with open_regular(path) as stream:
            if identity(os.fstat(stream.fileno()))!=fingerprint:raise ValueError('Export changed after creation')
            stream.seek(offset);raw=stream.read(size)
            if identity(os.fstat(stream.fileno()))!=fingerprint or identity(path.lstat())!=fingerprint or self.directory.is_symlink():raise ValueError('Export changed during transfer')
        if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=descriptor['chunk_sha256'][offset//CHUNK_BYTES]:raise ValueError('Export chunk checksum mismatch')
        return raw

    def close(self):
        with self.lock:self.closed=True;active=self.active
        if active:
            self.cancel(active['record']['export_id'])
            if active['monitor'].ident is None:active['monitor'].start()
            active['monitor'].join(timeout=10)
            if not active['monitor'].is_alive() and active['process'].poll() is not None and self.active is active:self._monitor(active)
            if self.active is not None:raise RuntimeError('Export shutdown incomplete; workspace ownership retained')


def execute(request):
    from terminal.archives import build_export
    root=Path(request['root']).resolve();session=identifier(request['session']);export_id=identifier(request['export_id'])
    work=root/'exports'/('.pending-'+session)/export_id
    try:
        with open_regular(work/'request.json') as stream:
            before=identity(os.fstat(stream.fileno()));raw=stream.read(MAX_REQUEST+16384)
            if identity(os.fstat(stream.fileno()))!=before or identity((work/'request.json').lstat())!=before:raise ValueError('Frozen export request changed')
        if hashlib.sha256(raw).hexdigest()!=request['request_sha256']:raise ValueError('Frozen export request checksum changed')
        if len(raw)>=MAX_REQUEST+16384:raise ValueError('Export request exceeds budget')
        frozen=json.loads(raw)
        store=object.__new__(RunStore);store.root=root;store.database=root/'terminal.sqlite3'
        def progress(phase):
            with (work/'progress.jsonl').open('ab') as stream:stream.write(canonical({'phase':phase})+b'\n')
        raw=build_export(store,frozen['strategy'],frozen['profile'],frozen['run_ids'],expected=frozen['expected'],progress=progress)
        progress('publish')
        descriptor={'export_id':export_id,'filename':f'{export_id}.ttproject.zip','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'chunk_bytes':CHUNK_BYTES,
                    'chunk_sha256':[hashlib.sha256(raw[i:i+CHUNK_BYTES]).hexdigest() for i in range(0,len(raw),CHUNK_BYTES)],'history_included':False,'note':NOTE}
        validate_descriptor(descriptor,export_id)
        stage=work/'archive.partial';write_new(stage,raw)
        write_new(work/'descriptor.json',canonical({'descriptor':descriptor,'file_identity':identity(stage.stat())}))
    except Exception as exc:
        # Privacy errors contain categories and entry names only. Other errors
        # must not expose source payloads, credentials or local paths.
        message=str(exc) if isinstance(exc,ValueError) and str(exc).startswith('Export withheld:') else 'Export validation or storage failed; verify selected saved reports and available storage'
        write_new(work/'error.json',canonical({'error':message}));raise
