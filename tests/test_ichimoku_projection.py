"""Independent arithmetic, ordinal/provenance and bounded transport expectations."""
import copy
import threading
import time
import unittest
from unittest.mock import patch

from terminal.data import canonical, digest
from terminal.market_sources import cache_market
from terminal.display_indicators import calculate, validate_instances, DisplayIndicators
from terminal.display_formula_catalog import FormulaState, metadata
import test_display_indicators as cache_tests
from test_display_indicators import instance


def ichi(**params):
    return instance('ichimoku', **(dict(conversion=2, base=3, span_b=4, displacement=2) | params))


def rows(n=6):
    return [dict(time=i*60, open=float(i+1), high=float(i+2), low=float(i), close=float(i+1), volume=1., confirmation='synthetic_closed') for i in range(n)]


def project(data, item=None, start=0, end=None):
    return calculate(data, [item or ichi()], 1, start, data[-1]['time'] if end is None else end)


class IchimokuArithmeticTests(unittest.TestCase):
    def test_independent_small_golden_and_exact_schema(self):
        data = rows()
        state = FormulaState(ichi())
        values = [state.update(r) for r in data]
        self.assertEqual(values[2], dict(tenkan=2.5, kijun=2., senkou_a=2.25, senkou_b=None, chikou=3.))
        self.assertEqual(values[3]['senkou_b'], 2.5)
        self.assertEqual((values[5]['senkou_a'], values[5]['senkou_b']), (5.25, 4.5))
        out = project(data)
        self.assertEqual(set(out['columns']['ichimoku']), {'tenkan', 'kijun'})
        env = out['projections']; p = env['instances']['ichimoku']
        self.assertEqual(env['raw_times'], [60,120,180,240,300,360])
        self.assertEqual(env['horizon'], 360)
        i = p['computed_at'].index(180)
        self.assertEqual((p['source_logical'][i], p['senkou_plotted_at'][i], p['chikou_plotted_at'][i]), (2,300,60))
        self.assertEqual(p['chikou'][i], 3.)
        self.assertEqual(p['senkou_plotted_at'][-1], 480)
        self.assertTrue(p['senkou_estimated'][-1])
        self.assertEqual({len(v) for k,v in p.items() if k != 'displacement'}, {4})

    def test_strict_field_bounds_and_metadata(self):
        validate_instances([ichi(conversion=1000, base=1, span_b=1000, displacement=100)])
        for field in ('conversion', 'base', 'span_b', 'displacement'):
            for value in (True, False, 0, -1, 1.5, float('inf'), float('nan'), 1001):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_instances([ichi(**{field:value})])
        with self.assertRaises(ValueError): validate_instances([ichi(displacement=101)])
        with self.assertRaises(ValueError): validate_instances([ichi(unknown=1)])
        self.assertEqual(metadata(ichi())['port_warmup_bars']['senkou_b'], 4)
        self.assertEqual(metadata(ichi())['contract'], 'ichimoku-raw-ordinal-v1')

    def test_left_prefix_matches_whole_geometry(self):
        data = rows(20)
        whole = project(data)['projections']['instances']['ichimoku']
        page = project(data, start=600)['projections']['instances']['ichimoku']
        self.assertEqual(page['source_logical'][0], -2)
        self.assertEqual(page['computed_at'][0], 540)
        for stamp, a, b in zip(page['computed_at'], page['senkou_a'], page['senkou_b']):
            k = whole['computed_at'].index(stamp)
            self.assertEqual((a,b), (whole['senkou_a'][k], whole['senkou_b'][k]))
        self.assertIsNone(page['chikou'][0])

    def test_asof_horizon_and_future_perturbation(self):
        data = rows(20)
        short = project(data[:10])
        self.assertEqual(project(data, end=540), short)
        changed = copy.deepcopy(data)
        for r in changed[10:]: r.update(close=99999., high=100000.)
        self.assertEqual(project(changed, end=540), short)
        p = short['projections']['instances']['ichimoku']
        self.assertEqual(max(t for t in p['chikou_plotted_at'] if t is not None), 480)
        old = project(data)['projections']['instances']['ichimoku']
        new = project(changed)['projections']['instances']['ichimoku']
        for k, stamp in enumerate(old['computed_at']):
            if stamp <= 600:
                for field in ('senkou_a', 'senkou_b', 'chikou'):
                    self.assertEqual(old[field][k], new[field][k])

    def test_gap_counts_raw_bars_and_segments_reset(self):
        data = rows(12)
        del data[5]
        out = project(data); p = out['projections']['instances']['ichimoku']
        self.assertNotIn(360, out['projections']['raw_times'])
        k = p['computed_at'].index(300)
        self.assertEqual(p['senkou_plotted_at'][k], 480)  # raw target skips missing bar
        k = p['computed_at'].index(420)
        self.assertIsNone(p['senkou_a'][k])
        self.assertIsNone(p['senkou_b'][k])
        self.assertNotEqual(p['segment'][k], p['segment'][k-1])
        self.assertEqual(p['chikou_plotted_at'][k], 240)

    def test_unknown_and_forming_occupy_slots_without_inputs(self):
        for confirmation in ('legacy_unknown', 'forming'):
            data = rows(12); data[5]['confirmation'] = confirmation
            p = project(data)['projections']['instances']['ichimoku']
            self.assertNotIn(360, p['computed_at'])
            k = p['computed_at'].index(300)
            self.assertEqual(p['senkou_plotted_at'][k], 420)
            k = p['computed_at'].index(420)
            self.assertIsNone(p['senkou_b'][k])
            self.assertEqual(p['chikou_plotted_at'][k], 300)

    def test_full_horizon_and_bounded_source_support(self):
        data = rows(10000)
        out = project(data, ichi(displacement=100), start=8200*60)
        p = out['projections']['instances']['ichimoku']
        self.assertEqual(len(out['projections']['raw_times']), 1800)
        self.assertEqual(len(p['computed_at']), 1900)
        self.assertEqual(p['source_logical'][0], -100)
        self.assertEqual(p['source_logical'][-1]+100, 1899)
        self.assertEqual(p['senkou_plotted_at'][-1], 606000)
        self.assertEqual(sum(p['senkou_estimated']), 100)

    def test_cancellation_conflict_and_graph_separation(self):
        event = threading.Event(); event.set()
        with self.assertRaises(InterruptedError): calculate(rows(), [ichi()], 1, 0, 300, event)
        data = rows(); data[3]['confirmation'] = 'conflict'
        with self.assertRaisesRegex(ValueError, 'conflict'): project(data)
        from terminal.graph import indicator_for
        self.assertIsNone(indicator_for(ichi()))


