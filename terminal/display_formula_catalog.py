"""Independently authored, causal chart-only formulas; no strategy IR dispatch.

All windows are current-inclusive, using confirmed source-native candles only.
Even finite windows stay unavailable before the persisted calculation origin.
"""
from collections import deque
import math
from terminal.graph import indicator_for

FIELDS = {kind: ('period',) for kind in (
    'wma', 'rma', 'vwma', 'donchian', 'roc', 'momentum', 'cci',
    'williamsr', 'mfi', 'cmf', 'stddev')}
FIELDS['keltner'] = ('period', 'atr_period', 'multiplier')
ADVANCED_FIELDS = {
    'dmi': ('period', 'adx_period'),
    'supertrend': ('period', 'multiplier'),
    'stochrsi': ('period', 'stochastic_period', 'smooth', 'signal'),
    'hma': ('period',),
    'bbpercentb': ('period', 'deviations'),
    'bbwidth': ('period', 'deviations'),
}
# Keep the original catalog batch independently addressable for compatibility.
BOUNDARY_FIELDS = {'sar': ('step', 'max'), 'vwap': ('mode', 'anchor')}
PROJECTION_FIELDS = {'ichimoku': ('conversion', 'base', 'span_b', 'displacement')}
ALL_FIELDS = {**FIELDS, **ADVANCED_FIELDS, **BOUNDARY_FIELDS, **PROJECTION_FIELDS}
CHANNELS = {'donchian', 'keltner'}
VOLUME_KINDS = {'vwma', 'mfi', 'cmf', 'vwap'}
SEEDS = {
    'sar': 'Local SAR contract, not platform parity: first bar unavailable; second close change seeds direction (tie up), two-bar extreme seed; prior-two-bar clamp, strict penetration reversals, strict extreme AF increments',
    'vwap': 'HLC3 weighted by source-native volume from exact UTC day or fixed anchor OPEN timestamp; complete contiguous confirmed coverage required; gaps poison the session, zero denominator unavailable',
    'dmi': 'N changes TR and winning positive DM (ties zero), SMA seed then Wilder; DX zero when DI sum zero; ADX first A DX mean then Wilder',
    'supertrend': 'Display ATR: N TR SMA seed then Wilder; median bands carried using prior close, strict current-close flips, initial up (+1), equality retains; inactive line unavailable',
    'stochrsi': 'Existing display RSI: engine Wilder seed with first close zero change, exposed after N+1 bars; rolling RSI range (flat zero), SMA K then SMA D',
    'hma': 'WMA(2*WMA(close,max(1,floor(N/2)))-WMA(close,N),max(1,floor(sqrt(N)))); period 1 identity',
    'bbpercentb': 'Existing population Bollinger bands; (close-lower)/(upper-lower); zero width unavailable',
    'bbwidth': 'Existing population Bollinger bands; 100*(upper-lower)/middle; zero middle unavailable',
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
    if kind == 'ichimoku':
        return ('tenkan', 'kijun', 'senkou_a', 'senkou_b', 'chikou')
    if kind == 'dmi':
        return ('plus_di', 'minus_di', 'adx')
    if kind == 'supertrend':
        return ('up', 'down', 'direction')
    if kind == 'stochrsi':
        return ('k', 'd')
    return ('upper', 'middle', 'lower') if kind in CHANNELS else ('value',)


def metadata(item):
    kind, params = item['type'], item['params']
    if kind == 'ichimoku':
        return dict(ports=list(ports(kind)), plot_ports=['tenkan', 'kijun'],
                    contract='ichimoku-raw-ordinal-v1', unit='price', confirmed_only=True,
                    before_origin='unavailable', warmup_bars=max(params['conversion'], params['base'], params['span_b']),
                    port_warmup_bars=dict(tenkan=params['conversion'], kijun=params['base'],
                        senkou_a=max(params['conversion'], params['base']), senkou_b=params['span_b'], chikou=1),
                    seed='Current-inclusive rolling high/low midpoints; Senkou A averages ready Tenkan/Kijun; Chikou is confirmed close',
                    displacement=params['displacement'], displacement_unit='actual raw bars',
                    information_time='computed_at; Chikou is learned later than its plotted_at location',
                    projected_timestamps='Native-interval estimates only beyond known raw tape')
    if kind in BOUNDARY_FIELDS:
        result = dict(ports=['value'], seed=SEEDS[kind], warmup_bars=2 if kind == 'sar' else 1,
                      unit='price', before_origin='unavailable', confirmed_only=True,
                      volume_basis='source-native; no cross-source volume equivalence' if kind == 'vwap' else None)
        if kind == 'sar':
            result['plot_style'] = 'dots'
        else:
            result.update(session_clock='UTC candle open', mode=params['mode'], anchor=params['anchor'],
                          coverage='Exact boundary and contiguous confirmed bars; no automatic backfill')
        return result
    n = params['period']
    warmup = max(n, params['atr_period']) if kind == 'keltner' else n + (kind in ('roc', 'momentum', 'mfi'))
    port_warmup = None
    if kind == 'dmi':
        warmup = n + params['adx_period']
        port_warmup = dict(plus_di=n+1, minus_di=n+1, adx=warmup)
    elif kind == 'stochrsi':
        k_ready = n + params['stochastic_period'] + params['smooth'] - 1
        warmup = k_ready + params['signal'] - 1
        port_warmup = dict(k=k_ready, d=warmup)
    elif kind == 'hma':
        warmup = n + max(1, math.isqrt(n)) - 1
    result = dict(ports=list(ports(kind)), seed=SEEDS[kind], warmup_bars=warmup,
                unit='percent' if kind in ('roc', 'williamsr', 'mfi', 'dmi', 'stochrsi', 'bbwidth') else
                'dimensionless' if kind in ('cci', 'cmf', 'bbpercentb') else 'price',
                volume_basis='source-native; no cross-source volume equivalence' if kind in VOLUME_KINDS else None,
                before_origin='unavailable', confirmed_only=True)
    if port_warmup is not None:
        result['port_warmup_bars'] = port_warmup
    if kind == 'supertrend':
        result['port_units'] = dict(up='price', down='price', direction='signed direction')
        result['plot_ports'] = ['up', 'down']
        result['direction_convention'] = '+1 up, -1 down; not Pine direction signs'
    return result


class FormulaState:
    def __new__(cls, item):
        if item['type'] == 'ichimoku':
            return IchimokuState(item)
        if item['type'] == 'sar':
            return SarState(item)
        if item['type'] == 'vwap':
            return VwapState(item)
        if item['type'] in ADVANCED_FIELDS:
            return AdvancedFormulaState(item)
        return super().__new__(cls)

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


def _wma(values):
    n = len(values)
    return sum((i+1)*value for i, value in enumerate(values))/(n*(n+1)/2)


class AdvancedFormulaState:
    """Causal display-only formulas. Engine RSI/BB reuse preserves their seeds."""
    def __init__(self, item):
        self.kind, self.params = item['type'], item['params']
        self.n = self.params['period']
        self.count = 0
        self.previous = None
        self.samples = deque(maxlen=self.n)
        self.smoothed = None
        self.adx = None
        self.direction = None
        self.upper = self.lower = None
        if self.kind == 'dmi':
            self.dx = deque(maxlen=self.params['adx_period'])
        elif self.kind == 'stochrsi':
            self.engine = indicator_for(dict(type='rsi', params=dict(period=self.n)))
            self.rsi = deque(maxlen=self.params['stochastic_period'])
            self.raw = deque(maxlen=self.params['smooth'])
            self.k = deque(maxlen=self.params['signal'])
        elif self.kind == 'hma':
            self.half = deque(maxlen=max(1, self.n//2))
            self.root = deque(maxlen=max(1, math.isqrt(self.n)))
        elif self.kind in ('bbpercentb', 'bbwidth'):
            self.engine = indicator_for(dict(type='bb', params=self.params))

    def update(self, row):
        result = dict.fromkeys(ports(self.kind))
        high, low, close = row['high'], row['low'], row['close']
        n = self.n
        self.count += 1
        if self.kind == 'dmi':
            previous, self.previous = self.previous, (high, low, close)
            if previous is None:
                return result
            up, down = high-previous[0], previous[1]-low
            sample = (max(high-low, abs(high-previous[2]), abs(low-previous[2])),
                      up if up > 0 and up > down else 0.0,
                      down if down > 0 and down > up else 0.0)
            self.samples.append(sample)
            if self.smoothed is None:
                if len(self.samples) < n:
                    return result
                self.smoothed = tuple(sum(s[i] for s in self.samples)/n for i in range(3))
            else:
                self.smoothed = tuple(((n-1)*old+new)/n for old, new in zip(self.smoothed, sample))
            tr, positive, negative = self.smoothed
            plus, minus = (100*(positive/tr), 100*(negative/tr)) if tr else (0.0, 0.0)
            dx = 100*(abs(plus-minus)/(plus+minus)) if plus+minus else 0.0
            self.dx.append(dx)
            a = self.params['adx_period']
            if self.adx is not None:
                self.adx = ((a-1)*self.adx+dx)/a
            elif len(self.dx) == a:
                self.adx = sum(self.dx)/a
            result.update(plus_di=plus, minus_di=minus, adx=self.adx)
        elif self.kind == 'supertrend':
            previous, self.previous = self.previous, close
            tr = high-low if previous is None else max(high-low, abs(high-previous), abs(low-previous))
            self.samples.append(tr)
            if self.smoothed is not None:
                self.smoothed = ((n-1)*self.smoothed+tr)/n
            elif len(self.samples) == n:
                self.smoothed = sum(self.samples)/n
            else:
                return result
            width = self.params['multiplier']*self.smoothed
            upper, lower = high/2+low/2+width, high/2+low/2-width
            if self.direction is None:
                self.upper, self.lower, self.direction = upper, lower, 1
            else:
                self.upper = upper if upper < self.upper or previous > self.upper else self.upper
                self.lower = lower if lower > self.lower or previous < self.lower else self.lower
                if self.direction == 1 and close < self.lower:
                    self.direction = -1
                elif self.direction == -1 and close > self.upper:
                    self.direction = 1
            result['up' if self.direction == 1 else 'down'] = self.lower if self.direction == 1 else self.upper
            result['direction'] = self.direction
        elif self.kind == 'stochrsi':
            self.engine.update_raw(close)
            # Exactly the existing display RSI availability gate, not TA-Lib's seed.
            if not self.engine.initialized or self.count < n+1:
                return result
            self.rsi.append(self.engine.value*100)
            if len(self.rsi) < self.rsi.maxlen:
                return result
            lowest, highest = min(self.rsi), max(self.rsi)
            self.raw.append(100*((self.rsi[-1]-lowest)/(highest-lowest)) if highest != lowest else 0.0)
            if len(self.raw) < self.raw.maxlen:
                return result
            value = sum(self.raw)/len(self.raw)
            self.k.append(value)
            result['k'] = value
            if len(self.k) == self.k.maxlen:
                result['d'] = sum(self.k)/len(self.k)
        elif self.kind == 'hma':
            self.samples.append(close)
            self.half.append(close)
            if len(self.samples) == n:
                self.root.append(2*_wma(self.half)-_wma(self.samples))
                if len(self.root) == self.root.maxlen:
                    result['value'] = _wma(self.root)
        elif self.kind in ('bbpercentb', 'bbwidth'):
            self.engine.update_raw(close, close, close)
            if self.engine.initialized:
                width = self.engine.upper-self.engine.lower
                if self.kind == 'bbpercentb':
                    result['value'] = (close-self.engine.lower)/width if width else None
                else:
                    result['value'] = 100*(width/self.engine.middle) if self.engine.middle else None
        return result


class SarState:
    """Explicit local two-bar seed and strict reversal contract, without parity claims."""
    def __init__(self, item):
        self.step, self.maximum = item['params']['step'], item['params']['max']
        self.previous = deque(maxlen=2)
        self.value = self.ep = self.direction = None
        self.af = self.step

    def update(self, row):
        high, low, close = row['high'], row['low'], row['close']
        if not self.previous:
            self.previous.append((high, low, close))
            return {'value': None}
        if self.direction is None:
            first = self.previous[0]
            self.direction = 1 if close >= first[2] else -1
            self.value = min(first[1], low) if self.direction == 1 else max(first[0], high)
            self.ep = max(first[0], high) if self.direction == 1 else min(first[1], low)
        else:
            candidate = self.value + self.af * (self.ep - self.value)
            if self.direction == 1:
                candidate = min(candidate, *(bar[1] for bar in self.previous))
                reverse = low < candidate
            else:
                candidate = max(candidate, *(bar[0] for bar in self.previous))
                reverse = high > candidate
            if reverse:
                self.direction *= -1
                self.value = max(self.ep, high) if self.direction == -1 else min(self.ep, low)
                self.ep = low if self.direction == -1 else high
                self.af = self.step
            else:
                self.value = candidate
                if (self.direction == 1 and high > self.ep) or (self.direction == -1 and low < self.ep):
                    self.ep = high if self.direction == 1 else low
                    self.af = min(self.maximum, self.af + self.step)
        self.previous.append((high, low, close))
        return {'value': self.value}


class VwapState:
    """A missing input poisons coverage until the next explicit session boundary.

    Unlike rolling indicators this object survives orchestration segment resets.
    It never treats the first bar after a gap as a fresh volume accumulator.
    """
    def __init__(self, item):
        self.mode, self.anchor = item['params']['mode'], item['params']['anchor']
        self.session = self.previous = None
        self.weighted = self.volume = 0.0
        self.poison = None
        self.reason = 'missing_session_start'

    def status(self):
        return dict(status='unavailable' if self.reason else 'ready', reason=self.reason)

    def observe(self, row, width, closed):
        stamp = row['time']
        boundary = stamp - stamp % 86400 if self.mode == 0 else self.anchor
        if stamp < boundary:
            self.reason = 'before_anchor'
            return {'value': None}
        if boundary != self.session:
            self.session, self.previous = boundary, None
            self.weighted = self.volume = 0.0
            self.poison = None if stamp == boundary else 'missing_session_start'
        if self.previous is not None and stamp != self.previous + width:
            self.poison = self.poison or 'incomplete_coverage'
        self.previous = stamp
        volume = row.get('volume')
        if not closed or type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0:
            self.poison = self.poison or 'incomplete_coverage'
        if self.poison:
            self.reason = self.poison
            return {'value': None}
        typical = row['high']/3 + row['low']/3 + row['close']/3
        self.weighted += typical * volume
        self.volume += volume
        self.reason = None if self.volume else 'zero_total_volume'
        return {'value': self.weighted/self.volume if self.volume else None}


def validate_boundary_params(kind, params):
    if set(params) != set(BOUNDARY_FIELDS[kind]):
        raise ValueError('Invalid indicator parameters')
    values = params
    if kind == 'sar':
        if any(type(v) not in (int, float) for v in values.values()) or not 0 < values['step'] <= values['max'] <= 1:
            raise ValueError('SAR requires finite 0 < step <= max <= 1')
    elif (type(values['mode']) is not int or values['mode'] not in (0, 1) or
          type(values['anchor']) is not int or not 0 <= values['anchor'] <= 253402300799 or
          (values['mode'] == 0 and values['anchor'] != 0)):
        raise ValueError('VWAP requires mode 0/1 and a valid UTC Unix-seconds anchor; day mode requires anchor 0')
    return values


def validate_timeframe(instances, minutes):
    for item in instances:
        if item['type'] == 'vwap' and item['params']['anchor'] % (minutes * 60):
            raise ValueError('VWAP anchor must align exactly with the native timeframe')


class IchimokuState:
    """Unshifted confirmed computations. The separate projection layer owns time."""
    def __init__(self, item):
        self.windows = {key: deque(maxlen=item['params'][key]) for key in ('conversion', 'base', 'span_b')}

    def update(self, row):
        middle = {}
        for key, window in self.windows.items():
            window.append((row['high'], row['low']))
            middle[key] = (max(h for h, _ in window)/2 + min(l for _, l in window)/2) if len(window) == window.maxlen else None
        tenkan, kijun = middle['conversion'], middle['base']
        return dict(tenkan=tenkan, kijun=kijun,
                    senkou_a=tenkan/2+kijun/2 if tenkan is not None and kijun is not None else None,
                    senkou_b=middle['span_b'], chikou=row['close'])
