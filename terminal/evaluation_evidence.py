"""Prospective, observational closed-bar evidence; never an order/fill explanation.

The optional extension reuses saved indicator rows and the existing finalization
receipts. No evaluator replay, financial calculation or snapshot migration occurs.
"""
import hashlib
import json
import math
import re

from terminal.data import canonical, digest
from terminal.graph import OUTPUTS, validate_graph
from terminal.profile import Profile
from terminal.storage import identifier

KEY = 'evaluation_evidence'
SCOPE = 'ordinary_closed_graph'
MAX_RECORDS = 10_000
MAX_METADATA = 4 * 1024 * 1024
MAX_HEADER = 4096
MAX_MANIFEST = 256 * 1024
MAX_SUMMARY = 64 * 1024
MAX_ROW = 64 * 1024
MAX_PAGE = 512 * 1024
MAX_VERIFY = 1024 * 1024
NOTICE = ('Recorded graph evaluations are not orders or fills. No link to an individual '
          'trade is inferred. Crossing history and detailed condition reasoning are not reconstructed.')
SCOPE_NOTICE = ('This journal supports new ordinary closed-bar graph runs only. Native, frozen-rule, '
                'intrabar, Position Management, window, experiment and Lab research runs are unsupported.')
DIAGNOSTIC = 'Prospective graph evaluation metadata; not an order or fill explanation.'


class InspectionLimit(ValueError):
    pass


def metadata_size(metadata):
    # Exact added bytes for this field in a nonempty canonical indicator object,
    # including its key, colon and comma, but excluding pre-existing row values.
    return len(canonical({KEY: metadata})) - 1


def supported(snapshot):
    allowed = {'schema_version', 'strategy', 'profile', 'dataset', 'runtime', 'snapshot_sha256'}
    if (not isinstance(snapshot, dict) or set(snapshot) - allowed
            or type(snapshot.get('schema_version')) is not int or snapshot['schema_version'] != 1):
        return False
    graph = snapshot.get('strategy')
    profile = snapshot.get('profile', {})
    return (isinstance(graph, dict) and set(graph) == {'version', 'nodes', 'outputs'}
            and isinstance(graph.get('nodes'), list)
            and not any(not isinstance(n, dict) or n.get('type') == 'frozen_rule' for n in graph['nodes'])
            and 'research' not in snapshot and isinstance(profile, dict)
            and profile.get('evaluation') == 'closed' and profile.get('position_management') is None)


class Recorder:
    """Opt-in worker observer. Capture failure permanently stops only annotations."""
    def __init__(self, snapshot):
        if not supported(snapshot):
            raise ValueError('Unsupported prospective evaluation scope')
        self.snapshot = snapshot
        self.observed = self.recorded = self.metadata_bytes = 0
        self.reason = None

    def capture(self, row, result, candle, primary, engine_time):
        self.observed += 1
        if self.reason is not None:
            return
        try:
            profile = self.snapshot['profile']
            metadata = dict(version=1, ordinal=self.recorded,
                snapshot_sha256=self.snapshot['snapshot_sha256'], observed_at=result['time'],
                engine_event_time_ns=str(engine_time), source_open=candle.time,
                source_close=candle.time + profile.get('execution_minutes', 1) * 60,
                primary_open=primary.time, primary_close=result['time'],
                outputs={key: row['values'].get(ref) if ref is not None else None
                         for key, ref in self.snapshot['strategy']['outputs'].items()})
            size = metadata_size(metadata)
            if self.recorded >= MAX_RECORDS:
                self.reason = 'record_limit'
            elif self.metadata_bytes + size > MAX_METADATA:
                self.reason = 'metadata_limit'
            else:
                row[KEY] = metadata
                self.metadata_bytes += size
                self.recorded += 1
        except Exception:
            # Instrumentation is observational. Never change trading, retry an
            # evaluation or expose a partial metadata object after a failure.
            self.reason = 'recording_failure'

    def finish(self, result):
        header = dict(version=1, scope=SCOPE, snapshot_sha256=self.snapshot['snapshot_sha256'],
            status='complete' if self.reason is None else 'recording_failed' if self.reason == 'recording_failure' else 'truncated',
            reason=self.reason, observed=self.observed, recorded=self.recorded,
            omitted=self.observed - self.recorded, metadata_bytes=self.metadata_bytes,
            limits={'records': MAX_RECORDS, 'metadata_bytes': MAX_METADATA},
            diagnostic_index=len(result['diagnostics']))
        result[KEY] = header
        result['diagnostics'].append({'type': KEY, 'message': DIAGNOSTIC, KEY: header})


def _integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 2**53 - 1


