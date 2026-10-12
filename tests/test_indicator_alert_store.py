"""Durable alert evidence tests use isolated synthetic databases only."""
import copy
import sqlite3
import tempfile
import unittest

from terminal.indicator_alert_store import IndicatorAlertStore
from terminal import indicator_alerts as alerts
from terminal.storage import RunStore
from test_indicator_alerts import definition, candles


class AlertStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.database = RunStore(self.directory.name)
        self.store = IndicatorAlertStore(self.database)
        self.rule = self.store.create('SMA crossing', definition())
        self.rows = alerts.replay(self.rule['definition'], candles([8, 12, 10, 14]))['rows']

    def arm(self):
        return self.store.begin_cursor(self.rule['id'], self.rule['revision'], self.rows[1])['token']

    def commit(self, token):
        return self.store.commit_evaluation(self.rule['id'], self.rule['revision'], token, 120, self.rows[2], observed_at=181)

    def test_create_arm_baseline_and_restart_never_restore_monitoring(self):
        self.assertIsNone(self.store.cursor(self.rule['id']))
        token = self.arm()
        self.assertEqual(self.store.events()['events'], [])
        self.commit(token)
        reopened = IndicatorAlertStore(self.database)
        self.assertIsNone(reopened.cursor(self.rule['id'])['token'])
        self.assertEqual(reopened.cursor(self.rule['id'])['confirmed_at'], 180)
        self.assertEqual(len(reopened.events()['events']), 1)
        with self.assertRaisesRegex(ValueError, 'paused'): self.commit(token)

    def test_dedup_across_receipt_retry_and_new_arm_tokens(self):
        token = self.arm(); first = self.commit(token)
        duplicate = self.commit(token)
        self.assertTrue(duplicate['duplicate']); self.assertEqual(first['event_id'], duplicate['event_id'])
        second_token = self.arm(); repeated = self.commit(second_token)
        self.assertTrue(repeated['duplicate']); self.assertEqual(first['event_id'], repeated['event_id'])
        self.assertEqual(len(self.store.events()['events']), 1)
        changed = copy.deepcopy(self.rows[2]); changed['conditions'][0]['left'] = 999
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            self.store.commit_evaluation(self.rule['id'], 1, second_token, 120, changed, observed_at=182)

    def test_atomic_failure_between_event_insert_and_cursor_advance(self):
        token = self.arm()
        with self.database.connect() as db:
            db.execute("CREATE TRIGGER fail_cursor BEFORE UPDATE OF confirmed_at ON indicator_alert_cursors_v1 BEGIN SELECT RAISE(ABORT,'injected cursor failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'injected'): self.commit(token)
        self.assertEqual(self.store.events()['events'], [])
        self.assertEqual(self.store.cursor(self.rule['id'])['confirmed_at'], 120)
        with self.database.connect() as db: db.execute('DROP TRIGGER fail_cursor')
        self.assertIsNotNone(self.commit(token)['event_id'])

    def test_immutable_evidence_read_state_and_at_most_once_banner_claim(self):
        event_id = self.commit(self.arm())['event_id']
        original = self.store.event(event_id)['evidence']
        self.assertEqual(original['observed_at'], 181)
        self.assertEqual((original['raw_open_time'], original['confirmed_at']), (120, 180))
        self.assertTrue(self.store.claim_banner(event_id)); self.assertFalse(self.store.claim_banner(event_id))
        self.assertTrue(self.store.mark_read(event_id)['is_read'])
        self.assertEqual(self.store.events(unread_only=True)['events'], [])
        self.assertFalse(self.store.mark_read(event_id, False)['is_read'])
        with self.database.connect() as db:
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
                db.execute('UPDATE indicator_alert_events_v1 SET evidence=? WHERE id=?', ('{}', event_id))
        reopened = IndicatorAlertStore(self.database)
        self.assertEqual(reopened.event(event_id)['evidence'], original)
        self.assertFalse(reopened.claim_banner(event_id))

    def test_rename_current_label_rebind_paused_and_recoverable_trash(self):
        token = self.arm(); event_id = self.commit(token)['event_id']
        original = self.store.event(event_id)['evidence']
        renamed = self.store.rename(self.rule['id'], 1, 'Current title')
        self.assertEqual(renamed['definition_revision'], 1)
        self.assertEqual(self.store.event(event_id)['current_name'], 'Current title')
        self.assertIsNone(self.store.cursor(self.rule['id'])['token'])
        with self.assertRaisesRegex(ValueError, 'changed'): self.store.rename(self.rule['id'], 1, 'Stale')
        rebound = self.store.rebind(self.rule['id'], 2, definition('cross_below'))
        self.assertEqual(rebound['definition_revision'], 2)
        self.assertIsNone(self.store.cursor(self.rule['id'])['token'])
        trashed = self.store.trash(self.rule['id'], 3)
        self.assertTrue(trashed['deleted']); self.assertEqual(self.store.list()['rules'], [])
        self.assertEqual(len(self.store.list(True)['rules']), 1)
        with self.assertRaisesRegex(ValueError, 'trashed'): self.store.begin_cursor(self.rule['id'], 4, self.rows[1])
        restored = self.store.restore(self.rule['id'], 4)
        self.assertFalse(restored['deleted'])
        self.assertEqual(self.store.event(event_id)['evidence'], original)

    def test_invalid_timestamp_cursor_transition_and_stale_tokens_fail_closed(self):
        token = self.arm(); bad = copy.deepcopy(self.rows[2]); bad['hit'] = False
        with self.assertRaisesRegex(ValueError, 'transition'):
            self.store.commit_evaluation(self.rule['id'], 1, token, 120, bad, observed_at=181)
        with self.assertRaisesRegex(ValueError, 'observation'):
            self.store.commit_evaluation(self.rule['id'], 1, token, 120, self.rows[2], observed_at=179)
        self.store.invalidate_cursor(self.rule['id'])
        with self.assertRaisesRegex(ValueError, 'paused'): self.commit(token)
        self.assertEqual(self.store.events()['events'], [])

    def test_saved_rule_count_is_not_capped_and_keyset_pages_have_no_lost_tail(self):
        for index in range(129): self.store.create('Rule '+str(index), self.rule['definition'])
        found = []; after = None
        while True:
            page = self.store.list(after=after, limit=20)
            found.extend(item['id'] for item in page['rules'])
            after = page['next_cursor']
            if after is None: break
        self.assertEqual(len(found), 130); self.assertEqual(len(set(found)), 130)

    def test_additive_store_preserves_existing_workspace_data(self):
        with self.database.connect() as db:
            db.execute("INSERT INTO strategies VALUES('fixture','Existing','graph','{}','now',NULL)")
        IndicatorAlertStore(self.database)
        with self.database.connect() as db:
            self.assertEqual(db.execute("SELECT name FROM strategies WHERE id='fixture'").fetchone()[0], 'Existing')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
