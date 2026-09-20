from decimal import Decimal
import tempfile
import time
import unittest

from terminal.library import prepare,for_window
from terminal.native import trust_identity
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class LibraryNativeWindowTests(unittest.TestCase):
    def wait(self,service,ident):
        limit=time.monotonic()+25
        while time.monotonic()<limit:
            state=service.jobs.status(ident)
            if state['status'] in ('completed','failed'):return state
            time.sleep(.03)
        self.fail('Native window worker exceeded bounded deadline')

    def call(self,service,command,params):
        return service.handle(dict(version=1,id='native-window',command=command,params=params))

    def trust(self,service,doc):
        response=self.call(service,'trust_native',dict(document=doc,expected_sha256=trust_identity(doc),acknowledge_user_permissions=True))
        self.assertEqual(response['type'],'result',response)

    def test_native_boundary_independent_trade_fee_golden_and_alternate_timeframe(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            try:
                profile=Profile(market='linear',capital='1000',primary_minutes=1,fee_rate='.001',funding_mode='assumed_zero',mark_mode='last_proxy').snapshot()
                for minutes in (1,3):
                    prices=[p for p in [100,102,104,106,108] for _ in range(minutes)]
                    bars=[Candle(i*60,p,p+1,p-1,p,100) for i,p in enumerate(prices)]
                    dataset=service.datasets.save('linear','BTCUSDT',0,len(bars)*60,bars,[],{},metadata={},provenance=[])
                    doc=prepare('native-ema-cross',2,minutes,{'fast':2,'slow':3,'quantity':'1'})['document']
                    window=dict(start=3*minutes*60,end=len(bars)*60,warmup_start=0)
                    request=dict(strategy=doc,profile={**profile,'primary_minutes':minutes},dataset_id=dataset['id'],window=window)
                    if minutes==1:
                        response=self.call(service,'start_window_run',request)
                        self.assertEqual(response['type'],'error');self.assertIn('Explicit trust',response['error']['message'])
                    self.trust(service,doc)
                    response=self.call(service,'start_window_run',request)
                    self.assertEqual(response['type'],'result',response)
                    ident=response['result']['run_id'];state=self.wait(service,ident)
                    self.assertEqual(state['status'],'completed',state)
                    result=service.store.result(ident)
                    self.assertEqual(len(result['trades']),1)
                    trade=result['trades'][0]
                    self.assertEqual(Decimal(trade['entry']['price']),106)
                    self.assertEqual(Decimal(trade['exit']['price']),108)
                    self.assertEqual(Decimal(result['metrics']['fees']),Decimal('.214'))
                    self.assertEqual(Decimal(result['metrics']['net_pnl']),Decimal('1.786'))
                    self.assertTrue(all(f['time_ns']>=window['start']*1_000_000_000 for f in result['fills']))
                    self.assertTrue(all(p['time_ns']>=window['start']*1_000_000_000 for p in result['equity']))
                    self.assertEqual(result['candles'][0]['time'],window['start'])
                changed={**doc,'source':doc['source']+'\n# Unreviewed source version\n'}
                response=self.call(service,'start_window_run',{**request,'strategy':changed})
                self.assertEqual(response['type'],'error');self.assertIn('reviewed adapter',response['error']['message'])
            finally:service.close()

    def test_two_distinct_strategy_batch_native_standalone_parity_and_no_automatic_trust(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            try:
                prices=[30,28,26,24,22,20,18,16,18,20,24,30,35,40,35,30,25,20,15,12,15,20,25,30]*2
                bars=[Candle(i*60,p,p+1,p-1,p,100) for i,p in enumerate(prices)]
                linear=service.datasets.save('linear','BTCUSDT',0,len(bars)*60,bars,[],{},metadata={},provenance=[])
                spot=service.datasets.save('spot','BTCUSDT',0,len(bars)*60,bars,[],{},metadata={},provenance=[])
                selections=[dict(entry_id='native-ema-cross',version=2,minutes=1,parameters={'fast':2,'slow':3,'quantity':'1'}),
                            dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':2})]
                profile=Profile(market='linear',capital='1000',primary_minutes=1,fee_rate='.001',funding_mode='assumed_zero',mark_mode='last_proxy').snapshot()
                params=dict(selections=selections,dataset_id=linear['id'],profile=profile,start=12*60,end=len(bars)*60,interval='daily',spot_dataset_id=spot['id'])
                preview=service.library_batches.preview(**params)
                self.assertIn('Explicit native trust',preview['rows'][0]['error'])
                native=prepare(**selections[0]);self.trust(service,native['document'])
                expected=service.library_batches.preview(**params)['contract_sha256']
                ident=service.library_batches.start(expected_contract=expected,**params)['batch_id']
                thread=service.library_batches.active['thread'];thread.join(timeout=30)
                self.assertFalse(thread.is_alive())
                report=service.library_batches.get(ident)
                self.assertEqual(report['status'],'completed',report)
                for row in report['rows'][:2]:
                    self.assertGreater(row['metrics']['completed_positions'],0)
                    self.assertIsNotNone(row['metrics']['net_pnl'])
                batch_result=service.store.result(report['rows'][0]['run_id'])
                response=self.call(service,'start_window_run',dict(strategy=native['document'],profile=profile,dataset_id=linear['id'],
                    window=dict(start=params['start'],end=params['end'],warmup_start=0)))
                self.assertEqual(response['type'],'result',response)
                standalone_id=response['result']['run_id'];state=self.wait(service,standalone_id)
                self.assertEqual(state['status'],'completed',state)
                standalone=service.store.result(standalone_id)
                self.assertEqual(standalone['trades'],batch_result['trades'])
                self.assertEqual(standalone['metrics'],batch_result['metrics'])
            finally:service.close()


if __name__=='__main__':unittest.main()
