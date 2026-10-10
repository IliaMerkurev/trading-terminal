"""Bounded presentation evidence. Displayed in this app does not mean read."""
import json
import math
import sqlite3

from terminal.data import digest
from terminal import research_evidence as evidence
from terminal.storage import identifier

INCOMPLETE = 'Display tracking incomplete: imported/legacy reports without local admission evidence are not recorded. Reading remains available.'


def candle_ranges(candles, seconds, viewport, *, closes=False):
    if (not isinstance(viewport,list) or len(viewport)!=2 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in viewport) or viewport[0]>viewport[1]):
        raise ValueError('Invalid displayed chart viewport')
    # Visible time labels are inclusive; persisted intervals are half-open opens.
    times=sorted({c['time'] for c in candles if viewport[0]<=c['time']+(seconds if closes else 0)<=viewport[1]})
    ranges=[]
    for start in times:
        if ranges and ranges[-1][1]==start:ranges[-1][1]=start+seconds
        else:ranges.append([start,start+seconds])
    return ranges


def _run(store, run_id):
    run=store.get(run_id)
    if run['status']!='completed' or not run['summary'] or run['summary'].get('origin')!='local':return None
    with store.connect() as db:
        row=db.execute("SELECT * FROM research_evidence WHERE event_id=? AND kind='started'",('started:'+run_id,)).fetchone()
    if not row:return None
    value=dict(row);value['details']=json.loads(value['details'])
    # The immutable admission is the authoritative provenance, including unknowns.
    if value['details'].get('identity',{}).get('snapshot_sha256')!=run['manifest'].get('snapshot_sha256'):
        raise ValueError('Local report admission identity mismatch')
    return value


def chart_page(service, surface, page, owner_id):
    """Issue a bounded reference to exactly the candles returned for presentation.

    Fetching only populates this memory cache; it appends no display evidence.
    Eviction/restart fails visibly rather than substituting another data source.
    """
    from collections import OrderedDict
    from copy import deepcopy
    if surface=='observation_chart':
        dataset=service.datasets.describe(owner_id)
        from terminal.observations import source_identity
        if source_identity(dataset)!=page['source']:raise ValueError('Displayed source identity changed')
        source,classification,namespace=evidence.provenance(dataset)
        value=dict(route='observations',owner_id=dataset['id'],role=surface,symbol=dataset['symbol'],market=dataset['market'],
                   source=source,provenance=classification,namespace=namespace,
                   details=dict(dataset_id=dataset['id'],dataset_sha256=dataset['content_sha256'],
                                provenance_sha256=digest(dataset.get('provenance',[]))))
        candles=page['candles'];seconds=dataset.get('interval_seconds',60)
    else:
        value=_run(service.store,owner_id);candles=page['series']['candles'];seconds=page['interval_seconds']
    reference=dict(surface=surface,owner_id=owner_id,start=page['start'],end=page['end'])
    cached=dict(value=value,candles=[{'time':c['time']} for c in candles],seconds=seconds,reference=reference)
    page_id=digest(cached)
    if not hasattr(service,'display_pages'):service.display_pages=OrderedDict()
    service.display_pages[page_id]=deepcopy(cached);service.display_pages.move_to_end(page_id)
    while len(service.display_pages)>32:service.display_pages.popitem(last=False)
    return {**page,'display_reference':dict(surface=surface,page_id=page_id)}


