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

    def test_annotations_restart_search_and_immutable_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            snapshot='{"rows":[],"inputs":{"note":"original"}}'
            try:
                with jobs.store.connect() as db:
                    for i in range(125):
                        db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',(f'{i:032x}','2026-01-01T00:00:00+00:00','completed',snapshot,None))
                oldest='0'*32
                self.assertEqual(manager.get(oldest)['metadata'],{'name':'','notes':'','revision':0})
                saved=manager.save_metadata(oldest,'  Исследование 100%_  ',"Owner's note",0)
                self.assertEqual(saved['name'],'Исследование 100%_')
                for query in ('  ИССЛЕДОВАНИЕ  ', '100%_', "Owner's",oldest):
                    page=manager.history_page(query=query)
                    self.assertEqual([r['id'] for r in page['rows']],[oldest])
                self.assertEqual(manager.history_page(query='absent')['rows'],[])
                with self.assertRaisesRegex(ValueError,'another editor'):
                    manager.save_metadata(oldest,'Overwrite','',0)
                for name,notes,revision in ((None,'',1),('x'*121,'',1),('', 'x'*4001,1),('','',True),('','',-1)):
                    with self.assertRaises(ValueError):manager.save_metadata(oldest,name,notes,revision)
                with self.assertRaisesRegex(ValueError,'Unknown'):
                    manager.save_metadata('f'*32,'Unknown','',0)
                for query in (None,'x'*201,'\x00'):
                    with self.assertRaises(ValueError):manager.history_page(query=query)
                manager.close();jobs.close()
                jobs=JobManager(root);manager=LibraryBatchManager(jobs)
                self.assertEqual(manager.get(oldest)['metadata'],saved)
                with jobs.store.connect() as db:
                    self.assertEqual([r[0] for r in db.execute('SELECT snapshot FROM library_batches')],[snapshot]*125)
                self.assertEqual(manager.save_metadata(oldest,'','',1),{'name':'','notes':'','revision':2})
            finally:manager.close();jobs.close()

    def test_annotation_write_failure_rolls_back_without_touching_batch(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs);ident='a'*32
            try:
                with jobs.store.connect() as db:
                    db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',(ident,'2026-01-01','completed','{"rows":[]}',None))
                saved=manager.save_metadata(ident,'Original','Keep notes',0)
                with jobs.store.connect() as db:
                    db.execute("CREATE TRIGGER fail_annotation BEFORE UPDATE ON library_batch_metadata BEGIN SELECT RAISE(ABORT,'Synthetic write failure'); END")
                    original=tuple(db.execute('SELECT * FROM library_batches').fetchone())
                with self.assertRaisesRegex(sqlite3.IntegrityError,'Synthetic write failure'):
                    manager.save_metadata(ident,'Changed','Lost?',1)
                self.assertEqual(manager.metadata(ident),saved)
                with jobs.store.connect() as db:self.assertEqual(tuple(db.execute('SELECT * FROM library_batches').fetchone()),original)
            finally:manager.close();jobs.close()

    def test_metadata_ipc_contract_and_original_run_files_survive(self):
        from terminal.service import AppService
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            service=AppService.__new__(AppService);service.library_batches=manager
            ident='c'*32
            try:
                run_id=jobs.store.create({'synthetic_fixture':'immutable evidence'})
                artifact=jobs.store.directory(run_id)/'result.json'
                artifact.write_bytes(b'{"synthetic_fixture":"original report bytes"}')
                before={p.name:p.read_bytes() for p in jobs.store.directory(run_id).iterdir()}
                with jobs.store.connect() as db:
                    db.execute('INSERT INTO library_batches VALUES(?,?,?,?,?)',(ident,'2026-01-01','completed','{"rows":[]}',None))
                    db.execute('UPDATE runs SET summary=? WHERE id=?',('{"net_pnl":"-7"}',run_id))
                def call(command,params):return service.handle({'version':1,'id':'fixture','command':command,'params':params})
                self.assertEqual(call('library_batch_save_metadata',{'batch_id':ident,'name':'Saved fixture','notes':'Synthetic only','expected_revision':0})['type'],'result')
                self.assertEqual(call('library_batch_history',{'before':None,'query':'fixture'})['type'],'result')
                self.assertEqual(call('library_batch_save_metadata',{'batch_id':ident,'name':'Missing fields'})['type'],'error')
                self.assertEqual(call('library_batch_metadata',{'batch_id':'f'*32})['type'],'error')
                self.assertEqual({p.name:p.read_bytes() for p in jobs.store.directory(run_id).iterdir()},before)
                with jobs.store.connect() as db:self.assertEqual(db.execute('SELECT summary FROM runs WHERE id=?',(run_id,)).fetchone()[0],'{"net_pnl":"-7"}')
            finally:manager.close();jobs.close()
