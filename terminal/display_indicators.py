"""Bounded cache-only chart presentation; never evaluates a strategy or orders.

The original engine primitives are shared with Strategy IR; additive kinds
have explicit display-only seeds. Origins and settings
belong to the workspace SQLite database, not a browser's shared localStorage.
"""
from collections import OrderedDict, deque
import copy
import json
import math
import re
import threading
from terminal.chart_history import INTERVALS
from terminal.data import canonical, digest, validate_symbol
from terminal.graph import indicator_for
from terminal import display_formula_catalog as formulas
from terminal import chart_presentation as prices
from terminal.market_sources import cache_market
CONTRACT = 'native-close-engine-seeds-v1'
MAX_BARS = 10000
MAX_INSTANCES = 8
FIELDS = {'sma': ('period',), 'ema': ('period',), 'bb': ('period', 'deviations'), 'rsi': ('period',), 'macd': ('fast', 'slow', 'signal'), 'volume': (), 'atr': ('period',), 'stochastic': ('period', 'smooth', 'signal'), 'obv': ()}

FIELDS.update(formulas.FIELDS)

def validate_instances(instances):
    if not isinstance(instances, list) or len(instances) > MAX_INSTANCES:
        raise ValueError('Use at most 8 indicators')
    seen = set()
    for item in instances:
        if not isinstance(item, dict) or set(item) - {'placement'} != {'id', 'type', 'params', 'color', 'visible'}:
            raise ValueError('Invalid indicator settings')
        ident = item['id']
        kind = item['type']
        params = item['params']
        if 'placement' in item and (kind != 'volume' or item['placement'] not in ('overlay', 'pane')):
            raise ValueError('Invalid volume placement')
        if not isinstance(ident, str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,63}', ident) or ident in seen:
            raise ValueError('Indicator IDs must be unique')
        seen.add(ident)
        if not isinstance(kind, str) or kind not in FIELDS or (not isinstance(params, dict)) or (set(params) != set(FIELDS[kind])):
            raise ValueError('Invalid indicator type or parameters')
        if type(item['visible']) is not bool or not isinstance(item['color'], str) or (not re.fullmatch('#[0-9a-fA-F]{6}', item['color'])):
            raise ValueError('Invalid visibility or color')
        for name, value in params.items():
            if name in ('deviations', 'multiplier'):
                if type(value) not in (int, float) or not math.isfinite(value) or (not 0 < value <= 10):
                    raise ValueError('BB deviations must be greater than 0 and at most 10' if name == 'deviations' else 'Keltner multiplier must be greater than 0 and at most 10')
            elif type(value) is not int or not 1 <= value <= 1000:
                raise ValueError('Periods must be whole numbers from 1 to 1000')
        if kind == 'macd' and params['fast'] >= params['slow']:
            raise ValueError('MACD fast must be less than slow')
    valid = copy.deepcopy(instances)
    for item in valid:
        if item['type'] == 'volume':
            item.setdefault('placement', 'overlay')
    return valid

class NativeDisplayState:
    """Independent display-only additions; existing engine seeds are untouched."""
    def __init__(self, item):
        self.kind, self.params = item['type'], item['params']
        self.previous = None
        self.value = None
        self.samples = deque(maxlen=self.params.get('period', 1))
        self.raw = deque(maxlen=self.params.get('smooth', 1))
        self.k = deque(maxlen=self.params.get('signal', 1))

    def update(self, row):
        close, high, low = row['close'], row['high'], row['low']
        if self.kind == 'atr':
            tr = high - low if self.previous is None else max(high-low, abs(high-self.previous), abs(low-self.previous))
            self.samples.append(tr)
            n = self.params['period']
            if self.value is not None:
                self.value = ((n-1)*self.value + tr)/n
            elif len(self.samples) == n:
                self.value = sum(self.samples)/n
            result = {'value': self.value}
        elif self.kind == 'obv':
            volume = row.get('volume')
            if type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0:
                self.previous = self.value = None
                return {'value': None}
            self.value = 0.0 if self.previous is None else self.value + (volume if close > self.previous else -volume if close < self.previous else 0)
            result = {'value': self.value}
        elif self.kind == 'stochastic':
            result = {'k': None, 'd': None}
            self.samples.append((high, low))
            if len(self.samples) == self.params['period']:
                highest = max(h for h, _ in self.samples)
                lowest = min(l for _, l in self.samples)
                # Explicit flat-window policy: zero; never infer missing data.
                self.raw.append((close-lowest)/(highest-lowest)*100 if highest != lowest else 0.0)
                if len(self.raw) == self.params['smooth']:
                    value = sum(self.raw)/len(self.raw)
                    self.k.append(value)
                    result['k'] = value
                    if len(self.k) == self.params['signal']:
                        result['d'] = sum(self.k)/len(self.k)
        else:
            raise ValueError('Unsupported native display formula')
        self.previous = close
        return result


