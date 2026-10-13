from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import time
import unittest

from terminal.data import BybitClient, DatasetStore, DataError, coverage, prepare_dataset
from terminal.graph import GraphEvaluator, example_graph
from terminal.profile import Profile
from terminal.series import Candle, PartialBars
from terminal.simulation import run_backtest


class CoarseResearchTests(unittest.TestCase):
    def test_contract_rejects_unsupported_modes_and_preserves_legacy_snapshot(self):
        self.assertNotIn('execution_minutes',Profile().snapshot())
        for params in ({'market':'linear'},{'evaluation':'intrabar'},{'primary_minutes':15},{'position_management':{}}):
            with self.assertRaises(ValueError):Profile(**{'execution_minutes':60,**params})
        p=Profile(execution_minutes=240,primary_minutes=240)
        self.assertEqual(Profile(**p.snapshot()),p)
        with self.assertRaisesRegex(ValueError,'Native Python'):
            run_backtest([Candle(0,10,10,10,10,1)],p,None,native_factory=lambda _:self.fail('Must not load native code'))

    def test_h4_costed_protection_and_gap_have_independent_expected_fills(self):
        p=Profile(version=2,primary_minutes=240,execution_minutes=240,fee_rate='.001',slippage='.01',stop_loss='.05')
        bars=[Candle(0,100,120,60,100,100),Candle(14400,100,100,80,90,100)]
        signal=lambda bars,t,complete:{'signals':{'entry_long':t==14400},'values':{}}
        result=run_backtest(bars,p,signal)
        self.assertEqual([D(f['price']) for f in result['fills']],[D('101'),D('94.99')])
        self.assertEqual(D(result['metrics']['fees']),D('.1940301'))
        self.assertEqual(D(result['metrics']['net_pnl']),D('-6.1439301'))
        self.assertEqual(result['fills'][0]['time_ns'],14400*10**9-1)
        gap=run_backtest([bars[0],Candle(14400,80,100,70,90,100)],p,signal)
        self.assertEqual(D(gap['fills'][1]['price']),D('79.20'))
        self.assertEqual(gap['fills'][1]['time_ns'],14400*10**9)

    def test_h1_sources_form_actual_h4_and_future_cannot_change_earlier_values(self):
        bars=[Candle(i*3600,x,x,x,x,1) for i,x in enumerate([10,12,14,16,20,22,24,26,30,32,34,36])]
        p=Profile(primary_minutes=240,execution_minutes=60,fee_rate='0',version=2)
        a=run_backtest(bars,p,GraphEvaluator(example_graph()))
        changed=bars[:8]+[Candle(c.time,99,99,99,99,1) for c in bars[8:]]
        b=run_backtest(changed,p,GraphEvaluator(example_graph()))
        self.assertEqual([v['time'] for v in a['indicators']],[14400,28800,43200])
        self.assertEqual(a['indicators'][1]['values']['mean.value'],21)
        self.assertEqual(a['indicators'][:2],b['indicators'][:2])
        self.assertEqual(a['fills'][0],b['fills'][0])
        aggregate=PartialBars(240,source_minutes=60)
        for bar in bars[:2]+bars[3:4]:aggregate.update(bar)
        self.assertEqual(aggregate.closed,[])

    def test_daily_benchmarks_keep_cash_costs_and_schedule(self):
        from terminal.benchmarks import run
        p=Profile(primary_minutes=1440,execution_minutes=1440,capital='180',fee_rate='0',min_notional='.01')
        bars=[Candle(i*86400,x,x,x,x,100) for i,x in enumerate([10,20,30])]
        dca=run(bars,p,0,259200,'daily');hold=run(bars,p,0,259200,'once')
        self.assertEqual([D(f['quantity']) for f in dca['fills'][:-1]],[6,3,2])
        self.assertEqual(D(dca['metrics']['final_equity']),330)
        self.assertEqual(D(hold['metrics']['final_equity']),540)
        self.assertEqual(dca['fills'][-1]['time_ns'],259200*10**9-1)

    def test_h4_download_alignment_closed_bar_filter_and_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            def transport(path,params):
                self.assertEqual(params['interval'],'240')
                rows=[[str(t*1000),'10','12','9','11','100'] for t in (28800,14400,0) if t*1000<=params['end']]
                return {'retCode':0,'time':35000*1000,'result':{'list':rows}}
            client=BybitClient(temp,transport=transport)
            bars=client.candles('spot','BTCUSDT',0,43200,minutes=240)
            self.assertEqual([b.time for b in bars],[0,14400])
            self.assertEqual(coverage(bars,0,43200,14400)['gaps'],[[28800,43200]])
            with self.assertRaisesRegex(DataError,'align'):client.candles('spot','BTCUSDT',60,43200,minutes=240)

    def test_incremental_history_fetches_only_missing_tail_and_exact_reuse_is_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            store=DatasetStore(Path(temp)/'datasets');calls=[]
            class Client:
                requests=[]
                def instruments(self,*_):return [{}]
                def candles(self,market,symbol,start,end,minutes=1):
                    calls.append((start,end,minutes))
                    return [Candle(t,10,11,9,10,1) for t in range(start,end,minutes*60)]
            first=prepare_dataset(Client(),store,'spot','BTCUSDT',0,28800,minutes=240)
            original=(store.root/first['id']/'manifest.json').read_bytes()
            extended=prepare_dataset(Client(),store,'spot','BTCUSDT',0,57600,minutes=240)
            self.assertEqual(calls,[(0,28800,240),(28800,57600,240)])
            self.assertEqual(extended['coverage']['trade']['count'],4)
            self.assertEqual((store.root/first['id']/'manifest.json').read_bytes(),original)
            class Offline:
                def instruments(self,*_):raise AssertionError('Exact verified cache must not access network')
            self.assertEqual(prepare_dataset(Offline(),store,'spot','BTCUSDT',0,57600,minutes=240),extended)
            with self.assertRaisesRegex(DataError,'resolution'):store.for_run(extended['id'],Profile())

    def test_managed_daily_batch_warmup_parity_and_interval_aware_report(self):
        from terminal.jobs import JobManager
        from terminal.library_batches import LibraryBatchManager
        with tempfile.TemporaryDirectory() as temp:
            jobs=JobManager(temp);manager=LibraryBatchManager(jobs)
            try:
                prices=[10,12,14,16,14,12,10,12,14,16]*5
                bars=[Candle(i*86400,p,p+1,p-1,p,100) for i,p in enumerate(prices)]
                data=jobs.datasets.save('spot','BTCUSDT',0,len(bars)*86400,bars,[],{},metadata={},provenance=[],minutes=1440)
                selections=[dict(entry_id='historical-return',version=1,minutes=1440,parameters={'lookback':1})]
                warmup=manager.warmup(selections,data['id'])
                self.assertEqual(warmup['start'],2*86400)
                params=dict(selections=selections,dataset_id=data['id'],profile=Profile(primary_minutes=1440,execution_minutes=1440).snapshot(),start=warmup['start'],end=data['range'][1],interval='weekly',spot_dataset_id=None)
                preview=manager.preview(**params)
                self.assertLess(preview['modeled_minutes'],200)
                ident=manager.start(expected_contract=preview['contract_sha256'],**params)['batch_id']
                deadline=time.monotonic()+25
                while manager.active is not None and time.monotonic()<deadline:time.sleep(.03)
                report=manager.get(ident)
                self.assertEqual(report['status'],'completed',report)
                self.assertTrue(all(row['status']=='completed' for row in report['rows']),report)
                row=report['snapshot']['rows'][0]
                expected=run_backtest(bars,Profile(**row['profile']),GraphEvaluator(row['document']['graph']),trade_start=params['start'])
                actual=jobs.store.result(report['rows'][0]['run_id'])
                from terminal.archives import validate_snapshot
                validate_snapshot(jobs.store.get(report['rows'][0]['run_id'])['manifest'])
                validate_snapshot(jobs.store.get(report['rows'][1]['run_id'])['manifest'])
                self.assertEqual(actual['trades'],expected['trades'])
                chart=jobs.store.chart_window(report['rows'][0]['run_id'],minutes=30)
                self.assertEqual(chart['interval_seconds'],86400)
                self.assertEqual(len(chart['series']['candles']),30)
                self.assertTrue(all(f['chart_time']%86400==0 for f in chart['series']['fills']))
            finally:manager.close();jobs.close()

    def test_ipc_preserves_native_interval_and_overlap_conflicts_fail(self):
        from terminal.service import AppService
        with tempfile.TemporaryDirectory() as temp:
            service=AppService(temp)
            try:
                def save(price,end):
                    return service.datasets.save('spot','BTCUSDT',0,end,[Candle(t,price,price,price,price,1) for t in range(0,end,14400)],[],{},metadata={},provenance=[],minutes=240)
                first=save(10,28800);save(11,43200)
                reply=service.handle({'version':1,'id':'interval','command':'list_datasets','params':{}})
                self.assertEqual(reply['type'],'result')
                self.assertTrue(all(row['interval_seconds']==14400 for row in reply['result']))
                class Offline:
                    def instruments(self,*_):raise AssertionError('Conflicting local snapshots must fail before network')
                with self.assertRaisesRegex(DataError,'Conflicting immutable'):
                    prepare_dataset(Offline(),service.datasets,'spot','BTCUSDT',0,57600,minutes=240)
                self.assertEqual(service.datasets.describe(first['id'])['range'],[0,28800])
            finally:service.close()
