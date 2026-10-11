"""Independent HA arithmetic and bounded shared-worker integration checks."""
import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from terminal import chart_presentation as prices
from terminal.chart_history import ChartHistory
from terminal.data import canonical, digest
from terminal.display_indicators import CONTRACT, DisplayIndicators, calculate
from terminal.market_hub import MarketHub
from terminal.service import AppService
from terminal.storage import RunStore


def row(stamp, opening=10, high=16, low=8, close=14, confirmation='synthetic_closed'):
    return dict(time=stamp, open=opening, high=high, low=low, close=close,
                volume=3, confirmation=confirmation)


def oracle(rows):
    """Fraction arithmetic, independently specified outside production helper."""
    previous = None
    expected = []
    for r in rows:
        closing = sum(Fraction(r[k]) for k in ('open', 'high', 'low', 'close')) / 4
        opening = (Fraction(r['open']) + Fraction(r['close'])) / 2 if previous is None else sum(previous) / 2
        expected.append((opening, max(r['high'], opening, closing), min(r['low'], opening, closing), closing))
        previous = opening, closing
    return expected


class PriceArithmeticTests(unittest.TestCase):
    def test_fraction_oracle_extrema_and_future_perturbation(self):
        rows = [row(0), row(60, 20, 24, 18, 22), row(120, 3, 6, 1, 4)]
        result, state = prices.replay(rows, 'heikin_ashi', 1, 0, 120)
        for actual, expected in zip(result, oracle(rows)):
            self.assertEqual([actual[k] for k in ('open', 'high', 'low', 'close')], list(map(float, expected)))
        self.assertEqual([p['time'] for p in result], [60, 120, 180])
        self.assertEqual(result[1]['low'], 12)  # HA opening extends below raw low.
        self.assertGreater(result[2]['high'], rows[2]['high'])
        self.assertEqual(result[0]['seed'], 'midpoint')
        self.assertEqual(result[1]['seed'], 'previous_confirmed')
        changed = copy.deepcopy(rows); changed[-1]['close'] = 5
        self.assertEqual(prices.replay(changed, 'heikin_ashi', 1, 0, 120)[0][:-1], result[:-1])
        self.assertEqual(state[0], 120)

    def test_gap_unknown_reset_conflict_and_preorigin(self):
        rows = [row(0), row(120, 20, 24, 18, 22), row(180, confirmation='legacy_unknown'), row(240)]
        result, _ = prices.replay(rows, 'heikin_ashi', 1, 0, 240)
        self.assertEqual(result[1]['open'], 21)
        self.assertEqual(result[2], dict(time=240, status='unavailable', seed=None, reason='unconfirmed_history'))
        self.assertEqual(result[3]['open'], 12)
        prefix, state = prices.replay(rows, 'heikin_ashi', 1, 0, 240, before_origin=True)
        self.assertTrue(all(p['reason'] == 'before_origin' for p in prefix)); self.assertIsNone(state)
        with self.assertRaisesRegex(ValueError, 'conflict'):
            prices.replay([row(0, confirmation='conflict')], 'heikin_ashi', 1, 0, 0)

    def test_preview_never_advances_seed_and_confirmation_matches(self):
        rows = [row(0), row(60, 20, 24, 18, 22)]
        _, state = prices.replay(rows, 'heikin_ashi', 1, 0, 60)
        original = state
        forming = row(120, 30, 40, 25, 35)
        first = prices.preview(forming, 'heikin_ashi', 1, state)
        for close in (32, 38, 35):
            forming['close'] = close
            next_tick = prices.preview(forming, 'heikin_ashi', 1, state)
            self.assertEqual(next_tick['open'], first['open'])
            self.assertEqual(state, original)
        confirmed, _ = prices.replay(rows + [forming], 'heikin_ashi', 1, 0, 120)
        self.assertEqual({k: first[k] for k in ('open','high','low','close')}, {k: confirmed[-1][k] for k in ('open','high','low','close')})
        for missing in (None, (0, 12, 12)):
            provisional = prices.preview(forming, 'heikin_ashi', 1, missing)
            self.assertEqual(provisional['seed'], 'provisional_midpoint')
            self.assertEqual(provisional['open'], 32.5)

    def test_cancellation_checked_every_32_inputs(self):
        cancel = Mock(); cancel.is_set.side_effect = [False, True]
        with self.assertRaises(InterruptedError):
            prices.replay([row(i*60) for i in range(100)], 'heikin_ashi', 1, 0, 6000, cancel)
        self.assertEqual(cancel.is_set.call_count, 2)


class PriceWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RunStore(Path(self.temp.name))
        self.hub = MarketHub()
        self.chart = ChartHistory(self.store, self.hub); self.chart.close()
        self.display = DisplayIndicators(self.chart)
        self.display.save('spot', 'BTCUSDT', [], 0)

    def tearDown(self):
        self.display.close(); self.temp.cleanup()

    def seed(self, rows, source='bybit', minutes=1, symbol='BTCUSDT'):
        market = 'spot' if source == 'bybit' else 'okx:spot'
        with self.store.connect() as db:
            for r in rows:
                payload = ChartHistory.payload(r); key = (market, symbol, minutes, r['time'])
                db.execute('INSERT OR IGNORE INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(payload).decode()))
                if r.get('confirmation') != 'legacy_unknown':
                    db.execute('INSERT OR IGNORE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key, digest(payload), r.get('confirmation','synthetic_closed')))

    def read(self, start=0, end=120, **kwargs):
        args = dict(market='spot', symbol='BTCUSDT', minutes=1, start=start, end=end, revision=1, price_style='heikin_ashi')
        args.update(kwargs)
        for _ in range(300):
            result = self.display.read(**args)
            args.pop('reanchor', None)
            if result['status'] != 'calculating':
                return result
            time.sleep(.005)
        self.fail('Replay did not finish')

    def forming(self, r):
        self.hub.source='bybit'; self.hub.market='spot'; self.hub.symbol='BTCUSDT'
        self.hub.candles={'1': {r['time']: dict(ChartHistory.payload(r), confirmed=False, provider_ms=1)}}

    def test_empty_indicators_style_identity_native_history_untouched(self):
        rows=[row(0), row(60,20,24,18,22), row(120)]
        self.seed(rows)
        with self.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM chart_candles_v1')]
        ha=self.read(); native=self.read(price_style='candles')
        self.assertEqual(ha['columns'], {})
        self.assertEqual(len(ha['price_candles']), 3)
        self.assertNotEqual(ha['revision'], native['revision'])
        self.assertEqual(ha['price_contract'], 'heikin-ashi-midpoint-seed-v1')
        self.assertTrue(ha['price_metadata']['synthetic'])
        self.assertFalse(native['price_metadata']['synthetic'])
        self.assertEqual(ha['origin']['contract'], CONTRACT)
        self.assertEqual(native['price_candles'], [])  # Raw history is already owned by the caller.
        self.assertNotIn('_price_state', ha)
        with self.store.connect() as db:
            self.assertEqual(before, [tuple(r) for r in db.execute('SELECT * FROM chart_candles_v1')])
            self.assertEqual(len(list(db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'chart_presentation%'"))), 1)
        self.assertEqual(len(self.display.cache), 2)

    def test_native_maximum_viewport_does_not_replay_or_duplicate_prices(self):
        self.seed([row(i*60) for i in range(1800)])
        with patch('terminal.display_indicators.prices.replay', side_effect=AssertionError('Native prices need no replay')):
            native=self.read(0,1799*60,price_style='candles')
        self.assertEqual(native['status'],'ready')
        self.assertEqual(native['price_candles'],[])
        self.assertLess(len(canonical(native)), 40000)

    def test_overlap_prepend_trim_reopen_and_deliberate_shared_reanchor(self):
        rows=[row(i*60, 10+i%5, 20+i%5, 5+i%5, 16+i%5) for i in range(80)]
        self.seed(rows[10:])
        first=self.read(600, 1800)
        self.seed(rows[:10])
        for start,end in ((1200,3600),(600,1200),(0,1800)):
            page=self.read(start,end)
            mapping={p['time']:p for p in page['price_candles']}
            for p in first['price_candles']:
                if p['time'] in mapping:self.assertEqual(p,mapping[p['time']])
            self.assertEqual(page['origin'], first['origin'])
        before=self.read(0,540)
        self.assertTrue(all(p['reason']=='before_origin' for p in before['price_candles']))
        self.display.close(); self.display=DisplayIndicators(self.chart)
        self.assertEqual(first['price_candles'], self.read(600,1800)['price_candles'])
        newer=self.read(600,1800,reanchor=True)
        self.assertEqual(newer['origin']['time'],0)
        self.assertEqual(newer['origin']['generation'],2)
        self.assertEqual(self.read(600,1800,price_style='candles')['origin'],newer['origin'])
        self.assertNotEqual(newer['price_candles'][0]['open'],first['price_candles'][0]['open'])

    def test_repeat_ticks_then_confirm_cache_stays_independent(self):
        self.seed([row(0),row(60,20,24,18,22)])
        self.forming(row(120,30,40,25,35))
        with patch('terminal.display_indicators.calculate', wraps=calculate) as work:
            first=self.read(); keys=list(self.display.cache)
            for close in (32,38,35):
                self.hub.candles['1'][120]['close']=close
                result=self.read()
                self.assertEqual(result['price_candles'][-1]['open'],first['price_candles'][-1]['open'])
                self.assertEqual(list(self.display.cache), keys)
                self.assertNotIn('_price_state', result)
            self.assertEqual(work.call_count,1)
            self.hub.candles['1'][120]['confirmed']=True
            confirmed=self.read()
            self.assertEqual(work.call_count,2)
        self.assertEqual(confirmed['price_candles'][-1]['status'],'confirmed')
        for k in ('open','high','low','close'):
            self.assertEqual(confirmed['price_candles'][-1][k],first['price_candles'][-1][k])
        self.assertEqual(first['price_candles'][-1]['status'],'forming')

    def test_unknown_historical_and_discontinuous_forming_are_explicit(self):
        self.seed([row(0),row(60,confirmation='legacy_unknown')])
        self.forming(row(60))
        result=self.read()
        self.assertEqual(result['price_candles'][-1]['status'],'unavailable')
        self.forming(row(120))
        result=self.read()
        self.assertEqual(result['price_candles'][-1]['seed'],'provisional_midpoint')
        self.forming(row(240))
        self.assertEqual(self.read(end=240)['price_candles'][-1]['seed'],'provisional_midpoint')
        # A stale hub observation cannot append a price before confirmed suffix.
        self.seed([row(300)]); self.forming(row(180))
        result=self.read(end=300)
        self.assertEqual(result['price_candles'][-1]['time'],360)
        self.assertFalse(any(p['status']=='forming' for p in result['price_candles']))

    def test_source_symbol_timeframe_origins_and_preview_are_isolated(self):
        self.seed([row(0),row(60)])
        self.seed([row(600,30,40,20,36)], source='okx')
        self.seed([row(3000,50,60,40,56)], minutes=5)
        self.seed([row(900,70,80,60,76)], symbol='ETHUSDT')
        self.forming(row(120))
        bybit=self.read()
        okx=self.read(600,720,source='okx',revision=0)
        coarse=self.read(3000,3300,minutes=5)
        other=self.read(900,1020,symbol='ETHUSDT',revision=0)
        self.assertEqual([p['origin']['time'] for p in (bybit,okx,coarse,other)],[0,600,3000,900])
        self.assertEqual(len(okx['price_candles']),1)
        self.assertEqual(coarse['price_candles'][0]['time'],3300)
        self.assertEqual(other['price_candles'][0]['open'],73)

    def test_missing_origin_and_10001_budget_never_reseed(self):
        self.seed([row(i*60) for i in range(10000)])
        result=self.read()
        self.seed([row(600000)])
        with self.assertRaisesRegex(ValueError,'10,000'):
            self.read(599940,600000)
        self.assertEqual(self.display.settings('spot','BTCUSDT')['origins']['1'],result['origin'])
        with self.store.connect() as db:db.execute('DELETE FROM chart_candles_v1 WHERE time=0')
        with self.assertRaisesRegex(ValueError,'origin is missing'):
            self.read()

    def test_output_budget_empty_and_conflict(self):
        empty=self.read()
        self.assertEqual(empty['status'],'empty'); self.assertEqual(empty['price_candles'],[])
        self.assertNotIn('1',self.display.settings('spot','BTCUSDT')['origins'])
        self.seed([row(i*60) for i in range(1801)])
        with self.assertRaisesRegex(ValueError,'1,800'):
            self.read(0,108000)
        with self.store.connect() as db:db.execute('UPDATE chart_confirmation_v1 SET conflict=1 WHERE time=0')
        with self.assertRaisesRegex(ValueError,'conflict'):
            self.read()

    def test_coalesced_worker_stale_result_and_shutdown(self):
        self.seed([row(i*60) for i in range(200)])
        entered=threading.Event(); release=threading.Event()
        def slow(*args,**kwargs):
            entered.set(); release.wait(2)
            return calculate(*args,**kwargs)
        with patch('terminal.display_indicators.calculate',side_effect=slow):
            first=self.display.read('spot','BTCUSDT',1,0,120,1,price_style='heikin_ashi')
            self.assertEqual(first['status'],'calculating'); self.assertTrue(entered.wait(1))
            stale_key=self.display.running[0]
            self.forming(row(180))
            self.display.read('spot','BTCUSDT',1,0,120,1,price_style='heikin_ashi')
            self.assertFalse(self.display.running[1].is_set())
            for end in (180,240,300):self.display.read('spot','BTCUSDT',1,0,end,1,price_style='heikin_ashi')
            self.assertTrue(self.display.running[1].is_set())
            self.assertIsNotNone(self.display.pending)
            release.set(); result=self.read(0,300)
            self.assertEqual(result['status'],'ready')
            self.assertNotIn(stale_key,self.display.cache)
        for end in (360,420,480):self.read(0,end)
        self.assertLessEqual(len(self.display.cache),2)
        entered.clear(); release.clear()
        with patch('terminal.display_indicators.calculate',side_effect=slow):
            self.display.read('spot','BTCUSDT',1,0,540,1,price_style='heikin_ashi')
            self.assertTrue(entered.wait(1))
            timer=threading.Timer(.02,release.set); timer.start()
            self.display.close(); timer.join()
        self.assertFalse(self.display.thread.is_alive())
        self.assertIsNone(self.display.pending)
        with self.assertRaisesRegex(ValueError,'stopping'):self.read()

    def test_complete_projected_payload_and_service_envelope_budget(self):
        self.seed([row(0),row(60)])
        self.forming(row(120))
        self.read(end=120)
        key=next(iter(self.display.cache))
        cached=self.display.cache[key]
        public={k:v for k,v in cached.items() if k!='_price_state'}
        # Fill just below the limit, then add the forming projection.
        cached['padding']='x'*(900*1024-len(canonical(public))-len(canonical({'padding':''})))
        self.assertLess(len(canonical({k:v for k,v in cached.items() if k!='_price_state'})),900*1024)
        self.forming(row(120))
        projected=self.read()
        self.assertEqual(projected['status'],'ready')
        self.assertGreater(len(canonical(projected)),900*1024)
        service=AppService.__new__(AppService)
        from terminal.indicator_transport import IndicatorTransport
        service.indicator_transport=IndicatorTransport()
        service.display_indicators=Mock()
        service.display_indicators.read.return_value={'padding':'x'*(900*1024-30)}
        response=service.handle(dict(version=1,id='r'*80,command='chart_indicator_read',params=dict(market='spot',symbol='BTCUSDT',minutes=1,start=0,end=120,revision=1,reanchor=False)))
        self.assertEqual(response['type'],'result')
        self.assertEqual(response['result']['status'],'paged')
        service.indicator_transport.close()

    def test_optional_service_parameter_strict_allowlist_and_style_validation(self):
        self.seed([row(0)])
        service=AppService.__new__(AppService); service.display_indicators=self.display
        from terminal.indicator_transport import IndicatorTransport
        service.indicator_transport=IndicatorTransport(); self.addCleanup(service.indicator_transport.close)
        params=dict(market='spot',symbol='BTCUSDT',minutes=1,start=0,end=0,revision=1,reanchor=False)
        def call(p):return service.handle(dict(version=1,id='test',command='chart_indicator_read',params=p))
        default=call(params)
        self.assertEqual(default['type'],'result')
        self.assertEqual(default['result']['price_style'],'candles')
        self.assertEqual(call(dict(params,price_style='heikin_ashi'))['type'],'result')
        for style in (None,True,[],{},'HA'):
            self.assertEqual(call(dict(params,price_style=style))['type'],'error')
        self.assertEqual(call(dict(params,price_style='heikin_ashi',origin=0))['type'],'error')
