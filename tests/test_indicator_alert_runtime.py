"""Actual Service/MarketHub integration with guarded synthetic source receipts."""
import copy
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from terminal.data import canonical, digest
from terminal.display_indicators import CONTRACT
from terminal.market_hub import MarketHub
from terminal.service import AppService


def ident():
    return uuid.uuid4().hex


def condition(predicate='above'):
    return dict(predicate=predicate, left=dict(kind='series', instance_id='signal', port='value'),
                right=dict(kind='level', unit='price', value=10))


def candle(stamp, value):
    return dict(time=stamp, open=value, high=value+1, low=value-1, close=value, volume=2)


def wait_for(check, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = check()
        if result:
            return result
        time.sleep(.01)
    raise AssertionError('Timed out waiting for bounded synthetic worker')


class SyntheticStream:
    """Uses actual Hub._run fanout, never replaces the alert execution path."""
    def __init__(self, market, symbol):
        self.market, self.symbol = market, symbol
        self.subscribed = False
        self.inputs = queue.Queue()
        self.keep_fresh = True
        self.closed = False
        self.sequence = 0

    def open(self):
        self.subscribed = True
        self.state.connected()

    def fresh(self):
        self.sequence += 1
        now = int(time.time() * 1000)
        self.state.ticker_update({'lastPrice': '10'}, now)
        self.state.book_update('snapshot', {'u': self.sequence, 'seq': self.sequence,
            'b': [['9', '1']], 'a': [['11', '1']]}, now)

    def read(self):
        if self.keep_fresh:
            self.fresh()
        try:
            value = self.inputs.get(timeout=.02)
        except queue.Empty:
            return []
        if isinstance(value, Exception):
            raise value
        return [value]

    def close(self):
        self.closed = True


class AlertServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 1_800_000_000  # aligned to supported small native intervals
        self.clock = patch('time.time', side_effect=lambda: self.now)
        self.clock.start()
        self.guards = []
        self.calls = {key: 0 for key in ('provider', 'paper', 'orders', 'notifications')}
        for target, kind in [
            ('terminal.data.BybitClient.get', 'provider'),
            ('terminal.okx_market.OKXHistory.candles', 'provider'),
            ('terminal.live_data.PublicStream.open', 'provider'),
            ('terminal.live.LiveManager.start', 'orders'),
            ('terminal.live.LiveManager.start_manual', 'paper'),
            ('terminal.live.LiveManager.manual', 'paper'),
            ('terminal.live.LiveManager._notify', 'notifications'),
        ]:
            def denied(*args, _kind=kind, **kwargs):
                self.calls[_kind] += 1
                raise AssertionError('Forbidden external or trading action')
            guard = patch(target, side_effect=denied)
            guard.start(); self.guards.append(guard)
        self.service = AppService(Path(self.temp.name))
        self.streams = []
        def factory(market, symbol):
            stream = SyntheticStream(market, symbol)
            self.streams.append(stream)
            return stream
        self.service.live.hub.stream_factory = factory
        self.okx = patch('terminal.market_hub.OKXPublicStream', side_effect=factory)
        self.okx.start()
        self.call('market_open', source='bybit', market='spot', symbol='BTCUSDT')
        wait_for(lambda: self.service.live.hub.snapshot()['status'] == 'CONNECTED')
        self.session = ident()
        self.call('alert_session_init', session_id=self.session)
        self.context_revision = 1
        self.context(1)
        self.minutes = 1
        self.seed([8, 8])

    def tearDown(self):
        self.service.close()
        self.okx.stop()
        for guard in reversed(self.guards):
            guard.stop()
        self.clock.stop()
        self.temp.cleanup()
        self.assertEqual(self.calls, dict(provider=0, paper=0, orders=0, notifications=0))

    def call(self, command, **params):
        response = self.service.handle(dict(version=1, id=ident(), command=command, params=params))
        if response['type'] != 'result':
            raise AssertionError(response['error']['message'])
        return response['result']

    def error(self, command, **params):
        response = self.service.handle(dict(version=1, id=ident(), command=command, params=params))
        self.assertEqual(response['type'], 'error', response)
        return response['error']['message']

    def context(self, minutes, visible=True, source='bybit'):
        return self.call('alert_context', session_id=self.session, context_revision=self.context_revision,
            source=source, market='spot', symbol='BTCUSDT', minutes=minutes, visible=visible)

    def seed(self, values, minutes=1):
        self.minutes = minutes
        width = minutes * 60
        boundary = self.now // width * width
        self.origin = boundary - len(values) * width
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        settings = self.call('chart_indicator_save', market='spot', symbol='BTCUSDT', source='bybit',
            instances=[dict(id='signal', type='sma', params={'period': 2}, color='#abcdef', visible=True)],
            revision=settings['revision'])
        settings['origins'][str(minutes)] = dict(time=self.origin, generation=1, contract=CONTRACT)
        self.service.display_indicators._write('spot', 'BTCUSDT', settings)
        with self.service.store.connect() as db:
            for index, value in enumerate(values):
                row = candle(self.origin + index * width, value)
                key = ('spot', 'BTCUSDT', minutes, row['time'])
                db.execute('INSERT OR REPLACE INTO chart_candles_v1 VALUES(?,?,?,?,?)', (*key, canonical(row).decode()))
                db.execute('INSERT OR REPLACE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)', (*key, digest(row), 'synthetic_closed'))
        with self.service.live.hub.lock:
            self.service.live.hub.candles.clear()
            self.service.live.hub.confirmations.clear()
        self.emit(boundary - width, values[-1], minutes)
        wait_for(lambda: str(minutes) in self.service.live.hub.confirmations)
        return settings

    def emit(self, stamp, value, minutes=None):
        minutes = minutes or self.minutes
        interval = 'D' if minutes == 1440 else str(minutes)
        event = dict(kind='candle' if minutes == 1 else 'display_candle', interval=interval,
                     confirmed=True, candle=candle(stamp, value), provider_ms=self.now * 1000)
        self.streams[-1].inputs.put(event)
        return event

    def create(self, predicate='above'):
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        preview = self.call('alert_preview', source='bybit', market='spot', symbol='BTCUSDT', minutes=self.minutes,
                            settings_revision=settings['revision'], conditions=[condition(predicate)])
        self.create_params = dict(request_id=ident(), name='Synthetic local rule', **preview)
        return self.call('alert_create', **self.create_params)

    def arm(self, rule):
        params = dict(request_id=ident(), rule_id=rule['id'], revision=rule['revision'],
                      definition_hash=rule['definition_hash'], session_id=self.session,
                      context_revision=self.context_revision, reviewed=True)
        self.call('alert_arm', **params)
        return params

    def phase(self, rule, phase):
        return wait_for(lambda: (state if state['phase'] == phase else None) if (state := self.call('alert_status', rule_id=rule['id'])) else None)

    def test_initial_true_has_no_backlog_then_known_false_to_true_and_duplicate(self):
        self.seed([12, 12])
        rule = self.create()
        self.arm(rule); self.phase(rule, 'ARMED')
        self.assertEqual(self.call('alert_events')['events'], [])
        boundary = self.now
        self.now += 60; self.emit(boundary, 4)
        wait_for(lambda: self.service.indicator_alerts.store.cursor(rule['id'])['confirmed_at'] == self.now)
        self.now += 60; receipt = self.emit(boundary + 60, 20)
        event = wait_for(lambda: self.call('alert_events')['events'])
        self.assertEqual(len(event), 1)
        evidence = event[0]['evidence']
        self.assertEqual((evidence['raw_open_time'], evidence['confirmed_at'], evidence['observed_at']),
                         (boundary+60, boundary+120, boundary+120))
        self.assertEqual((evidence['conditions'][0]['previous_left'], evidence['conditions'][0]['left']), (8, 12))
        self.streams[-1].inputs.put(receipt)
        time.sleep(.25)
        self.assertEqual(len(self.call('alert_events')['events']), 1)
        self.assertTrue(self.call('alert_claim_banner', event_id=event[0]['id'])['claimed'])
        self.assertFalse(self.call('alert_claim_banner', event_id=event[0]['id'])['claimed'])
        self.assertTrue(self.call('alert_mark_read', event_id=event[0]['id'])['is_read'])

    def test_five_minute_native_arm_between_closes_and_later_cross(self):
        self.context_revision += 1; self.context(5)
        self.seed([8, 12], 5)
        baseline = self.service.live.hub.confirmations['5']
        baseline['observed_monotonic'] -= 120
        self.now += 120
        rule = self.create('cross_above')
        self.arm(rule); self.phase(rule, 'ARMED')
        self.assertEqual(self.call('alert_events')['events'], [])
        next_open = self.now // 300 * 300
        self.now = next_open + 300
        self.emit(next_open, 12, 5)
        event = wait_for(lambda: self.call('alert_events')['events'])[0]
        self.assertEqual(event['evidence']['confirmed_at'], self.now)
        self.assertEqual(event['evidence']['conditions'][0]['previous_left'], 10)
        self.assertEqual(event['evidence']['conditions'][0]['left'], 12)

    def test_create_lost_reply_is_durable_and_current_chart_changes_do_not_duplicate(self):
        rule = self.create()
        self.seed([8, 8])
        again = self.call('alert_create', **self.create_params)
        self.assertEqual(again['id'], rule['id'])
        self.assertEqual(len(self.call('alert_list')['rules']), 1)
        changed = dict(self.create_params, name='Different')
        self.assertIn('reused', self.error('alert_create', **changed))
        self.service.close(); self.service = AppService(Path(self.temp.name))
        self.assertEqual(self.call('alert_create', **self.create_params)['id'], rule['id'])
        self.assertEqual(self.call('alert_get', rule_id=rule['id'])['runtime']['phase'], 'PAUSED')

    def test_optional_fields_preview_readonly_and_strict_validation(self):
        before = self.service.display_indicators.settings('spot', 'BTCUSDT')
        rule = self.create()
        self.assertEqual(self.service.display_indicators.settings('spot', 'BTCUSDT'), before)
        self.assertEqual(self.call('alert_get', rule_id=rule['id'])['id'], rule['id'])
        self.assertEqual(self.call('alert_events'), dict(events=[], next_cursor=None))
        self.assertEqual(self.call('alert_status')['rules'], [])
        self.assertIn('unexpected', self.error('alert_list', nonsense=True))
        self.assertIn('unexpected', self.error('alert_arm', rule_id=rule['id']))
        wrong = dict(self.create_params, request_id=ident(), definition_hash='0'*64)
        self.assertIn('hash', self.error('alert_create', **wrong))

    def test_pending_arm_context_switch_cannot_publish_or_rearm_with_same_request(self):
        rule = self.create()
        entered, release = threading.Event(), threading.Event()
        from terminal.indicator_alert_runtime import replay as original
        def blocked(*args, **kwargs):
            entered.set(); release.wait(3)
            return original(*args, **kwargs)
        with patch('terminal.indicator_alert_runtime.replay', side_effect=blocked):
            params = self.arm(rule); self.assertTrue(entered.wait(2))
            self.context_revision += 1; self.context(5)
            release.set()
            self.phase(rule, 'PAUSED')
        time.sleep(.1)
        self.assertIsNone(self.service.indicator_alerts.store.cursor(rule['id']))
        self.assertEqual(self.call('alert_arm', **params)['phase'], 'PAUSED')
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_new_session_and_service_restart_pause_without_automatic_resume(self):
        rule = self.create(); params = self.arm(rule); self.phase(rule, 'ARMED')
        self.call('alert_session_init', session_id=ident())
        self.phase(rule, 'PAUSED')
        self.assertIsNone(self.call('alert_status')['context'])
        self.assertIn('changed', self.error('alert_context', session_id=self.session, context_revision=2,
            source='bybit', market='spot', symbol='BTCUSDT', minutes=1, visible=True))
        self.service.close(); self.service = AppService(Path(self.temp.name))
        self.assertEqual(self.call('alert_arm', **params)['phase'], 'PAUSED')
        self.assertIsNone(self.service.indicator_alerts.store.cursor(rule['id'])['token'])

    def test_stale_poll_pauses_without_another_candle(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        self.streams[-1].keep_fresh = False
        with self.service.live.hub.state.lock:
            self.service.live.hub.state.ticker_at = time.monotonic() - 20
        state = self.phase(rule, 'PAUSED')
        self.assertIn('stale', state['reason'])

    def test_native_close_stales_despite_fresh_ticker(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        self.now += 76
        self.assertIn('Native confirmed close is stale', self.phase(rule, 'PAUSED')['reason'])

    def test_receipt_gap_does_not_recover_from_cached_history(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        stamp = self.now + 60
        self.now += 120
        self.emit(stamp, 20)
        self.phase(rule, 'PAUSED')
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_changed_prefix_hash_pauses_even_without_new_receipt(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        with self.service.store.connect() as db:
            db.execute('UPDATE chart_candles_v1 SET candle=? WHERE market=? AND time=?',
                       (canonical(candle(self.origin, 9)).decode(), 'spot', self.origin))
        self.assertIn('input changed', self.phase(rule, 'PAUSED')['reason'])

    def test_hidden_deleted_preserve_but_changed_params_require_rebind(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        items = settings['instances']; items[0]['visible'] = False
        self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT',
                  instances=items, revision=settings['revision'])
        self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'ARMED')
        current = self.service.display_indicators.settings('spot', 'BTCUSDT')
        current['instances'][0]['params']['period'] = 3
        self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT',
                  instances=current['instances'], revision=current['revision'])
        self.phase(rule, 'PAUSED')
        self.assertTrue(self.call('alert_get', rule_id=rule['id'])['rebind_required'])
        current = self.service.display_indicators.settings('spot', 'BTCUSDT')
        current['instances'][0]['params']['period'] = 2
        self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT',
                  instances=current['instances'], revision=current['revision'])
        self.assertIn('rebind', self.error('alert_arm', request_id=ident(), rule_id=rule['id'], revision=rule['revision'],
            definition_hash=rule['definition_hash'], session_id=self.session, context_revision=1, reviewed=True))
        current = self.service.display_indicators.settings('spot', 'BTCUSDT')
        preview = self.call('alert_preview', source='bybit', market='spot', symbol='BTCUSDT', minutes=1,
                            settings_revision=current['revision'], conditions=[condition()])
        rule = self.call('alert_rebind', rule_id=rule['id'], revision=rule['revision'], **preview)
        self.assertFalse(rule['rebind_required'])
        self.arm(rule); self.phase(rule, 'ARMED')
        current = self.service.display_indicators.settings('spot', 'BTCUSDT')
        self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT', instances=[], revision=current['revision'])
        self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'ARMED')

    def test_observer_does_not_block_source_switch_and_strategy_feed_still_does(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        self.assertEqual(len(self.service.live.hub.consumers), 0)
        self.call('market_open', source='okx', market='spot', symbol='BTCUSDT')
        self.phase(rule, 'PAUSED')
        wait_for(lambda: self.service.live.hub.snapshot()['status'] == 'CONNECTED')
        from terminal.market_hub import MarketFeed
        feed = MarketFeed(self.service.live.hub); feed.open()
        try:
            self.assertIn('Pause strategy', self.error('market_open', source='bybit', market='spot', symbol='BTCUSDT'))
        finally:
            feed.close()

    def test_reconnect_pauses_then_explicit_new_arm_establishes_new_baseline(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        self.streams[-1].inputs.put(ConnectionError('synthetic reconnect'))
        self.phase(rule, 'PAUSED')
        wait_for(lambda: len(self.streams) == 2 and self.service.live.hub.snapshot()['status'] == 'CONNECTED')
        self.emit(self.now - 60, 8)
        wait_for(lambda: bool(self.service.live.hub.confirmations))
        self.arm(rule); self.phase(rule, 'ARMED')
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_bounded_three_queue_overflow_fails_closed_during_arm(self):
        rule = self.create()
        entered, release = threading.Event(), threading.Event()
        from terminal.indicator_alert_runtime import replay as original
        def blocked(*args, **kwargs):
            entered.set(); release.wait(3); return original(*args, **kwargs)
        with patch('terminal.indicator_alert_runtime.replay', side_effect=blocked):
            self.arm(rule); self.assertTrue(entered.wait(2))
            observer = self.service.indicator_alerts.states[rule['id']]['observer']
            for offset in range(4): self.emit(self.now - (5-offset)*60, 8)
            wait_for(lambda: observer.failed)
            self.assertEqual(observer.events.qsize(), 3)
            release.set(); self.phase(rule, 'PAUSED')
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_metadata_edits_are_paused_and_uncertain_edits_inspectable(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        renamed = self.call('alert_rename', rule_id=rule['id'], revision=rule['revision'], name='Renamed')
        self.assertEqual(renamed['runtime']['phase'], 'PAUSED')
        self.assertIn('changed', self.error('alert_rename', rule_id=rule['id'], revision=rule['revision'], name='Renamed'))
        archived = self.call('alert_archive', rule_id=rule['id'], revision=renamed['revision'])
        self.assertEqual(self.call('alert_list')['rules'], [])
        self.assertEqual(self.call('alert_list', trashed=True)['rules'][0]['id'], rule['id'])
        restored = self.call('alert_restore', rule_id=rule['id'], revision=archived['revision'])
        self.assertEqual(restored['runtime']['phase'], 'PAUSED')

    def test_catalog_request_lookup_and_duplicate_burst_are_read_only_and_bounded(self):
        catalog = self.call('alert_catalog')
        self.assertEqual(catalog['ports']['rsi']['value'], catalog['ports']['stochastic']['k'])
        self.assertNotEqual(catalog['ports']['rsi']['value'], catalog['ports']['roc']['value'])
        self.assertEqual(catalog['ports']['ichimoku'], dict(tenkan='price', kijun='price'))
        self.assertEqual(self.call('alert_request', request_id=ident()), None)
        rule = self.create(); params = self.arm(rule); self.phase(rule, 'ARMED')
        self.assertEqual(self.call('alert_request', request_id=self.create_params['request_id'])['rule_id'], rule['id'])
        self.assertEqual(self.call('alert_request', request_id=params['request_id'])['kind'], 'arm')
        for _ in range(20): self.emit(self.now - 60, 8)
        wait_for(lambda: self.streams[-1].inputs.empty())
        time.sleep(.1)
        observer = self.service.indicator_alerts.states[rule['id']]['observer']
        self.assertEqual(observer.events.qsize(), 0)
        self.assertFalse(observer.failed)
        self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'ARMED')
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_premature_baseline_observation_and_future_close_are_rejected(self):
        rule = self.create()
        receipt = self.service.live.hub.confirmations['1']
        receipt['observed_at'] = self.now - 1
        self.assertIn('before native confirmation', self.error('alert_arm', request_id=ident(), rule_id=rule['id'],
            revision=rule['revision'], definition_hash=rule['definition_hash'], session_id=self.session,
            context_revision=1, reviewed=True))
        receipt['observed_at'] = self.now
        self.arm(rule); self.phase(rule, 'ARMED')
        self.emit(self.now, 20)  # It cannot be confirmed until now+60.
        self.assertIn('before its close', self.phase(rule, 'PAUSED')['reason'])
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_conflicting_duplicate_below_provider_watermark_is_not_silently_dropped(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        receipt = dict(kind='candle', interval='1', candle=candle(self.now - 60, 50),
                       provider_ms=(self.now - 10) * 1000)
        self.streams[-1].inputs.put(receipt)
        self.assertIn('duplicate', self.phase(rule, 'PAUSED')['reason'])
        self.assertEqual(self.call('alert_events')['events'], [])

    def test_active_definition_byte_budget_rejects_complete_second_admission(self):
        from terminal.indicator_alerts import encode
        rule = self.create()
        other = self.create()
        with patch('terminal.indicator_alerts.MAX_ACTIVE_BYTES', len(encode(rule['definition'])) + 3):
            self.arm(rule); self.phase(rule, 'ARMED')
            self.assertIn('byte resource budget', self.error('alert_arm', request_id=ident(), rule_id=other['id'],
                revision=other['revision'], definition_hash=other['definition_hash'], session_id=self.session,
                context_revision=1, reviewed=True))
            self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'ARMED')
            self.assertEqual(self.call('alert_status', rule_id=other['id'])['phase'], 'PAUSED')
            self.assertEqual(len(self.service.live.hub.observers), 1)

    def test_close_timeout_retains_dependencies_and_workspace_until_worker_stops(self):
        rule = self.create()
        entered, release = threading.Event(), threading.Event()
        from terminal.indicator_alert_runtime import replay as original
        def blocked(*args, **kwargs):
            entered.set(); release.wait(5); return original(*args, **kwargs)
        try:
            with patch('terminal.indicator_alert_runtime.replay', side_effect=blocked):
                self.arm(rule); self.assertTrue(entered.wait(2))
                with self.assertRaisesRegex(RuntimeError, 'keep dependencies'):
                    self.service.close()
                self.assertTrue(self.service.display_indicators.thread.is_alive())
                self.assertTrue(self.service.live.chart_history.thread.is_alive())
                self.assertTrue(self.service.live.hub.thread.is_alive())
                self.assertIsNone(self.service.indicator_alerts.store.cursor(rule['id']))
        finally:
            release.set()
            wait_for(lambda: not self.service.indicator_alerts.thread.is_alive())

    def test_layout_only_edit_keeps_arm_and_cached_raw_values(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        # SMA is a price overlay; layout changes neither its frozen params nor origin.
        candidate = dict(version=1, price_weight=400, recorded_weight=150, panes=[])
        self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT',
            instances=settings['instances'], revision=settings['revision'], pane_layout=candidate)
        self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'ARMED')
        self.assertEqual(self.call('alert_get', rule_id=rule['id'])['definition'], rule['definition'])

    def test_concurrent_save_revert_cannot_hide_changed_dependency(self):
        rule = self.create(); self.arm(rule); self.phase(rule, 'ARMED')
        settings = self.service.display_indicators.settings('spot', 'BTCUSDT')
        changed = copy.deepcopy(settings['instances']); changed[0]['params']['period'] = 3
        entered, release, second_done = threading.Event(), threading.Event(), threading.Event()
        original = self.service.display_indicators.save
        errors = []
        def blocking_save(**params):
            result = original(**params)
            if params['instances'][0]['params']['period'] == 3:
                entered.set(); release.wait(3)
            return result
        def save(items, revision, done=None):
            try:
                self.call('chart_indicator_save', source='bybit', market='spot', symbol='BTCUSDT',
                          instances=items, revision=revision)
            except Exception as exc:
                errors.append(exc)
            finally:
                if done: done.set()
        with patch.object(self.service.display_indicators, 'save', side_effect=blocking_save):
            first = threading.Thread(target=save, args=(changed, settings['revision']))
            second = threading.Thread(target=save, args=(settings['instances'], settings['revision']+1, second_done))
            first.start()
            try:
                self.assertTrue(entered.wait(2)); second.start()
                self.assertFalse(second_done.wait(.1))
                self.assertEqual(self.service.display_indicators.settings('spot', 'BTCUSDT')['instances'][0]['params']['period'], 3)
            finally:
                release.set(); first.join(3)
                if second.ident is not None: second.join(3)
        self.assertEqual(errors, [])
        self.assertTrue(second_done.is_set())
        self.assertEqual(self.service.display_indicators.settings('spot', 'BTCUSDT')['instances'][0]['params']['period'], 2)
        self.assertEqual(self.call('alert_status', rule_id=rule['id'])['phase'], 'PAUSED')
        self.assertTrue(self.call('alert_get', rule_id=rule['id'])['rebind_required'])
