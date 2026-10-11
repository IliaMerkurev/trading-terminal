# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the Mozilla Public License, v. 2.0.
# If a copy was not distributed with this file, obtain one at
# https://mozilla.org/MPL/2.0/.
# Derived from vumanchu Cipher B + Divergences v17 and Cipher A v1 (Pine v4).
# Original credits: dynausmaux, falconCoin, LazyBear, RicardoSantos,
# LucemAnb, andreholanda73, TradingView.
# Swing implementation derived from Jazal's Swing Free v1, credit DonovanWall.
"""Current-timeframe, confirmed-bar adaptation; no execution or network access.

Input rows are raw finite OHLC with candle-open `time`. The caller must supply
only closed contiguous rows and reset on gaps or unknown confirmation. Event
`confirmed_at` is the confirmation candle OPEN (add interval to obtain close);
`pivot_time` is display placement only, never executable availability. Windows
and histories are bounded and deepcopy-safe for replay checkpointing.

Pine arithmetic na is represented by None. EMA seeds on first non-na value;
SMA and Wilder seeds count non-na observations; rolling extrema ignore na
within their last N bars (including partial early windows). Zero denominators
are na, not invented zero readings. These are source-derived calculations,
not a claim of independently verified TradingView runtime numeric parity.
"""
from collections import deque
import math

SOURCES = {
    'vmc_cipher_b': 'https://www.tradingview.com/script/Msm4SjwI-VuManChu-Cipher-B-Divergences/',
    'vmc_cipher_a': 'https://www.tradingview.com/script/9hWqVcG9-VuManChu-Cipher-A/',
    'vmc_swing': 'https://www.tradingview.com/script/q23anHmP-VuManChu-Swing-Free/',
}
COMMON = dict(source='hlc3', channel=9, average=12, signal=3,
              flow_period=60, flow_multiplier=150.0, rsi_period=14)
DEFAULTS = {
    'vmc_cipher_b': dict(COMMON, flow_offset=2.5, overbought=53.0,
        oversold=-53.0, gold_oversold=-75.0, stoch_period=14,
        stoch_rsi_period=14, stoch_k=3, stoch_d=3, stoch_log=True,
        stoch_average=False, wt_regular=True, wt_secondary=True,
        wt_hidden=False, hidden_no_limits=True, wt_div_top=45.0,
        wt_div_bottom=-65.0, wt_secondary_top=15.0,
        wt_secondary_bottom=-40.0, rsi_regular=False, rsi_hidden=False,
        rsi_div_top=60.0, rsi_div_bottom=30.0,
        stoch_regular=False, stoch_hidden=False),
    'vmc_cipher_a': dict(COMMON, average=13, ema1=5, ema2=11, ema3=15,
        ema4=18, ema5=21, ema6=24, ema7=28, ema8=34, yellow_oversold=-80.0),
    'vmc_swing': dict(source='close', period=20, multiplier=3.5),
}
FIELDS = {k: tuple(v) for k, v in DEFAULTS.items()}
BOOLS = {k for k, v in DEFAULTS['vmc_cipher_b'].items() if type(v) is bool}
LENGTHS = {'channel', 'average', 'signal', 'flow_period', 'rsi_period',
           'stoch_period', 'stoch_rsi_period', 'stoch_k', 'stoch_d', 'period',
           *(f'ema{i}' for i in range(1, 9))}


def validate_params(kind, params):
    if kind not in DEFAULTS or not isinstance(params, dict) or set(params) != set(FIELDS[kind]):
        raise ValueError('Invalid VuManChu parameters')
    for key, value in params.items():
        if key == 'source':
            if value not in ('open', 'high', 'low', 'close', 'hl2', 'hlc3', 'ohlc4'):
                raise ValueError('Invalid VuManChu price source')
        elif key in BOOLS:
            if type(value) is not bool:
                raise ValueError('VuManChu toggles must be boolean')
        elif key in LENGTHS:
            if type(value) is not int or not 1 <= value <= 1000:
                raise ValueError('VuManChu periods must be integers from 1 to 1000')
        elif type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 10000:
            raise ValueError('VuManChu values must be finite and within +/-10000')
    if 'multiplier' in params and params['multiplier'] <= 0:
        raise ValueError('Swing multiplier must be positive')
    for low, high in (('oversold', 'overbought'), ('wt_div_bottom', 'wt_div_top'),
                      ('wt_secondary_bottom', 'wt_secondary_top'), ('rsi_div_bottom', 'rsi_div_top')):
        if low in params and params[low] >= params[high]:
            raise ValueError('VuManChu lower thresholds must be below upper thresholds')
    if 'flow_multiplier' in params and params['flow_multiplier'] <= 0:
        raise ValueError('Flow multiplier must be positive')


