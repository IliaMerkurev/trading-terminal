"""UTC minute aggregation without access to unobserved bars."""
from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class Candle:
    time: int  # UTC interval start, seconds
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        values = (self.open, self.high, self.low, self.close, self.volume)
        if not all(isfinite(v) for v in values) or min(values[:4]) <= 0 or self.volume < 0:
            raise ValueError("Invalid OHLCV values")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError("Inconsistent OHLC range")


class PartialBars:
    """Only complete UTC-aligned primary bars enter closed history.

    Every update is an observed minute CLOSE. Gaps reset the forming candle;
    an incomplete primary interval is not silently accepted as complete.
    """
    def __init__(self, minutes=60, history_limit=None):
        if minutes not in (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440):
            raise ValueError("Unsupported primary timeframe")
        self.minutes = minutes
        if history_limit is not None and (type(history_limit) is not int or history_limit < 1):
            raise ValueError("History limit must be positive")
        self.history_limit = history_limit
        self.closed = []
        self.current = None
        self.last_time = None
        self.count = 0
        self.gaps = []

    def update(self, bar):
        if bar.time % 60 or (self.last_time is not None and bar.time <= self.last_time):
            raise ValueError("Minute candles must be UTC-aligned and strictly increasing")
        gap = self.last_time is not None and bar.time != self.last_time + 60
        if gap:
            self.gaps.append((self.last_time + 60, bar.time))
            if self.history_limit is not None:
                self.gaps = self.gaps[-self.history_limit:]
        bucket = bar.time // (self.minutes * 60) * self.minutes * 60
        if self.current is None or self.current.time != bucket or gap:
            self.current = replace(bar, time=bucket)
            self.count = 1 if bar.time == bucket else 0
        else:
            c = self.current
            self.current = Candle(bucket, c.open, max(c.high, bar.high), min(c.low, bar.low),
                                  bar.close, c.volume + bar.volume)
            if self.count:
                self.count += 1
        self.last_time = bar.time
        complete = self.count == self.minutes
        observed = self.current
        if complete:
            self.closed.append(observed)
            if self.history_limit is not None:
                self.closed = self.closed[-self.history_limit:]
        return observed, complete

    def snapshot(self):
        if self.current is None:
            return self.closed[:]
        if self.closed and self.closed[-1].time == self.current.time:
            return self.closed[:]
        # A partial interval starting after a gap is not a valid primary bar.
        return self.closed + ([self.current] if self.count else [])
