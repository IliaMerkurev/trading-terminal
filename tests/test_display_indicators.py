import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from terminal.chart_history import ChartHistory
from terminal.data import canonical,digest
from terminal.display_indicators import DisplayIndicators,calculate,validate_instances,MAX_BARS
from terminal.market_hub import MarketHub
from terminal.storage import RunStore


def instance(kind,**params):
    return dict(id=kind,type=kind,params=params,color='#7eabff',visible=True)


def candles(closes,minutes=1):
    return [dict(time=i*minutes*60,open=float(c),high=float(c)+1,low=float(c)-1,close=float(c),volume=float(i),confirmation='synthetic_closed') for i,c in enumerate(closes)]


class DisplayArithmeticTests(unittest.TestCase):
    def test_independent_fraction_oracle(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/display_indicator_golden.json').read_text())
        items=[instance('sma',period=3),instance('ema',period=3),instance('bb',period=2,deviations=2),instance('rsi',period=2),instance('macd',fast=2,slow=3,signal=2)]
        actual=calculate(candles([float(c) for c in fixture['closes']]),items,1,0,420)['columns']
        for key in ('sma','ema','rsi'):
            for got,want in zip(actual[key]['value'],fixture[key+('2' if key=='rsi' else '3')]):
                if want is None:self.assertIsNone(got)
                else:self.assertAlmostEqual(got,float(Fraction(want)),places=12)
        for i,want in enumerate(fixture['bb2_2']):
            if want is None:self.assertIsNone(actual['bb']['middle'][i]);continue
            self.assertAlmostEqual(actual['bb']['middle'][i],float(Fraction(want['middle'])))
            self.assertAlmostEqual((actual['bb']['upper'][i]-actual['bb']['middle'][i])**2,float(Fraction(want['band_distance_squared'])))
            self.assertAlmostEqual(actual['bb']['middle'][i]-actual['bb']['lower'][i],actual['bb']['upper'][i]-actual['bb']['middle'][i])
        for i,want in enumerate(fixture['macd2_3_2']):
            for port,value in want.items():
                if value is None:self.assertIsNone(actual['macd'][port][i])
                else:self.assertAlmostEqual(actual['macd'][port][i],float(Fraction(value)),places=12)

    def test_short_goldens_flat_rising_falling_and_volume(self):
        items=[instance('sma',period=3),instance('ema',period=3),instance('bb',period=2,deviations=2),instance('macd',fast=2,slow=3,signal=2)]
        out=calculate(candles([10,12,14,16]),items,1,0,180)['columns']
        self.assertEqual(out['sma']['value'][2],12);self.assertEqual(out['ema']['value'][2],12.5)
        self.assertEqual([out['bb'][p][2] for p in ('middle','upper','lower')],[13,15,11])
        self.assertAlmostEqual(out['macd']['macd'][2],11/18);self.assertAlmostEqual(out['macd']['macd'][3],85/108)
        self.assertAlmostEqual(out['macd']['signal'][3],59/81);self.assertAlmostEqual(out['macd']['histogram'][3],19/324)
        for closes,expected in [([10,10,10],100),([10,11,12],100),([12,11,10],0),([10,12,11],50)]:
            out=calculate(candles(closes),[instance('rsi',period=2)],1,0,120)
            self.assertEqual(out['columns']['rsi']['value'],[None,None,expected])
        rows=candles([10,10,10]);rows[0]['volume']=0;rows[1].update(open=11,volume=7);rows[2]['volume']=None
        out=calculate(rows,[instance('volume')],1,0,120)
        self.assertEqual(out['columns']['volume']['value'],[0,7,None]);self.assertEqual(out['directions'],[1,-1,1])

    def test_validation_atomic_bounds(self):
        for period in (1,1000):validate_instances([instance('ema',period=period)])
        for period in (True,0,1001,1.5,float('nan'),float('inf')):
            with self.assertRaises(ValueError):validate_instances([instance('ema',period=period)])
        for value in (True,0,11,float('inf')):
            with self.assertRaises(ValueError):validate_instances([instance('bb',period=2,deviations=value)])
        with self.assertRaises(ValueError):validate_instances([instance('macd',fast=3,slow=3,signal=2)])
        with self.assertRaises(ValueError):validate_instances([instance('volume')]*9)

    def test_gap_unknown_forming_and_future_perturbation(self):
        items=[instance('ema',period=2),instance('volume')]
        rows=candles([10,12,14,16,18]);rows[2]['confirmation']='forming'
        out=calculate(rows,items,1,0,240)
        self.assertEqual(out['columns']['ema']['value'][2:4],[None,None])
        rows[2]['confirmation']='legacy_unknown';self.assertEqual(calculate(rows,items,1,0,240)['columns'],out['columns'])
        rows[2]['confirmation']='synthetic_closed';whole=calculate(rows,items,1,0,240)
        changed=copy.deepcopy(rows);changed[-1]['close']=100
        self.assertEqual(calculate(changed,items,1,0,240)['columns']['ema']['value'][:-1],whole['columns']['ema']['value'][:-1])
        del rows[2];gap=calculate(rows,items,1,0,240)
        self.assertIn(180,gap['times']);self.assertIsNone(gap['columns']['ema']['value'][gap['times'].index(180)])
        self.assertEqual(gap['gaps'],1)


class DisplayCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=RunStore(Path(self.temp.name));self.hub=MarketHub()
        self.chart=ChartHistory(self.store,self.hub);self.chart.close() # No network worker.
        self.display=DisplayIndicators(self.chart)
    def tearDown(self):self.display.close();self.temp.cleanup()
    def seed(self,rows,confirmed=True):
        with self.store.connect() as db:
            for row in rows:
                payload=ChartHistory.payload(row);key=('spot','BTCUSDT',1,row['time'])
                db.execute('INSERT OR IGNORE INTO chart_candles_v1 VALUES(?,?,?,?,?)',(*key,canonical(payload).decode()))
                if confirmed:db.execute('INSERT OR IGNORE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)',(*key,digest(payload),'synthetic_closed'))
    def read(self,start=0,end=17940,**kw):
        for _ in range(300):
            out=self.display.read('spot','BTCUSDT',1,start,end,self.settings['revision'],**kw);kw.pop('reanchor',None)
            if out['status']!='calculating':return out
            time.sleep(.01)
        self.fail('Display calculation did not finish')
    def test_paging_trim_prepend_reopen_and_origin(self):
        rows=candles([100+(i%19) for i in range(2200)]);self.seed(rows[100:])
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=20),instance('rsi',period=14),instance('macd',fast=12,slow=26,signal=9)],0)
        first=self.read(6000,23940)
        def mapping(out,ident,port):return dict(zip(out['times'],out['columns'][ident][port]))
        for start,end in [(6000,41940),(24000,131940),(42000,149940)]:
            page=self.read(start,end)
            for ident,port in [('ema','value'),('rsi','value'),('macd','signal')]:
                a,b=mapping(first,ident,port),mapping(page,ident,port)
                for stamp in a.keys()&b.keys():self.assertEqual(a[stamp],b[stamp])
        self.seed(rows[:100]);self.assertEqual(self.read(6000,23940)['origin']['time'],6000)
        self.display.close();self.display=DisplayIndicators(self.chart);again=self.read(6000,23940)
        self.assertEqual(first['columns'],again['columns'])
        reanchored=self.read(6000,23940,reanchor=True);self.assertEqual(reanchored['origin']['time'],0);self.assertEqual(reanchored['origin']['generation'],2)
        self.assertNotEqual(first['columns']['ema'],reanchored['columns']['ema'])
    def test_metadata_no_age_promotion_conflict_and_idempotence(self):
        self.seed(candles([10,12,14]),confirmed=False)
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=2),instance('volume')],0)
        out=self.read(0,120);self.assertEqual(out['unknown'],3);self.assertEqual(out['columns']['ema']['value'],[None]*3)
        self.hub.market='spot';self.hub.symbol='BTCUSDT';self.hub.candles={'1':{120:{**ChartHistory.payload(candles([10,12,14])[2]),'confirmed':False,'provider_ms':120000}}}
        self.assertEqual(self.read(0,120)['unknown'],3)
        self.hub.candles['1'][120]['confirmed']=True
        confirmed=self.read(0,120);self.assertEqual(confirmed['confirmed'],1)
        self.assertEqual(confirmed['revision'],self.read(0,120)['revision'])
        self.hub.candles['1'][120]['close']=15
        with self.assertRaisesRegex(ValueError,'conflict'):self.read(0,120)
    def test_over_budget_no_reseed_and_memoization(self):
        self.seed(candles([10]*10000));self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=2)],0)
        with patch('terminal.display_indicators.calculate',wraps=calculate) as calculation:
            self.read(0,120);self.read(0,120);self.assertEqual(calculation.call_count,1)
        self.seed([dict(candles([10])[0],time=10000*60)])
        with self.assertRaisesRegex(ValueError,'10,000'):self.read(600000-299*60,600000)
        self.assertEqual(self.display.settings('spot','BTCUSDT')['origins']['1']['time'],0)
    def test_invalid_save_preserves_config_and_corrupt_storage_nonfatal(self):
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=2)],0)
        with self.assertRaises(ValueError):self.display.save('spot','BTCUSDT',[instance('ema',period=True)],1)
        self.assertEqual(self.settings,self.display.settings('spot','BTCUSDT'))
        with self.store.connect() as db:db.execute("UPDATE chart_presentation_v1 SET document='[]'")
        self.assertIn('warning',self.display.settings('spot','BTCUSDT'))

    def test_async_coalescing_responsiveness_cancellation_and_forming_projection(self):
        import threading
        self.seed(candles([100+i%19 for i in range(350)]))
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=20),instance('volume')],0)
        entered=threading.Event();release=threading.Event();original=calculate
        def slow(*args,**kwargs):
            entered.set();release.wait(2)
            return original(*args,**kwargs)
        self.hub.market='spot';self.hub.symbol='BTCUSDT'
        self.hub.candles={'1':{21000:{'time':21000,'open':110.,'high':120.,'low':100.,'close':111.,'volume':1.,'confirmed':False,'provider_ms':1}}}
        with patch('terminal.display_indicators.calculate',side_effect=slow) as work:
            started=time.monotonic();out=self.display.read('spot','BTCUSDT',1,18000,21000,1)
            self.assertEqual(out['status'],'calculating');self.assertLess(time.monotonic()-started,.5);self.assertTrue(entered.wait(1))
            for volume in (2,3,4):
                self.hub.candles['1'][21000]['volume']=volume
                out=self.display.read('spot','BTCUSDT',1,18000,21000,1)
                self.assertEqual(out['status'],'calculating')
                self.assertFalse(self.display.running[1].is_set())
            self.assertEqual(self.display.settings('spot','BTCUSDT')['revision'],1)
            release.set();out=self.read(18000,21000)
            self.assertEqual(work.call_count,1);self.assertEqual(out['columns']['volume']['value'][-1],4)
            self.assertIsNone(out['columns']['ema']['value'][-1]);self.assertEqual(out['times'][-1],21060)
        # One active replay plus only the newest waiting request; no backlog.
        entered.clear();release.clear()
        with patch('terminal.display_indicators.calculate',side_effect=slow):
            self.display.read('spot','BTCUSDT',1,0,6000,1);self.assertTrue(entered.wait(1))
            for end in (6060,6120,6180):self.display.read('spot','BTCUSDT',1,0,end,1)
            self.assertIsNotNone(self.display.pending);self.assertTrue(self.display.running[1].is_set())
            release.set();self.assertEqual(self.read(0,6180)['status'],'ready')
        self.display.close();self.assertFalse(self.display.thread.is_alive())

    def test_preorigin_finite_windows_and_transport_window_cap(self):
        rows=candles([100+i%19 for i in range(2400)]);self.seed(rows[2100:])
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=20),instance('sma',period=20),instance('bb',period=20,deviations=2),instance('volume')],0)
        self.read(2100*60,2399*60);self.seed(rows[:2100])
        older=self.read(300*60,599*60)
        self.assertEqual(len(older['times']),300);self.assertTrue(older['before_origin'])
        self.assertEqual(older['columns']['ema']['value'],[None]*300)
        self.assertTrue(all(v is not None for v in older['columns']['sma']['value']))
        with self.assertRaisesRegex(ValueError,'1,800'):self.read(0,1800*60)

    def test_confirmed_duplicate_stale_correction_and_delayed_coarse_confirmation(self):
        from terminal.live_data import PublicStream
        hub=self.hub;base=ChartHistory.payload(candles([10])[0])
        def event(price,stamp):return {'kind':'candle','candle':dict(base,close=price),'provider_ms':stamp}
        hub._observe_candle(event(10,100));hub._observe_candle(event(10,200));hub._observe_candle(event(11,150))
        self.assertNotIn('conflict',hub.latest('1')[0]);self.assertEqual(hub.latest('1')[0]['provider_ms'],200)
        hub._observe_candle(event(11,250));self.assertTrue(hub.latest('1')[0]['conflict'])
        stream=PublicStream('spot','BTCUSDT');stream.intervals=('60',)
        def packet(start,stamp,confirmed,close=10):return json.dumps({'topic':'kline.60.BTCUSDT','ts':stamp,'data':[{'interval':'60','confirm':confirmed,'start':start,'end':start+3600000-1,'open':'10','high':'12','low':'9','close':str(close),'volume':'1'}]})
        self.assertEqual(len(stream.parse(packet(0,3600000,True),3600000)),1)
        self.assertEqual(len(stream.parse(packet(3600000,3601000,False),3601000)),1)
        correction=stream.parse(packet(0,3602000,True,11),3602000)
        self.assertEqual(len(correction),1);self.assertEqual(correction[0]['candle']['close'],11)
        self.assertEqual(stream.parse(packet(0,3601500,True,10),3601500),[])

    def test_rest_correction_persists_conflict_without_overwriting_price(self):
        from terminal.data import DataError
        self.seed(candles([10,11,12]))
        self.chart.stop.clear()
        self.chart.client.get=lambda *a,**kw:{'list':[['120000','12','14','11','13','2']]}
        self.chart.client.requests=[]
        with patch('terminal.chart_history.time.time',return_value=180):
            with self.assertRaisesRegex(DataError,'changed'):self.chart.fetch('spot','BTCUSDT',1,None)
        self.chart.stop.set()
        self.settings=self.display.save('spot','BTCUSDT',[instance('ema',period=2)],0)
        with self.assertRaisesRegex(ValueError,'conflict'):self.read(0,120)
        with self.store.connect() as db:
            self.assertEqual(json.loads(db.execute('SELECT candle FROM chart_candles_v1 WHERE time=120').fetchone()[0])['close'],12)


    def test_period_one_finite_window_does_not_bridge_gap_at_origin_join(self):
        rows=candles([10]*13)
        self.seed(rows[10:])
        self.settings=self.display.save('spot','BTCUSDT',[
            instance('sma',period=1),instance('bb',period=1,deviations=2)],0)
        self.read(600,720)
        self.seed(rows[:9])  # Missing candle starts at 540, immediately before origin.
        result=self.read(0,720)
        self.assertIn(600,result['times'])  # Missing slot's interval-end whitespace.
        gap=result['times'].index(600)
        self.assertIsNone(result['columns']['sma']['value'][gap])
        for port in ('upper','middle','lower'):
            self.assertIsNone(result['columns']['bb'][port][gap])
        self.assertEqual(result['columns']['sma']['value'][gap-1],10)
        self.assertEqual(result['columns']['sma']['value'][gap+1],10)

