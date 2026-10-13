"""Versioned, presentation-only chart pane membership and relative sizing."""
import copy
import math
import re

AUXILIARY_KINDS = frozenset(('vmc_cipher_b', 'rsi', 'macd', 'volume', 'atr', 'stochastic', 'obv', 'roc', 'momentum', 'cci', 'williamsr', 'mfi', 'cmf', 'stddev', 'dmi', 'stochrsi', 'bbpercentb', 'bbwidth'))


def pane_unit(item):
    kind = item['type']
    if kind not in AUXILIARY_KINDS or kind == 'volume' and item.get('placement', 'overlay') != 'pane':
        return None
    return {'rsi': 'bounded100', 'stochastic': 'bounded100',
            'macd': 'price_difference', 'momentum': 'price_difference',
            'atr': 'price_distance', 'stddev': 'price_distance'}.get(kind, kind)


def validate_layout(layout, instances):
    """Every auxiliary instance belongs to exactly one compatible pane, even hidden."""
    def invalid():
        raise ValueError('Invalid or unsupported pane layout; use compatible panes and weights from 1 to 10000')

    if not isinstance(layout, dict) or set(layout) != {'version', 'price_weight', 'recorded_weight', 'panes'} or type(layout['version']) is not int or layout['version'] != 1 or not isinstance(layout['panes'], list):
        invalid()

    def weight(value):
        if type(value) not in (int, float) or not 1 <= value <= 10000 or not math.isfinite(value):
            invalid()

    weight(layout['price_weight'])
    weight(layout['recorded_weight'])
    expected = {item['id']: pane_unit(item) for item in instances if pane_unit(item) is not None}
    assigned, pane_ids = set(), set()
    for pane in layout['panes']:
        if not isinstance(pane, dict) or set(pane) != {'id', 'weight', 'instance_ids'}:
            invalid()
        ident = pane['id']
        if not isinstance(ident, str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,63}', ident) or ident in pane_ids or ident in ('price', 'recorded'):
            invalid()
        pane_ids.add(ident)
        weight(pane['weight'])
        members = pane['instance_ids']
        if not isinstance(members, list) or not members:
            invalid()
        unit = None
        for member in members:
            if not isinstance(member, str) or member not in expected or member in assigned:
                invalid()
            if unit is not None and expected[member] != unit:
                invalid()
            unit = expected[member]
            assigned.add(member)
    if assigned != set(expected):
        invalid()
    return copy.deepcopy(layout)