def calculate(candles, instances, minutes, start, end, cancel=None):
    """One streaming replay; viewport is an output filter, never the seed."""
    width = minutes * 60
    states = {}
    count = 0
    previous = None
    gaps = 0
    unknown = 0
    columns = {i['id']: {p: [] for p in ('upper', 'middle', 'lower') if i['type'] == 'bb'} for i in instances}
    for i in instances:
        if i['type'] in formulas.FIELDS:
            columns[i['id']] = {p: [] for p in formulas.ports(i['type'])}
        elif i['type'] == 'stochastic':
            columns[i['id']] = {'k': [], 'd': []}
        elif i['type'] == 'macd':
            columns[i['id']] = {p: [] for p in ('macd', 'signal', 'histogram')}
        elif i['type'] != 'bb':
            columns[i['id']] = {'value': []}
    times = []
    directions = []
    confirmed = 0

    def reset():
        return {i['id']: formulas.FormulaState(i) if i['type'] in formulas.FIELDS else NativeDisplayState(i) if i['type'] in ('atr', 'stochastic', 'obv') else indicator_for(i) for i in instances if i['type'] != 'volume'}
    states = reset()
    for index, row in enumerate(candles):
        if index % 32 == 0 and cancel and cancel.is_set():
            raise InterruptedError('Display calculation superseded')
        stamp = row['time']
        closed = row.get('confirmation') in ('closed_rest', 'provider_confirmed', 'synthetic_closed')
        if row.get('confirmation') == 'conflict':
            raise ValueError('Confirmed candle conflict; calculation invalidated. Review the cached source.')
        # Missing timestamps and unconfirmed inputs reset the segment.
        gap = previous is not None and stamp != previous + width
        if gap or not closed:
            states = reset()
            count = 0
            if gap:
                gaps += 1
        previous = stamp
        if closed:
            count += 1
            confirmed += 1
        else:
            unknown += 1
        visible = start <= stamp <= end
        if visible:
            # Whitespace prevents lines bridging a missing candle.
            if gap and times and (times[-1] < stamp):
                times.append(stamp)
                directions.append(0)
                for ports in columns.values():
                    for values in ports.values():
                        values.append(None)
            times.append(stamp + width)
            directions.append(1 if row['close'] >= row['open'] else -1)
        for item in instances:
            ident = item['id']
            kind = item['type']
            values = {p: None for p in columns[ident]}
            if kind == 'volume':
                volume = row.get('volume')
                if type(volume) in (int, float) and math.isfinite(volume) and (volume >= 0):
                    values['value'] = volume
            elif closed:
                state = states[ident]
                source = row['close']
                if kind in formulas.FIELDS or kind in ('atr', 'stochastic', 'obv'):
                    values = state.update(row)
                elif kind == 'macd':
                    line, signal = state
                    line.update_raw(source)
                    if line.initialized:
                        signal.update_raw(line.value)
                        values['macd'] = line.value
                        if signal.initialized:
                            values.update(signal=signal.value, histogram=line.value - signal.value)
                else:
                    if kind == 'bb':
                        state.update_raw(source, source, source)
                    else:
                        state.update_raw(source)
                    if state.initialized and (kind != 'rsi' or count >= item['params']['period'] + 1):
                        if kind == 'bb':
                            values = {p: getattr(state, p) for p in values}
                        else:
                            values['value'] = state.value * (100 if kind == 'rsi' else 1)
            if visible:
                for port, value in values.items():
                    if value is not None and (not math.isfinite(value)):
                        raise ValueError('Non-finite display indicator value')
                    columns[ident][port].append(value)
    return dict(times=times, columns=columns, directions=directions, confirmed=confirmed, unknown=unknown, gaps=gaps, segment_bars=count)