def _header(header, snapshot):
    fields = {'version', 'scope', 'snapshot_sha256', 'status', 'reason', 'observed', 'recorded',
              'omitted', 'metadata_bytes', 'limits', 'diagnostic_index'}
    if (not isinstance(header, dict) or set(header) != fields or type(header['version']) is not int
            or header['version'] != 1 or header['scope'] != SCOPE
            or header['snapshot_sha256'] != snapshot['snapshot_sha256'] or not supported(snapshot)
            or header['limits'] != {'records': MAX_RECORDS, 'metadata_bytes': MAX_METADATA}
            or any(not _integer(header[k]) for k in ('observed', 'recorded', 'omitted', 'metadata_bytes', 'diagnostic_index'))
            or header['recorded'] > MAX_RECORDS or header['metadata_bytes'] > MAX_METADATA
            or header['recorded'] + header['omitted'] != header['observed']
            or len(canonical(header)) > MAX_HEADER):
        raise ValueError('Invalid evaluation evidence header')
    expected = {None: 'complete', 'record_limit': 'truncated', 'metadata_limit': 'truncated',
                'recording_failure': 'recording_failed'}
    if (not isinstance(header['reason'], (str, type(None))) or header['reason'] not in expected
            or expected[header['reason']] != header['status']
            or (header['status'] == 'complete') != (header['omitted'] == 0)):
        raise ValueError('Invalid evaluation evidence completeness')


def _row(row, index, snapshot):
    meta = row.get(KEY) if isinstance(row, dict) else None
    fields = {'version', 'ordinal', 'snapshot_sha256', 'observed_at', 'engine_event_time_ns',
              'source_open', 'source_close', 'primary_open', 'primary_close', 'outputs'}
    if (not isinstance(meta, dict) or set(meta) != fields or type(meta['version']) is not int
            or meta['version'] != 1 or type(meta['ordinal']) is not int or meta['ordinal'] != index
            or meta['snapshot_sha256'] != snapshot['snapshot_sha256']
            or any(not _integer(meta[k]) for k in ('observed_at', 'source_open', 'source_close', 'primary_open', 'primary_close'))):
        raise ValueError('Invalid recorded evaluation identity')
    profile = snapshot['profile']
    source = profile.get('execution_minutes', 1) * 60
    primary = profile['primary_minutes'] * 60
    if (meta['source_open'] % source or meta['primary_open'] % primary
            or meta['source_close'] != meta['source_open'] + source
            or meta['primary_close'] != meta['primary_open'] + primary
            or not meta['primary_open'] <= meta['source_open'] < meta['primary_close']
            or not meta['source_close'] == meta['primary_close'] == meta['observed_at'] == row.get('time')
            or meta['engine_event_time_ns'] != str(meta['source_close'] * 1_000_000_000 - 1)):
        raise ValueError('Invalid recorded evaluation clocks')
    values, signals, outputs = row.get('values'), row.get('signals'), meta['outputs']
    if (not isinstance(values, dict) or not isinstance(signals, dict) or set(signals) != set(OUTPUTS)
            or not isinstance(outputs, dict) or set(outputs) != set(OUTPUTS)):
        raise ValueError('Invalid recorded graph outputs')
    for value in values.values():
        if value is not None and (type(value) not in (int, float, bool) or not math.isfinite(value)):
            raise ValueError('Invalid recorded graph value')
    for key, ref in snapshot['strategy']['outputs'].items():
        value = values.get(ref) if ref is not None else None
        if ((ref is not None and ref not in values) or type(signals[key]) is not bool
                or (value is not None and type(value) is not bool)
                or outputs[key] is not value or signals[key] is not (value is True)):
            raise ValueError('Recorded output does not match the observed graph value')
    return meta


def validate_result(result, snapshot):
    """Only the new opt-in extension is validated; legacy contracts stay intact."""
    if KEY not in result:
        return
    header = result[KEY]
    _header(header, snapshot)
    rows, diagnostics = result['indicators'], result['diagnostics']
    if len(rows) != header['observed'] or len(diagnostics) != header['diagnostic_index'] + 1:
        raise ValueError('Evaluation evidence counts changed')
    expected = {'type': KEY, 'message': DIAGNOSTIC, KEY: header}
    if diagnostics[-1] != expected or any(isinstance(d, dict) and (KEY in d or d.get('type') == KEY) for d in diagnostics[:-1]):
        raise ValueError('Evaluation evidence completion record changed')
    size = 0
    previous = -1
    for index, row in enumerate(rows):
        if index < header['recorded']:
            meta = _row(row, index, snapshot)
            if meta['observed_at'] <= previous:
                raise ValueError('Recorded evaluation order changed')
            previous = meta['observed_at']
            size += metadata_size(meta)
        elif isinstance(row, dict) and KEY in row:
            raise ValueError('Evidence must be an uninterrupted retained prefix')
    if size != header['metadata_bytes']:
        raise ValueError('Recorded metadata size changed')


