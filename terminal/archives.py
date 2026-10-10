"""Versioned JSON-only archives; fixed destinations, bounded transfer, no extraction."""
import base64
import hashlib
import io
import json
import math
from pathlib import Path,PurePosixPath
import re
import stat
import sqlite3
import uuid
import zipfile

from terminal.data import canonical,digest,write_new,DatasetStore
from terminal.graph import validate_graph
from terminal.native import validate_native
from terminal.library import MAX_LIBRARY_ROWS
from terminal.profile import Profile,dec
from terminal.storage import SERIES,identifier

MAX_ARCHIVE=64*1024*1024
MAX_EXPANDED=128*1024*1024
MAX_FILES=25
CHUNK=256*1024


def validate_strategy(strategy):
    if not isinstance(strategy,dict) or set(strategy)!={'name','kind','document'} or not isinstance(strategy['name'],str) or not 1<=len(strategy['name'])<=120 or not strategy['name'].strip():
        raise ValueError('Invalid project strategy descriptor')
    if len(canonical(strategy['document']))>1024*1024:raise ValueError('Strategy exceeds size budget')
    if strategy['kind']=='graph':
        if set(strategy['document'])!={'graph','layout'}:raise ValueError('Invalid graph document')
        validate_graph(strategy['document']['graph'])
    elif strategy['kind']=='native':validate_native(strategy['document'])
    else:raise ValueError('Unsupported strategy format')


def privacy_check(value,entry):
    """Conservative export gate; report categories without secret values."""
    text=canonical(value).decode()
    patterns={
        'private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'credential literal':r'(?i)(?:api[_-]?key|api[_-]?secret|access[_-]?token|password|secret[_-]?key)[\\"\s]*[:=][\\"\s]*[A-Za-z0-9_+/=-]{8,}',
        'provider token':r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})',
        'personal email':r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        'local path':r'(?i)(?:[A-Z]:\\\\|/Users/|/home/|\\\\\\\\[^\\]+\\\\)',
    }
    for category,pattern in patterns.items():
        if re.search(pattern,text):raise ValueError(f'Export withheld: {category} detected in {entry}; review the source locally')


