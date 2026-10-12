"""Pure frozen local indicator conditions. No runtime, network or strategy dispatch.

All timestamps are UTC seconds. Input candle time is OPEN; evidence time is the
confirmed CLOSE. Existing display formulas are the only calculation engine.
"""
import copy
import hashlib
import json
import math

from terminal import display_formula_catalog as formulas
from terminal import display_indicators as display
from terminal import vumanchu_indicators as vmc
from terminal.chart_history import INTERVALS
from terminal.data import validate_symbol
from terminal.display_events import CONTRACT as EVENT_CONTRACT, FORMULA_CONTRACT
from terminal.market_sources import cache_market

CONTRACT = 'frozen-indicator-alert-v1'
MAX_DEFINITION_BYTES = 256 * 1024
MAX_ACTIVE_BYTES = 256 * 1024
MAX_CONDITIONS = 16
CLOSED = frozenset(('closed_rest', 'provider_confirmed', 'synthetic_closed'))
DIVERGENCES = frozenset(('regular_bullish', 'regular_bearish', 'hidden_bullish', 'hidden_bearish'))
OSCILLATOR_PORT = {'wt': 'wt2', 'wt_secondary': 'wt2', 'rsi': 'rsi', 'stoch': 'stoch_k'}
PREDICATES = frozenset(('above', 'below', 'cross_above', 'cross_below', 'divergence'))


def _json_value(value):
    if value is None or type(value) in (str, bool):
        return
    if type(value) is int:
        try:
            if math.isfinite(value):
                return
        except OverflowError:
            pass
        raise ValueError('Alert integers must fit finite numeric calculations')
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _json_value(child)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for child in value.values():
            _json_value(child)
        return
    raise ValueError('Alert documents require strict finite JSON values')


