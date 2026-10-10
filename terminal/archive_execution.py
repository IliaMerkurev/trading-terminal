"""Versioned import execution controls; retained receipts remain schema 1.

Only explicit start/resume creates an attempt. Recovery is metadata-only. Bulk
validation and staging run in an application-owned process, never in IPC.
"""
from pathlib import Path
from contextlib import contextmanager
import time
import hashlib
import json
import sqlite3
import subprocess
import sys
import threading
import uuid

from terminal.archive_receipts import ArchiveReceipts, now
from terminal.data import canonical, digest, write_new
from terminal.storage import RunStore, SERIES, identifier
from terminal.process_lifecycle import worker_job, worker_options

BATCH_ROWS = 128
BATCH_BYTES = 256 * 1024


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS archive_recovery_sources(operation_id TEXT PRIMARY KEY, upload_id TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS archive_execution(
            operation_id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version=1),
            revision INTEGER NOT NULL, attempt_key TEXT NOT NULL,
            state TEXT NOT NULL, phase TEXT NOT NULL,
            staged_rows INTEGER NOT NULL DEFAULT 0, total_rows INTEGER,
            cancel_requested_at TEXT, cancel_acknowledged_at TEXT,
            termination_reason TEXT, error_code TEXT);
        CREATE TABLE IF NOT EXISTS archive_attempts(
            operation_id TEXT NOT NULL, attempt_key TEXT NOT NULL, revision INTEGER NOT NULL,
            started_at TEXT NOT NULL, terminal_at TEXT, outcome TEXT, reason TEXT,
            prior_receipt TEXT NOT NULL,
            PRIMARY KEY(operation_id,attempt_key), UNIQUE(operation_id,revision));
    ''')


class Stopped(Exception):
    pass


class Conflict(ValueError):
    pass


def guard(db, operation_id, attempt_key):
    row = db.execute('SELECT * FROM archive_execution WHERE operation_id=?', (operation_id,)).fetchone()
    if not row or row['attempt_key'] != attempt_key or row['state'] != 'running':
        raise Stopped('Import attempt is no longer active')
    return row


def settle(store, operation_id, reason, expected_key=None):
    """Only call after process reaping (or exclusive startup ownership)."""
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        control = db.execute('SELECT * FROM archive_execution WHERE operation_id=?', (operation_id,)).fetchone()
        if not control or control['state']=='terminal' or (expected_key is not None and control['attempt_key']!=expected_key):
            return
        receipt = db.execute('SELECT * FROM archive_imports WHERE operation_id=?', (operation_id,)).fetchone()
        stamp = now()
        if receipt['outcome'] != 'completed' and receipt['phase'] != 'terminal':
            published = db.execute("SELECT count(*) FROM archive_import_items WHERE operation_id=? AND publication_state='published'", (operation_id,)).fetchone()[0]
            outcome = 'partial' if published else 'cancelled' if reason == 'user_cancelled' else 'interrupted' if reason in ('process_restart','worker_interrupted') else 'rejected' if reason=='validation_rejected' and receipt['expected_run_count'] is None else 'failed'
            db.execute("UPDATE archive_import_items SET publication_state='incomplete' WHERE operation_id=? AND publication_state='writing'", (operation_id,))
            db.execute("UPDATE runs SET status='interrupted' WHERE id IN (SELECT destination_id FROM archive_import_items WHERE operation_id=? AND kind='run' AND publication_state!='published') AND status!='completed'", (operation_id,))
            db.execute("UPDATE archive_imports SET phase='terminal',outcome=?,termination_reason=?,terminal_at=?,updated_at=? WHERE operation_id=?", (outcome, 'process_restart' if reason == 'process_restart' else 'storage_failure' if reason == 'storage_failure' else 'validation_rejected' if reason=='validation_rejected' else None, stamp, stamp, operation_id))
        receipt = db.execute('SELECT outcome FROM archive_imports WHERE operation_id=?', (operation_id,)).fetchone()
        reason = 'finished' if receipt['outcome'] == 'completed' else reason
        db.execute("UPDATE archive_execution SET state='terminal',phase='terminal',termination_reason=?,cancel_acknowledged_at=? WHERE operation_id=?", (reason, stamp if reason == 'user_cancelled' else None, operation_id))
        db.execute('UPDATE archive_attempts SET terminal_at=?,outcome=?,reason=? WHERE operation_id=? AND attempt_key=? AND terminal_at IS NULL', (stamp, receipt['outcome'], reason, operation_id, control['attempt_key']))


def reconcile(store):
    with store.connect() as db:
        ids = [row[0] for row in db.execute("SELECT operation_id FROM archive_execution WHERE state!='terminal'")]
    for operation_id in ids:
        settle(store, operation_id, 'process_restart')


class ImportWorker:
    def __init__(self, manager):
        self.manager = manager
        self.store = manager.store
        self.jobs = manager.jobs
        self.lock = threading.RLock()
        self.active = None

    def start(self, operation_id, expected_revision=None, attempt_key=None):
        operation_id = identifier(operation_id)
        resume = attempt_key is not None
        if resume:
            identifier(attempt_key)
            if type(expected_revision) is not int or expected_revision < 0:
                raise ValueError('Invalid import revision')
        # This lock covers only local ownership transitions, not worker execution.
        with self.lock:
            with self.store.connect() as db:
                row = db.execute('SELECT * FROM archive_imports WHERE operation_id=?', (operation_id,)).fetchone()
                control = db.execute('SELECT * FROM archive_execution WHERE operation_id=?', (operation_id,)).fetchone()
                duplicate = resume and db.execute('SELECT attempt_key,revision,started_at,terminal_at,outcome,reason FROM archive_attempts WHERE operation_id=? AND attempt_key=?', (operation_id, attempt_key)).fetchone()
            if not row:
                raise ValueError('Import receipt does not exist')
            if duplicate or row['outcome'] == 'completed' or (not resume and (control or row['phase'] != 'receiving')):
                status=self.manager.status(operation_id)
                status['acknowledged_attempt']=dict(duplicate) if duplicate else status['execution']
                return status
            self.manager._ready()
            if self.jobs is None:
                raise ValueError('Managed import requires workspace ownership')
            if resume:
                if self.manager.upload is not None:raise ValueError('Finish or cancel the receiving transfer before continuing another import')
                if row['phase'] != 'terminal' or row['outcome'] not in ('partial','interrupted','failed','cancelled') or (control and control['state'] != 'terminal'):
                    raise ValueError('Import is not eligible for explicit continuation')
                with self.store.connect() as db:
                    items=db.execute('SELECT * FROM archive_import_items WHERE operation_id=?',(operation_id,)).fetchall()
                    if self.manager.receipts._inconsistent(db,row,items,metadata_only=True):raise ValueError('Inconsistent receipt cannot be continued')
                if (control['revision'] if control else 0) != expected_revision:
                    raise ValueError('Import revision changed; inspect before continuing')
            else:
                upload = self.manager.upload
                if not upload or upload['id'] != operation_id or upload['offset'] != upload['size']:
                    raise ValueError('Archive transfer is incomplete')
            owner = 'archive:' + operation_id
            with self.jobs.lock:
                self.jobs.require_storage_ready()
                if self.jobs.active or self.jobs.reservation or self.active:
                    raise ValueError('One calculation, batch or archive import is already active')
                self.jobs.reservation = owner
            key = attempt_key if resume else uuid.uuid4().hex
            claimed=False;launching=False
            try:
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    current = db.execute('SELECT * FROM archive_imports WHERE operation_id=?', (operation_id,)).fetchone()
                    if dict(current) != dict(row):
                        raise ValueError('Import changed; inspect before continuing')
                    revision = (control['revision'] if control else 0) + 1
                    db.execute('INSERT INTO archive_attempts VALUES(?,?,?,?,NULL,NULL,NULL,?)', (operation_id, key, revision, now(), canonical(dict(row)).decode()))
                    db.execute('''INSERT INTO archive_execution(operation_id,version,revision,attempt_key,state,phase)
                        VALUES(?,1,?,?,'running','validating') ON CONFLICT(operation_id) DO UPDATE SET
                        revision=excluded.revision,attempt_key=excluded.attempt_key,state='running',phase='verifying',
                        staged_rows=0,total_rows=NULL,cancel_requested_at=NULL,cancel_acknowledged_at=NULL,termination_reason=NULL,error_code=NULL''', (operation_id, revision, key))
                    db.execute("UPDATE archive_imports SET phase=?,outcome=NULL,termination_reason=NULL,error_code=NULL,terminal_at=NULL,updated_at=? WHERE operation_id=?", ('publishing' if row['expected_run_count'] is not None else 'validating', now(), operation_id))
                claimed=True;launching=True
                self.manager.upload = None
                self._launch(operation_id, key, owner)
            except Exception as exc:
                if isinstance(exc,sqlite3.Error) or (not launching and isinstance(exc,OSError)):
                    self.manager._storage_failure(operation_id)
                if self.active is None:
                    try:
                        # A post-commit exception may hide a successful claim;
                        # prove its exact key before settling anything. Never
                        # rewrite the preceding terminal attempt on rollback.
                        if not claimed:
                            with self.store.connect() as db:
                                current=db.execute('SELECT attempt_key,state FROM archive_execution WHERE operation_id=?',(operation_id,)).fetchone()
                            claimed=bool(current and current['attempt_key']==key and current['state']!='terminal')
                        if claimed:settle(self.store,operation_id,'launch_failure',expected_key=key)
                    finally:
                        with self.jobs.lock:
                            if self.jobs.reservation == owner:self.jobs.reservation = None
                raise
        return self.manager.status(operation_id)

    def _launch(self, operation_id, key, owner):
        job = None; process = None; anchor = None; active = None
        try:
            anchor = sqlite3.connect(self.store.database, timeout=15, check_same_thread=False)
            anchor.execute('SELECT count(*) FROM sqlite_master').fetchone()
            job = worker_job(self.jobs.instance_file)
            process = subprocess.Popen([sys.executable,'-m','terminal.worker'], cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **worker_options(job))
            # Ownership exists before assignment/bootstrap can fail. A cleanup
            # timeout must never expose the workspace while this process lives.
            active = {'operation_id':operation_id,'key':key,'owner':owner,'process':process,'job':job,'anchor':anchor}
            monitor = threading.Thread(target=self._monitor, args=(active,), daemon=True)
            active['monitor'] = monitor; self.active = active
            job.assign(process)
            process.stdin.write(canonical({'version':1,'command':'archive_import','root':str(self.store.root),'operation_id':operation_id,'attempt_key':key})+b'\n')
            process.stdin.close()
            monitor.start()
        except Exception:
            if job:job.close()
            if process:
                if process.stdin and not process.stdin.closed:
                    try:process.stdin.close()
                    except OSError:pass
                try:
                    with self.store.connect() as db:db.execute("UPDATE archive_execution SET termination_reason='launch_failure' WHERE operation_id=? AND attempt_key=?",(operation_id,key))
                finally:
                    # Reaping and settlement stay asynchronous and owned even
                    # if platform cleanup cannot finish in the usual interval.
                    if active and active['monitor'].ident is None:active['monitor'].start()
            elif anchor:anchor.close()
            raise

    def _monitor(self, active):
        try:
            active['process'].wait()
            active['job'].close()
        except Exception:
            self.manager._storage_failure(active['operation_id'])
            return  # Keep anchor, reservation and ownership until cleanup is proved.
        try:
            with self.store.connect() as db:
                row = db.execute('SELECT state,termination_reason FROM archive_execution WHERE operation_id=?', (active['operation_id'],)).fetchone()
            reason = 'user_cancelled' if row['state'] == 'cancel_requested' else row['termination_reason'] or 'worker_interrupted'
            settle(self.store, active['operation_id'], reason, expected_key=active['key'])
            if reason == 'storage_failure' or row['termination_reason']=='storage_failure':self.manager._storage_failure(active['operation_id'])
        except Exception:
            self.manager._storage_failure(active['operation_id'])
        finally:
            active['anchor'].close()
            with self.lock:
                if self.active is active:
                    with self.jobs.lock:
                        if self.jobs.reservation == active['owner']:self.jobs.reservation = None
                    self.active = None

    def cancel(self, operation_id, attempt_key=None):
        identifier(operation_id)
        with self.lock:
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT phase,outcome FROM archive_imports WHERE operation_id=?', (operation_id,)).fetchone()
                if not row:raise ValueError('Import receipt does not exist')
                control = db.execute('SELECT * FROM archive_execution WHERE operation_id=?', (operation_id,)).fetchone()
                if not control:return None
                if attempt_key is None:return {'operation_id':operation_id,'status':'attempt_required'}
                if identifier(attempt_key)!=control['attempt_key']:return {'operation_id':operation_id,'status':'stale_attempt'}
                if row['outcome'] == 'completed' or control['state'] == 'terminal':
                    return {'operation_id':operation_id,'status':'too_late' if row['outcome']=='completed' else control['state']}
                db.execute("UPDATE archive_execution SET state='cancel_requested',cancel_requested_at=COALESCE(cancel_requested_at,?) WHERE operation_id=?", (now(), operation_id))
            if self.active and self.active['operation_id'] == operation_id:self.active['job'].terminate()
        return {'operation_id':operation_id,'status':'cancel_requested'}

    def close(self):
        with self.lock:active = self.active
        if active:
            self.cancel(active['operation_id'],active['key'])
            active['monitor'].join(timeout=10)
            if active['monitor'].is_alive() or active['process'].poll() is None:
                raise RuntimeError('Archive worker shutdown incomplete; workspace ownership retained')


def _progress(store, operation_id, key, phase, staged=0, total=None):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE');guard(db,operation_id,key)
        db.execute('UPDATE archive_execution SET phase=?,staged_rows=?,total_rows=? WHERE operation_id=?', (phase,staged,total,operation_id))


def _check_file(path, expected):
    if path.is_symlink() or path.parent.is_symlink():raise Conflict('Unexpected symbolic link at reserved artifact')
    if path.exists() and (not path.is_file() or (path.stat().st_size!=len(expected) or path.read_bytes() != expected)):raise Conflict('Reserved artifact differs from expected content')


def execute(request):
    from terminal.archives import read_archive
    root = Path(request['root']).resolve()
    operation_id = identifier(request['operation_id']); key = identifier(request['attempt_key'])
    store = object.__new__(RunStore);store.root=root;store.database=root/'terminal.sqlite3'
    if (root/'runs').is_symlink() or (root/'imports').is_symlink():raise Conflict('Workspace artifact directories cannot be symbolic links')
    original_connect=store.connect
    maximum=0.0
    @contextmanager
    def measured_connect():
        nonlocal maximum
        began=[]
        with original_connect() as db:
            db.set_trace_callback(lambda sql:began.append(time.monotonic()) if sql=='BEGIN IMMEDIATE' else None)
            yield db
        if began:
            elapsed=time.monotonic()-began[0]
            if elapsed>maximum:
                maximum=elapsed
                with (root/'imports'/f'{key}.timings.jsonl').open('ab') as stream:stream.write(canonical({'max_write_seconds':maximum})+b'\n')
    store.connect=measured_connect
    receipts = ArchiveReceipts(store)
    try:
        _progress(store,operation_id,key,'validating')
        path = root/'imports'/f'{operation_id}.partial'
        if path.is_symlink():raise Conflict('Retained archive path is a symbolic link')
        if not path.exists():
            with store.connect() as db:
                recovery=db.execute('SELECT upload_id FROM archive_recovery_sources WHERE operation_id=?',(operation_id,)).fetchone()
            if recovery:
                path=root/'imports'/f'{identifier(recovery[0])}.recovery'
                if path.is_symlink():raise Conflict('Recovery archive path is a symbolic link')
        with store.connect() as db:
            expected_bytes=db.execute('SELECT expected_bytes FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()[0]
        if path.stat().st_size!=expected_bytes:raise Conflict('Retained archive size changed')
        raw = path.read_bytes()
        with store.connect() as db:
            guard(db,operation_id,key)
            receipt = dict(db.execute('SELECT * FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone())
        if len(raw)!=receipt['expected_bytes'] or (receipt['archive_sha256'] and hashlib.sha256(raw).hexdigest()!=receipt['archive_sha256']):raise Conflict('Retained archive bytes do not match the original import')
        project,documents = read_archive(raw)
        _progress(store,operation_id,key,'verifying')
        if receipt['expected_run_count'] is None:
            receipts.reserve(operation_id,raw,project,documents,attempt_key=key)
        else:
            content = digest({'version':1,'entries':[[name,digest(documents[name])] for name in sorted(documents)]})
            if content != receipt['validated_content_sha256']:raise Conflict('Validated archive identity changed')
        with store.connect() as db:
            items = [dict(row) for row in db.execute('SELECT * FROM archive_import_items WHERE operation_id=? ORDER BY kind,ordinal',(operation_id,))]
        runs = [item for item in items if item['kind']=='run'];strategies=[item for item in items if item['kind']=='strategy']
        if receipt['expected_run_count'] is not None and receipt['expected_run_count']!=len(project['runs']):raise Conflict('Reserved run count changed')
        if any(item['publication_state'] not in ('reserved','writing','incomplete','published') for item in runs) or len(runs)!=len(project['runs']) or len(strategies)!=1 or strategies[0]['ordinal']!=0 or strategies[0]['publication_state']!='reserved' or strategies[0]['expected_strategy_sha256']!=digest({**project['strategy'],'profile':project['profile']}):raise Conflict('Reserved import mapping changed')
        # Verify EVERY prior publication before permitting any continuation writes.
        for ordinal,(item,source) in enumerate(zip(runs,project['runs'])):
            snapshot=documents[f'runs/{source}/snapshot.json'];result=documents[f'runs/{source}/result.json']
            if item['ordinal']!=ordinal or item['source_run_id']!=source or item['expected_snapshot_sha256']!=digest(snapshot) or item['expected_result_sha256']!=digest(result) or json.loads(item['expected_series_counts'])!={kind:len(result[kind]) for kind in SERIES}:raise Conflict('Reserved run identity changed')
            verify_run(store,item,snapshot,result)
            _progress(store,operation_id,key,'verifying')
        with store.connect() as db:
            if db.execute('SELECT 1 FROM strategies WHERE id=?',(strategies[0]['destination_id'],)).fetchone():raise Conflict('Reserved strategy destination already exists')
        total=sum(len(documents[f'runs/{source}/result.json'][kind]) for source in project['runs'] for kind in SERIES)
        staged=0
        for item,source in zip(runs,project['runs']):
            snapshot=documents[f'runs/{source}/snapshot.json'];result=documents[f'runs/{source}/result.json']
            staged=publish_run(store,operation_id,key,item,snapshot,result,staged,total)
        # A cancellation claim and final completion compete in this same short transaction.
        envelope=project['strategy'];stamp=now()
        document=canonical(envelope['document']).decode();profile=canonical(project['profile']).decode()
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');guard_item(db,operation_id,key,strategies[0],('reserved',))
            count=db.execute("SELECT count(*) FROM archive_import_items WHERE operation_id=? AND kind='run' AND publication_state='published'",(operation_id,)).fetchone()[0]
            if count!=len(runs):raise Conflict('Import reports are incomplete')
            db.execute('INSERT INTO strategies(id,name,kind,document,updated_at,profile) VALUES(?,?,?,?,?,?)',(strategies[0]['destination_id'],envelope['name'],envelope['kind'],document,stamp,profile))
            ArchiveReceipts._changed(db.execute("UPDATE archive_import_items SET publication_state='published',published_at=? WHERE operation_id=? AND kind='strategy' AND publication_state='reserved'",(stamp,operation_id)))
            ArchiveReceipts._changed(db.execute("UPDATE archive_imports SET phase='terminal',outcome='completed',termination_reason='finished',terminal_at=?,updated_at=? WHERE operation_id=? AND phase='publishing'",(stamp,stamp,operation_id)))
    except Stopped:
        pass
    except Exception as exc:
        reason='storage_failure' if isinstance(exc,(OSError,sqlite3.Error)) and not isinstance(exc,FileNotFoundError) else 'input_conflict' if isinstance(exc,(Conflict,FileNotFoundError)) else 'validation_rejected'
        try:
            with store.connect() as db:
                db.execute('UPDATE archive_execution SET termination_reason=?,error_code=? WHERE operation_id=? AND attempt_key=? AND state=\'running\'',(reason,reason,operation_id,key))
        except Exception:pass
        raise


def verify_run(store,item,snapshot,result):
    ident=identifier(item['destination_id']);directory=store.directory(ident)
    expected_snapshot=canonical(snapshot);expected_result=canonical(result)
    _check_file(directory/'snapshot.json',expected_snapshot);_check_file(directory/'result.json',expected_result)
    published=item['publication_state']=='published'
    if published and (not (directory/'snapshot.json').is_file() or not (directory/'result.json').is_file()):raise Conflict('Published artifact is missing')
    with store.connect() as db:
        run=db.execute('SELECT * FROM runs WHERE id=?',(ident,)).fetchone()
        expected_summary=canonical({'metrics':result['metrics'],'profile':result['profile'],'engine':result['engine'],'engine_version':result['engine_version'],'metric_version':result['metric_version'],'dataset':snapshot['dataset']['id'],'snapshot':result['manifest_sha256'],'origin':'imported','history_omitted':result.get('history_omitted',False)}).decode()
        if published and run and run['summary']!=expected_summary:raise Conflict('Published summary or imported provenance changed')
        if not run or run['manifest']!=expected_snapshot.decode() or (published and (run['status']!='completed' or run['result_hash']!=item['expected_result_sha256'])) or (not published and run['status'] not in ('importing','interrupted')):raise Conflict('Reserved run placeholder changed')
        counts={kind:0 for kind in SERIES}
        for row in db.execute('SELECT kind,row_index,value FROM series WHERE run_id=? ORDER BY kind,row_index',(ident,)):
            kind,index,value=row
            if kind not in SERIES or not 0<=index<len(result[kind]) or value!=canonical(result[kind][index]).decode():raise Conflict('Staged normalized content changed')
            counts[kind]+=1
        if published and counts!={kind:len(result[kind]) for kind in SERIES}:raise Conflict('Published normalized content is incomplete')


def guard_item(db,operation_id,key,item,states):
    guard(db,operation_id,key)
    current=db.execute('SELECT * FROM archive_import_items WHERE operation_id=? AND kind=? AND ordinal=?',(operation_id,item['kind'],item['ordinal'])).fetchone()
    operation=db.execute('SELECT phase FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()
    fields=('destination_id','source_run_id','expected_snapshot_sha256','expected_result_sha256','expected_strategy_sha256','expected_series_counts')
    if not current or not operation or operation['phase']!='publishing' or current['publication_state'] not in states or any(current[field]!=item[field] for field in fields):raise Conflict('Import reservation changed before publication')
    if item['kind']=='run':
        run=db.execute('SELECT status FROM runs WHERE id=?',(item['destination_id'],)).fetchone()
        if not run or run[0] not in ('importing','interrupted'):raise Conflict('Import placeholder changed before publication')


def publish_run(store,operation_id,key,item,snapshot,result,staged,total):
    count=sum(len(result[kind]) for kind in SERIES)
    if item['publication_state']=='published':return staged+count
    ident=item['destination_id'];directory=store.directory(ident)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE');guard_item(db,operation_id,key,item,('reserved','writing','incomplete'))
        db.execute("UPDATE runs SET status='importing' WHERE id=? AND status IN ('importing','interrupted')",(ident,))
        db.execute("UPDATE archive_import_items SET publication_state='writing',publication_started_at=COALESCE(publication_started_at,?) WHERE operation_id=? AND kind='run' AND ordinal=?",(now(),operation_id,item['ordinal']))
    write_new(directory/'snapshot.json',canonical(snapshot));write_new(directory/'result.json',canonical(result))
    for kind in SERIES:
        batch=[];size=0
        def commit():
            nonlocal staged
            if not batch:return
            with store.connect() as db:
                db.execute('BEGIN IMMEDIATE');guard_item(db,operation_id,key,item,('writing',))
                for index,value in batch:
                    old=db.execute('SELECT value FROM series WHERE run_id=? AND kind=? AND row_index=?',(ident,kind,index)).fetchone()
                    if old:
                        if old[0]!=value:raise Conflict('Staged normalized content changed')
                    else:db.execute('INSERT INTO series VALUES(?,?,?,?)',(ident,kind,index,value))
                staged+=len(batch)
                db.execute("UPDATE archive_execution SET phase='staging',staged_rows=?,total_rows=? WHERE operation_id=?",(staged,total,operation_id))
        for index,row in enumerate(result[kind]):
            value=canonical(row).decode();length=len(value.encode())
            if batch and (len(batch)>=BATCH_ROWS or size+length>BATCH_BYTES):commit();batch=[];size=0
            batch.append((index,value));size+=length
        commit()
    summary=canonical({'metrics':result['metrics'],'profile':result['profile'],'engine':result['engine'],'engine_version':result['engine_version'],'metric_version':result['metric_version'],'dataset':snapshot['dataset']['id'],'snapshot':result['manifest_sha256'],'origin':'imported','history_omitted':result.get('history_omitted',False)}).decode()
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE');guard_item(db,operation_id,key,item,('writing',))
        counts={row[0]:row[1] for row in db.execute('SELECT kind,count(*) FROM series WHERE run_id=? GROUP BY kind',(ident,))}
        if any(counts.get(kind,0)!=len(result[kind]) for kind in SERIES) or set(counts)-set(SERIES):raise Conflict('Staged normalized row counts changed')
        ArchiveReceipts._changed(db.execute("UPDATE runs SET status='completed',error=NULL,result_hash=?,summary=? WHERE id=? AND status='importing'",(item['expected_result_sha256'],summary,ident)))
        ArchiveReceipts._changed(db.execute("UPDATE archive_import_items SET publication_state='published',published_at=? WHERE operation_id=? AND kind='run' AND ordinal=? AND publication_state='writing'",(now(),operation_id,item['ordinal'])))
    return staged
