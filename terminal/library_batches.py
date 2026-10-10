"""Frozen library rows using the existing sequential experiment/job ownership."""
from datetime import datetime, timezone
import json
import sqlite3
import uuid
import math
from importlib.metadata import PackageNotFoundError

from terminal import benchmarks, library, research_evidence, source_limits
from terminal.data import canonical, digest, runtime_snapshot
from terminal.experiments import ExperimentManager, MAX_MINUTE_RUNS, validate_range
from terminal.native import preview as native_preview
from terminal.process_lifecycle import platform_capabilities
from terminal.profile import Profile
from terminal.series import PartialBars
from terminal.storage import identifier

MAX_ROWS = library.MAX_LIBRARY_ROWS


class LibraryBatchManager(ExperimentManager):
    # _reserve, _run, cancel and close deliberately retain the existing scheduler.
    def __init__(self, jobs):
        self.jobs = jobs; self.store = jobs.store; self.active = None
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS library_batches(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,snapshot TEXT NOT NULL,error TEXT);
                CREATE TABLE IF NOT EXISTS library_batch_metadata(batch_id TEXT PRIMARY KEY,name TEXT NOT NULL,notes TEXT NOT NULL,revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS library_rows(batch_id TEXT NOT NULL,ordinal INTEGER NOT NULL,status TEXT NOT NULL,run_id TEXT,error TEXT,reused INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(batch_id,ordinal));
            ''')
            db.execute("UPDATE library_batches SET status='interrupted',error='Application stopped; explicit pending-row resume required' WHERE status IN ('running','preparing')")
            db.execute("UPDATE library_rows SET status='interrupted',error='No mid-run recovery' WHERE status='running'")

    def prepare(self, selections, dataset_id, profile, start, end, interval, spot_dataset_id):
        if not isinstance(selections, list) or not 1 <= len(selections) <= MAX_ROWS:
            raise ValueError(f'Select 1–{MAX_ROWS} explicit strategy/timeframe rows')
        profile = Profile(**profile)
        if profile.evaluation != 'closed':raise ValueError('Library research requires confirmed bars')
        manifest = self.jobs.datasets.describe(dataset_id)
        self.jobs.datasets.check_profile(manifest, profile)
        validate_range([start,end], manifest['range'], 'Evaluation range')
        if start%(profile.execution_minutes*60) or end%(profile.execution_minutes*60):
            raise ValueError('Evaluation boundaries must align to execution candles')
        benchmarks.schedule(start,end,interval)
        runtime = runtime_snapshot(); rows = []; seen = set()
        for selection in selections:
            if not isinstance(selection,dict) or set(selection) != {'entry_id','version','minutes','parameters'}:
                raise ValueError('Invalid library selection fields')
            try:
                prepared = library.for_window(library.prepare(**selection),start)
            except (ValueError,OSError,PackageNotFoundError) as exc:
                entry=next((e for e in library.catalog() if e['id']==selection.get('entry_id') and e['version']==selection.get('version')),None)
                if entry is None or entry['kind']!='Native':raise
                # A missing/changed optional native source cannot hide graph results.
                key=digest(selection)
                if key in seen:raise ValueError('Duplicate strategy/version/parameter/timeframe row')
                seen.add(key)
                rows.append(dict(kind='native',name=entry['name'],selection=selection,contract=None,document=None,
                    profile={**profile.snapshot(),'primary_minutes':selection['minutes']},dataset=self._dataset(manifest),
                    error=f'Native preparation unavailable: {exc}',source_default_minutes=entry['source_default_minutes'],
                    author_recommended_minutes=entry['author_recommended_minutes']))
                continue
            key = digest(prepared['contract'])
            if key in seen:raise ValueError('Duplicate strategy/version/parameter/timeframe row')
            seen.add(key)
            entry = next(e for e in library.catalog() if e['id']==selection['entry_id'])
            error = None
            row_profile={**profile.snapshot(),'primary_minutes':selection['minutes'],'version':prepared['profile']['version']}
            try:row_profile=Profile(**row_profile).snapshot()
            except ValueError as exc:error=str(exc)
            if profile.market not in entry['markets']:error = 'Strategy does not support this market'
            elif prepared['kind']=='native':
                report = native_preview(prepared['document'])
                if profile.execution_minutes!=1:error = 'Native Python requires detailed M1 execution history'
                elif not self.store.is_trusted(report['trust_sha256']):error = 'Explicit native trust required in the existing editor'
                elif report['dependency_problems']:error = 'Reviewed native dependencies unavailable'
                elif not platform_capabilities()['native_execution']['available']:
                    error = platform_capabilities()['native_execution']['reason']
                elif profile.position_management is not None or float(profile.stop_loss) or float(profile.take_profit):
                    error = 'Native strategies require their own protection semantics; graph position/stop/take policies are incompatible'
            required = prepared['contract']['warmup_bars'] * selection['minutes'] * 60
            aligned = ((manifest['range'][0]+selection['minutes']*60-1)//(selection['minutes']*60))*(selection['minutes']*60)
            if not error and start-aligned < required:error = 'Insufficient preceding indicator warmup'
            rows.append(dict(kind=prepared['kind'],name=prepared['name'],selection=selection,contract=prepared['contract'],
                document=prepared['document'],profile=row_profile,dataset=self._dataset(manifest),error=error,
                source_default_minutes=entry['source_default_minutes'],author_recommended_minutes=entry['author_recommended_minutes']))
        # Baselines use real spot history, an independent account and no strategy policies.
        spot_id = dataset_id if profile.market=='spot' else spot_dataset_id
        for schedule,name in [('once','Buy & Hold'),(interval,'Scheduled DCA')]:
            row = dict(kind='benchmark',name=name,error=None)
            try:
                if profile.market == 'linear':
                    raise ValueError('Spot benchmark N/A: linear comparisons require an independently specified '
                                     'spot execution profile and explicit spot fee assumption; use a spot-origin '
                                     'comparison with reviewed spot settings')
                if spot_id is None:raise ValueError('No actual matching spot counterpart: benchmark N/A')
                spot = self.jobs.datasets.describe(spot_id)
                if spot['source'] != manifest['source']:raise ValueError('Spot counterpart source differs')
                p = Profile(**{**profile.snapshot(),'version':1,'market':'spot','leverage':'1','primary_minutes':profile.execution_minutes,
                               'stop_loss':'0','take_profit':'0','position_management':None}).snapshot()
                document = dict(benchmark='passive',version=1,start=start,end=end,interval=schedule)
                self.jobs.datasets.check_profile(spot,Profile(**p))
                frozen = benchmarks.validate_document(document,Profile(**p),spot,runtime)
                row.update(document=document,profile=p,dataset=self._dataset(spot),contract=frozen)
            except ValueError as exc:row['error']=str(exc)
            rows.append(row)
        breakdown=[]
        for ordinal,row in enumerate(rows):
            if row['error']:
                breakdown.append(dict(ordinal=ordinal,kind=row['kind'],prefix_source_candles=0,
                    evaluation_source_candles=0,modeled_source_candles=0))
                continue
            seconds=row['profile'].get('execution_minutes',1)*60
            prefix=0 if row['kind']=='benchmark' else (start-row['dataset']['range'][0])//seconds
            evaluation=(end-start)//seconds
            breakdown.append(dict(ordinal=ordinal,kind=row['kind'],execution_minutes=seconds//60,
                prefix_source_candles=prefix,evaluation_source_candles=evaluation,
                modeled_source_candles=prefix+evaluation))
        workload=sum(row['modeled_source_candles'] for row in breakdown)
        if workload > MAX_MINUTE_RUNS:raise ValueError('Batch exceeds 2,000,000 modeled source-candle executions including strategy prefix')
        value = dict(version=1,metric_version=benchmarks.VERSION,rows=rows,start=start,end=end,runtime=runtime,
                     workload_version=2,workload_breakdown=breakdown,modeled_source_candles=workload,
                     source_load_policy=source_limits.policy(),
                     modeled_minutes=workload,capital=profile.capital,market=profile.market,symbol=profile.symbol,
                     inputs=dict(selections=selections,dataset_id=dataset_id,profile=profile.snapshot(),start=start,end=end,
                                 interval=interval,spot_dataset_id=spot_dataset_id))
        return json.loads(canonical({**value,'contract_sha256':digest(value)}))

    def warmup(self,selections,dataset_id):
        if not isinstance(selections,list) or not 1<=len(selections)<=MAX_ROWS:
            raise ValueError(f'Select 1–{MAX_ROWS} strategy/timeframe rows')
        manifest=self.jobs.datasets.describe(dataset_id)
        required=manifest['range'][0];alignment=manifest.get('interval_seconds',60)
        for selection in selections:
            try:prepared=library.prepare(**selection)
            except (ValueError,OSError,PackageNotFoundError):
                entry=next((e for e in library.catalog() if e['id']==selection.get('entry_id') and e['version']==selection.get('version')),None)
                if entry is None or entry['kind']!='Native':raise
                continue  # Preview retains this unavailable row and its reason.
            step=selection['minutes']*60
            required=max(required,((manifest['range'][0]+step-1)//step+prepared['contract']['warmup_bars'])*step)
            alignment=math.lcm(alignment,step)
        start=(required+alignment-1)//alignment*alignment
        return {'start':start,'end':manifest['range'][1],'history_start':manifest['range'][0],
                'available':start<manifest['range'][1],
                'note':'Suggested boundary reserves complete preceding indicator bars. Full hash and gap checks run during preparation.'}

    @staticmethod
    def _dataset(manifest):
        return {k:manifest[k] for k in ('id','range','content_sha256')}

    def preview(self, **params):
        frozen = self.prepare(**params)
        return dict(contract_sha256=frozen['contract_sha256'],modeled_minutes=frozen['modeled_minutes'],
                    modeled_source_candles=frozen['modeled_source_candles'],workload_version=frozen['workload_version'],
                    workload_breakdown=frozen['workload_breakdown'],source_load_policy=frozen['source_load_policy'],
                    rows=[{k:r.get(k) for k in ('name','kind','error','contract')} for r in frozen['rows']])

    def start(self, expected_contract, observation=None, **params):
        frozen = self.prepare(**params)
        if frozen['contract_sha256'] != expected_contract:raise ValueError('Preview changed; review workload again')
        if not any(not r['error'] and r['kind']!='benchmark' for r in frozen['rows']):
            raise ValueError('No compatible strategy rows; review preflight errors')
        ident = uuid.uuid4().hex
        thread = self._reserve(ident,self._batch)
        try:
            self._save(ident,frozen,'preparing',observation=observation)
            thread.start()
        except Exception as exc:
            if isinstance(exc,(sqlite3.Error,OSError)):
                self.jobs.latch_storage_failure(ident,'observation_batch_admission')
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'batch_id':ident}

    def _save(self, ident, frozen, status, evidence=None, observation=None):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if observation is not None:
                from terminal.observations import attach_batch, source_identity
                attach_batch(db,ident,observation,frozen,source_identity(self.jobs.datasets.describe(frozen['inputs']['dataset_id'])))
            if evidence is not None:
                research_evidence.append(db,'frozen:library:'+ident,'frozen',evidence)
            db.execute('INSERT INTO library_batches VALUES(?,?,?,?,NULL)',
                       (ident,datetime.now(timezone.utc).isoformat(),status,canonical(frozen).decode()))
            for ordinal,row in enumerate(frozen['rows']):
                db.execute('INSERT INTO library_rows VALUES(?,?,?,NULL,?,0)',
                           (ident,ordinal,'incompatible' if row['error'] else 'pending',row['error']))

    def freeze_validation(self, batch_id, ordinal, dataset_id, start, end, spot_dataset_id):
        report=self.get(batch_id);source=report['snapshot']
        if report['status'] in ('running','preparing','frozen') or source.get('phase')=='out_of_sample':
            raise ValueError('Select a finished selection batch, not a holdout')
        if type(ordinal) is not int or not 0<=ordinal<len(report['rows']):raise ValueError('Invalid candidate ordinal')
        row=report['rows'][ordinal];spec=source['rows'][ordinal]
        if row['status']!='completed' or spec['kind']=='benchmark':raise ValueError('Only a completed strategy can be frozen')
        if type(start) is not int or start<source['end']:raise ValueError('Validation must start after the selection range')
        prepared=library.for_window(library.prepare(**spec['selection']),source['start'])
        if prepared['contract']!=spec['contract'] or prepared['document']!=spec['document']:
            raise ValueError('Selected library source changed; run a new selection first')
        previous=self.jobs.datasets.describe(spec['dataset']['id']);later=self.jobs.datasets.describe(dataset_id)
        if any(previous[k]!=later[k] for k in ('source','market','symbol')):raise ValueError('Later history must match source, market and symbol')
        frozen=self.prepare([spec['selection']],dataset_id,spec['profile'],start,end,source['inputs']['interval'],spot_dataset_id)
        strategy_errors = [r['error'] for r in frozen['rows'] if r['kind'] != 'benchmark' and r['error']]
        if strategy_errors:raise ValueError('Validation preflight: '+'; '.join(strategy_errors))
        # Explicitly unavailable passive alternatives remain N/A; they must not
        # prevent an otherwise valid frozen strategy from later-period testing.
        entry=next(e for e in library.catalog() if e['id']==spec['selection']['entry_id'])
        with self.store.connect() as db:
            previous_attempts=db.execute("SELECT count(*) FROM library_batches WHERE json_extract(snapshot,'$.phase')='out_of_sample' AND json_extract(snapshot,'$.symbol')=? AND json_extract(snapshot,'$.market')=? AND json_extract(snapshot,'$.start')<? AND json_extract(snapshot,'$.end')>?",(source['symbol'],source['market'],end,start)).fetchone()[0]
            variants=db.execute("SELECT count(DISTINCT json_extract(b.snapshot,'$.rows[' || r.ordinal || '].contract') || json_extract(b.snapshot,'$.rows[' || r.ordinal || '].profile')) FROM library_rows r JOIN library_batches b ON b.id=r.batch_id WHERE r.run_id IS NOT NULL AND coalesce(json_extract(b.snapshot,'$.phase'),'selection')!='out_of_sample' AND json_extract(b.snapshot,'$.rows[' || r.ordinal || '].kind')!='benchmark' AND json_extract(b.snapshot,'$.symbol')=? AND json_extract(b.snapshot,'$.market')=?",(source['symbol'],source['market'])).fetchone()[0]
        frozen['phase']='out_of_sample'
        frozen['validation']=dict(selection_batch_id=batch_id,selection_ordinal=ordinal,selection_run_id=row['run_id'],
            selection_range=[source['start'],source['end']],candidate_sha256=digest(spec),
            selection_contract=spec['contract'],selection_profile=spec['profile'],selection_metrics=row['metrics'],
            selection_attempted_variants=variants,holdout_attempt=previous_attempts+1,
            source_version_date=entry['source_version_date'],frozen_at=datetime.now(timezone.utc).isoformat(),
            warning='Repeated or changed selections reuse the holdout. This does not prove the external author never observed this period. Source versions may postdate the market history.')
        frozen['contract_sha256']=digest({k:v for k,v in frozen.items() if k!='contract_sha256'})
        ident=uuid.uuid4().hex
        evidence=research_evidence.event(later,spec['profile'],start,end,route='library',owner_id=ident,
            identity={'selection_batch_id':batch_id,'ordinal':ordinal,'candidate_sha256':digest(spec)})
        self.jobs.require_storage_ready()
        try:self._save(ident,frozen,'frozen',evidence)
        except (OSError,sqlite3.Error):
            self.jobs.latch_storage_failure(ident,'research_freeze');raise
        return {'batch_id':ident,'contract_sha256':frozen['contract_sha256']}

    def start_validation(self, batch_id):
        report=self.get(batch_id)
        if report['status']!='frozen' or report['snapshot'].get('phase')!='out_of_sample':
            raise ValueError('Validation must be frozen and can start only once')
        self._unchanged(report['snapshot'])
        thread=self._reserve(batch_id,self._batch)
        try:
            with self.store.connect() as db:db.execute("UPDATE library_batches SET status='preparing' WHERE id=?",(batch_id,))
            thread.start()
        except Exception:
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'batch_id':batch_id}

    def resume(self, batch_id):
        report = self.get(batch_id)
        if report['status'] not in ('cancelled','interrupted','failed') or not any(r['status']=='pending' for r in report['rows']):
            raise ValueError('Only stopped batches with pending rows can resume')
        self._unchanged(report['snapshot'])
        thread = self._reserve(batch_id,self._batch)
        try:
            with self.store.connect() as db:db.execute("UPDATE library_batches SET status='preparing',error=NULL WHERE id=?",(batch_id,))
            thread.start()
        except Exception:
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'batch_id':batch_id}

    def _unchanged(self, frozen):
        if digest({k:v for k,v in frozen.items() if k!='contract_sha256'}) != frozen['contract_sha256']:
            raise ValueError('Frozen batch checksum mismatch')
        if runtime_snapshot()!=frozen['runtime']:raise ValueError('Runtime changed; frozen batch cannot resume')
        for row in frozen['rows']:
            if row['error']:continue
            if self._dataset(self.jobs.datasets.describe(row['dataset']['id']))!=row['dataset']:
                raise ValueError('Frozen dataset changed')
            if row['kind']!='benchmark':
                prepared=library.for_window(library.prepare(**row['selection']),frozen['start'])
                if prepared['contract']!=row['contract'] or prepared['document']!=row['document']:
                    raise ValueError('Reviewed library source changed')

    def _preflight_data(self, active, frozen):
        # Hash and coverage checks run on the scheduler thread, never the IPC thread.
        for dataset_id in dict.fromkeys(r['dataset']['id'] for r in frozen['rows'] if not r['error']):
            if active['stop'].is_set():return
            _,bars,_,_=self.jobs.datasets.load(dataset_id)
            for row in frozen['rows']:
                if row['error'] or row['dataset']['id']!=dataset_id:continue
                if not any(frozen['start']<=b.time<frozen['end'] for b in bars):raise ValueError('Evaluation history is empty')
                if row['kind']=='benchmark':continue
                aggregate=PartialBars(row['profile']['primary_minutes'],history_limit=row['contract']['warmup_bars'],source_minutes=row['profile'].get('execution_minutes',1))
                for bar in bars:
                    if active['stop'].is_set():return
                    if bar.time>=frozen['start']:break
                    aggregate.update(bar)
                if len(aggregate.closed)<row['contract']['warmup_bars']:
                    raise ValueError('History gaps leave insufficient complete warmup bars')

    def _batch(self, active):
        ident=active['id'];status='completed';error=None
        try:
            report=self.get(ident);frozen=report['snapshot']
            self._unchanged(frozen);self._preflight_data(active,frozen)
            with self.store.connect() as db:db.execute("UPDATE library_batches SET status='running' WHERE id=?",(ident,))
            for row in report['rows']:
                self.jobs.require_storage_ready()
                if active['stop'].is_set():break
                if row['status']!='pending':continue
                ordinal=row['ordinal'];spec=frozen['rows'][ordinal]
                def started(run_id):
                    with self.store.connect() as db:db.execute("UPDATE library_rows SET status='running',run_id=? WHERE batch_id=? AND ordinal=?",(run_id,ident,ordinal))
                try:
                    reused=False
                    if spec['kind']=='benchmark':
                        research={'benchmark_contract':spec['contract']['contract_sha256']}
                        with self.store.connect() as db:
                            cached=db.execute("SELECT id FROM runs WHERE status='completed' AND json_extract(summary,'$.origin')='local' AND json_extract(manifest,'$.research.benchmark_contract')=? ORDER BY created_at,id LIMIT 1",(research['benchmark_contract'],)).fetchone()
                        if cached:
                            self.store.result(cached['id']);started(cached['id']);result=self.store.get(cached['id']);reused=True
                    else:
                        research={'window':{'start':frozen['start'],'end':frozen['end'],'warmup_start':spec['dataset']['range'][0]},
                                  'library':{'batch_id':ident,'ordinal':ordinal,'contract':spec['contract'],'batch_sha256':frozen['contract_sha256'],'phase':frozen.get('phase','selection'),'validation':frozen.get('validation')}}
                    if not reused:
                        document=spec['document']['graph'] if spec['kind']=='graph' else spec['document']
                        result=self._run(active,document,{'dataset':spec['dataset'],'runtime':frozen['runtime']},spec['profile'],research,started)
                    if result:
                        with self.store.connect() as db:db.execute('UPDATE library_rows SET status=?,error=?,reused=? WHERE batch_id=? AND ordinal=?',(result['status'],result['error'],int(reused),ident,ordinal))
                except Exception as exc:
                    with self.store.connect() as db:db.execute("UPDATE library_rows SET status='failed',error=? WHERE batch_id=? AND ordinal=?",(str(exc)[:2000],ident,ordinal))
            if active['stop'].is_set():status='cancelled'
            elif any(r['status']!='completed' for r in self.get(ident)['rows']):status='completed_with_errors'
        except Exception as exc:status='failed';error=str(exc)[:2000]
        finally:
            self._finalize(ident,'library_batch','library_batches',status,error)

    def get(self, batch_id):
        with self.store.connect() as db:
            record=db.execute('SELECT * FROM library_batches WHERE id=?',(identifier(batch_id),)).fetchone()
            if record is None:raise ValueError('Unknown library batch')
            rows=db.execute('SELECT l.*,r.summary FROM library_rows l LEFT JOIN runs r ON r.id=l.run_id WHERE batch_id=? ORDER BY ordinal',(batch_id,)).fetchall()
        result=dict(record);result['metadata']=self.metadata(batch_id);result['snapshot']=json.loads(result['snapshot']);result['rows']=[]
        for saved in rows:
            row=dict(saved);summary=json.loads(row.pop('summary')) if saved['summary'] else None
            row['metrics']=benchmarks.metrics({'status':'completed',**summary},result['snapshot']['start'],result['snapshot']['end']) if row['status']=='completed' and summary else None
            row['progress']=self.jobs.status(row['run_id']).get('progress') if row['status']=='running' and row['run_id'] else None
            result['rows'].append(row)
        with self.store.connect() as db:result['research_evidence']=research_evidence.frozen_review(db,'library',batch_id)
        result['active_id']=self.active['id'] if self.active else None
        with self.store.connect() as db:
            link=db.execute('SELECT observation_id AS id,revision FROM observation_batches WHERE batch_id=?',(batch_id,)).fetchone()
        result['observation']=dict(link) if link else None
        result['storage_failure']=self.jobs.storage_diagnostic()
        return result

    def metadata(self, batch_id):
        with self.store.connect() as db:
            if db.execute('SELECT 1 FROM library_batches WHERE id=?',(identifier(batch_id),)).fetchone() is None:
                raise ValueError('Unknown library batch')
            row=db.execute('SELECT name,notes,revision FROM library_batch_metadata WHERE batch_id=?',(identifier(batch_id),)).fetchone()
        return dict(row) if row else {'name':'','notes':'','revision':0}

    def save_metadata(self, batch_id, name, notes, expected_revision):
        """Mutable annotations only; optimistic concurrency protects other editors."""
        identifier(batch_id)
        if not isinstance(name,str) or len(name)>120 or '\x00' in name:
            raise ValueError('Comparison name must be text of at most 120 characters')
        if not isinstance(notes,str) or len(notes)>4000 or '\x00' in notes:
            raise ValueError('Comparison notes must be text of at most 4000 characters')
        if type(expected_revision) is not int or expected_revision<0:
            raise ValueError('Invalid metadata revision')
        name=name.strip()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM library_batches WHERE id=?',(batch_id,)).fetchone() is None:
                raise ValueError('Unknown library batch')
            row=db.execute('SELECT revision FROM library_batch_metadata WHERE batch_id=?',(batch_id,)).fetchone()
            if (row['revision'] if row else 0)!=expected_revision:
                raise ValueError('Comparison details changed in another editor. Reload saved details before saving again.')
            revision=expected_revision+1
            db.execute('INSERT INTO library_batch_metadata VALUES(?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET name=excluded.name,notes=excluded.notes,revision=excluded.revision',
                       (batch_id,name,notes,revision))
        return {'name':name,'notes':notes,'revision':revision}

    def history_page(self, before=None, query=""):
        """Search the full catalog before bounded keyset paging; literal Unicode casefold."""
        if not isinstance(query,str) or len(query)>200 or '\x00' in query:
            raise ValueError('Search must be text of at most 200 characters')
        query=query.strip().casefold()
        params=[];clauses=[]
        if query:
            clauses.append("(instr(casefold(coalesce(m.name,'')),?)>0 OR instr(casefold(coalesce(m.notes,'')),?)>0 OR instr(casefold(b.id),?)>0 OR instr(casefold(b.created_at),?)>0)")
            params.extend([query]*4)
        if before is not None:
            if not isinstance(before,dict) or set(before)!={'created_at','id'}:
                raise ValueError('Invalid comparison history cursor')
            identifier(before['id'])
            if not isinstance(before['created_at'],str) or len(before['created_at'])>64:
                raise ValueError('Invalid comparison history timestamp')
            datetime.fromisoformat(before['created_at'])
            clauses.append('(b.created_at,b.id)<(?,?)')
            params.extend([before['created_at'],before['id']])
        where='WHERE '+' AND '.join(clauses) if clauses else ''
        with self.store.connect() as db:
            db.create_function('casefold',1,lambda value:value.casefold())
            rows=db.execute(f"SELECT b.id,b.created_at,b.status,b.error,coalesce(json_extract(b.snapshot,'$.phase'),'selection') AS phase,coalesce(m.name,'') AS name FROM library_batches b LEFT JOIN library_batch_metadata m ON m.batch_id=b.id {where} ORDER BY b.created_at DESC,b.id DESC LIMIT 51",params).fetchall()
        selected=[];size=0
        for row in rows[:50]:
            value=dict(row);size+=len(canonical(value))
            if size>512*1024:
                if not selected:raise ValueError('Individual comparison row exceeds IPC budget')
                break
            selected.append(value)
        cursor={k:selected[-1][k] for k in ('created_at','id')} if len(rows)>len(selected) else None
        return {'rows':selected,'next':cursor}

    def recent(self):
        return self.history_page()['rows']

    def equity(self, batch_id, ordinal):
        report=self.get(batch_id)
        if type(ordinal) is not int or not 0<=ordinal<len(report['rows']) or report['snapshot']['rows'][ordinal]['kind']=='benchmark':
            raise ValueError('Select a strategy row for equity comparison')
        selected=[report['rows'][ordinal]]+[r for r in report['rows'] if report['snapshot']['rows'][r['ordinal']]['kind']=='benchmark']
        curves=[]
        for row in selected:
            spec=report['snapshot']['rows'][row['ordinal']]
            curve=dict(name=spec['name'],status=row['status'],run_id=row['run_id'],points=[])
            if row['status']=='completed':
                with self.store.connect() as db:
                    count=db.execute("SELECT count(*) FROM series WHERE run_id=? AND kind='equity'",(row['run_id'],)).fetchone()[0]
                    # Direct indexed lookups, at most 400 observations per curve.
                    indices=sorted({round(i*(count-1)/399) for i in range(min(count,400))}) if count>400 else list(range(count))
                    for index in indices:
                        point=json.loads(db.execute("SELECT value FROM series WHERE run_id=? AND kind='equity' AND row_index=?",(row['run_id'],index)).fetchone()[0])
                        if point['time_ns']>=report['snapshot']['start']*1_000_000_000:
                            curve['points'].append({'time_ns':point['time_ns'],'equity':point['equity']})
                curve['observations']=count
            curves.append(curve)
        return dict(start=report['snapshot']['start'],end=report['snapshot']['end'],capital=report['snapshot']['capital'],curves=curves,
                    note='Up to 400 sampled observations per curve; metrics use every recorded point. Passive spot alternatives are not leverage/risk equivalent.')
