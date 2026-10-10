"""Shutdown attempts every owned cleanup without hiding journal failure."""
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock,patch

from terminal.graph import example_graph
from terminal.jobs import JobManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


def failures(error):
    if isinstance(error,ExceptionGroup):
        return [nested for item in error.exceptions for nested in failures(item)]
    return [error]


class ShutdownResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)

    def test_live_pause_write_failure_still_stops_background_owners_and_unlocks(self):
        service=AppService(self.tmp.name)
        service.live.session_id='a'*32
        original=sqlite3.OperationalError('injected read-only journal')
        with patch.object(service.store,'connect',side_effect=original), \
             patch.object(service.library_batches,'close',wraps=service.library_batches.close) as batches, \
             patch.object(service.experiments,'close',wraps=service.experiments.close) as experiments, \
             patch.object(service.downloads,'close',wraps=service.downloads.close) as downloads:
            with self.assertRaises(ExceptionGroup) as caught:service.close()
        self.assertIn(original,failures(caught.exception))
        batches.assert_called_once();experiments.assert_called_once();downloads.assert_called_once()
        self.assertTrue(service.live.stop.is_set())
        self.assertTrue(service.live.delivery_stop.is_set())
        self.assertFalse(service.live.delivery_thread.is_alive())
        self.assertFalse(service.live.chart_history.thread.is_alive())
        self.assertTrue(service.jobs.instance_file.closed)
        reopened=JobManager(self.tmp.name);reopened.close()

    def test_storage_failure_during_active_run_shutdown_still_terminates_before_unlock(self):
        service=AppService(self.tmp.name)
        bars=[Candle(i*60,100,101,99,100,100) for i in range(120)]
        dataset=service.datasets.save('spot','BTCUSDT',0,7200,bars,[],{},metadata={},provenance=[])
        service.jobs.start(example_graph(),Profile(primary_minutes=1),dataset['id'])
        active=service.jobs.active
        original=sqlite3.OperationalError('injected full disk')
        with patch.object(service.store,'connect',side_effect=original):
            with self.assertRaises(ExceptionGroup) as caught:service.close()
        self.assertIn(original,failures(caught.exception))
        self.assertIsNotNone(active['process'].poll())
        self.assertFalse(active['monitor'].is_alive())
        self.assertIsNone(service.jobs.active)
        self.assertTrue(service.jobs.instance_file.closed)
        self.assertEqual(service.jobs.storage_diagnostic()['kind'],'run')
        reopened=JobManager(self.tmp.name);reopened.close()

    def test_all_cleanups_attempted_but_lock_retained_for_live_warmup(self):
        jobs=JobManager(self.tmp.name);self.addCleanup(jobs.close)
        service=object.__new__(AppService);service.jobs=jobs
        original=sqlite3.OperationalError('injected journal failure')
        warmup=Mock();warmup.is_alive.return_value=True
        live=Mock(thread=None,warmup_thread=warmup,hub=Mock(thread=None),
                  chart_history=Mock(thread=None),delivery_thread=None)
        live.close.side_effect=original
        service.live=live
        service.library_batches=Mock(active=None)
        service.experiments=Mock(active=None)
        service.downloads=Mock(thread=None)
        with self.assertRaises(ExceptionGroup) as caught:service.close()
        self.assertIn(original,failures(caught.exception))
        self.assertTrue(any('ownership is retained' in str(error) for error in failures(caught.exception)))
        for owner in (live,service.library_batches,service.experiments,service.downloads):owner.close.assert_called_once()
        self.assertFalse(jobs.instance_file.closed)
        with self.assertRaisesRegex(ValueError,'Another application instance'):JobManager(self.tmp.name)
        # This is an explicit second close after the owner has actually exited.
        warmup.is_alive.return_value=False
        with self.assertRaises(ExceptionGroup):service.close()
        self.assertTrue(jobs.instance_file.closed)

    def test_replay_cancel_terminates_even_when_status_write_fails(self):
        jobs=JobManager(self.tmp.name);self.addCleanup(jobs.close)
        job=Mock();jobs.active={'id':'a'*32,'kind':'replay','cancelled':False,'job':job}
        original=sqlite3.OperationalError('injected locked database')
        try:
            with patch.object(jobs.store,'connect',side_effect=original):
                with self.assertRaises(sqlite3.OperationalError) as caught:jobs.cancel_replay('a'*32)
            self.assertIs(caught.exception,original)
            job.terminate.assert_called_once()
            self.assertTrue(jobs.active['cancelled'])
        finally:jobs.active=None


if __name__=='__main__':unittest.main()
