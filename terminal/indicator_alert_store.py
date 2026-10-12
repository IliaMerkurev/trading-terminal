"""Durable local rule library and atomic alert evidence/cursor transactions.

This module owns no monitor, provider, banner or thread. Cursor tokens are
capabilities issued for an explicit baseline and invalidated on startup/pause.
They never restore an armed runtime after restart.
"""
import hashlib
import uuid

from terminal.chart_presets import preset_name
from terminal.storage import identifier
from terminal.indicator_alerts import (
    encode, decode, validate_definition, definition_hash, transition, _integer,
)

MAX_EVENT_BYTES = 600 * 1024
MAX_PAGE_BYTES = 600 * 1024


def _truth(value):
    if value is not None and type(value) is not bool:
        raise ValueError('Invalid alert cursor truth')
    return None if value is None else int(value)


def _bool(value):
    return None if value is None else bool(value)


class IndicatorAlertStore:
    def __init__(self, store):
        self.store = store
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS indicator_alert_review_v1(rule_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS indicator_alert_requests_v1(
                    request_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, rule_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS indicator_alert_rules_v1(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL,
                    definition_revision INTEGER NOT NULL, deleted INTEGER NOT NULL,
                    definition TEXT NOT NULL, definition_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS indicator_alert_cursors_v1(
                    rule_id TEXT PRIMARY KEY, token TEXT, definition_revision INTEGER NOT NULL,
                    confirmed_at INTEGER NOT NULL, truth INTEGER, state_truth INTEGER, evaluation_hash TEXT);
                CREATE TABLE IF NOT EXISTS indicator_alert_events_v1(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                    rule_id TEXT NOT NULL, definition_revision INTEGER NOT NULL,
                    confirmed_at INTEGER NOT NULL, observed_at INTEGER NOT NULL,
                    evidence TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0,
                    banner_claimed INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(rule_id,definition_revision,confirmed_at));
                CREATE TRIGGER IF NOT EXISTS indicator_alert_event_immutable_v1
                    BEFORE UPDATE OF id,rule_id,definition_revision,confirmed_at,observed_at,evidence
                    ON indicator_alert_events_v1 BEGIN
                        SELECT RAISE(ABORT,'Alert event evidence is immutable');
                    END;
            ''')
            # Startup invalidates prior capabilities, not evidence or progress.
            db.execute('UPDATE indicator_alert_cursors_v1 SET token=NULL')

    @staticmethod
    def _metadata(row):
        return dict(id=row['id'], name=row['name'], revision=row['revision'],
                    definition_revision=row['definition_revision'], deleted=bool(row['deleted']),
                    definition_hash=row['definition_hash'])

    def _row(self, db, rule_id, revision=None):
        identifier(rule_id)
        if revision is not None:
            _integer(revision, 1)
        row = db.execute('SELECT * FROM indicator_alert_rules_v1 WHERE id=?', (rule_id,)).fetchone()
        if row is None:
            raise ValueError('Alert rule not found')
        if revision is not None and row['revision'] != revision:
            raise ValueError('Alert rule changed; reload before continuing')
        return row

    def requires_rebind(self, rule_id):
        with self.store.connect() as db:
            return db.execute('SELECT 1 FROM indicator_alert_review_v1 WHERE rule_id=?', (rule_id,)).fetchone() is not None

    def require_rebind(self, rule_id):
        identifier(rule_id)
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO indicator_alert_review_v1 VALUES(?)', (rule_id,))

    def inspect_request(self, request_id):
        identifier(request_id)
        with self.store.connect() as db:
            row = db.execute('SELECT request_id,kind,rule_id FROM indicator_alert_requests_v1 WHERE request_id=?', (request_id,)).fetchone()
        return dict(row) if row else None

    def request(self, request_id, kind, fingerprint):
        """Durable bounded identities make uncertain create/arm replies inspectable.

        Each record is constant-size; it never retains a duplicate definition.
        Like saved rules/events, the local ledger is not a fixed-count quota.
        """
        identifier(request_id)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM indicator_alert_requests_v1 WHERE request_id=?', (request_id,)).fetchone()
        if row and (row['kind'] != kind or row['fingerprint'] != fingerprint):
            raise ValueError('Alert request identity was reused with different content')
        return row['rule_id'] if row else None

    def record_arm_request(self, request_id, fingerprint, rule_id):
        identifier(request_id); identifier(rule_id)
        with self.store.connect() as db:
            db.execute('INSERT INTO indicator_alert_requests_v1 VALUES(?,?,?,?)',
                       (request_id, 'arm', fingerprint, rule_id))

    def create(self, name, definition, request_id=None):
        name = preset_name(name)
        definition = validate_definition(definition)
        raw, digest = encode(definition).decode(), definition_hash(definition)
        ident = uuid.uuid4().hex
        fingerprint = hashlib.sha256(encode([name, definition], 300 * 1024)).hexdigest()
        if request_id is not None:
            prior = self.request(request_id, 'create', fingerprint)
            if prior:
                return self.get(prior)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if request_id is not None:
                # Runtime serializes requests, and this recheck also protects
                # direct callers from a concurrent duplicate create.
                prior = db.execute('SELECT * FROM indicator_alert_requests_v1 WHERE request_id=?', (request_id,)).fetchone()
                if prior:
                    if prior['kind'] != 'create' or prior['fingerprint'] != fingerprint:
                        raise ValueError('Alert request identity was reused with different content')
                    ident = prior['rule_id']
                else:
                    db.execute('INSERT INTO indicator_alert_requests_v1 VALUES(?,?,?,?)', (request_id, 'create', fingerprint, ident))
            if request_id is None or prior is None:
                db.execute('INSERT INTO indicator_alert_rules_v1 VALUES(?,?,1,1,0,?,?)', (ident, name, raw, digest))
        return self.get(ident)

    def get(self, rule_id, revision=None):
        with self.store.connect() as db:
            row = self._row(db, rule_id, revision)
        definition = validate_definition(decode(row['definition']))
        if definition_hash(definition) != row['definition_hash']:
            raise ValueError('Saved alert definition failed integrity verification')
        return dict(self._metadata(row), definition=definition)

    def list(self, trashed=False, *, after=None, limit=20):
        if type(trashed) is not bool or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Invalid alert library page')
        if after is not None:
            identifier(after)
        with self.store.connect() as db:
            rows = db.execute('SELECT * FROM indicator_alert_rules_v1 WHERE deleted=? AND id>? ORDER BY id LIMIT ?',
                              (int(trashed), after or '', limit+1)).fetchall()
        return dict(rules=[self._metadata(row) for row in rows[:limit]],
                    next_cursor=rows[limit-1]['id'] if len(rows) > limit else None)

    def _change(self, rule_id, revision, *, name=None, deleted=None, definition=None):
        if name is not None:
            name = preset_name(name)
        if definition is not None:
            definition = validate_definition(definition)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, rule_id, revision)
            if deleted is None and row['deleted']:
                raise ValueError('Restore the alert rule before editing it')
            if deleted is not None and bool(row['deleted']) == deleted:
                raise ValueError('Alert rule already has that trash state')
            # Rebind never updates an event's frozen definition or restores a token.
            db.execute('UPDATE indicator_alert_rules_v1 SET name=?,revision=?,definition_revision=?,deleted=?,definition=?,definition_hash=? WHERE id=?',
                       (name if name is not None else row['name'], revision+1,
                        row['definition_revision'] + (definition is not None),
                        row['deleted'] if deleted is None else int(deleted),
                        row['definition'] if definition is None else encode(definition).decode(),
                        row['definition_hash'] if definition is None else definition_hash(definition), rule_id))
            db.execute('UPDATE indicator_alert_cursors_v1 SET token=NULL WHERE rule_id=?', (rule_id,))
            if definition is not None:
                db.execute('DELETE FROM indicator_alert_review_v1 WHERE rule_id=?', (rule_id,))
        return self.get(rule_id)

    def rename(self, rule_id, revision, name):
        return self._change(rule_id, revision, name=name)

    def trash(self, rule_id, revision):
        return self._change(rule_id, revision, deleted=True)

    def restore(self, rule_id, revision):
        return self._change(rule_id, revision, deleted=False)

    def rebind(self, rule_id, revision, definition):
        return self._change(rule_id, revision, definition=definition)

    def cursor(self, rule_id):
        identifier(rule_id)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM indicator_alert_cursors_v1 WHERE rule_id=?', (rule_id,)).fetchone()
        return None if row is None else dict(token=row['token'], definition_revision=row['definition_revision'],
            confirmed_at=row['confirmed_at'], truth=_bool(row['truth']), state_truth=_bool(row['state_truth']))

    def begin_cursor(self, rule_id, revision, baseline):
        """Seed without delivery. Caller must first review/validate explicit Arm.

        Baseline is the final replay row. It can be true or a historical hit;
        no event is written. Runtime must validate its complete active set first.
        """
        _integer(baseline.get('confirmed_at'), 1)
        truth, state_truth = _truth(baseline.get('truth')), _truth(baseline.get('state_truth'))
        token = uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, rule_id, revision)
            if row['deleted']:
                raise ValueError('Cannot start a trashed alert rule')
            definition = validate_definition(decode(row['definition']))
            width = definition['context']['minutes'] * 60
            if baseline['confirmed_at'] < definition['origin']['time'] + width or baseline['confirmed_at'] % width:
                raise ValueError('Invalid alert baseline close')
            db.execute('INSERT OR REPLACE INTO indicator_alert_cursors_v1 VALUES(?,?,?,?,?,?,NULL)',
                       (rule_id, token, row['definition_revision'], baseline['confirmed_at'], truth, state_truth))
        return self.cursor(rule_id)

    def invalidate_cursor(self, rule_id=None):
        if rule_id is not None:
            identifier(rule_id)
        with self.store.connect() as db:
            if rule_id is None:
                db.execute('UPDATE indicator_alert_cursors_v1 SET token=NULL')
            else:
                db.execute('UPDATE indicator_alert_cursors_v1 SET token=NULL WHERE rule_id=?', (rule_id,))

    def commit_evaluation(self, rule_id, revision, token, expected_close, evaluation, *, observed_at):
        """Atomically write a computed hit and advance its reviewed cursor.

        Only trusted pure replay output enters here. The runtime is responsible
        for live receipt provenance/freshness/epoch fences, absent from this slice.
        A duplicate close returns its existing journal ID without rewriting it.
        """
        identifier(token)
        _integer(expected_close, 1); _integer(observed_at, 1)
        if type(evaluation) is not dict or set(evaluation) != {'raw_open_time', 'confirmed_at', 'truth', 'state_truth', 'hit', 'conditions'}:
            raise ValueError('Invalid alert evaluation evidence')
        encode(evaluation, MAX_EVENT_BYTES)
        _integer(evaluation['confirmed_at'], 1); _integer(evaluation['raw_open_time'])
        if type(evaluation['hit']) is not bool or type(evaluation['conditions']) is not list:
            raise ValueError('Invalid alert evaluation evidence')
        truth, state_truth = _truth(evaluation['truth']), _truth(evaluation['state_truth'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, rule_id, revision)
            cursor = db.execute('SELECT * FROM indicator_alert_cursors_v1 WHERE rule_id=?', (rule_id,)).fetchone()
            if row['deleted'] or cursor is None or cursor['token'] != token or cursor['definition_revision'] != row['definition_revision']:
                raise ValueError('Alert cursor is paused or superseded')
            definition = validate_definition(decode(row['definition']))
            width = definition['context']['minutes'] * 60
            stamp = evaluation['confirmed_at']
            if stamp != expected_close + width or evaluation['raw_open_time'] != expected_close or observed_at < stamp:
                raise ValueError('Alert close is not contiguous or observation precedes confirmation')
            event_id = hashlib.sha256(encode([rule_id, row['definition_revision'], stamp])).hexdigest()
            existing = db.execute('SELECT id,evidence FROM indicator_alert_events_v1 WHERE rule_id=? AND definition_revision=? AND confirmed_at=?',
                                  (rule_id, row['definition_revision'], stamp)).fetchone()
            evaluation_digest = hashlib.sha256(encode(evaluation, MAX_EVENT_BYTES)).hexdigest()
            if cursor['confirmed_at'] == stamp:
                if cursor['evaluation_hash'] != evaluation_digest:
                    raise ValueError('Conflicting duplicate alert evidence')
                return dict(event_id=existing['id'] if existing else None, duplicate=True, confirmed_at=stamp)
            if cursor['confirmed_at'] != expected_close:
                raise ValueError('Alert cursor changed; receipt was not committed')
            if len(evaluation['conditions']) != len(definition['conditions']):
                raise ValueError('Alert condition evidence is incomplete')
            for index, (evidence, condition) in enumerate(zip(evaluation['conditions'], definition['conditions'])):
                expected_kind = 'state' if condition['predicate'] in ('above', 'below') else 'impulse'
                if evidence.get('index') != index or evidence.get('predicate') != condition['predicate'] or evidence.get('kind') != expected_kind:
                    raise ValueError('Alert condition evidence does not match the frozen rule')
                _truth(evidence.get('truth'))
            expected_state = transition(evaluation['conditions'], definition['combine'], _bool(cursor['truth']), _bool(cursor['state_truth']))
            if any(evaluation[key] != expected_state[key] for key in ('truth', 'state_truth', 'hit')):
                raise ValueError('Alert transition does not match its durable baseline')
            if existing:
                import json
                original = json.loads(existing['evidence'])
                if any(original[key] != evaluation[key] for key in evaluation):
                    raise ValueError('Conflicting previously committed alert evidence')
            payload = dict(version=1, rule_id=rule_id, definition_revision=row['definition_revision'],
                           definition_hash=row['definition_hash'], definition=definition,
                           observed_at=observed_at, **evaluation)
            if evaluation['hit']:
                db.execute('INSERT OR IGNORE INTO indicator_alert_events_v1(id,rule_id,definition_revision,confirmed_at,observed_at,evidence) VALUES(?,?,?,?,?,?)',
                           (event_id, rule_id, row['definition_revision'], stamp, observed_at, encode(payload, MAX_EVENT_BYTES).decode()))
            # Keeping this in the same transaction is the event/cursor safety boundary.
            db.execute('UPDATE indicator_alert_cursors_v1 SET confirmed_at=?,truth=?,state_truth=?,evaluation_hash=? WHERE rule_id=? AND token=?',
                       (stamp, truth, state_truth, evaluation_digest, rule_id, token))
            return dict(event_id=event_id if evaluation['hit'] else None, duplicate=existing is not None, confirmed_at=stamp)

    @staticmethod
    def _event(row):
        # Events can contain a 256 KiB definition plus bounded condition evidence.
        import json
        evidence = json.loads(row['evidence'])
        encode(evidence, MAX_EVENT_BYTES)
        return dict(id=row['id'], sequence=row['sequence'], rule_id=row['rule_id'], current_name=row['name'],
                    is_read=bool(row['is_read']), banner_claimed=bool(row['banner_claimed']), evidence=evidence)

    def event(self, event_id):
        if type(event_id) is not str or len(event_id) != 64 or any(c not in '0123456789abcdef' for c in event_id):
            raise ValueError('Invalid alert event identifier')
        with self.store.connect() as db:
            row = db.execute('SELECT e.*,r.name FROM indicator_alert_events_v1 e JOIN indicator_alert_rules_v1 r ON r.id=e.rule_id WHERE e.id=?', (event_id,)).fetchone()
        if row is None:
            raise ValueError('Alert event not found')
        return self._event(row)

    def events(self, *, after=0, limit=20, unread_only=False):
        _integer(after)
        if type(limit) is not int or not 1 <= limit <= 100 or type(unread_only) is not bool:
            raise ValueError('Invalid alert journal page')
        with self.store.connect() as db:
            rows = db.execute('SELECT e.*,r.name FROM indicator_alert_events_v1 e JOIN indicator_alert_rules_v1 r ON r.id=e.rule_id WHERE e.sequence>? AND (?=0 OR e.is_read=0) ORDER BY e.sequence LIMIT ?',
                              (after, int(unread_only), limit+1)).fetchall()
        result = []
        for row in rows[:limit]:
            candidate = self._event(row)
            try:
                encode(dict(events=result+[candidate], next_cursor=row['sequence']), MAX_PAGE_BYTES)
            except ValueError:
                if not result:
                    raise ValueError('Alert event exceeds journal page budget; use exact event lookup')
                break
            result.append(candidate)
        return dict(events=result, next_cursor=result[-1]['sequence'] if len(result) < len(rows) else None)

    def mark_read(self, event_id, is_read=True):
        if type(is_read) is not bool:
            raise ValueError('Invalid read state')
        self.event(event_id)
        with self.store.connect() as db:
            db.execute('UPDATE indicator_alert_events_v1 SET is_read=? WHERE id=?', (int(is_read), event_id))
        return self.event(event_id)

    def claim_banner(self, event_id):
        """Durable at-most-once attempt; a lost response may mean no banner."""
        self.event(event_id)
        with self.store.connect() as db:
            changed = db.execute('UPDATE indicator_alert_events_v1 SET banner_claimed=1 WHERE id=? AND banner_claimed=0', (event_id,)).rowcount
        return changed == 1
