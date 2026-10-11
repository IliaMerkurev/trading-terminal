"""Original display-only transport for confirmed indicator annotations.

Formula events use candle opens. This boundary converts them to interval ends
once, without turning delayed pivot geometry into earlier availability.
"""
import math
from terminal.data import digest

CONTRACT = 'confirmed-vmc-events-v1'
FORMULA_CONTRACT = 'vmc-confirmed-core-v1'
KINDS = frozenset(('cross_up', 'cross_down', 'buy_dot', 'sell_dot',
    'regular_bullish', 'regular_bearish', 'hidden_bullish', 'hidden_bearish',
    'divergence_buy_dot', 'divergence_sell_dot', 'gold_buy_dot',
    'long_ema', 'short_ema', 'red_cross', 'blue_triangle', 'red_diamond',
    'blood_diamond', 'yellow_cross', 'bull_candle', 'swing_long', 'swing_short'))
OSCILLATORS = frozenset(('wt', 'wt_secondary', 'rsi', 'stoch'))


class EventCollector:
    """Retains only visible confirmation markers or intersecting connectors.

    Segment identity is the first raw open of a contiguous closed segment and
    survives checkpoint/window boundaries. No historical event log is retained
    in recursive checkpoints.
    """
    def __init__(self, instances, minutes, start, end):
        self.width = minutes * 60
        self.start, self.end = start, end
        self.items = {i['id']: {} for i in instances if i['type'].startswith('vmc_')}

    def observe(self, ident, events, segment):
        if ident not in self.items:
            return
        for raw in events:
            kind = raw.get('kind')
            if kind not in KINDS:
                raise ValueError('Invalid display event kind')
            stamps = {key: raw[key] for key in ('confirmed_at', 'pivot_time')}
            if 'previous_pivot_time' in raw:
                stamps['previous_pivot_time'] = raw['previous_pivot_time']
            if any(type(value) is not int or value < 0 for value in stamps.values()):
                raise ValueError('Invalid display event timestamp')
            confirmed, pivot = stamps['confirmed_at'], stamps['pivot_time']
            previous = stamps.get('previous_pivot_time')
            if pivot > confirmed or (previous is not None and previous >= pivot):
                raise ValueError('Invalid display event chronology')
            if confirmed > self.end:
                continue
            # Confirmation markers live at availability. A delayed connector
            # can intersect the viewport even when its predecessor is outside.
            marker_visible = self.start <= confirmed
            connector_visible = previous is not None and pivot >= self.start and previous <= self.end
            if not marker_visible and not connector_visible:
                continue
            if type(segment) is not int or segment < 0 or pivot < segment or (previous is not None and previous < segment):
                raise ValueError('Display event crosses a replay segment')
            item = dict(kind=kind, **{key: value+self.width for key, value in stamps.items()}, segment=segment)
            for key in ('value', 'previous_value'):
                if key == 'previous_value' and key not in raw:
                    continue
                value = raw.get(key)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('Non-finite display event value')
                item[key] = value
            oscillator = raw.get('oscillator')
            if oscillator is not None:
                if oscillator not in OSCILLATORS:
                    raise ValueError('Invalid display event oscillator')
                item['oscillator'] = oscillator
            item['id'] = digest([ident, kind, oscillator, pivot, confirmed, previous, segment])
            self.items[ident][item['id']] = item

    def result(self):
        return dict(version=1, contract=CONTRACT, horizon=self.end+self.width,
            instances={ident: sorted(events.values(), key=lambda e: (e['confirmed_at'], e['pivot_time'], e['id']))
                       for ident, events in self.items.items()})
