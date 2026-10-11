"""Independent arithmetic and presentation boundaries for the chart-only catalog."""
import copy
import hashlib
import json
import math
import threading
import unittest
from terminal import display_formula_catalog as formulas
from terminal.data import canonical
from terminal.indicator_transport import IndicatorTransport
from terminal.display_indicators import calculate, validate_instances, DisplayIndicators
from tests.test_display_indicators import instance, candles
from tests import test_display_indicators as infrastructure

ITEMS = [instance(kind, **({'period': 3, 'atr_period': 2, 'multiplier': 2} if kind == 'keltner' else {'period': 3})) for kind in formulas.FIELDS]


def replay(rows, items=ITEMS):
    # Keep the original independent arithmetic batches; instance count is uncapped.
    columns = {}
    for offset in range(0, len(items), 8):
        columns.update(calculate(rows, items[offset:offset+8], 1, 0, rows[-1]['time'])['columns'])
    return columns


class FormulaArithmeticTests(unittest.TestCase):
    def test_independent_short_goldens(self):
        rows = candles([2, 4, 8, 6, 10])
        for row, volume in zip(rows, [1, 2, 3, 4, 5]):
            row['volume'] = volume
        out = replay(rows)
        expected = {
            'wma': [None, None, 17/3, 19/3, 25/3],
            'rma': [None, None, 14/3, 46/9, 182/27],
            'vwma': [None, None, 17/3, 56/9, 49/6],
            'roc': [None, None, None, 200, 150],
            'momentum': [None, None, None, 4, 6],
            'cci': [None, None, 100, 0, 100],
            'williamsr': [None, None, -12.5, -50, -100/6],
            'mfi': [None, None, None, 400/7, 3700/49],
            'cmf': [None, None, 0, 0, 0],
            'stddev': [None, None, math.sqrt(56/9), math.sqrt(8/3), math.sqrt(8/3)],
        }
        for kind, values in expected.items():
            with self.subTest(kind=kind):
                for actual, wanted in zip(out[kind]['value'], values):
                    if wanted is None:
                        self.assertIsNone(actual)
                    else:
                        self.assertAlmostEqual(actual, wanted, places=10)
        self.assertEqual(out['donchian'], {'upper':[None,None,9,9,11], 'middle':[None,None,5,6,8], 'lower':[None,None,1,3,5]})
        # EMA: 2,3,5.5,5.75,7.875. TR:2,3,5,3,5. ATR:2.5,3.75,3.375,4.1875.
        self.assertEqual(out['keltner'], {'upper':[None,None,13,12.5,16.25], 'middle':[None,None,5.5,5.75,7.875], 'lower':[None,None,-2,-1,-.5]})

    def test_warmup_one_and_maximum_and_metadata(self):
        for item in ITEMS:
            kind = item['type']
            meta = formulas.metadata(item)
            self.assertEqual(meta['ports'], list(formulas.ports(kind)))
            self.assertEqual(meta['before_origin'], 'unavailable')
            self.assertTrue(meta['seed'])
            self.assertTrue(meta['confirmed_only'])
            rows = candles(list(range(1, 8)))
            for row in rows: row['volume'] = 1
            for values in replay(rows, [item])[kind].values():
                self.assertTrue(all(value is None for value in values[:meta['warmup_bars']-1]))
                self.assertIsNotNone(values[meta['warmup_bars']-1])
            for period in (1, 1000):
                changed = copy.deepcopy(item)
                changed['params']['period'] = period
                if kind == 'keltner': changed['params']['atr_period'] = period
                validate_instances([changed])
                count = formulas.metadata(changed)['warmup_bars']
                rows = candles(list(range(1, count+1)))
                for row in rows: row['volume'] = 1
                for values in replay(rows, [changed])[kind].values():
                    self.assertEqual(values[:-1], [None]*(count-1))
                    self.assertIsNotNone(values[-1])

    def test_mfi_direction_ties_and_zero_policies(self):
        item = instance('mfi', period=2)
        for closes, expected in [([1,2,3],100),([3,2,1],0),([2,2,2],None),([1,1,2],100),([3,3,2],0)]:
            rows = candles(closes)
            for row in rows: row['volume'] = 1
            self.assertEqual(replay(rows,[item])['mfi']['value'], [None,None,expected])
        rows = candles([2,2,2,2])
        for row in rows: row.update(high=2, low=2, volume=0)
        out = replay(rows)
        for kind in ('cci','williamsr','stddev'): self.assertEqual(out[kind]['value'][2:], [0,0])
        for kind in ('vwma','cmf','mfi'): self.assertTrue(all(v is None for v in out[kind]['value']))
        fractional = candles([.1]*3)
        for row in fractional: row.update(high=.1, low=.1)
        for kind in ('cci', 'stddev'):
            self.assertEqual(replay(fractional,[instance(kind,period=3)])[kind]['value'][-1],0)
        rows = candles([0,1,2,3])
        self.assertIsNone(replay(rows,[instance('roc',period=3)])['roc']['value'][-1])
        rows = candles([2,2,2])
        for row in rows: row.update(high=2,low=2,volume=1)
        self.assertEqual(replay(rows,[instance('cmf',period=3)])['cmf']['value'][-1],0)

    def test_cmf_asymmetric_closes(self):
        rows = candles([8,2,7])
        for row, volume in zip(rows,[1,2,3]):row.update(high=10,low=0,volume=volume)
        # Multipliers .6,-.6,.4; weighted sum .6 over six units volume.
        self.assertAlmostEqual(replay(rows,[instance('cmf',period=3)])['cmf']['value'][-1],.1)

    def test_invalid_volume_resets_only_volume_dependent_state(self):
        rows = candles([1,2,3,4,5,6,7,8,9])
        for row in rows:row['volume']=1
        base = replay(rows)
        for bad in (None,True,-1,float('nan'),float('inf'),'1','missing'):
            changed = copy.deepcopy(rows)
            if bad == 'missing':changed[3].pop('volume')
            else:changed[3]['volume']=bad
            out = replay(changed)
            suffix = replay(changed[4:])
            for kind, ports in out.items():
                if kind in formulas.VOLUME_KINDS:
                    self.assertIsNone(ports['value'][3])
                    self.assertEqual(ports['value'][4:],suffix[kind]['value'])
                else:self.assertEqual(ports,base[kind])

    def test_unknown_gap_future_conflict_and_cancellation(self):
        rows = candles([1,3,2,4,6,5,7,9,8,10,12,11])
        for row in rows:row['volume']=1
        base = replay(rows)
        changed = copy.deepcopy(rows);changed[-1].update(close=100,high=120,low=50,volume=9000)
        future = replay(changed)
        for kind, ports in base.items():
            for port, values in ports.items():self.assertEqual(values[:-1],future[kind][port][:-1])
        suffix = replay(rows[6:])
        for confirmation in ('forming','legacy_unknown'):
            changed = copy.deepcopy(rows);changed[5]['confirmation']=confirmation
            out = replay(changed)
            for kind, ports in out.items():
                for port, values in ports.items():
                    self.assertIsNone(values[5]);self.assertEqual(values[6:],suffix[kind][port])
        out = replay(rows[:5]+rows[6:])
        for kind, ports in out.items():
            for port, values in ports.items():
                self.assertIsNone(values[5]);self.assertEqual(values[6:],suffix[kind][port])
        changed[5]['confirmation']='conflict'
        with self.assertRaisesRegex(ValueError,'conflict'):replay(changed)
        cancel = threading.Event();cancel.set()
        with self.assertRaises(InterruptedError):calculate(rows,ITEMS[:8],1,0,660,cancel)

    def test_strict_parameters(self):
        for item in ITEMS:
            for bad in (True,False,0,1001,1.5,float('nan'),float('inf'),'3'):
                changed = copy.deepcopy(item);changed['params']['period']=bad
                with self.assertRaises(ValueError):validate_instances([changed])
            changed=copy.deepcopy(item);changed['params']['extra']=1
            with self.assertRaises(ValueError):validate_instances([changed])
            changed=copy.deepcopy(item);changed['params'].pop('period')
            with self.assertRaises(ValueError):validate_instances([changed])
        for key, bads in [('multiplier',(True,0,-1,10.1,float('inf'),float('nan'),'2')),('atr_period',(True,0,1001,2.5))]:
            for bad in bads:
                params=dict(period=3,atr_period=2,multiplier=2);params[key]=bad
                with self.assertRaises(ValueError):validate_instances([instance('keltner',**params)])
        for multiplier in (.01,10):validate_instances([instance('keltner',period=1,atr_period=1,multiplier=multiplier)])
        self.assertEqual(validate_instances(ITEMS[:9]), ITEMS[:9])


