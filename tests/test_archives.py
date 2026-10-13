import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from terminal.archives import ArchiveManager,read_archive,privacy_check,CHUNK
from terminal.comparison import compare_runs
from terminal.data import DatasetStore,run_manifest,canonical,digest,write_new
from terminal.graph import example_graph,GraphEvaluator
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest
from terminal.storage import RunStore


class ArchiveTests(unittest.TestCase):
    def test_library_ordinal_bound_accepts_large_batches_and_legacy_rows(self):
        from terminal.archives import validate_snapshot
        from terminal.library import MAX_LIBRARY_ROWS
        snapshot=copy.deepcopy(self.store.get(self.run_id)['manifest'])
        snapshot['research']={'window':{'start':600,'end':3600,'warmup_start':0},'library':{
            'batch_id':'b'*32,'ordinal':11,'batch_sha256':'c'*64,
            'contract':{'document_sha256':digest({'graph':snapshot['strategy'],'layout':{}})}}}
        for ordinal in (11,MAX_LIBRARY_ROWS-1):
            snapshot['research']['library']['ordinal']=ordinal
            snapshot['snapshot_sha256']=digest({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})
            validate_snapshot(snapshot)
        snapshot['research']['library']['ordinal']=MAX_LIBRARY_ROWS
        snapshot['snapshot_sha256']=digest({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})
        with self.assertRaisesRegex(ValueError,'Invalid library provenance'):validate_snapshot(snapshot)

    def test_passive_benchmark_archive_preserves_contract_and_result(self):
        from terminal.benchmarks import validate_document,run
        document={'benchmark':'passive','version':1,'start':0,'end':3600,'interval':'once'}
        snapshot=run_manifest(document,self.profile,self.dataset)
        frozen=validate_document(document,self.profile,self.dataset,snapshot['runtime'])
        snapshot['research']={'benchmark_contract':frozen['contract_sha256']}
        snapshot['snapshot_sha256']=digest({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})
        bars=DatasetStore(self.store.root/'datasets').load(self.dataset['id'])[1]
        result=run(bars,self.profile,0,3600,'once');result['manifest_sha256']=snapshot['snapshot_sha256']
        ident=self.store.create(snapshot);self.store.status(ident,'running');self.store.complete(ident,result)
        info=self.manager.export(self.strategy,self.profile.snapshot(),[ident])
        project,files=read_archive((self.store.root/'exports'/info['filename']).read_bytes())
        self.assertEqual(files[f'runs/{ident}/result.json']['metrics'],result['metrics'])
        self.assertEqual(files[f'runs/{ident}/snapshot.json'],snapshot)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=RunStore(self.root/'source')
        self.strategy={'name':'Synthetic research','kind':'graph','document':{'graph':example_graph(),'layout':{}}}
        bars=[Candle(i*60,100+i%10,101+i%10,99+i%10,100+i%10,10) for i in range(60)]
        self.dataset=DatasetStore(self.store.root/'datasets').save('spot','BTCUSDT',0,3600,bars,[],{},metadata={},provenance=[])
        self.profile=Profile(primary_minutes=1)
        snapshot=run_manifest(example_graph(),self.profile,self.dataset)
        result=run_backtest(bars,self.profile,GraphEvaluator(example_graph()))
        result['manifest_sha256']=snapshot['snapshot_sha256']
        self.run_id=self.store.create(snapshot);self.store.status(self.run_id,'running');self.store.complete(self.run_id,result)
        self.manager=ArchiveManager(self.store)

    def export(self):
        info=self.manager.export(self.strategy,self.profile.snapshot(),[self.run_id])
        return (self.store.root/'exports'/info['filename']).read_bytes()

    def upload(self,manager,raw):
        transfer=manager.begin(len(raw))
        for offset in range(0,len(raw),CHUNK):manager.append(transfer['upload_id'],offset,base64.b64encode(raw[offset:offset+CHUNK]).decode())
        return manager.finish(transfer['upload_id'])

    def two_run_archive(self):
        second=self.store.create(self.store.get(self.run_id)['manifest'])
        self.store.status(second,'running');self.store.complete(second,self.store.result(self.run_id))
        info=self.manager.export(self.strategy,self.profile.snapshot(),[self.run_id,second])
        return (self.store.root/'exports'/info['filename']).read_bytes()

    def test_partial_two_run_failure_has_durable_mapping_and_preserves_bytes(self):
        raw=self.two_run_archive();destination=RunStore(self.root/'partial');manager=ArchiveManager(destination)
        existing=destination.create(self.store.get(self.run_id)['manifest'])
        destination.status(existing,'running');destination.complete(existing,self.store.result(self.run_id))
        before={p:p.read_bytes() for p in destination.directory(existing).glob('*.json')}
        original=manager.receipts.publish_run
        def fail_second(operation_id,ordinal,*args):
            if ordinal==1:raise OSError('private-storage-details-must-not-leak')
            return original(operation_id,ordinal,*args)
        with patch.object(manager.receipts,'publish_run',side_effect=fail_second),self.assertRaises(ValueError) as error:
            self.upload(manager,raw)
        operation=manager.recent()['rows'][0]['operation_id'];receipt=manager.status(operation)
        self.assertEqual(receipt['outcome'],'partial')
        self.assertEqual([item['publication_state'] for item in receipt['items']],['published','reserved','reserved'])
        self.assertEqual([item['current_status'] for item in receipt['items']],['completed','importing','missing'])
        self.assertIn(operation,str(error.exception));self.assertNotIn('private-storage',str(error.exception))
        self.assertEqual(destination.strategies(),[]);self.assertIsNone(manager.upload)
        self.assertEqual({p:p.read_bytes() for p in before},before)
        self.assertEqual(len(destination.recent()),3)

    def test_invalid_strategy_save_fields_are_rejected_before_any_run_write(self):
        raw=self.two_run_archive()
        for invalid in ('blank-name','oversized-document'):
            with self.subTest(invalid=invalid):
                project,docs=read_archive(raw)
                if invalid=='blank-name':project['strategy']['name']='   '
                else:project['strategy']['document']['layout']={'oversized':'x'*(1024*1024)}
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w') as archive:
                    for name,value in docs.items():archive.writestr(name,canonical(value))
                destination=RunStore(self.root/invalid);manager=ArchiveManager(destination)
                with self.assertRaises(ValueError):self.upload(manager,buffer.getvalue())
                self.assertEqual(destination.recent(),[]);self.assertEqual(destination.strategies(),[])
                self.assertFalse((destination.root/'runs').exists());self.assertIsNone(manager.upload)

    def test_service_error_envelope_keeps_operation_identity_and_redacts_storage(self):
        from terminal.service import AppService
        service=AppService(self.root/'service');self.addCleanup(service.close)
        raw=self.export();transfer=service.archives.begin(len(raw))
        service.archives.append(transfer['upload_id'],0,base64.b64encode(raw).decode())
        with patch.object(service.archives.receipts,'publish_run',side_effect=OSError('private')):
            response=service.handle({'version':1,'id':'archive-error-test','command':'archive_finish','params':{'upload_id':transfer['upload_id']}})
        self.assertEqual(response['type'],'error')
        note=response['error']['message']
        self.assertIn(transfer['operation_id'],note);self.assertIn('Do not retry blindly',note);self.assertNotIn('private',note)
        self.assertEqual(service.archives.status(transfer['operation_id'])['outcome'],'failed')

    def test_roundtrip_preserves_metrics_but_never_bundles_history_or_overwrites_runs(self):
        raw=self.export();project,files=read_archive(raw)
        archived=files[f'runs/{self.run_id}/result.json']
        self.assertEqual(archived['candles'],[])
        self.assertEqual(archived['metrics'],self.store.result(self.run_id)['metrics'])
        self.assertFalse(project['history_included'])
        destination=RunStore(self.root/'destination')
        result=self.upload(ArchiveManager(destination),raw)
        self.assertEqual(result['datasets_found'],0)
        self.assertNotEqual(result['run_ids'][0],self.run_id)
        imported=destination.get(result['run_ids'][0])
        self.assertEqual(imported['summary']['origin'],'imported')
        self.assertEqual(destination.strategy(result['strategy_id'])['profile'],self.profile.snapshot())
        self.assertEqual(destination.result(imported['id'])['trades'],self.store.result(self.run_id)['trades'])
        self.assertFalse((destination.root/'datasets').exists())

    def test_native_archive_import_does_not_execute_or_grant_trust(self):
        marker=self.root/'not-executed'
        # A top-level raise is valid Python but would fail immediately if imported.
        source='raise RuntimeError("Archive source must not execute")\n'
        doc={'version':1,'engine':'nautilus_trader','engine_version':'1.231.0','source':source,'class_name':'Example','config_class':'ExampleConfig','config':{},'bar_minutes':[1],'dependencies':{},'provenance':'Independently authored nonexecution fixture'}
        info=self.manager.export({'name':'Source preview','kind':'native','document':doc},self.profile.snapshot(),[])
        destination=RunStore(self.root/'native')
        result=self.upload(ArchiveManager(destination),(self.store.root/'exports'/info['filename']).read_bytes())
        self.assertEqual(destination.strategy(result['strategy_id'])['document']['source'],source)
        with destination.connect() as db:self.assertEqual(db.execute('select count(*) from native_trust').fetchone()[0],0)
        self.assertFalse(marker.exists())

    def test_unsafe_entries_and_zip_bombs_are_rejected(self):
        for name in ('../outside.json','C:/outside.json','runs\\bad.json','/absolute.json','project.json/extra'):
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w') as archive:archive.writestr(name,'{}')
            with self.assertRaises(ValueError):read_archive(buffer.getvalue())
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('project.json','0'*(2*1024*1024))
        with self.assertRaisesRegex(ValueError,'resource budget'):read_archive(buffer.getvalue())
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as archive:
            item=zipfile.ZipInfo('project.json');item.external_attr=0o120777<<16;archive.writestr(item,'{}')
        with self.assertRaisesRegex(ValueError,'entry type'):read_archive(buffer.getvalue())

    def test_checksum_failure_persists_nothing_and_chunks_require_exact_offsets(self):
        raw=self.export();project,docs=read_archive(raw)
        docs[f'runs/{self.run_id}/result.json']['metrics']['net_pnl']='99999'
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as archive:
            for name,value in docs.items():archive.writestr(name,canonical(value))
        destination=RunStore(self.root/'invalid');manager=ArchiveManager(destination)
        with self.assertRaisesRegex(ValueError,'validation rejected'):self.upload(manager,output.getvalue())
        self.assertEqual(destination.recent(),[]);self.assertEqual(destination.strategies(),[])
        transfer=manager.begin(5)
        with self.assertRaises(ValueError):manager.append(transfer['upload_id'],1,base64.b64encode(b'abc').decode())
        with self.assertRaises(ValueError):manager.finish(transfer['upload_id'])
        manager.cancel()

    def test_export_gate_reports_category_without_values(self):
        for value in ({'password':'not-a-real-credential'},{'source':'-----BEGIN PRIVATE KEY-----'},{'note':'someone@example.test'},{'path':'C:\\Users\\fixture\\file'}):
            with self.assertRaisesRegex(ValueError,'Export withheld') as error:privacy_check(value,'project.json')
            self.assertNotIn(next(iter(value.values())),str(error.exception))

    def test_comparison_exposes_changed_costs_strategy_data_and_runtime_contracts(self):
        original=self.store.get(self.run_id)['manifest'];second=copy.deepcopy(original)
        second['profile']['fee_rate']='0.002';second['runtime']['packages']['nautilus_trader']='other-version'
        second['snapshot_sha256']=digest({k:v for k,v in second.items() if k!='snapshot_sha256'})
        new=self.store.create(second);self.store.status(new,'running');result=self.store.result(self.run_id)
        result['profile']=second['profile'];result['manifest_sha256']=second['snapshot_sha256'];self.store.complete(new,result)
        comparison=compare_runs(self.store,[self.run_id,new]);fields={d['field'] for d in comparison['differences']}
        self.assertIn('profile.fee_rate',fields);self.assertIn('runtime.packages.nautilus_trader',fields)
        self.assertFalse(comparison['same_contract'])