class IchimokuCacheTests(unittest.TestCase):
    setUp = cache_tests.DisplayCacheTests.setUp
    tearDown = cache_tests.DisplayCacheTests.tearDown
    seed = cache_tests.DisplayCacheTests.seed
    read = cache_tests.DisplayCacheTests.read



    def test_paging_prefix_reanchor_reopen_source(self):
        data = rows(300); self.seed(data[20:])
        self.settings = self.display.save('spot','BTCUSDT',[ichi()],0)
        first = self.read(6000,11940)
        p = first['projections']
        self.assertEqual(p['context'], dict(source='bybit',market='spot',symbol='BTCUSDT',minutes=1,start=6000,end=11940,generation=1,origin=1200,settings_revision=1))
        self.seed(data[:20])
        before = self.read(0,11940)
        q = before['projections']['instances']['ichimoku']
        self.assertGreaterEqual(min(q['computed_at']), 1260)
        self.assertEqual(before['projections']['raw_times'][0], 60)
        reanchor = self.read(0,11940,reanchor=True)
        self.assertEqual(reanchor['projections']['context']['generation'], 2)
        self.assertLess(min(reanchor['projections']['instances']['ichimoku']['computed_at']),1260)
        self.display.close(); self.display = DisplayIndicators(self.chart)
        self.assertEqual(self.read(0,11940)['projections'], reanchor['projections'])
        other = self.display.settings('spot','BTCUSDT','okx')
        self.assertNotIn('ichimoku', [item['type'] for item in other['instances']])
        self.assertEqual(other['origins'], {})


    def test_large_projection_is_complete_for_paged_transport(self):
        self.seed(rows(1900))
        items = [dict(ichi(conversion=1,base=1,span_b=1,displacement=100), id=f'cloud{i}') for i in range(8)]
        self.settings=self.display.save('spot','BTCUSDT',items,0)
        out=self.read(6000,113940)
        self.assertEqual(out['status'],'ready')
        self.assertGreater(len(canonical(out)),900*1024)
        self.assertEqual(len(out['projections']['instances']),8)
        self.assertEqual(out['projections']['contract'],'ichimoku-raw-ordinal-v1')


    def test_forming_axis_and_tick_does_not_recompute(self):
        data=rows(8); self.seed(data[:6])
        self.settings=self.display.save('spot','BTCUSDT',[ichi()],0)
        self.hub.market='spot'; self.hub.symbol='BTCUSDT'
        self.hub.candles={'1':{360:dict(self.chart.payload(data[6]),confirmed=False,provider_ms=360000)}}
        out=self.read(0,360); p=out['projections']
        self.assertEqual(p['raw_times'][-1],420)
        self.assertNotIn(420,p['instances']['ichimoku']['computed_at'])
        with patch('terminal.display_indicators.calculate', wraps=calculate) as calculation:
            self.hub.candles['1'][360]['close']=500.
            tick=self.read(0,360)
            self.assertEqual(tick['projections'],p)
            self.assertEqual(calculation.call_count,0)

    def test_source_timeframe_and_hidden_instance_isolation(self):
        data = rows(30)
        self.seed(data)
        self.settings = self.display.save('spot', 'BTCUSDT', [ichi()], 0)
        base = self.read(0, 1740)
        with self.store.connect() as db:
            for minutes, source, scale in ((1, 'okx', 10), (5, 'bybit', 100)):
                for row in data:
                    payload = self.chart.payload(dict(row, time=row['time']*minutes,
                        open=row['open']*scale, high=row['high']*scale, low=row['low']*scale, close=row['close']*scale))
                    key = (cache_market('spot', source), 'BTCUSDT', minutes, payload['time'])
                    db.execute('INSERT INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(payload).decode()))
                    db.execute('INSERT INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key,digest(payload),'synthetic_closed'))
        self.display.save('spot', 'BTCUSDT', [ichi()], 0, source='okx')
        for minutes, source, scale in ((1, 'okx', 10), (5, 'bybit', 100)):
            for _ in range(300):
                out = self.display.read('spot', 'BTCUSDT', minutes, 0, 1740*minutes, 1, source=source)
                if out['status'] != 'calculating': break
                time.sleep(.01)
            self.assertEqual(out['status'], 'ready')
            self.assertEqual(out['projections']['context']['source'], source)
            self.assertEqual(out['projections']['context']['minutes'], minutes)
            self.assertEqual(out['projections']['instances']['ichimoku']['senkou_a'][-1],
                             base['projections']['instances']['ichimoku']['senkou_a'][-1]*scale)
        self.settings = self.display.save('spot', 'BTCUSDT', [dict(ichi(), visible=False)], 1)
        self.assertEqual(self.read(0,1740)['projections']['instances'], {})

    def test_combined_forming_input_budget(self):
        data = rows(10001)
        self.seed(data[:10000])
        self.settings = self.display.save('spot', 'BTCUSDT', [ichi()], 0)
        self.hub.market='spot'; self.hub.symbol='BTCUSDT'
        self.hub.candles={'1':{600000:dict(self.chart.payload(data[-1]),confirmed=False,provider_ms=600000000)}}
        with self.assertRaisesRegex(ValueError, '10,000-bar work budget'):
            self.read(9999*60,10000*60)