class FormulaTransportTests(unittest.TestCase):
    setUp=infrastructure.DisplayCacheTests.setUp
    tearDown=infrastructure.DisplayCacheTests.tearDown
    seed=infrastructure.DisplayCacheTests.seed
    read=infrastructure.DisplayCacheTests.read

    def test_origin_reopen_namespace_and_json_transport(self):
        rows=candles([10+i%7 for i in range(30)])
        self.seed(rows[10:])
        revision=0
        for items in (ITEMS[:8],ITEMS[8:]):
            self.settings=self.display.save('spot','BTCUSDT',items,revision)
            revision=self.settings['revision']
            original=self.read(600,1740)
            self.seed(rows[:10])
            full=self.read(0,1740)
            self.assertEqual(full['status'],'ready')
            self.assertEqual(full['origin']['time'],600)
            for ident,ports in full['columns'].items():
                self.assertEqual(full['formula_metadata'][ident],formulas.metadata(next(i for i in items if i['id']==ident)))
                for port,values in ports.items():
                    self.assertEqual(values[:10],[None]*10)
                    self.assertEqual(values[10:],original['columns'][ident][port])
            self.assertLess(len(canonical(full)),900*1024)
            self.assertEqual(self.display.settings('spot','BTCUSDT',source='okx')['revision'],0)
            self.display.close();self.display=DisplayIndicators(self.chart)
            self.assertEqual(self.read(600,1740)['columns'],original['columns'])
        with self.assertRaisesRegex(ValueError,'changed'):self.display.save('spot','BTCUSDT',[],0)

    def test_output_and_byte_budgets(self):
        rows=candles([1e100+i*1e90 for i in range(1801)])
        for row in rows:row.update(high=row['close']+1e91,low=row['close']-1e91)
        self.seed(rows)
        items=[dict(instance('keltner',period=2,atr_period=2,multiplier=2),id='channel'+str(i)) for i in range(8)]
        self.settings=self.display.save('spot','BTCUSDT',items,0)
        with self.assertRaisesRegex(ValueError,'1,800'):self.read(0,1800*60)
        result=self.read(0,1799*60)
        self.assertEqual(result['status'],'ready')
        self.assertEqual(set(result['columns']), {item['id'] for item in items})
        transport = IndicatorTransport()
        try:
            descriptor = transport.pack(result)
            self.assertEqual(descriptor['status'], 'paged')
            pages = [transport.page(descriptor['snapshot_id'], i) for i in range(descriptor['pages'])]
            self.assertTrue(all(len(canonical(page)) < 900*1024 for page in pages))
            encoded = ''.join(page['text'] for page in pages).encode()
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), descriptor['sha256'])
            self.assertEqual(json.loads(encoded), result)
        finally:
            transport.close()
        # The unchanged 900 KiB message boundary requires paging, not result loss.
        raw=calculate(rows[:1800],items,1,0,1799*60)
        self.assertGreater(len(canonical(raw)),900*1024)
        self.assertEqual(self.display.settings('spot','BTCUSDT')['origins']['1']['time'],0)
