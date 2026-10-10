import json
import tempfile
import unittest
from unittest.mock import patch

from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager


class LibraryHistoryTests(unittest.TestCase):
    def test_keyset_pages_reopen_oldest_without_execution_or_rewriting(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                snapshot=json.dumps({'phase':'selection','rows':[], 'inputs':{'note':'Synthetic saved comparison'}})
                with jobs.store.connect() as db:
                    for i in range(125):
                        db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',
                                   (f'{i:032x}','2026-01-01T00:00:00+00:00','completed',snapshot,None))
                first=manager.history_page();self.assertEqual(len(first['rows']),50)
                self.assertEqual(manager.recent(),first['rows'])
                # Same-timestamp IDs and a new leading row cannot duplicate/skip older records.
                with jobs.store.connect() as db:
                    db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',
                               ('f'*32,'2026-01-02T00:00:00+00:00','completed',snapshot,None))
                second=manager.history_page(first['next']);third=manager.history_page(second['next'])
                ids=[r['id'] for page in (first,second,third) for r in page['rows']]
                self.assertEqual(len(ids),125);self.assertEqual(len(set(ids)),125)
                self.assertEqual(len(third['rows']),25);self.assertIsNone(third['next'])
                with patch.object(jobs,'start',side_effect=AssertionError('Must not recalculate')):
                    reopened=manager.get(ids[-1])
                self.assertEqual(reopened['snapshot'],json.loads(snapshot))
                with jobs.store.connect() as db:
                    self.assertEqual(db.execute('SELECT snapshot FROM library_batches WHERE id=?',(ids[-1],)).fetchone()[0],snapshot)
                for invalid in ({}, {'id':'bad','created_at':'2026-01-01'}, {'id':'0'*32,'created_at':'invalid'}):
                    with self.assertRaises(ValueError):manager.history_page(invalid)
            finally:
                manager.close();jobs.close()

    def test_byte_limited_page_keeps_an_exact_continuation(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                with jobs.store.connect() as db:
                    for i in range(4):
                        db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',
                            (f'{i:032x}','2026-01-01T00:00:00+00:00','failed','{"rows":[]}', 'Synthetic failure detail '*9000))
                first=manager.history_page()
                self.assertGreater(len(first['rows']),0);self.assertLess(len(first['rows']),50)
                self.assertIsNotNone(first['next'])
                second=manager.history_page(first['next'])
                ids=[r['id'] for page in (first,second) for r in page['rows']]
                self.assertEqual(len(ids),4);self.assertEqual(len(set(ids)),4)
                self.assertIsNone(second['next'])
            finally:manager.close();jobs.close()
