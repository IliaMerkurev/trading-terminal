"""One active worker, immutable requests, bounded logs and explicit cancellation."""
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import threading
import uuid

from terminal.data import DatasetStore,canonical,run_manifest
from terminal.graph import validate_graph
from terminal.profile import Profile
from terminal.storage import RunStore
from terminal.process_lifecycle import lock_workspace,unlock_workspace,worker_job,worker_options,require_native_execution


class FinalizerBootstrapError(Exception):
    pass


class JobManager:
    def __init__(self,root):
        workspace=Path(root).resolve()
        workspace.mkdir(parents=True,exist_ok=True)
        self.instance_file=(workspace/"instance.lock").open("a+b")
        self.instance_file.seek(0,2)
        if self.instance_file.tell()==0:
            self.instance_file.write(b"0");self.instance_file.flush()
        self.instance_file.seek(0)
        try: lock_workspace(self.instance_file)
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
        self.storage_failure=None
        self.store.recover()
        from terminal.archive_receipts import ArchiveReceipts
        ArchiveReceipts(self.store).reconcile()
        from terminal.archive_execution import reconcile
        reconcile(self.store)
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS replay_jobs(
                id TEXT PRIMARY KEY,session_id TEXT NOT NULL,status TEXT NOT NULL,error TEXT,result TEXT)''')
            db.execute("UPDATE replay_jobs SET status='interrupted',error='Application exited before replay completion' WHERE status IN ('running','cancel_requested')")

    def require_storage_ready(self):
        with self.lock:
            if self.storage_failure is not None:
                raise ValueError(self.storage_failure['message'])

    def latch_storage_failure(self,ident,kind):
        # Never copy exception text (paths, payloads or secrets) into this overlay.
        # The first failure owns the diagnostic until restart; no automatic retry.
        with self.lock:
            if self.storage_failure is None:
                self.storage_failure={'id':ident,'kind':kind,'durable':False,
                    'message':('New calculations and archive imports blocked by storage finalization failure. Inspect the archive operation and saved work, check available storage, and restart the application. Other active work may still be running. No automatic retry.' if kind=='archive_import' else 'Calculations blocked by storage finalization failure. Saved status may be unfinished; owned work may still need cleanup. Check available storage and restart the application. No automatic retry.')}

    def storage_diagnostic(self):
        with self.lock:
            return dict(self.storage_failure) if self.storage_failure is not None else None

    def scheduler_status(self):
        with self.lock:
            return {'storage_failure':self.storage_diagnostic(),
                    'active':{'id':self.active['id'],'kind':self.active.get('kind','run')} if self.active else None,
                    'reservation':self.reservation}

    def start_replay(self,session_id):
        self.require_storage_ready()
        from terminal.live_store import LiveStore
        from terminal.data import runtime_snapshot
        journal=object.__new__(LiveStore);journal.store=self.store
        journal.get(session_id)  # Validate before creating a job; never restore/mutate the session.
        with self.lock:
            self.require_storage_ready()
            if self.active or self.reservation:raise ValueError('One calculation or experiment is already active')
            replay_id=uuid.uuid4().hex
            directory=self.store.root/'replays'/replay_id;directory.mkdir(parents=True)
            with self.store.connect() as db:
                db.execute('INSERT INTO replay_jobs VALUES(?,?,?,NULL,NULL)',(replay_id,session_id,'running'))
            job=None;process=None;anchor=None
            try:
                # Keep the WAL/shared-memory lifetime owned by the service while a
                # cancellable process holds a read transaction. On Windows killing
                # the last connection can otherwise race WAL cleanup/reopening.
                anchor=sqlite3.connect(self.store.database,timeout=15,check_same_thread=False)
                anchor.execute('SELECT count(*) FROM sqlite_master').fetchone()
                job=worker_job(self.instance_file)
                process=subprocess.Popen([sys.executable,'-m','terminal.worker'],cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**worker_options(job))
                job.assign(process)
                self.active={'id':replay_id,'kind':'replay','process':process,'job':job,'cancelled':False}
                reader=threading.Thread(target=self._drain,args=(replay_id,process.stdout,directory),daemon=True);reader.start()
                process.stdin.write(canonical({'version':1,'command':'replay','root':str(self.store.root),
                    'replay_id':replay_id,'session_id':session_id,'runtime':runtime_snapshot()})+b'\n');process.stdin.close()
                monitor=threading.Thread(target=self._monitor_replay,args=(replay_id,session_id,process,job,reader,anchor),daemon=True)
                self.active['monitor']=monitor;monitor.start()
            except Exception:
                if job:job.close()
                if process:
                    if sys.platform!='linux' and process.poll() is None:process.terminate()
                    process.wait(timeout=5)
                    if process.stdin and not process.stdin.closed:process.stdin.close()
                if anchor:anchor.close()
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
                'progress':self._progress(self.store.root/'replays'/row['id']),'storage_failure':self.storage_diagnostic(),
                'worker_active':self.scheduler_status()['active']=={'id':row['id'],'kind':'replay'}}

    def cancel_replay(self,replay_id):
        with self.lock:
            active=self.active
            if not active or active.get('kind')!='replay' or active['id']!=replay_id:
                raise ValueError('That replay is not active')
            active['cancelled']=True
            try:
                with self.store.connect() as db:db.execute("UPDATE replay_jobs SET status='cancel_requested' WHERE id=?",(replay_id,))
            finally:active['job'].terminate()
        return {'status':'cancel_requested'}

    def _monitor_replay(self,replay_id,session_id,process,job,reader,anchor):
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
            except Exception:
                self.latch_storage_failure(replay_id,'replay')
            finally:
                try:anchor.close()
                finally:self.active=None

    def start(self,strategy,profile,dataset_id,*,research=None,owner=None,expected_runtime=None):
        self.require_storage_ready()
        native=isinstance(strategy,dict) and strategy.get("engine")=="nautilus_trader"
        benchmark=isinstance(strategy,dict) and 'benchmark' in strategy
        if native:
            from terminal.native import preview
            report=preview(strategy)
            if not self.store.is_trusted(report["trust_sha256"]): raise ValueError("Explicit trust is required before loading this Python source")
            if report["dependency_problems"]: raise ValueError("Native dependencies are missing or incompatible; no automatic installation")
            require_native_execution()
        elif not benchmark:
            validate_graph(strategy)
        if not isinstance(profile,Profile): profile=Profile(**profile)
        if native and profile.execution_minutes!=1:raise ValueError("Native Python requires detailed M1 execution history")
        manifest=self.datasets.describe(dataset_id)
        self.datasets.check_profile(manifest,profile)
        if benchmark:
            from terminal.benchmarks import validate_document
            frozen=validate_document(strategy,profile,manifest)
            if research!={'benchmark_contract':frozen['contract_sha256']}:
                raise ValueError('Benchmark jobs require their frozen contract')
        snapshot=run_manifest(strategy,profile,manifest)
        if expected_runtime is not None and snapshot['runtime']!=expected_runtime:raise ValueError('Runtime changed since experiment preparation')
        if research is not None:
            from terminal.data import digest
            snapshot.pop('snapshot_sha256')
            snapshot['research']=research
            snapshot=json.loads(canonical(snapshot))
            snapshot['snapshot_sha256']=digest(snapshot)
        with self.lock:
            self.require_storage_ready()
            if self.reservation is not None and self.reservation!=owner:raise ValueError('A parameter experiment owns the calculation slot')
            if self.active is not None: raise ValueError("One backtest is already active")
            from terminal.research_evidence import admission
            try:
                generation=uuid.uuid4().hex
                run_id=self.store.create(snapshot,evidence=admission(snapshot,manifest,owner),local_generation=generation)
            except (OSError,sqlite3.Error):
                self.latch_storage_failure(owner or 'admission','research_admission')
                raise
            job=None;process=None
            try:
                job=worker_job(self.instance_file)
                process=subprocess.Popen([sys.executable,"-m","terminal.worker"],cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**worker_options(job))
                job.assign(process)
                self.active={"id":run_id,"generation":generation,"process":process,"job":job,"cancelled":False,"phase":"computing"}
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
                if job:job.close()
                if process:
                    if sys.platform!='linux' and process.poll() is None: process.terminate()
                    process.wait(timeout=5)
                    if process.stdin and not process.stdin.closed:process.stdin.close()
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
        from terminal import result_finalization as finalization
        with self.lock:
            active=self.active
            if active is None or active['id']!=run_id:return
        anchor=None;cleanup=False;owned_cleanup=False;code=0;error=None
        try:
            code=process.wait();job.close();reader.join(timeout=5)
            if reader.is_alive():raise RuntimeError('Worker log cleanup is incomplete')
            owned_cleanup=True
            with self.lock:pending=active.get('cancel_pending')
            if pending:pending.wait()
            with self.lock:cancelled=active['cancelled']
            if not cancelled and code==0:
                finalization.claim(self.store,run_id,active['generation'])
                # Keep WAL lifetime in the service while a cancellable finalizer
                # owns a DB connection; required by the retained Windows path.
                anchor=sqlite3.connect(self.store.database,timeout=15,check_same_thread=False)
                anchor.execute('SELECT count(*) FROM sqlite_master').fetchone()
                new_job=worker_job(self.instance_file);candidate=None;owned_cleanup=False
                try:
                    candidate=subprocess.Popen([sys.executable,'-m','terminal.worker'],cwd=Path(__file__).resolve().parents[1],
                        stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**worker_options(new_job))
                    # Retain the same active record and monitor captured by batch
                    # waiters. GO follows attachment and platform assignment.
                    with self.lock:
                        active.update(process=candidate,job=new_job,phase='finalizing')
                    process=candidate;job=new_job
                    new_job.assign(candidate)
                    with self.lock:cancelled=active['cancelled']
                    if cancelled:new_job.terminate()
                    else:
                        candidate.stdin.write(canonical({'version':1,'command':'finalize_run','root':str(self.store.root),
                            'run_id':run_id,'generation':active['generation']})+b'\n')
                    candidate.stdin.close()
                except Exception as exc:
                    cleanup_error=None
                    try:new_job.close()
                    except Exception as failure:cleanup_error=failure
                    if candidate:
                        try:
                            if candidate.stdin and not candidate.stdin.closed:candidate.stdin.close()
                        except BrokenPipeError:pass
                        except Exception as failure:cleanup_error=cleanup_error or failure
                        candidate.wait()  # Never release ownership on uncertain reaping.
                    if cleanup_error:raise cleanup_error
                    owned_cleanup=True
                    raise FinalizerBootstrapError('Result finalizer could not start') from exc
                code=candidate.wait();new_job.close();owned_cleanup=True
            elif code and not cancelled:
                error_file=self.store.directory(run_id)/'worker-error.json'
                error=json.loads(error_file.read_bytes())['message'] if error_file.exists() else f'Worker exited with code {code}'
            cleanup=True
        except finalization.Stopped:
            cleanup=owned_cleanup
        except (OSError,sqlite3.Error):
            self.latch_storage_failure(run_id,'run');code=finalization.STORAGE_EXIT
            cleanup=owned_cleanup
        except Exception as exc:
            error=str(exc)[:2000]
            cleanup=owned_cleanup
            if not cleanup:self.latch_storage_failure(run_id,'run')
        if not cleanup:
            self.latch_storage_failure(run_id,'run')
            # Anchor/active ownership retained; close() must report this honestly.
            active['anchor']=anchor
            return
        with self.lock:pending=active.get('cancel_pending')
        if pending:pending.wait()
        try:
            control=finalization.status(self.store,run_id)
            if active.get('storage_failed') or code==finalization.STORAGE_EXIT or control and control['error_code']=='storage_failure':
                self.latch_storage_failure(run_id,'run')
            else:
                if active['cancelled']:finalization.cancel(self.store,run_id,active['generation'])
                finalization.settle(self.store,run_id,active['generation'],code=code,error=error)
        except Exception:
            self.latch_storage_failure(run_id,'run')
        finally:
            try:
                if anchor:anchor.close()
            except Exception:
                self.latch_storage_failure(run_id,'run');active['anchor']=anchor
                return
            with self.lock:
                if self.active is active:self.active=None

    def cancel(self,run_id):
        from terminal import result_finalization as finalization
        with self.lock:
            active=self.active
            if active is None or active.get('kind')=='replay' or active['id']!=run_id:
                # A completed result can win just before a delayed cancel call.
                active=None
            else:
                active['cancelled']=True
                if 'cancel_pending' not in active:active['cancel_pending']=threading.Event()
        if active is None:
            if self.store.get(run_id)['status']=='completed':return {'status':'too_late'}
            raise ValueError('That run is not active')
        try:
            status=finalization.cancel(self.store,run_id,active['generation'],timeout=.25)
        except sqlite3.OperationalError as exc:
            if (getattr(exc,'sqlite_errorcode',0)&255) not in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):
                self.latch_storage_failure(run_id,'run')
                with self.lock:
                    active['storage_failed']=True
                    if self.active is active:active['job'].terminate()
                raise
            # A stalled write owner cannot monopolize foreground dispatch. The
            # request is pending, not terminal; reap then persist the cutoff.
            status='cancel_requested'
        except Exception:
            self.latch_storage_failure(run_id,'run')
            with self.lock:
                active['storage_failed']=True
                if self.active is active:active['job'].terminate()
            raise
        finally:active['cancel_pending'].set()
        if status=='cancel_requested':
            with self.lock:
                if self.active is active:active['job'].terminate()
        return {'status':status}

    def status(self,run_id):
        from terminal.result_finalization import status as finalization_status
        record=self.store.get(run_id)
        with self.lock:
            worker_active=bool(self.active and self.active['id']==run_id)
            pending_cancel=bool(worker_active and self.active['cancelled'])
        displayed='cancel_requested' if pending_cancel and record['status'] in ('running','finalizing') else record['status']
        return {'id':run_id,'status':displayed,'durable_status':record['status'],'error':record['error'],
                'progress':self._progress(self.store.directory(run_id)),
                'finalization':finalization_status(self.store,run_id),'worker_active':worker_active,
                'summary':record['summary'],'storage_failure':self.storage_diagnostic()}

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

    def close(self,*,release_workspace=True):
        errors=[]
        with self.lock:active=self.active
        if active:
            try:
                if active.get('kind')=='replay':self.cancel_replay(active['id'])
                else:self.cancel(active['id'])
            except Exception as exc:errors.append(exc)
            monitor=active['monitor'];monitor.join(timeout=10)
            if monitor.is_alive() or active['process'].poll() is None or self.active is active:
                errors.append(RuntimeError('Worker shutdown has not completed; workspace ownership is retained'))
                raise ExceptionGroup('Worker shutdown failed',errors)
        if release_workspace and not self.instance_file.closed:
            self.instance_file.seek(0)
            unlock_workspace(self.instance_file)
            self.instance_file.close()
        if errors:raise ExceptionGroup('Worker shutdown cleanup failed',errors)
