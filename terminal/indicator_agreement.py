"""Pure, versioned description of existing indicator outputs at one raw close.

No formula calculation, providers, strategy dispatch, persistence or UI gating.
Callers must authenticate the source/revision/origin/window/generation/freshness
of the supplied snapshot before using these results. See ADR 0057.
"""
import copy
from fractions import Fraction
import hashlib
from importlib.resources import files
import json
import math
import struct

_MANIFEST = json.loads(files('terminal').joinpath('indicator_agreement_v1.json').read_text())
MANIFEST_HASH = hashlib.sha256(json.dumps(_MANIFEST, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
VERSION = _MANIFEST['version']
WEIGHT_VERSION = _MANIFEST['weight_version']
_DIRECTIONS = tuple(_MANIFEST['directions'])
_GROUPS = tuple(_MANIFEST['groups'])
_CLOSED = frozenset(_MANIFEST['raw_contract']['confirmed'])
_SAFE_INTEGER = 2**53 - 1


def manifest():
    """Return a detached manifest; callers cannot change evaluator semantics."""
    return copy.deepcopy(_MANIFEST)


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _integer(value):
    return _finite(value) and int(value) == value and abs(value) <= _SAFE_INTEGER


def _normal(value):
    if value is None or type(value) in (str, bool):
        return value
    if _finite(value) and abs(value) <= _SAFE_INTEGER:
        return int(value) if int(value) == value else value
    raise ValueError('Agreement parameters must be finite JSON scalars with safe numbers')


def normalize_params(params):
    if type(params) is not dict or not all(type(key) is str for key in params):
        raise ValueError('Agreement parameters must be an object')
    return {key: _normal(params[key]) for key in sorted(params)}


def variant_key(kind, params):
    """A stable cross-language identity; 20, 20.0 and -0/0 normalize equally."""
    normalized = normalize_params(params)
    tokens = []
    for key, value in normalized.items():
        token = ['number', struct.pack('>d', float(value)).hex()] if type(value) in (int, float) else [type(value).__name__ if value is not None else 'null', value]
        # Use JSON names rather than language-specific scalar type names.
        if type(value) is str:
            token[0] = 'string'
        if type(value) is bool:
            token[0] = 'boolean'
        tokens.append([key, token])
    return json.dumps([kind, tokens], ensure_ascii=False, separators=(',', ':'))


def _check_params(kind, params, rule):
    if rule.get('classification') != 'directional':
        return
    if set(params) != set(rule['parameters']):
        raise ValueError('Agreement directional parameters do not match the manifest')
    for key, value in params.items():
        if key in ('step', 'max'):
            if not _finite(value) or not 0 < value <= 1:
                raise ValueError('Invalid SAR parameter')
        elif key in ('deviations', 'multiplier'):
            if not _finite(value) or not 0 < value <= 10:
                raise ValueError('Invalid band parameter')
        elif key == 'mode':
            if not _integer(value) or value not in (0, 1):
                raise ValueError('Invalid VWAP mode')
        elif key == 'anchor':
            if not _integer(value) or not 0 <= value <= 253402300799:
                raise ValueError('Invalid VWAP anchor')
        elif not _integer(value) or not 1 <= value <= 1000:
            raise ValueError('Invalid indicator period')
    if kind == 'sar' and params['step'] > params['max']:
        raise ValueError('Invalid SAR step')
    if kind == 'vwap' and params['mode'] == 0 and params['anchor'] != 0:
        raise ValueError('Invalid day VWAP anchor')
    if kind == 'macd' and params['fast'] >= params['slow']:
        raise ValueError('Invalid MACD periods')


def _mean(rows):
    return tuple(sum((row[i] for row in rows), Fraction()) / len(rows) for i in range(3))


def _vote(status):
    return tuple(Fraction(int(status == direction)) for direction in _DIRECTIONS)


def _distribution(fractions):
    if fractions is None:
        return None
    scaled = [value * _MANIFEST['rounding']['total'] for value in fractions]
    rounded = [value.numerator // value.denominator for value in scaled]
    order = sorted(range(3), key=lambda i: (-(scaled[i] - rounded[i]), i))
    for i in order[:100 - sum(rounded)]:
        rounded[i] += 1
    return dict(fractions={d: float(v) for d, v in zip(_DIRECTIONS, fractions)},
                exact={d: [str(v.numerator), str(v.denominator)] for d, v in zip(_DIRECTIONS, fractions)},
                percentages=dict(zip(_DIRECTIONS, rounded)))


class PreparedAgreement:
    """Detached, indexed snapshot reusable for many exact-close evaluations.

    Preparation is linear in raw rows and output cells. Flat guard run lengths
    make each member assessment constant-time, independent of period or prefix.
    This class never replays indicator formulas and does not cache result rows.
    """
    def __init__(self, snapshot):
        width = snapshot.get('interval_seconds')
        if not _integer(width) or width <= 0:
            raise ValueError('Agreement interval must be positive integer seconds')
        self.width = int(width)
        self.members = []
        seen = set()
        for item in snapshot['instances']:
            if type(item) is not dict or type(item.get('id')) is not str or not item['id'] or item['id'] in seen or type(item.get('type')) is not str or type(item.get('visible')) is not bool:
                raise ValueError('Agreement members require unique IDs, type and explicit visibility')
            seen.add(item['id'])
            params = normalize_params(item.get('params'))
            kind = item['type']
            rule = _MANIFEST['rules'].get(kind, dict(classification='unsupported', reason='Unknown indicator type'))
            _check_params(kind, params, rule)
            if kind == 'vwap' and params['anchor'] % self.width:
                raise ValueError('VWAP anchor must align to the raw interval')
            self.members.append(dict(id=item['id'], type=kind, params=params, visible=item['visible'],
                                     variant_key=variant_key(kind, params), rule=rule))
        self.members.sort(key=lambda item: (item['type'], item['variant_key'], item['id']))
        self.raw = {}
        previous = None
        runs = dict(closes=0, flat_closes=0, ranges=0, flat_ranges=0)
        for original in snapshot['candles']:
            row = copy.deepcopy(original)
            stamp = row.get('time')
            if not _integer(stamp) or stamp < 0 or stamp % self.width or (previous is not None and stamp <= previous['time']):
                raise ValueError('Agreement raw times must be aligned and strictly increasing')
            contiguous = previous is not None and stamp == previous['time'] + self.width
            closed = (row.get('confirmation') in _CLOSED and row.get('conflict', False) is False
                      and all(_finite(row.get(key)) for key in ('open', 'high', 'low', 'close'))
                      and row['low'] <= min(row['open'], row['close']) <= max(row['open'], row['close']) <= row['high'])
            close_ok = closed and _finite(row.get('close'))
            range_ok = closed and _finite(row.get('high')) and _finite(row.get('low')) and row['high'] >= row['low']
            runs['closes'] = (runs['closes'] if contiguous else 0) + 1 if close_ok else 0
            runs['flat_closes'] = (runs['flat_closes'] if contiguous and previous.get('close') == row.get('close') else 0) + 1 if close_ok else 0
            flat_range = range_ok and row['high'] == row['low']
            runs['ranges'] = (runs['ranges'] if contiguous else 0) + 1 if range_ok else 0
            runs['flat_ranges'] = (runs['flat_ranges'] if contiguous and previous.get('high') == row.get('high') else 0) + 1 if flat_range else 0
            self.raw[stamp + self.width] = dict(row=row, runs=dict(runs), closed=closed)
            previous = row
        display = snapshot['display']
        self.times = {}
        previous_time = None
        for index, stamp in enumerate(display['times']):
            if not _integer(stamp) or stamp < self.width or stamp % self.width or (previous_time is not None and stamp <= previous_time):
                raise ValueError('Agreement output times must be aligned and strictly increasing')
            self.times[stamp] = index
            previous_time = stamp
        self.columns = copy.deepcopy(display['columns'])

    def _value(self, ident, port, close_time):
        index = self.times.get(close_time)
        column = self.columns.get(ident, {}).get(port, [])
        value = column[index] if index is not None and type(column) is list and index < len(column) else None
        return value if _finite(value) else None

    def _assess(self, item, close_time):
        rule, params = item['rule'], item['params']
        result = dict(id=item['id'], type=item['type'], params=dict(params), variant_key=item['variant_key'],
                      group=rule.get('group'), status='unavailable', reason='target_missing', values={})
        if not item['visible']:
            return dict(result, status='hidden', reason='Hidden instances do not vote')
        if rule['classification'] != 'directional':
            return dict(result, status=rule['classification'], reason=rule['reason'])
        current = self.raw.get(close_time)
        if current is None:
            return result
        if not current['closed'] or not _finite(current['row'].get('close')):
            return dict(result, reason='target_not_confirmed_or_invalid')
        values = {port: self._value(item['id'], port, close_time) for port in rule['ports']}
        if rule['rule'] == 'adx_di' and values['adx'] is not None and values['adx'] < rule['adx_neutral_below']:
            return dict(result, status='neutral', reason='adx_below_threshold', values={'adx': values['adx']})
        result['values'] = values
        if any(value is None for value in values.values()):
            return dict(result, reason='output_unavailable_at_requested_close')
        guard = rule.get('guard')
        if guard in ('flat_closes', 'flat_range', 'flat_smoothed_range'):
            length = params['period'] + (1 if guard == 'flat_closes' else params['smooth'] - 1 if guard == 'flat_smoothed_range' else 0)
            category = 'closes' if guard == 'flat_closes' else 'ranges'
            result['values'] = dict(values, guard_bars=length)
            if current['runs'][category] < length:
                return dict(result, reason='raw_guard_unavailable')
            if current['runs']['flat_' + category] >= length:
                return dict(result, status='neutral', reason='flat_raw_window')
        mode = rule['rule']
        if mode == 'raw_close_compare':
            left, right = current['row']['close'], values[rule['ports'][0]]
            result['values'] = dict(values, raw_close=left)
            status = 'up' if left > right else 'down' if left < right else 'neutral'
        elif mode == 'signed_direction':
            value = values[rule['ports'][0]]
            if value not in (rule['up'], rule['down']):
                return dict(result, reason='invalid_direction')
            status = 'up' if value == rule['up'] else 'down'
        elif mode == 'adx_di':
            status = 'up' if values['plus_di'] > values['minus_di'] else 'down' if values['plus_di'] < values['minus_di'] else 'neutral'
        elif mode == 'adjacent_change':
            previous = self.raw.get(close_time - self.width)
            before = self._value(item['id'], rule['ports'][0], close_time - self.width)
            if previous is None or not previous['closed'] or not _finite(previous['row'].get('close')) or before is None:
                return dict(result, reason='adjacent_confirmed_output_unavailable')
            result['values'] = dict(values, previous=before)
            value = values[rule['ports'][0]]
            status = 'up' if value > before else 'down' if value < before else 'neutral'
        else:
            value = values[rule['ports'][0]]
            status = 'up' if value > rule['upper'] else 'down' if value < rule['lower'] else 'neutral'
        return dict(result, status=status, reason=mode)

    def evaluate(self, close_time):
        if not _integer(close_time) or close_time < self.width or close_time % self.width:
            raise ValueError('Agreement close must align exactly to the raw interval')
        members = [self._assess(item, close_time) for item in self.members]
        variant_members = {}
        for member in members:
            if member['group'] is not None and member['status'] != 'hidden':
                variant_members.setdefault(member['variant_key'], []).append(member)
        variants = []
        by_type = {}
        for key, copies in variant_members.items():
            first = copies[0]
            same = all((item['status'], item['reason'], item['values']) == (first['status'], first['reason'], first['values']) for item in copies)
            status = first['status'] if same else 'unavailable'
            variant = dict(key=key, type=first['type'], group=first['group'], params=first['params'],
                           member_ids=[item['id'] for item in copies], status=status,
                           reason=first['reason'] if same else 'duplicate_variant_conflict', values=first['values'] if same else {})
            variants.append(variant)
            by_type.setdefault(first['type'], []).append(variant)
        types, type_fractions = [], {}
        for kind, rows in by_type.items():
            available = [row for row in rows if row['status'] in _DIRECTIONS]
            fractions = _mean([_vote(row['status']) for row in available]) if available else None
            type_fractions[kind] = fractions
            types.append(dict(type=kind, group=rows[0]['group'], available_variants=len(available), total_variants=len(rows),
                              fully_covered=len(available) == len(rows), variant_keys=[row['key'] for row in rows], distribution=_distribution(fractions)))
        groups, group_fractions = [], {}
        for group in _GROUPS:
            rows = [row for row in types if row['group'] == group]
            available = [type_fractions[row['type']] for row in rows if type_fractions[row['type']] is not None]
            fractions = _mean(available) if available else None
            group_fractions[group] = fractions
            groups.append(dict(group=group, available_types=len(available), total_types=len(rows),
                               types=[row['type'] for row in rows], distribution=_distribution(fractions)))
        available_groups = [row for row in group_fractions.values() if row is not None]
        full = sum(row['fully_covered'] for row in types)
        minimum = Fraction(*_MANIFEST['coverage']['minimum_fully_covered_type_fraction'])
        reasons = []
        if len(available_groups) < _MANIFEST['coverage']['minimum_available_groups']:
            reasons.append('insufficient_available_groups')
        if not types or Fraction(full, len(types)) < minimum:
            reasons.append('insufficient_fully_covered_types')
        overall = _mean(available_groups) if not reasons else None
        conflict = any(row[0] > Fraction(1, 2) for row in available_groups) and any(row[1] > Fraction(1, 2) for row in available_groups)
        return dict(version=VERSION, weight_version=WEIGHT_VERSION, manifest_hash=MANIFEST_HASH,
                    close_time=close_time, open_time=close_time-self.width, interval_seconds=self.width,
                    state='available' if overall is not None else 'unavailable', reasons=reasons,
                    overall=_distribution(overall), groups=groups, types=types, variants=variants, members=members,
                    coverage=dict(fully_covered_types=full, available_types=sum(row['distribution'] is not None for row in types),
                                  total_types=len(types), available_variants=sum(row['status'] in _DIRECTIONS for row in variants),
                                  total_variants=len(variants), available_groups=len(available_groups)),
                    exclusions={status: [row['id'] for row in members if row['status'] == status] for status in ('hidden', 'context', 'unsupported', 'unavailable')},
                    group_conflict=conflict)


def prepare_agreement(snapshot):
    return PreparedAgreement(snapshot)


def evaluate_agreement(snapshot):
    return prepare_agreement(snapshot).evaluate(snapshot['close_time'])


def threshold_evidence(result, direction, threshold, required_groups=()):
    """Pure evidence only, not an alert definition or transition evaluator."""
    if direction not in ('up', 'down') or not _finite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Agreement threshold requires up/down and a finite fraction from 0 to 1')
    if len(set(required_groups)) != len(required_groups) or any(group not in _GROUPS for group in required_groups):
        raise ValueError('Agreement required groups must be distinct known groups')
    if result.get('version') != VERSION or result.get('weight_version') != WEIGHT_VERSION or result.get('manifest_hash') != MANIFEST_HASH:
        raise ValueError('Agreement result contract mismatch')
    exact_threshold = Fraction(str(threshold))
    def fraction(distribution):
        return Fraction(*map(int, distribution['exact'][direction])) if distribution is not None else None
    overall = fraction(result['overall'])
    groups = {row['group']: fraction(row['distribution']) for row in result['groups']}
    overall_pass = overall >= exact_threshold if overall is not None else None
    group_pass = {group: groups[group] > Fraction(1, 2) if groups[group] is not None else None for group in required_groups}
    unavailable = overall_pass is None or any(value is None for value in group_pass.values())
    return dict(direction=direction, threshold=threshold, required_groups=list(required_groups), overall_pass=overall_pass,
                group_pass=group_pass, truth=None if unavailable else overall_pass and all(group_pass.values()),
                reason='agreement_unavailable' if unavailable else 'exact_threshold_and_group_majorities')
