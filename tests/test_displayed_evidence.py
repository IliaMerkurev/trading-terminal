"""Synthetic displayed-period contracts, independent of strategy profitability."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from terminal import research_evidence as evidence
from terminal.displayed_evidence import record,candle_ranges,chart_page
from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.observations import Observations
from terminal.profile import Profile
from terminal.series import Candle
from terminal.storage import RunStore


class DisplayedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        jobs=JobManager(self.tmp.name);self.addCleanup(jobs.close)
        batches=LibraryBatchManager(jobs);self.addCleanup(batches.close)
        self.service=SimpleNamespace(jobs=jobs,store=jobs.store,datasets=jobs.datasets,library_batches=batches,observations=Observations(jobs.store,jobs.datasets))
        self.dataset=jobs.datasets.save('spot','BTCUSDT',0,3600,[Candle(i*60,100+i,102+i,99+i,101+i,10) for i in range(60) if i!=12],[],{},metadata={'synthetic':True},provenance=[],source='Synthetic display evidence')
        self.presentation='a'*32
        self.reference=dict(surface='observation_chart',dataset_id=self.dataset['id'],start=600,end=900)

    def view(self,viewport,**kwargs):
        ref=kwargs.get('reference',self.reference)
        if ref['surface']=='observation_chart' and set(ref)=={'surface','dataset_id','start','end'}:
            page=self.service.observations.window(ref['dataset_id'],ref['start'],ref['end'])
            ref=chart_page(self.service,'observation_chart',page,ref['dataset_id'])['display_reference']
        elif ref['surface']=='run_chart' and 'run_id' in ref:
            page=self.service.store.chart_window(ref['run_id'],ref['start'],ref['minutes'])
            ref=chart_page(self.service,'run_chart',page,ref['run_id'])['display_reference']
        return record(self.service,kwargs.get('presentation',self.presentation),ref,viewport)
    def rows(self):
        with self.service.store.connect() as db:return [dict(r) for r in db.execute("SELECT * FROM research_evidence WHERE kind='viewed'")]

    def test_view_without_test_separates_gaps_pan_and_dedup(self):
        self.service.observations.window(self.dataset['id'],600,900)
        note=self.service.observations.save(None,0,self.dataset['id'],600,900,'Synthetic claim','')
        self.assertEqual(self.rows(),[])
        self.assertEqual(self.view([600,840])['recorded'],2)
        self.assertEqual([(r['evaluation_start'],r['evaluation_end']) for r in self.rows()],[(600,720),(780,900)])
        self.assertEqual(self.view([600,840])['recorded'],0)
        self.assertEqual(self.view([661,779])['recorded'],0)
        self.assertEqual(self.view([660,660])['recorded'],1)
        preview=evidence.preview(self.service.jobs,self.dataset['id'],600,900)
        self.assertEqual(preview['counts'],{'viewed':3});self.assertEqual(self.service.store.recent(),[])
        self.assertEqual(evidence.preview(self.service.jobs,self.dataset['id'],720,780)['total'],0)
        self.assertTrue(all(r['role']=='observation_chart' for r in self.rows()))
        self.service.observations.save(note['id'],1,self.dataset['id'],600,900,'Changed note','')
        self.assertEqual(len(self.rows()),3)
        old=self.rows();coverage=preview['coverage_start'];view_coverage=preview['view_coverage_start']
        reopened=RunStore(self.tmp.name)
        with reopened.connect() as db:
            summary=evidence.overlaps(db,self.dataset,600,900)
            self.assertEqual(summary['coverage_start'],coverage);self.assertEqual(summary['view_coverage_start'],view_coverage)
            self.assertEqual([dict(r) for r in db.execute("SELECT * FROM research_evidence WHERE kind='viewed'")],old)
            with self.assertRaises(sqlite3.Error):db.execute("DELETE FROM research_evidence WHERE kind='viewed'")
            real={**self.dataset,'source':'Bybit public API','metadata':{},'provenance':[]}
            self.assertEqual(evidence.overlaps(db,real,600,900)['total'],0)
            self.assertEqual(evidence.overlaps(db,{**self.dataset,'source':'Other synthetic fixture'},600,900)['total'],0)

    def test_open_close_labels_and_whitespace_have_independent_expected_ranges(self):
        candles=[{'time':600},{'time':660},{'time':780}]
        self.assertEqual(candle_ranges(candles,60,[660,780]),[[660,720],[780,840]])
        self.assertEqual(candle_ranges(candles,60,[660,780],closes=True),[[600,720]])
        self.assertEqual(candle_ranges(candles,60,[721,839],closes=True),[])
        self.assertEqual(candle_ranges(candles,60,[-900,0]),[])
        for invalid in ([float('nan'),1],[3,1],[True,4],[],None):
            with self.assertRaises(ValueError):candle_ranges(candles,60,invalid)

    def test_write_failure_keeps_reader_and_durable_incomplete_review(self):
        with self.service.store.connect() as db:db.execute("CREATE TRIGGER reject_view BEFORE INSERT ON research_evidence WHEN NEW.kind='viewed' BEGIN SELECT RAISE(ABORT,'Injected display failure'); END")
        with self.assertRaises(sqlite3.Error):self.view([600,840])
        self.assertEqual(self.rows(),[])
        self.assertEqual(len(self.service.observations.window(self.dataset['id'],600,900)['candles']),4)
        with RunStore(self.tmp.name).connect() as db:self.assertIn('incomplete',evidence.overlaps(db,self.dataset,600,900)['display_warning'])
        self.assertIsNone(self.service.jobs.storage_diagnostic())

    def test_reference_source_injection_and_unbounded_pages_are_rejected(self):
        with self.assertRaises(ValueError):self.view([600,840],reference={**self.reference,'source':'real'})
        with self.assertRaises(ValueError):self.view([600,840],reference={**self.reference,'end':999999})
        with self.assertRaises(ValueError):self.view([600,840],presentation='invalid')
        self.assertEqual(self.rows(),[])

    def test_authentic_report_comparison_and_frozen_review_preserve_bytes(self):
        params=dict(selections=[dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':2})],dataset_id=self.dataset['id'],profile=Profile(primary_minutes=1,capital='180',allocation='100',gap_policy='skip').snapshot(),start=600,end=1200,interval='daily',spot_dataset_id=None)
        batches=self.service.library_batches
        batch=batches.start(expected_contract=batches.preview(**params)['contract_sha256'],**params)['batch_id']
        thread=batches.active['thread'];thread.join(40);self.assertFalse(thread.is_alive())
        report=batches.get(batch);run_id=report['rows'][0]['run_id']
        self.assertEqual(report['rows'][0]['status'],'completed')
        before={p:p.read_bytes() for p in Path(self.tmp.name).glob('runs/*/*.json')}
        self.view(None,reference=dict(surface='comparison_metrics',batch_id=batch,ordinal=0))
        self.view(None,reference=dict(surface='run_metrics',run_id=run_id))
        self.view([660,780],reference=dict(surface='run_chart',run_id=run_id,start=600,minutes=30))
        self.assertEqual([(r['role'],r['evaluation_start'],r['evaluation_end']) for r in self.rows()], [('comparison_metrics',600,1200),('run_metrics',600,1200),('run_chart',600,720)])
        # Observation-only later-period display adds zero attempts to its freeze review.
        self.view([1800,1920],reference={**self.reference,'start':1800,'end':2100})
        frozen=batches.freeze_validation(batch,0,self.dataset['id'],1800,2400,None)['batch_id']
        saved=batches.get(frozen)['research_evidence']
        self.assertEqual(saved['counts'],{'viewed':1})
        self.view([1980,2040],reference={**self.reference,'start':1800,'end':2100})
        self.assertEqual(batches.get(frozen)['research_evidence'],saved)
        self.assertEqual({p:p.read_bytes() for p in before},before)
        with self.service.store.connect() as db:
            started=db.execute("SELECT count(*) FROM research_evidence WHERE kind='started'").fetchone()[0]
        self.assertEqual(started,3)
        self.view(None,reference=dict(surface='comparison_metrics',batch_id=batch,ordinal=1))
        passive=json.loads(self.rows()[-1]['details']);self.assertEqual(passive['original_role'],'passive')
        # A local snapshot without an original admission remains explicitly incomplete.
        with patch('terminal.displayed_evidence._run',return_value=None):
            result=self.view(None,reference=dict(surface='run_metrics',run_id=run_id))
        self.assertTrue(result['incomplete']);self.assertEqual(len(self.rows()),6)

    def test_server_page_reference_preserves_rendered_source_and_bounds_cache(self):
        page=self.service.observations.window(self.dataset['id'],600,900)
        issued=chart_page(self.service,'observation_chart',page,self.dataset['id'])['display_reference']
        self.assertEqual(self.rows(),[])
        with patch.object(self.service.datasets,'describe',side_effect=AssertionError('No re-read while panning')):
            record(self.service,self.presentation,issued,[600,660])
        self.assertEqual(self.rows()[0]['source'],'Synthetic display evidence')
        self.assertEqual(record(self.service,self.presentation,issued,[600,660])['recorded'],0)
        for i in range(33):
            chart_page(self.service,'observation_chart',self.service.observations.window(self.dataset['id'],i*60,(i+1)*60),self.dataset['id'])
        self.assertEqual(len(self.service.display_pages),32)
        with self.assertRaisesRegex(ValueError,'expired'):record(self.service,self.presentation,issued,[600,660])
        self.assertEqual(len(self.rows()),1)

    def test_ipc_fetch_has_zero_views_and_frontend_caveat_must_persist(self):
        from terminal.service import AppService
        def request(command,params):
            return AppService.handle(self.service,dict(version=1,id='synthetic-request',command=command,params=params))
        page=request('local_history_window',{k:self.reference[k] for k in ('dataset_id','start','end')})
        self.assertEqual(page['type'],'result');self.assertEqual(self.rows(),[])
        result=request('research_displayed',dict(presentation_id=self.presentation,reference=page['result']['display_reference'],viewport=[600,840]))
        self.assertEqual(result['type'],'result');self.assertEqual(result['result']['recorded'],2)
        with self.service.store.connect() as db:
            db.execute("CREATE TRIGGER fail_caveat BEFORE INSERT ON research_evidence WHEN NEW.role='display-incomplete' BEGIN SELECT RAISE(ABORT,'Injected caveat failure'); END")
        result=request('research_display_incomplete',{})
        self.assertEqual(result['type'],'error')
        self.assertIsNotNone(self.service.store.display_warning)
        with self.service.store.connect() as db:db.execute('DROP TRIGGER fail_caveat')
        result=request('research_display_incomplete',{});self.assertEqual(result['type'],'result')
        preview=request('research_evidence_preview',dict(dataset_id=self.dataset['id'],start=1800,end=2400))['result']
        self.assertEqual(preview['total'],0);self.assertIn('incomplete',preview['display_warning'])
        self.assertEqual(len(self.rows()),2)
