"""Independent local-history/journal expectations; all data is synthetic."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.observations import Observations
from terminal.profile import Profile
from terminal.series import Candle


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.jobs=JobManager(self.temp.name);self.addCleanup(self.jobs.close)
        self.library=LibraryBatchManager(self.jobs);self.addCleanup(self.library.close)
        self.obs=Observations(self.jobs.store,self.jobs.datasets)
        self.dataset=self.jobs.datasets.save('spot','BTCUSDT',0,3600,
            [Candle(i*60,100+i,102+i,99+i,101+i,10) for i in range(60) if i!=12],[],{},
            metadata={'synthetic':True},provenance=[],source='Synthetic observation contract')
        self.profile=Profile(primary_minutes=1,capital='180',allocation='100',gap_policy='skip')

    def save(self,**changes):
        return self.obs.save(**dict(observation_id=None,expected_revision=0,dataset_id=self.dataset['id'],
            start=600,end=1200,hypothesis='Price rises by one per minute',falsification='A declining close',**changes))

    def params(self):
        return dict(selections=[dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':2})],
                    dataset_id=self.dataset['id'],profile=self.profile.snapshot(),start=600,end=1200,interval='daily',spot_dataset_id=None)

    def test_window_is_bounded_local_and_exposes_actual_gaps(self):
        with patch.object(self.jobs.datasets,'load',side_effect=AssertionError('No full materialization')),patch('terminal.data.request.urlopen',side_effect=AssertionError('No network')):
            result=self.obs.window(self.dataset['id'],600,900)
        self.assertEqual([r['time'] for r in result['candles']],[600,660,780,840])
        self.assertEqual([r['close'] for r in result['candles']],[111,112,114,115])
        self.assertEqual(result['missing'],[720]);self.assertEqual(result['source']['classification'],'synthetic')
        self.assertEqual(self.jobs.store.recent(),[])
        for start,end in ((601,900),(600,901),(900,600),(-60,900),(0,3660)):
            with self.assertRaises(ValueError):self.obs.window(self.dataset['id'],start,end)

    def test_long_history_pages_never_load_full_table_and_limit_is_preflight(self):
        long=self.jobs.datasets.save('spot','BTCUSDT',0,1200*3600,[Candle(i*3600,100,102,99,101+i%2,10) for i in range(1200)],[],{},metadata={'synthetic':True},provenance=[],source='Synthetic long observation',minutes=60)
        import pyarrow.parquet as pq
        original=pq.ParquetFile.iter_batches
        batches=[]
        def checked(reader,*args,**kwargs):
            self.assertEqual(kwargs['batch_size'],256)
            for batch in original(reader,*args,**kwargs):
                batches.append(batch.num_rows);yield batch
        with patch('pyarrow.parquet.ParquetFile.iter_batches',checked),patch('pyarrow.parquet.read_table',side_effect=AssertionError('No read_table')):
            result=self.obs.window(long['id'],1000*3600,1200*3600)
        self.assertEqual(len(result['candles']),200);self.assertEqual(result['candles'][0]['time'],3600000)
        self.assertLessEqual(max(batches),256)
        with patch('pyarrow.parquet.ParquetFile',side_effect=AssertionError('Limit before file scan')):
            with self.assertRaisesRegex(ValueError,'500'):self.obs.window(long['id'],0,501*3600)

    def test_corruption_missing_and_wrong_source_never_substitute(self):
        record=self.save();file=self.jobs.datasets.root/self.dataset['id']/'trade.parquet'
        raw=file.read_bytes();file.write_bytes(raw[:10]+bytes([raw[10]^1])+raw[11:])
        with self.assertRaisesRegex(ValueError,'checksum'):self.obs.window(self.dataset['id'],600,900)
        with self.assertRaisesRegex(ValueError,'checksum'):self.save()
        file.unlink();self.assertIn('unavailable',self.obs.get(record['id'])['source_error'])
        self.assertEqual(self.jobs.store.recent(),[])

    def test_revision_guard_keeps_original_and_never_records_view_evidence(self):
        original=self.save()
        updated=self.obs.save(original['id'],1,self.dataset['id'],600,1200,'Different claim','Different falsifier')
        self.assertEqual(updated['revision'],2);self.assertEqual(self.obs.get(original['id'],1)['hypothesis'],'Price rises by one per minute')
        with self.assertRaisesRegex(ValueError,'changed'):self.obs.save(original['id'],1,self.dataset['id'],600,1200,'Stale','Stale')
        with self.assertRaisesRegex(ValueError,'fixed'):self.obs.save(original['id'],2,self.dataset['id'],660,1200,'Different range','No')
        with self.jobs.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM research_evidence WHERE kind!='coverage'").fetchone()[0],0)
            with self.assertRaises(sqlite3.Error):db.execute("UPDATE observation_revisions SET hypothesis='mutated'")
        reopened=Observations(self.jobs.store,self.jobs.datasets).get(original['id'])
        self.assertEqual(reopened['hypothesis'],'Different claim');self.assertEqual(self.obs.history()['rows'][0]['revision'],2)

    def test_failed_link_or_batch_insert_rolls_back_and_never_starts_thread(self):
        record=self.save();params=self.params();contract=self.library.preview(**params)['contract_sha256']
        with self.jobs.store.connect() as db:db.execute("CREATE TRIGGER fail_batch BEFORE INSERT ON library_batches BEGIN SELECT RAISE(ABORT,'Injected batch write failure'); END")
        with patch('threading.Thread.start') as launch:
            with self.assertRaises(sqlite3.Error):self.library.start(expected_contract=contract,observation={'id':record['id'],'revision':1},**params)
        launch.assert_not_called();self.assertIsNone(self.jobs.reservation);self.assertIsNone(self.library.active)
        self.assertIsNotNone(self.jobs.storage_diagnostic())
        with self.jobs.store.connect() as db:
            for table in ('observation_batches','library_batches','library_rows','runs'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)

    def test_exact_link_admission_and_revisions_do_not_change_immutable_snapshot(self):
        record=self.save();params=self.params();contract=self.library.preview(**params)['contract_sha256']
        with patch('threading.Thread.start') as launch:
            batch=self.library.start(expected_contract=contract,observation={'id':record['id'],'revision':1},**params)['batch_id']
        launch.assert_called_once()
        # No actual worker was created in this transaction-focused test.
        self.library.active=None;self.jobs.reservation=None
        with self.jobs.store.connect() as db:before=db.execute('SELECT snapshot FROM library_batches WHERE id=?',(batch,)).fetchone()[0]
        self.obs.save(record['id'],1,self.dataset['id'],600,1200,'Edited after admission','New falsifier')
        reopened=self.obs.get(record['id'])
        self.assertEqual(reopened['links'],[dict(batch_id=batch,revision=1,status='preparing')])
        self.assertEqual(self.library.get(batch)['observation'],dict(id=record['id'],revision=1))
        with self.jobs.store.connect() as db:after=db.execute('SELECT snapshot FROM library_batches WHERE id=?',(batch,)).fetchone()[0]
        self.assertEqual(before,after);self.assertNotIn('observation',json.loads(after))

    def test_range_mismatch_rejects_link_without_launch_or_quarantine(self):
        record=self.save();params={**self.params(),'start':660};contract=self.library.preview(**params)['contract_sha256']
        with patch('threading.Thread.start') as launch:
            with self.assertRaisesRegex(ValueError,'differ'):self.library.start(expected_contract=contract,observation={'id':record['id'],'revision':1},**params)
        launch.assert_not_called();self.assertIsNone(self.jobs.reservation);self.assertIsNone(self.jobs.storage_diagnostic())
        self.assertEqual(self.obs.get(record['id'])['links'],[])

    def test_note_write_failure_preserves_draft_target_revision(self):
        record=self.save()
        with self.jobs.store.connect() as db:db.execute("CREATE TRIGGER fail_note BEFORE INSERT ON observation_revisions BEGIN SELECT RAISE(ABORT,'Injected note failure'); END")
        with self.assertRaises(sqlite3.Error):self.obs.save(record['id'],1,self.dataset['id'],600,1200,'Unsaved','Unsaved')
        self.assertEqual(self.obs.get(record['id'])['revision'],1)

    def test_replaced_physical_source_identity_cannot_link_old_note(self):
        record=self.save();params=self.params();contract=self.library.preview(**params)['contract_sha256']
        path=self.jobs.datasets.root/self.dataset['id']/'manifest.json'
        manifest=json.loads(path.read_text());manifest['files_sha256']['trade']='a'*64
        path.write_text(json.dumps(manifest))
        with patch('threading.Thread.start') as launch:
            with self.assertRaisesRegex(ValueError,'identity changed'):
                self.library.start(expected_contract=contract,observation={'id':record['id'],'revision':1},**params)
        launch.assert_not_called();self.assertIsNone(self.jobs.reservation)
        self.assertIn('unavailable',self.obs.get(record['id'])['source_error'])

    def test_optional_falsification_limits_and_history_keyset(self):
        record=self.obs.save(None,0,self.dataset['id'],600,1200,'Required hypothesis','')
        self.assertEqual(record['falsification'],'')
        from terminal.observations import SOURCE_LIMIT
        with patch('terminal.observations.MAX_FILE_BYTES',1):
            with self.assertRaisesRegex(ValueError,'inspection limits'):self.obs.window(self.dataset['id'],600,1200)
        with patch('terminal.observations.MAX_ROWS',1):
            with self.assertRaisesRegex(ValueError,'inspection limits'):self.obs.window(self.dataset['id'],600,1200)
        # Independent 51-way same-timestamp tie verifies bounded stable paging.
        with self.jobs.store.connect() as db:
            db.execute('DELETE FROM observations')
            source=json.dumps(record['source'])
            for i in range(51):
                ident=f'{i:032x}'
                db.execute('INSERT INTO observations VALUES(?,?,1)',(ident,'2024-01-01T00:00:00+00:00'))
                db.execute('INSERT INTO observation_revisions VALUES(?,1,?,?,?,?,?,?)',
                    (ident,'2024-01-01T00:00:00+00:00',source,600,1200,'Hypothesis '+str(i),''))
        first=self.obs.history();second=self.obs.history(first['next'])
        self.assertEqual(len(first['rows']),50);self.assertEqual(len(second['rows']),1)
        self.assertEqual(first['rows'][0]['id'],f'{50:032x}');self.assertEqual(second['rows'][0]['id'],f'{0:032x}')
        self.assertIsNone(second['next'])

    def test_new_only_authentic_fixture_has_independent_chart_expectations(self):
        from scripts.prepare_observation_fixture import create_fixture
        destination=Path(self.temp.name)/'new-observation-fixture'
        fixture=create_fixture(destination)
        with self.assertRaises(FileExistsError):create_fixture(destination)
        from terminal.service import AppService
        service=AppService(destination)
        try:
            initial=service.observations.get(fixture['observation_id'])
            self.assertEqual(initial['revision'],1);self.assertEqual(service.store.recent(),[])
            page=service.observations.window(fixture['dataset_id'],fixture['start'],fixture['end'])
            self.assertEqual(len(page['candles']),24)
            self.assertEqual([page['candles'][0]['close'],page['candles'][-1]['close']],[100.5,123.5])
            gap=service.observations.window(fixture['gapped_dataset_id'],1704067200,1704067200+500*3600)
            self.assertEqual(len(gap['candles']),499);self.assertEqual(gap['missing'],[1704153600])
        finally:service.close()
