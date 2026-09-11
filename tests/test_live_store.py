import json
from pathlib import Path
import tempfile
import unittest

from terminal.graph import example_graph
from terminal.live_store import LiveSession, LiveStore, RecoveryRequired
from terminal.profile import Profile
from terminal.series import Candle
from terminal.storage import RunStore


def bar(minute,price):
    return Candle(minute*60,price,price,price,price,1)


class LiveJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs=RunStore(Path(self.temp.name))
        self.store=LiveStore(self.runs)
        self.id=self.store.create(example_graph(),Profile(primary_minutes=1),'test-strategy','Synthetic transition')
        self.session=LiveSession(self.store,self.id)

    def test_restart_recovery_dedup_and_delivery_attempt(self):
        self.session.ingest(bar(0,100),60000,'warmup')
        self.store.state(self.id,'CONNECTED','Verified fixture')
        event=self.session.ingest(bar(1,110),120000)[0]
        self.assertTrue(self.store.claim(event['id']))
        restored=LiveSession(self.store,self.id)
        self.assertEqual(self.store.get(self.id)['status'],'PAUSED')
        self.assertFalse(self.store.claim(event['id']))
        self.assertEqual(restored.ingest(bar(1,110),130000),[])
        self.assertEqual(restored.ingest(bar(2,120),180000,'recovered'),[])
        restored.ingest(bar(3,90),240000,'recovered')
        self.assertEqual(self.store.events(self.id)[0]['delivery'],'suppressed')
        self.store.state(self.id,'CONNECTED','Recovered fixture')
        restored.ingest(bar(4,100),300000)
        self.assertEqual([e['time'] for e in self.store.events(self.id) if e['type']=='entry_long'],[300,120])
        self.assertEqual(restored.verify_replay(),{'match':True,'checked_events':3})

    def test_gap_blocks_state_until_reconstructed_and_conflicts_fail(self):
        self.session.ingest(bar(0,100),60000,'warmup')
        with self.assertRaises(RecoveryRequired):self.session.ingest(bar(2,120),180000)
        self.assertEqual(self.session.last,0)
        self.assertEqual(self.store.get(self.id)['status'],'RECOVERING DATA')
        self.session.ingest(bar(1,110),180000,'recovered')
        self.session.ingest(bar(2,120),180000,'recovered')
        self.assertEqual(self.store.events(self.id)[0]['delivery'],'suppressed')
        with self.assertRaises(RecoveryRequired):self.session.ingest(bar(1,99),180000)
        self.assertEqual(self.store.get(self.id)['status'],'ERROR')
        self.assertTrue(self.session.verify_replay()['match'])

    def test_unclosed_data_rejected_and_replay_detects_tampering(self):
        with self.assertRaises(ValueError):self.session.ingest(bar(0,100),59000)
        self.session.ingest(bar(0,100),60000,'warmup')
        self.session.ingest(bar(1,110),120000,'recovered')
        with self.runs.connect() as db:db.execute('DELETE FROM live_signals WHERE session_id=?',(self.id,))
        self.assertFalse(self.session.verify_replay()['match'])

    def test_additive_schema_leaves_existing_records_unchanged(self):
        # Add a representative preexisting row and rerun migration twice.
        with self.runs.connect() as db:
            db.execute('INSERT INTO strategies VALUES(?,?,?,?,?,?)',('existing','Preserve','graph','{}','old','{}'))
            before=[tuple(r) for r in db.execute('SELECT * FROM strategies')]
        LiveStore(self.runs);LiveStore(self.runs)
        with self.runs.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM strategies')],before)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
