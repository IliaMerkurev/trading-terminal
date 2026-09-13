"""Bounded sequential research, immutable selection and separate-period validation."""
import copy
from datetime import datetime,timezone
from decimal import Decimal
import itertools
import json
import math
import threading
import uuid

from terminal.data import canonical,digest,runtime_snapshot
from terminal.graph import validate_graph
from terminal.profile import Profile,dec
from terminal.storage import identifier

MAX_COMBINATIONS=256
MAX_MINUTE_RUNS=2_000_000


def parameter_fields(graph,profile=None):
    fields=[]
    for node in graph['nodes']:
        for key,value in node['params'].items():
            fields.append({'key':f"node.{node['id']}.{key}",'label':f"{node['id']} / {key}",
                'type':'integer' if key in ('period','fast','slow','signal') else 'number' if isinstance(value,(int,float)) else 'choice',
                'choices':['open','high','low','close','volume'] if key=='field' else ['>','>=','<','<=','==','!='] if key=='operator' else None,'current':value})
    fields.extend({'key':f'profile.{key}','label':label,'type':'fraction' if key in ('stop_loss','take_profit') else 'number','choices':None,'current':None}
        for key,label in [('stop_loss','Stop loss (fraction)'),('take_profit','Take profit (fraction)'),('allocation','Capital allocation'),('leverage','Leverage')])
    pm=(profile or {}).get('position_management')
    if pm is not None:
        from terminal.position_management import PositionConfig
        pm=PositionConfig(**pm).snapshot()
        for key in ('repeated_entry','scale_allocation_percent','max_entries','trailing_activation','trailing_distance','break_even_activation','atr_period','atr_stop_multiplier','atr_trailing_multiplier'):
            fields.append({'key':f'pm.{key}','label':'Position / '+key.replace('_',' '),
                           'type':'choice' if key=='repeated_entry' else 'integer' if key in ('max_entries','atr_period') else 'decimal',
                           'choices':['ignore','scale'] if key=='repeated_entry' else None,'current':pm[key]})
        for collection in ('dca','partial_take'):
            for index,row in enumerate(pm[collection]):
                for key,value in row.items():
                    fields.append({'key':f'pm.{collection}.{index}.{key}','label':f'Position / {collection} {index+1} / {key}',
                                   'type':'decimal','choices':None,'current':value})
    return fields


def apply_parameters(graph,profile,parameters):
    graph=copy.deepcopy(graph);profile=copy.deepcopy(profile)
    for key,value in parameters.items():
        parts=key.split('.')
        if parts[0]=='profile':profile[parts[1]]=str(value)
        elif parts[0]=='pm':
            if 'position_management' not in profile:raise ValueError('Enable Position Management before varying its parameters')
            if len(parts)==2:profile['position_management'][parts[1]]=value
            elif len(parts)==4:profile['position_management'][parts[1]][int(parts[2])][parts[3]]=str(value)
            else:raise ValueError('Invalid Position Management parameter path')
        else:next(n for n in graph['nodes'] if n['id']==parts[1])['params'][parts[2]]=value
    validate_graph(graph);Profile(**profile)
    return graph,profile


def normalize_axes(graph,axes,profile=None):
    if not isinstance(axes,list) or not 1<=len(axes)<=6:raise ValueError('Choose 1–6 parameter fields')
    fields={f['key']:f for f in parameter_fields(graph,profile)};seen=set();normalized=[];count=1
    for axis in axes:
        if not isinstance(axis,dict) or set(axis)!={'key','values'} or axis['key'] not in fields or axis['key'] in seen:raise ValueError('Unknown or duplicate parameter field')
        seen.add(axis['key']);field=fields[axis['key']]
        if not isinstance(axis['values'],list) or not 1<=len(axis['values'])<=100:raise ValueError('Each parameter requires 1–100 explicit values')
        values=[]
        for value in axis['values']:
            if field['type']=='choice':
                if value not in field['choices']:raise ValueError('Unsupported parameter choice')
            else:
                if isinstance(value,bool):raise ValueError('Boolean is not a numeric parameter')
                number=dec(value)
                if field['type']=='integer':
                    if number!=number.to_integral_value():raise ValueError('Indicator periods must be integers')
                    value=int(number)
                elif field['type']=='fraction':
                    if not 0<=number<1:raise ValueError('Protection fractions must be in [0, 1)')
                    value=str(number.normalize())
                elif field['type']=='decimal':value=str(number.normalize())
                else:
                    value=float(number)
                    if not math.isfinite(value):raise ValueError('Parameter exceeds numeric range')
            if value not in values:values.append(value)
        count*=len(values)
        if count>MAX_COMBINATIONS:raise ValueError(f'Grid exceeds {MAX_COMBINATIONS} unique combinations')
        normalized.append({'key':axis['key'],'values':values})
    return normalized,count