def validate_snapshot(snapshot):
    required={'schema_version','strategy','profile','dataset','runtime','snapshot_sha256'}
    if not isinstance(snapshot,dict) or set(snapshot)-{'research'}!=required or snapshot['schema_version']!=1:
        raise ValueError('Invalid run snapshot')
    if digest({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})!=snapshot['snapshot_sha256']:raise ValueError('Run snapshot checksum mismatch')
    Profile(**snapshot['profile'])
    passive = isinstance(snapshot['strategy'],dict) and 'benchmark' in snapshot['strategy']
    if passive:
        from terminal.benchmarks import validate_document
        profile=Profile(**snapshot['profile'])
        frozen=validate_document(snapshot['strategy'],profile,{**snapshot['dataset'],'market':profile.market,'symbol':profile.symbol},snapshot['runtime'])
        if snapshot.get('research')!={'benchmark_contract':frozen['contract_sha256']}:
            raise ValueError('Invalid archived benchmark contract')
    elif 'research' in snapshot:
        from terminal.experiments import validate_range
        research=snapshot['research']
        if not isinstance(research,dict) or set(research)-{'experiment','library'}!={'window'}:raise ValueError('Invalid research provenance')
        if 'library' in research:
            origin=research['library']
            if not isinstance(origin,dict) or set(origin)-{'phase','validation'}!={'batch_id','ordinal','contract','batch_sha256'} or type(origin['ordinal']) is not int or not 0<=origin['ordinal']<MAX_LIBRARY_ROWS:
                raise ValueError('Invalid library provenance')
            if origin.get('phase','selection') not in ('selection','out_of_sample'):raise ValueError('Invalid library research phase')
            if origin.get('phase')=='out_of_sample':
                validation=origin.get('validation')
                if not isinstance(validation,dict) or not re.fullmatch('[a-f0-9]{64}',str(validation.get('candidate_sha256',''))):raise ValueError('Invalid frozen validation identity')
                if type(validation.get('holdout_attempt')) is not int or validation['holdout_attempt']<1:raise ValueError('Invalid holdout attempt')
                ranges=validation.get('selection_range')
                if not isinstance(ranges,list) or len(ranges)!=2 or any(type(v) is not int for v in ranges) or not ranges[0]<ranges[1]<=research['window']['start']:raise ValueError('Overlapping archived validation range')
            elif origin.get('validation') is not None:raise ValueError('Selection cannot contain holdout metrics')
            identifier(origin['batch_id'])
            if not re.fullmatch('[a-f0-9]{64}',origin['batch_sha256']):raise ValueError('Invalid library batch checksum')
            document={'graph':snapshot['strategy'],'layout':{}} if not snapshot['strategy'].get('engine') else snapshot['strategy']
            if origin['contract'].get('document_sha256')!=digest(document):raise ValueError('Library document checksum mismatch')
        window=research['window']
        if not isinstance(window,dict) or set(window)!={'start','end','warmup_start'}:raise ValueError('Invalid research window')
        validate_range([window['start'],window['end']],snapshot['dataset']['range'],'Archived trading window')
        if type(window['warmup_start']) is not int or window['warmup_start']%60 or not snapshot['dataset']['range'][0]<=window['warmup_start']<=window['start']:raise ValueError('Invalid archived warmup')
    strategy=snapshot['strategy']
    if strategy.get('engine')=='nautilus_trader':validate_native(strategy)
    elif not passive:validate_graph(strategy)
    data=snapshot['dataset']
    if not re.fullmatch('[a-f0-9]{64}',data['id']) or not isinstance(data['range'],list) or len(data['range'])!=2 or any(type(v) is not int for v in data['range']) or data['range'][1]<=data['range'][0]:
        raise ValueError('Invalid archived dataset description')


