import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from terminal.archives import ArchiveManager,read_archive,privacy_check,CHUNK
from terminal.comparison import compare_runs
from terminal.data import DatasetStore,run_manifest,canonical,digest
from terminal.graph import example_graph,GraphEvaluator
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest
from terminal.storage import RunStore


class ArchiveTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ValueError,'checksum'):self.upload(manager,output.getvalue())
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
