from pathlib import Path
import tempfile
import unittest

from scripts.prepare_library_fixture import create_fixture
from terminal.data import DatasetStore, metadata_profile_fields
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager


class LibraryFixtureTests(unittest.TestCase):
    def test_new_only_fixture_has_complete_metadata_and_catalog_warmup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'new-synthetic-root'
            fixture = create_fixture(root)
            before = (root / 'synthetic-library-fixture.json').read_bytes()
            with self.assertRaises(FileExistsError):
                create_fixture(root)
            self.assertEqual((root / 'synthetic-library-fixture.json').read_bytes(), before)
            self.assertEqual(len(fixture['windows']), 2)
            self.assertLess(fixture['windows'][0]['end'], fixture['windows'][1]['history_start'])
            jobs = JobManager(root)
            manager = LibraryBatchManager(jobs)
            try:
                for window in fixture['windows']:
                    manifest, bars, _, _ = DatasetStore(root / 'datasets').load(window['dataset_id'])
                    self.assertTrue(manifest['metadata']['synthetic'])
                    self.assertIn('Synthetic', manifest['source'])
                    self.assertTrue(manifest['coverage']['trade']['complete'])
                    self.assertEqual(len(bars), 4032)
                    self.assertEqual(metadata_profile_fields(manifest)['quantity_step'], '0.000001')
                    self.assertEqual(manager.warmup(fixture['selections'], window['dataset_id'])['start'], window['start'])
                    preview = manager.preview(selections=fixture['selections'], dataset_id=window['dataset_id'],
                        profile=window['profile'], start=window['start'], end=window['end'],
                        interval=fixture['interval'], spot_dataset_id=None)
                    self.assertEqual(len(preview['rows']), 16)
                    prepared=manager.prepare(selections=fixture['selections'], dataset_id=window['dataset_id'],
                        profile=window['profile'], start=window['start'], end=window['end'],
                        interval=fixture['interval'], spot_dataset_id=None)
                    graph=next(r for r in prepared['rows'] if r['kind']=='graph' and not r['error'])
                    passive=next(r for r in prepared['rows'] if r['kind']=='benchmark' and not r['error'])
                    self.assertEqual(graph['profile']['version'],2)
                    self.assertEqual(passive['profile']['version'],1)
                    for key in ('capital','market','symbol','fee_rate','slippage','execution_minutes'):
                        self.assertEqual(graph['profile'][key],passive['profile'][key])
                    self.assertEqual(graph['dataset']['id'],passive['dataset']['id'])
                    unavailable = [r for r in preview['rows'] if r['error']]
                    self.assertEqual(len(unavailable), 2)
                    self.assertTrue(all(r['kind'] == 'native' for r in unavailable))
            finally:
                manager.close()
                jobs.close()

    def test_relative_destination_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'absolute'):
            create_fixture('relative-fixture')