def ports(kind):
    if kind == 'vmc_cipher_b':
        return ('wt1', 'wt2', 'fast_wave', 'flow', 'rsi', 'stoch_k', 'stoch_d')
    if kind == 'vmc_cipher_a':
        return tuple(f'ema{i}' for i in range(1, 9))
    if kind == 'vmc_swing':
        return ('filter', 'upper', 'lower')
    raise ValueError('Unknown VuManChu indicator')


def metadata(item):
    kind = item['type']
    return dict(ports=list(ports(kind)), contract='vmc-confirmed-core-v1',
        license='MPL-2.0', source=SOURCES[kind],
        source_version='17' if kind == 'vmc_cipher_b' else '1',
        author='Jazal; underlying Range Filter by DonovanWall' if kind == 'vmc_swing' else 'vumanchu',
        unit='dimensionless' if kind == 'vmc_cipher_b' else 'price',
        confirmed_only=True, before_origin='unavailable',
        seed='First non-na EMA; SMA/Wilder non-na count; zero-denominator unavailable',
        gap_policy='Caller resets on missing or unconfirmed bars; no synthetic candles',
        event_clock='confirmed_at and pivot_time are raw candle-open timestamps; availability is confirmation close',
        divergence_confirmation_bars=2,
        labels={'fast_wave': 'Fast WT (WT1-WT2)', 'flow': 'VMC flow (candle-body proxy)'},
        omitted=['Sommi flags', 'Sommi HTF diamonds (lookahead)', 'HTF MACD colors', 'Schaff cycle'],
        adaptations=['Closed-bar events only', 'Independent secondary divergence enable',
                     'Log Stoch RSI requires strictly positive close', 'No TradingView runtime parity claim'])


class _Average:
    def __init__(self, period, mode='ema'):
        self.period, self.mode, self.value = period, mode, None
        self.samples = deque(maxlen=period)
        self.total = 0.0

    def update(self, x):
        if x is None:
            return self.value
        if self.mode == 'ema':
            alpha = 2 / (self.period + 1)
            self.value = x if self.value is None else alpha * x + (1-alpha) * self.value
        elif self.mode == 'rma' and self.value is not None:
            self.value = (self.value * (self.period - 1) + x) / self.period
        else:
            if len(self.samples) == self.period:
                self.total -= self.samples[0]
            self.samples.append(x)
            self.total += x
            if len(self.samples) == self.period:
                self.value = self.total / self.period
        return self.value


class _RSI:
    def __init__(self, period):
        self.previous = None
        self.up, self.down = _Average(period, 'rma'), _Average(period, 'rma')

    def update(self, x):
        if x is None:
            return None
        previous, self.previous = self.previous, x
        if previous is None:
            return None
        u = self.up.update(max(x-previous, 0))
        d = self.down.update(max(previous-x, 0))
        if u is None or d is None or u + d == 0:
            return None
        if d == 0:
            return 100.0
        if u == 0:
            return 0.0
        return 100.0 - 100.0 / (1.0 + u / d)


def _source(row, name):
    if name in ('open', 'high', 'low', 'close'):
        return row[name]
    fields = {'hl2': ('high', 'low'), 'hlc3': ('high', 'low', 'close'),
              'ohlc4': ('open', 'high', 'low', 'close')}[name]
    return sum(row[k] for k in fields) / len(fields)


def _cross(a, b, pa, pb):
    if any(x is None for x in (a, b, pa, pb)):
        return 0
    return 1 if a > b and pa <= pb else -1 if a < b and pa >= pb else 0


