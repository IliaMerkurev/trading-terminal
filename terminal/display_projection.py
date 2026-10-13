"""Bounded display-only Ichimoku geometry; never adds rows to the price domain.

All timestamps are UTC interval ends. Information becomes available at
computed_at, including Chikou values drawn at an earlier plotted_at timestamp.
The request start/end are inclusive candle OPEN timestamps; horizon is the end
label of the requested final interval, not a wall-clock confirmation assertion.
source_logical uses the exact raw_times domain (and may be negative for left
support). Each per-instance array has equal length, bounded by 1800 + 100.
"""
from bisect import bisect_left, bisect_right
import math

CONTRACT = 'ichimoku-raw-ordinal-v1'
MAX_DISPLACEMENT = 100


class ProjectionCollector:
    def __init__(self, candles, instances, minutes, start, end):
        self.width = minutes * 60
        self.start, self.end = start, end
        self.times = sorted({r['time'] for r in candles if r['time'] <= end})
        self.positions = {stamp: index for index, stamp in enumerate(self.times)}
        self.first = bisect_left(self.times, start)
        self.last = bisect_right(self.times, end) - 1
        self.items = {i['id']: dict(displacement=i['params']['displacement'], **{key: [] for key in (
            'source_logical', 'computed_at', 'segment', 'senkou_a', 'senkou_b', 'chikou',
            'senkou_plotted_at', 'chikou_plotted_at', 'senkou_estimated')})
            for i in instances if i['type'] == 'ichimoku'}

    def observe(self, ident, stamp, segment, values):
        item = self.items[ident]
        index = self.positions[stamp]
        d = item['displacement']
        if self.first > self.last or not self.first-d <= index <= self.last:
            return
        forward, backward = index+d, index-d
        ahead = forward > self.last
        forward_time = (self.times[self.last] + (forward-self.last)*self.width if ahead else self.times[forward]) + self.width
        backward_time = self.times[backward]+self.width if backward >= self.first else None
        a, b, c = values['senkou_a'], values['senkou_b'], values['chikou'] if backward_time is not None else None
        if a is None and b is None and c is None:
            return
        if any(value is not None and not math.isfinite(value) for value in (a, b, c)):
            raise ValueError('Non-finite display indicator value')
        row = dict(source_logical=index-self.first, computed_at=stamp+self.width, segment=segment,
                   senkou_a=a, senkou_b=b, chikou=c, senkou_plotted_at=forward_time,
                   chikou_plotted_at=backward_time, senkou_estimated=ahead)
        for key, value in row.items():
            item[key].append(value)

    def result(self):
        return dict(version=1, contract=CONTRACT, raw_times=[stamp+self.width for stamp in self.times[self.first:self.last+1]],
                    horizon=self.end+self.width, instances=self.items)
