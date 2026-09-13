import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from terminal.data import DatasetStore
from terminal.experiments import normalize_axes
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=AppService(self.temp.name);self.addCleanup(self.service.close)
        self.manager=self.service.experiments;self.store=self.service.store
        bars=[Candle(i*60,100+i%6,102+i%6,98+i%6,100+i%6,100) for i in range(36)]
        self.dataset=self.service.datasets.save('spot','BTCUSDT',0,2160,bars,[],{},metadata={},provenance=[])
        self.graph=example_graph();self.profile=Profile(version=2,primary_minutes=1,fee_rate='0').snapshot()
        self.strategy=self.store.save_strategy('Independent grid fixture','graph',{'graph':self.graph,'layout':{}},None,profile=self.profile)
        self.params=dict(strategy_id=self.strategy,dataset_id=self.dataset['id'],profile=self.profile,is_range=[360,1080],oos_range=[1440,2160],axes=[{'key':'node.mean.period','values':[2,3]},{'key':'profile.stop_loss','values':['0','.05']}])

    def wait(self,predicate):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.03)
        self.fail('Bounded experiment deadline exceeded')

    def test_deduplication_limits_and_costs_not_optimized(self):
        axes,count=normalize_axes(self.graph,[{'key':'node.mean.period','values':[2,'2',3]}])
        self.assertEqual(count,2);self.assertEqual(axes[0]['values'],[2,3])
        for axes in ([{'key':'profile.fee_rate','values':[0]}],[{'key':'node.mean.period','values':[1.5]}],[{'key':'profile.stop_loss','values':['NaN']}],[{'key':'node.mean.period','values':list(range(1,101))},{'key':'profile.allocation','values':[1,2,3]}]):
            with self.assertRaises(ValueError):normalize_axes(self.graph,axes)
        with self.assertRaisesRegex(ValueError,'later and disjoint'):self.manager.preview(**{**self.params,'oos_range':[720,1200]})
        with self.assertRaisesRegex(ValueError,'warmup'):self.manager.preview(**{**self.params,'axes':[{'key':'node.mean.period','values':[100]}]})

    def test_grid_equals_independent_runs_freezes_then_validates_and_copies(self):
        ident=self.manager.start(**self.params)['experiment_id']
        self.store.save_strategy('Edited afterwards','graph',{'graph':example_graph(),'layout':{}},self.strategy,profile=Profile().snapshot())
        with self.assertRaisesRegex(ValueError,'calculation slot'):
            self.service.jobs.start(self.graph,self.profile,self.dataset['id'])
        self.wait(lambda:self.manager.active is None)
        report=self.manager.get(ident)
        self.assertEqual(report['status'],'completed',report)
        self.assertEqual(report['finished'],4)
        self.assertEqual(report['snapshot']['profile']['version'],2)
        self.assertTrue(all(r['status']=='completed' for r in report['rows']),report['rows'])
        for row in report['rows']:
            manifest=self.store.get(row['run_id'])['manifest']
            solo=self.service.jobs.start(manifest['strategy'],manifest['profile'],self.dataset['id'],research={'window':manifest['research']['window']})
            self.wait(lambda:self.service.jobs.active is None)
            expected=self.store.result(solo);actual=self.store.result(row['run_id'])
            for field in ('metrics','fills','trades','indicators','equity'):self.assertEqual(actual[field],expected[field],field)
        frozen=self.manager.freeze(ident,0)
        self.manager.validate(frozen['validation_id']);self.wait(lambda:self.manager.active is None)
        validation=self.manager.get(ident)['validations'][0]
        self.assertEqual(validation['status'],'completed',validation)
        with self.assertRaisesRegex(ValueError,'only once'):self.manager.validate(frozen['validation_id'])
        manifest=self.store.get(validation['run_id'])['manifest'];actual=self.store.result(validation['run_id'])
        self.assertTrue(all(f['time_ns']>=1440*10**9 for f in actual['fills']))
        self.assertTrue(all(c['time']>=1440 for c in actual['candles']))
        self.assertEqual(actual['candles'],[])
        self.assertEqual(actual['candles_reference']['range'],[1440,2160])
        chart=self.store.chart_window(validation['run_id'],None,30)
        self.assertEqual(chart['range'],[1440,2160]);self.assertEqual(len(chart['series']['candles']),12)
        solo=self.service.jobs.start(manifest['strategy'],manifest['profile'],self.dataset['id'],research={'window':manifest['research']['window']})
        self.wait(lambda:self.service.jobs.active is None)
        expected=self.store.result(solo)
        for field in ('metrics','fills','trades','indicators','equity'):self.assertEqual(actual[field],expected[field],field)
        copied=self.manager.copy_candidate(ident,0)['strategy_id']
        self.assertNotEqual(copied,self.strategy)
        self.assertEqual(self.store.strategy(copied)['profile']['version'],2)
        # Archive retains selection identity while omitting downloaded candles.
        archive=self.service.archives.export({'name':'Candidate','kind':'graph','document':{'graph':manifest['strategy'],'layout':{}}},manifest['profile'],[validation['run_id']])
        from terminal.archives import read_archive
        _,documents=read_archive((self.store.root/'exports'/archive['filename']).read_bytes())
        snap=documents[f"runs/{validation['run_id']}/snapshot.json"]
        self.assertEqual(snap['research']['experiment']['candidate_sha256'],frozen['candidate_sha256'])

    def test_cancel_stops_pending_combinations_and_releases_slot(self):
        ident=self.manager.start(**self.params)['experiment_id'];self.manager.cancel(ident)
        self.wait(lambda:self.manager.active is None)
        report=self.manager.get(ident)
        self.assertEqual(report['status'],'cancelled')
        self.assertLess(sum(r['run_id'] is not None for r in report['rows']),4)
        self.assertFalse(any(r['status']=='running' for r in report['rows']))
        self.assertIsNone(self.service.jobs.reservation)

    def test_position_parameter_grid_matches_single_runs_and_preserves_frozen_policy(self):
        from terminal.position_management import PositionConfig
        profile={**self.profile,'position_management':PositionConfig(max_entries=3,repeated_entry='scale',
                    dca=[{'distance':'.02','allocation_percent':'10'}],partial_take=[{'distance':'.03','fraction':'.5'}]).snapshot()}
        params={**self.params,'profile':profile,'axes':[{'key':'pm.dca.0.distance','values':['.02','.03']}]}
        fields=self.manager.fields(self.strategy,profile)
        self.assertIn('pm.atr_stop_multiplier',[field['key'] for field in fields])
        self.assertNotIn('pm.max_leverage',[field['key'] for field in fields])
        ident=self.manager.start(**params)['experiment_id'];self.wait(lambda:self.manager.active is None)
        report=self.manager.get(ident)
        self.assertEqual(report['status'],'completed',report)
        self.assertEqual([row['status'] for row in report['rows']],['completed','completed'])
        for row in report['rows']:
            manifest=self.store.get(row['run_id'])['manifest']
            solo=self.service.jobs.start(manifest['strategy'],manifest['profile'],self.dataset['id'],research={'window':manifest['research']['window']})
            self.wait(lambda:self.service.jobs.active is None)
            actual,expected=self.store.result(row['run_id']),self.store.result(solo)
            for field in ('metrics','fills','trades','indicators','equity'):self.assertEqual(actual[field],expected[field],field)
        frozen=self.manager.freeze(ident,0)
        copied=self.manager.copy_candidate(ident,0)['strategy_id']
        self.assertEqual(self.store.strategy(copied)['profile']['position_management']['dca'][0]['distance'],'0.02')
        self.manager.validate(frozen['validation_id']);self.wait(lambda:self.manager.active is None)
        validation=self.manager.get(ident)['validations'][0]
        self.assertEqual(validation['status'],'completed',validation)
        self.assertEqual(validation['snapshot']['profile']['position_management']['max_entries'],3)

    def test_position_axes_require_enabled_bounded_configuration(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):
            normalize_axes(self.graph,[{'key':'pm.max_entries','values':[2]}],self.profile)
        profile=Profile(**{**self.profile,'position_management':{}}).snapshot()
        for key,values in [('pm.max_entries',[100]),('pm.atr_period',[1]),('pm.trailing_distance',['1'])]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.manager.preview(**{**self.params,'profile':profile,'axes':[{'key':key,'values':values}]})

    def test_worker_errors_remain_failed_and_interruption_does_not_resume(self):
        with patch.object(self.service.jobs,'start',side_effect=ValueError('Controlled worker failure')):
            ident=self.manager.start(**self.params)['experiment_id'];self.wait(lambda:self.manager.active is None)
        self.assertEqual([r['status'] for r in self.manager.get(ident)['rows']],['failed']*4)
        with self.store.connect() as db:db.execute("UPDATE experiments SET status='running' WHERE id=?",(ident,))
        self.service.close();self.service=AppService(self.temp.name);self.addCleanup(self.service.close)
        self.assertEqual(self.service.experiments.get(ident)['status'],'interrupted')
        self.assertIsNone(self.service.experiments.active)

    def test_future_holdout_changes_do_not_change_is_ranking_or_frozen_parameters(self):
        original=self.manager.start(**self.params)['experiment_id'];self.wait(lambda:self.manager.active is None)
        _,bars,_,_=self.service.datasets.load(self.dataset['id'])
        changed=[Candle(b.time,200,400,50,300,b.volume) if b.time>=1440 else b for b in bars]
        future=self.service.datasets.save('spot','BTCUSDT',0,2160,changed,[],{},metadata={},provenance=[])
        other=self.manager.start(**{**self.params,'dataset_id':future['id']})['experiment_id'];self.wait(lambda:self.manager.active is None)
        def ranking(ident):return sorted(self.manager.get(ident)['rows'],key=lambda r:(-float(r['summary']['metrics']['net_pnl']),r['ordinal']))
        a,b=ranking(original),ranking(other)
        self.assertEqual([r['ordinal'] for r in a],[r['ordinal'] for r in b])
        self.assertEqual([r['summary']['metrics'] for r in a],[r['summary']['metrics'] for r in b])
        # Candidate zero is predeclared in this fixture, not chosen by OOS PnL.
        self.manager.freeze(original,0);self.manager.freeze(other,0)
        sa=self.manager.get(original)['validations'][0]['snapshot'];sb=self.manager.get(other)['validations'][0]['snapshot']
        for field in ('graph','parameters','profile'):self.assertEqual(sa[field],sb[field])