class _Divergences:
    """Literal valuewhen(fractal, value, 0)[2] history, including zero-is-false."""
    def __init__(self, top=None, bottom=None):
        self.top, self.bottom = top, bottom
        self.window = deque(maxlen=5)
        self.latest = {'top': None, 'bottom': None}
        self.history = deque(maxlen=2)

    def update(self, value, row, index, rsi=None):
        self.window.append((value, row['high'], row['low'], row['time'], index, rsi))
        prior = self.history[0] if len(self.history) == 2 else {'top': None, 'bottom': None}
        result = {'events': [], 'previous_bottom': prior['bottom']}
        if len(self.window) == 5 and all(v[0] is not None for v in self.window):
            center = self.window[2]
            others = [self.window[i][0] for i in (0, 1, 3, 4)]
            for side, qualifies in (
                ('top', all(center[0] > v for v in others) and (self.top is None or center[0] >= self.top)),
                ('bottom', all(center[0] < v for v in others) and (self.bottom is None or center[0] <= self.bottom))):
                # Pine v4 implicitly casts the numeric fractal series to bool.
                if not qualifies or center[0] == 0:
                    continue
                previous = prior[side]
                self.latest[side] = center
                if previous is None:
                    continue
                price_index = 1 if side == 'top' else 2
                price_delta = center[price_index] - previous[price_index]
                osc_delta = center[0] - previous[0]
                if price_delta * osc_delta < 0:
                    regular = price_delta > 0 if side == 'top' else price_delta < 0
                    result['events'].append(dict(
                        kind=('regular_' if regular else 'hidden_') + ('bearish' if side == 'top' else 'bullish'),
                        index=index, pivot_index=center[4], pivot_time=center[3],
                        confirmed_at=row['time'], previous_pivot_time=previous[3],
                        value=center[0], previous_value=previous[0]))
        self.history.append(dict(self.latest))
        return result


