"""Local history observations and revision-bound links; never financial evidence."""
from datetime import datetime, timezone
import hashlib
import json
import math
import uuid

import pyarrow.parquet as pq

from terminal.data import canonical, digest
from terminal.research_evidence import provenance
from terminal.storage import identifier

PAGE_CANDLES = 500
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_FOOTER_BYTES = 4 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_ROW_GROUPS = 8192
SOURCE_LIMIT = 'Local history exceeds inspection limits (256 MiB file, 4 MiB footer, 2,000,000 rows, 8,192 row groups). Prepare a smaller separate snapshot; no range is changed automatically.'
LIMITATION = 'Notes do not prove which candles were viewed. Displayed local surfaces are recorded separately; untracked views and external exposure remain incomplete.'


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS observations(
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS observation_revisions(
            observation_id TEXT NOT NULL, revision INTEGER NOT NULL, saved_at TEXT NOT NULL,
            source TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
            hypothesis TEXT NOT NULL, falsification TEXT NOT NULL,
            PRIMARY KEY(observation_id,revision));
        CREATE TABLE IF NOT EXISTS observation_batches(
            batch_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TRIGGER IF NOT EXISTS observation_revision_no_update BEFORE UPDATE ON observation_revisions
            BEGIN SELECT RAISE(ABORT,'Observation revisions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS observation_revision_no_delete BEFORE DELETE ON observation_revisions
            BEGIN SELECT RAISE(ABORT,'Observation revisions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS observation_link_no_update BEFORE UPDATE ON observation_batches
            BEGIN SELECT RAISE(ABORT,'Observation links are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS observation_link_no_delete BEFORE DELETE ON observation_batches
            BEGIN SELECT RAISE(ABORT,'Observation links are immutable'); END;
    ''')


def source_identity(manifest):
    return {**{k:manifest[k] for k in ('id','source','market','symbol','range','content_sha256','files_sha256')},
            'interval_seconds':manifest.get('interval_seconds',60),
            'provenance_sha256':digest(manifest.get('provenance',[])),
            'classification':provenance(manifest)[1]}


def validate_window(manifest, start, end):
    step=manifest.get('interval_seconds',60)
    if (type(start) is not int or type(end) is not int or end<=start or start%step or end%step
            or start<manifest['range'][0] or end>manifest['range'][1]):
        raise ValueError('Choose increasing UTC boundaries aligned to source candles inside this exact history')


class Observations:
    def __init__(self, store, datasets):
        self.store=store;self.datasets=datasets

    def window(self, dataset_id, start, end):
        manifest=self.datasets.describe(dataset_id)
        validate_window(manifest,start,end)
        step=manifest.get('interval_seconds',60)
        if (end-start)//step>PAGE_CANDLES:raise ValueError('Local chart page exceeds 500 source candles')
        path=self.datasets.root/dataset_id/'trade.parquet'
        # Constant-memory integrity verification. No DatasetStore.load/read_table or
        # full-file byte buffer: chart paging must not materialize years of bars.
        with path.open('rb') as stream:
            stream.seek(0,2);size=stream.tell()
            if size>MAX_FILE_BYTES:raise ValueError(SOURCE_LIMIT)
            if size<12:raise ValueError('Invalid local Parquet file')
            stream.seek(-8,2);footer=stream.read(8)
            if footer[4:]!=b'PAR1':raise ValueError('Invalid local Parquet footer')
            if int.from_bytes(footer[:4],'little')>MAX_FOOTER_BYTES:raise ValueError(SOURCE_LIMIT)
            stream.seek(0);sha=hashlib.sha256();hashed=0
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                hashed+=len(chunk)
                if hashed>MAX_FILE_BYTES:raise ValueError(SOURCE_LIMIT)
                sha.update(chunk)
            if sha.hexdigest()!=manifest['files_sha256']['trade']:
                raise ValueError('Local trade history checksum mismatch; source cannot be displayed')
            stream.seek(0)
            parquet=pq.ParquetFile(stream,thrift_string_size_limit=1024*1024,thrift_container_size_limit=100_000)
            if parquet.metadata.num_rows>MAX_ROWS or parquet.metadata.num_row_groups>MAX_ROW_GROUPS:raise ValueError(SOURCE_LIMIT)
            expected={'time':'int64',**{k:'double' for k in ('open','high','low','close','volume')}}
            if len(parquet.schema_arrow)!=6 or {f.name:str(f.type) for f in parquet.schema_arrow}!=expected:raise ValueError('Invalid local candle schema')
            if any(parquet.metadata.row_group(i).total_byte_size>128*1024*1024 for i in range(parquet.metadata.num_row_groups)):
                raise ValueError('Local Parquet row group exceeds 128 MiB inspection limit; prepare a smaller separate snapshot')
            rows=[];previous=None;decoded=0
            for batch in parquet.iter_batches(batch_size=256,columns=['time','open','high','low','close','volume']):
                decoded+=batch.num_rows
                if decoded>MAX_ROWS:raise ValueError(SOURCE_LIMIT)
                done=False
                for row in batch.to_pylist():
                    t=row['time']
                    if type(t) is not int or (previous is not None and t<=previous) or t%step:
                        raise ValueError('Local history contains invalid candle order or boundaries')
                    previous=t
                    if t>=end:done=True;break
                    if t<start:continue
                    if not all(isinstance(row[k],(int,float)) and math.isfinite(row[k]) for k in ('open','high','low','close','volume')):
                        raise ValueError('Local history contains invalid candle values')
                    if row['low']>min(row['open'],row['close']) or row['high']<max(row['open'],row['close']) or row['low']<=0 or row['volume']<0:
                        raise ValueError('Local history contains invalid OHLC candles')
                    rows.append(row)
                if done:break
        present={r['time'] for r in rows}
        missing=[t for t in range(start,end,step) if t not in present]
        return dict(source=source_identity(manifest),start=start,end=end,candles=rows,missing=missing,
                    limitation=LIMITATION,note='Local prepared trade candles. Candle times are opening UTC timestamps; no live requests or strategy execution.')

    def save(self, observation_id, expected_revision, dataset_id, start, end, hypothesis, falsification):
        if type(expected_revision) is not int or expected_revision<0:raise ValueError('Invalid observation revision')
        if not isinstance(hypothesis,str) or not hypothesis.strip() or len(hypothesis)>2000:
            raise ValueError('Enter a hypothesis of 1–2000 characters')
        if not isinstance(falsification,str) or len(falsification)>2000:
            raise ValueError('Optional falsification condition must be at most 2000 characters')
        manifest=self.datasets.describe(dataset_id);validate_window(manifest,start,end)
        identity=source_identity(manifest)
        # A note must refer to available verified local bytes, not just a manifest.
        verified=self.window(dataset_id,start,min(end,start+manifest.get('interval_seconds',60)))
        if verified['source']!=identity:raise ValueError('Source changed while saving; reopen the exact local history')
        ident=identifier(observation_id) if observation_id is not None else uuid.uuid4().hex
        now=datetime.now(timezone.utc).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision FROM observations WHERE id=?',(ident,)).fetchone()
            if observation_id is None:
                if expected_revision!=0:raise ValueError('New observations require revision zero')
                db.execute('INSERT INTO observations VALUES(?,?,1)',(ident,now))
            elif current is None or current['revision']!=expected_revision:
                raise ValueError('Observation changed; reopen its latest revision before saving')
            else:
                original=db.execute('SELECT source,start,end FROM observation_revisions WHERE observation_id=? AND revision=?',(ident,expected_revision)).fetchone()
                if json.loads(original['source'])!=identity or original['start']!=start or original['end']!=end:
                    raise ValueError('Saved observation source and range are fixed; create a new observation for a different period')
                db.execute('UPDATE observations SET revision=revision+1 WHERE id=?',(ident,))
            revision=expected_revision+1
            db.execute('INSERT INTO observation_revisions VALUES(?,?,?,?,?,?,?,?)',
                       (ident,revision,now,canonical(identity).decode(),start,end,hypothesis.strip(),falsification.strip()))
        return self.get(ident,revision)

    def get(self, observation_id, revision=None):
        identifier(observation_id)
        if revision is not None and (type(revision) is not int or revision<1):raise ValueError('Invalid observation revision')
        with self.store.connect() as db:
            current=db.execute('SELECT * FROM observations WHERE id=?',(observation_id,)).fetchone()
            if current is None:raise ValueError('Unknown observation')
            row=db.execute('SELECT * FROM observation_revisions WHERE observation_id=? AND revision=?',
                           (observation_id,current['revision'] if revision is None else revision)).fetchone()
            if row is None:raise ValueError('Unknown observation revision')
            links=[dict(r) for r in db.execute('SELECT l.batch_id,l.revision,b.status FROM observation_batches l JOIN library_batches b ON b.id=l.batch_id WHERE l.observation_id=? ORDER BY b.created_at DESC LIMIT 101',(observation_id,))]
        result={**dict(row),'id':observation_id,'latest_revision':current['revision'],'source':json.loads(row['source']),
                'links':links[:100],'more_links':len(links)>100,'limitation':LIMITATION}
        try:
            actual=source_identity(self.datasets.describe(result['source']['id']))
            if actual!=result['source']:raise ValueError('Stored source identity changed')
            if not (self.datasets.root/actual['id']/'trade.parquet').is_file():raise ValueError('Local trade history is missing')
            result['source_error']=None
        except (OSError,ValueError) as exc:result['source_error']=f'Exact saved history unavailable: {exc}'
        return result

    def history(self, before=None):
        if before is not None:
            if not isinstance(before,dict) or set(before)!={'id','created_at'}:raise ValueError('Invalid observation history cursor')
            identifier(before['id'])
            if not isinstance(before['created_at'],str) or len(before['created_at'])>64:raise ValueError('Invalid observation history timestamp')
            datetime.fromisoformat(before['created_at'])
        with self.store.connect() as db:
            rows=[dict(r) for r in db.execute('''SELECT o.id,o.created_at,o.revision,r.saved_at,r.hypothesis,r.start,r.end,r.source
                FROM observations o JOIN observation_revisions r ON r.observation_id=o.id AND r.revision=o.revision
                WHERE (? IS NULL OR (o.created_at,o.id)<(?,?)) ORDER BY o.created_at DESC,o.id DESC LIMIT 51''',
                (None if before is None else before['id'],None if before is None else before['created_at'],None if before is None else before['id']))]
        return {'rows':[{**r,'source':json.loads(r['source'])} for r in rows[:50]],'next':{k:rows[49][k] for k in ('id','created_at')} if len(rows)>50 else None}


def attach_batch(db, batch_id, reference, frozen, current_source):
    if not isinstance(reference,dict) or set(reference)!={'id','revision'}:raise ValueError('Invalid observation reference')
    identifier(reference['id'])
    if type(reference['revision']) is not int or reference['revision']<1:raise ValueError('Invalid observation revision')
    row=db.execute('SELECT * FROM observation_revisions WHERE observation_id=? AND revision=?',(reference['id'],reference['revision'])).fetchone()
    if row is None:raise ValueError('Observation revision no longer available')
    source=json.loads(row['source']);inputs=frozen['inputs']
    if source!=current_source:raise ValueError('Exact observation source identity changed; the test cannot be linked')
    if (source['id']!=inputs['dataset_id'] or row['start']!=inputs['start'] or row['end']!=inputs['end']):
        raise ValueError('Test source or dates differ from observation; create a new observation or explicitly detach it')
    db.execute('INSERT INTO observation_batches VALUES(?,?,?)',(batch_id,reference['id'],reference['revision']))
