"""Bounded cache-only frozen-rule research; never a live alert delivery path.

Raw inputs, frozen definitions and calculated rows are durable immutable evidence.
Only status/coverage advance. Opening saved research never recalculates anything.
"""
import hashlib
import json
import threading
import time
import uuid

from terminal import indicator_alerts as core
from terminal.chart_history import ChartHistory
from terminal.market_sources import cache_market
from terminal.storage import identifier

MAX_RESPONSE_BYTES = 600 * 1024
MAX_WORKING_BYTES = 256 * 1024 * 1024
MAX_INPUTS = 10000
MAX_UNFINISHED = 8
UNFINISHED = ('queued', 'running', 'cancel_requested')
CACHE_WARNING = ('Saved event numbers and frozen conditions are authoritative. Adjacent price candles '
                 'come from the CURRENT local cache and may have changed since the event; '
                 'they are not the original calculation snapshot.')


def _bounded_int(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Invalid ' + label)
    return value


def _response(value):
    core.encode(value, MAX_RESPONSE_BYTES)
    return value


def _cache_key(definition):
    context = definition['context']
    return cache_market(context['market'], context['source']), context['symbol'], context['minutes']


CACHE_SQL = ('SELECT c.candle,p.provenance,p.content_hash,p.conflict FROM chart_candles_v1 c '
             'LEFT JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) '
             'WHERE c.market=? AND c.symbol=? AND c.minutes=? AND c.time>=? AND c.time<=? '
             'ORDER BY c.time LIMIT ?')


class IndicatorAlertHistory:
    def __init__(self, alert_store):
        self.alerts = alert_store
        self.store = alert_store.store
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.closed = False
        self.tokens = {}
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS indicator_history_runs_v1(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
                    created_at INTEGER NOT NULL, rule_snapshot TEXT NOT NULL,
                    start INTEGER NOT NULL, end INTEGER NOT NULL, input_count INTEGER NOT NULL,
                    input_hash TEXT NOT NULL, status TEXT NOT NULL, cancel_requested INTEGER NOT NULL,
                    summary TEXT, error TEXT);
                CREATE TABLE IF NOT EXISTS indicator_history_inputs_v1(
                    run_id TEXT NOT NULL, row_index INTEGER NOT NULL, candle TEXT NOT NULL,
                    PRIMARY KEY(run_id,row_index));
                CREATE TABLE IF NOT EXISTS indicator_history_rows_v1(
                    run_id TEXT NOT NULL, row_index INTEGER NOT NULL, confirmed_at INTEGER NOT NULL,
                    in_range INTEGER NOT NULL, hit INTEGER NOT NULL, evaluation TEXT NOT NULL,
                    PRIMARY KEY(run_id,row_index), UNIQUE(run_id,confirmed_at));
                CREATE INDEX IF NOT EXISTS indicator_history_matches_v1
                    ON indicator_history_rows_v1(run_id,in_range,hit,confirmed_at);
                CREATE TRIGGER IF NOT EXISTS indicator_history_identity_v1
                    BEFORE UPDATE OF sequence,id,request_id,fingerprint,created_at,rule_snapshot,start,end,input_count,input_hash
                    ON indicator_history_runs_v1 BEGIN SELECT RAISE(ABORT,'Historical snapshot is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_terminal_v1
                    BEFORE UPDATE ON indicator_history_runs_v1 WHEN OLD.status NOT IN ('queued','running','cancel_requested')
                    BEGIN SELECT RAISE(ABORT,'Terminal historical run is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_input_update_v1
                    BEFORE UPDATE ON indicator_history_inputs_v1 BEGIN SELECT RAISE(ABORT,'Historical input is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_input_delete_v1
                    BEFORE DELETE ON indicator_history_inputs_v1 BEGIN SELECT RAISE(ABORT,'Historical input is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_row_update_v1
                    BEFORE UPDATE ON indicator_history_rows_v1 BEGIN SELECT RAISE(ABORT,'Historical output is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_row_delete_v1
                    BEFORE DELETE ON indicator_history_rows_v1 BEGIN SELECT RAISE(ABORT,'Historical output is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_input_insert_v1
                    BEFORE INSERT ON indicator_history_inputs_v1
                    WHEN (SELECT status FROM indicator_history_runs_v1 WHERE id=NEW.run_id) != 'queued'
                    BEGIN SELECT RAISE(ABORT,'Historical input snapshot is sealed'); END;
                CREATE TRIGGER IF NOT EXISTS indicator_history_row_insert_v1
                    BEFORE INSERT ON indicator_history_rows_v1
                    WHEN (SELECT status FROM indicator_history_runs_v1 WHERE id=NEW.run_id) != 'running'
                    BEGIN SELECT RAISE(ABORT,'Historical output snapshot is sealed'); END;
            ''')
            db.execute("UPDATE indicator_history_runs_v1 SET status='interrupted',cancel_requested=0,error=? WHERE status IN ('queued','running','cancel_requested')",
                       ('Service restarted; this scan was interrupted and will not automatically resume',))
        self.thread = threading.Thread(target=self._run, daemon=True, name='indicator-history')
        self.thread.start()

    @staticmethod
    def _run_row(db, run_id):
        identifier(run_id)
        row = db.execute('SELECT * FROM indicator_history_runs_v1 WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('Historical scan not found')
        return row

    @staticmethod
    def _metadata(row, include_definition=False):
        rule = json.loads(row['rule_snapshot'])
        result = dict(id=row['id'], sequence=row['sequence'], request_id=row['request_id'],
            created_at=row['created_at'], status=row['status'], cancel_requested=bool(row['cancel_requested']),
            rule_id=rule['id'], rule_name=rule['name'], rule_revision=rule['revision'],
            definition_revision=rule['definition_revision'], definition_hash=rule['definition_hash'],
            context=rule['definition']['context'], origin=rule['definition']['origin'],
            start=row['start'], end=row['end'], input_count=row['input_count'], input_hash=row['input_hash'],
            coverage_complete=row['status'] == 'completed', summary=json.loads(row['summary']) if row['summary'] else None,
            error=row['error'])
        if include_definition:
            result['definition'] = rule['definition']
        return result

    def get(self, run_id):
        with self.store.connect() as db:
            return _response(self._metadata(self._run_row(db, run_id), True))

    def request(self, request_id):
        identifier(request_id)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM indicator_history_runs_v1 WHERE request_id=?', (request_id,)).fetchone()
        return _response(dict(request_id=request_id, found=row is not None,
                              run=self._metadata(row) if row else None))

    def list(self, after=None, limit=20):
        _bounded_int(limit, 1, 20, 'historical run page limit')
        if after is not None:
            core._integer(after, 1)
        with self.store.connect() as db:
            rows = db.execute('SELECT * FROM indicator_history_runs_v1 WHERE sequence<? ORDER BY sequence DESC LIMIT ?',
                              (after if after is not None else 2**63-1, limit+1)).fetchall()
        result = []
        for row in rows[:limit]:
            candidate = self._metadata(row)
            try:
                _response(dict(runs=result+[candidate], next_cursor=row['sequence']))
            except ValueError:
                if not result:
                    raise ValueError('Historical run metadata exceeds response budget')
                break
            result.append(candidate)
        return _response(dict(runs=result, next_cursor=result[-1]['sequence'] if len(result) < len(rows) else None))

    def preview(self, rule_id, revision):
        rule = self.alerts.get(rule_id, revision)
        definition = rule['definition']
        width = definition['context']['minutes'] * 60
        with self.store.connect() as db:
            bounds = db.execute('SELECT MIN(c.time),MAX(c.time),COUNT(*) FROM chart_candles_v1 c '
                'JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) '
                "WHERE c.market=? AND c.symbol=? AND c.minutes=? AND p.conflict=0 AND p.provenance IN ('closed_rest','provider_confirmed','synthetic_closed')",
                _cache_key(definition)).fetchone()
        return _response(dict(rule=rule, cached_start=None if bounds[0] is None else bounds[0]+width,
            cached_end=None if bounds[1] is None else bounds[1]+width, cached_count=bounds[2],
            origin_raw_open=definition['origin']['time'], max_inputs=MAX_INPUTS,
            max_working_bytes=MAX_WORKING_BYTES, max_unfinished=MAX_UNFINISHED,
            note='Available cache bounds are inclusive confirmed-close UTC seconds, not a promise of contiguous or conflict-free coverage. All warmup from the frozen origin is required; moving only Start cannot reduce that cost.'))

    def start(self, request_id, rule_id, revision, definition_hash, start, end):
        identifier(request_id); identifier(rule_id)
        core._integer(revision, 1); core._integer(start, 1); core._integer(end, 1)
        if type(definition_hash) is not str or len(definition_hash) != 64 or any(c not in '0123456789abcdef' for c in definition_hash):
            raise ValueError('Invalid frozen definition hash')
        fingerprint = hashlib.sha256(core.encode([rule_id, revision, definition_hash, start, end])).hexdigest()
        with self.lock, self.store.connect() as db:
            if self.closed:
                raise ValueError('Historical worker is closed')
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM indicator_history_runs_v1 WHERE request_id=?', (request_id,)).fetchone()
            if prior:
                if prior['fingerprint'] != fingerprint:
                    raise ValueError('Historical request identity was reused with different content')
                return _response(self._metadata(prior))
            if db.execute("SELECT COUNT(*) FROM indicator_history_runs_v1 WHERE status IN ('queued','running','cancel_requested')").fetchone()[0] >= MAX_UNFINISHED:
                raise ValueError('At most eight unfinished historical scans are allowed')
            stored = self.alerts._row(db, rule_id, revision)
            definition = core.validate_definition(core.decode(stored['definition']))
            if core.definition_hash(definition) != definition_hash or stored['definition_hash'] != definition_hash:
                raise ValueError('Frozen rule definition changed or failed integrity verification')
            rule = dict(self.alerts._metadata(stored), definition=definition)
            width = definition['context']['minutes'] * 60
            origin = definition['origin']['time']
            if start > end or start % width or end % width or start < origin+width:
                raise ValueError('Scan requires ordered inclusive UTC confirmed-close boundaries at or after the frozen origin')
            count = (end-origin)//width
            if not 1 <= count <= MAX_INPUTS:
                raise ValueError('Full-origin input including all warmup exceeds 10,000 candles; an earlier End may help, a later Start cannot')
            estimated = core.working_estimate(definition, count, include_values=True)
            cache_bytes = db.execute('SELECT COALESCE(SUM(length(CAST(candle AS BLOB))),0) FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time>=? AND time<=?',
                                    (*_cache_key(definition), origin, end-width)).fetchone()[0]
            if estimated + cache_bytes*4 > MAX_WORKING_BYTES:
                raise ValueError('Historical snapshot exceeds estimated 256 MiB working resource budget')
            cached = db.execute(CACHE_SQL, (*_cache_key(definition), origin, end-width, MAX_INPUTS+1)).fetchall()
            tape = [ChartHistory.annotate(row) for row in cached]
            core._tape(tape, definition)
            if len(tape) != count or tape[-1]['time'] != end-width:
                raise ValueError('Required full-origin cache coverage is missing through the requested End')
            raw = [core.encode(row, MAX_RESPONSE_BYTES).decode() for row in tape]
            input_hash = hashlib.sha256(core.encode(tape, MAX_WORKING_BYTES)).hexdigest()
            run_id = uuid.uuid4().hex
            db.execute('INSERT INTO indicator_history_runs_v1(id,request_id,fingerprint,created_at,rule_snapshot,start,end,input_count,input_hash,status,cancel_requested) VALUES(?,?,?,?,?,?,?,?,?,?,0)',
                (run_id, request_id, fingerprint, int(time.time()), core.encode(rule, MAX_RESPONSE_BYTES).decode(), start, end, count, input_hash, 'queued'))
            db.executemany('INSERT INTO indicator_history_inputs_v1 VALUES(?,?,?)', ((run_id, index, value) for index, value in enumerate(raw)))
            result = self._metadata(self._run_row(db, run_id))
        self.wake.set()
        return _response(result)

    def cancel(self, run_id):
        with self.lock, self.store.connect() as db:
            row = self._run_row(db, run_id)
            if row['status'] in UNFINISHED:
                token = self.tokens.get(run_id)
                if token:
                    token.set()
                status = 'cancelled' if row['status'] == 'queued' else 'cancel_requested'
                db.execute('UPDATE indicator_history_runs_v1 SET status=?,cancel_requested=?,error=? WHERE id=?',
                           (status, int(status == 'cancel_requested'), 'Cancelled by user' if status == 'cancelled' else None, run_id))
        return self.get(run_id)

    def _run(self):
        while True:
            with self.lock:
                if self.closed:
                    return
                with self.store.connect() as db:
                    run = db.execute("SELECT * FROM indicator_history_runs_v1 WHERE status='queued' ORDER BY sequence LIMIT 1").fetchone()
                    if run:
                        token = self.tokens[run['id']] = threading.Event()
                        db.execute("UPDATE indicator_history_runs_v1 SET status='running' WHERE id=?", (run['id'],))
            if run is None:
                self.wake.wait(.25); self.wake.clear()
                continue
            try:
                with self.store.connect() as db:
                    inputs = db.execute('SELECT candle FROM indicator_history_inputs_v1 WHERE run_id=? ORDER BY row_index', (run['id'],)).fetchall()
                tape = [json.loads(row['candle']) for row in inputs]
                if hashlib.sha256(core.encode(tape, MAX_WORKING_BYTES)).hexdigest() != run['input_hash']:
                    raise ValueError('Historical input snapshot failed integrity verification')
                definition = json.loads(run['rule_snapshot'])['definition']
                calculated = core.replay(definition, tape, token, include_values=True)
                rows = calculated['rows']
                selected = [row for row in rows if run['start'] <= row['confirmed_at'] <= run['end']]
                unknown = sum(row['truth'] is None for row in selected)
                summary = dict(requested_rows=len(selected), evaluated_rows=len(selected), known_rows=len(selected)-unknown,
                    unknown_rows=unknown, match_count=sum(row['hit'] for row in selected),
                    pre_range_rows=len(rows)-len(selected), pre_range_unknown_rows=sum(row['truth'] is None for row in rows if row['confirmed_at'] < run['start']),
                    initial_unknown_rows=next((index for index, row in enumerate(selected) if row['truth'] is not None), len(selected)),
                    unknown_reason='warmup_or_missing_value', input_rows=len(rows), coverage_start=selected[0]['confirmed_at'], coverage_end=selected[-1]['confirmed_at'])
                with self.lock:
                    if self.closed:
                        continue
                    with self.store.connect() as db:
                        current = self._run_row(db, run['id'])
                        if current['status'] not in UNFINISHED:
                            continue
                        if token.is_set() or current['cancel_requested']:
                            raise InterruptedError('Historical scan cancelled')
                        # Publish the entire computed timeline atomically or no output.
                        db.executemany('INSERT INTO indicator_history_rows_v1 VALUES(?,?,?,?,?,?)',
                            ((run['id'], index, row['confirmed_at'], int(run['start'] <= row['confirmed_at'] <= run['end']),
                              int(row['hit']), core.encode(row, MAX_RESPONSE_BYTES).decode()) for index, row in enumerate(rows)))
                        db.execute("UPDATE indicator_history_runs_v1 SET status='completed',summary=?,cancel_requested=0 WHERE id=?",
                                   (core.encode(summary).decode(), run['id']))
            except Exception as exc:
                with self.lock:
                    if self.closed:
                        continue
                    with self.store.connect() as db:
                        current = self._run_row(db, run['id'])
                        if current['status'] in UNFINISHED:
                            cancelled = token.is_set() or current['cancel_requested']
                            db.execute('UPDATE indicator_history_runs_v1 SET status=?,cancel_requested=0,error=? WHERE id=?',
                                       ('cancelled' if cancelled else 'error', str(exc)[:1000] or 'Historical calculation failed', run['id']))
            finally:
                with self.lock:
                    self.tokens.pop(run['id'], None)

    def _completed(self, db, run_id):
        run = self._run_row(db, run_id)
        if run['status'] != 'completed':
            raise ValueError('Historical scan has no complete result; status is ' + run['status'])
        return run

    def matches(self, run_id, after=0, limit=20):
        core._integer(after)
        _bounded_int(limit, 1, 20, 'historical match page limit')
        with self.store.connect() as db:
            self._completed(db, run_id)
            rows = db.execute('SELECT row_index,evaluation FROM indicator_history_rows_v1 WHERE run_id=? AND in_range=1 AND hit=1 AND confirmed_at>? ORDER BY confirmed_at LIMIT ?',
                              (run_id, after, limit+1)).fetchall()
        items = []
        for row in rows[:limit]:
            item = dict(row_index=row['row_index'], **json.loads(row['evaluation']))
            try:
                _response(dict(matches=items+[item], next_cursor=item['confirmed_at']))
            except ValueError:
                if not items:
                    raise ValueError('Historical match exceeds response budget; use exact row lookup')
                break
            items.append(item)
        return _response(dict(matches=items, next_cursor=items[-1]['confirmed_at'] if len(items) < len(rows) else None))

    @staticmethod
    def _chart_row(row):
        return dict(row_index=row['row_index'], candle=json.loads(row['candle']),
                    evaluation=json.loads(row['evaluation']), in_range=bool(row['in_range']))

    def row(self, run_id, confirmed_at=None, raw_open_time=None):
        if (confirmed_at is None) == (raw_open_time is None):
            raise ValueError('Provide exactly one confirmed close or native raw open')
        with self.store.connect() as db:
            run = self._completed(db, run_id)
            width = json.loads(run['rule_snapshot'])['definition']['context']['minutes'] * 60
            if raw_open_time is not None:
                core._integer(raw_open_time)
                confirmed_at = raw_open_time + width
            core._integer(confirmed_at, 1)
            row = db.execute('SELECT r.*,i.candle FROM indicator_history_rows_v1 r JOIN indicator_history_inputs_v1 i USING(run_id,row_index) WHERE r.run_id=? AND r.confirmed_at=?',
                             (run_id, confirmed_at)).fetchone()
            if row is None:
                raise ValueError('Exact historical candle is absent; no nearest candle is substituted')
            return _response(self._chart_row(row))

    def chart(self, run_id, start_index=None, limit=200, target_confirmed_at=None):
        _bounded_int(limit, 1, 200, 'historical chart window limit')
        if start_index is not None:
            core._integer(start_index)
        if target_confirmed_at is not None:
            core._integer(target_confirmed_at, 1)
        with self.store.connect() as db:
            run = self._completed(db, run_id)
            definition = json.loads(run['rule_snapshot'])['definition']
            width = definition['context']['minutes'] * 60
            target = None
            if target_confirmed_at is not None:
                exact = db.execute('SELECT row_index FROM indicator_history_rows_v1 WHERE run_id=? AND confirmed_at=?',
                                   (run_id, target_confirmed_at)).fetchone()
                target = dict(confirmed_at=target_confirmed_at, raw_open_time=target_confirmed_at-width,
                              row_index=exact['row_index'] if exact else None, included=False,
                              status='available' if exact else 'missing')
            if start_index is None:
                start_index = max(0, target['row_index']-40) if target and target['row_index'] is not None else (run['start']-width-definition['origin']['time'])//width
            rows = db.execute('SELECT r.*,i.candle FROM indicator_history_rows_v1 r JOIN indicator_history_inputs_v1 i USING(run_id,row_index) WHERE r.run_id=? AND r.row_index>=? ORDER BY r.row_index LIMIT ?',
                              (run_id, start_index, limit)).fetchall()
        result = dict(run_id=run_id, total_rows=run['input_count'], start_index=start_index,
                      next_index=None, rows=[], markers=[], target=target, byte_limited=False)
        for row in rows:
            item = self._chart_row(row)
            marker = [dict(row_index=row['row_index'], confirmed_at=row['confirmed_at'], raw_open_time=row['confirmed_at']-width)] if row['hit'] and row['in_range'] else []
            candidate = dict(result, rows=result['rows']+[item], markers=result['markers']+marker,
                             next_index=row['row_index']+1 if row['row_index']+1 < run['input_count'] else None)
            if target:
                candidate['target'] = dict(target, included=any(item['row_index'] == target['row_index'] for item in candidate['rows']))
            try:
                # Reserve metadata space for the truthful clipping flag.
                core.encode(candidate, MAX_RESPONSE_BYTES-32)
            except ValueError:
                if not result['rows']:
                    raise ValueError('Exact historical chart row exceeds response byte budget; data was not truncated')
                result['byte_limited'] = True
                break
            result = candidate
        return _response(result)

    def event_evidence(self, event_id, before=40, after=40):
        _bounded_int(before, 0, 199, 'event context before count')
        _bounded_int(after, 0, 199, 'event context after count')
        if before+after+1 > 200:
            raise ValueError('Event price context is limited to 200 native intervals')
        event = self.alerts.event(event_id)
        evidence = event['evidence']
        definition = core.validate_definition(evidence['definition'])
        width = definition['context']['minutes']*60
        target = evidence['confirmed_at']-width
        with self.store.connect() as db:
            rows = db.execute(CACHE_SQL, (*_cache_key(definition), max(0, target-before*width), target+after*width, 200)).fetchall()
        candles = [ChartHistory.annotate(row) for row in rows]
        exact = next((row for row in candles if row['time'] == target), None)
        state = 'missing' if exact is None else 'confirmed' if exact['confirmation'] in core.CLOSED else 'conflict' if exact['confirmation'] == 'conflict' else 'unconfirmed'
        result = dict(event=event, context=definition['context'], warning=CACHE_WARNING,
            price_context_source='current_cache', target_raw_open_time=target,
            target_confirmed_at=evidence['confirmed_at'], target_status=state,
            target_candle=exact if state == 'confirmed' else None,
            candles=[], byte_limited=False)
        for candle in candles:
            candidate = dict(result, candles=result['candles']+[candle])
            try:
                core.encode(candidate, MAX_RESPONSE_BYTES-32)
            except ValueError:
                result['byte_limited'] = True
                break
            result = candidate
        result['target_in_window'] = state == 'confirmed' and any(candle['time'] == target for candle in result['candles'])
        return _response(result)

    def close(self):
        errors = []
        with self.lock:
            if not self.closed:
                self.closed = True
                for token in self.tokens.values():
                    token.set()
                try:
                    with self.store.connect() as db:
                        db.execute("UPDATE indicator_history_runs_v1 SET status='interrupted',cancel_requested=0,error=? WHERE status IN ('queued','running','cancel_requested')",
                                   ('Service stopped; this scan was interrupted and will not automatically resume',))
                except Exception as exc:
                    errors.append(exc)
            # Shutdown signals and joining cannot depend on a successful write.
            # A later close retries joining, never storage after ownership release.
            self.wake.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            errors.append(RuntimeError('Historical worker shutdown is still pending; keep dependencies and workspace ownership'))
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise ExceptionGroup('Historical shutdown cleanup failed', errors)
