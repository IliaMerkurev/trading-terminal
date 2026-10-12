"""Independent offline historical contracts through the actual strict Service."""
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
import uuid

from terminal import indicator_alerts as core
from terminal import indicator_alert_history as history
from terminal.data import canonical, digest
from terminal.display_indicators import CONTRACT
from terminal.service import AppService


def ident():
    return uuid.uuid4().hex


def candle(stamp, value):
    return dict(time=stamp, open=value, high=value+1, low=value-1, close=value, volume=2)


def condition():
    return dict(predicate='cross_above', left=dict(kind='series', instance_id='signal', port='value'),
                right=dict(kind='level', value=10, unit='price'))


def wait(check, timeout=8):
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        value = check()
        if value:
            return value
        time.sleep(.01)
    raise AssertionError('Synthetic historical worker did not settle')


class HistoricalServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = {kind: 0 for kind in ('provider', 'paper', 'orders', 'notifications', 'arm', 'context')}
        self.guards = []
        for target, kind in [
            ('terminal.data.BybitClient.get', 'provider'), ('terminal.okx_market.OKXHistory.candles', 'provider'),
            ('terminal.live_data.PublicStream.open', 'provider'), ('terminal.market_hub.OKXPublicStream.open', 'provider'),
            ('terminal.live.LiveManager.start', 'orders'), ('terminal.live.LiveManager.start_manual', 'paper'),
            ('terminal.live.LiveManager.manual', 'paper'), ('terminal.live.LiveManager._notify', 'notifications'),
            ('terminal.indicator_alert_runtime.IndicatorAlertRuntime.arm', 'arm'),
            ('terminal.indicator_alert_runtime.IndicatorAlertRuntime.register_context', 'context'),
            ('terminal.indicator_alert_runtime.IndicatorAlertRuntime.session_init', 'context'),
        ]:
            def deny(*args, _kind=kind, **kwargs):
                self.calls[_kind] += 1
                raise AssertionError('Forbidden historical side effect')
            guard = patch(target, side_effect=deny); guard.start(); self.guards.append(guard)
        self.service = AppService(Path(self.temp.name))
        self.origin = 1_800_000_000
        self.minutes = 1
        self.seed(([8, 10, 12, 12, 10, 8]*61)[:362])
        self.rule = self.create_rule()

    def tearDown(self):
        self.service.close()
        for guard in reversed(self.guards):
            guard.stop()
        self.temp.cleanup()
        self.assertEqual(self.calls, {key: 0 for key in self.calls})

    def call(self, command, **params):
        response = self.service.handle(dict(version=1, id=ident(), command=command, params=params))
        self.assertEqual(response['type'], 'result', response)
        return response['result']

    def error(self, command, **params):
        response = self.service.handle(dict(version=1, id=ident(), command=command, params=params))
        self.assertEqual(response['type'], 'error', response)
        return response['error']['message']

    def seed(self, values, minutes=1):
        self.values = values; self.minutes = minutes
        with self.service.store.connect() as db:
            for index, value in enumerate(values):
                row = candle(self.origin+index*minutes*60, value)
                key = ('spot', 'BTCUSDT', minutes, row['time'])
                db.execute('INSERT OR REPLACE INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(row).decode()))
                db.execute('INSERT OR REPLACE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key, digest(row), 'synthetic_closed'))

    def create_rule(self, conditions=None):
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        settings = self.call('chart_indicator_save', market='spot', symbol='BTCUSDT', source='bybit',
            instances=[dict(id='signal', type='sma', params={'period': 2}, visible=True, color='#abcdef')], revision=settings['revision'])
        settings['origins'][str(self.minutes)] = dict(time=self.origin, generation=1, contract=CONTRACT)
        self.service.display_indicators._write('spot', 'BTCUSDT', settings)
        preview = self.call('alert_preview', source='bybit', market='spot', symbol='BTCUSDT', minutes=self.minutes,
                            settings_revision=settings['revision'], conditions=conditions or [condition()])
        return self.call('alert_create', request_id=ident(), name='Synthetic frozen crossing', **preview)

    def params(self, **changes):
        result = dict(request_id=ident(), rule_id=self.rule['id'], revision=self.rule['revision'],
            definition_hash=self.rule['definition_hash'], start=self.origin+self.minutes*60,
            end=self.origin+len(self.values)*self.minutes*60)
        return dict(result, **changes)

    def completed(self, run_id):
        result = wait(lambda: (r if (r := self.call('alert_history_get', run_id=run_id))['status'] not in history.UNFINISHED else None))
        self.assertEqual(result['status'], 'completed', result)
        return result

    def scan(self, **changes):
        run = self.call('alert_history_start', **self.params(**changes))
        return self.completed(run['id'])

    def all_hits(self, run_id):
        hits = []; after = 0
        while True:
            page = self.call('alert_history_matches', run_id=run_id, after=after)
            hits.extend(page['matches'])
            if page['next_cursor'] is None:
                return hits
            after = page['next_cursor']

    def test_sixty_independently_expected_crossings_three_pages_and_unknowns(self):
        before = self.call('alert_events')
        run = self.scan()
        self.assertTrue(run['coverage_complete'])
        self.assertEqual(run['summary'], dict(requested_rows=362, evaluated_rows=362, known_rows=360,
            unknown_rows=2, match_count=60, pre_range_rows=0, pre_range_unknown_rows=0, initial_unknown_rows=2, unknown_reason='warmup_or_missing_value', input_rows=362,
            coverage_start=self.origin+60, coverage_end=self.origin+362*60))
        hits = self.all_hits(run['id'])
        self.assertEqual([h['confirmed_at'] for h in hits], [self.origin+(3+6*i)*60 for i in range(60)])
        for hit in hits:
            self.assertEqual(hit['values'], {'signal': {'value': 11.0}})
            self.assertEqual([hit['conditions'][0][key] for key in ('left','right','previous_left','previous_right')], [11,10,9,10])
        chart = self.call('alert_history_chart', run_id=run['id'])
        self.assertEqual(len(chart['rows']), 200)
        self.assertEqual(len(chart['markers']), 33)
        self.assertEqual(chart['next_index'], 200)
        self.assertEqual(self.call('alert_events'), before)
        self.assertIsNone(self.service.indicator_alerts.store.cursor(self.rule['id']))
        self.assertEqual(self.call('alert_status', rule_id=self.rule['id'])['phase'], 'PAUSED')

    def test_start_is_view_filter_not_reseed_and_future_cannot_change_prior_rows(self):
        end = self.origin+30*60
        whole = self.scan(end=end)
        later = self.scan(start=self.origin+3*60, end=end)
        self.assertEqual(self.all_hits(whole['id']), self.all_hits(later['id']))
        self.assertEqual(later['input_count'], 30)
        self.assertEqual(later['summary']['pre_range_rows'], 2)
        self.assertEqual(later['summary']['pre_range_unknown_rows'], 2)
        self.assertEqual(later['summary']['unknown_rows'], 0)
        self.seed(self.values[:30]+[999]*332)
        repeated = self.scan(end=end)
        self.assertEqual(self.all_hits(whole['id']), self.all_hits(repeated['id']))
        self.assertEqual(whole['input_hash'], repeated['input_hash'])

    def test_original_boundary_equality_and_five_minute_exact_clocks(self):
        self.seed([8,12,10,14], minutes=5)
        self.rule = self.create_rule()
        run = self.scan(start=self.origin+15*60)
        hits = self.all_hits(run['id'])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['confirmed_at'], self.origin+15*60)
        self.assertEqual(hits[0]['raw_open_time'], self.origin+10*60)
        self.assertEqual(hits[0]['conditions'][0]['previous_left'], 10)
        exact = self.call('alert_history_row', run_id=run['id'], raw_open_time=self.origin+10*60)
        self.assertEqual(exact['evaluation']['confirmed_at'], self.origin+15*60)
        self.assertIn('Exact', self.error('alert_history_row', run_id=run['id'], confirmed_at=self.origin+15*60-1))

    def test_immutable_rule_raw_values_and_restart_without_recalculation(self):
        run = self.scan()
        hits = self.all_hits(run['id'])
        row = self.call('alert_history_row', run_id=run['id'], confirmed_at=hits[-1]['confirmed_at'])
        self.seed([777]*362)
        renamed = self.call('alert_rename', rule_id=self.rule['id'], revision=1, name='Later title')
        self.call('alert_archive', rule_id=self.rule['id'], revision=renamed['revision'])
        self.create_rule()
        self.service.close(); self.service = AppService(Path(self.temp.name))
        with patch.object(core, 'replay', side_effect=AssertionError('Saved reads must never recalculate')):
            self.assertEqual(self.call('alert_history_get', run_id=run['id']), run)
            self.assertEqual(self.all_hits(run['id']), hits)
            self.assertEqual(self.call('alert_history_row', run_id=run['id'], confirmed_at=hits[-1]['confirmed_at']), row)
        with self.service.store.connect() as db:
            for table, column in [('indicator_history_runs_v1','input_hash'), ('indicator_history_inputs_v1','candle'), ('indicator_history_rows_v1','evaluation')]:
                with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
                    db.execute(f'UPDATE {table} SET {column}=?', ('changed',))
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_snapshot_is_captured_before_async_replay_and_later_rebind(self):
        entered = threading.Event(); release = threading.Event(); original = core.replay
        def blocked(*args, **kwargs):
            entered.set(); self.assertTrue(release.wait(3)); return original(*args, **kwargs)
        with patch.object(core, 'replay', side_effect=blocked):
            run = self.call('alert_history_start', **self.params())
            self.assertTrue(entered.wait(3))
            self.seed([999]*362)
            changed = copy.deepcopy(self.rule['definition']); changed['conditions'][0]['right']['value'] = 1000
            self.service.indicator_alerts.store.rebind(self.rule['id'], 1, changed)
            release.set()
            finished = self.completed(run['id'])
        self.assertEqual(finished['definition_hash'], self.rule['definition_hash'])
        self.assertEqual(finished['summary']['match_count'], 60)
        self.assertEqual(self.all_hits(run['id'])[0]['values']['signal']['value'], 11)

    def test_uncertain_start_request_identity_concurrent_and_read_only(self):
        params = self.params()
        self.assertFalse(self.call('alert_history_request', request_id=params['request_id'])['found'])
        returned = []; barrier = threading.Barrier(3)
        def start():
            barrier.wait(); returned.append(self.service.indicator_history.start(**params))
        threads = [threading.Thread(target=start) for _ in range(2)]
        for thread in threads: thread.start()
        barrier.wait()
        for thread in threads: thread.join(3)
        self.assertEqual(len(returned), 2)
        self.assertEqual(returned[0]['id'], returned[1]['id'])
        finished = self.completed(returned[0]['id'])
        self.call('alert_rename', rule_id=self.rule['id'], revision=1, name='Changed after start')
        self.assertEqual(self.call('alert_history_start', **params)['id'], finished['id'])
        self.assertIn('reused', self.error('alert_history_start', **dict(params, end=params['end']-60)))
        for _ in range(3):
            self.assertEqual(self.call('alert_history_request', request_id=params['request_id'])['run']['id'], finished['id'])
        self.assertEqual(len(self.call('alert_history_list')['runs']), 1)

    def test_eight_unfinished_queued_and_running_cancel_authoritative(self):
        entered = threading.Event(); release = threading.Event(); original = core.replay
        def blocked(*args, **kwargs):
            entered.set(); self.assertTrue(release.wait(5)); return original(*args, **kwargs)
        with patch.object(core, 'replay', side_effect=blocked):
            active = self.call('alert_history_start', **self.params())
            self.assertTrue(entered.wait(3))
            queued = [self.call('alert_history_start', **self.params()) for _ in range(7)]
            self.assertIn('eight', self.error('alert_history_start', **self.params()))
            cancelled = self.call('alert_history_cancel', run_id=queued[-1]['id'])
            self.assertEqual(cancelled['status'], 'cancelled'); self.assertFalse(cancelled['cancel_requested'])
            pending = self.call('alert_history_cancel', run_id=active['id'])
            self.assertEqual(pending['status'], 'cancel_requested'); self.assertTrue(pending['cancel_requested'])
            self.assertFalse(pending['coverage_complete']); self.assertIsNone(pending['summary'])
            for queued_run in queued[:-1]: self.call('alert_history_cancel', run_id=queued_run['id'])
            release.set()
            terminal = wait(lambda: (r if (r := self.call('alert_history_get', run_id=active['id']))['status'] == 'cancelled' else None))
            self.assertFalse(terminal['cancel_requested']); self.assertFalse(terminal['coverage_complete'])
        self.service.close(); self.service = AppService(Path(self.temp.name))
        self.assertEqual(self.call('alert_history_get', run_id=active['id'])['status'], 'cancelled')

    def test_startup_interrupts_durable_queued_snapshot_without_resume(self):
        with tempfile.TemporaryDirectory() as target, self.service.indicator_history.lock:
            run = self.call('alert_history_start', **self.params())
            # A consistent SQLite backup of this new synthetic schema models a
            # process dying after durable admission and before worker selection.
            destination = sqlite3.connect(str(Path(target)/'terminal.sqlite3'))
            with self.service.store.connect() as source: source.backup(destination)
            destination.close()
            with patch.object(core, 'replay', side_effect=AssertionError('Startup cannot resume research')):
                reopened = AppService(Path(target))
                try:
                    result = reopened.indicator_history.get(run['id'])
                    self.assertEqual(result['status'], 'interrupted')
                    self.assertFalse(result['coverage_complete']); self.assertIsNone(result['summary'])
                    self.assertEqual(reopened.indicator_history.request(run['request_id'])['run']['id'], run['id'])
                finally: reopened.close()
            self.call('alert_history_cancel', run_id=run['id'])

    def test_shutdown_interrupts_worker_and_retains_dependencies_on_timeout(self):
        entered = threading.Event(); release = threading.Event(); original = core.replay
        def blocked(*args, **kwargs):
            entered.set(); release.wait(5); return original(*args, **kwargs)
        with patch.object(core, 'replay', side_effect=blocked):
            run = self.call('alert_history_start', **self.params())
            self.assertTrue(entered.wait(3))
            with patch.object(self.service.live, 'close') as live_close, patch.object(self.service.indicator_history.thread, 'join'):
                with self.assertRaisesRegex(RuntimeError, 'shutdown'):
                    self.service.close()
                live_close.assert_not_called()
            result = self.call('alert_history_get', run_id=run['id'])
            self.assertEqual(result['status'], 'interrupted'); self.assertFalse(result['coverage_complete'])
            release.set()
            self.service.indicator_history.thread.join(3)
        self.service.close(); self.service = AppService(Path(self.temp.name))
        self.assertEqual(self.call('alert_history_get', run_id=run['id'])['status'], 'interrupted')

    def test_missing_origin_gaps_tail_provenance_conflicts_fail_without_admission(self):
        for index, change, fragment in [
            (0, 'delete', 'origin'), (8, 'delete', 'gap'), (361, 'delete', 'coverage'),
            (8, 'forming', 'confirmed'), (8, 'conflict', 'confirmed'), (8, 'hash', 'confirmed')]:
            with self.subTest(change=change,index=index):
                self.seed(self.values)
                with self.service.store.connect() as db:
                    if change == 'delete':
                        db.execute('DELETE FROM chart_candles_v1 WHERE time=?', (self.origin+index*60,))
                    elif change == 'forming':
                        db.execute("UPDATE chart_confirmation_v1 SET provenance='forming' WHERE time=?", (self.origin+index*60,))
                    elif change == 'conflict':
                        db.execute('UPDATE chart_confirmation_v1 SET conflict=1 WHERE time=?', (self.origin+index*60,))
                    else:
                        db.execute("UPDATE chart_confirmation_v1 SET content_hash='bad' WHERE time=?", (self.origin+index*60,))
                params = self.params()
                self.assertIn(fragment, self.error('alert_history_start', **params))
                self.assertFalse(self.call('alert_history_request', request_id=params['request_id'])['found'])

    def test_invalid_ranges_revisions_versions_and_strict_routes(self):
        for fields in ({'start': self.origin}, {'start': self.origin+120, 'end': self.origin+60},
                       {'start': self.origin+61}, {'end': True}, {'revision': 999}, {'definition_hash': 'a'*64}):
            self.error('alert_history_start', **self.params(**fields))
        self.error('alert_history_start', **dict(self.params(), surprise=True))
        self.error('alert_history_row', run_id=ident())
        self.error('alert_history_chart', run_id=ident(), limit=201)
        self.error('alert_history_matches', run_id=ident(), limit=21)
        changed = copy.deepcopy(self.rule['definition']); changed['contract'] = 'future'
        with self.service.store.connect() as db:
            db.execute('UPDATE indicator_alert_rules_v1 SET definition=? WHERE id=?', (canonical(changed).decode(), self.rule['id']))
        self.assertIn('Unsupported', self.error('alert_history_start', **self.params()))

    def test_full_origin_10000_boundary_later_start_does_not_reduce_cost(self):
        self.seed([8,10,12,12,10,8]*1667)
        self.assertIn('10,000', self.error('alert_history_start', **self.params(start=self.origin+10001*60, end=self.origin+10001*60)))
        run = self.scan(start=self.origin+10000*60, end=self.origin+10000*60)
        self.assertEqual(run['input_count'], 10000)
        self.assertEqual(run['summary']['pre_range_rows'], 9999)
        self.assertEqual(run['summary']['requested_rows'], 1)

    def test_working_budget_fails_before_formula_engine(self):
        self.seed([10]*5000)
        self.rule = self.create_rule([condition()]*16)
        with patch.object(core.display, 'calculate', side_effect=AssertionError('Preflight must precede formulas')):
            self.assertIn('256 MiB', self.error('alert_history_start', **self.params()))
        self.assertEqual(self.call('alert_history_list')['runs'], [])

    def test_chart_markers_page_independent_exact_target_and_byte_fallback(self):
        run = self.scan(); hits = self.all_hits(run['id']); target = hits[-1]['confirmed_at']
        window = self.call('alert_history_chart', run_id=run['id'], target_confirmed_at=target)
        self.assertEqual(window['start_index'], hits[-1]['row_index']-40)
        self.assertTrue(window['target']['included'])
        for offset in (0, hits[19]['confirmed_at'], hits[39]['confirmed_at']):
            self.call('alert_history_matches', run_id=run['id'], after=offset)
            self.assertEqual(self.call('alert_history_chart', run_id=run['id'], target_confirmed_at=target), window)
        with patch.object(history, 'MAX_RESPONSE_BYTES', 2200):
            clipped = self.call('alert_history_chart', run_id=run['id'], target_confirmed_at=target)
            self.assertTrue(clipped['byte_limited']); self.assertFalse(clipped['target']['included'])
            self.assertEqual(clipped['next_index'], clipped['rows'][-1]['row_index']+1)
            self.assertEqual(clipped['target']['row_index'], hits[-1]['row_index'])
            exact = self.call('alert_history_row', run_id=run['id'], confirmed_at=target)
            self.assertEqual(exact['candle']['time'], target-60)
            self.assertEqual(len(core.encode(clipped, 2200)) <= 2200, True)
        with patch.object(history, 'MAX_RESPONSE_BYTES', 300):
            self.assertIn('budget', self.error('alert_history_row', run_id=run['id'], confirmed_at=target))
        absent = self.call('alert_history_chart', run_id=run['id'], target_confirmed_at=target+1)
        self.assertEqual(absent['target']['status'], 'missing'); self.assertFalse(absent['target']['included'])

    def test_match_byte_cursor_and_saved_run_pages(self):
        run = self.scan(); expected = self.all_hits(run['id'])
        with patch.object(history, 'MAX_RESPONSE_BYTES', 2500):
            self.assertEqual(self.all_hits(run['id']), expected)
        # Bounded tiny scans prove the 20-row newest-first cursor without an
        # artificial permanent saved-run count cap.
        for _ in range(21): self.scan(end=self.origin+180)
        first = self.call('alert_history_list'); second = self.call('alert_history_list', after=first['next_cursor'])
        self.assertEqual((len(first['runs']), len(second['runs'])), (20,2))
        self.assertEqual(len({r['id'] for r in first['runs']+second['runs']}), 22)
        self.assertIsNone(second['next_cursor'])

    def event(self):
        rows = core.replay(self.rule['definition'], [dict(candle(self.origin+i*60,value), confirmation='synthetic_closed') for i,value in enumerate(self.values[:3])])['rows']
        token = self.service.indicator_alerts.store.begin_cursor(self.rule['id'], 1, rows[1])['token']
        return self.service.indicator_alerts.store.commit_evaluation(self.rule['id'], 1, token, rows[1]['confirmed_at'], rows[2], observed_at=rows[2]['confirmed_at']+1)['event_id']

    def test_original_event_numbers_authoritative_current_cache_explicit_exact_missing(self):
        event_id = self.event(); original = self.call('alert_event', event_id=event_id)
        before = self.call('alert_events'); cursor = self.service.indicator_alerts.store.cursor(self.rule['id'])
        target = self.origin+120
        for state in ('confirmed', 'unconfirmed', 'conflict', 'missing'):
            self.seed([777]*362)
            with self.service.store.connect() as db:
                if state == 'missing': db.execute('DELETE FROM chart_candles_v1 WHERE time=?', (target,))
                elif state == 'unconfirmed': db.execute("UPDATE chart_confirmation_v1 SET provenance='forming' WHERE time=?", (target,))
                elif state == 'conflict': db.execute('UPDATE chart_confirmation_v1 SET conflict=1 WHERE time=?', (target,))
            result = self.call('alert_event_evidence', event_id=event_id)
            self.assertEqual(result['event'], original)
            self.assertEqual(result['target_status'], state)
            self.assertEqual(result['target_raw_open_time'], target)
            self.assertIn('CURRENT local cache', result['warning'])
            self.assertEqual(result['target_candle']['close'] if state == 'confirmed' else result['target_candle'], 777 if state == 'confirmed' else None)
        self.assertEqual(self.call('alert_events'), before)
        self.assertEqual(self.service.indicator_alerts.store.cursor(self.rule['id']), cursor)
        self.error('alert_event_evidence', event_id=event_id, before=100, after=100)

    def test_original_divergence_targets_confirmation_and_keeps_earlier_pivot(self):
        from terminal import vumanchu_indicators as vmc
        self.seed([100+10*math.sin(i*.4)+i*.01 for i in range(100)])
        settings = dict(version=1, revision=1, origins={'1': dict(time=self.origin, generation=1, contract=CONTRACT)},
            instances=[dict(id='wave', type='vmc_cipher_b', params=dict(vmc.DEFAULTS['vmc_cipher_b'], wt_div_bottom=-10, wt_div_top=10), visible=True, color='#ffffff')])
        definition = core.freeze_rule(settings, 'bybit', 'spot', 'BTCUSDT', 1,
            [dict(predicate='divergence', instance_id='wave', event_kind='regular_bullish', oscillator='wt')])
        rule = self.service.indicator_alerts.store.create('Confirmed wave', definition)
        tape = [dict(candle(self.origin+i*60, value), confirmation='synthetic_closed') for i,value in enumerate(self.values)]
        rows = core.replay(definition, tape)['rows']
        hit_index = next(index for index,row in enumerate(rows) if row['hit'])
        previous, hit = rows[hit_index-1], rows[hit_index]
        token = self.service.indicator_alerts.store.begin_cursor(rule['id'], 1, previous)['token']
        event = self.service.indicator_alerts.store.commit_evaluation(rule['id'], 1, token, previous['confirmed_at'], hit, observed_at=hit['confirmed_at'])
        result = self.call('alert_event_evidence', event_id=event['event_id'])
        divergence = result['event']['evidence']['conditions'][0]['events'][0]
        self.assertEqual(result['target_confirmed_at'], divergence['confirmed_at'])
        self.assertEqual(result['target_raw_open_time'], divergence['confirmed_at']-60)
        self.assertEqual(divergence['pivot_time'], divergence['confirmed_at']-120)
        self.assertNotEqual(result['target_raw_open_time'], divergence['pivot_time']-60)
        self.assertEqual(result['target_candle']['time'], hit['confirmed_at']-60)

    def test_optional_value_snapshot_preserves_default_replay_bytes(self):
        tape = [dict(candle(self.origin+i*60, value), confirmation='synthetic_closed') for i,value in enumerate(self.values)]
        plain = core.replay(self.rule['definition'], tape)
        rich = core.replay(self.rule['definition'], tape, include_values=True)
        for kind in ('rows', 'events'):
            for row in rich[kind]:
                row.pop('values')
        self.assertEqual(core.encode(plain, history.MAX_WORKING_BYTES), core.encode(rich, history.MAX_WORKING_BYTES))
        self.assertEqual(plain['events'][0]['conditions'][0]['left'], 11)

    def test_all_150_crossings_large_fixture_and_byte_paged_markers(self):
        self.seed(([8,10,12,12,10,8]*151)[:902])
        run = self.scan(); hits = self.all_hits(run['id'])
        self.assertEqual([row['confirmed_at'] for row in hits], [self.origin+(3+6*i)*60 for i in range(150)])
        index = 0; markers = []
        with patch.object(history, 'MAX_RESPONSE_BYTES', 4000):
            while index is not None:
                page = self.call('alert_history_chart', run_id=run['id'], start_index=index)
                markers.extend(item['confirmed_at'] for item in page['markers'])
                index = page['next_index']
        self.assertEqual(markers, [row['confirmed_at'] for row in hits])

    def test_async_calculation_error_has_no_partial_coverage_or_rows(self):
        with patch.object(core, 'replay', side_effect=ValueError('Synthetic calculation fault')):
            run = self.call('alert_history_start', **self.params())
            terminal = wait(lambda: (r if (r := self.call('alert_history_get', run_id=run['id']))['status'] == 'error' else None))
        self.assertFalse(terminal['coverage_complete']); self.assertIsNone(terminal['summary'])
        self.assertIn('Synthetic calculation fault', terminal['error'])
        self.assertIn('no complete', self.error('alert_history_chart', run_id=run['id']))
        with self.service.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM indicator_history_rows_v1 WHERE run_id=?', (run['id'],)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
