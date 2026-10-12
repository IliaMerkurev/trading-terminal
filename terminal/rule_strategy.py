"""Reviewed frozen-rule graph drafts and exact, backtest-only replay admission.

No provider, alert runtime, native source or trading route is invoked here.
The existing alert replay owns all formulas and three-state/pulse semantics.
"""
from datetime import datetime, timezone
import json
import re
import uuid

from terminal.data import canonical, digest
from terminal.profile import Profile
from terminal.storage import identifier

CONTRACT = 'frozen-rule-strategy-v1'
NODE = 'frozen_rule'
SNAPSHOT_BYTES = 300 * 1024
LIMITATION = ('Backtest only: Bybit native M1, closed bars, matching market/symbol, '
              'contiguous data beginning exactly at the frozen origin; at most 10,000 '
              'bars within the estimated 256 MiB replay budget. No live/PAPER, '
              'parameter experiments or research-window reseeding.')


def frozen_nodes(graph):
    return [node for node in graph.get('nodes', []) if node.get('type') == NODE]


def reject_frozen(graph, route):
    if frozen_nodes(graph):
        raise ValueError('Frozen indicator rules are unavailable in ' + route + '. ' + LIMITATION)


def _supported(definition):
    context = definition['context']
    if context['source'] != 'bybit' or context['minutes'] != 1:
        raise ValueError('This conversion supports only saved Bybit native M1 rules. The original rule is unchanged.')