def summary_fields(result):
    return {KEY: result[KEY]} if KEY in result else {}


def page(store, run_id, offset=0, limit=25, expected_identity=None):
    """Bounded local receipt-backed read, not whole-artifact authentication."""
    identifier(run_id)
    if (not _integer(offset) or type(limit) is not int or not 1 <= limit <= 50
            or expected_identity is not None and (not isinstance(expected_identity, str)
                or re.fullmatch('[a-f0-9]{64}', expected_identity) is None)):
        raise ValueError('Invalid bounded evaluation-page request')
    base = dict(version=1, run_id=run_id, status='unavailable', notice=NOTICE,
                 scope_notice=SCOPE_NOTICE, rows=[], offset=offset, next=None, total=0)
    reply = {**base, 'rows': []}
    def unavailable(status, detail):
        return {**base, 'rows': [], 'status': status, 'detail': detail}
    try:
        with store.connect(timeout=.1) as db:
            db.execute('BEGIN')
            saved = db.execute('''SELECT status, result_hash,
                length(CAST(manifest AS BLOB)) AS mb, length(CAST(summary AS BLOB)) AS sb,
                CASE WHEN length(CAST(manifest AS BLOB))<=? THEN manifest END AS manifest,
                CASE WHEN length(CAST(summary AS BLOB))<=? THEN summary END AS summary
                FROM runs WHERE id=?''', (MAX_MANIFEST, MAX_SUMMARY, run_id)).fetchone()
            if saved is None or saved['status'] != 'completed':
                return unavailable('unavailable', 'No completed saved result is available.')
            if (saved['mb'] or 0) > MAX_MANIFEST or (saved['sb'] or 0) > MAX_SUMMARY:
                raise InspectionLimit('Saved metadata exceeds the bounded inspection limit.')
            snapshot, summary = json.loads(saved['manifest']), json.loads(saved['summary'])
            imported = db.execute("SELECT 1 FROM archive_import_items WHERE kind='run' AND destination_id=?", (run_id,)).fetchone()
            if not isinstance(summary, dict) or summary.get('origin') != 'local' or imported:
                return unavailable('unsupported', 'Imported reports are not supported by this local evaluation journal. Their saved payload remains unchanged.')
            if not isinstance(snapshot, dict) or not supported(snapshot):
                return unavailable('unsupported', SCOPE_NOTICE)
            if KEY not in summary:
                return unavailable('unavailable', 'Prospective evaluation evidence was not recorded for this run. Earlier runs are never reconstructed.')
            if digest({k: v for k, v in snapshot.items() if k != 'snapshot_sha256'}) != snapshot.get('snapshot_sha256'):
                raise ValueError('Saved snapshot checksum mismatch')
            validate_graph(snapshot['strategy'])
            profile = Profile(**snapshot['profile'])
            if profile.snapshot() != snapshot['profile']:
                raise ValueError('Incomplete saved profile')
            header = summary[KEY]
            _header(header, snapshot)
            control = db.execute('SELECT * FROM local_finalization WHERE run_id=?', (run_id,)).fetchone()
            if (control is None or control['phase'] != 'completed'
                    or control['snapshot_hash'] != snapshot['snapshot_sha256']
                    or control['result_hash'] != saved['result_hash'] or summary.get('snapshot') != snapshot['snapshot_sha256']):
                raise ValueError('Local finalization identity is unavailable or inconsistent')
            admission = db.execute('''SELECT kind, run_id, length(CAST(details AS BLOB)) AS size,
                CASE WHEN length(CAST(details AS BLOB))<=? THEN details END AS details
                FROM research_evidence WHERE event_id=?''', (MAX_MANIFEST, 'started:' + run_id)).fetchone()
            if admission is not None and admission['size'] > MAX_MANIFEST:
                raise InspectionLimit('Local admission exceeds the bounded inspection limit.')
            if (admission is None or admission['kind'] != 'started' or admission['run_id'] != run_id
                    or json.loads(admission['details']).get('identity', {}).get('snapshot_sha256') != snapshot['snapshot_sha256']):
                raise ValueError('Local admission does not match the saved snapshot')

            verified = {}
            verified_bytes = 0
            def read_row(kind, index):
                nonlocal verified_bytes
                if (kind, index) in verified:
                    return verified[(kind, index)]
                receipts = db.execute('''SELECT * FROM local_finalization_batches WHERE run_id=? AND generation=?
                    AND kind=? AND start_index<=? AND start_index+row_count>? ORDER BY ordinal LIMIT 2''',
                    (run_id, control['generation'], kind, index, index)).fetchall()
                if len(receipts) != 1:
                    raise ValueError('Missing or overlapping evaluation batch receipt')
                receipt = receipts[0]
                if (not _integer(receipt['row_count'], 1) or receipt['row_count'] > 128
                        or not _integer(receipt['start_index']) or not _integer(receipt['encoded_bytes'])):
                    raise ValueError('Invalid evaluation batch receipt')
                start, end = receipt['start_index'], receipt['start_index'] + receipt['row_count']
                sizes = db.execute('''SELECT row_index, length(CAST(value AS BLOB)) AS bytes FROM series
                    WHERE run_id=? AND kind=? AND row_index>=? AND row_index<? ORDER BY row_index''',
                    (run_id, kind, start, end)).fetchall()
                if ([r['row_index'] for r in sizes] != list(range(start, end))
                        or sum(r['bytes'] for r in sizes) != receipt['encoded_bytes']):
                    raise ValueError('Recorded evaluation batch has changed or has holes')
                if verified_bytes + receipt['encoded_bytes'] > MAX_VERIFY:
                    raise InspectionLimit('Evaluation receipt verification exceeds the 1 MiB read budget.')
                if any(r['bytes'] > MAX_ROW for r in sizes):
                    raise InspectionLimit('An evaluation receipt row exceeds the 64 KiB inspection limit.')
                raw_rows = db.execute('''SELECT row_index,value FROM series WHERE run_id=? AND kind=?
                    AND row_index>=? AND row_index<? ORDER BY row_index''', (run_id, kind, start, end)).fetchall()
                content = hashlib.sha256()
                for row in raw_rows:
                    content.update(canonical([kind, row['row_index'], row['value']]))
                    content.update(b'\n')
                if content.hexdigest() != receipt['content_hash']:
                    raise ValueError('Recorded evaluation content does not match its finalization receipt')
                verified_bytes += receipt['encoded_bytes']
                for row in raw_rows:
                    verified[(kind, row['row_index'])] = row['value']
                return verified[(kind, index)]

            completion = json.loads(read_row('diagnostics', header['diagnostic_index']))
            if completion != {'type': KEY, 'message': DIAGNOSTIC, KEY: header}:
                raise ValueError('Evaluation completeness metadata does not match its finalization receipt')
            for kind, count in (('diagnostics', header['diagnostic_index'] + 1), ('indicators', header['observed'])):
                actual = db.execute('SELECT COUNT(*),MIN(row_index),MAX(row_index) FROM series WHERE run_id=? AND kind=?', (run_id, kind)).fetchone()
                if tuple(actual) != (count, 0 if count else None, count - 1 if count else None):
                    raise ValueError('Recorded evaluation prefix is missing or inconsistent')
            if header['omitted']:
                boundary = json.loads(read_row('indicators', header['recorded']))
                if not isinstance(boundary, dict) or KEY in boundary:
                    raise ValueError('Recorded evaluation truncation boundary changed')
            identity = digest([run_id, snapshot['snapshot_sha256'], saved['result_hash'], control['generation'], header])
            if expected_identity is not None and expected_identity != identity:
                raise ValueError('Evaluation page identity changed; reopen the journal')
            if offset > header['recorded']:
                raise ValueError('Evaluation page is outside the retained prefix')
            reply.update(status='available', identity=identity, header=header, total=header['recorded'],
                         snapshot_sha256=snapshot['snapshot_sha256'], graph=snapshot['strategy'],
                         detail='Selected stored rows and completeness metadata match local admission and finalization receipts. This is not whole-artifact or provider authentication.')
            for index in range(offset, min(header['recorded'], offset + limit)):
                try:
                    row = json.loads(read_row('indicators', index))
                except InspectionLimit:
                    if reply['rows']:
                        break
                    raise
                _row(row, index, snapshot)
                candidate = {**reply, 'rows': [*reply['rows'], row]}
                if len(canonical(candidate)) > MAX_PAGE - 256:
                    if reply['rows']:
                        break
                    raise InspectionLimit('Evaluation page exceeds the 512 KiB response limit.')
                reply['rows'].append(row)
            end = offset + len(reply['rows'])
            reply['next'] = end if end < header['recorded'] else None
            return reply
    except InspectionLimit as exc:
        return unavailable('inspection_limit', str(exc))
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError):
        return unavailable('invalid', 'Saved evaluation evidence is incomplete or inconsistent. Nothing is reconstructed; existing results remain unchanged.')