class DisplayIndicators:

    def __init__(self, history):
        self.history = history
        self.store = history.store
        self.lock = threading.RLock()
        self.cache = OrderedDict()
        self.condition = threading.Condition(self.lock)
        self.pending = None
        self.running = None
        self.closed = False
        with self.store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS chart_presentation_v1(market TEXT NOT NULL,symbol TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(market,symbol))')
        self.thread = threading.Thread(target=self._run, daemon=True, name='chart-display')
        self.thread.start()

    def key(self, market, symbol, source='bybit'):
        if market not in ('spot', 'linear'):
            raise ValueError('Unsupported chart market')
        validate_symbol(symbol)
        return (cache_market(market,source), symbol)

    def settings(self, market, symbol, source='bybit'):
        key = self.key(market, symbol, source)
        with self.store.connect() as db:
            row = db.execute('SELECT document FROM chart_presentation_v1 WHERE market=? AND symbol=?', key).fetchone()
        fallback = dict(version=1, revision=0, instances=[dict(id='default_volume', type='volume', params={}, color='#42cda8', visible=True, placement='overlay')], origins={})
        if row:
            try:
                doc = json.loads(row[0])
                if type(doc.get('version')) is not int or doc['version'] != 1 or type(doc.get('revision')) is not int or (doc['revision'] < 0):
                    raise ValueError()
                doc['instances'] = validate_instances(doc['instances'])
                if not isinstance(doc.get('origins'), dict) or len(doc['origins']) > 6:
                    raise ValueError()
                for interval, origin in doc['origins'].items():
                    if interval not in map(str, INTERVALS) or set(origin) != {'time', 'generation', 'contract'} or origin['contract'] != CONTRACT or (type(origin['time']) is not int) or (origin['time'] < 0) or origin['time'] % (int(interval) * 60) or (type(origin['generation']) is not int) or (origin['generation'] < 1):
                        raise ValueError()
                return doc
            except (ValueError, TypeError, KeyError, AttributeError):
                fallback['warning'] = 'Saved indicator settings are invalid or unsupported; use Apply to replace them.'
        return fallback

    def save(self, market, symbol, instances, revision, source='bybit'):
        valid = validate_instances(instances)
        if type(revision) is not int:
            raise ValueError('Invalid settings revision')
        with self.lock:
            doc = self.settings(market, symbol, source)
            if doc['revision'] != revision:
                raise ValueError('Indicator settings changed; reopen Indicators before applying')
            doc = dict(version=1, revision=revision + 1, instances=valid, origins=doc['origins'])
            self._write(cache_market(market,source), symbol, doc)
            self.cache.clear()
            if self.running:
                self.running[1].set()
            self.pending = None
            return doc

    def _write(self, market, symbol, doc):
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO chart_presentation_v1 VALUES(?,?,?)', (market, symbol, canonical(doc).decode()))

    def read(self, market, symbol, minutes, start, end, revision, reanchor=False, source='bybit', price_style='candles'):
        price_info = prices.metadata(price_style)
        self.key(market, symbol, source)
        if type(minutes) is not int or minutes not in INTERVALS:
            raise ValueError('Unsupported native interval')
        if type(start) is not int or type(end) is not int or start < 0 or (end < start) or start % (minutes * 60) or end % (minutes * 60):
            raise ValueError('Invalid chart window')
        if type(reanchor) is not bool or type(revision) is not int:
            raise ValueError('Invalid calculation request')
        with self.lock:
            if self.closed:
                raise ValueError('Display calculation is stopping')
            doc = self.settings(market, symbol, source)
            if doc['revision'] != revision:
                raise ValueError('Settings changed; calculation superseded')
            self.history.capture_hub(market, symbol, minutes, source)
            with self.store.connect() as db:
                key = (cache_market(market,source), symbol, minutes)
                origin = doc['origins'].get(str(minutes))
                if origin is None or reanchor:
                    first = db.execute('SELECT MIN(time) FROM (SELECT time FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? ORDER BY time DESC LIMIT ?)', (*key, MAX_BARS)).fetchone()[0]
                    if reanchor:
                        first = db.execute('SELECT MIN(time) FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=?', key).fetchone()[0]
                    if first is None:
                        return dict(status='empty', message='No cached native history. Indicators never fetch history.', settings=doc, times=[], columns={}, price_candles=[], **price_info)
                    candidate = dict(time=first, generation=origin['generation'] + 1 if origin else 1, contract=CONTRACT)
                else:
                    candidate = origin
                rows = db.execute('SELECT c.candle,p.provenance,p.content_hash,p.conflict FROM chart_candles_v1 c LEFT JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) WHERE c.market=? AND c.symbol=? AND c.minutes=? AND c.time>=? AND c.time<=? ORDER BY c.time LIMIT ?', (*key, candidate['time'], max(end, candidate['time']), MAX_BARS + 1)).fetchall()
                if len(rows) > MAX_BARS:
                    raise ValueError('Saved calculation origin exceeds 10,000 cached bars. Recursive calculation is unavailable; origin was not changed.')
                candles = [self.history.annotate(r) for r in rows]
                if not candles or candles[0]['time'] != candidate['time']:
                    raise ValueError('Saved calculation origin is missing from cache; no silent reseeding')
                # Finite windows can use a bounded local prefix. Recursive
                # values before their persisted origin remain unavailable.
                if start < candidate['time']:
                    prefix = db.execute('SELECT c.candle,p.provenance,p.content_hash,p.conflict FROM chart_candles_v1 c LEFT JOIN chart_confirmation_v1 p USING(market,symbol,minutes,time) WHERE c.market=? AND c.symbol=? AND c.minutes=? AND c.time>=? AND c.time<? ORDER BY c.time LIMIT 2801', (*key, max(0, start - 999 * minutes * 60), min(end + minutes * 60, candidate['time']))).fetchall()
                else:
                    prefix = []
            if len(candles) + len(prefix) > MAX_BARS:
                raise ValueError('Combined cached prefix exceeds the 10,000-bar work budget')
            if sum((start <= c['time'] <= end for c in candles)) + sum((start <= json.loads(r['candle'])['time'] <= end for r in prefix)) > 1800:
                raise ValueError('Indicator output exceeds the 1,800-bar viewport budget')
            if candidate != origin:
                doc['origins'][str(minutes)] = candidate
                self._write(cache_market(market,source), symbol, doc)
            # Forming volume is projected after replay, so ticks cannot
            # cancel or reseed unchanged confirmed calculations.
            transient = []
            current_forming = None
            if (source,market, symbol) == (getattr(self.history.hub,'source','bybit'),self.history.hub.market, self.history.hub.symbol):
                known = {c['time'] for c in candles}
                observed = self.history.hub.latest(INTERVALS[minutes])
                transient = [self.history.payload(r) for r in observed if start <= r['time'] <= end and r['time'] not in known and (r.get('confirmed') is not True)]
                latest = max(observed, key=lambda r: r['time'], default=None)
                if latest and latest.get('confirmed') is not True and start <= latest['time'] <= end:
                    if latest.get('conflict'):
                        raise ValueError('Confirmed candle conflict; calculation invalidated')
                    # Legacy cache rows remain unavailable, even if the hub now
                    # observes that timestamp without an explicit confirmation.
                    if latest['time'] not in known and latest['time'] > candles[-1]['time']:
                        current_forming = self.history.payload(latest)
            if sum((start <= c['time'] <= end for c in candles)) + sum((start <= json.loads(r['candle'])['time'] <= end for r in prefix)) + len(transient) > 1800:
                raise ValueError('Indicator output exceeds the 1,800-bar viewport budget')
            if any((c['confirmation'] == 'conflict' for c in candles)):
                raise ValueError('Confirmed candle conflict; calculation invalidated. Review the cached source.')
            cache_key = digest([key, candidate, doc['instances'], candles, [dict(r) for r in prefix], start, end, price_style, price_info['price_contract']])

            def compute(cancel):
                output = calculate(candles, [i for i in doc['instances'] if i['visible']], minutes, start, end, cancel)
                if prefix:
                    volume_only = [i for i in doc['instances'] if i['type'] in ('volume', 'sma', 'bb') and i['visible']]
                    earlier = calculate([self.history.annotate(r) for r in prefix], volume_only, minutes, start, end, cancel)
                    # Both replays are individually segmented. Also break their
                    # join when the missing candle is immediately before origin,
                    # including period-1 indicators which need no warmup gap.
                    if earlier['times'] and output['times'] and output['times'][0] > earlier['times'][-1] + minutes * 60:
                        output['times'].insert(0, output['times'][0] - minutes * 60)
                        output['directions'].insert(0, 0)
                        for ports in output['columns'].values():
                            for values in ports.values():
                                values.insert(0, None)
                    for ident, ports in output['columns'].items():
                        for port, values in ports.items():
                            ports[port] = earlier['columns'].get(ident, {}).get(port, [None] * len(earlier['times'])) + values
                    output['times'] = earlier['times'] + output['times']
                    output['directions'] = earlier['directions'] + output['directions']
                output['price_candles'], price_state = [], None
                if price_style == 'heikin_ashi':
                    output['price_candles'], price_state = prices.replay(candles, price_style, minutes, start, end, cancel)
                    if prefix:
                        earlier_prices, _ = prices.replay([self.history.annotate(r) for r in prefix], price_style, minutes, start, end, cancel, before_origin=True)
                        output['price_candles'] = earlier_prices + output['price_candles']
                output.update(price_info)
                output['formula_metadata'] = {i['id']: formulas.metadata(i) for i in doc['instances'] if i['type'] in formulas.FIELDS}
                output.update(status='ready', settings=doc, origin=candidate, revision=cache_key, before_origin=start < candidate['time'], volume_unit=('contracts' if market=='linear' else 'base currency')+' (OKX native); up = close ≥ open, down = close < open' if source=='okx' else 'source-native units (unverified); up = close ≥ open, down = close < open')
                if len(canonical(output)) > 900 * 1024:
                    raise ValueError('Indicator output exceeds transport budget; hide or remove some indicators')
                output['_price_state'] = price_state
                return output
            if cache_key in self.cache:
                output = copy.deepcopy(self.cache[cache_key])
                price_state = output.pop('_price_state', None)
                output.update(price_info)
                output.setdefault('price_candles', [])
                if output['status'] == 'ready' and transient:
                    for row in sorted(transient, key=lambda r: r['time']):
                        stamp = row['time'] + minutes * 60
                        # Hub transient rows may extend only the output suffix.
                        if output['times'] and stamp <= output['times'][-1]:
                            continue
                        output['times'].append(stamp)
                        output['directions'].append(1 if row['close'] >= row['open'] else -1)
                        for item in doc['instances']:
                            if item['id'] in output['columns']:
                                for port, values in output['columns'][item['id']].items():
                                    values.append(row.get('volume') if item['type'] == 'volume' else None)
                        output['unknown'] += 1
                    output['revision'] = digest([cache_key, transient])
                if output['status'] == 'ready':
                    if price_style == 'heikin_ashi' and current_forming is not None:
                        output['price_candles'].append(prices.preview(current_forming, price_style, minutes, price_state))
                    # Enforce the combined payload after all transient projections.
                    if len(canonical(output)) > 900 * 1024:
                        raise ValueError('Indicator output exceeds transport budget; hide or remove some indicators')
                return output
            if not self.running or self.running[0] != cache_key or self.running[1].is_set():
                if self.running:
                    self.running[1].set()
                self.pending = (cache_key, compute)
                self.condition.notify()
            return dict(status='calculating', message='Calculating cached confirmed history…', settings=doc, origin=candidate, times=[], columns={}, price_candles=[], **price_info)

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.closed or self.pending is not None)
                if self.closed:
                    return
                key, compute = self.pending
                self.pending = None
                cancel = threading.Event()
                self.running = (key, cancel)
            try:
                result = compute(cancel)
            except InterruptedError:
                result = None
            except Exception:
                result = dict(status='error', error='Display calculation failed or is inconsistent; price browsing remains available.', times=[], columns={})
            with self.condition:
                if not cancel.is_set() and result is not None:
                    self.cache[key] = result
                    while len(self.cache) > 2:
                        self.cache.popitem(last=False)
                self.running = None

    def close(self):
        with self.condition:
            self.closed = True
            self.pending = None
            if self.running:
                self.running[1].set()
            self.condition.notify()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Display calculation shutdown is still pending')