def validate_snapshot(raw):
    from terminal import indicator_alerts as core
    if type(raw) is not str or len(raw.encode('utf-8')) > SNAPSHOT_BYTES:
        raise ValueError('Invalid frozen-rule strategy snapshot size')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate frozen-rule snapshot key')
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        core.encode(value, SNAPSHOT_BYTES)
        core._keys(value, 'version contract rule definition', 'frozen-rule strategy snapshot')
        if type(value['version']) is not int or value['version'] != 1 or value['contract'] != CONTRACT:
            raise ValueError('Unsupported frozen-rule strategy contract')
        rule = value['rule']
        core._keys(rule, 'id name revision definition_revision definition_hash', 'frozen rule provenance')
        identifier(rule['id'])
        if type(rule['name']) is not str or not rule['name'].strip() or len(rule['name']) > 120:
            raise ValueError('Invalid frozen rule name')
        core._integer(rule['revision'], 1)
        core._integer(rule['definition_revision'], 1)
        definition = core.validate_definition(value['definition'])
        if core.definition_hash(definition) != rule['definition_hash']:
            raise ValueError('Frozen rule definition hash mismatch')
        _supported(definition)
        if core.encode(value, SNAPSHOT_BYTES).decode() != raw:
            raise ValueError('Frozen rule snapshot must retain its canonical bytes')
        return value
    except (TypeError, KeyError, RecursionError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid frozen-rule strategy snapshot') from exc


def _name(value):
    if type(value) is not str or not value.strip() or len(value.strip()) > 120:
        raise ValueError('Strategy name must contain 1–120 characters')
    return value.strip()


class RuleStrategies:
    def __init__(self, rules):
        self.rules, self.store = rules, rules.store
        with self.store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS indicator_strategy_requests_v1(
                request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                strategy_id TEXT NOT NULL)''')

    def _preview(self, row, name, direction):
        from terminal import indicator_alerts as core
        if row['deleted']:
            raise ValueError('Restore the archived rule before creating a strategy')
        name = _name(name)
        definition = core.validate_definition(core.decode(row['definition']))
        if core.definition_hash(definition) != row['definition_hash']:
            raise ValueError('Saved rule definition hash mismatch')
        _supported(definition)
        context = definition['context']
        if direction not in ('long', 'short'):
            raise ValueError('Explicitly choose Long or Short entry')
        if direction == 'short' and context['market'] == 'spot':
            raise ValueError('Unleveraged spot cannot enter short; choose Long')
        rule = {key: row[key] for key in ('id', 'name', 'revision', 'definition_revision', 'definition_hash')}
        snapshot = core.encode(dict(version=1, contract=CONTRACT, rule=rule, definition=definition), SNAPSHOT_BYTES).decode()
        validate_snapshot(snapshot)
        graph = dict(version=1, nodes=[dict(id='frozen_rule', type=NODE, inputs={}, params=dict(snapshot=snapshot))],
                     outputs={key: 'frozen_rule.value' if key == 'entry_' + direction else None
                              for key in ('entry_long', 'exit_long', 'entry_short', 'exit_short')})
        profile = Profile(market=context['market'], symbol=context['symbol'], primary_minutes=1, version=2).snapshot()
        result = dict(contract=CONTRACT, rule=rule, name=name, direction=direction, graph=graph,
                      layout={'frozen_rule': dict(x=80, y=100)}, profile=profile,
                      warnings=[LIMITATION,
                          'Frozen condition parameters are read-only. Change the source rule and convert again to create a different condition.',
                          'No exit signal, stop loss or take profit is added. Configure exits/protection before running; end-of-test reporting follows the existing simulation model.',
                          'Initial settings: capital 1000 USDT, fixed allocation 100 USDT, leverage 1, fee 0.1%, slippage 0%, stop loss 0%, take profit 0%. Review instrument precision and costs in the editor.',
                          'Dataset provenance is checked separately. Explicit synthetic fixtures stay synthetic; a source label alone is insufficient.'])
        result['preview_hash'] = digest(result)
        return result

    def preview(self, rule_id, revision, name, direction):
        with self.store.connect() as db:
            return self._preview(self.rules._row(db, rule_id, revision), name, direction)

    def request(self, request_id):
        identifier(request_id)
        with self.store.connect() as db:
            row = db.execute('SELECT request_id,strategy_id FROM indicator_strategy_requests_v1 WHERE request_id=?', (request_id,)).fetchone()
        return dict(row) if row else None

    def create(self, rule_id, revision, name, direction, preview_hash, request_id):
        identifier(request_id)
        if type(preview_hash) is not str or not re.fullmatch('[a-f0-9]{64}', preview_hash):
            raise ValueError('Review the exact strategy preview before creating it')
        fingerprint = digest(dict(rule_id=rule_id, revision=revision, name=name, direction=direction, preview_hash=preview_hash))
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM indicator_strategy_requests_v1 WHERE request_id=?', (request_id,)).fetchone()
            if prior:
                if prior['fingerprint'] != fingerprint:
                    raise ValueError('Strategy request identity was reused with different content')
                return dict(request_id=request_id, strategy_id=prior['strategy_id'])
            preview = self._preview(self.rules._row(db, rule_id, revision), name, direction)
            if preview['preview_hash'] != preview_hash:
                raise ValueError('Strategy preview changed; review it again before creating')
            if any(row['name'].strip().casefold() == preview['name'].casefold()
                   for row in db.execute('SELECT name FROM strategies')):
                raise ValueError('A strategy with this name already exists; choose another name')
            ident = uuid.uuid4().hex
            document = dict(graph=preview['graph'], layout=preview['layout'])
            db.execute('INSERT INTO strategies(id,name,kind,document,updated_at,profile) VALUES(?,?,?,?,?,?)',
                       (ident, preview['name'], 'graph', canonical(document).decode(), datetime.now(timezone.utc).isoformat(), canonical(preview['profile']).decode()))
            db.execute('INSERT INTO indicator_strategy_requests_v1 VALUES(?,?,?)', (request_id, fingerprint, ident))
        return dict(request_id=request_id, strategy_id=ident)


def check_admission(graph, profile, manifest, research=None):
    from terminal import indicator_alerts as core
    from terminal.research_evidence import provenance
    nodes = frozen_nodes(graph)
    if not nodes:
        return None
    if len(nodes) != 1:
        raise ValueError('One frozen indicator-rule node is supported per strategy')
    snapshot = validate_snapshot(nodes[0]['params']['snapshot'])
    definition = snapshot['definition']; context = definition['context']
    if research is not None:
        raise ValueError('Frozen indicator rules do not support research-window or parameter-experiment reseeding')
    if (profile.evaluation != 'closed' or profile.primary_minutes != 1 or profile.execution_minutes != 1
            or profile.gap_policy != 'reject' or profile.market != context['market'] or profile.symbol != context['symbol']):
        raise ValueError('Frozen rule requires its matching market/symbol, closed native M1 and reject-gaps profile')
    if (manifest.get('interval_seconds', 60) != 60 or manifest.get('market') != context['market']
            or manifest.get('symbol') != context['symbol'] or manifest['range'][0] != definition['origin']['time']):
        raise ValueError('Frozen rule requires matching native M1 data starting exactly at its saved origin')
    coverage = manifest['coverage']['trade']
    count = (manifest['range'][1] - manifest['range'][0]) // 60
    if not coverage['complete'] or coverage['count'] != count or not 1 <= count <= 10000:
        raise ValueError('Frozen rule requires 1–10,000 contiguous full-origin candles; data was not trimmed')
    _, classification, _ = provenance(manifest)
    synthetic = manifest.get('metadata', {}).get('synthetic') is True
    if classification == 'real' and manifest['source'] == 'Bybit public API':
        # Existing general research classification is intentionally permissive.
        # This adapter additionally needs the exact request context and a clock
        # after the final close before labeling rows as historical REST closes.
        matching = False
        for record in manifest.get('provenance', []):
            if not isinstance(record, dict) or record.get('endpoint') != '/v5/market/kline':
                continue
            params = record.get('params', {})
            stamp = record.get('provider_time_ms')
            try:
                retrieved = datetime.fromisoformat(record.get('retrieved_at', '').replace('Z', '+00:00'))
                valid_clock = retrieved.tzinfo is not None and retrieved.timestamp() >= manifest['range'][1]
            except (ValueError, TypeError, AttributeError, OverflowError):
                valid_clock = False
            if (isinstance(params, dict) and params.get('category') == context['market']
                    and params.get('symbol') == context['symbol'] and params.get('interval') == '1'
                    and type(params.get('start')) is int and params['start'] <= manifest['range'][0] * 1000
                    and type(params.get('end')) is int and params['end'] >= manifest['range'][1] * 1000 - 1
                    and type(stamp) is int and stamp >= manifest['range'][1] * 1000 and valid_clock
                    and isinstance(record.get('response_sha256'), str)
                    and re.fullmatch('[a-f0-9]{64}', record['response_sha256'])):
                matching = True
        if not matching:
            raise ValueError('Frozen-rule history lacks matching Bybit M1 request provenance and confirmed-close clocks')
        confirmation = 'closed_rest'
    elif (classification == 'synthetic' and synthetic
          and manifest['metadata'].get('frozen_rule_source') == context['source']):
        confirmation = 'synthetic_closed'
    else:
        raise ValueError('Frozen-rule dataset source is unverified: use recorded Bybit REST provenance or an explicitly attributed synthetic fixture')
    if core.working_estimate(definition, count) + count * 1024 > 256 * 1024 * 1024:
        raise ValueError('Frozen-rule replay and schedule exceed the estimated 256 MiB working resource budget')
    return dict(snapshot=snapshot, confirmation=confirmation, count=count)


class FrozenSchedule:
    """Identity-bound, single-use close sequence; never accepts a user schedule."""
    def __init__(self, graph, profile, manifest, candles, research=None, cancel=None):
        from terminal import indicator_alerts as core
        admitted = check_admission(graph, profile, manifest, research)
        if admitted is None:
            raise ValueError('No frozen rule was admitted')
        node = frozen_nodes(graph)[0]
        self.node_id, self.snapshot = node['id'], node['params']['snapshot']
        self.context = admitted['snapshot']['definition']['context']
        self.dataset_id = manifest['id']
        self.index = 0
        tape = [dict(time=c.time, open=c.open, high=c.high, low=c.low, close=c.close, volume=c.volume,
                     confirmation=admitted['confirmation']) for c in candles]
        if len(tape) != admitted['count']:
            raise ValueError('Frozen-rule materialized tape differs from admitted coverage')
        result = core.replay(admitted['snapshot']['definition'], tape, cancel=cancel)
        self.rows = tuple((row['confirmed_at'], row['hit'], row['truth'], row['state_truth']) for row in result['rows'])
        self.candles = tuple((c.time, c.open, c.high, c.low, c.close, c.volume) for c in candles)

    def bind(self, node):
        if self.index or node['id'] != self.node_id or node['params']['snapshot'] != self.snapshot:
            raise ValueError('Frozen replay schedule does not match this untouched graph node')

    def check_execution(self, profile, candles, trade_start):
        if (trade_start is not None or profile.evaluation != 'closed' or profile.primary_minutes != 1
                or profile.execution_minutes != 1 or profile.gap_policy != 'reject'
                or profile.market != self.context['market'] or profile.symbol != self.context['symbol']
                or tuple((c.time, c.open, c.high, c.low, c.close, c.volume) for c in candles) != self.candles):
            raise ValueError('Execution differs from the admitted frozen-rule tape/profile')

    def consume(self, candle, time, complete):
        if not complete or self.index >= len(self.rows):
            raise ValueError('Frozen rule requires one complete admitted native close per evaluation')
        expected, hit, truth, state_truth = self.rows[self.index]
        if time != expected or (candle.time, candle.open, candle.high, candle.low, candle.close, candle.volume) != self.candles[self.index]:
            raise ValueError('Frozen-rule close was skipped, duplicated or changed')
        self.index += 1
        return dict(value=hit, condition_truth=truth, state_truth=state_truth)
