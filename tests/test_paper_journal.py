import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

from terminal.paper_journal import PaperJournal, PaperRecordingError
from terminal.profile import Profile, dec
from terminal.storage import RunStore


class PaperJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=RunStore(Path(self.temp.name))
        with self.store.connect() as db:db.execute('CREATE TABLE paper_observations(session_id TEXT,sequence INTEGER,observation TEXT,result TEXT,PRIMARY KEY(session_id,sequence))')
        self.profile=Profile(market='linear',leverage='2',primary_minutes=1)
        self.lookup=Mock();self.lookup.get.return_value=None

    def journal(self):
        journal=PaperJournal(self.store,'fixture',self.profile,self.lookup)
        self.addCleanup(journal.close)
        return journal

    def price(self,ms,price,next_funding):
        return {'observed_ms':ms,'provider_ms':ms,'price':price,'mark':price,'next_funding_ms':next_funding}

    def test_delayed_confirmed_funding_preserves_observations_and_independent_account(self):
        journal=self.journal()
        journal.append(self.price(60000,'100',120000),{'entry_short':True});journal.process()
        journal.append(self.price(120000,'100',240000));self.assertEqual(journal.process(),[])
        journal.append(self.price(180000,'90',240000),{'exit_short':True});self.assertEqual(journal.process(),[])
        self.assertEqual(journal.snapshot()['pending_observations'],2)
        self.assertTrue(journal.snapshot()['waiting_funding'])
        self.lookup.get.return_value='.01'
        results=journal.process()
        self.assertEqual(len(results),2)
        self.assertEqual(dec(results[-1]['equity']),dec('1021.62'))
        self.assertEqual(results[0]['events'][0]['amount'],'2')
        self.assertEqual(journal.snapshot()['pending_observations'],0)

    def test_restart_reconstructs_completed_account_and_pending_funding(self):
        journal=self.journal()
        journal.append(self.price(60000,'100',120000),{'entry_short':True});journal.process()
        journal.append(self.price(120000,'100',240000));journal.process();journal.close()
        restored=self.journal()
        self.assertEqual(restored.snapshot()['position']['side'],'short')
        self.assertEqual(restored.snapshot()['pending_observations'],1)
        self.lookup.get.return_value='.01';restored.process()
        self.assertEqual(dec(restored.snapshot()['cash']),dec('1001.8'))
        restored.close();again=self.journal()
        self.assertEqual(dec(again.snapshot()['cash']),dec('1001.8'))
        self.assertEqual(again.process(),[])

    def test_failed_result_commit_stops_engine_and_keeps_input(self):
        journal=self.journal();journal.append(self.price(60000,'100',120000),{'entry_short':True})
        with self.store.connect() as db:db.execute('DROP TABLE paper_observations')
        with self.assertRaises(PaperRecordingError):journal.process()
        self.assertTrue(journal.engine.closed)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM paper_inputs').fetchone()[0],1)

    def test_unobserved_funding_gap_cannot_silently_resume(self):
        journal=self.journal();journal.append(self.price(60000,'100',120000),{'entry_short':True});journal.process()
        with self.assertRaises(PaperRecordingError):journal.append(self.price(600000,'90',720000))
        self.assertEqual(journal.sequence,1)
