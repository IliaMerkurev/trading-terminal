"""Independently authored, causal chart-only formulas; no strategy IR dispatch.

All windows are current-inclusive, using confirmed source-native candles only.
Even finite windows stay unavailable before the persisted calculation origin.
"""
from collections import deque
import math

FIELDS = {kind: ('period',) for kind in (
    'wma', 'rma', 'vwma', 'donchian', 'roc', 'momentum', 'cci',
    'williamsr', 'mfi', 'cmf', 'stddev')}
FIELDS['keltner'] = ('period', 'atr_period', 'multiplier')
CHANNELS = {'donchian', 'keltner'}
VOLUME_KINDS = {'vwma', 'mfi', 'cmf'}
SEEDS = {
    'wma': 'Rolling closes; weights 1 through N, newest weight N',
    'rma': 'SMA of first N closes, then Wilder smoothing (previous*(N-1)+close)/N',
    'vwma': 'Rolling sum(close*volume)/sum(volume); zero total volume unavailable',
    'donchian': 'Current-inclusive rolling highest high / lowest low and midpoint',
    'keltner': 'First-close-seeded EMA; display SMA-seeded Wilder ATR (not graph ATR)',
    'roc': '100*(close/close[N]-1); zero denominator unavailable',
    'momentum': 'close-close[N]',
    'cci': 'HLC3 rolling mean absolute deviation; divisor 0.015; flat window zero',
    'williamsr': '-100*(highest high-close)/(highest high-lowest low); flat window zero',
    'mfi': 'N successive HLC3 changes; equal ignored; positive-only 100, negative-only 0, neither unavailable',
    'cmf': 'Rolling volume-weighted money-flow multiplier; flat candle zero; zero total volume unavailable',
    'stddev': 'Population standard deviation of N closes (divisor N)',
}


def ports(kind):
    return ('upper', 'middle', 'lower') if kind in CHANNELS else ('value',)


def metadata(item):
    kind, params = item['type'], item['params']
    n = params['period']
    warmup = max(n, params['atr_period']) if kind == 'keltner' else n + (kind in ('roc', 'momentum', 'mfi'))
    return dict(ports=list(ports(kind)), seed=SEEDS[kind], warmup_bars=warmup,
                unit='percent' if kind in ('roc', 'williamsr', 'mfi') else
                'dimensionless' if kind in ('cci', 'cmf') else 'price',
                volume_basis='source-native; no cross-source volume equivalence' if kind in VOLUME_KINDS else None,
                before_origin='unavailable', confirmed_only=True)


class FormulaState:
    def __init__(self, item):
        self.kind, self.params = item['type'], item['params']
        self.n = self.params['period']
        self.samples = deque(maxlen=self.n + (self.kind in ('roc', 'momentum')))
        self.previous = None
        self.value = None
        self.atr = None
        self.trs = deque(maxlen=self.params.get('atr_period', 1))
        self.count = 0

    def update(self, row):
        result = dict.fromkeys(ports(self.kind))
        close, high, low = row['close'], row['high'], row['low']
        volume = row.get('volume')
        if self.kind in VOLUME_KINDS and (type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0):
            self.samples.clear()
            self.previous = None
            return result
        n, kind = self.n, self.kind
        self.count += 1
        if kind == 'keltner':
            a = self.params['atr_period']
            tr = high-low if self.previous is None else max(high-low, abs(high-self.previous), abs(low-self.previous))
            self.trs.append(tr)
            self.atr = ((a-1)*self.atr+tr)/a if self.atr is not None else sum(self.trs)/a if len(self.trs) == a else None
            self.value = close if self.value is None else self.value + 2/(n+1)*(close-self.value)
            self.previous = close
            if self.count >= max(n, a):
                width = self.params['multiplier']*self.atr
                result.update(upper=self.value+width, middle=self.value, lower=self.value-width)
            return result
        if kind == 'mfi':
            typical = high/3 + low/3 + close/3
            if self.previous is not None:
                flow = typical*volume
                self.samples.append((flow if typical > self.previous else 0, flow if typical < self.previous else 0))
            self.previous = typical
        elif kind in ('vwma', 'cmf'):
            weighted = close*volume if kind == 'vwma' else (0 if high == low else ((close-low)-(high-close))/(high-low))*volume
            self.samples.append((weighted, volume))
        elif kind in ('donchian', 'williamsr'):
            self.samples.append((high, low))
        elif kind == 'cci':
            self.samples.append(high/3 + low/3 + close/3)
        else:
            self.samples.append(close)
        if len(self.samples) != self.samples.maxlen:
            return result
        if kind == 'wma':
            value = sum((i+1)*c for i, c in enumerate(self.samples))/(n*(n+1)/2)
        elif kind == 'rma':
            self.value = sum(self.samples)/n if self.value is None else ((n-1)*self.value+close)/n
            value = self.value
        elif kind in ('vwma', 'cmf'):
            total = sum(v for _, v in self.samples)
            value = sum(w for w, _ in self.samples)/total if total else None
        elif kind in ('donchian', 'williamsr'):
            upper = max(h for h, _ in self.samples)
            lower = min(l for _, l in self.samples)
            if kind == 'donchian':
                return dict(upper=upper, middle=upper/2+lower/2, lower=lower)
            value = -100*((upper-close)/(upper-lower)) if upper != lower else 0.0
        elif kind == 'roc':
            value = 100*(close/self.samples[0]-1) if self.samples[0] else None
        elif kind == 'momentum':
            value = close-self.samples[0]
        elif kind == 'cci':
            mean = self.samples[0] + sum(c-self.samples[0] for c in self.samples)/n
            deviation = sum(abs(c-mean) for c in self.samples)/n
            value = ((self.samples[-1]-mean)/deviation)/0.015 if deviation else 0.0
        elif kind == 'mfi':
            positive = sum(p for p, _ in self.samples)
            negative = sum(m for _, m in self.samples)
            value = 100*(positive/(positive+negative)) if positive or negative else None
        elif kind == 'stddev':
            offsets = [c-self.samples[0] for c in self.samples]
            mean = sum(offsets)/n
            value = math.sqrt(sum((c-mean)**2 for c in offsets)/n)
        else:
            raise ValueError('Unsupported display formula')
        result['value'] = value
        return result
