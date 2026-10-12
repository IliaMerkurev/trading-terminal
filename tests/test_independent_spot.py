"""Independent passive inputs and immutable provenance, with tiny offline goldens."""
import copy
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from terminal import benchmarks
from terminal.archives import ArchiveManager, read_archive, validate_snapshot
from terminal.data import digest, run_manifest, DataError
from terminal.graph import example_graph
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle


def explicit_spot(**changes):
    p=Profile(capital='1000',primary_minutes=1,fee_rate='.01',slippage='.01',tick_size='.5',quantity_step='.1',
              min_quantity='.1',max_quantity='20',min_notional='1',max_notional='2000',**changes)
    return {'version':1,'profile':p.snapshot(),'assumptions':{'version':1,'fee_source':'explicit_spot',
        'fee_note':'Independently reviewed synthetic spot fee and slippage.', 'slippage_source':'explicit_spot',
        'precision_source':'reviewed_manual','precision_note':'Independently invented spot limits for offline testing.'}}


class IndependentSpotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.jobs=JobManager(self.temp.name);self.manager=LibraryBatchManager(self.jobs)
        self.addCleanup(self.temp.cleanup)
        self.bars=[Candle(i*60,100,100,100,100,100) for i in range(48)]
        self.spot=self.jobs.datasets.save('spot','BTCUSDT',0,2880,self.bars,[],{},metadata={},provenance=[])
        self.linear=self.jobs.datasets.save('linear','BTCUSDT',0,2880,self.bars,[],{},metadata={},provenance=[])
        linear=Profile(market='linear',capital='1000',leverage='2',primary_minutes=1,fee_rate='.02',slippage='.02',
            tick_size='1',quantity_step='1',min_quantity='1',max_quantity='5',min_notional='150',max_notional='500',
            funding_mode='assumed_zero',mark_mode='last_proxy')
        self.params={'selections':[{'entry_id':'rsi-threshold','version':1,'minutes':1,'parameters':{'period':2}}],
            'dataset_id':self.linear['id'],'profile':linear.snapshot(),'start':720,'end':1440,'interval':'daily',
            'spot_dataset_id':self.spot['id'],'spot_benchmark':explicit_spot()}

    def tearDown(self):
        self.manager.close();self.jobs.close()

    def wait(self,ident):
        if self.manager.active:
            thread=self.manager.active['thread'];thread.join(40);self.assertFalse(thread.is_alive())
        return self.manager.get(ident)

    def start(self,params=None):
        params=params or self.params
        return self.manager.start(expected_contract=self.manager.preview(**params)['contract_sha256'],**params)['batch_id']

    def test_independent_constraints_costs_goldens_and_cache_identity(self):
        frozen=self.manager.prepare(**self.params);row=frozen['rows'][1];p=Profile(**row['profile'])
        self.assertIsNone(row['error'])
        for name in benchmarks.SPOT_EXECUTION_FIELDS:self.assertEqual(getattr(p,name),self.params['spot_benchmark']['profile'][name])
        self.assertEqual(p.leverage,'1');self.assertEqual(p.maintenance_rate,'0');self.assertEqual(p.funding_mode,'assumed_zero')
        result=benchmarks.run(self.bars,p,720,1440,'once')
        self.assertEqual([D(f['quantity']) for f in result['fills']],[D('9.8'),D('9.8')])
        self.assertEqual([D(f['price']) for f in result['fills']],[101,99])
        self.assertEqual(D(result['metrics']['fees']),D('19.6'))
        self.assertEqual(D(result['metrics']['final_equity']),D('960.8'))
        # Retained passive scheduling caps maximum size, then rejects minimums.
        # At ask 101 / bid 99, total loss is 4 USDT per unit including both fees.
        for field,value,quantity in [('max_quantity','9','9'),('min_quantity','10',None),('min_notional','1001',None),('max_notional','900','8.9')]:
            changed=copy.deepcopy(self.params);changed['spot_benchmark']['profile'][field]=value
            spec=self.manager.prepare(**changed)['rows'][1]
            self.assertNotEqual(row['contract']['contract_sha256'],spec['contract']['contract_sha256'])
            rejected=benchmarks.run(self.bars,Profile(**spec['profile']),720,1440,'once')
            if quantity is None:
                self.assertEqual(rejected['fills'],[],field);self.assertEqual(D(rejected['metrics']['final_equity']),1000)
            else:
                self.assertEqual([D(f['quantity']) for f in rejected['fills']],[D(quantity)]*2,field)
                self.assertEqual(D(rejected['metrics']['final_equity']),1000-4*D(quantity))
        tick_case=copy.deepcopy(self.params);tick_case['spot_benchmark']['profile']['slippage']='.013'
        spec=self.manager.prepare(**tick_case)['rows'][1]
        rounded=benchmarks.run(self.bars,Profile(**spec['profile']),720,1440,'once')
        # Ask rounds up to 101.5 and bid down to 98.5 on the independent .5 tick.
        self.assertEqual([D(f['price']) for f in rounded['fills']],[D('101.5'),D('98.5')])
        self.assertEqual([D(f['quantity']) for f in rounded['fills']],[D('9.7')]*2)
        self.assertEqual(D(rounded['metrics']['final_equity']),D('951.5'))
        changed=copy.deepcopy(self.params);changed['profile'].update(fee_rate='.03',tick_size='2',quantity_step='2')
        self.assertEqual(row['contract'],self.manager.prepare(**changed)['rows'][1]['contract'])
        changed=copy.deepcopy(self.params);changed['spot_benchmark']['assumptions']['fee_source']='explicit_shared'
        self.assertNotEqual(row['contract']['contract_sha256'],self.manager.prepare(**changed)['rows'][1]['contract']['contract_sha256'])
        changed=copy.deepcopy(self.params);changed['spot_benchmark']['profile'].update(fee_rate='0',slippage='0')
        spec=self.manager.prepare(**changed)['rows'][1]
        self.assertNotEqual(row['contract']['contract_sha256'],spec['contract']['contract_sha256'])
        self.assertEqual(D(benchmarks.run(self.bars,Profile(**spec['profile']),720,1440,'once')['metrics']['final_equity']),1000)
        self.assertEqual(frozen,self.manager.prepare(**self.params))
        with self.assertRaisesRegex(ValueError,'Preview changed'):
            self.manager.start(expected_contract=frozen['contract_sha256'],**changed)

    def test_missing_incomplete_mismatched_and_protection_inputs_remain_row_local(self):
        alternatives=[{'spot_benchmark':None},{'spot_dataset_id':None},{'spot_dataset_id':'a'*64},
                      {'spot_dataset_id':self.linear['id']}]
        for key in benchmarks.SPOT_EXECUTION_FIELDS:
            value=explicit_spot();del value['profile'][key];alternatives.append({'spot_benchmark':value})
        for key,value in [('symbol','ETHUSDT'),('capital','999'),('stop_loss','.1'),('version',2),('leverage','2'),('tier_assumption',None)]:
            settings=explicit_spot();settings['profile'][key]=value;alternatives.append({'spot_benchmark':settings})
        for change in alternatives:
            frozen=self.manager.prepare(**{**self.params,**change})
            self.assertFalse(frozen['rows'][0]['error'],change)
            self.assertTrue(all(r['error'] for r in frozen['rows'][1:]),change)
            self.assertEqual(frozen['modeled_source_candles'],24)
        other=self.jobs.datasets.save('spot','BTCUSDT',0,2880,self.bars,[],{},metadata={},provenance=[],source='Different synthetic source')
        frozen=self.manager.prepare(**{**self.params,'spot_dataset_id':other['id']})
        self.assertTrue(all('source differs' in r['error'] for r in frozen['rows'][1:]))
        incomplete=self.jobs.datasets.save('spot','BTCUSDT',0,2880,self.bars[:-1],[],{},metadata={},provenance=[])
        frozen=self.manager.prepare(**{**self.params,'spot_dataset_id':incomplete['id']})
        self.assertTrue(all('coverage' in r['error'] for r in frozen['rows'][1:]))

    def test_worker_cache_archive_and_frozen_later_inputs(self):
        report=self.wait(self.start());self.assertEqual(report['status'],'completed',report)
        ids=[r['run_id'] for r in report['rows'][1:]]
        for row in report['rows'][1:]:
            result=self.jobs.store.result(row['run_id']);self.assertEqual(D(result['metrics']['final_equity']),D('960.8'))
            snapshot=self.jobs.store.get(row['run_id'])['manifest'];validate_snapshot(snapshot)
            self.assertEqual(snapshot['strategy']['execution_assumptions'],self.params['spot_benchmark']['assumptions'])
            tampered=copy.deepcopy(snapshot);tampered['strategy']['execution_assumptions']['fee_source']='explicit_shared'
            tampered['snapshot_sha256']=digest({k:v for k,v in tampered.items() if k!='snapshot_sha256'})
            with self.assertRaisesRegex(ValueError,'benchmark contract'):validate_snapshot(tampered)
        strategy={'name':'Synthetic independent spot fixture','kind':'graph','document':{'graph':example_graph(),'layout':{}}}
        archive=ArchiveManager(self.jobs.store).export(strategy,self.params['profile'],ids)
        _,files=read_archive((self.jobs.store.root/'exports'/archive['filename']).read_bytes())
        self.assertEqual(files[f'runs/{ids[0]}/snapshot.json'],self.jobs.store.get(ids[0])['manifest'])
        again=self.wait(self.start());self.assertEqual([r['run_id'] for r in again['rows'][1:]],ids)
        self.assertTrue(all(r['reused'] for r in again['rows'][1:]))
        later_spot=self.jobs.datasets.save('spot','BTCUSDT',0,2880,self.bars,[],{},metadata={'changed_instrument':'not used'},provenance=[])
        frozen=self.manager.freeze_validation(report['id'],0,self.linear['id'],1800,2880,later_spot['id'])
        later=self.manager.get(frozen['batch_id'])['snapshot']
        self.assertEqual(later['rows'][1]['profile'],report['snapshot']['rows'][1]['profile'])
        self.assertEqual(later['rows'][1]['document']['execution_assumptions'],self.params['spot_benchmark']['assumptions'])
        self.assertEqual(later['rows'][1]['dataset']['id'],later_spot['id'])
        self.assertEqual(later['rows'][1]['contract']['start'],1800)
        self.manager.start_validation(frozen['batch_id']);self.assertEqual(self.wait(frozen['batch_id'])['status'],'completed')

    def test_resume_retains_original_shared_costs_and_provenance(self):
        self.params['spot_benchmark']['assumptions']['fee_source']='explicit_shared'
        original=self.manager._run
        def finish_strategy(active,*args):
            result=original(active,*args);active['stop'].set();return result
        with patch.object(self.manager,'_run',side_effect=finish_strategy):report=self.wait(self.start())
        self.assertEqual([r['status'] for r in report['rows']],['completed','pending','pending'])
        self.params['spot_benchmark']['profile']['fee_rate']='.5'
        self.params['spot_benchmark']['assumptions']['precision_note']='Changed draft'
        self.manager.resume(report['id']);resumed=self.wait(report['id'])
        self.assertEqual(resumed['status'],'completed',resumed)
        self.assertEqual(resumed['snapshot'],report['snapshot'])
        self.assertEqual(D(self.jobs.store.result(resumed['rows'][1]['run_id'])['metrics']['fees']),D('19.6'))

    def test_optional_missing_preflight_is_local_but_corruption_is_global(self):
        actual=self.jobs.datasets.load
        def unavailable(ident):
            if ident==self.spot['id']:raise FileNotFoundError('Synthetic optional source removed')
            return actual(ident)
        with patch.object(self.jobs.datasets,'load',side_effect=unavailable):report=self.wait(self.start())
        self.assertEqual([r['status'] for r in report['rows']],['completed','incompatible','incompatible'])
        self.assertEqual(report['status'],'completed_with_errors')
        (self.jobs.datasets.root/self.spot['id']/'trade.parquet').write_bytes(b'corrupt')
        report=self.wait(self.start());self.assertEqual(report['status'],'failed')
        self.assertIn('checksum',report['error']);self.assertTrue(all(r['run_id'] is None for r in report['rows']))

    def test_legacy_document_shape_and_hash_are_exact(self):
        p=Profile(capital='1000',primary_minutes=1)
        document={'benchmark':'passive','version':1,'start':720,'end':1440,'interval':'once'}
        runtime={'fixed':'independent golden'}
        expected=dict(version=1,metric_version=1,execution='retained-nautilus',source=self.spot['source'],
            dataset_id=self.spot['id'],content_sha256=self.spot['content_sha256'],symbol='BTCUSDT',profile=p.snapshot(),
            start=720,end=1440,schedule='once',purchases=[720],end_treatment='full_close_with_costs',cash_yield='0',external_cashflows=False,runtime=runtime)
        self.assertEqual(benchmarks.validate_document(document,p,self.spot,runtime),{**expected,'contract_sha256':digest(expected)})
        for value in (None,{}, {**explicit_spot()['assumptions'],'unexpected':True}):
            with self.assertRaises(ValueError):benchmarks.validate_document({**document,'execution_assumptions':value},p,self.spot,runtime)
        legacy={k:v for k,v in self.params.items() if k!='spot_benchmark'}
        legacy.update(dataset_id=self.spot['id'],profile=p.snapshot(),spot_dataset_id=None)
        frozen=self.manager.prepare(**legacy)
        self.assertEqual(frozen['inputs'],legacy)
        self.assertNotIn('execution_assumptions',frozen['rows'][1]['contract'])
        self.assertEqual(set(frozen['rows'][1]['document']),set(document))

    def test_worker_rejects_rehashed_provenance_tampering(self):
        import io, json
        from types import SimpleNamespace
        from terminal import worker
        p=Profile(**benchmarks.independent_spot(self.params['spot_benchmark'],Profile(**self.params['profile']))['profile'])
        document={'benchmark':'passive','version':1,'start':720,'end':1440,'interval':'once',
                  'execution_assumptions':self.params['spot_benchmark']['assumptions']}
        snapshot=run_manifest(document,p,self.spot)
        frozen=benchmarks.validate_document(document,p,self.spot,snapshot['runtime'])
        snapshot['research']={'benchmark_contract':frozen['contract_sha256']}
        snapshot['strategy']['execution_assumptions']['fee_source']='explicit_shared'
        snapshot['snapshot_sha256']=digest({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})
        ident=self.jobs.store.create(snapshot)
        request={'version':1,'command':'run','run_id':ident,'root':str(self.jobs.store.root)}
        with patch.dict('os.environ',{'_TRADING_TERMINAL_SUPERVISOR':'0'}), patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(request).encode()))), patch('terminal.benchmarks.run') as run:
            with self.assertRaisesRegex(ValueError,'Worker benchmark contract mismatch'):worker.main()
            run.assert_not_called()

    def test_metadata_market_order_limit_and_service_optional_admission(self):
        from terminal.data import metadata_profile_fields
        from terminal.service import AppService
        metadata={'instrument':{'priceFilter':{'tickSize':'.5'},'lotSizeFilter':{'minOrderQty':'.1',
            'basePrecision':'.1','minOrderAmt':'1','maxMarketOrderQty':'20','maxOrderAmt':'2000'}}}
        fields=metadata_profile_fields({**self.spot,'metadata':metadata})
        self.assertEqual(fields['max_quantity'],'20');self.assertEqual(fields['quantity_step'],'.1')
        self.assertIn('historical',fields['tier_assumption'])
        service=AppService(Path(self.temp.name)/'api');self.addCleanup(service.close)
        with patch.object(service.library_batches,'preview',return_value={'checked':True}) as preview:
            response=service.handle({'version':1,'id':'a2','command':'library_batch_preview','params':self.params})
            preview.assert_called_once_with(**self.params)
            self.assertNotIn('error',response)
