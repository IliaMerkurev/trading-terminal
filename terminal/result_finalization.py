"""Owned local result publication, separate from imported-report authority.

Bulk work runs in a managed process. Staged series remain invisible until the
short completion transaction. The mutation epoch protects normal concurrent
writes, not a hostile actor able to rewrite the database or its triggers.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from terminal.data import canonical, digest, write_new
from terminal.storage import SERIES, RunStore, identifier

BATCH_ROWS = 128
BATCH_BYTES = 256 * 1024
STORAGE_EXIT = 74
INVALID_EXIT = 65
EMPTY_CHAIN = hashlib.sha256(b'').hexdigest()


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS local_finalization(
            run_id TEXT PRIMARY KEY, generation TEXT NOT NULL UNIQUE,
            snapshot_hash TEXT NOT NULL, state TEXT NOT NULL, phase TEXT NOT NULL,
            staged_rows INTEGER NOT NULL DEFAULT 0, staged_bytes INTEGER NOT NULL DEFAULT 0,
            total_rows INTEGER, mutation_epoch INTEGER NOT NULL DEFAULT 0,
            receipt_chain TEXT NOT NULL, result_hash TEXT, error_code TEXT,
            oversized_rows INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS local_finalization_batches(
            run_id TEXT NOT NULL, generation TEXT NOT NULL, ordinal INTEGER NOT NULL,
            kind TEXT NOT NULL, start_index INTEGER NOT NULL, row_count INTEGER NOT NULL,
            encoded_bytes INTEGER NOT NULL, content_hash TEXT NOT NULL, chain TEXT NOT NULL,
            PRIMARY KEY(run_id,ordinal));
        CREATE TRIGGER IF NOT EXISTS local_series_insert AFTER INSERT ON series BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=NEW.run_id;
        END;
        CREATE TRIGGER IF NOT EXISTS local_series_delete AFTER DELETE ON series BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=OLD.run_id;
        END;
        CREATE TRIGGER IF NOT EXISTS local_series_update AFTER UPDATE ON series BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=OLD.run_id OR run_id=NEW.run_id;
        END;
        CREATE TRIGGER IF NOT EXISTS local_batch_insert AFTER INSERT ON local_finalization_batches BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=NEW.run_id;
        END;
        CREATE TRIGGER IF NOT EXISTS local_batch_delete AFTER DELETE ON local_finalization_batches BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=OLD.run_id;
        END;
        CREATE TRIGGER IF NOT EXISTS local_batch_update AFTER UPDATE ON local_finalization_batches BEGIN
            UPDATE local_finalization SET mutation_epoch=mutation_epoch+1 WHERE run_id=OLD.run_id OR run_id=NEW.run_id;
        END;
    ''')


class Stopped(Exception):
    pass


def register(db, run_id, generation, snapshot_hash):
    """Called only in the real local admission transaction, never by imports."""
    identifier(generation)
    db.execute("INSERT INTO local_finalization(run_id,generation,snapshot_hash,state,phase,receipt_chain) VALUES(?,?,?,'computing','computing',?)",
               (run_id, generation, snapshot_hash, EMPTY_CHAIN))


def guard(db, run_id, generation, states=('finalizing',)):
    control=db.execute('SELECT * FROM local_finalization WHERE run_id=?',(run_id,)).fetchone()
    run=db.execute('SELECT status,manifest FROM runs WHERE id=?',(run_id,)).fetchone()
    if not control or control['generation']!=generation:
        raise ValueError('Local finalization ownership does not match')
    if control['state']=='cancel_requested' or run and run['status']=='cancel_requested':
        raise Stopped('Local finalization was cancelled')
    if not run or control['state'] not in states or run['status']!=('running' if control['state']=='computing' else 'finalizing'):
        raise ValueError('Local finalization is not active')
    if db.execute("SELECT 1 FROM archive_import_items WHERE kind='run' AND destination_id=?",(run_id,)).fetchone():
        raise ValueError('An imported destination cannot become a local calculation')
    return control,run


def claim(store, run_id, generation):
    directory=store.directory(run_id)
    if (directory/'result.json').exists() or (directory/'result.json').is_symlink():
        raise ValueError('Unexpected result artifact before local finalization')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        control,run=guard(db,run_id,generation,('computing',))
        if run['status']!='running' or control['mutation_epoch'] or db.execute('SELECT 1 FROM series WHERE run_id=? LIMIT 1',(run_id,)).fetchone():
            raise ValueError('Unexpected staged content before local finalization')
        db.execute("UPDATE local_finalization SET state='finalizing',phase='decoding' WHERE run_id=?",(run_id,))
        db.execute("UPDATE runs SET status='finalizing' WHERE id=?",(run_id,))


def cancel(store, run_id, generation, *, timeout=15):
    """The durable completion/cancellation cutoff; no process waits here."""
    with store.connect(timeout=timeout) as db:
        db.execute('BEGIN IMMEDIATE')
        run=db.execute('SELECT status FROM runs WHERE id=?',(run_id,)).fetchone()
        control=db.execute('SELECT generation,state FROM local_finalization WHERE run_id=?',(run_id,)).fetchone()
        if not run or not control or control['generation']!=generation:
            raise ValueError('Local cancellation ownership does not match')
        if run['status']=='completed':return 'too_late'
        if control['state']=='terminal':return run['status']
        db.execute("UPDATE local_finalization SET state='cancel_requested' WHERE run_id=?",(run_id,))
        db.execute("UPDATE runs SET status='cancel_requested' WHERE id=? AND status!='completed'",(run_id,))
    return 'cancel_requested'


def settle(store, run_id, generation, *, code=0, error=None):
    """Only after reaping; committed completion is immutable even on errors."""
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM local_finalization WHERE run_id=?',(run_id,)).fetchone()
        run=db.execute('SELECT status FROM runs WHERE id=?',(run_id,)).fetchone()
        if not row or row['generation']!=generation or not run:
            raise ValueError('Local settlement ownership does not match')
        if run['status']=='completed':
            db.execute("UPDATE local_finalization SET state='terminal',phase='completed' WHERE run_id=?",(run_id,))
            return 'completed'
        if row['state']=='terminal':return run['status']
        status='cancelled' if row['state']=='cancel_requested' else 'failed'
        message=None if status=='cancelled' else error or ('Result persistence failed; restart required' if code==STORAGE_EXIT else 'Result finalization did not complete')
        db.execute("UPDATE runs SET status=?,error=? WHERE id=? AND status!='completed'",(status,message,run_id))
        db.execute("UPDATE local_finalization SET state='terminal',phase=?,error_code=COALESCE(error_code,?) WHERE run_id=?",(status,'storage_failure' if code==STORAGE_EXIT else None,run_id))
        return status


def recover(db):
    db.execute("UPDATE local_finalization SET state='terminal',phase=CASE WHEN (SELECT status FROM runs WHERE id=run_id)='completed' THEN 'completed' ELSE 'interrupted' END WHERE state!='terminal'")


def status(store, run_id):
    with store.connect() as db:
        row=db.execute('SELECT generation,state,phase,staged_rows,staged_bytes,total_rows,oversized_rows,error_code FROM local_finalization WHERE run_id=?',(run_id,)).fetchone()
    return dict(row) if row and row['phase']!='computing' else None


def _read(path):
    if path.is_symlink() or not path.is_file():raise ValueError('Local result input is not a regular file')
    return path.read_bytes()


def finalize(store, run_id, generation, checkpoint=lambda phase:None):
    """Process-owned heavy work. Checkpoints are callable test seams, not IPC."""
    directory=store.directory(run_id)
    maximum=0.0
    @contextmanager
    def transaction():
        nonlocal maximum
        start=time.monotonic()
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');guard(db,run_id,generation)
            yield db
        elapsed=time.monotonic()-start
        if elapsed>maximum:
            maximum=elapsed
            with (directory/'finalization-timings.jsonl').open('ab') as stream:
                stream.write(canonical({'max_write_seconds':maximum})+b'\n')
    def progress(phase):
        with transaction() as db:db.execute('UPDATE local_finalization SET phase=? WHERE run_id=?',(phase,run_id))
        checkpoint(phase)
    progress('decoding')
    with store.connect() as db:
        control,run=guard(db,run_id,generation)
        manifest=json.loads(run['manifest'])
    manifest_text=canonical(manifest).decode()
    snapshot=_read(directory/'snapshot.json')
    if snapshot!=canonical(manifest) or manifest['snapshot_sha256']!=control['snapshot_hash'] or digest({k:v for k,v in manifest.items() if k!='snapshot_sha256'})!=control['snapshot_hash']:
        raise ValueError('Local snapshot identity changed')
    result=json.loads(_read(directory/'worker-result.json'))
    if not isinstance(result,dict) or result.get('status')!='completed' or result.get('manifest_sha256')!=control['snapshot_hash']:
        raise ValueError('Worker result does not match the immutable snapshot')
    if result.get('schema_version')!=1 or any(not isinstance(result.get(kind),list) for kind in SERIES):
        raise ValueError('Invalid normalized result schema')
    from terminal.evaluation_evidence import validate_result,summary_fields
    validate_result(result,manifest)
    progress('encoding')
    raw=canonical(result);result_hash=hashlib.sha256(raw).hexdigest()
    summary=canonical({'metrics':result['metrics'],'profile':result['profile'],'engine':result['engine'],
        'engine_version':result['engine_version'],'metric_version':result['metric_version'],
        'dataset':manifest['dataset']['id'],'snapshot':result['manifest_sha256'],'origin':'local',
        'history_omitted':result.get('history_omitted',False),**summary_fields(result)}).decode()
    total=sum(len(result[kind]) for kind in SERIES)
    with transaction() as db:db.execute('UPDATE local_finalization SET total_rows=?,result_hash=? WHERE run_id=?',(total,result_hash,run_id))
    progress('artifact')
    write_new(directory/'result.json',raw)
    checkpoint('artifact_written')
    progress('staging')
    rows=0;encoded_bytes=0;chain=EMPTY_CHAIN;receipts=[];oversized=0
    for kind in SERIES:
        batch=[];size=0
        def commit():
            nonlocal rows,encoded_bytes,chain,oversized
            if not batch:return
            content=hashlib.sha256()
            for index,value in batch:
                content.update(canonical([kind,index,value]));content.update(b'\n')
            receipt=[run_id,generation,len(receipts),kind,batch[0][0],len(batch),size,content.hexdigest()]
            new_chain=hashlib.sha256(canonical([chain,receipt])).hexdigest()
            oversized+=sum(len(value.encode())>BATCH_BYTES for _,value in batch)
            with transaction() as db:
                current,_=guard(db,run_id,generation)
                if current['receipt_chain']!=chain or current['staged_rows']!=rows or current['staged_bytes']!=encoded_bytes:
                    raise ValueError('Local staging receipt changed')
                db.executemany('INSERT INTO series VALUES(?,?,?,?)',((run_id,kind,index,value) for index,value in batch))
                db.execute('INSERT INTO local_finalization_batches VALUES(?,?,?,?,?,?,?,?,?)',(*receipt,new_chain))
                db.execute('UPDATE local_finalization SET staged_rows=?,staged_bytes=?,receipt_chain=?,oversized_rows=? WHERE run_id=?',(rows+len(batch),encoded_bytes+size,new_chain,oversized,run_id))
            rows+=len(batch);encoded_bytes+=size;chain=new_chain;receipts.append((*receipt,new_chain))
            checkpoint('batch:'+str(len(receipts)))
        for index,row in enumerate(result[kind]):
            value=canonical(row).decode();length=len(value.encode())
            if batch and (len(batch)>=BATCH_ROWS or size+length>BATCH_BYTES):commit();batch=[];size=0
            batch.append((index,value));size+=length
            # Preserve previously valid oversized rows as isolated, measured writes.
            if size>BATCH_BYTES:commit();batch=[];size=0
        commit()
    progress('verifying')
    with store.connect() as db:
        db.execute('BEGIN')
        verified,_=guard(db,run_id,generation)
        if verified['receipt_chain']!=chain or verified['staged_rows']!=rows or verified['staged_bytes']!=encoded_bytes or rows!=total:
            raise ValueError('Local staging totals changed')
        cursor=iter(db.execute('SELECT kind,row_index,value FROM series WHERE run_id=? ORDER BY kind,row_index',(run_id,)))
        for kind in sorted(SERIES):
            for index,value in enumerate(result[kind]):
                actual=next(cursor,None)
                if actual is None or tuple(actual)!=(kind,index,canonical(value).decode()):
                    raise ValueError('Staged normalized content or order changed')
        if next(cursor,None) is not None:raise ValueError('Unexpected staged normalized content')
        actual_receipts=iter(db.execute('SELECT * FROM local_finalization_batches WHERE run_id=? ORDER BY ordinal',(run_id,)))
        for expected in receipts:
            actual=next(actual_receipts,None)
            if actual is None or tuple(actual)!=expected:raise ValueError('Local staging receipt changed')
        if next(actual_receipts,None) is not None:raise ValueError('Unexpected local staging receipt')
        epoch=verified['mutation_epoch']
    if _read(directory/'result.json')!=raw:raise ValueError('Local result artifact changed')
    checkpoint('verified')
    # No scans/encoding here: the read snapshot and mutation epoch bind the exact
    # independently verified content to this publication cutoff.
    with transaction() as db:
        current,run=guard(db,run_id,generation)
        if current['mutation_epoch']!=epoch or current['receipt_chain']!=chain or current['staged_rows']!=total or current['result_hash']!=result_hash or current['staged_bytes']!=encoded_bytes or current['snapshot_hash']!=manifest['snapshot_sha256'] or run['manifest']!=manifest_text:
            raise ValueError('Local publication changed after verification')
        db.execute("UPDATE runs SET status='completed',error=NULL,result_hash=?,summary=? WHERE id=? AND status='finalizing'",(result_hash,summary,run_id))
        db.execute("UPDATE local_finalization SET phase='completed' WHERE run_id=?",(run_id,))
    checkpoint('committed')


def execute(request):
    root=Path(request['root']).resolve();run_id=identifier(request['run_id']);generation=identifier(request['generation'])
    store=object.__new__(RunStore);store.root=root;store.database=root/'terminal.sqlite3'
    try:
        finalize(store,run_id,generation)
        return 0
    except Stopped:
        return 0
    except Exception as exc:
        storage=isinstance(exc,(OSError,sqlite3.Error))
        try:
            with store.connect() as db:
                db.execute('UPDATE local_finalization SET error_code=? WHERE run_id=? AND generation=?',('storage_failure' if storage else 'invalid_result',run_id,generation))
        except Exception:
            storage=True
        return STORAGE_EXIT if storage else INVALID_EXIT