class VumanchuState:
    """One closed-contiguous-segment state; events contain this update only."""
    def __init__(self, item):
        self.kind = item['type']
        self.params = dict(item['params'])
        validate_params(self.kind, self.params)
        self.index, self.previous, self.events = -1, None, []
        self.prev_values = {}
        self.regime = None
        p = self.params
        if self.kind == 'vmc_swing':
            self.range1, self.range2 = _Average(p['period']), _Average(2*p['period']-1)
            self.filter, self.direction, self.condition = None, 0, None
            return
        self.esa, self.deviation = _Average(p['channel']), _Average(p['channel'])
        self.wave, self.wave_signal = _Average(p['average']), _Average(p['signal'], 'sma')
        self.flow = _Average(p['flow_period'], 'sma')
        self.rsi = _RSI(p['rsi_period'])
        if self.kind == 'vmc_cipher_a':
            self.emas = [_Average(p[f'ema{i}']) for i in range(1, 9)]
        else:
            self.stoch_rsi = _RSI(p['stoch_rsi_period'])
            self.stoch_window = deque(maxlen=p['stoch_period'])
            self.stoch_k, self.stoch_d = _Average(p['stoch_k'], 'sma'), _Average(p['stoch_d'], 'sma')
            self.divs = {'wt': _Divergences(p['wt_div_top'], p['wt_div_bottom']),
                'wt_secondary': _Divergences(p['wt_secondary_top'], p['wt_secondary_bottom']),
                'wt_unbounded': _Divergences(),
                'rsi': _Divergences(p['rsi_div_top'], p['rsi_div_bottom']),
                'rsi_unbounded': _Divergences(), 'stoch': _Divergences()}

    def _event(self, kind, row, value=None, pivot=None, oscillator=None):
        event = dict(kind=kind, index=self.index, pivot_index=self.index,
                     pivot_time=row['time'], confirmed_at=row['time'], value=value)
        if pivot:
            event.update(pivot_index=self.index-2, pivot_time=pivot)
        if oscillator:
            event['oscillator'] = oscillator
        self.events.append(event)

    def update(self, row):
        # Fail before mutating state. Confirmation/gap policy belongs to replay.
        for key in ('open', 'high', 'low', 'close', 'time'):
            if type(row.get(key)) not in (int, float) or not math.isfinite(row[key]):
                raise ValueError('VuManChu requires finite raw OHLC/time')
        if row['high'] < max(row['open'], row['close'], row['low']) or row['low'] > min(row['open'], row['close']):
            raise ValueError('Invalid VuManChu OHLC range')
        if self.previous and row['time'] <= self.previous['time']:
            raise ValueError('VuManChu rows must be strictly chronological')
        if self.kind == 'vmc_cipher_b' and self.params['stoch_log'] and row['close'] <= 0:
            raise ValueError('Log Stoch RSI requires positive close; disable log for nonpositive prices')
        self.index += 1
        self.events = []
        if self.kind == 'vmc_swing':
            result = self._swing(row)
        else:
            p = self.params
            source = _source(row, p['source'])
            esa = self.esa.update(source)
            deviation = self.deviation.update(abs(source-esa))
            ci = (source-esa)/(0.015*deviation) if deviation else None
            wt1 = self.wave.update(ci)
            wt2 = self.wave_signal.update(wt1)
            flow_input = p['flow_multiplier']*(row['close']-row['open'])/(row['high']-row['low']) if row['high'] != row['low'] else None
            flow = self.flow.update(flow_input)
            rsi = self.rsi.update(row['close'])
            values = dict(wt1=wt1, wt2=wt2, rsi=rsi, flow=flow)
            cross = _cross(wt1, wt2, self.prev_values.get('wt1'), self.prev_values.get('wt2'))
            if self.kind == 'vmc_cipher_a':
                result = self._cipher_a(row, values, cross)
            else:
                values['flow'] = flow-p['flow_offset'] if flow is not None else None
                result = self._cipher_b(row, values, cross)
            self.prev_values = {**values, **result}
        self.previous = dict(row)
        return result

    def _cipher_a(self, row, values, cross):
        result = {f'ema{i+1}': ema.update(row['close']) for i, ema in enumerate(self.emas)}
        self.regime = 1 if result['ema8'] < result['ema2'] else -1
        prev = self.prev_values
        def cross_ema(a, b):
            return _cross(result[a], result[b], prev.get(a), prev.get(b))
        red = cross_ema('ema1', 'ema2') == -1
        diamond = cross == -1
        wt2, rsi, flow = (values[k] for k in ('wt2', 'rsi', 'flow'))
        flags = dict(long_ema=cross_ema('ema2', 'ema8') == 1,
            short_ema=cross_ema('ema2', 'ema8') == -1, red_cross=red,
            blue_triangle=cross_ema('ema2', 'ema3') == 1, red_diamond=diamond,
            blood_diamond=diamond and red,
            yellow_cross=diamond and all(x is not None for x in (wt2, rsi, flow)) and
                self.params['yellow_oversold'] < wt2 < 45 and 15 < rsi < 30 and flow < -5,
            bull_candle=bool(self.previous) and row['open'] > result['ema2'] and
                row['open'] > result['ema8'] and self.previous['close'] > self.previous['open'] and
                row['close'] > row['open'] and not diamond and not red)
        for kind, enabled in flags.items():
            if enabled:
                self._event(kind, row, row['close'])
        return result

    def _cipher_b(self, row, values, cross):
        p = self.params
        r = self.stoch_rsi.update(math.log(row['close']) if p['stoch_log'] else row['close'])
        self.stoch_window.append(r)
        valid = [x for x in self.stoch_window if x is not None]
        raw = 100*(r-min(valid))/(max(valid)-min(valid)) if r is not None and valid and max(valid) != min(valid) else None
        k = self.stoch_k.update(raw)
        d = self.stoch_d.update(k)
        k_display = (k+d)/2 if p['stoch_average'] and k is not None and d is not None else None if p['stoch_average'] else k
        result = dict(values, fast_wave=values['wt1']-values['wt2'] if values['wt1'] is not None and values['wt2'] is not None else None,
                      stoch_k=k_display, stoch_d=d)
        if cross:
            self._event('cross_up' if cross == 1 else 'cross_down', row, values['wt2'], oscillator='wt')
            if cross == 1 and values['wt2'] <= p['oversold']:
                self._event('buy_dot', row, values['wt2'], oscillator='wt')
            if cross == -1 and values['wt2'] >= p['overbought']:
                self._event('sell_dot', row, values['wt2'], oscillator='wt')
        histories = {}
        for name, tracker in self.divs.items():
            val = values['wt2'] if name.startswith('wt') else values['rsi'] if name.startswith('rsi') else k_display
            histories[name] = tracker.update(val, row, self.index, values['rsi'])
        regular = []
        for name, enabled in (('wt', p['wt_regular']), ('wt_secondary', p['wt_regular'] and p['wt_secondary']),
                              ('rsi', p['rsi_regular']), ('stoch', p['stoch_regular'])):
            if enabled:
                for event in histories[name]['events']:
                    if event['kind'].startswith('regular_'):
                        event = dict(event, oscillator=name)
                        self.events.append(event)
                        regular.append(event)
        for name, enabled in (('wt', p['wt_hidden']), ('rsi', p['rsi_hidden']), ('stoch', p['stoch_hidden'])):
            history = name + '_unbounded' if p['hidden_no_limits'] and name != 'stoch' else name
            if enabled:
                for event in histories[history]['events']:
                    if event['kind'].startswith('hidden_'):
                        self.events.append(dict(event, oscillator=name))
        if p['wt_hidden'] and p['wt_secondary']:
            for event in histories['wt_secondary']['events']:
                if event['kind'].startswith('hidden_'):
                    self.events.append(dict(event, oscillator='wt_secondary'))
        for direction in ('bullish', 'bearish'):
            matches = [e for e in regular if e['kind'] == 'regular_' + direction]
            if matches:
                event = matches[0]
                self.events.append(dict(event, kind='divergence_buy_dot' if direction == 'bullish' else 'divergence_sell_dot'))
        # Gold reads the prior qualifying WT trough history even for an RSI div.
        previous = histories['wt']['previous_bottom']
        gold_div = any(e['kind'] == 'regular_bullish' and e['oscillator'] in ('wt', 'rsi') for e in regular)
        wt2 = values['wt2']
        if gold_div and previous is not None and previous[5] is not None and wt2 is not None and previous[0] <= p['gold_oversold'] and wt2 > p['gold_oversold'] and previous[0]-wt2 <= -5 and previous[5] < 30:
            event = next(e for e in regular if e['kind'] == 'regular_bullish' and e['oscillator'] in ('wt', 'rsi'))
            self.events.append(dict(event, kind='gold_buy_dot', value=wt2))
        return result

    def _swing(self, row):
        source = _source(row, self.params['source'])
        previous = _source(self.previous, self.params['source']) if self.previous else None
        change = abs(source-previous) if previous is not None else None
        radius = self.range2.update(self.range1.update(change))
        radius = radius*self.params['multiplier'] if radius is not None else None
        old = self.filter
        if old is None:
            self.filter = source
        elif radius is not None:
            self.filter = source-radius if source-radius > old else source+radius if source+radius < old else old
            self.direction = 1 if self.filter > old else -1 if self.filter < old else self.direction
        self.regime = self.direction
        changed = previous is not None and source != previous
        long = changed and source > self.filter and self.direction == 1
        short = changed and source < self.filter and self.direction == -1
        if long and self.condition == -1:
            self._event('swing_long', row, self.filter)
        if short and self.condition == 1:
            self._event('swing_short', row, self.filter)
        self.condition = 1 if long else -1 if short else self.condition
        return dict(filter=self.filter, upper=self.filter+radius if radius is not None else None,
                    lower=self.filter-radius if radius is not None else None)


def calculate_vumanchu(candles, kind, params=None, *, interval_seconds=None):
    """Test/research replay; explicit closed provenance required, gaps reset.

    No data fetch, strategy dispatch, or trade execution. Unconfirmed rows produce
    null columns and reset state, matching chart replay. Each event retains its
    raw confirmation OPEN timestamp; callers must add the known interval.
    """
    item = dict(type=kind, params=dict(DEFAULTS[kind], **(params or {})))
    state = VumanchuState(item)
    series = {key: [] for key in ports(kind)}
    events, previous_time = [], None
    for row in candles:
        closed = row.get('confirmation') in ('closed_rest', 'provider_confirmed', 'synthetic_closed')
        gap = previous_time is not None and interval_seconds is not None and row['time'] != previous_time+interval_seconds
        if gap or not closed:
            state = VumanchuState(item)
        values = state.update(row) if closed else {key: None for key in ports(kind)}
        for key in series:
            series[key].append(values[key])
        if closed:
            events.extend(dict(e) for e in state.events)
        previous_time = row['time']
    return dict(series=series, events=events, metadata=metadata(item))