def encode(value, budget=MAX_DEFINITION_BYTES):
    try:
        _json_value(value)
        raw = json.dumps(value, allow_nan=False, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise ValueError('Alert documents require strict finite JSON values') from exc
    if len(raw) > budget:
        raise ValueError('Alert document exceeds its byte resource budget; content was not truncated')
    return raw


def decode(raw):
    if not isinstance(raw, (str, bytes)) or len(raw.encode('utf-8') if isinstance(raw, str) else raw) > MAX_DEFINITION_BYTES:
        raise ValueError('Alert document exceeds its byte resource budget')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key in alert document')
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        encode(value)
        return value
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise ValueError('Invalid strict JSON alert document') from exc


def _keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError('Invalid ' + label)


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63-1:
        raise ValueError('Invalid alert integer')


def _number(value):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('Alert numbers must be finite')
    return int(value) if float(value).is_integer() else value


def port_units(kind):
    """Only causal numeric ports; projected geometry is not an alert input."""
    if kind in vmc.FIELDS:
        result = dict.fromkeys(vmc.ports(kind), 'price')
        if kind == 'vmc_cipher_b':
            result = dict.fromkeys(vmc.ports(kind), 'vmc_oscillator')
            result.update(rsi='bounded_0_100', stoch_k='bounded_0_100', stoch_d='bounded_0_100', flow='vmc_body_flow')
        return result
    if kind == 'ichimoku':
        return {'tenkan': 'price', 'kijun': 'price'}
    if kind == 'supertrend':
        return {'up': 'price', 'down': 'price', 'direction': 'direction'}
    if kind in formulas.ALL_FIELDS:
        unit = ('price_difference' if kind == 'momentum' else 'price_distance' if kind == 'stddev'
                else 'bounded_0_100' if kind in ('mfi', 'dmi', 'stochrsi')
                else 'signed_percent' if kind == 'roc' else 'bounded_minus100_0' if kind == 'williamsr'
                else 'width_percent' if kind == 'bbwidth' else 'flow_ratio' if kind == 'cmf' else 'band_ratio' if kind == 'bbpercentb' else 'cci' if kind == 'cci' else 'price')
        return dict.fromkeys(formulas.ports(kind), unit)
    if kind == 'bb':
        return dict.fromkeys(('upper', 'middle', 'lower'), 'price')
    if kind == 'macd':
        return dict.fromkeys(('macd', 'signal', 'histogram'), 'price_difference')
    if kind == 'stochastic':
        return dict.fromkeys(('k', 'd'), 'bounded_0_100')
    if kind in display.FIELDS:
        return {'value': 'bounded_0_100' if kind == 'rsi' else 'volume_native' if kind in ('volume', 'obv') else 'price_distance' if kind == 'atr' else 'price'}
    raise ValueError('Unsupported alert indicator')


def _formula_contract(item):
    metadata = vmc.metadata(item) if item['type'] in vmc.FIELDS else formulas.metadata(item) if item['type'] in formulas.ALL_FIELDS else {}
    return dict(display=display.CONTRACT, vmc=FORMULA_CONTRACT if item['type'] in vmc.FIELDS else None,
                metadata_sha256=hashlib.sha256(encode(metadata)).hexdigest())


def _instance(item):
    valid = display.validate_instances([dict(id=item['id'], type=item['type'], params=item['params'], color='#ffffff', visible=True)])[0]
    valid['params'] = {key: _number(value) if type(value) in (int, float) else value for key, value in valid['params'].items()}
    return dict(id=valid['id'], type=valid['type'], params=valid['params'], contract=_formula_contract(valid))


def _operand(value, instances):
    if type(value) is not dict:
        raise ValueError('Invalid alert operand')
    kind = value.get('kind')
    if kind == 'series':
        _keys(value, 'kind instance_id port', 'series operand')
        item = instances.get(value['instance_id']) if type(value['instance_id']) is str else None
        if not item or type(value['port']) is not str or value['port'] not in port_units(item['type']):
            raise ValueError('Unknown or noncausal indicator port')
        return copy.deepcopy(value), port_units(item['type'])[value['port']]
    if kind == 'price':
        _keys(value, 'kind port', 'raw price operand')
        if value['port'] not in ('open', 'high', 'low', 'close'):
            raise ValueError('Invalid raw price port')
        return copy.deepcopy(value), 'price'
    if kind == 'level':
        _keys(value, 'kind value unit', 'level operand')
        if type(value['unit']) is not str:
            raise ValueError('Invalid level unit')
        return dict(value, value=_number(value['value'])), value['unit']
    raise ValueError('Unsupported alert operand')


def _conditions(conditions, instances):
    if type(conditions) is not list or not 1 <= len(conditions) <= MAX_CONDITIONS:
        raise ValueError('Use 1 to 16 conditions per alert rule')
    result, used = [], set()
    for condition in conditions:
        predicate = condition.get('predicate') if type(condition) is dict else None
        if type(predicate) is not str or predicate not in PREDICATES:
            raise ValueError('Unsupported alert predicate')
        if predicate == 'divergence':
            _keys(condition, 'predicate instance_id event_kind oscillator', 'divergence condition')
            ident = condition['instance_id']
            if type(ident) is not str or ident not in instances or instances[ident]['type'] != 'vmc_cipher_b':
                raise ValueError('Confirmed divergence requires frozen VMC B')
            if type(condition['event_kind']) is not str or type(condition['oscillator']) is not str or condition['event_kind'] not in DIVERGENCES or condition['oscillator'] not in OSCILLATOR_PORT:
                raise ValueError('Unsupported confirmed divergence')
            used.add(ident)
            result.append(copy.deepcopy(condition))
        else:
            _keys(condition, 'predicate left right', 'numeric condition')
            left, left_unit = _operand(condition['left'], instances)
            right, right_unit = _operand(condition['right'], instances)
            if left['kind'] == 'level' or left_unit != right_unit:
                raise ValueError('Alert operands require compatible units and a nonconstant left input')
            if predicate in ('above', 'below') and right['kind'] != 'level':
                raise ValueError('Above/below state conditions require a level')
            for operand in (left, right):
                if operand['kind'] == 'series':
                    used.add(operand['instance_id'])
            result.append(dict(predicate=predicate, left=left, right=right))
    return result, used


def freeze_rule(settings, source, market, symbol, minutes, conditions, combine='ALL'):
    """Capture only dependencies from applied settings; do not consult them later."""
    encode(settings, 64 * 1024 * 1024)
    instances = display.validate_instances(settings['instances'])
    _integer(settings['revision'])
    if type(minutes) is not int or minutes not in INTERVALS:
        raise ValueError('Unsupported native interval')
    origin = settings.get('origins', {}).get(str(minutes))
    if origin is None:
        raise ValueError('A saved calculation origin is required before freezing an alert')
    frozen = {item['id']: _instance(item) for item in instances}
    normalized, used = _conditions(conditions, frozen)
    definition = dict(version=1, contract=CONTRACT, context=dict(source=source, market=market, symbol=symbol, minutes=minutes),
        settings_revision=settings['revision'], origin=copy.deepcopy(origin), event_contract=EVENT_CONTRACT,
        combine=combine, instances=[frozen[ident] for ident in sorted(used)], conditions=normalized)
    return validate_definition(definition)


def validate_definition(value):
    """Return an independent normalized snapshot; never accept executable content."""
    encode(value)
    _keys(value, 'version contract context settings_revision origin event_contract combine instances conditions', 'frozen rule')
    if type(value['version']) is not int or value['version'] != 1 or value['contract'] != CONTRACT or value['event_contract'] != EVENT_CONTRACT:
        raise ValueError('Unsupported frozen alert version or formula contract')
    _keys(value['context'], 'source market symbol minutes', 'alert context')
    context = value['context']
    cache_market(context['market'], context['source'])
    validate_symbol(context['symbol'])
    minutes = context['minutes']
    if type(minutes) is not int or minutes not in INTERVALS:
        raise ValueError('Unsupported native interval')
    _integer(value['settings_revision'])
    _keys(value['origin'], 'time generation contract', 'calculation origin')
    origin = value['origin']
    _integer(origin['time']); _integer(origin['generation'], 1)
    if origin['contract'] != display.CONTRACT or origin['time'] % (minutes * 60):
        raise ValueError('Unsupported or unaligned calculation origin')
    if value['combine'] not in ('ALL', 'ANY') or type(value['instances']) is not list:
        raise ValueError('Invalid alert combination or instances')
    instances = {}
    for item in value['instances']:
        _keys(item, 'id type params contract', 'frozen indicator')
        normalized = _instance(item)
        if item['contract'] != normalized['contract']:
            raise ValueError('Unsupported frozen indicator formula contract')
        if normalized['id'] in instances:
            raise ValueError('Duplicate frozen indicator ID')
        instances[normalized['id']] = normalized
    conditions, used = _conditions(value['conditions'], instances)
    if used != set(instances):
        raise ValueError('Frozen rule contains unused indicator dependencies')
    formulas.validate_timeframe(list(instances.values()), minutes)
    result = copy.deepcopy(value)
    result.update(instances=[instances[ident] for ident in sorted(instances)], conditions=conditions)
    encode(result)
    return result


def definition_hash(definition):
    return hashlib.sha256(encode(validate_definition(definition))).hexdigest()


def validate_active_set(definitions):
    """Runtime must check the complete candidate set before enabling any member."""
    normalized, size = [], 2
    for item in definitions:
        valid = validate_definition(item)
        size += len(encode(valid)) + bool(normalized)
        if size > MAX_ACTIVE_BYTES:
            raise ValueError('Active alerts exceed the 256 KiB byte resource budget; nothing was truncated')
        normalized.append(valid)
    return normalized


def changed_dependencies(definition, settings):
    """Missing/hidden/moved originals do not change a frozen calculation."""
    definition = validate_definition(definition)
    current = {item['id']: _instance(item) for item in display.validate_instances(settings['instances'])}
    return [item['id'] for item in definition['instances'] if item['id'] in current and current[item['id']] != item]


def combine_truth(values, combine):
    """Kleene three-state logic: false dominates ALL; true dominates ANY."""
    if combine not in ('ALL', 'ANY') or any(value is not None and type(value) is not bool for value in values):
        raise ValueError('Invalid alert truth values')
    if combine == 'ALL':
        return False if False in values else None if None in values else True
    return True if True in values else None if None in values else False


def transition(conditions, combine, previous_truth=None, previous_state_truth=None):
    """Pulses are per-close; state edges require consecutive known false/true."""
    truth = combine_truth([item['truth'] for item in conditions], combine)
    states = [item['truth'] for item in conditions if item['kind'] == 'state']
    pulses = [item['truth'] for item in conditions if item['kind'] == 'impulse']
    state_truth = combine_truth(states, combine) if states else None
    if not pulses:
        hit = previous_truth is False and truth is True
    elif combine == 'ALL':
        hit = truth is True
    else:
        hit = any(value is True for value in pulses) or (previous_state_truth is False and state_truth is True)
    return dict(truth=truth, state_truth=state_truth, hit=hit)


def _tape(candles, definition):
    if type(candles) is not list or not candles or len(candles) > display.MAX_BARS:
        raise ValueError('Replay requires 1 to 10,000 full-origin raw candles')
    width = definition['context']['minutes'] * 60
    expected = definition['origin']['time']
    for row in candles:
        if type(row) is not dict or type(row.get('time')) is not int or row['time'] != expected:
            raise ValueError('Saved calculation origin is missing or raw candle coverage has a gap')
        _integer(row['time']); _integer(row['time'] + width, 1)
        if type(row.get('confirmation')) is not str or row['confirmation'] not in CLOSED or row.get('conflict'):
            raise ValueError('Alert replay requires confirmed, nonconflicting raw candles')
        for port in ('open', 'high', 'low', 'close'):
            _number(row.get(port))
        if row['low'] > min(row['open'], row['close']) or row['high'] < max(row['open'], row['close']) or row['low'] > row['high']:
            raise ValueError('Invalid raw OHLC geometry')
        if row.get('volume') is not None and _number(row['volume']) < 0:
            raise ValueError('Invalid raw candle volume')
        expected += width


def working_estimate(definition, count, *, include_values=False):
    # Includes the row/condition dictionaries and copied hit evidence, beyond
    # the display engine's separate formula-array preflight. No silent trimming.
    estimated = count * (4096 + 4096 * len(definition['conditions']))
    for item in definition['instances']:
        ports = len(port_units(item['type']))
        event_slots = 12 if item['type'] == 'vmc_cipher_b' else 8 if item['type'] == 'vmc_cipher_a' else 1 if item['type'] == 'vmc_swing' else 0
        estimated += count * (ports * 80 + event_slots * 1024)
        estimated += 4096 + sum(value * 48 for key, value in item['params'].items()
            if type(value) is int and key not in ('anchor', 'flow_multiplier', 'flow_offset'))
    if include_values:
        estimated += count * (2048 + sum(512 + 160 * len(port_units(item['type'])) for item in definition['instances']))
    if estimated > 256 * 1024 * 1024:
        raise ValueError('Alert evidence exceeds the estimated 256 MiB working resource budget')
    return estimated


def replay(definition, candles, cancel=None, *, include_values=False):
    """Replay one frozen full-origin tape, returning every close and hit evidence.

    No observed_at is fabricated here. A runtime must seed its arm baseline from
    the last row without delivering historical hits, then accept only observed
    subsequent native closes. A historical scan consumes the same rows unchanged.
    """
    if type(include_values) is not bool:
        raise ValueError('Invalid replay value snapshot option')
    definition = validate_definition(definition)
    _tape(candles, definition)
    working_estimate(definition, len(candles), include_values=include_values)
    minutes = definition['context']['minutes']
    instances = [dict(id=item['id'], type=item['type'], params=item['params'], visible=True, color='#ffffff') for item in definition['instances']]
    result = display.calculate(candles, instances, minutes, candles[0]['time'], candles[-1]['time'], cancel)
    positions = {stamp: index for index, stamp in enumerate(result['times'])}
    events = {}
    for ident, items in result['indicator_events']['instances'].items():
        for item in items:
            events.setdefault((ident, item['confirmed_at']), []).append(item)
    definition_digest = definition_hash(definition)
    rows, hits = [], []
    previous_truth = previous_state_truth = None

    def value(operand, index):
        if index < 0:
            return None
        if operand['kind'] == 'level':
            return operand['value']
        if operand['kind'] == 'price':
            return candles[index][operand['port']]
        position = positions[candles[index]['time'] + minutes * 60]
        return result['columns'][operand['instance_id']][operand['port']][position]

    for index, candle in enumerate(candles):
        if index % 32 == 0 and cancel and cancel.is_set():
            raise InterruptedError('Alert replay cancelled')
        confirmed = candle['time'] + minutes * 60
        evidence = []
        for condition_index, condition in enumerate(definition['conditions']):
            predicate = condition['predicate']
            item = dict(index=condition_index, predicate=predicate, kind='state' if predicate in ('above', 'below') else 'impulse')
            if predicate == 'divergence':
                matches = [e for e in events.get((condition['instance_id'], confirmed), [])
                           if e['kind'] == condition['event_kind'] and e.get('oscillator') == condition['oscillator']]
                port = OSCILLATOR_PORT[condition['oscillator']]
                current = result['columns'][condition['instance_id']][port][positions[confirmed]]
                # An unavailable oscillator is not evidence that no impulse occurred.
                truth = bool(matches) if matches or current is not None else None
                item.update(truth=truth, value=current, events=copy.deepcopy(matches), reason='confirmed_divergence' if matches else 'no_confirmed_divergence' if truth is False else 'warmup_or_missing_value')
            else:
                left, right = value(condition['left'], index), value(condition['right'], index)
                prior_left, prior_right = value(condition['left'], index-1), value(condition['right'], index-1)
                known = left is not None and right is not None
                if predicate.startswith('cross_'):
                    known = known and prior_left is not None and prior_right is not None
                truth = None if not known else (left > right if predicate == 'above' else left < right if predicate == 'below'
                         else prior_left <= prior_right and left > right if predicate == 'cross_above'
                         else prior_left >= prior_right and left < right)
                item.update(truth=truth, left=left, right=right, previous_left=prior_left, previous_right=prior_right,
                            reason='warmup_or_missing_value' if truth is None else 'condition_true' if truth else 'condition_false')
            evidence.append(item)
        state = transition(evidence, definition['combine'], previous_truth, previous_state_truth)
        row = dict(raw_open_time=candle['time'], confirmed_at=confirmed, conditions=evidence, **state)
        if include_values:
            row['values'] = {ident: {port: values[positions[confirmed]] for port, values in ports.items()}
                             for ident, ports in result['columns'].items()}
        rows.append(row)
        if row['hit']:
            hits.append(copy.deepcopy(row))
        previous_truth, previous_state_truth = row['truth'], row['state_truth']
    return dict(version=1, definition_hash=definition_digest, rows=rows, events=hits)
