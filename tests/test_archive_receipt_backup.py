"""Full closed-workspace copies, never a live database-file-only copy."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from terminal.data import canonical
from terminal.service import AppService
from tests.archive_receipt_fixtures import archive, sentinels


def files(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*')
            if p.is_file() and p.name not in ('terminal.sqlite3','terminal.sqlite3-wal','terminal.sqlite3-shm')}


def tables(root):
    with sqlite3.connect((root/'terminal.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name:[list(row) for row in db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid')] for name in names}


def copy_closed(source, destination):
    destination.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect((source/'terminal.sqlite3').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(destination/'terminal.sqlite3') as dst:src.backup(dst)
    for path in source.iterdir():
        if path.name in ('terminal.sqlite3','terminal.sqlite3-wal','terminal.sqlite3-shm'):continue
        if path.is_dir():shutil.copytree(path,destination/path.name)
        else:shutil.copy2(path,destination/path.name)


def check_database(store):
    with store.connect() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    for run in store.recent():
        if run['status']=='completed':store.result(run['id'])


class ReceiptBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_legacy_full_copy_adds_only_empty_receipt_tables(self):
        source=self.root/'legacy';service=AppService(source)
        sentinels(service.store);service.close()
        # Model a pre-feature closed workspace without manufacturing import history.
        with sqlite3.connect(source/'terminal.sqlite3') as db:
            db.execute('DROP TABLE archive_import_items');db.execute('DROP TABLE archive_imports')
        (source/'datasets'/'retained').mkdir(parents=True);(source/'datasets'/'retained'/'fixture.bin').write_bytes(b'independent full-root retention fixture')
        (source/'imports').mkdir();(source/'imports'/'legacy.partial').write_bytes(b'never parse or promote')
        before=tables(source);artifacts=files(source);destination=self.root/'copy';copy_closed(source,destination)
        for _ in range(2):
            service=AppService(destination)
            try:
                check_database(service.store)
                self.assertEqual(service.archives.recent()['rows'],[])
                after=tables(destination);self.assertEqual({name:after[name] for name in before},before)
                self.assertEqual(set(after)-set(before),{'archive_imports','archive_import_items'})
            finally:service.close()
            self.assertEqual(files(destination),artifacts)
        self.assertEqual(tables(source),before);self.assertEqual(files(source),artifacts)

    def test_complete_and_interrupted_receipts_survive_full_restore_without_resume(self):
        source=self.root/'source';service=AppService(source);sentinels(service.store)
        raw,_,_=archive()
        def import_one():
            op=service.archives.begin(len(raw))['operation_id'];service.archives.append(op,0,base64.b64encode(raw).decode());return op
        complete=import_one();service.archives.finish(complete)
        interrupted=import_one();original=service.archives.receipts.publish_run
        def fail_second(op,ordinal,*args):
            if ordinal==1:raise OSError('fixture')
            return original(op,ordinal,*args)
        with patch.object(service.archives.receipts,'publish_run',side_effect=fail_second),patch.object(service.archives.receipts,'stop',side_effect=OSError('fixture')):
            with self.assertRaises(ValueError):service.archives.finish(interrupted)
        mappings={op:service.archives.status(op) for op in (complete,interrupted)}
        service.close();before=tables(source);artifacts=files(source);destination=self.root/'restored';copy_closed(source,destination)
        service=AppService(destination)
        try:
            check_database(service.store)
            self.assertEqual(service.archives.status(complete),mappings[complete])
            recovered=service.archives.status(interrupted);self.assertEqual(recovered['outcome'],'partial')
            self.assertEqual(recovered['termination_reason'],'process_restart')
            self.assertEqual([i['destination_id'] for i in recovered['items']],[i['destination_id'] for i in mappings[interrupted]['items']])
            self.assertIsNone(service.jobs.active);self.assertIsNone(service.archives.upload)
            after=tables(destination)
            for name in before:
                if name not in ('runs','archive_imports','archive_import_items'):self.assertEqual(before[name],after[name])
            self.assertEqual(len(after['runs']),len(before['runs']))
            for old,new in zip(before['runs'],after['runs']):
                changed=[i for i,(a,b) in enumerate(zip(old,new)) if a!=b]
                self.assertTrue(not changed or old[2]=='importing' and new[2]=='interrupted' and set(changed)<={2,4})
        finally:service.close()
        self.assertEqual(files(destination),artifacts);self.assertEqual(tables(source),before);self.assertEqual(files(source),artifacts)
        unchanged=tables(destination);service=AppService(destination);service.close();self.assertEqual(tables(destination),unchanged)