def warmup_bars(graph):
    nodes={n['id']:n for n in graph['nodes']};required={}
    for ident in validate_graph(graph):
        node=nodes[ident];p=node['params'];prior=max((required[ref.split('.')[0]] for ref in node['inputs'].values()),default=0)
        own=p.get('period',p.get('slow',0)+p.get('signal',0))
        required[ident]=prior+own+(1 if node['type'].startswith('cross_') else 0)
    return max(required.values(),default=0)


def validate_range(value,bounds,label):
    if not isinstance(value,list) or len(value)!=2 or any(type(t) is not int or t%60 for t in value) or not bounds[0]<=value[0]<value[1]<=bounds[1]:raise ValueError(f'{label} must be an increasing UTC minute range inside the dataset')
    return value


class ExperimentManager:
    def __init__(self,jobs):
        self.jobs=jobs;self.store=jobs.store;self.active=None
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,snapshot TEXT NOT NULL,error TEXT);
                CREATE TABLE IF NOT EXISTS experiment_rows(experiment_id TEXT NOT NULL,ordinal INTEGER NOT NULL,parameters TEXT NOT NULL,status TEXT NOT NULL,run_id TEXT,error TEXT,PRIMARY KEY(experiment_id,ordinal));
                CREATE TABLE IF NOT EXISTS validations(id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL,snapshot TEXT NOT NULL,run_id TEXT,error TEXT);
            ''')
            db.execute("UPDATE experiments SET status='interrupted',error='Application stopped; no automatic resume' WHERE status IN ('running','cancel_requested')")
            db.execute("UPDATE experiment_rows SET status='interrupted' WHERE status='running'")
            db.execute("UPDATE validations SET status='interrupted',error='Application stopped; no automatic retry' WHERE status IN ('running','cancel_requested')")

    def prepare(self,strategy_id,dataset_id,profile,is_range,oos_range,axes):
        strategy=self.store.strategy(strategy_id)
        if strategy['kind']!='graph':raise ValueError('Parameter experiments support saved visual strategies only')
        graph=strategy['document']['graph'];validate_graph(graph);profile=Profile(**profile)
        manifest=self.jobs.datasets.describe(dataset_id);self.jobs.datasets.check_profile(manifest,profile)
        validate_range(is_range,manifest['range'],'In-sample range');validate_range(oos_range,manifest['range'],'Out-of-sample range')
        if is_range[1]>oos_range[0]:raise ValueError('Out-of-sample must be later and disjoint from in-sample')
        axes,count=normalize_axes(graph,axes,profile.snapshot())
        if count*((is_range[1]-manifest['range'][0])//60)>MAX_MINUTE_RUNS:raise ValueError('Grid exceeds the 2,000,000 modeled-minute budget including warmup')
        required=0
        for values in itertools.product(*(a['values'] for a in axes)):
            candidate,p=apply_parameters(graph,profile.snapshot(),dict(zip((a['key'] for a in axes),values)))
            required=max(required,max(warmup_bars(candidate),(p.get('position_management') or {}).get('atr_period',0))*profile.primary_minutes*60)
        first_complete=((manifest['range'][0]+profile.primary_minutes*60-1)//(profile.primary_minutes*60))*(profile.primary_minutes*60)
        if oos_range[0]-first_complete<required:raise ValueError('Insufficient preceding warmup for the declared out-of-sample range')
        return {'version':1,'strategy_id':strategy_id,'name':strategy['name'],'graph':graph,'layout':strategy['document'].get('layout',{}),
            'dataset':{k:manifest[k] for k in ('id','range','content_sha256')},'profile':profile.snapshot(),'is_range':is_range,'oos_range':oos_range,'axes':axes,'count':count,
            'warmup_start':manifest['range'][0],'required_warmup_seconds':required,'runtime':runtime_snapshot(),
            'warnings':['Selection metrics use in-sample data only. Repeated holdout use weakens independence.']+(['In-sample starts before full indicator warmup; initial signals remain unavailable.'] if is_range[0]-first_complete<required else [])}

    def preview(self,**params):
        snapshot=self.prepare(**params)
        return {k:snapshot[k] for k in ('count','axes','warnings','required_warmup_seconds')}

    def fields(self,strategy_id,profile=None):
        strategy=self.store.strategy(strategy_id)
        if strategy['kind']!='graph':raise ValueError('Select a visual strategy')
        return parameter_fields(strategy['document']['graph'],Profile(**profile).snapshot() if profile is not None else None)

    def _reserve(self,ident,target):
        with self.jobs.lock:
            if self.active or self.jobs.active or self.jobs.reservation:raise ValueError('One calculation or experiment is already active')
            self.jobs.reservation=ident
            self.active={'id':ident,'stop':threading.Event(),'thread':None}
            thread=threading.Thread(target=target,args=(self.active,),daemon=True)
            self.active['thread']=thread
            return thread

    def start(self,**params):
        snapshot=json.loads(canonical(self.prepare(**params)));ident=uuid.uuid4().hex
        thread=self._reserve(ident,self._grid)
        try:
            with self.store.connect() as db:
                db.execute('INSERT INTO experiments VALUES(?,?,?,?,NULL)',(ident,datetime.now(timezone.utc).isoformat(),'running',canonical(snapshot).decode()))
                for i,values in enumerate(itertools.product(*(a['values'] for a in snapshot['axes']))):
                    parameters=dict(zip((a['key'] for a in snapshot['axes']),values))
                    db.execute('INSERT INTO experiment_rows VALUES(?,?,?,?,NULL,NULL)',(ident,i,canonical(parameters).decode(),'pending'))
            thread.start()
        except Exception:
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'experiment_id':ident}

    def _run(self,active,graph,snapshot,profile,research,on_started):
        with self.jobs.lock:
            if active['stop'].is_set():return None
            run_id=self.jobs.start(graph,profile,snapshot['dataset']['id'],research=research,owner=active['id'],expected_runtime=snapshot['runtime'])
            on_started(run_id)
            monitor=self.jobs.active['monitor']
        while monitor.is_alive():
            monitor.join(timeout=.1)
            if active['stop'].is_set():
                with self.jobs.lock:
                    if self.jobs.active and self.jobs.active['id']==run_id and not self.jobs.active['cancelled']:self.jobs.cancel(run_id)
        return self.store.get(run_id)

    def _grid(self,active):
        ident=active['id'];status='completed';error=None
        try:
            report=self.get(ident);snapshot=report['snapshot']
            for row in report['rows']:
                if active['stop'].is_set():break
                def started(run_id):
                    with self.store.connect() as db:db.execute("UPDATE experiment_rows SET run_id=?,status='running' WHERE experiment_id=? AND ordinal=?",(run_id,ident,row['ordinal']))
                try:
                    graph,profile=apply_parameters(snapshot['graph'],snapshot['profile'],row['parameters'])
                    result=self._run(active,graph,snapshot,profile,{'window':{'start':snapshot['is_range'][0],'end':snapshot['is_range'][1],'warmup_start':snapshot['warmup_start']},'experiment':{'id':ident,'ordinal':row['ordinal'],'parameters':row['parameters'],'phase':'in_sample','is_range':snapshot['is_range'],'oos_range':snapshot['oos_range'],'axes':snapshot['axes'],'snapshot_sha256':digest(snapshot)}},started)
                    if result:
                        with self.store.connect() as db:db.execute('UPDATE experiment_rows SET status=?,error=? WHERE experiment_id=? AND ordinal=?',(result['status'],result['error'],ident,row['ordinal']))
                except Exception as exc:
                    with self.store.connect() as db:db.execute("UPDATE experiment_rows SET status='failed',error=? WHERE experiment_id=? AND ordinal=?",(str(exc)[:2000],ident,row['ordinal']))
            if active['stop'].is_set():status='cancelled'
            else:
                with self.store.connect() as db:
                    failed=db.execute("SELECT COUNT(*) FROM experiment_rows WHERE experiment_id=? AND status='failed'",(ident,)).fetchone()[0]
                if failed:status='completed_with_errors'
        except Exception as exc:status='failed';error=str(exc)[:2000]
        finally:
            with self.store.connect() as db:db.execute('UPDATE experiments SET status=?,error=? WHERE id=?',(status,error,ident))
            with self.jobs.lock:self.active=None;self.jobs.reservation=None

    def recent(self):
        with self.store.connect() as db:rows=db.execute('SELECT id,created_at,status,error,json_extract(snapshot,\'$.name\') AS name FROM experiments ORDER BY created_at DESC LIMIT 100').fetchall()
        return [dict(r) for r in rows]

    def get(self,experiment_id):
        with self.store.connect() as db:
            record=db.execute('SELECT * FROM experiments WHERE id=?',(identifier(experiment_id),)).fetchone()
            if record is None:raise ValueError('Experiment does not exist')
            rows=db.execute('SELECT e.*,r.summary FROM experiment_rows e LEFT JOIN runs r ON r.id=e.run_id WHERE experiment_id=? ORDER BY ordinal',(experiment_id,)).fetchall()
            validations=db.execute('SELECT * FROM validations WHERE experiment_id=? ORDER BY created_at',(experiment_id,)).fetchall()
        result=dict(record);result['snapshot']=json.loads(result['snapshot']);result['rows']=[{**dict(r),'parameters':json.loads(r['parameters']),'summary':json.loads(r['summary']) if r['summary'] else None} for r in rows]
        result['validations']=[{**dict(r),'snapshot':json.loads(r['snapshot']),'summary':self.store.get(r['run_id'])['summary'] if r['run_id'] else None} for r in validations]
        result['finished']=sum(r['status'] in ('completed','failed','cancelled','interrupted') for r in rows)
        result['active_id']=self.active['id'] if self.active else None
        return result

    def cancel(self,active_id):
        with self.jobs.lock:
            if not self.active or self.active['id']!=active_id:raise ValueError('That experiment or validation is not active')
            self.active['stop'].set()
            if self.jobs.active:self.jobs.cancel(self.jobs.active['id'])
        return {'status':'cancel_requested'}

    def freeze(self,experiment_id,ordinal):
        report=self.get(experiment_id)
        if report['status']=='running':raise ValueError('Wait for the experiment to finish before selecting a candidate')
        if type(ordinal) is not int or not 0<=ordinal<len(report['rows']):raise ValueError('Invalid candidate ordinal')
        row=report['rows'][ordinal]
        if row['status']!='completed':raise ValueError('Only a completed candidate can be frozen')
        source=report['snapshot'];graph,profile=apply_parameters(source['graph'],source['profile'],row['parameters'])
        snapshot={**source,'graph':graph,'profile':profile,'candidate_ordinal':ordinal,'candidate_run_id':row['run_id'],'parameters':row['parameters']}
        snapshot['candidate_sha256']=digest({'graph':graph,'profile':profile,'dataset':source['dataset'],'runtime':source['runtime'],'oos_range':source['oos_range']})
        ident=uuid.uuid4().hex
        with self.store.connect() as db:db.execute('INSERT INTO validations VALUES(?,?,?,?,?,NULL,NULL)',(ident,experiment_id,datetime.now(timezone.utc).isoformat(),'frozen',canonical(snapshot).decode()))
        return {'validation_id':ident,'candidate_sha256':snapshot['candidate_sha256'],'warning':'Changing parameters requires a new frozen candidate. Reusing a holdout is another attempt, not an independent discovery.'}

    def validate(self,validation_id):
        with self.store.connect() as db:row=db.execute('SELECT * FROM validations WHERE id=?',(identifier(validation_id),)).fetchone()
        if row is None or row['status']!='frozen':raise ValueError('Validation must be frozen and can run only once per attempt')
        thread=self._reserve(validation_id,self._validation)
        try:
            with self.store.connect() as db:db.execute("UPDATE validations SET status='running' WHERE id=?",(validation_id,))
            thread.start()
        except Exception:
            with self.jobs.lock:self.active=None;self.jobs.reservation=None
            raise
        return {'validation_id':validation_id}

    def _validation(self,active):
        ident=active['id'];status='cancelled';error=None
        try:
            with self.store.connect() as db:row=db.execute('SELECT * FROM validations WHERE id=?',(ident,)).fetchone()
            s=json.loads(row['snapshot'])
            def started(run_id):
                with self.store.connect() as db:db.execute('UPDATE validations SET run_id=? WHERE id=?',(run_id,ident))
            result=self._run(active,s['graph'],s,s['profile'],{'window':{'start':s['oos_range'][0],'end':s['oos_range'][1],'warmup_start':s['warmup_start']},'experiment':{'id':row['experiment_id'],'validation_id':ident,'candidate_sha256':s['candidate_sha256'],'candidate_run_id':s['candidate_run_id'],'ordinal':s['candidate_ordinal'],'parameters':s['parameters'],'phase':'out_of_sample','is_range':s['is_range'],'oos_range':s['oos_range'],'axes':s['axes']}},started)
            if result:status=result['status'];error=result['error']
        except Exception as exc:status='failed';error=str(exc)[:2000]
        finally:
            with self.store.connect() as db:db.execute('UPDATE validations SET status=?,error=? WHERE id=?',(status,error,ident))
            with self.jobs.lock:self.active=None;self.jobs.reservation=None

    def copy_candidate(self,experiment_id,ordinal):
        report=self.get(experiment_id)
        if type(ordinal) is not int or not 0<=ordinal<len(report['rows']):raise ValueError('Invalid candidate ordinal')
        row=report['rows'][ordinal]
        if row['status']!='completed':raise ValueError('Select a completed result')
        s=report['snapshot'];graph,profile=apply_parameters(s['graph'],s['profile'],row['parameters'])
        ident=self.store.save_strategy((s['name']+' candidate '+str(ordinal+1))[:120],'graph',{'graph':graph,'layout':s['layout']},None,profile=profile)
        return {'strategy_id':ident}

    def close(self):
        with self.jobs.lock:
            active=self.active
            if active:self.cancel(active['id'])
        if active:
            active['thread'].join(timeout=15)
            if active['thread'].is_alive():raise RuntimeError('Experiment shutdown has not completed')
