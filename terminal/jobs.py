"""One active worker, immutable requests, bounded logs and explicit cancellation."""
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
import threading
import uuid

from terminal.data import DatasetStore,canonical,run_manifest
from terminal.graph import validate_graph
from terminal.profile import Profile
from terminal.storage import RunStore
from terminal.windows_job import WindowsJob


class JobManager:
    def __init__(self,root):
        workspace=Path(root).resolve()
        workspace.mkdir(parents=True,exist_ok=True)
        self.instance_file=(workspace/"instance.lock").open("a+b")
        self.instance_file.seek(0,2)
        if self.instance_file.tell()==0:
            self.instance_file.write(b"0");self.instance_file.flush()
        self.instance_file.seek(0)
        try: msvcrt.locking(self.instance_file.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.instance_file.close()
            raise ValueError("Another application instance already owns this local workspace")
        try: self.store=RunStore(workspace)
        except Exception:
            self.instance_file.close()
            raise
        self.datasets=DatasetStore(self.store.root/"datasets")
        self.lock=threading.RLock()
        self.active=None
        self.reservation=None
        self.store.recover()
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS replay_jobs(
                id TEXT PRIMARY KEY,session_id TEXT NOT NULL,status TEXT NOT NULL,error TEXT,result TEXT)''')
            db.execute("UPDATE replay_jobs SET status='interrupted',error='Application exited before replay completion' WHERE status IN ('running','cancel_requested')")

    def start_replay(self,session_id):
        from terminal.live_store import LiveStore
        from terminal.data import runtime_snapshot
        journal=object.__new__(LiveStore);journal.store=self.store
        journal.get(session_id)  # Validate before creating a job; never restore/mutate the session.
        with self.lock:
            if self.active or self.reservation:raise ValueError('One calculation or experiment is already active')
            replay_id=uuid.uuid4().hex
            directory=self.store.root/'replays'/replay_id;directory.mkdir(parents=True)
            with self.store.connect() as db:
                db.execute('INSERT INTO replay_jobs VALUES(?,?,?,NULL,NULL)',(replay_id,session_id,'running'))
            job=None;process=None
            try:
                job=WindowsJob()
                process=subprocess.Popen([sys.executable,'-m','terminal.worker'],cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                job.assign(process)
                self.active={'id':replay_id,'kind':'replay','process':process,'job':job,'cancelled':False}
                reader=threading.Thread(target=self._drain,args=(replay_id,process.stdout,directory),daemon=True);reader.start()
                process.stdin.write(canonical({'version':1,'command':'replay','root':str(self.store.root),
                    'replay_id':replay_id,'session_id':session_id,'runtime':runtime_snapshot()})+b'\n');process.stdin.close()
                monitor=threading.Thread(target=self._monitor_replay,args=(replay_id,session_id,process,job,reader),daemon=True)
                self.active['monitor']=monitor;monitor.start()
            except Exception:
                if job:job.close()
                if process:
                    if process.poll() is None:process.terminate()
                    process.wait(timeout=5)
                self.active=None
                with self.store.connect() as db:db.execute("UPDATE replay_jobs SET status='failed',error='Replay worker could not start' WHERE id=?",(replay_id,))
                raise
        return {'replay_id':replay_id}

    def replay_status(self,replay_id=None):
        from terminal.storage import identifier
        with self.store.connect() as db:
            row=(db.execute('SELECT * FROM replay_jobs WHERE id=?',(identifier(replay_id),)).fetchone() if replay_id is not None
                 else db.execute('SELECT * FROM replay_jobs ORDER BY rowid DESC LIMIT 1').fetchone())
        if row is None:
            if replay_id is not None:raise ValueError('Unknown replay job')
            return None
        return {**dict(row),'result':json.loads(row['result']) if row['result'] else None,
                'progress':self._progress(self.store.root/'replays'/row['id'])}

    def cancel_replay(self,replay_id):
        with self.lock:
            active=self.active
            if not active or active.get('kind')!='replay' or active['id']!=replay_id:
                raise ValueError('That replay is not active')
            active['cancelled']=True
            with self.store.connect() as db:db.execute("UPDATE replay_jobs SET status='cancel_requested' WHERE id=?",(replay_id,))
            active['job'].terminate()
        return {'status':'cancel_requested'}

    def _monitor_replay(self,replay_id,session_id,process,job,reader):
        code=process.wait();job.close();reader.join(timeout=5)
        directory=self.store.root/'replays'/replay_id
        with self.lock:
            status='failed';error=None;result=None
            try:
                if self.active['cancelled']:status='cancelled'
                elif code==0:
                    saved=json.loads((directory/'worker-result.json').read_bytes())
                    result=saved['result']
                    if saved['session_id']!=session_id or type(result.get('match')) is not bool or type(result.get('checked_events')) is not int:
                        raise ValueError('Invalid replay worker result')
                    status='completed'
                else:
                    failure=directory/'worker-error.json'
                    error=json.loads(failure.read_bytes())['message'] if failure.exists() else f'Replay worker exited with code {code}'
            except Exception as exc:status='failed';error=str(exc)[:2000];result=None
            try:
                with self.store.connect() as db:
                    db.execute('UPDATE replay_jobs SET status=?,error=?,result=? WHERE id=?',
                               (status,error,canonical(result).decode() if status=='completed' else None,replay_id))
            finally:self.active=None

    def start(self,strategy,profile,dataset_id,*,research=None,owner=None,expected_runtime=None):
        native=isinstance(strategy,dict) and strategy.get("engine")=="nautilus_trader"
        if native:
            from terminal.native import preview
            report=preview(strategy)
            if not self.store.is_trusted(report["trust_sha256"]): raise ValueError("Explicit trust is required before loading this Python source")
            if report["dependency_problems"]: raise ValueError("Native dependencies are missing or incompatible; no automatic installation")
        else:
            validate_graph(strategy)
        if not isinstance(profile,Profile): profile=Profile(**profile)
        manifest=self.datasets.describe(dataset_id)
        self.datasets.check_profile(manifest,profile)
        snapshot=run_manifest(strategy,profile,manifest)
        if expected_runtime is not None and snapshot['runtime']!=expected_runtime:raise ValueError('Runtime changed since experiment preparation')
        if research is not None:
            from terminal.data import digest
            snapshot.pop('snapshot_sha256')
            snapshot['research']=research
            snapshot=json.loads(canonical(snapshot))
            snapshot['snapshot_sha256']=digest(snapshot)
        with self.lock:
            if self.reservation is not None and self.reservation!=owner:raise ValueError('A parameter experiment owns the calculation slot')
            if self.active is not None: raise ValueError("One backtest is already active")
            run_id=self.store.create(snapshot)
            job=WindowsJob()
            process=None
            try:
                process=subprocess.Popen([sys.executable,"-m","terminal.worker"],cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                job.assign(process)
                self.active={"id":run_id,"process":process,"job":job,"cancelled":False}
                self.store.status(run_id,"running")
                reader=threading.Thread(target=self._drain,args=(run_id,process.stdout),daemon=True)
                reader.start()
                payload={"version":1,"command":"run","root":str(self.store.root),"run_id":run_id}
                process.stdin.write(canonical(payload)+b"\n")
                process.stdin.close()
                monitor=threading.Thread(target=self._monitor,args=(run_id,process,job,reader),daemon=True)
                self.active["monitor"]=monitor
                monitor.start()
                return run_id
            except Exception:
                job.close()
                if process:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=5)
                self.active=None
                self.store.status(run_id,"failed","Worker could not be attached or started")
                raise

    def _drain(self,run_id,stream,directory=None):
        # Native stdout/stderr is never interpreted as protocol messages.
        remaining=256*1024
        with ((directory or self.store.directory(run_id))/"worker.log").open("wb") as log:
            while data:=stream.read(4096):
                if remaining>0:
                    log.write(data[:remaining]);remaining-=len(data[:remaining])
                    log.flush()
        stream.close()

    def _monitor(self,run_id,process,job,reader):
        code=process.wait()
        job.close()  # Also stop any child that outlived the worker.
        reader.join(timeout=5)
        with self.lock:
            active=self.active
            if active is None or active["id"]!=run_id: return
            try:
                if active["cancelled"]:
                    self.store.status(run_id,"cancelled")
                elif code==0:
                    file=self.store.directory(run_id)/"worker-result.json"
                    self.store.complete(run_id,json.loads(file.read_bytes()))
                else:
                    error_file=self.store.directory(run_id)/"worker-error.json"
                    message=json.loads(error_file.read_bytes())["message"] if error_file.exists() else f"Worker exited with code {code}"
                    self.store.status(run_id,"failed",message)
            except Exception as exc:
                self.store.status(run_id,"failed",str(exc)[:2000])
            finally:
                self.active=None

    def cancel(self,run_id):
        with self.lock:
            if self.active is None or self.active.get('kind')=='replay' or self.active["id"]!=run_id: raise ValueError("That run is not active")
            self.active["cancelled"]=True
            self.store.status(run_id,"cancel_requested")
            self.active["job"].terminate()
        return {"status":"cancel_requested"}

    def status(self,run_id):
        record=self.store.get(run_id)
        return {"id":run_id,"status":record["status"],"error":record["error"],"progress":self._progress(self.store.directory(run_id)),"summary":record["summary"]}

    @staticmethod
    def _progress(directory):
        progress=None
        file=directory/"progress.jsonl"
        if file.exists():
            try:
                with file.open("rb") as stream:
                    stream.seek(max(0,file.stat().st_size-4096))
                    raw=stream.read(4096)
                lines=raw.split(b"\n")
                if len(lines)>=2: progress=json.loads(lines[-2])
            except (OSError,ValueError): pass
        return progress

    def logs(self,run_id):
        self.store.get(run_id)
        file=self.store.directory(run_id)/"worker.log"
        if not file.exists(): return {"text":"Worker preparation; no output yet.","truncated":False}
        with file.open("rb") as stream:
            size=file.stat().st_size
            stream.seek(max(0,size-16384))
            return {"text":stream.read(16384).decode("utf-8",errors="replace"),"truncated":size>16384}

    def close(self):
        with self.lock:
            active=self.active
            if active:
                if active.get('kind')=='replay':self.cancel_replay(active['id'])
                else:self.cancel(active["id"])
                monitor=active["monitor"]
        if active:
            monitor.join(timeout=10)
            if monitor.is_alive():
                raise RuntimeError("Worker shutdown has not completed; workspace ownership is retained")
        if not self.instance_file.closed:
            self.instance_file.seek(0)
            msvcrt.locking(self.instance_file.fileno(),msvcrt.LK_UNLCK,1)
            self.instance_file.close()
