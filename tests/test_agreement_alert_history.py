"""Bounded agreement integration tests with independent synthetic expectations."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from terminal import indicator_agreement as agreement
from terminal import indicator_alerts as core
from terminal import display_indicators as display
from terminal.data import canonical, digest
from terminal.indicator_alert_runtime import IndicatorAlertRuntime
from terminal.service import AppService
from test_indicator_alerts import settings as legacy_settings, condition as legacy_condition, candles as legacy_candles
import test_indicator_alert_history as history_helpers
from test_indicator_alert_history import ident
import test_indicator_alert_runtime as runtime_helpers
from test_indicator_alert_runtime import wait_for


def member(ident, kind, period=1, visible=True):
    return dict(id=ident, type=kind, params={'period': period}, visible=visible, color='#abcdef')


def members():
    return [member('trend', 'sma', 2), member('momentum', 'roc'), member('volume', 'cmf')]


def condition(direction='up', threshold=.66, groups=None):
    return dict(predicate='agreement', direction=direction, threshold=threshold,
                required_groups=['trend', 'momentum'] if groups is None else groups)


def settings(items=None, origin=0):
    return dict(version=1, revision=1, instances=items if items is not None else members(),
                origins={'1': dict(time=origin, generation=1, contract=display.CONTRACT)})


def frozen(items=None, conditions=None, combine='ALL'):
    return core.freeze_rule(settings(items), 'bybit', 'spot', 'BTCUSDT', 1, conditions or [condition()], combine)


def tape(values=None, count=482):
    values = values if values is not None else ([10, 10, 14, 14, 14, 14, 10, 10]*((count+7)//8))[:count]
    return [dict(time=index*60, open=value, high=value+3, low=value-1, close=value,
                 volume=1, confirmation='synthetic_closed') for index, value in enumerate(values)]


class AgreementCoreIntegrationTests(unittest.TestCase):
    def test_exact_legacy_fixture_and_backward_compatible_catalog(self):
        fixture = json.loads(Path('tests/fixtures/alert_v1_compatibility.json').read_text())
        rule = core.freeze_rule(legacy_settings(), 'bybit', 'spot', 'BTCUSDT', 1, [legacy_condition()])
        self.assertEqual(core.encode(rule).decode(), fixture['canonical'])
        self.assertEqual(core.definition_hash(rule), fixture['definition_hash'])
        self.assertEqual(core.replay(rule, legacy_candles([8, 10, 12, 12, 10, 8])), fixture['replay'])
        catalog = IndicatorAlertRuntime.catalog()
        self.assertEqual(catalog['version'], 1)
        self.assertEqual(catalog['predicates'], ['above', 'below', 'cross_above', 'cross_below', 'divergence'])
        self.assertEqual(catalog['agreement_capability']['manifest_hash'], agreement.MANIFEST_HASH)
        self.assertEqual(catalog['agreement_capability']['definition_version'], 2)

    def test_applied_visible_supported_members_and_strict_versions_keys(self):
        items = members()+[member('hidden', 'rsi', 2, False), member('context', 'atr', 2),
                           dict(id='unsupported', type='ichimoku', params={'conversion': 9, 'base': 26, 'span_b': 52, 'displacement': 26}, visible=True, color='#abcdef'),
                           member('copy', 'sma', 2)]
        rule = frozen(items)
        self.assertEqual(rule['version'], 2)
        self.assertEqual(rule['agreement']['member_ids'], ['copy', 'momentum', 'trend', 'volume'])
        self.assertEqual({item['id'] for item in rule['instances']}, set(rule['agreement']['member_ids']))
        self.assertEqual(core.validate_definition(core.decode(core.encode(rule))), rule)
        variants = []
        for key, value in [('version', 3), ('contract', core.CONTRACT), ('unknown', True)]:
            invalid = copy.deepcopy(rule); invalid[key] = value; variants.append(invalid)
        for key, value in [('version', 'future'), ('weight_version', 'future'), ('manifest_hash', '0'*64), ('unknown', True), ('member_ids', ['trend', 'trend'])]:
            invalid = copy.deepcopy(rule); invalid['agreement'][key] = value; variants.append(invalid)
        for key, value in [('threshold', True), ('threshold', 1.1), ('direction', 'neutral'), ('required_groups', ['trend', 'trend']), ('required_groups', ['future']), ('extra', 1)]:
            invalid = copy.deepcopy(rule); invalid['conditions'][0][key] = value; variants.append(invalid)
        invalid = copy.deepcopy(rule); invalid['version']=1; invalid['contract']=core.CONTRACT; invalid.pop('agreement'); variants.append(invalid)
        for invalid in variants:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                core.validate_definition(invalid)

    def test_one_calculation_preparation_and_exact_copy_dedup(self):
        items = members()+[member('copy', 'sma', 2)]
        original = display.calculate
        with patch.object(display, 'calculate', wraps=original) as calc, patch.object(agreement, 'prepare_agreement', wraps=agreement.prepare_agreement) as prepare:
            result = core.replay(frozen(items, [condition(), condition('down')]), tape(), include_values=True)
        self.assertEqual(calc.call_count, 1); self.assertEqual(prepare.call_count, 1)
        self.assertEqual(len(calc.call_args.args[0]), 482)
        self.assertEqual(len(calc.call_args.args[1]), 3)
        row = result['rows'][2]
        proof = row['conditions'][0]['agreement']
        self.assertEqual(proof['overall']['exact']['up'], ['2', '3'])
        self.assertEqual(proof['coverage']['total_variants'], 3)
        self.assertEqual(next(v for v in proof['variants'] if v['type']=='sma')['member_ids'], ['copy', 'trend'])
        self.assertEqual(set(row['values']), {'copy', 'trend', 'momentum', 'volume'})
        self.assertTrue(proof['group_conflict'])

    def test_482_rows_unknown_neutral_conflict_and_sixty_edges_each_direction(self):
        for direction, offset in [('up', 2), ('down', 6)]:
            result = core.replay(frozen(conditions=[condition(direction)]), tape())
            self.assertEqual(len(result['rows']), 482)
            self.assertEqual(sum(row['truth'] is None for row in result['rows']), 1)
            self.assertEqual([row['raw_open_time']//60 for row in result['events']], list(range(offset, 482, 8)))
            self.assertEqual(result['rows'][3]['conditions'][0]['agreement']['overall']['exact']['neutral'], ['2', '3'])
            self.assertFalse(result['rows'][3]['hit'])

    def test_exact_inclusive_threshold_and_strict_half_required_group(self):
        # Two trend variants split 50/50; Momentum is Up, so overall is 75% Up.
        items = [member('a', 'sma', 2), member('b', 'ema', 2), member('m', 'roc')]
        output = dict(times=[60, 120], columns={'a': {'value':[10, 9]}, 'b': {'value':[10, 11]}, 'm': {'value':[0, 1]}}, indicator_events={'instances':{}})
        with patch.object(display, 'calculate', return_value=output):
            result = core.replay(frozen(items, [condition(threshold=.75, groups=[]), condition(threshold=.75, groups=['trend'])]), tape([10, 10]))
        self.assertTrue(result['rows'][1]['conditions'][0]['truth'])
        self.assertFalse(result['rows'][1]['conditions'][1]['truth'])
        self.assertFalse(result['rows'][1]['conditions'][1]['threshold']['group_pass']['trend'])
        # Rounded 67% must not pass .67 when the exact fraction is 2/3.
        result = core.replay(frozen(conditions=[condition(threshold=.67)]), tape(count=3))
        self.assertEqual(result['rows'][2]['conditions'][0]['agreement']['overall']['percentages']['up'], 67)
        self.assertFalse(result['rows'][2]['truth'])

    def test_sustained_true_unknown_resets_and_mixed_impulses(self):
        rows = tape([10, 10, 14, 18, 22, 26, 26, 30])
        for row in rows: row.update(high=row['close']+1, low=row['close']-3)
        rows[4]['volume'] = None
        items = [member('trend', 'sma', 2), member('volume', 'cmf')]
        state = condition(threshold=.75, groups=[])
        result = core.replay(frozen(items, [state]), rows)
        self.assertEqual([r['truth'] for r in result['rows']], [None, False, True, True, None, True, False, True])
        self.assertEqual([r['raw_open_time']//60 for r in result['events']], [2, 7])
        pulse = dict(predicate='cross_above', left=dict(kind='price', port='close'), right=dict(kind='level', value=20, unit='price'))
        for mode, expected in [('ALL', []), ('ANY', [2, 4, 7])]:
            replay = core.replay(frozen(items, [state, pulse], mode), rows)
            self.assertEqual([r['raw_open_time']//60 for r in replay['events']], expected)

    def test_mixed_duplicate_divergence_preserves_each_original_event_identity(self):
        import math
        from terminal import vumanchu_indicators as vmc
        params=dict(vmc.DEFAULTS['vmc_cipher_b'],wt_div_bottom=-10,wt_div_top=10)
        items=members()+[dict(id=ident,type='vmc_cipher_b',params=params,visible=True,color='#abcdef') for ident in ('vmcA','vmcB')]
        conditions=[dict(predicate='divergence',instance_id=ident,event_kind='regular_bullish',oscillator='wt') for ident in ('vmcA','vmcB')]
        rows=legacy_candles([100+10*math.sin(i*.4)+i*.01 for i in range(100)])
        baseline=core.replay(frozen(items,conditions,'ANY'),rows)
        with patch.object(display,'calculate',wraps=display.calculate) as calc:
            extended=core.replay(frozen(items,conditions+[condition()],'ANY'),rows)
        self.assertEqual(len(calc.call_args.args[1]),4)
        self.assertTrue(any(r['conditions'][0]['events'] for r in baseline['rows']))
        for before,after in zip(baseline['rows'],extended['rows']):
            self.assertEqual(before['conditions'],after['conditions'][:2])
            for a,b in zip(after['conditions'][0]['events'],after['conditions'][1]['events']):
                self.assertNotEqual(a['id'],b['id'])

    def test_budget_preflight_includes_members_conditions_and_no_fixed_member_quota(self):
        many = [member(f'sma{i}', 'sma', 2) for i in range(200)] + [member('roc', 'roc')]
        rule = frozen(many)
        self.assertEqual(len(rule['agreement']['member_ids']), 201)
        # Small tape fits despite > any arbitrary small member quota.
        self.assertLess(core.working_estimate(rule, 1, include_values=True), 256*1024*1024)
        with patch.object(display, 'calculate', side_effect=AssertionError('must not allocate formula outputs')) as calc:
            with self.assertRaisesRegex(ValueError, '256 MiB'):
                core.replay(rule, tape(count=482), include_values=True)
        calc.assert_not_called()
        with self.assertRaisesRegex(ValueError, '10,000'):
            core.replay(frozen(), tape(count=10001))


class AgreementHistoryIntegrationTests(unittest.TestCase):
    # Reuse isolated Service mechanics without inheriting/rerunning its suite.
    setUp = history_helpers.HistoricalServiceTests.setUp
    tearDown = history_helpers.HistoricalServiceTests.tearDown
    call = history_helpers.HistoricalServiceTests.call
    error = history_helpers.HistoricalServiceTests.error
    seed = history_helpers.HistoricalServiceTests.seed
    create_rule = history_helpers.HistoricalServiceTests.create_rule
    params = history_helpers.HistoricalServiceTests.params
    completed = history_helpers.HistoricalServiceTests.completed
    scan = history_helpers.HistoricalServiceTests.scan
    all_hits = history_helpers.HistoricalServiceTests.all_hits

    def agreement_rule(self, direction='up'):
        config = self.service.display_indicators.settings('spot', 'BTCUSDT')
        config = self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT', revision=config['revision'], instances=members())
        preview = self.call('alert_preview', source='bybit', market='spot', symbol='BTCUSDT', minutes=1,
                            settings_revision=config['revision'], conditions=[condition(direction)])
        self.rule = self.call('alert_create', request_id=ident(), name='Frozen agreement', **preview)
        return preview

    def load_tape(self):
        self.values = [row['close'] for row in tape()]
        with self.service.store.connect() as db:
            db.execute('DELETE FROM chart_candles_v1'); db.execute('DELETE FROM chart_confirmation_v1')
            for row in tape():
                row = dict(row, time=row['time']+self.origin); row.pop('confirmation')
                key=('spot', 'BTCUSDT', 1, row['time'])
                db.execute('INSERT INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(row).decode()))
                db.execute('INSERT INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key, digest(row), 'synthetic_closed'))

    def test_every_row_paging_immutable_after_graph_changes_and_restart(self):
        self.load_tape(); self.agreement_rule()
        journal = self.call('alert_events'); runtime = self.call('alert_status')
        run = self.scan(); self.assertEqual(run['summary']['match_count'],60)
        self.assertEqual((run['summary']['known_rows'],run['summary']['unknown_rows']), (481,1))
        hits = self.all_hits(run['id']); self.assertEqual(len(hits),60)
        self.assertEqual([row['confirmed_at'] for row in hits], [self.origin+(3+8*i)*60 for i in range(60)])
        rows=[]; start=0
        while True:
            page=self.call('alert_history_chart',run_id=run['id'],start_index=start,limit=50)
            rows.extend(page['rows'])
            if page['next_index'] is None: break
            self.assertGreater(page['next_index'],start); start=page['next_index']
        self.assertEqual(len(rows),482)
        self.assertTrue(rows[2]['evaluation']['conditions'][0]['agreement']['group_conflict'])
        self.assertIsNone(rows[0]['evaluation']['conditions'][0]['agreement']['overall'])
        exact=self.call('alert_history_row',run_id=run['id'],confirmed_at=self.origin+180)
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=[member('other','ema',3)])
        self.assertEqual(self.call('alert_history_row',run_id=run['id'],confirmed_at=self.origin+180),exact)
        self.assertEqual(self.call('alert_events'),journal); self.assertEqual(self.call('alert_status'),runtime)
        self.assertIsNone(self.service.indicator_alerts.store.cursor(self.rule['id']))
        with self.service.store.connect() as db, self.assertRaises(sqlite3.IntegrityError):
            db.execute("UPDATE indicator_history_rows_v1 SET evaluation='{}' WHERE run_id=?",(run['id'],))
        self.service.close(); self.service=AppService(Path(self.temp.name))
        self.assertEqual(self.call('alert_history_row',run_id=run['id'],confirmed_at=self.origin+180),exact)
        self.assertEqual(self.call('alert_events'),journal)

    def test_historical_sustained_true_unknown_and_reset_rows_are_retained(self):
        self.values=[10,10,14,18,22,26,26,30]
        with self.service.store.connect() as db:
            db.execute('DELETE FROM chart_candles_v1'); db.execute('DELETE FROM chart_confirmation_v1')
            for index,row in enumerate(tape(self.values)):
                row=dict(row,time=self.origin+row['time'],high=row['close']+1,low=row['close']-3,volume=None if index==4 else 1)
                row.pop('confirmation');key=('spot','BTCUSDT',1,row['time'])
                db.execute('INSERT INTO chart_candles_v1 VALUES(?,?,?,?,?)',(*key,canonical(row).decode()))
                db.execute('INSERT INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)',(*key,digest(row),'synthetic_closed'))
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],
                         instances=[member('trend','sma',2),member('volume','cmf')])
        preview=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=1,
                          settings_revision=config['revision'],conditions=[condition(threshold=.75,groups=[])])
        self.rule=self.call('alert_create',request_id=ident(),name='Unknown reset',**preview)
        run=self.scan();page=self.call('alert_history_chart',run_id=run['id'])
        self.assertEqual([r['evaluation']['truth'] for r in page['rows']],[None,False,True,True,None,True,False,True])
        self.assertEqual([r['row_index'] for r in page['rows'] if r['evaluation']['hit']],[2,7])
        self.assertEqual(run['summary']['unknown_rows'],2)
        unknown=page['rows'][4]['evaluation']['conditions'][0]['agreement']
        self.assertIsNone(unknown['overall'])
        self.assertEqual(next(m for m in unknown['members'] if m['id']=='volume')['status'],'unavailable')

    def test_preview_changed_composition_rejected_and_paused_save_revert_sticky(self):
        self.load_tape(); preview=self.agreement_rule()
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        changed=members(); changed[0]['params']['period']=3
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=changed)
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=members())
        self.assertTrue(self.call('alert_get',rule_id=self.rule['id'])['rebind_required'])
        self.assertIn('changed',self.error('alert_create',request_id=ident(),name='Stale preview',**preview))
        self.service.close(); self.service=AppService(Path(self.temp.name))
        self.assertTrue(self.call('alert_get',rule_id=self.rule['id'])['rebind_required'])
        fresh=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=1,settings_revision=config['revision'],conditions=[condition()])
        rebound=self.call('alert_rebind',rule_id=self.rule['id'],revision=self.rule['revision'],**fresh)
        self.assertFalse(rebound['rebind_required']); self.assertEqual(rebound['runtime']['phase'],'PAUSED')


class AgreementLiveIntegrationTests(unittest.TestCase):
    setUp = runtime_helpers.AlertServiceTests.setUp
    tearDown = runtime_helpers.AlertServiceTests.tearDown
    call = runtime_helpers.AlertServiceTests.call
    error = runtime_helpers.AlertServiceTests.error
    context = runtime_helpers.AlertServiceTests.context
    seed = runtime_helpers.AlertServiceTests.seed
    emit = runtime_helpers.AlertServiceTests.emit
    arm = runtime_helpers.AlertServiceTests.arm
    phase = runtime_helpers.AlertServiceTests.phase

    def test_passive_close_event_frozen_graph_changes_and_sticky_rebind(self):
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=members())
        preview=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=1,
                          settings_revision=config['revision'],conditions=[condition()])
        rule=self.call('alert_create',request_id=ident(),name='Live agreement',**preview)
        self.arm(rule); self.phase(rule,'ARMED')
        self.assertEqual(self.call('alert_events')['events'],[])
        # Hidden, removed and added graph members never recapture the frozen IDs.
        altered=[dict(members()[0],visible=False),member('new','ema',3)]
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=altered)
        self.assertFalse(self.call('alert_get',rule_id=rule['id'])['rebind_required'])
        self.assertEqual(self.call('alert_get',rule_id=rule['id'])['definition'],preview['definition'])
        boundary=self.now
        self.now+=60;self.emit(boundary,12)
        events=wait_for(lambda:self.call('alert_events')['events'])
        self.assertEqual(len(events),1)
        proof=events[0]['evidence']['conditions'][0]['agreement']
        self.assertEqual({m['id'] for m in proof['members']},{'trend','momentum','volume'})
        self.assertEqual((proof['open_time'],proof['close_time']),(boundary,boundary+60))
        self.assertEqual(events[0]['evidence']['observed_at'],boundary+60)
        self.now+=60;self.emit(boundary+60,14)
        wait_for(lambda:self.service.indicator_alerts.store.cursor(rule['id'])['confirmed_at']==self.now)
        self.assertEqual(len(self.call('alert_events')['events']),1)
        changed=copy.deepcopy(altered);changed[0]['params']['period']=3
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=changed)
        self.phase(rule,'PAUSED')
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=altered)
        self.assertTrue(self.call('alert_get',rule_id=rule['id'])['rebind_required'])
        self.assertEqual(self.call('alert_events')['events'],events)

    def test_corrupt_first_rule_cannot_bypass_healthy_save_revert_fence(self):
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=members())
        preview=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=1,
                          settings_revision=config['revision'],conditions=[condition()])
        rule=self.call('alert_create',request_id=ident(),name='Healthy agreement',**preview)
        self.arm(rule);self.phase(rule,'ARMED')
        for digit,archived in [('0',0),('1',1)]:
            bad=self.service.indicator_alerts.store.create('Unusable snapshot',preview['definition'])
            with self.service.store.connect() as db:
                db.execute("UPDATE indicator_alert_rules_v1 SET id=?,definition='{}',deleted=? WHERE id=?",(digit*32,archived,bad['id']))
        self.assertEqual(self.service.indicator_alerts.store.list()['rules'][0]['id'],'0'*32)
        changed=members();changed[0]['params']['period']=3
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=changed)
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=members())
        self.assertTrue(self.call('alert_get',rule_id=rule['id'])['rebind_required'])
        self.phase(rule,'PAUSED')
        self.assertTrue(self.service.indicator_alerts.store.requires_rebind('0'*32))
        self.assertTrue(self.service.indicator_alerts.store.requires_rebind('1'*32))
        self.assertEqual(self.call('alert_events')['events'],[])

    def test_initial_true_arm_does_not_emit_and_rearm_does_not_recapture(self):
        self.seed([8,12])
        config=self.service.display_indicators.settings('spot','BTCUSDT')
        config=self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=members())
        preview=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=1,
                          settings_revision=config['revision'],conditions=[condition()])
        rule=self.call('alert_create',request_id=ident(),name='Initial true',**preview)
        self.arm(rule);self.phase(rule,'ARMED')
        self.assertEqual(self.call('alert_events')['events'],[])
        self.call('alert_pause',rule_id=rule['id'])
        self.call('chart_indicator_save',source='bybit',market='spot',symbol='BTCUSDT',revision=config['revision'],instances=[])
        self.arm(rule);self.phase(rule,'ARMED')
        self.assertEqual(self.call('alert_get',rule_id=rule['id'])['definition'],preview['definition'])
        self.assertEqual(self.call('alert_events')['events'],[])
