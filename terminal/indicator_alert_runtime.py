"""Explicitly armed, cache-only local indicator alerts on passive Hub receipts.

One bounded worker reuses the frozen core and existing display formulas. It does
not own a connection, provider, strategy, PAPER action or notification channel.
"""
from collections import OrderedDict
import copy
import hashlib
import queue
import threading
import time

from terminal.chart_history import INTERVALS
from terminal.chart_presets import preset_name
from terminal.data import digest
from terminal.indicator_alerts import (
    freeze_rule, validate_definition, definition_hash as hash_definition, changed_dependencies,
    validate_active_set, replay, encode, _integer,
)
from terminal.indicator_alert_store import IndicatorAlertStore
from terminal.market_sources import cache_market
from terminal.storage import identifier


class DependencyChanged(ValueError):
    pass


class IndicatorAlertRuntime:
    POLL_SECONDS = .2
    RECEIPT_MAX_AGE = 15

    def __init__(self, display):
        self.display, self.history = display, display.history
        self.hub = self.history.hub
        self.store = IndicatorAlertStore(display.store)
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.closed = False
        self.session_id = None
        from collections import deque
        self.sessions = deque(maxlen=256)
        self.context_revision = 0
        self.context = None
        self.states = OrderedDict()
        self.thread = threading.Thread(target=self._run, daemon=True, name='indicator-alerts')
        self.thread.start()

    @staticmethod
    def catalog():
        from terminal.indicator_alerts import PREDICATES, DIVERGENCES, OSCILLATOR_PORT, port_units, MAX_CONDITIONS, agreement_capability
        from terminal.display_indicators import FIELDS
        return dict(version=1, ports={kind: port_units(kind) for kind in sorted(FIELDS)},
                    predicates=sorted(PREDICATES), divergences=sorted(DIVERGENCES),
                    oscillators=list(OSCILLATOR_PORT), combine=['ALL', 'ANY'], max_conditions=MAX_CONDITIONS,
                    price_ports=['open', 'high', 'low', 'close'], price_unit='price',
                    agreement_capability=agreement_capability())

    def request(self, request_id):
        with self.lock:
            result = self.store.inspect_request(request_id)
            return None if result is None else dict(result, runtime=self._status(result['rule_id']))

    def _status(self, rule_id):
        state = self.states.get(rule_id)
        if state is None:
            return dict(rule_id=rule_id, phase='PAUSED', reason='Explicit Arm review required',
                        confirmed_at=None, request_id=None)
        return dict(rule_id=rule_id, **{key: state.get(key) for key in
                    ('phase', 'reason', 'confirmed_at', 'request_id')})

    def status(self, rule_id=None):
        with self.lock:
            if rule_id is not None:
                self.store.get(rule_id)
                return self._status(rule_id)
            return dict(session_id=self.session_id, context_revision=self.context_revision,
                        context=copy.deepcopy(self.context), rules=[self._status(key) for key in self.states])

    def get(self, rule_id, revision=None):
        with self.lock:
            return dict(self.store.get(rule_id, revision), runtime=self._status(rule_id),
                        rebind_required=self.store.requires_rebind(rule_id))

    def list(self, trashed=False, after=None, limit=20):
        with self.lock:
            result = self.store.list(trashed, after=after, limit=limit)
            for rule in result['rules']:
                rule['runtime'] = self._status(rule['id'])
                rule['rebind_required'] = self.store.requires_rebind(rule['id'])
            return result

    def session_init(self, session_id):
        identifier(session_id)
        with self.lock:
            if session_id != self.session_id:
                if session_id in self.sessions:
                    raise ValueError('Alert client session was superseded; initialize a new session')
                self._pause_all('New frontend session; explicit context and Arm required')
                self.session_id = session_id
                self.sessions.append(session_id)
                self.context_revision, self.context = 0, None
            return dict(session_id=session_id, context_revision=self.context_revision)

    def register_context(self, session_id, context_revision, source, market, symbol, minutes, visible):
        identifier(session_id); _integer(context_revision, 1)
        self.display.key(market, symbol, source)
        if type(minutes) is not int or minutes not in INTERVALS or type(visible) is not bool:
            raise ValueError('Invalid alert UI context')
        context = dict(source=source, market=market, symbol=symbol, minutes=minutes) if visible else None
        with self.lock:
            if session_id != self.session_id:
                raise ValueError('Alert client session changed; initialize before registering context')
            if context_revision < self.context_revision or (context_revision == self.context_revision and context != self.context):
                raise ValueError('Alert UI context was superseded')
            if context_revision > self.context_revision:
                # Even A -> B -> A with identical visible values invalidates pending Arm.
                self._pause_all('Market context changed; explicit Arm required')
                self.context_revision, self.context = context_revision, context
            return dict(session_id=session_id, context_revision=self.context_revision, context=copy.deepcopy(self.context))

    def preview(self, source, market, symbol, minutes, settings_revision, conditions, combine='ALL'):
        _integer(settings_revision)
        with self.display.lock:
            settings = self.display.settings(market, symbol, source)
            if settings.get('warning') or settings['revision'] != settings_revision:
                raise ValueError('Applied indicator settings changed; reload before preview')
            definition = freeze_rule(settings, source, market, symbol, minutes, conditions, combine)
        return dict(definition=definition, definition_hash=hash_definition(definition), settings_revision=settings_revision)

    def _review_definition(self, definition, expected_hash, settings_revision):
        valid = validate_definition(definition)
        if hash_definition(valid) != expected_hash or valid['settings_revision'] != settings_revision:
            raise ValueError('Alert review hash or applied settings revision does not match')
        latest = self.preview(**valid['context'], settings_revision=settings_revision,
                              conditions=valid['conditions'], combine=valid['combine'])
        if latest['definition_hash'] != expected_hash:
            raise ValueError('Applied alert dependencies or origin changed; preview again')
        return valid

    def create(self, request_id, name, definition, definition_hash, settings_revision):
        name = preset_name(name)
        valid = validate_definition(definition)
        if hash_definition(valid) != definition_hash or valid['settings_revision'] != settings_revision or type(settings_revision) is not int:
            raise ValueError('Alert review hash or applied settings revision does not match')
        fingerprint = hashlib.sha256(encode([name, valid], 300 * 1024)).hexdigest()
        with self.lock, self.display.lock:
            prior = self.store.request(request_id, 'create', fingerprint)
            if prior:
                # Reconciliation deliberately precedes current chart revision checks.
                return self.get(prior)
            valid = self._review_definition(valid, definition_hash, settings_revision)
            rule = self.store.create(name, valid, request_id)
            return self.get(rule['id'])

    def rebind(self, rule_id, revision, definition, definition_hash, settings_revision):
        with self.lock, self.display.lock:
            valid = self._review_definition(definition, definition_hash, settings_revision)
            self._pause(rule_id, 'Rule rebound; explicit Arm review required')
            self.store.rebind(rule_id, revision, valid)
            return self.get(rule_id)

    def rename(self, rule_id, revision, name):
        return self._edit('rename', rule_id, revision, name)

    def archive(self, rule_id, revision):
        return self._edit('trash', rule_id, revision)

    def restore(self, rule_id, revision):
        return self._edit('restore', rule_id, revision)

    def _edit(self, action, rule_id, revision, *args):
        with self.lock:
            getattr(self.store, action)(rule_id, revision, *args)
            self._pause(rule_id, 'Rule changed; explicit Arm review required')
            return self.get(rule_id)

    def _pause(self, rule_id, reason, rebind=False):
        if rebind:
            self.store.require_rebind(rule_id)
        state = self.states.get(rule_id)
        if state:
            state['cancel'].set()
            state['observer'].close()
            # Discard potentially large replay inputs immediately. The worker may
            # still own a local copy until its cooperative cancellation check.
            for key in ('tape', 'definition', 'rule', 'baseline', 'prefix_hash'):
                state.pop(key, None)
            state.update(phase='PAUSED', reason=reason)
        self.store.invalidate_cursor(rule_id)

    def _pause_all(self, reason):
        for rule_id in list(self.states):
            if self.states[rule_id]['phase'] != 'PAUSED':
                self._pause(rule_id, reason)
        self.store.invalidate_cursor()

    def pause(self, rule_id=None):
        with self.lock:
            if rule_id is None:
                self._pause_all('Paused explicitly')
            else:
                self.store.get(rule_id)
                self._pause(rule_id, 'Paused explicitly')
            self.wake.set()
            return self.status(rule_id)

    def save_settings(self, **params):
        # Save and dependency fencing are one linearized Service operation.
        # Two concurrent save/revert requests cannot hide a transient change.
        with self.lock, self.display.lock:
            result = self.display.save(**params)
            self.settings_changed()
            return result

    def settings_changed(self):
        """Observe applied saves synchronously, including transient changed/reverted params."""
        with self.lock:
            for trashed in (False, True):
                after = None
                while True:
                    page = self.store.list(trashed, after=after, limit=100)
                    for metadata in page['rules']:
                        try:
                            definition = self.store.get(metadata['id'])['definition']
                            context = definition['context']
                            settings = self.display.settings(context['market'], context['symbol'], context['source'])
                            changed = settings.get('warning') or changed_dependencies(definition, settings)
                        except (ValueError, TypeError, KeyError):
                            # A broken unrelated entry cannot skip healthy rules'
                            # sticky save/revert fence after settings have committed.
                            self._pause(metadata['id'], 'Saved alert definition unavailable; reviewed rebind required', True)
                            continue
                        if changed:
                            self._pause(metadata['id'], 'Surviving indicator parameters changed; review and rebind required', True)
                    after = page['next_cursor']
                    if after is None:
                        break
            for rule_id, state in list(self.states.items()):
                if state['phase'] == 'PAUSED':
                    continue
                try:
                    self._fence(state)
                except Exception as exc:
                    self._pause(rule_id, str(exc)[:500], isinstance(exc, DependencyChanged))

    def _fence(self, state):
        if self.closed or state['cancel'].is_set():
            raise ValueError('Alert operation paused or service stopping')
        if (state['session_id'], state['context_revision']) != (self.session_id, self.context_revision) or state['definition']['context'] != self.context:
            raise ValueError('Alert UI context changed')
        observer = state['observer']
        snap = self.hub.snapshot()
        context = state['definition']['context']
        if observer.failed or not snap['active'] or snap['status'] != 'CONNECTED' or not snap['fresh']:
            raise ValueError('Market source stale, interrupted or observer overflowed; explicit Arm required')
        if (snap['source'], snap['market'], snap['symbol']) != (context['source'], context['market'], context['symbol']) or snap['generation'] != observer.generation or snap['observation_epoch'] != observer.epoch:
            raise ValueError('Market source or connection generation changed')
        if state['history_epoch'] != self.history.epoch:
            raise ValueError('Chart source context changed')
        settings = self.display.settings(context['market'], context['symbol'], context['source'])
        if settings.get('warning') or changed_dependencies(state['definition'], settings):
            raise DependencyChanged('Surviving indicator parameters changed; review and rebind required')
        now = int(time.time())
        if now < state['confirmed_at'] or now - state['confirmed_at'] > context['minutes'] * 60 + self.RECEIPT_MAX_AGE:
            raise ValueError('Native confirmed close is stale; explicit Arm required')

    def arm(self, request_id, rule_id, revision, definition_hash, session_id, context_revision, reviewed):
        identifier(request_id); identifier(session_id); _integer(context_revision, 1)
        if reviewed is not True:
            raise ValueError('Review and explicitly acknowledge the frozen alert before Arm')
        fingerprint = digest([rule_id, revision, definition_hash, session_id, context_revision, reviewed])
        with self.lock, self.display.lock, self.hub.lock:
            prior = self.store.request(request_id, 'arm', fingerprint)
            if prior:
                return self._status(prior)
            if self.closed:
                raise ValueError('Alert runtime is stopping')
            rule = self.store.get(rule_id, revision)
            if self.store.requires_rebind(rule_id):
                raise ValueError('Changed indicator parameters require reviewed rebind before Arm')
            if rule['deleted'] or rule['definition_hash'] != definition_hash:
                raise ValueError('Alert rule archived or review hash changed')
            if rule_id in self.states and self.states[rule_id]['phase'] != 'PAUSED':
                raise ValueError('Alert already armed or preparing; inspect status before another Arm')
            validate_active_set([s['definition'] for s in self.states.values() if s['phase'] != 'PAUSED'] + [rule['definition']])
            observer = self.hub.observe(INTERVALS[rule['definition']['context']['minutes']])
            baseline = observer.initial
            state = dict(phase='ARMING', reason='Warming full-origin cached confirmations; no historical delivery',
                         request_id=request_id, rule=rule, definition=rule['definition'], observer=observer,
                         session_id=session_id, context_revision=context_revision, history_epoch=self.history.epoch,
                         cancel=threading.Event(), baseline=baseline, sequence=0, confirmed_at=0)
            try:
                if baseline is None or baseline['conflict']:
                    raise ValueError('A fresh observed native confirmation is required before Arm')
                state['confirmed_at'] = baseline['candle']['time'] + rule['definition']['context']['minutes'] * 60
                if baseline['observed_at'] < state['confirmed_at']:
                    raise ValueError('Arm baseline was observed before native confirmation close')
                if not 0 <= time.monotonic() - baseline['observed_monotonic'] <= rule['definition']['context']['minutes'] * 60 + self.RECEIPT_MAX_AGE:
                    raise ValueError('Observed native baseline is stale; wait for a new native confirmation')
                self._fence(state)
                self.store.record_arm_request(request_id, fingerprint, rule_id)
            except Exception as exc:
                observer.close()
                if isinstance(exc, DependencyChanged):
                    self.store.require_rebind(rule_id)
                raise
            self.states[rule_id] = state
            # Paused display statuses are merely hints; durable rules/cursors and
            # request identities remain available after this bounded LRU eviction.
            for key in list(self.states):
                if len(self.states) <= 256:
                    break
                if self.states[key]['phase'] == 'PAUSED':
                    del self.states[key]
            self.wake.set()
            return self._status(rule_id)

    def _cached_tape(self, definition, end):
        context = definition['context']
        key = (cache_market(context['market'], context['source']), context['symbol'], context['minutes'])
        with self.history.store.connect() as db:
            rows = db.execute('SELECT c.candle,p.provenance,p.content_hash,p.conflict FROM chart_candles_v1 c LEFT JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) WHERE c.market=? AND c.symbol=? AND c.minutes=? AND c.time>=? AND c.time<=? ORDER BY c.time LIMIT 10001',
                              (*key, definition['origin']['time'], end)).fetchall()
        if len(rows) > 10000:
            raise ValueError('Frozen alert origin exceeds the 10,000-bar replay resource budget')
        return [self.history.annotate(row) for row in rows]

    @staticmethod
    def _raw_hash(tape):
        return digest([{key: row.get(key) for key in ('time', 'open', 'high', 'low', 'close', 'volume')} for row in tape])

    def _check_tape(self, state, tape):
        cached = self._cached_tape(state['definition'], tape[-1]['time'])
        if any(row['confirmation'] == 'conflict' for row in cached) or self._raw_hash(cached) != self._raw_hash(tape):
            raise ValueError('Cached alert input changed or coverage was removed; explicit review required')
        # Provenance downgrades and missing rows are not valid known inputs.
        from terminal.indicator_alerts import _tape
        _tape(cached, state['definition'])

    def _prepare(self, rule_id, state):
        definition = state['definition']
        context = definition['context']
        # capture_hub only persists already observed rows; it never fetches.
        with self.hub.lock:
            self.history.capture_hub(context['market'], context['symbol'], context['minutes'], context['source'])
        tape = self._cached_tape(definition, state['baseline']['candle']['time'])
        if not tape or self._raw_hash(tape[-1:]) != self._raw_hash([state['baseline']['candle']]):
            raise ValueError('Observed Arm baseline does not match complete cached input')
        result = replay(definition, tape, state['cancel'])
        with self.lock, self.display.lock, self.hub.lock, self.history.lock:
            self._fence(state)
            if not 0 <= time.monotonic() - state['baseline']['observed_monotonic'] <= context['minutes'] * 60 + self.RECEIPT_MAX_AGE:
                raise ValueError('Arm warmup outlived fresh baseline; review and Arm again')
            self._check_tape(state, tape)
            self._fence(state)
            cursor = self.store.begin_cursor(rule_id, state['rule']['revision'], result['rows'][-1])
            state.update(phase='ARMED', reason='Monitoring subsequently observed native closes',
                         prefix_hash=self._raw_hash(tape), token=cursor['token'])

    def _receipt(self, rule_id, state, receipt):
        context = state['definition']['context']
        if receipt['sequence'] != state['sequence'] + 1 or receipt['epoch'] != state['observer'].epoch or receipt['generation'] != state['observer'].generation:
            raise ValueError('Alert receipt queue or epoch changed')
        if any(receipt[key] != context[key] for key in ('source', 'market', 'symbol')) or receipt['interval'] != INTERVALS[context['minutes']] or receipt['conflict']:
            raise ValueError('Alert receipt source, native interval or confirmed content conflict')
        if not 0 <= time.monotonic() - receipt['observed_monotonic'] <= self.RECEIPT_MAX_AGE:
            raise ValueError('Queued alert receipt became stale')
        candle = receipt['candle']
        tape = self._cached_tape(state['definition'], state['confirmed_at'] - context['minutes'] * 60)
        if self._raw_hash(tape) != state['prefix_hash']:
            raise ValueError('Cached alert input changed; explicit review required')
        width = context['minutes'] * 60
        if receipt['observed_at'] < candle['time'] + width:
            raise ValueError('Native confirmation was observed before its close')
        if candle['time'] < state['confirmed_at']:
            known = next((row for row in tape if row['time'] == candle['time']), None)
            if known is None or self._raw_hash([known]) != self._raw_hash([candle]):
                raise ValueError('Conflicting or out-of-origin duplicate confirmation')
            state['sequence'] = receipt['sequence']
            return
        if candle['time'] != state['confirmed_at']:
            raise ValueError('Observed native confirmation gap; cached history cannot deliver missed alerts')
        candidate = tape + [candle]
        result = replay(state['definition'], candidate, state['cancel'])
        with self.lock, self.display.lock, self.hub.lock, self.history.lock:
            self._fence(state)
            self._check_tape(state, tape)
            # Preserve all observed confirmations even if a delayed UI has not
            # captured them. Existing cache conflicts are checked before commit.
            self.history.capture_hub(context['market'], context['symbol'], context['minutes'], context['source'])
            self._check_tape(state, candidate)
            if not 0 <= time.monotonic() - receipt['observed_monotonic'] <= self.RECEIPT_MAX_AGE:
                raise ValueError('Alert calculation outlived fresh observation')
            self._fence(state)
            self.store.commit_evaluation(rule_id, state['rule']['revision'], state['token'],
                                         state['confirmed_at'], result['rows'][-1], observed_at=receipt['observed_at'])
            state.update(prefix_hash=self._raw_hash(candidate), sequence=receipt['sequence'], confirmed_at=result['rows'][-1]['confirmed_at'])

    def _run(self):
        while True:
            self.wake.wait(self.POLL_SECONDS)
            self.wake.clear()
            with self.lock:
                if self.closed:
                    return
                active = [(key, state) for key, state in self.states.items() if state['phase'] != 'PAUSED']
            for rule_id, state in active:
                try:
                    with self.lock:
                        self._fence(state)
                    if state['phase'] == 'ARMING':
                        self._prepare(rule_id, state)
                    else:
                        with self.lock:
                            tape = self._cached_tape(state['definition'], state['confirmed_at'] - state['definition']['context']['minutes'] * 60)
                            if self._raw_hash(tape) != state['prefix_hash']:
                                raise ValueError('Cached alert input changed; explicit review required')
                            self._check_tape(state, tape)
                        # One receipt per rule per turn preserves fairness and a
                        # periodic stale poll when no new candle ever arrives.
                        try:
                            receipt = state['observer'].events.get_nowait()
                        except queue.Empty:
                            continue
                        self._receipt(rule_id, state, receipt)
                        self.wake.set()
                except Exception as exc:
                    with self.lock:
                        if self.states.get(rule_id) is state and state['phase'] != 'PAUSED':
                            self._pause(rule_id, str(exc)[:500] or 'Alert evaluation interrupted', isinstance(exc, DependencyChanged))

    def close(self):
        with self.lock:
            self.closed = True
            self._pause_all('Service stopped; explicit Arm required after restart')
            self.wake.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Alert worker shutdown is still pending; keep dependencies and workspace ownership')