def read_archive(raw):
    if len(raw)>MAX_ARCHIVE:raise ValueError('Archive exceeds 64 MiB')
    documents={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files=archive.infolist()
        if not 1<=len(files)<=MAX_FILES:raise ValueError('Archive file count exceeds budget')
        total=0;seen=set()
        for info in files:
            name=info.filename;path=PurePosixPath(name)
            if name!=info.orig_filename or name in seen or name.casefold() in seen or '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or name!=str(path) or info.is_dir():
                raise ValueError('Unsafe or duplicate archive path')
            seen.add(name.casefold())
            if name!='project.json' and not re.fullmatch(r'runs/[a-f0-9]{32}/(?:snapshot|result)\.json',name):raise ValueError('Unexpected archive content')
            if stat.S_ISLNK(info.external_attr>>16) or info.flag_bits&1 or info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise ValueError('Unsupported archive entry type')
            total+=info.file_size
            if total>MAX_EXPANDED or info.file_size>64*1024*1024 or info.file_size>max(1024*1024,info.compress_size*200):raise ValueError('Expanded archive exceeds resource budget')
            content=archive.read(info)
            if len(content)!=info.file_size:raise ValueError('Archive size mismatch')
            documents[name]=json.loads(content,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
    project=documents.get('project.json')
    if not isinstance(project,dict) or set(project)!={'schema_version','strategy','profile','runs','files','history_included'} or project['schema_version']!=1 or project['history_included'] is not False:
        raise ValueError('Unsupported project archive schema')
    validate_strategy(project['strategy']);Profile(**project['profile'])
    run_ids=project['runs']
    if not isinstance(run_ids,list) or len(run_ids)>8 or len(set(run_ids))!=len(run_ids):raise ValueError('Invalid archived run list')
    expected={'project.json'}
    for run_id in run_ids:
        identifier(run_id);expected.update({f'runs/{run_id}/snapshot.json',f'runs/{run_id}/result.json'})
    if set(documents)!=expected or set(project['files'])!=expected-{'project.json'}:raise ValueError('Archive manifest does not match its entries')
    for name,expected_hash in project['files'].items():
        if digest(documents[name])!=expected_hash:raise ValueError('Archive content checksum mismatch')
    for run_id in run_ids:
        snapshot=documents[f'runs/{run_id}/snapshot.json'];validate_snapshot(snapshot)
        result=documents[f'runs/{run_id}/result.json']
        if result.get('schema_version')!=1 or result.get('status')!='completed' or result.get('manifest_sha256')!=snapshot['snapshot_sha256'] or result.get('profile')!=snapshot['profile'] or any(not isinstance(result.get(k),list) for k in SERIES):raise ValueError('Invalid archived normalized result')
        if result['candles'] or 'metrics' not in result or result.get('history_omitted') is not True:raise ValueError('Historical candles must be omitted from this archive format')
        if not all(k in result for k in ('engine','engine_version','metric_version')):raise ValueError('Missing archived result versions')
        metrics=result['metrics']
        if not isinstance(metrics,dict) or set(metrics)!={'final_equity','net_pnl','max_drawdown','trade_count','win_rate','fees','funding'}:raise ValueError('Invalid archived metrics')
        for key in ('final_equity','net_pnl','max_drawdown','fees','funding'):dec(metrics[key])
        if type(metrics['trade_count']) is not int or metrics['trade_count']!=len(result['trades']) or metrics['trade_count']<0:raise ValueError('Invalid archived trade count')
        if metrics['win_rate'] is not None and not 0<=dec(metrics['win_rate'])<=1:raise ValueError('Invalid archived win rate')
        if type(result['metric_version']) is not int or result['metric_version']!=1:raise ValueError('Unsupported archived metric definition')
        if result['engine']!='nautilus_trader' or not isinstance(result['engine_version'],str):raise ValueError('Invalid archived engine identity')
        for trade in result['trades']:
            for side in ('entry','exit'):
                fill=trade[side]
                if fill['side'] not in ('buy','sell') or type(fill['time_ns']) is not int or not isinstance(fill['reason'],str):raise ValueError('Invalid archived fill')
                for key in ('price','quantity','fee'):dec(fill[key])
            for key in ('gross_pnl','fees','funding','net_pnl'):dec(trade[key])
        for point in result['indicators']:
            if type(point['time']) is not int or not isinstance(point['values'],dict):raise ValueError('Invalid archived indicator point')
            for value in point['values'].values():
                if value is not None and (not isinstance(value,(int,float,bool)) or not math.isfinite(value)):raise ValueError('Invalid archived indicator value')
        for point in result['equity']:
            if type(point['time_ns']) is not int:raise ValueError('Invalid archived equity time')
            dec(point['equity'])
        for series,time_key,strict in (('indicators','time',True),('equity','time_ns',True),('fills','time_ns',False)):
            times=[p[time_key] for p in result[series]]
            if any(type(t) is not int or t<0 for t in times) or any(b<=a if strict else b<a for a,b in zip(times,times[1:])):raise ValueError('Invalid archived series ordering')
        for fill in result['fills']:
            if fill['side'] not in ('buy','sell') or not isinstance(fill['reason'],str):raise ValueError('Invalid archived marker')
            for key in ('price','quantity','fee'):dec(fill[key])
    return project,documents


class ArchiveManager:
    def __init__(self,store,jobs=None):
        from terminal.archive_receipts import ArchiveReceipts
        self.store=store;self.jobs=jobs;self.upload=None;self.blocked=False
        self.receipts=ArchiveReceipts(store)

    def _ready(self):
        if self.jobs is not None:self.jobs.require_storage_ready()
        if self.blocked:raise ValueError('Archive imports blocked by storage finalization failure. Inspect saved imports and restart; no automatic retry.')

    def _storage_failure(self,operation_id):
        self.blocked=True
        if self.jobs is not None:self.jobs.latch_storage_failure(operation_id,'archive_import')
        try:self.receipts.stop(operation_id,'storage_failure')
        except Exception:pass  # Earlier durable phase/IDs remain authoritative.

    @staticmethod
    def _failure_note(operation_id):
        return (f'Archive import outcome requires inspection. Operation {operation_id}. '
                'Completed and incomplete records may remain; no rollback was performed. '
                'Inspect this import or Recent imports. Inspection may require waiting for synchronous finalization or restarting the service. '
                'Do not retry blindly: a new import creates new IDs. This transfer cannot be resumed. '
                'If inspection is unavailable, its persisted outcome is unknown; this error is not a durable receipt.')

    def status(self,operation_id):
        identifier(operation_id)
        try:return self.receipts.status(operation_id)
        except Exception:raise ValueError(f'Import inspection unavailable for operation {operation_id}; outcome unknown. No changes were requested.') from None

    def recent(self,before=None,limit=25):
        try:return self.receipts.list(before,limit)
        except Exception:raise ValueError('Recent import inspection unavailable; saved outcomes are unknown. No changes were requested.') from None

    def export(self,strategy,profile,run_ids):
        validate_strategy(strategy);Profile(**profile)
        if not isinstance(run_ids,list) or len(run_ids)>8 or len(set(run_ids))!=len(run_ids):raise ValueError('Choose up to eight different saved runs')
        documents={}
        for run_id in run_ids:
            snapshot=self.store.get(run_id)['manifest'];result=self.store.result(run_id)
            documents[f'runs/{run_id}/snapshot.json']=snapshot
            # Raw historical OHLCV and worker logs are deliberately not copied.
            result={**result,'candles':[],'history_omitted':True}
            documents[f'runs/{run_id}/result.json']=result
        project={'schema_version':1,'strategy':strategy,'profile':profile,'runs':run_ids,
                 'files':{name:digest(value) for name,value in documents.items()},'history_included':False}
        documents['project.json']=project
        if sum(len(canonical(value)) for value in documents.values())>MAX_EXPANDED:raise ValueError('Selected results exceed archive budget; export fewer runs')
        for name,value in documents.items():privacy_check(value,name)
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,value in documents.items():archive.writestr(name,canonical(value))
        raw=output.getvalue();read_archive(raw)
        export_id=uuid.uuid4().hex
        file=self.store.root/'exports'/f'{export_id}.ttproject.zip'
        write_new(file,raw)
        return {'export_id':export_id,'filename':file.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                'history_included':False,'note':'Saved in the local exports folder. Dataset descriptions do not guarantee a rerun; worker logs, consent records and raw candles are excluded.'}

    def begin(self,size):
        self._ready()
        if type(size) is not int or not 1<=size<=MAX_ARCHIVE:raise ValueError('Expected an archive of at most 64 MiB')
        if self.upload:raise ValueError('An archive transfer is already active; cancel it first')
        operation_id=uuid.uuid4().hex;file=self.store.root/'imports'/f'{operation_id}.partial'
        try:
            self.receipts.begin(operation_id,size)
            file.parent.mkdir(exist_ok=True);file.touch(exist_ok=False)
        except sqlite3.IntegrityError:
            raise ValueError('Import operation identifier collision; no transfer was started.') from None
        except Exception:
            self._storage_failure(operation_id)
            raise ValueError(self._failure_note(operation_id)) from None
        self.upload={'id':operation_id,'size':size,'offset':0,'file':file}
        return {'operation_id':operation_id,'upload_id':operation_id,'chunk_bytes':CHUNK}

    def append(self,upload_id,offset,data):
        upload=self.upload
        if not upload or upload_id!=upload['id'] or type(offset) is not int or offset!=upload['offset']:raise ValueError('Invalid transfer identifier or offset')
        if not isinstance(data,str) or len(data)>4*((CHUNK+2)//3):raise ValueError('Upload chunk exceeds budget')
        raw=base64.b64decode(data,validate=True)
        if not raw or len(raw)>CHUNK or offset+len(raw)>upload['size']:raise ValueError('Invalid upload size')
        try:
            with upload['file'].open('ab') as stream:stream.write(raw)
        except OSError:
            self._storage_failure(upload_id);self.upload=None
            raise ValueError(self._failure_note(upload_id)) from None
        upload['offset']+=len(raw)
        return {'offset':upload['offset']}

    def cancel(self,operation_id=None):
        # Legacy cancellation is restricted to the current receiving transfer.
        ident=operation_id if operation_id is not None else (self.upload['id'] if self.upload else None)
        if ident is None:return {'status':'no_active_transfer'}
        try:result=self.receipts.cancel(ident)
        except Exception:raise ValueError(f'Cancellation outcome unavailable for operation {identifier(ident)}; inspect before another action.') from None
        if result['status']=='cancelled' and self.upload and self.upload['id']==ident:self.upload=None
        return result  # Retained upload bytes are never parsed or resumed at startup.

    def finish(self,upload_id):
        identifier(upload_id)
        self._ready()
        upload=self.upload
        if not upload or upload_id!=upload['id']:
            raise ValueError(f'Import cannot be finished again. Inspect operation {upload_id}; no retry or resume is supported.')
        if upload['offset']!=upload['size']:raise ValueError('Archive transfer is incomplete')
        try:self.receipts.claim(upload_id)
        except ValueError:
            raise ValueError(f'Import finish was already claimed. Inspect operation {upload_id}; no changes were requested.') from None
        except Exception:
            self._storage_failure(upload_id);self.upload=None
            raise ValueError(self._failure_note(upload_id)) from None
        try:
            try:
                raw=upload['file'].read_bytes()
            except Exception:
                self._storage_failure(upload_id)
                raise ValueError(self._failure_note(upload_id)) from None
            try:project,documents=read_archive(raw)
            except Exception:
                try:self.receipts.stop(upload_id,'validation_rejected',rejected=True)
                except Exception:self._storage_failure(upload_id)
                raise ValueError(f'Archive validation rejected for operation {upload_id}. No output identities were reserved. Inspect this import for its persisted outcome.') from None
            try:
                self.receipts.reserve(upload_id,raw,project,documents)
                for ordinal,source in enumerate(project['runs']):
                    self.receipts.publish_run(upload_id,ordinal,documents[f'runs/{source}/snapshot.json'],documents[f'runs/{source}/result.json'])
                self.receipts.publish_strategy(upload_id,project['strategy'],project['profile'])
                receipt=self.receipts.status(upload_id)
            except Exception:
                self._storage_failure(upload_id)
                raise ValueError(self._failure_note(upload_id)) from None
            # Advisory lookup cannot change a committed publication outcome.
            found=0;availability='checked'
            for source in project['runs']:
                dataset=documents[f'runs/{source}/snapshot.json']['dataset']
                try:
                    actual=DatasetStore(self.store.root/'datasets').describe(dataset['id'])
                    if actual['content_sha256']==dataset['content_sha256']:found+=1
                except (FileNotFoundError,ValueError):pass
                except Exception:found=None;availability='unchecked';break
            return {'operation_id':upload_id,'receipt':receipt,
                    'strategy_id':next(item['destination_id'] for item in receipt['items'] if item['kind']=='strategy'),
                    'profile':project['profile'],'run_ids':[item['destination_id'] for item in receipt['items'] if item['kind']=='run'],
                    'history_included':False,'datasets_found':found,'dataset_availability':availability,
                    'note':'Import completed. Saved reports are not locally verified calculations. Artifact files have not been verified by this inspection. Python was not executed and no new trust was granted. Rerunning requires matching checked data, dependencies and separate source consent.'}
        finally:
            if self.upload is upload:self.upload=None
