"""Local SQLite metadata and immutable run artifacts."""
from datetime import datetime,timezone
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from terminal.data import canonical,write_new

SERIES=("fills","trades","events","equity","indicators","diagnostics","candles","engine_orders")
TIME_SQL="CASE WHEN kind IN ('candles','indicators') THEN json_extract(value,'$.time') ELSE json_extract(value,'$.time_ns')/1000000000.0 END"


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[a-f0-9]{32}",value):
        raise ValueError("Invalid local object identifier")
    return value


class RunStore:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.database=self.root/"terminal.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
                    manifest TEXT NOT NULL, error TEXT, result_hash TEXT, summary TEXT);
                CREATE TABLE IF NOT EXISTS series(
                    run_id TEXT NOT NULL, kind TEXT NOT NULL, row_index INTEGER NOT NULL,
                    value TEXT NOT NULL, PRIMARY KEY(run_id,kind,row_index));
                CREATE TABLE IF NOT EXISTS strategies(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
                    document TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS native_trust(identity TEXT PRIMARY KEY, granted_at TEXT NOT NULL);
            """)
            db.execute(f"CREATE INDEX IF NOT EXISTS series_time ON series(run_id,kind,({TIME_SQL}))")
            if 'profile' not in {row[1] for row in db.execute('PRAGMA table_info(strategies)')}:
                db.execute('ALTER TABLE strategies ADD COLUMN profile TEXT')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.database,timeout=15)
        db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def directory(self,run_id):
        return self.root/"runs"/identifier(run_id)

    def create(self,manifest):
        run_id=uuid.uuid4().hex
        write_new(self.directory(run_id)/"snapshot.json",canonical(manifest))
        with self.connect() as db:
            db.execute("INSERT INTO runs(id,created_at,status,manifest) VALUES(?,?,?,?)",
                       (run_id,datetime.now(timezone.utc).isoformat(),"created",canonical(manifest).decode()))
        return run_id

    def status(self,run_id,status,error=None):
        if status not in ("created","running","cancel_requested","cancelled","failed","interrupted","importing"):
            raise ValueError("Invalid worker status")
        with self.connect() as db:
            changed=db.execute("UPDATE runs SET status=?,error=? WHERE id=? AND status!='completed'",
                               (status,error,identifier(run_id))).rowcount
            if not changed: raise ValueError("Unknown run or immutable completed run")

    def get(self,run_id):
        with self.connect() as db:
            row=db.execute("SELECT * FROM runs WHERE id=?",(identifier(run_id),)).fetchone()
        if row is None: raise ValueError("Run does not exist")
        result=dict(row)
        result["manifest"]=json.loads(result["manifest"])
        result["summary"]=json.loads(result["summary"]) if result["summary"] else None
        return result

    def recent(self,limit=100):
        if type(limit) is not int or not 1<=limit<=100: raise ValueError("Run list limit must be 1–100")
        with self.connect() as db:
            rows=db.execute("SELECT id,created_at,status,error,summary FROM runs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
        return [{**dict(row),"summary":json.loads(row["summary"]) if row["summary"] else None} for row in rows]

    def complete(self,run_id,result,origin='local'):
        run=self.get(run_id)
        required='running' if origin=='local' else 'importing' if origin=='imported' else None
        if required is None or run["status"]!=required: raise ValueError("Only a matching active worker or validated import can complete")
        if result.get("status")!="completed" or result.get("manifest_sha256")!=run["manifest"]["snapshot_sha256"]:
            raise ValueError("Worker result does not match the immutable snapshot")
        if result.get("schema_version")!=1 or any(not isinstance(result.get(kind),list) for kind in SERIES):
            raise ValueError("Invalid normalized result schema")
        raw=canonical(result)
        write_new(self.directory(run_id)/"result.json",raw)
        summary={"metrics":result["metrics"],"profile":result["profile"],"engine":result["engine"],
                 "engine_version":result["engine_version"],"metric_version":result["metric_version"],
                 "dataset":run["manifest"]["dataset"]["id"],"snapshot":result["manifest_sha256"],"origin":origin,"history_omitted":result.get('history_omitted',False)}
        with self.connect() as db:
            state=db.execute("SELECT status FROM runs WHERE id=?",(run_id,)).fetchone()[0]
            if state!=required: raise ValueError("Run cancelled before completion")
            for kind in SERIES:
                db.executemany("INSERT INTO series VALUES(?,?,?,?)",
                    ((run_id,kind,index,canonical(row).decode()) for index,row in enumerate(result[kind])))
            db.execute("UPDATE runs SET status='completed',result_hash=?,summary=? WHERE id=?",
                       (hashlib.sha256(raw).hexdigest(),canonical(summary).decode(),run_id))

    def page(self,run_id,kind,offset=0,limit=200):
        identifier(run_id)
        if kind not in SERIES or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=1000:
            raise ValueError("Invalid bounded result-page request")
        if self.get(run_id)["status"]!="completed": raise ValueError("No completed result available")
        with self.connect() as db:
            rows=db.execute("SELECT value FROM series WHERE run_id=? AND kind=? AND row_index>=? ORDER BY row_index LIMIT ?",
                            (run_id,kind,offset,limit)).fetchall()
            count=db.execute("SELECT COUNT(*) FROM series WHERE run_id=? AND kind=?",(run_id,kind)).fetchone()[0]
        selected=[];size=0
        for row in rows:
            size+=len(row["value"].encode())
            if size>512*1024:
                if not selected: raise ValueError("Individual result row exceeds IPC budget")
                break
            selected.append(json.loads(row["value"]))
        next_offset=offset+len(selected)
        return {"rows":selected,"total":count,"offset":offset,"next":next_offset if next_offset<count else None}

    def result(self,run_id):
        run=self.get(run_id)
        if run["status"]!="completed": raise ValueError("Run is not completed")
        raw=(self.directory(run_id)/"result.json").read_bytes()
        if hashlib.sha256(raw).hexdigest()!=run["result_hash"]: raise ValueError("Saved result checksum mismatch")
        return json.loads(raw)

    def chart_window(self,run_id,start=None,minutes=240):
        run=self.get(run_id)
        if run["status"]!="completed": raise ValueError("No completed result available")
        if type(minutes) is not int or not 30<=minutes<=480 or (start is not None and (type(start) is not int or start%60)):
            raise ValueError("Chart requests require aligned start and 30–480 minutes")
        window=run['manifest'].get('research',{}).get('window')
        first,last=[window['start'],window['end']] if window else run["manifest"]["dataset"]["range"]
        start=first if start is None else max(first,min(start,max(first,last-60)))
        end=min(last,start+minutes*60)
        result={"start":start,"end":end,"range":[first,last],"series":{}}
        with self.connect() as db:
            for kind in ("candles","indicators","fills","equity"):
                # Candle timestamps are interval starts; indicators are availability times.
                lower,upper=(start,end) if kind=="candles" else (start+1e-6,end+1e-6)
                rows=db.execute(f"SELECT value FROM series WHERE run_id=? AND kind=? AND ({TIME_SQL})>=? AND ({TIME_SQL})<? ORDER BY ({TIME_SQL}),row_index LIMIT 4000",(run_id,kind,lower,upper)).fetchall()
                result["series"][kind]=[json.loads(row[0]) for row in rows]
        for fill in result['series']['fills']:
            # Derive the candle association before JavaScript rounds epoch nanoseconds.
            fill['chart_time']=(fill['time_ns']//60_000_000_000+1)*60
        if run['summary'].get('origin')=='local' and run['manifest'].get('research',{}).get('experiment'):
            from terminal.data import DatasetStore
            import pyarrow.parquet as pq
            dataset=run['manifest']['dataset']
            try:
                manifest=DatasetStore(self.root/'datasets').describe(dataset['id'])
                if manifest['content_sha256']!=dataset['content_sha256']:raise ValueError('Shared candle identity changed')
                path=self.root/'datasets'/dataset['id']/'trade.parquet'
                with path.open('rb') as stream:
                    checksum=hashlib.file_digest(stream,'sha256').hexdigest()
                if checksum!=manifest['files_sha256']['trade']:raise ValueError('Shared candle checksum mismatch')
                result['series']['candles']=pq.read_table(path,filters=[('time','>=',start),('time','<',end)]).to_pylist()
            except FileNotFoundError:
                result['history_note']='The shared dataset is unavailable; saved derived results are unchanged.'
        if len(canonical(result))>900*1024: raise ValueError("Chart window exceeds payload budget; choose a shorter window")
        return result

    def save_strategy(self,name,kind,document,strategy_id=None,profile=None):
        if not isinstance(name,str) or not name.strip() or len(name)>120 or kind not in ("graph","native"):
            raise ValueError("Invalid strategy name or format")
        if len(canonical(document))>1024*1024: raise ValueError("Strategy exceeds size budget")
        strategy_id=identifier(strategy_id) if strategy_id else uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO strategies(id,name,kind,document,updated_at,profile) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,kind=excluded.kind,document=excluded.document,updated_at=excluded.updated_at,profile=COALESCE(excluded.profile,strategies.profile)",
                       (strategy_id,name,kind,canonical(document).decode(),datetime.now(timezone.utc).isoformat(),canonical(profile).decode() if profile is not None else None))
        return strategy_id

    def strategies(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,name,kind,updated_at FROM strategies ORDER BY updated_at DESC")]

    def strategy(self,strategy_id):
        with self.connect() as db:
            row=db.execute("SELECT * FROM strategies WHERE id=?",(identifier(strategy_id),)).fetchone()
        if row is None: raise ValueError("Strategy does not exist")
        return {**dict(row),"document":json.loads(row["document"]),"profile":json.loads(row['profile']) if row['profile'] else None}

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE runs SET status='interrupted',error='Application exited before worker or import completion' WHERE status IN ('created','running','cancel_requested','importing')")

    def trust_native(self,identity):
        if not isinstance(identity,str) or not re.fullmatch(r"[a-f0-9]{64}",identity): raise ValueError("Invalid native trust identity")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO native_trust VALUES(?,?)",(identity,datetime.now(timezone.utc).isoformat()))

    def is_trusted(self,identity):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM native_trust WHERE identity=?",(identity,)).fetchone() is not None