def _record(service, presentation_id, reference, viewport):
    identifier(presentation_id)
    if not isinstance(reference,dict):raise ValueError('Invalid displayed presentation reference')
    surface=reference.get('surface');value=None;run_id=None
    if surface in ('observation_chart','run_chart'):
        if set(reference)!={'surface','page_id'} or not isinstance(reference['page_id'],str) or len(reference['page_id'])!=64:
            raise ValueError('Invalid chart presentation reference')
        page=getattr(service,'display_pages',{}).get(reference['page_id'])
        if not page or page['reference']['surface']!=surface:raise ValueError('Displayed chart reference expired; reopen the chart to resume tracking')
        from copy import deepcopy
        value=deepcopy(page['value'])
        if value is None:return dict(recorded=0,incomplete=True,warning=INCOMPLETE)
        reference=page['reference']
        ranges=candle_ranges(page['candles'],page['seconds'],viewport,closes=surface=='run_chart')
        if surface=='run_chart':run_id=reference['owner_id']
    elif surface in ('run_metrics','comparison_metrics'):
        expected={'surface','run_id'} if surface=='run_metrics' else {'surface','batch_id','ordinal'}
        if set(reference)!=expected:raise ValueError('Invalid report presentation reference')
        if surface=='comparison_metrics':
            if type(reference['ordinal']) is not int or not 0<=reference['ordinal']<98:raise ValueError('Invalid comparison row')
            batch=service.library_batches.get(reference['batch_id'])
            row=next((r for r in batch['rows'] if r['ordinal']==reference['ordinal']),None)
            if not row or row['status']!='completed' or not row['metrics']:raise ValueError('No completed comparison metrics')
            run_id=row['run_id']
        else:run_id=reference['run_id']
        value=_run(service.store,run_id)
        if value is None:return dict(recorded=0,incomplete=True,warning=INCOMPLETE)
        if viewport is not None:raise ValueError('Metrics expose their full evaluation period')
        ranges=[[value['evaluation_start'],value['evaluation_end']]]
        if surface=='comparison_metrics' and ranges[0]!=[batch['snapshot']['start'],batch['snapshot']['end']]:
            raise ValueError('Comparison and local report evaluation range mismatch')
    if value is None:raise ValueError('Unsupported display surface')
    if surface!='observation_chart':
        details=value['details']
        value={**value,'route':'library' if surface=='comparison_metrics' else 'report','owner_id':reference.get('batch_id',run_id),
               'role':surface,'details':{**{k:details[k] for k in ('dataset_id','dataset_sha256','identity','provenance_sha256') if k in details},'original_role':value['role'],'cohort':details.get('cohort'),'profile':details.get('profile')}}
    recorded=0
    with service.store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for start,end in ranges:
            details={**value['details'],'presentation_id':presentation_id,'surface':surface,'reference':reference,
                     'displayed_range':[start,end],'meaning':'Displayed in this app; not proof of reading'}
            event_id='viewed:'+digest([presentation_id,reference,value['source'],value['provenance'],details.get('dataset_sha256'),details.get('provenance_sha256'),start,end])
            if db.execute('SELECT 1 FROM research_evidence WHERE event_id=?',(event_id,)).fetchone():continue
            evidence.append(db,event_id,'viewed',{**value,'evaluation_start':start,'evaluation_end':end,'details':details},run_id)
            recorded+=1
    return dict(recorded=recorded,incomplete=False,warning=None)


def persist_warning(store):
    """Best effort during reading; subsequent review must retain the caveat."""
    warning=getattr(store,'display_warning',None)
    if warning:
        with store.connect() as db:
            db.execute("INSERT OR IGNORE INTO research_evidence(event_id,recorded_at,kind,route,owner_id,role,details) VALUES(?,?,'coverage','system','local','display-incomplete',?)",warning)
        store.display_warning=None
        store.display_warning_saved=True


def mark_incomplete(store):
    from datetime import datetime,timezone
    import uuid
    if getattr(store,'display_warning_saved',False):return
    if not getattr(store,'display_warning',None):
        store.display_warning=('display-warning:'+uuid.uuid4().hex,datetime.now(timezone.utc).isoformat(),
                               '{"warning":"A displayed surface could not be fully recorded; overlap history may omit exposure."}')
    try:persist_warning(store)
    except (OSError, sqlite3.Error):pass


def record(service, presentation_id, reference, viewport):
    try:
        result=_record(service,presentation_id,reference,viewport)
    except Exception:
        mark_incomplete(service.store)
        raise
    if result['incomplete']:mark_incomplete(service.store)
    else:persist_warning(service.store)
    return result
