"""Conservative, bounded views of immutable saved-run evidence only."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from terminal.data import canonical, digest


def mapping(value):
    return value if isinstance(value, dict) else {}


def at(value, *path):
    for key in path:
        value = mapping(value).get(key)
    return value


def text(value):
    return value if isinstance(value, str) and value.strip() else None


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)) or len(str(value)) > 256:
        return None
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            return None
        sign, digits, exponent = result.as_tuple()
        if abs(exponent) > 1000 or len(digits) > 256:
            return None
        if not any(digits):
            return '0'
        digits = list(digits)
        while digits[-1] == 0:
            digits.pop(); exponent += 1
        exact = ('-' if sign else '') + ''.join(map(str, digits)) + 'e' + str(exponent)
        return format(Decimal(exact), 'f') if abs(exponent) <= 32 and len(digits) <= 64 else exact
    except InvalidOperation:
        return None


def amount(value, *, rate=False):
    normalized = number(value)
    if normalized is None:
        return None
    n = Decimal(normalized)
    return normalized if (0 <= n < 1 if rate else n > 0) else None


def choice(value, choices):
    return value if type(value) in (str, int) and value in choices else None


def integer(value):
    return value if type(value) is int and value >= 0 else None


def fingerprint(value):
    return value if isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) else None


def period(value):
    if (isinstance(value, list) and len(value) == 2 and all(integer(v) is not None for v in value)
            and value[0] < value[1] and all(utc(v) for v in value)):
        return value
    return None


def bounded(value):
    if value is None:
        return None
    raw = canonical(value)
    if len(raw) <= 900:
        return value
    return {'display': 'Large recorded value; see the original run snapshot', 'metadata_sha256': digest(value)}


def coverage(value, requested=None):
    value = mapping(value)
    required = ('requested_start', 'requested_end', 'actual_start', 'actual_end', 'count', 'expected_count', 'gaps', 'complete')
    if (any(k not in value for k in required) or not isinstance(value['gaps'], list)
            or type(value['complete']) is not bool
            or any(integer(value[k]) is None for k in required[:6])
            or period([value['actual_start'], value['actual_end']]) is None
            or period([value['requested_start'], value['requested_end']]) is None
            or value['count'] <= 0 or value['expected_count'] < value['count']
            or not value['requested_start'] <= value['actual_start'] < value['actual_end'] <= value['requested_end']
            or any(period(g) is None for g in value['gaps'])
            or value['complete'] != (not value['gaps'])):
        return None
    start,end=value['requested_start'],value['requested_end']
    expected=value['expected_count']
    if requested != [start,end] or not expected or (end-start)%expected:
        return None
    step=(end-start)//expected;gaps=value['gaps']
    if (step not in (60,300,900,3600,14400,86400) or any(t%step for t in (start,end,value['actual_start'],value['actual_end']))
            or any(not start <= a < b <= end or a%step or b%step for a,b in gaps)
            or any(a[1] >= b[0] for a,b in zip(gaps,gaps[1:]))
            or any(a <= value['actual_start'] < b or a < value['actual_end'] <= b for a,b in gaps)
            or sum((b-a)//step for a,b in gaps) != expected-value['count']
            or (value['actual_start']>start and (not gaps or gaps[0] != [start,value['actual_start']]))
            or (value['actual_end']<end and (not gaps or gaps[-1] != [value['actual_end'],end]))):
        return None
    return {k: value[k] for k in required}


def funding_coverage(value, requested=None):
    v=mapping(value)
    required=('count','expected_using_current_interval','missing_expected','complete_against_current_interval','assumption')
    if (any(k not in v for k in required) or integer(v['count']) is None or integer(v['expected_using_current_interval']) is None
            or not isinstance(v['missing_expected'],list) or any(integer(t) is None for t in v['missing_expected'])
            or type(v['complete_against_current_interval']) is not bool or not text(v['assumption'])
            or v['complete_against_current_interval'] and bool(v['missing_expected'])
            or period(requested) is None
            or any(not requested[0] <= t < requested[1] for t in v['missing_expected'])
            or any(a >= b for a,b in zip(v['missing_expected'],v['missing_expected'][1:]))
            or len(v['missing_expected']) > v['expected_using_current_interval']
            or v['count'] < v['expected_using_current_interval']-len(v['missing_expected'])):
        return None
    return {k:v[k] for k in required}


def utc(seconds):
    try:
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace('+00:00', 'Z')
    except (ValueError, OverflowError, OSError):
        return None


def graph_trace(store, run):
    """Two indexed endpoint reads; never read full candles, trades or artifacts."""
    strategy = mapping(at(run, 'manifest', 'strategy'))
    if 'nodes' not in strategy or not isinstance(strategy['nodes'], list):
        return None
    with store.connect() as db:
        endpoints = [db.execute(
            "SELECT json_extract(value,'$.time') AS time,json_type(value,'$.time') AS time_type FROM series WHERE run_id=? AND kind='indicators' "
            f"ORDER BY row_index {order} LIMIT 1", (run['id'],)).fetchone() for order in ('ASC', 'DESC')]
    if any(row is None or row['time_type'] != 'integer' or integer(row['time']) is None for row in endpoints):
        return None
    first, last = [row['time'] for row in endpoints]
    if first > last or not utc(first) or not utc(last):
        return None
    return {'first_close_utc': utc(first), 'last_close_utc': utc(last)}


def environment(value):
    v=mapping(value)
    if not all(text(v.get(k)) for k in ('python','platform','machine')) or not isinstance(v.get('packages'),dict) or not v['packages'] or not all(text(k) and text(n) for k,n in v['packages'].items()):
        return None
    return {k:v[k] for k in ('python','platform','machine','packages')}


def review(store, runs):
    records = []
    for run in runs:
        manifest = mapping(run.get('manifest')); profile = mapping(manifest.get('profile'))
        dataset = mapping(manifest.get('dataset')); window = mapping(at(manifest, 'research', 'window'))
        strategy = mapping(manifest.get('strategy')); summary = mapping(run.get('summary'))
        declared = period([window.get('start'), window.get('end')])
        if strategy.get('benchmark') == 'passive':
            declared = period([strategy.get('start'), strategy.get('end')])
        input_range = period(dataset.get('range'))
        if declared and (input_range is None or not input_range[0] <= declared[0] < declared[1] <= input_range[1]):
            declared = None
        warmup = [window.get('warmup_start'), window.get('start')]
        warmup = warmup if declared and input_range and all(integer(v) is not None and utc(v) for v in warmup) and input_range[0] <= warmup[0] <= warmup[1] == declared[0] else None
        records.append(dict(manifest=manifest, profile=profile, dataset=dataset, summary=summary,
                            declared=declared, warmup=warmup, trace=graph_trace(store, run)))
    rows = []

    def add(key, group, label, getter, note, missing='Not recorded or unsupported in this saved result.'):
        values = [getter(r) for r in records]
        known = [v for v in values if v is not None]
        # Known conflicts take precedence; missing evidence remains explicit per cell.
        status = 'different' if len({canonical(v) for v in known}) > 1 else 'unknown' if len(known) < len(values) else 'matched'
        rows.append(dict(key=key, group=group, label=label, status=status, note=note,
                         values=[dict(value=bounded(v), known=v is not None, reason=None if v is not None else missing) for v in values]))

    add('source', 'Data', 'Recorded data source', lambda r: text(r['dataset'].get('source')),
        'A source label is provenance metadata, not independent provider authentication. Synthetic sources remain synthetic.')
    add('content', 'Data', 'Dataset content fingerprint', lambda r: fingerprint(r['dataset'].get('content_sha256')),
        'Saved SHA-256 covers normalized trade, mark and funding inputs, including warmup and unused suffix. A match does not authenticate the provider or verify files currently on disk.')
    add('range', 'Data', 'Requested input range', lambda r: period(r['dataset'].get('range')),
        'UTC Unix seconds; start inclusive, end exclusive. This is the dataset request, not the trading period.')
    add('coverage', 'Data', 'Actual saved trade-data coverage', lambda r: coverage(at(r['dataset'], 'coverage', 'trade'),period(r['dataset'].get('range'))),
        'Recorded actual source-bar bounds, counts and gaps. Equal coverage alone does not establish equal candles.')
    add('mark_coverage', 'Data', 'Saved mark-data coverage', lambda r:coverage(at(r['dataset'],'coverage','mark'),period(r['dataset'].get('range'))),
        'Separate mark-price input coverage. Spot or absent mark history has no recorded mark coverage; it is not evidence of a matching perpetual mark model.')
    add('funding_coverage', 'Data', 'Saved funding coverage assumption', lambda r:funding_coverage(at(r['dataset'],'coverage','funding'),period(r['dataset'].get('range'))),
        'Completeness is only against the saved current interval projected historically, not verified historical funding schedules.')
    add('market', 'Data', 'Market and instrument', lambda r: {k:r['profile'][k] for k in ('market','symbol')} if choice(r['profile'].get('market'),('spot','linear')) and isinstance(r['profile'].get('symbol'),str) and re.fullmatch('[A-Z0-9]{1,24}USDT',r['profile']['symbol']) else None,
        'Spot and perpetual results are different market contexts even for the same symbol.')
    add('declared', 'Period', 'Declared evaluation window', lambda r:r['declared'],
        'Saved research or passive-benchmark window; UTC Unix seconds, end exclusive. Ordinary runs may not record this separately.')
    add('trace', 'Period', 'Recorded graph evaluation closes', lambda r:r['trace'],
        'First/last archived graph evaluation closes, both inclusive. These may include unknown indicator values; they do not prove readiness, continuous evaluations or causal fills. Native/passive traces are not treated as graph evaluations.')
    add('warmup', 'Period', 'Declared pre-evaluation warmup', lambda r:r['warmup'],
        'Input start through evaluation start, end exclusive. Equal endpoints mean no declared pre-window input; indicator readiness is separate.')
    add('readiness', 'Period', 'Actual indicator readiness / warmup completion', lambda r:None,
        'This result format does not archive a verified whole-strategy readiness boundary. It cannot be recovered from first trade, current settings or dataset bounds.')
    add('capital', 'Capital', 'Initial capital', lambda r:amount(r['profile'].get('capital')),
        'Saved simulation capital; numeric formatting is normalized only for equality. No return or PnL is recalculated.')
    add('currency', 'Capital', 'Explicit account currency', lambda r:text(r['profile'].get('currency')),
        'Current built-in models use USDT, but a missing historical currency field is not independent archived evidence. Financial columns below retain their original USDT contract.')
    for key, label in [('fee_rate','Commission rate'),('slippage','Slippage rate')]:
        add(key, 'Costs & execution', label, lambda r,k=key:amount(r['profile'].get(k), rate=True),
            'Saved rate as a fraction, not percent. Equal rates do not imply equal realized costs; slippage is already reflected in recorded fill prices.')
    for key, label in [('funding_mode','Funding assumption'),('mark_mode','Mark-price assumption'),('evaluation','Condition evaluation'),('path','Modeled price path'),('gap_policy','Gap policy')]:
        add(key, 'Costs & execution', label, lambda r,k=key:choice(r['profile'].get(k),{'funding_mode':('history','assumed_zero'),'mark_mode':('history','last_proxy'),'evaluation':('closed','intrabar'),'path':('OLHC','OHLC'),'gap_policy':('reject','skip')}[k]),
            'Original saved execution assumption; no current setting is substituted. Funding is relevant to perpetuals; zero realized funding does not establish complete history.')
    for key, label in [('version','Execution profile version'),('primary_minutes','Primary timeframe (minutes)'),('execution_minutes','Explicit execution resolution (minutes)')]:
        add(key, 'Costs & execution', label, lambda r,k=key:choice(r['profile'].get(k),(1,2) if k=='version' else (1,5,15,60,240,1440) if k=='execution_minutes' else (1,3,5,15,30,60,120,240,360,720,1440)),
            'Missing historical fields are unknown here, including omitted legacy M1 defaults; no current default is inserted.')
    add('venue', 'Costs & execution', 'Explicit execution venue', lambda r:text(r['profile'].get('venue')),
        'Dataset source does not independently identify the execution venue or historical exchange constraints.')
    add('engine', 'Costs & execution', 'Engine and metric versions', lambda r:{k:r['summary'][k] for k in ('engine','engine_version','metric_version')} if text(r['summary'].get('engine')) and text(r['summary'].get('engine_version')) and type(r['summary'].get('metric_version')) is int and r['summary']['metric_version'] > 0 else None,
        'Different versions can change accounting or metric meaning; matching version labels alone do not prove implementation identity.')
    add('runtime', 'Costs & execution', 'Runtime implementation fingerprint', lambda r:fingerprint(at(r['manifest'],'runtime','implementation_sha256')),
        'Saved Python implementation fingerprint. Package/platform differences remain in recorded metadata details.')
    add('environment', 'Costs & execution', 'Runtime environment metadata', lambda r:environment(r['manifest'].get('runtime')),
        'Saved Python, platform, architecture and package versions. Large values use a metadata fingerprint; individual differences remain in recorded metadata details.')
    add('profile', 'Costs & execution', 'Full saved profile metadata', lambda r:digest(r['profile']) if r['profile'] else None,
        'Includes recorded allocation, leverage, position management, precision and risk assumptions. Equal metadata hashes do not fill missing fields or establish equivalent strategy quality.')
    counts = {s:sum(row['status']==s for row in rows) for s in ('matched','different','unknown')}
    return dict(version=1, rows=rows, counts=counts,
                note='Recorded evidence review only. Unknown is not a match; differences are warnings, not a strategy ranking. Reports are not rerun and current cache/settings are not consulted.')
