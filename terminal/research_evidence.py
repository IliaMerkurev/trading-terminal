"""Forward-only research admissions, separate from immutable financial artifacts."""
from datetime import datetime, timezone
import json

from terminal.data import canonical, digest

LIMITATION = ('Records begin at coverage start; legacy/imported attempts, untracked views, replay/live activity and outside-app exposure are unrecorded. Displayed evidence means rendered in this app, not proof of reading; chart gaps are excluded, metrics expose the full evaluation range. '
              'No recorded overlap does not establish an unseen or independent holdout. Started means durable admission, not completed computation. '
              'Same-symbol spot/linear calendar exposure is not a comparable performance cohort. Evaluation overlap excludes warmup-only input. Synthetic evidence is isolated by declared source; unknown provenance remains uncertain.')


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS research_evidence(
            event_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, kind TEXT NOT NULL,
            route TEXT NOT NULL, owner_id TEXT NOT NULL, run_id TEXT, role TEXT NOT NULL,
            symbol TEXT, market TEXT, source TEXT, provenance TEXT, namespace TEXT,
            evaluation_start INTEGER, evaluation_end INTEGER, details TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS evidence_overlap ON research_evidence(symbol,evaluation_start,evaluation_end);
        CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON research_evidence
            BEGIN SELECT RAISE(ABORT,'Research evidence is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON research_evidence
            BEGIN SELECT RAISE(ABORT,'Research evidence is append-only'); END;
    ''')
    db.execute("INSERT OR IGNORE INTO research_evidence(event_id,recorded_at,kind,route,owner_id,role,details) VALUES('coverage-start',?,'coverage','system','local','coverage','{}')",(datetime.now(timezone.utc).isoformat(),))

    db.execute("INSERT OR IGNORE INTO research_evidence(event_id,recorded_at,kind,route,owner_id,role,details) VALUES('view-coverage-start',?,'coverage','system','local','view-coverage','{}')",(datetime.now(timezone.utc).isoformat(),))


def provenance(dataset):
    source=dataset.get('source') or 'Unknown source'
    metadata=dataset.get('metadata',{})
    declared=canonical({'source':source,'provenance':dataset.get('provenance',[])}).decode().lower()
    if metadata.get('synthetic') is True or 'synthetic' in declared:
        return source,'synthetic','synthetic:'+source
    records=dataset.get('provenance',[])
    # A source label alone (also used by old synthetic fixtures) is insufficient.
    if source=='Bybit public API' and any(isinstance(r,dict) and r.get('endpoint')=='/v5/market/kline' and r.get('response_sha256') and r.get('retrieved_at') for r in records):
        return source,'real','real'
    return source,'unknown','unknown'


def event(dataset,profile,start,end,*,route,owner_id,role='strategy',identity=None,input_start=None):
    source,classification,namespace=provenance(dataset)
    return dict(route=route,owner_id=owner_id,role=role,symbol=profile['symbol'],market=profile['market'],source=source,
        provenance=classification,namespace=namespace,evaluation_start=start,evaluation_end=end,
        details=dict(dataset_id=dataset['id'],dataset_sha256=dataset['content_sha256'],input_range=[dataset['range'][0] if input_start is None else input_start,end],
                     evaluation_range=[start,end],identity=identity,cohort=digest(profile),profile=profile,
                     provenance_sha256=digest(dataset.get('provenance',[]))))


def admission(snapshot,dataset,owner=None):
    research=snapshot.get('research',{});strategy=snapshot['strategy'];profile=snapshot['profile']
    window=research.get('window',{});benchmark='benchmark' in strategy
    start=window.get('start',strategy.get('start',dataset['range'][0]) if benchmark else dataset['range'][0])
    end=window.get('end',strategy.get('end',dataset['range'][1]) if benchmark else dataset['range'][1])
    library=research.get('library');experiment=research.get('experiment')
    route='library' if library else 'experiment' if experiment else 'library' if benchmark and owner else 'custom'
    parent=(library or {}).get('batch_id') or (experiment or {}).get('validation_id') or (experiment or {}).get('id') or owner
    value=event(dataset,profile,start,end,route=route,owner_id=parent,role='passive' if benchmark else 'strategy',
        input_start=window.get('warmup_start',dataset['range'][0]),identity=dict(strategy_sha256=digest(strategy),snapshot_sha256=snapshot['snapshot_sha256'],
        library=library,experiment=experiment,benchmark_contract=research.get('benchmark_contract')))
    return value


def append(db,event_id,kind,value,run_id=None):
    # Event IDs identify physical admission/freeze, never deduplicate by strategy hash.
    details=dict(value['details'])
    if kind=='frozen':
        details['prior_overlap']=overlaps(db,{'symbol':value['symbol'],'range':details['evaluation_range']},
            *details['evaluation_range'],classification=(value['source'],value['provenance'],value['namespace']))
    value={**value,'owner_id':value['owner_id'] or run_id,'details':canonical(details).decode()}
    db.execute('INSERT INTO research_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (event_id,datetime.now(timezone.utc).isoformat(),kind,value['route'],value['owner_id'],run_id,value['role'],value['symbol'],value['market'],value['source'],value['provenance'],value['namespace'],value['evaluation_start'],value['evaluation_end'],value['details']))


def overlaps(db,dataset,start,end,classification=None):
    from terminal.experiments import validate_range
    validate_range([start,end],dataset['range'],'Evidence evaluation range')
    source,classification,namespace=classification or provenance(dataset)
    # Unknown and real observations share conservative calendar warnings. Explicit
    # synthetic sources only compare within their declared fixture namespace.
    scope="namespace=?" if classification=='synthetic' else "provenance IN ('real','unknown')"
    params=[dataset['symbol'],end,start]+([namespace] if classification=='synthetic' else [])
    where=f"kind IN ('started','frozen','viewed') AND symbol=? AND evaluation_start<? AND evaluation_end>? AND {scope}"
    groups=[dict(r) for r in db.execute(f'''SELECT route,kind,role,source,provenance,market,
        json_extract(details,'$.cohort') AS cohort,
        json_extract(details,'$.original_role') AS original_role,
        json_extract(details,'$.profile.primary_minutes') AS primary_minutes,
        coalesce(json_extract(details,'$.profile.execution_minutes'),1) AS execution_minutes,
        json_extract(details,'$.profile.version') AS model_version,count(*) AS count,
        min(evaluation_start) AS first_start,max(evaluation_end) AS last_end
        FROM research_evidence WHERE {where} GROUP BY route,kind,role,source,provenance,market,cohort,original_role
        ORDER BY route,kind,role,source,provenance,market,cohort LIMIT 51''',params)]
    total=db.execute(f'SELECT count(*) FROM research_evidence WHERE {where}',params).fetchone()[0]
    counts={r['kind']:r['n'] for r in db.execute(f'SELECT kind,count(*) AS n FROM research_evidence WHERE {where} GROUP BY kind',params)}
    view_coverage=db.execute("SELECT recorded_at FROM research_evidence WHERE event_id='view-coverage-start'").fetchone()[0]
    coverage=db.execute("SELECT recorded_at FROM research_evidence WHERE event_id='coverage-start'").fetchone()[0]
    display_warning=db.execute("SELECT recorded_at FROM research_evidence WHERE role='display-incomplete' ORDER BY recorded_at DESC LIMIT 1").fetchone()
    warning='Display tracking incomplete: a displayed surface could not be fully recorded; overlap history may omit exposure.' if display_warning else None
    return dict(display_warning=warning,coverage_start=coverage,view_coverage_start=view_coverage,counts=counts,source=source,provenance=classification,range=[start,end],symbol=dataset['symbol'],
        total=total,groups=groups[:50],groups_truncated=len(groups)>50,limitation=LIMITATION,
        message=f"{total} recorded events overlap this evaluation period: {counts.get('started',0)} admissions, {counts.get('frozen',0)} freezes, {counts.get('viewed',0)} displayed ranges. Displayed ranges are not test attempts.")


def preview(jobs,dataset_id,start,end):
    from terminal.displayed_evidence import persist_warning
    persist_warning(jobs.store)
    dataset=jobs.datasets.describe(dataset_id)
    with jobs.store.connect() as db:return overlaps(db,dataset,start,end)


def frozen_review(db,route,ident):
    row=db.execute('SELECT details FROM research_evidence WHERE event_id=?',('frozen:'+route+':'+ident,)).fetchone()
    return json.loads(row['details']).get('prior_overlap') if row else None
