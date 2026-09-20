"""Frozen library rows using the existing sequential experiment/job ownership."""
from datetime import datetime, timezone
import json
import uuid

from terminal import benchmarks, library
from terminal.data import canonical, digest, runtime_snapshot
from terminal.experiments import ExperimentManager, MAX_MINUTE_RUNS, validate_range
from terminal.native import preview as native_preview
from terminal.profile import Profile
from terminal.series import PartialBars
from terminal.storage import identifier

MAX_ROWS = 12


class LibraryBatchManager(ExperimentManager):
    # _reserve, _run, cancel and close deliberately retain the existing scheduler.
    def __init__(self, jobs):
        self.jobs = jobs; self.store = jobs.store; self.active = None
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS library_batches(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,snapshot TEXT NOT NULL,error TEXT);
                CREATE TABLE IF NOT EXISTS library_rows(batch_id TEXT NOT NULL,ordinal INTEGER NOT NULL,status TEXT NOT NULL,run_id TEXT,error TEXT,reused INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(batch_id,ordinal));
            ''')
            db.execute("UPDATE library_batches SET status='interrupted',error='Application stopped; explicit pending-row resume required' WHERE status IN ('running','preparing')")
            db.execute("UPDATE library_rows SET status='interrupted',error='No mid-run recovery' WHERE status='running'")

    def prepare(self, selections, dataset_id, profile, start, end, interval, spot_dataset_id):
        if not isinstance(selections, list) or not 1 <= len(selections) <= MAX_ROWS:
            raise ValueError('Select 1–12 explicit strategy/timeframe rows')
        profile = Profile(**profile)
        if profile.evaluation != 'closed':raise ValueError('Library research requires confirmed bars')
        manifest = self.jobs.datasets.describe(dataset_id)
        self.jobs.datasets.check_profile(manifest, profile)
        validate_range([start,end], manifest['range'], 'Evaluation range')
        benchmarks.schedule(start,end,interval)
        runtime = runtime_snapshot(); rows = []; seen = set()
        for selection in selections:
            if not isinstance(selection,dict) or set(selection) != {'entry_id','version','minutes','parameters'}:
                raise ValueError('Invalid library selection fields')
            prepared = library.prepare(**selection)
            key = digest(prepared['contract'])
            if key in seen:raise ValueError('Duplicate strategy/version/parameter/timeframe row')
            seen.add(key)
            entry = next(e for e in library.catalog() if e['id']==selection['entry_id'])
            row_profile = Profile(**{**profile.snapshot(),'primary_minutes':selection['minutes'],
                                     'version':prepared['profile']['version']}).snapshot()
            error = None
            if profile.market not in entry['markets']:error = 'Strategy does not support this market'
            elif prepared['kind']=='native':
                report = native_preview(prepared['document'])
                if not self.store.is_trusted(report['trust_sha256']):error = 'Explicit native trust required in the existing editor'
                elif report['dependency_problems']:error = 'Reviewed native dependencies unavailable'
                else:error = 'Native separate-window warmup is not supported by this library version'
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
                if spot_id is None:raise ValueError('No actual matching spot counterpart: benchmark N/A')
                spot = self.jobs.datasets.describe(spot_id)
                if spot['source'] != manifest['source']:raise ValueError('Spot counterpart source differs')
                p = Profile(**{**profile.snapshot(),'version':1,'market':'spot','leverage':'1','primary_minutes':1,
                               'stop_loss':'0','take_profit':'0','position_management':None}).snapshot()
                document = dict(benchmark='passive',version=1,start=start,end=end,interval=schedule)
                self.jobs.datasets.check_profile(spot,Profile(**p))
                frozen = benchmarks.validate_document(document,Profile(**p),spot,runtime)
                row.update(document=document,profile=p,dataset=self._dataset(spot),contract=frozen)
            except ValueError as exc:row['error']=str(exc)
            rows.append(row)
        workload = sum((end-r['dataset']['range'][0])//60 for r in rows if not r['error'])
        if workload > MAX_MINUTE_RUNS:raise ValueError('Batch exceeds 2,000,000 modeled minutes including warmup')
        value = dict(version=1,metric_version=benchmarks.VERSION,rows=rows,start=start,end=end,runtime=runtime,
                     modeled_minutes=workload,capital=profile.capital,market=profile.market,symbol=profile.symbol,
                     inputs=dict(selections=selections,dataset_id=dataset_id,profile=profile.snapshot(),start=start,end=end,
                                 interval=interval,spot_dataset_id=spot_dataset_id))
        return json.loads(canonical({**value,'contract_sha256':digest(value)}))

    @staticmethod
    def _dataset(manifest):
        return {k:manifest[k] for k in ('id','range','content_sha256')}

    def preview(self, **params):
        frozen = self.prepare(**params)
        return dict(contract_sha256=frozen['contract_sha256'],modeled_minutes=frozen['modeled_minutes'],
                    rows=[{k:r.get(k) for k in ('name','kind','error','contract')} for r in frozen['rows']])

    def start(self, expected_contract, **params):
        frozen = self.prepare(**params)
        if frozen['contract_sha256'] != expected_contract:raise ValueError('Preview changed; review workload again')
        if not any(not r['error'] and r['kind']!='benchmark' for r in frozen['rows']):
            raise ValueError('No compatible strategy rows; review preflight errors')
        ident = uuid.uuid4().hex
        thread = self._reserve(ident,self._batch)
        try:
            with self.store.connect() as db:
                db.execute('INSERT INTO library_batches VALUES(?,?,?,?,NULL)',
                           (ident,datetime.now(timezone.utc).isoformat(),'preparing',canonical(frozen).decode()))
                for ordinal,row in enumerate(frozen['rows']):
                    db.execute('INSERT INTO library_rows VALUES(?,?,?,NULL,?,0)',
                               (ident,ordinal,'incompatible' if row['error'] else 'pending',row['error']))
            thread.start()
        except Exception:
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'batch_id':ident}

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
                prepared=library.prepare(**row['selection'])
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
                aggregate=PartialBars(row['profile']['primary_minutes'],history_limit=row['contract']['warmup_bars'])
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
                                  'library':{'batch_id':ident,'ordinal':ordinal,'contract':spec['contract'],'batch_sha256':frozen['contract_sha256']}}
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
            with self.store.connect() as db:db.execute('UPDATE library_batches SET status=?,error=? WHERE id=?',(status,error,ident))
            with self.jobs.lock:self.active=None;self.jobs.reservation=None

    def get(self, batch_id):
        with self.store.connect() as db:
            record=db.execute('SELECT * FROM library_batches WHERE id=?',(identifier(batch_id),)).fetchone()
            if record is None:raise ValueError('Unknown library batch')
            rows=db.execute('SELECT l.*,r.summary FROM library_rows l LEFT JOIN runs r ON r.id=l.run_id WHERE batch_id=? ORDER BY ordinal',(batch_id,)).fetchall()
        result=dict(record);result['snapshot']=json.loads(result['snapshot']);result['rows']=[]
        for saved in rows:
            row=dict(saved);summary=json.loads(row.pop('summary')) if saved['summary'] else None
            row['metrics']=benchmarks.metrics({'status':'completed',**summary},result['snapshot']['start'],result['snapshot']['end']) if row['status']=='completed' and summary else None
            row['progress']=self.jobs.status(row['run_id']).get('progress') if row['status']=='running' and row['run_id'] else None
            result['rows'].append(row)
        result['active_id']=self.active['id'] if self.active else None
        return result

    def recent(self):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,created_at,status,error FROM library_batches ORDER BY created_at DESC,id DESC LIMIT 50')]

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
