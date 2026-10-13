"""Read-only, bounded input availability checks for independent research drafts.

This does not verify saved output artifacts, execute strategies, or guarantee equal
results. The original run and all workspace content remain unchanged.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import stat

from terminal.data import canonical, digest, runtime_snapshot, validate_range, validate_interval, coverage
from terminal.graph import validate_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.source_limits import checked_parquet, check_materialization, check_manifest
from terminal.storage import identifier

MAX_SNAPSHOT = 256 * 1024
MAX_SUMMARY = 64 * 1024
MAX_ROWS = 100_000
MAX_FILE = 8 * 1024 * 1024
MAX_DECODED = 16 * 1024 * 1024
MAX_MATERIALIZATION = 128 * 1024 * 1024
LIMIT = ('Input inspection limit: 100,000 rows per table, 8 MiB per file, '
         '16 MiB decoded-size estimate and 128 MiB materialization estimate. '
         'This does not mean the saved data is missing or corrupt.')


class InspectionLimit(ValueError):
    pass


def _inside(root, path):
    """Refuse linked descendants, including the runs/datasets parent directories."""
    root = Path(root).resolve()
    path = Path(path)
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Linked saved input paths are unsupported for inspection')
        mode = current.stat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError('Only regular local files and directories can be inspected')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Saved input path is outside this workspace')
    return path


def _small_json(path, limit):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise InspectionLimit('Saved metadata exceeds the bounded inspection limit')
    return json.loads(raw)


def _record(store, run_id):
    # Do not decode oversized legacy database values before admission.
    with store.connect() as db:
        row = db.execute('''SELECT status, length(CAST(manifest AS BLOB)) AS manifest_bytes,
            length(CAST(summary AS BLOB)) AS summary_bytes,
            CASE WHEN length(CAST(manifest AS BLOB))<=? THEN manifest END AS manifest,
            CASE WHEN length(CAST(summary AS BLOB))<=? THEN summary END AS summary
            FROM runs WHERE id=?''', (MAX_SNAPSHOT, MAX_SUMMARY, identifier(run_id))).fetchone()
    if row is None:
        raise ValueError('Run does not exist')
    if row['status'] != 'completed':
        return row['status'], {}, {}
    if row['manifest_bytes'] is None or row['summary_bytes'] is None:
        raise ValueError('Saved metadata is absent')
    if row['manifest'] is None or row['summary'] is None:
        raise InspectionLimit('Saved metadata exceeds the bounded inspection limit')
    return row['status'], json.loads(row['manifest']), json.loads(row['summary'])


def _dataset(store, datasets, saved, profile):
    if not isinstance(saved, dict):
        raise ValueError('Recorded dataset conditions are unavailable')
    dataset_id = saved['id']
    if not isinstance(dataset_id, str) or len(dataset_id) != 64 or any(c not in '0123456789abcdef' for c in dataset_id):
        raise ValueError('Recorded dataset identity is missing or invalid')
    directory = _inside(store.root, datasets.root / dataset_id)
    manifest = _small_json(_inside(store.root, directory / 'manifest.json'), MAX_SNAPSHOT)
    if not isinstance(manifest, dict):
        raise ValueError('Local dataset manifest must be an object')
    check_manifest(manifest)
    validate_range(manifest['market'], manifest['symbol'], *manifest['range'])
    seconds = manifest.get('interval_seconds', 60)
    if type(seconds) is not int or seconds % 60:
        raise ValueError('Invalid dataset interval')
    validate_interval(*manifest['range'], seconds // 60)
    if not isinstance(manifest.get('source'), str) or not manifest['source'].strip():
        raise ValueError('Dataset source was not recorded')
    payload = {k: v for k, v in manifest.items() if k not in ('id', 'files_sha256')}
    if manifest.get('id') != dataset_id or digest(payload) != dataset_id:
        raise ValueError('Dataset manifest identity checksum mismatch')
    projection = {k: manifest[k] for k in ('id', 'content_sha256', 'coverage', 'source', 'range')}
    if manifest.get('interval_seconds', 60) != 60:
        projection['interval_seconds'] = manifest['interval_seconds']
    if canonical(projection) != canonical(saved):
        raise ValueError('Local dataset conditions differ from the immutable snapshot')
    datasets.check_profile(manifest, profile)
    content = {}
    with ExitStack() as stack:
        checked = {}; decoded = 0
        for name in ('trade', 'mark', 'funding'):
            path = _inside(store.root, directory / (name + '.parquet'))
            stream = stack.enter_context(path.open('rb'))
            try:
                parquet, estimate = checked_parquet(stream, name, manifest['files_sha256'][name],
                    max_file_bytes=MAX_FILE, max_rows=MAX_ROWS, limit_message=LIMIT)
            except ValueError as exc:
                if str(exc) == LIMIT:
                    raise InspectionLimit(LIMIT) from exc
                raise
            checked[name] = parquet; decoded += estimate
            if decoded > MAX_DECODED:
                raise InspectionLimit(LIMIT)
        try:
            estimate = check_materialization(checked, decoded)
        except ValueError as exc:
            raise InspectionLimit(LIMIT) from exc
        if estimate > MAX_MATERIALIZATION:
            raise InspectionLimit(LIMIT)
        for name, parquet in checked.items():
            content[name] = parquet.read().to_pylist()
    if digest(content) != saved['content_sha256']:
        raise ValueError('Normalized dataset content checksum mismatch')
    start, end = manifest['range']
    for name in ('trade', 'mark'):
        bars = [Candle(**row) for row in content[name]]
        if any(not start <= b.time < end or b.time % seconds for b in bars) or any(a.time >= b.time for a, b in zip(bars, bars[1:])):
            raise ValueError('Invalid source candle ordering or range')
        if name == 'trade' or manifest['market'] == 'linear':
            if canonical(coverage(bars, start, end, seconds)) != canonical(manifest['coverage'][name]):
                raise ValueError('Recorded coverage differs from actual source candles')
    if manifest['coverage']['funding']['count'] != len(content['funding']):
        raise ValueError('Recorded funding count differs from source history')
    return {**{k: manifest[k] for k in ('id', 'market', 'symbol', 'source', 'range', 'coverage')},
            'interval_seconds': manifest.get('interval_seconds', 60)}


def review(store, datasets, run_id):
    identifier(run_id)
    checks = []
    def add(key, status, detail, **extra):
        checks.append(dict(key=key, status=status, detail=detail, **extra))
    report = {'version': 1, 'run_id': run_id, 'can_prepare': False,
              'runtime_changed': False, 'checks': checks, 'inspection_limit': LIMIT,
              'note': ('Only saved conditions and local input availability are checked. Saved result artifacts '
                       'and calculations are not verified. Matching evidence does not guarantee equal new results '
                       'or provider authenticity. No downloads or calculations are started.')}
    def finish():
        report['review_sha256'] = digest(report)
        return report
    try:
        status, snapshot, summary = _record(store, run_id)
        if status != 'completed' or not isinstance(summary, dict) or summary.get('origin') != 'local':
            add('origin', 'unsupported', 'Only completed local runs are supported. Imported reports remain view-only here.')
            return finish()
        if not isinstance(snapshot, dict) or type(snapshot.get('schema_version')) is not int or snapshot.get('schema_version') != 1:
            raise ValueError('Saved snapshot schema is missing or unsupported')
        if digest({k: v for k, v in snapshot.items() if k != 'snapshot_sha256'}) != snapshot.get('snapshot_sha256'):
            raise ValueError('Immutable snapshot checksum mismatch')
        disk = _small_json(_inside(store.root, store.directory(run_id) / 'snapshot.json'), MAX_SNAPSHOT)
        if canonical(disk) != canonical(snapshot):
            raise ValueError('Saved snapshot file differs from the recorded snapshot')
        if not isinstance(snapshot.get('dataset'), dict):
            raise ValueError('Saved dataset conditions are unavailable')
        if (summary.get('snapshot') != snapshot['snapshot_sha256'] or
                summary.get('dataset') != snapshot.get('dataset', {}).get('id') or
                canonical(summary.get('profile')) != canonical(snapshot.get('profile'))):
            raise ValueError('Saved summary is inconsistent with its immutable conditions')
        add('snapshot', 'available', 'Snapshot checksum, saved file and summary condition links match.')
    except InspectionLimit as exc:
        add('snapshot', 'inspection_limit', str(exc)); return finish()
    except FileNotFoundError:
        add('snapshot', 'unavailable', 'The original snapshot file is unavailable.'); return finish()
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, OSError):
        add('snapshot', 'invalid', 'Saved snapshot conditions are incomplete, invalid, inconsistent or unsafe to read.'); return finish()

    graph = snapshot.get('strategy'); raw_profile = snapshot.get('profile'); profile = None
    try:
        if not isinstance(raw_profile, dict):
            raise ValueError('The full saved simulation profile is unavailable.')
        if type(raw_profile.get('primary_minutes')) is not int:
            raise ValueError('Saved primary timeframe must be an integer')
        profile = Profile(**raw_profile)
        # Only the versioned M1/no-management omissions survive this equality.
        if canonical(profile.snapshot()) != canonical(raw_profile):
            raise ValueError('Incomplete or noncanonical profile; current defaults will not fill saved conditions.')
        add('profile', 'available', 'Every recorded simulation, capital, cost and execution field is preserved.')
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError):
        profile = None
        add('profile', 'unknown', 'Full canonical simulation conditions are unavailable or unsupported; no current defaults are substituted.')
    scope_ok = False
    nodes = graph.get('nodes') if isinstance(graph, dict) else None
    frozen = isinstance(nodes, list) and any(isinstance(n, dict) and n.get('type') == 'frozen_rule' for n in nodes)
    expected_keys = {'schema_version', 'strategy', 'profile', 'dataset', 'runtime', 'snapshot_sha256'}
    try:
        if set(snapshot) - (expected_keys | {'research'}):
            raise ValueError('Unknown saved snapshot extensions are unsupported.')
        if 'research' in snapshot:
            raise ValueError('Window, warmup, experiment and Lab research contracts are not supported by this first draft-copy flow.')
        if not isinstance(graph, dict) or 'engine' in graph or 'benchmark' in graph:
            raise ValueError('Native Python and benchmark snapshots are unsupported; no source is loaded or trusted.')
        if frozen:
            raise ValueError('Frozen-rule contracts require their dedicated workflow and are not copied here.')
        validate_graph(graph)
        if profile is None or profile.evaluation != 'closed':
            raise ValueError('This first copy flow requires a complete closed-bar graph profile; intrabar runs are unsupported.')
        scope_ok = True
        add('strategy', 'available', 'Ordinary closed-bar graph is supported. Original name/layout were not recorded; the copy gets a new name and neutral layout.')
    except (ValueError, TypeError, KeyError):
        # Preserve useful specific scope explanations without source/parser details.
        if set(snapshot) - (expected_keys | {'research'}): detail = 'Unknown saved snapshot extensions are unsupported and will not be silently dropped.'
        elif 'research' in snapshot: detail = 'Window, warmup, experiment and Lab research contracts are not supported in this first copy flow.'
        elif isinstance(graph, dict) and ('engine' in graph or 'benchmark' in graph): detail = 'Native Python and benchmark snapshots are unsupported; no source is loaded or trusted.'
        elif frozen: detail = 'Frozen-rule snapshots are unsupported in this first copy flow.'
        else: detail = 'Only valid ordinary closed-bar graphs with complete profiles are supported; intrabar or unknown graph contracts are not copied.'
        add('strategy', 'unsupported', detail)

    current = runtime_snapshot(); saved_runtime = snapshot.get('runtime')
    runtime_known = (isinstance(saved_runtime, dict) and set(saved_runtime) == set(current)
        and all(isinstance(saved_runtime.get(k), str) and saved_runtime[k] for k in ('python', 'platform', 'machine', 'implementation_sha256'))
        and len(saved_runtime['implementation_sha256']) == 64 and all(c in '0123456789abcdef' for c in saved_runtime['implementation_sha256'])
        and isinstance(saved_runtime.get('packages'), dict) and bool(saved_runtime['packages'])
        and all(isinstance(k, str) and isinstance(v, str) and k and v for k, v in saved_runtime['packages'].items()))
    runtime_changed = runtime_known and canonical(saved_runtime) != canonical(current)
    report['runtime_changed'] = bool(runtime_changed)
    def environment(value):
        return {**{k: value[k] for k in ('python', 'platform', 'machine', 'implementation_sha256')},
                'packages_sha256': digest(value['packages'])}
    add('runtime', 'different' if runtime_changed else 'matched' if runtime_known else 'unknown',
        'New research uses the current runtime. Recorded implementation, package or platform evidence differs.' if runtime_changed else
        'Recorded runtime evidence matches; equal calculation output is not guaranteed.' if runtime_known else 'The complete original runtime was not recorded.',
        saved=environment(saved_runtime) if runtime_known else None, current=environment(current))
    contracts = {k: summary.get(k) for k in ('engine', 'engine_version', 'metric_version')}
    contracts_ok = canonical(contracts) == canonical({'engine': 'nautilus_trader', 'engine_version': '1.231.0', 'metric_version': 1}) and current['packages'].get('nautilus_trader') == '1.231.0'
    contracts_ok = contracts_ok and runtime_known and saved_runtime['packages'].get('nautilus_trader') == '1.231.0'
    add('contracts', 'matched' if contracts_ok else 'unsupported',
        'Recorded engine/metric labels match this supported engine; these are not an independent verification of saved output.' if contracts_ok else
        'Recorded engine or metric versions are absent or unsupported by this copy flow.', saved=contracts)
    platform_ok = sys.platform in ('linux', 'win32')
    add('platform', 'available' if platform_ok else 'unsupported', 'Current graph worker platform is supported.' if platform_ok else 'Graph worker lifecycle is unsupported on this platform.')
    dataset = None
    if profile is not None:
        try:
            dataset = _dataset(store, datasets, snapshot['dataset'], profile)
            add('data', 'available', 'Exact dataset identity, recorded coverage/range and normalized trade, mark and funding content verified locally. Source labels do not authenticate a provider.',
                source=dataset['source'], dataset_id=dataset['id'], range=dataset['range'], interval_seconds=dataset['interval_seconds'])
        except InspectionLimit as exc:
            add('data', 'inspection_limit', str(exc))
        except FileNotFoundError:
            add('data', 'unavailable', 'Original local dataset files are missing. No substitute history is selected or downloaded.')
        except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, OSError):
            add('data', 'invalid', 'Original dataset identity/content, profile compatibility or safe local path verification failed. No substitute history is selected.')
    else:
        add('data', 'unknown', 'Data compatibility cannot be checked without complete saved simulation conditions.')
    report['can_prepare'] = bool(scope_ok and runtime_known and contracts_ok and platform_ok and dataset)
    # The read-only preparation copies only these exact frozen conditions.
    if report['can_prepare']:
        report['draft'] = {'name': f'Research copy of run {run_id[:8]}', 'graph': graph,
                          'profile': raw_profile, 'dataset': dataset, 'snapshot_sha256': snapshot['snapshot_sha256']}
    return finish()


def prepare(store, datasets, run_id, expected_review, acknowledge_runtime_change):
    if type(acknowledge_runtime_change) is not bool:
        raise ValueError('Expected an explicit current-runtime acknowledgement')
    result = review(store, datasets, run_id)
    if result['review_sha256'] != expected_review:
        raise ValueError('Saved inputs or current runtime changed. Check availability and review again.')
    if not result['can_prepare']:
        raise ValueError('Saved conditions cannot prepare a draft; review the availability checks.')
    if result['runtime_changed'] and not acknowledge_runtime_change:
        raise ValueError('Acknowledge that this is new research using the changed current runtime.')
    return {'run_id': run_id, 'review_sha256': expected_review, 'runtime_changed': result['runtime_changed'], **result['draft']}
