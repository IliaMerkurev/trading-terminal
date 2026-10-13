"""Isolated synthetic expectations for reviewed conversion and replay admission."""
import copy
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from terminal import indicator_alerts as core
from terminal.data import DatasetStore, canonical
from terminal.graph import GraphEvaluator, validate_graph
from terminal.indicator_alert_store import IndicatorAlertStore
from terminal.profile import Profile
from terminal.rule_strategy import RuleStrategies, FrozenSchedule, check_admission, validate_snapshot
from terminal.series import Candle
from terminal.storage import RunStore
from test_indicator_alerts import definition, candles, settings
from test_agreement_alert_history import frozen as agreement_definition, tape as agreement_tape


def bars(rows):
    return [Candle(**{key: row[key] for key in ('time','open','high','low','close','volume')}) for row in rows]


def raw(predicate, level=10):
    return dict(predicate=predicate, left=dict(kind='price', port='close'),
                right=dict(kind='level', value=level, unit='price'))


class RuleStrategyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = RunStore(self.root)
        self.rules = IndicatorAlertStore(self.database)
        self.conversions = RuleStrategies(self.rules)
        self.rule = self.rules.create('Frozen source', definition())
        self.request = dict(rule_id=self.rule['id'], revision=1, name='Reviewed strategy', direction='long')
        self.preview = self.conversions.preview(**self.request)

    def create(self, request_id='a'*32, **changes):
        return self.conversions.create(**{**self.request, 'preview_hash': self.preview['preview_hash'],
                                        'request_id': request_id, **changes})

    def dataset(self, rows, **changes):
        arguments = dict(metadata={'synthetic': True, 'frozen_rule_source': 'bybit'}, provenance=[],
                         source='Synthetic frozen-rule acceptance')
        arguments.update(changes)
        return DatasetStore(self.root/'datasets').save('spot','BTCUSDT',rows[0]['time'],rows[-1]['time']+60,
                                                      bars(rows),[],{},**arguments)

    def evaluate(self, preview, rows):
        manifest = self.dataset(rows)
        profile = Profile(**preview['profile'])
        schedule = FrozenSchedule(preview['graph'],profile,manifest,bars(rows))
        evaluator = GraphEvaluator(preview['graph'],frozen_schedule=schedule)
        return [evaluator([bar],bar.time+60,True) for bar in bars(rows)]

    def test_preview_is_read_only_and_defaults_and_full_provenance_are_explicit(self):
        self.assertEqual(self.database.strategies(), [])
        self.assertEqual(self.preview['profile']['primary_minutes'],1)
        self.assertEqual(self.preview['profile']['stop_loss'],'0')
        self.assertEqual(self.preview['profile']['take_profit'],'0')
        self.assertEqual(self.preview['graph']['outputs'],dict(entry_long='frozen_rule.value',exit_long=None,entry_short=None,exit_short=None))
        snapshot = validate_snapshot(self.preview['graph']['nodes'][0]['params']['snapshot'])
        self.assertEqual(snapshot['definition'],self.rule['definition'])
        self.assertEqual(snapshot['rule']['definition_hash'],self.rule['definition_hash'])
        self.assertTrue(any('No exit signal' in item for item in self.preview['warnings']))
        self.assertEqual(self.rules.events()['events'],[])

    def test_create_retry_read_only_receipt_restart_and_source_rebind_preserve_snapshot(self):
        saved = self.create()
        original = self.database.strategy(saved['strategy_id'])
        self.rules.rebind(self.rule['id'],1,definition(config=settings(params={'period':3})))
        self.assertEqual(self.create(),saved)
        self.assertEqual(self.conversions.request('a'*32),saved)
        self.assertEqual(RuleStrategies(self.rules).request('a'*32),saved)
        self.assertEqual(self.database.strategy(saved['strategy_id']),original)
        self.assertEqual(len(self.database.strategies()),1)
        self.assertIsNone(self.conversions.request('b'*32))
        with self.assertRaisesRegex(ValueError,'different content'):
            self.create(name='Different')

    def test_stale_renamed_archived_deleted_and_wrong_preview_cannot_create(self):
        with self.assertRaisesRegex(ValueError,'preview changed'):
            self.create(preview_hash='0'*64)
        self.rules.rename(self.rule['id'],1,'Renamed')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.create()
        self.rules.trash(self.rule['id'],2)
        with self.assertRaisesRegex(ValueError,'archived'):
            self.conversions.preview(**{**self.request,'revision':3})
        with self.database.connect() as db:
            db.execute('DELETE FROM indicator_alert_rules_v1 WHERE id=?',(self.rule['id'],))
        with self.assertRaisesRegex(ValueError,'not found'):
            self.conversions.preview(**self.request)
        self.assertEqual(self.database.strategies(),[])

    def test_name_collision_never_overwrites_and_new_name_requires_new_review(self):
        existing = self.database.save_strategy('REVIEWED STRATEGY','graph',{'graph':{},'layout':{}})
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.create()
        self.assertEqual(self.database.strategy(existing)['document']['graph'],{})
        self.assertIsNone(self.conversions.request('a'*32))
        with self.assertRaisesRegex(ValueError,'preview changed'):
            self.create(name='Unique')

    def test_receipt_failure_rolls_back_strategy_and_preserves_existing_data(self):
        existing = self.database.save_strategy('Unrelated','graph',{'graph':{},'layout':{}})
        with self.database.connect() as db:
            db.execute("CREATE TRIGGER reject_conversion BEFORE INSERT ON indicator_strategy_requests_v1 BEGIN SELECT RAISE(ABORT,'injected receipt failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'injected'):
            self.create()
        self.assertEqual([s['id'] for s in self.database.strategies()],[existing])
        self.assertIsNone(self.conversions.request('a'*32))

    def test_concurrent_same_identity_commits_one_strategy(self):
        results=[]; errors=[]
        def create():
            try: results.append(self.create())
            except Exception as exc: errors.append(exc)
        workers=[threading.Thread(target=create) for _ in range(2)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(5)
        self.assertEqual(errors,[])
        self.assertEqual(len(results),2)
        self.assertEqual(results[0],results[1])
        self.assertEqual(len(self.database.strategies()),1)

    def test_explicit_direction_and_unsupported_context_do_not_modify_rule(self):
        for direction in ('', 'both', 'short'):
            with self.subTest(direction=direction), self.assertRaises(ValueError):
                self.conversions.preview(**{**self.request,'direction':direction})
        config=settings();config['origins']['5']=dict(config['origins']['1'])
        for source,minutes in [('okx',1),('bybit',5)]:
            rule=self.rules.create(source+str(minutes),core.freeze_rule(config,source,'spot','BTCUSDT',minutes,[raw('above')]))
            with self.assertRaisesRegex(ValueError,'only saved Bybit native M1'):
                self.conversions.preview(rule['id'],1,'Unsupported','long')
            self.assertEqual(self.rules.get(rule['id'])['definition'],rule['definition'])

    def test_snapshot_strictness_and_single_frozen_node_and_missing_schedule(self):
        graph=copy.deepcopy(self.preview['graph'])
        with self.assertRaisesRegex(ValueError,'admitted backtest'):
            GraphEvaluator(graph)
        graph['nodes'].append({**graph['nodes'][0],'id':'second'})
        with self.assertRaisesRegex(ValueError,'One frozen'):
            validate_graph(graph)
        payload=json.loads(self.preview['graph']['nodes'][0]['params']['snapshot'])
        payload['definition']['instances'][0]['params']['period']=9
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            validate_snapshot(core.encode(payload).decode())
        with self.assertRaises(ValueError): validate_snapshot('{"version":1,"version":1}')

    def test_saved_source_node_immutable_while_exit_and_cost_edits_persist(self):
        saved=self.create();strategy=self.database.strategy(saved['strategy_id'])
        document=copy.deepcopy(strategy['document'])
        document['graph']['nodes'].append(dict(id='price',type='price',inputs={},params={'field':'close'}))
        profile={**strategy['profile'],'fee_rate':'0.002','stop_loss':'0.02'}
        self.database.save_strategy('Edited strategy','graph',document,saved['strategy_id'],profile)
        self.assertEqual(self.database.strategy(saved['strategy_id'])['profile']['fee_rate'],'0.002')
        document['graph']['nodes']=document['graph']['nodes'][1:]
        with self.assertRaisesRegex(ValueError,'immutable'):
            self.database.save_strategy('Changed','graph',document,saved['strategy_id'],profile)

    def test_exact_expected_sma_cross_and_first_known_state_and_mixed_any(self):
        rows=candles([8,10,12,12,10,8]); result=self.evaluate(self.preview,rows)
        self.assertEqual([i for i,r in enumerate(result) if r['signals']['entry_long']],[2])
        self.assertIsNone(result[0]['values']['frozen_rule.condition_truth'])
        self.assertIsNone(result[1]['values']['frozen_rule.condition_truth'])
        state=self.rules.create('State',definition('above'))
        preview=self.conversions.preview(state['id'],1,'State strategy','long')
        self.assertFalse(any(r['signals']['entry_long'] for r in self.evaluate(preview,candles([12,12,13]))))
        mixed=definition(conditions=[raw('above',0),raw('cross_above',10)],combine='ANY')
        rule=self.rules.create('Mixed',mixed);preview=self.conversions.preview(rule['id'],1,'Mixed strategy','long')
        result=self.evaluate(preview,candles([9,11,9,11]))
        self.assertEqual([i for i,r in enumerate(result) if r['signals']['entry_long']],[1,3])

    def test_all_any_agreement_exact_replay_and_future_independence(self):
        candidates=[definition(conditions=[raw('above'),raw('below',15)],combine='ALL'),
                    definition(conditions=[raw('cross_above'),raw('cross_below')],combine='ALL'),
                    definition(conditions=[raw('above'),raw('cross_below')],combine='ANY'),agreement_definition()]
        for index,frozen in enumerate(candidates):
            with self.subTest(index=index):
                rule=self.rules.create('Case '+str(index),frozen)
                preview=self.conversions.preview(rule['id'],1,'Graph '+str(index),'long')
                rows=agreement_tape(count=18)
                expected=core.replay(frozen,rows)['rows']
                with patch('terminal.indicator_alerts.replay',wraps=core.replay) as replay:
                    actual=self.evaluate(preview,rows)
                    self.assertEqual(replay.call_count,1)
                self.assertEqual([r['signals']['entry_long'] for r in actual],[r['hit'] for r in expected])
                self.assertEqual([r['values']['frozen_rule.condition_truth'] for r in actual],[r['truth'] for r in expected])
                changed=copy.deepcopy(rows)
                for row in changed[10:]: row.update(open=20,high=23,low=19,close=20)
                self.assertEqual(actual[:10],self.evaluate(preview,changed)[:10])

    def test_admission_rejects_source_origin_gaps_interval_profile_and_resource_changes(self):
        rows=candles([8,10,12]);manifest=self.dataset(rows);graph=self.preview['graph'];profile=Profile(**self.preview['profile'])
        for changes in ({'range':[60,240]}, {'source':'Bybit public API','metadata':{},'provenance':[]}, {'interval_seconds':300}, {'market':'linear'}, {'symbol':'ETHUSDT'}, {'coverage':{'trade':{'count':3,'complete':False}}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check_admission(graph,profile,{**manifest,**changes})
        for changes in ({'evaluation':'intrabar'},{'primary_minutes':5},{'gap_policy':'skip'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check_admission(graph,Profile(**{**self.preview['profile'],**changes}),manifest)
        with self.assertRaisesRegex(ValueError,'reseeding'): check_admission(graph,profile,manifest,{})
        with patch('terminal.indicator_alerts.working_estimate',return_value=256*1024*1024):
            with self.assertRaisesRegex(ValueError,'256 MiB'): check_admission(graph,profile,manifest)

    def test_materialized_tape_clocks_missing_origin_and_schedule_identity_fail_closed(self):
        rows=candles([8,10,12]);manifest=self.dataset(rows);graph=self.preview['graph'];profile=Profile(**self.preview['profile'])
        with self.assertRaises(ValueError): FrozenSchedule(graph,profile,manifest,bars(rows)[1:])
        for times,complete in [([120],True),([60],False),([60,60],True),([60,180],True)]:
            schedule=FrozenSchedule(graph,profile,manifest,bars(rows));evaluator=GraphEvaluator(graph,frozen_schedule=schedule)
            with self.subTest(times=times,complete=complete), self.assertRaises(ValueError):
                for index,stamp in enumerate(times): evaluator([bars(rows)[index]],stamp,complete)
        schedule=FrozenSchedule(graph,profile,manifest,bars(rows))
        altered=copy.deepcopy(graph);altered['nodes'][0]['id']='renamed';altered['outputs']['entry_long']='renamed.value'
        with self.assertRaisesRegex(ValueError,'does not match'): GraphEvaluator(altered,frozen_schedule=schedule)
        cancelled=threading.Event();cancelled.set()
        with self.assertRaises(InterruptedError): FrozenSchedule(graph,profile,manifest,bars(rows),cancel=cancelled)

    def test_experiments_and_unprepared_live_replay_are_explicitly_unavailable(self):
        from terminal.experiments import parameter_fields,warmup_bars
        from terminal.signals import replay_signals
        graph=self.preview['graph']
        for action in (lambda:parameter_fields(graph),lambda:warmup_bars(graph),lambda:list(replay_signals(graph,1,'closed',bars(candles([8,10,12]))))):
            with self.assertRaises(ValueError): action()

    def test_recorded_rest_provenance_requires_exact_context_and_close_clocks(self):
        rows=candles([8,10,12]);manifest=self.dataset(rows)
        record=dict(endpoint='/v5/market/kline',params=dict(category='spot',symbol='BTCUSDT',interval='1',start=0,end=179999),
                    response_sha256='e'*64,retrieved_at='2026-01-01T00:00:00+00:00',provider_time_ms=180000)
        manifest.update(source='Bybit public API',metadata={},provenance=[record])
        profile=Profile(**self.preview['profile']);graph=self.preview['graph']
        self.assertEqual(check_admission(graph,profile,manifest)['confirmation'],'closed_rest')
        invalid=[]
        for key,value in [('symbol','ETHUSDT'),('category','linear'),('interval','5'),('start',60000),('end',119999)]:
            item=copy.deepcopy(record);item['params'][key]=value;invalid.append(item)
        for key,value in [('provider_time_ms',179999),('retrieved_at','1970-01-01T00:02:00+00:00'),('retrieved_at','2026-01-01T00:00:00'),('response_sha256','not-a-hash')]:
            invalid.append({**record,key:value})
        for item in invalid:
            with self.subTest(item=item),self.assertRaises(ValueError):
                check_admission(graph,profile,{**manifest,'provenance':[item]})

    def test_divergence_hits_keep_confirmed_close_instead_of_pivot_time(self):
        from terminal import vumanchu_indicators as vmc
        rows=candles([100+10*math.sin(i*.4)+i*.01 for i in range(100)])
        config=settings('vmc_cipher_b',dict(vmc.DEFAULTS['vmc_cipher_b'],wt_div_bottom=-10,wt_div_top=10))
        frozen=definition(config=config,conditions=[dict(predicate='divergence',instance_id='signal',event_kind='regular_bullish',oscillator='wt')])
        rule=self.rules.create('Confirmed divergence',frozen)
        preview=self.conversions.preview(rule['id'],1,'Divergence strategy','long')
        expected=core.replay(frozen,rows)['events'];self.assertTrue(expected)
        actual=self.evaluate(preview,rows)
        self.assertEqual([(i+1)*60 for i,row in enumerate(actual) if row['signals']['entry_long']], [row['confirmed_at'] for row in expected])
        for hit in expected:
            self.assertTrue(all(event['confirmed_at']-event['pivot_time']==120 for event in hit['conditions'][0]['events']))

    def test_physical_budget_excess_refuses_before_formula_replay(self):
        frozen=definition(conditions=[raw('above')]*16)
        rule=self.rules.create('Large evidence',frozen)
        preview=self.conversions.preview(rule['id'],1,'Large strategy','long')
        rows=candles([10]*5000);manifest=self.dataset(rows)
        with patch('terminal.indicator_alerts.replay',side_effect=AssertionError('must preflight')):
            with self.assertRaisesRegex(ValueError,'256 MiB'):
                FrozenSchedule(preview['graph'],Profile(**preview['profile']),manifest,bars(rows))

    def test_linear_short_keeps_direction_and_existing_accounting_path(self):
        from terminal.simulation import run_backtest
        frozen=core.freeze_rule(settings(),'bybit','linear','BTCUSDT',1,[raw('cross_below')])
        rule=self.rules.create('Linear short',frozen)
        preview=self.conversions.preview(rule['id'],1,'Linear strategy','short')
        self.assertEqual(preview['graph']['outputs']['entry_short'],'frozen_rule.value')
        rows=candles([12,12,8,8,9,11,8,9])
        manifest=DatasetStore(self.root/'datasets').save('linear','BTCUSDT',0,len(rows)*60,bars(rows),bars(rows),{},
            metadata={'synthetic':True,'frozen_rule_source':'bybit'},provenance=[],source='Synthetic linear conversion')
        profile=Profile(**{**preview['profile'],'funding_mode':'assumed_zero','mark_mode':'last_proxy','take_profit':'0.1'})
        schedule=FrozenSchedule(preview['graph'],profile,manifest,bars(rows))
        result=run_backtest(bars(rows),profile,GraphEvaluator(preview['graph'],frozen_schedule=schedule))
        self.assertEqual([i for i,row in enumerate(result['indicators']) if row['signals']['entry_short']],[2,6])
        self.assertTrue(result['engine_orders'])


class RuleStrategyServiceTests(unittest.TestCase):
    def setUp(self):
        from terminal.service import AppService
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=AppService(Path(self.temp.name));self.addCleanup(self.service.close)
        self.rule=self.service.indicator_alerts.store.create('Offline rule',definition())

    def call(self,command,**params):
        return self.service.handle(dict(version=1,id='test',command=command,params=params))

    def test_service_preview_create_request_save_and_backtest_with_real_worker(self):
        request=dict(rule_id=self.rule['id'],revision=1,name='Worker strategy',direction='long')
        preview=self.call('alert_strategy_preview',**request)
        self.assertEqual(preview['type'],'result',preview)
        preview=preview['result']
        saved=self.call('alert_strategy_create',**request,preview_hash=preview['preview_hash'],request_id='c'*32)
        self.assertEqual(saved['type'],'result',saved)
        self.assertEqual(self.call('alert_strategy_request',request_id='c'*32)['result'],saved['result'])
        values=[8,10,12,12,10,8,12,12,10,8]
        rows=candles(values)
        manifest=self.service.datasets.save('spot','BTCUSDT',0,len(rows)*60,bars(rows),[],{},
            metadata={'synthetic':True,'frozen_rule_source':'bybit'},provenance=[],source='Synthetic conversion worker acceptance')
        graph=preview['graph'];graph['nodes'] += [dict(id='close',type='price',inputs={},params={'field':'close'}),
            dict(id='level',type='constant',inputs={},params={'value':10}),
            dict(id='exit',type='compare',inputs={'left':'close.value','right':'level.value'},params={'operator':'<'})]
        graph['outputs']['exit_long']='exit.value'
        started=self.call('start_run',strategy=graph,profile=preview['profile'],dataset_id=manifest['id'])
        self.assertEqual(started['type'],'result',started)
        run_id=started['result']['run_id'];deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            status=self.service.jobs.status(run_id)
            if status['status'] in ('completed','failed','cancelled') and not status.get('worker_active'): break
            time.sleep(.03)
        self.assertEqual(status['status'],'completed',status)
        result=self.service.store.result(run_id)
        expected=core.replay(self.rule['definition'],rows)['rows']
        self.assertEqual([row['signals']['entry_long'] for row in result['indicators']],[row['hit'] for row in expected])
        self.assertGreaterEqual(len(result['trades']),1)
        self.assertEqual(self.service.indicator_alerts.store.events()['events'],[])
        self.assertEqual(self.service.store.get(run_id)['manifest']['strategy']['nodes'][0],graph['nodes'][0])

    def test_service_strict_parameters_and_live_rejection_before_journal_or_provider(self):
        self.assertEqual(self.call('alert_strategy_preview',rule_id=self.rule['id'],revision=1,name='Test',direction='long',extra=True)['type'],'error')
        preview=self.service.rule_strategies.preview(self.rule['id'],1,'Live rejection','long')
        saved=self.service.rule_strategies.create(self.rule['id'],1,'Live rejection','long',preview['preview_hash'],'d'*32)
        for paper in (False,True):
            with patch.object(self.service.live.journal,'create',side_effect=AssertionError('journal must remain untouched')), patch.object(self.service.live.hub,'open',side_effect=AssertionError('provider must remain untouched')):
                result=self.call('live_start',strategy_id=saved['strategy_id'],profile=preview['profile'],paper=paper,channels=[])
            self.assertEqual(result['type'],'error',result)
            self.assertIn('live/PAPER',result['error']['message'])
