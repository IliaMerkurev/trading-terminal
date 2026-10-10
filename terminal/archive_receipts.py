"""Status-only import ledger: identities precede files; publication is transactional.

This is process-restart recovery on retained healthy storage, not retry/resume,
archive-wide rollback, artifact verification, or power-loss durability.
"""
from datetime import datetime, timezone
import hashlib
import json
import uuid

from terminal.data import canonical, digest, write_new
from terminal.storage import SERIES, identifier


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS archive_imports(
            operation_id TEXT PRIMARY KEY, receipt_schema_version INTEGER NOT NULL CHECK(receipt_schema_version=1),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, terminal_at TEXT,
            expected_bytes INTEGER NOT NULL CHECK(expected_bytes BETWEEN 1 AND 67108864),
            archive_sha256 TEXT, validated_content_sha256 TEXT,
            phase TEXT NOT NULL CHECK(phase IN ('receiving','validating','publishing','terminal')),
            outcome TEXT CHECK(outcome IN ('completed','partial','interrupted','failed','rejected','cancelled','unknown')),
            termination_reason TEXT CHECK(termination_reason IN ('finished','validation_rejected','storage_failure','process_restart','transfer_cancelled','metadata_inconsistent')),
            expected_run_count INTEGER CHECK(expected_run_count BETWEEN 0 AND 8),
            expected_strategy_count INTEGER CHECK(expected_strategy_count=1),
            error_code TEXT CHECK(error_code IN ('storage_unavailable','invalid_archive','inconsistent_ledger')),
            CHECK((phase='terminal')=(outcome IS NOT NULL)));
        CREATE INDEX IF NOT EXISTS archive_import_order ON archive_imports(created_at DESC,operation_id DESC);
        CREATE TABLE IF NOT EXISTS archive_import_items(
            operation_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('run','strategy')),
            ordinal INTEGER NOT NULL CHECK(ordinal BETWEEN 0 AND 7), destination_id TEXT NOT NULL,
            source_run_id TEXT, expected_snapshot_sha256 TEXT, expected_result_sha256 TEXT,
            expected_strategy_sha256 TEXT, expected_series_counts TEXT,
            publication_state TEXT NOT NULL CHECK(publication_state IN ('reserved','writing','published','incomplete','unknown')),
            reserved_at TEXT NOT NULL, publication_started_at TEXT, published_at TEXT,
            PRIMARY KEY(operation_id,kind,ordinal), UNIQUE(kind,destination_id),
            CHECK((kind='run' AND source_run_id IS NOT NULL AND expected_snapshot_sha256 IS NOT NULL
                AND expected_result_sha256 IS NOT NULL AND expected_series_counts IS NOT NULL AND expected_strategy_sha256 IS NULL)
                OR (kind='strategy' AND ordinal=0 AND source_run_id IS NULL AND expected_snapshot_sha256 IS NULL
                AND expected_result_sha256 IS NULL AND expected_series_counts IS NULL AND expected_strategy_sha256 IS NOT NULL)));
    ''')


class ArchiveReceipts:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _changed(cursor):
        if cursor.rowcount != 1:
            raise ValueError('Import state changed; inspect the existing operation')

    def begin(self, operation_id, size):
        identifier(operation_id)
        stamp = now()
        with self.store.connect() as db:
            db.execute('INSERT INTO archive_imports(operation_id,receipt_schema_version,created_at,updated_at,expected_bytes,phase) VALUES(?,1,?,?,?,\'receiving\')',
                       (operation_id,stamp,stamp,size))

    def claim(self, operation_id):
        with self.store.connect() as db:
            self._changed(db.execute("UPDATE archive_imports SET phase='validating',updated_at=? WHERE operation_id=? AND phase='receiving'",(now(),identifier(operation_id))))

    def reserve(self, operation_id, raw, project, documents, attempt_key=None):
        """Reserve every output together, before any output directory is created."""
        operation_id = identifier(operation_id)
        run_ids = [uuid.uuid4().hex for _ in project['runs']]
        strategy_id = uuid.uuid4().hex
        if len(set([*run_ids,strategy_id])) != len(run_ids)+1:
            raise ValueError('Generated import identifiers collide')
        content_hash = digest({'version':1,'entries':[[name,digest(documents[name])] for name in sorted(documents)]})
        prepared=[]
        for source in project['runs']:
            snapshot=documents[f'runs/{source}/snapshot.json'];result=documents[f'runs/{source}/result.json']
            prepared.append((canonical(snapshot).decode(),digest(snapshot),digest(result),canonical({kind:len(result[kind]) for kind in SERIES}).decode()))
        envelope={**project['strategy'],'profile':project['profile']}
        strategy_hash=digest(envelope);raw_hash=hashlib.sha256(raw).hexdigest()
        stamp = now()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if attempt_key is not None:
                from terminal.archive_execution import guard
                guard(db,operation_id,attempt_key)
            operation = db.execute('SELECT * FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()
            if not operation or operation['phase'] != 'validating' or operation['archive_sha256'] is not None or operation['expected_bytes'] != len(raw):
                raise ValueError('Import cannot reserve output identities')
            for ident in [*run_ids,strategy_id]:
                identifier(ident)
                if self.store.directory(ident).exists() or db.execute('SELECT 1 FROM runs WHERE id=?',(ident,)).fetchone() or db.execute('SELECT 1 FROM strategies WHERE id=?',(ident,)).fetchone() or db.execute('SELECT 1 FROM archive_import_items WHERE destination_id=?',(ident,)).fetchone():
                    raise ValueError('Import destination already exists')
            for ordinal,(source,ident) in enumerate(zip(project['runs'],run_ids)):
                snapshot = documents[f'runs/{source}/snapshot.json']
                result = documents[f'runs/{source}/result.json']
                db.execute('INSERT INTO runs(id,created_at,status,manifest) VALUES(?,?,\'importing\',?)',(ident,stamp,prepared[ordinal][0]))
                db.execute('''INSERT INTO archive_import_items(operation_id,kind,ordinal,destination_id,source_run_id,
                    expected_snapshot_sha256,expected_result_sha256,expected_series_counts,publication_state,reserved_at)
                    VALUES(?,'run',?,?,?,?,?,?,'reserved',?)''',
                    (operation_id,ordinal,ident,source,*prepared[ordinal][1:],stamp))
            envelope = {**project['strategy'],'profile':project['profile']}
            db.execute('''INSERT INTO archive_import_items(operation_id,kind,ordinal,destination_id,expected_strategy_sha256,publication_state,reserved_at)
                VALUES(?,'strategy',0,?,?,'reserved',?)''',(operation_id,strategy_id,strategy_hash,stamp))
            self._changed(db.execute('''UPDATE archive_imports SET archive_sha256=?,validated_content_sha256=?,expected_run_count=?,
                expected_strategy_count=1,phase='publishing',updated_at=? WHERE operation_id=? AND phase='validating' ''',
                (raw_hash,content_hash,len(run_ids),stamp,operation_id)))

    def publish_run(self, operation_id, ordinal, snapshot, result):
        operation_id = identifier(operation_id)
        # Only a not-started, owned destination can enter its single write attempt.
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            item = self._item(db,operation_id,'run',ordinal)
            run = db.execute('SELECT * FROM runs WHERE id=?',(item['destination_id'],)).fetchone()
            if item['publication_state'] != 'reserved' or not run or run['status'] != 'importing' or digest(json.loads(run['manifest'])) != item['expected_snapshot_sha256']:
                raise ValueError('Import run is not an untouched reservation')
            if digest(snapshot) != item['expected_snapshot_sha256'] or digest(result) != item['expected_result_sha256'] or result['manifest_sha256'] != snapshot['snapshot_sha256']:
                raise ValueError('Import publication does not match its reservation')
            if {kind:len(result[kind]) for kind in SERIES} != json.loads(item['expected_series_counts']):
                raise ValueError('Import series counts changed')
            if self.store.directory(item['destination_id']).exists():
                raise ValueError('Import destination already contains artifacts')
            self._changed(db.execute("UPDATE archive_import_items SET publication_state='writing',publication_started_at=? WHERE operation_id=? AND kind='run' AND ordinal=? AND publication_state='reserved'",(now(),operation_id,ordinal)))
        ident = item['destination_id']
        write_new(self.store.directory(ident)/'snapshot.json',canonical(snapshot))
        write_new(self.store.directory(ident)/'result.json',canonical(result))
        summary = {'metrics':result['metrics'],'profile':result['profile'],'engine':result['engine'],
                   'engine_version':result['engine_version'],'metric_version':result['metric_version'],
                   'dataset':snapshot['dataset']['id'],'snapshot':result['manifest_sha256'],'origin':'imported','history_omitted':result.get('history_omitted',False)}
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self._item(db,operation_id,'run',ordinal)
            run = db.execute('SELECT * FROM runs WHERE id=?',(ident,)).fetchone()
            if current['publication_state'] != 'writing' or current['destination_id'] != ident or not run or run['status'] != 'importing' or digest(json.loads(run['manifest'])) != item['expected_snapshot_sha256'] or current['expected_result_sha256'] != digest(result):
                raise ValueError('Import reservation changed before publication')
            for kind in SERIES:
                db.executemany('INSERT INTO series VALUES(?,?,?,?)',((ident,kind,index,canonical(row).decode()) for index,row in enumerate(result[kind])))
            self._changed(db.execute("UPDATE runs SET status='completed',result_hash=?,summary=? WHERE id=? AND status='importing'",(item['expected_result_sha256'],canonical(summary).decode(),ident)))
            self._changed(db.execute("UPDATE archive_import_items SET publication_state='published',published_at=? WHERE operation_id=? AND kind='run' AND ordinal=? AND publication_state='writing'",(now(),operation_id,ordinal)))

    def _item(self, db, operation_id, kind, ordinal):
        operation = db.execute('SELECT phase FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()
        item = db.execute('SELECT * FROM archive_import_items WHERE operation_id=? AND kind=? AND ordinal=?',(operation_id,kind,ordinal)).fetchone()
        if not operation or operation['phase'] != 'publishing' or not item:
            raise ValueError('Import publication is unavailable; inspect the operation')
        return dict(item)

    def publish_strategy(self, operation_id, strategy, profile):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            item = self._item(db,identifier(operation_id),'strategy',0)
            operation = db.execute('SELECT expected_run_count FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()
            rows = db.execute("SELECT publication_state FROM archive_import_items WHERE operation_id=? AND kind='run'",(operation_id,)).fetchall()
            if len(rows) != operation[0] or any(row[0] != 'published' for row in rows) or item['publication_state'] != 'reserved' or digest({**strategy,'profile':profile}) != item['expected_strategy_sha256']:
                raise ValueError('Import is not ready for strategy publication')
            stamp = now()
            db.execute('INSERT INTO strategies(id,name,kind,document,updated_at,profile) VALUES(?,?,?,?,?,?)',
                       (item['destination_id'],strategy['name'],strategy['kind'],canonical(strategy['document']).decode(),stamp,canonical(profile).decode()))
            self._changed(db.execute("UPDATE archive_import_items SET publication_state='published',published_at=? WHERE operation_id=? AND kind='strategy' AND ordinal=0 AND publication_state='reserved'",(stamp,operation_id)))
            self._changed(db.execute("UPDATE archive_imports SET phase='terminal',outcome='completed',termination_reason='finished',terminal_at=?,updated_at=? WHERE operation_id=? AND phase='publishing'",(stamp,stamp,operation_id)))

    def stop(self, operation_id, reason, *, rejected=False):
        """One bounded metadata write. Never overwrite committed completion."""
        if reason not in ('storage_failure','process_restart','validation_rejected'):
            raise ValueError('Invalid import termination reason')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM archive_imports WHERE operation_id=?',(identifier(operation_id),)).fetchone()
            if not row or row['phase'] == 'terminal':
                return
            items = db.execute('SELECT * FROM archive_import_items WHERE operation_id=?',(operation_id,)).fetchall()
            published = sum(item['publication_state']=='published' for item in items)
            inconsistent = self._inconsistent(db,row,items)
            outcome = 'unknown' if inconsistent else 'partial' if published else 'rejected' if rejected else 'interrupted' if reason=='process_restart' else 'failed'
            stamp = now()
            db.execute("UPDATE archive_import_items SET publication_state='incomplete' WHERE operation_id=? AND publication_state='writing'",(operation_id,))
            self._changed(db.execute("UPDATE archive_imports SET phase='terminal',outcome=?,termination_reason=?,error_code=?,terminal_at=?,updated_at=? WHERE operation_id=? AND phase!='terminal'",(outcome,'metadata_inconsistent' if inconsistent else reason,'inconsistent_ledger' if inconsistent else 'invalid_archive' if rejected else 'storage_unavailable' if reason=='storage_failure' else None,stamp,stamp,operation_id)))

    def cancel(self, operation_id):
        operation_id = identifier(operation_id)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT phase,outcome FROM archive_imports WHERE operation_id=?',(operation_id,)).fetchone()
            if not row:
                raise ValueError('Import receipt does not exist')
            if row['phase'] != 'receiving':
                return {'status':'cancelled' if row['outcome']=='cancelled' else 'too_late','operation_id':operation_id}
            stamp = now()
            self._changed(db.execute("UPDATE archive_imports SET phase='terminal',outcome='cancelled',termination_reason='transfer_cancelled',terminal_at=?,updated_at=? WHERE operation_id=? AND phase='receiving'",(stamp,stamp,operation_id)))
        return {'status':'cancelled','operation_id':operation_id}

    def reconcile(self):
        # Called by JobManager only after exclusive workspace ownership/recovery.
        with self.store.connect() as db:
            ids = [row[0] for row in db.execute("SELECT operation_id FROM archive_imports WHERE phase!='terminal'")]
        for ident in ids:
            self.stop(ident,'process_restart')

    def _inconsistent(self, db, operation, items, metadata_only=False):
        phase=operation['phase'];outcome=operation['outcome']
        if operation['expected_run_count'] is None:
            return bool(items) or any(operation[key] is not None for key in ('archive_sha256','validated_content_sha256','expected_strategy_count')) or phase=='publishing' or outcome in ('completed','partial')
        if phase in ('receiving','validating') or operation['expected_strategy_count']!=1 or not all(isinstance(operation[key],str) and len(operation[key])==64 for key in ('archive_sha256','validated_content_sha256')):
            return True
        runs=[i for i in items if i['kind']=='run'];strategies=[i for i in items if i['kind']=='strategy']
        if len(runs)!=operation['expected_run_count'] or sorted(i['ordinal'] for i in runs)!=list(range(len(runs))) or len(strategies)!=1:
            return True
        published=sum(item['publication_state']=='published' for item in items)
        if any(item['publication_state']=='unknown' for item in items) or (strategies[0]['publication_state']=='published' and (phase!='terminal' or outcome!='completed')):
            return True
        if outcome=='completed' and published!=len(items) or outcome=='partial' and not 0<published<len(items):
            return True
        if outcome in ('failed','interrupted','rejected','cancelled') and published:
            return True
        if outcome in ('rejected','cancelled') and not (outcome=='cancelled' and db.execute('SELECT 1 FROM archive_execution WHERE operation_id=?',(operation['operation_id'],)).fetchone()):
            return True  # Neither outcome is permitted after output reservation.
        for item in runs:
            run=db.execute('SELECT status,result_hash'+('' if metadata_only else ',manifest')+' FROM runs WHERE id=?',(item['destination_id'],)).fetchone()
            if not run:
                return True
            try:
                if not metadata_only and digest(json.loads(run['manifest']))!=item['expected_snapshot_sha256']:return True
            except (ValueError,TypeError,OverflowError):
                return True
            if (item['publication_state']=='published')!=(run['status']=='completed') or (item['publication_state']=='published' and run['result_hash']!=item['expected_result_sha256']):
                return True
        return False

    def status(self, operation_id):
        with self.store.connect() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT * FROM archive_imports WHERE operation_id=?',(identifier(operation_id),)).fetchone()
            if not row:
                raise ValueError('Import receipt does not exist')
            operation = dict(row)
            items = [dict(row) for row in db.execute('SELECT * FROM archive_import_items WHERE operation_id=? ORDER BY kind,ordinal',(operation_id,))]
            execution=db.execute('SELECT * FROM archive_execution WHERE operation_id=?',(operation_id,)).fetchone()
            operation['execution']=dict(execution) if execution else None
            operation['revision']=execution['revision'] if execution else 0
            operation['attempts']=[dict(value) for value in db.execute('SELECT attempt_key,revision,started_at,terminal_at,outcome,reason FROM archive_attempts WHERE operation_id=? ORDER BY revision DESC LIMIT 10',(operation_id,))]
            operation['inspection_state'] = 'unknown' if self._inconsistent(db,operation,items,metadata_only=execution is not None) else 'available'
            for item in items:
                if item['expected_series_counts']:
                    item['expected_series_counts'] = json.loads(item['expected_series_counts'])
                if item['kind']=='run':
                    current = db.execute('SELECT status FROM runs WHERE id=?',(item['destination_id'],)).fetchone()
                    item['current_status'] = current[0] if current else 'missing'
                else:
                    current = db.execute(('SELECT id FROM strategies WHERE id=?' if execution is not None else 'SELECT name,kind,document,profile FROM strategies WHERE id=?'),(item['destination_id'],)).fetchone()
                    item['current_status'] = 'available' if current else 'missing'
                    item['modified_since_import'] = (digest({'name':current['name'],'kind':current['kind'],'document':json.loads(current['document']),'profile':json.loads(current['profile']) if current['profile'] else None}) != item['expected_strategy_sha256']) if current and item['publication_state']=='published' and execution is None else None
            operation['items'] = items
            operation['artifact_verification'] = 'not_checked'
            operation['content_identity'] = 'bound' if operation['archive_sha256'] else 'not_bound'
            return operation

    def list(self, before=None, limit=25):
        if type(limit) is not int or not 1<=limit<=100:
            raise ValueError('Import list limit must be 1–100')
        where = '';params = []
        if before is not None:
            if not isinstance(before,dict) or set(before)!={'created_at','operation_id'} or not isinstance(before['created_at'],str) or len(before['created_at'])>64:
                raise ValueError('Invalid import history cursor')
            identifier(before['operation_id']);datetime.fromisoformat(before['created_at'])
            where = 'WHERE (created_at,operation_id)<(?,?)';params = [before['created_at'],before['operation_id']]
        with self.store.connect() as db:
            rows = [dict(row) for row in db.execute(f'''SELECT operation_id,created_at,updated_at,phase,outcome,termination_reason,expected_bytes,
                archive_sha256,validated_content_sha256,expected_run_count FROM archive_imports {where} ORDER BY created_at DESC,operation_id DESC LIMIT ?''',(*params,limit+1))]
        selected = rows[:limit]
        return {'rows':selected,'next':{key:selected[-1][key] for key in ('created_at','operation_id')} if len(rows)>limit else None}