class VolumePlacementTests(unittest.TestCase):
    setUp = DisplayCacheTests.setUp
    tearDown = DisplayCacheTests.tearDown
    def test_default_overlay_migration_explicit_pane_and_hidden_roundtrip(self):
        initial=self.display.settings('spot','BTCUSDT')
        self.assertEqual(initial['instances'][0]['type'],'volume')
        self.assertEqual(initial['instances'][0]['placement'],'overlay')
        old=instance('volume');other=copy.deepcopy(old);other['id']='second';other.update(placement='pane',visible=False)
        saved=self.display.save('spot','BTCUSDT',[old,other],0)
        self.assertEqual([i['placement'] for i in saved['instances']],['overlay','pane'])
        self.assertEqual(self.display.settings('spot','BTCUSDT'),saved)
        self.assertEqual(self.display.settings('spot','BTCUSDT',source='okx')['revision'],0)
        saved=self.display.save('spot','BTCUSDT',[],1)
        self.assertEqual(self.display.settings('spot','BTCUSDT')['instances'],[])
        invalid=instance('ema',period=2);invalid['placement']='overlay'
        with self.assertRaises(ValueError):validate_instances([invalid])
        invalid=instance('volume');invalid['placement']='anything'
        with self.assertRaises(ValueError):validate_instances([invalid])
