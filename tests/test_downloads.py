from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from terminal.downloads import DownloadManager


class DownloadTests(unittest.TestCase):
    def test_nonblocking_progress_single_task_and_cancel(self):
        def prepare(client,store,*args):
            progress=args[-1]
            progress('trade',.1)
            client.cancel.wait(5)
            if client.cancel.is_set(): raise ValueError('Download cancelled')
            return {'id':'fixture'}
        with tempfile.TemporaryDirectory() as root,patch('terminal.downloads.prepare_dataset',prepare):
            manager=DownloadManager(Path(root))
            self.addCleanup(manager.close)
            before=time.monotonic()
            manager.start('spot','BTCUSDT',0,60)
            self.assertLess(time.monotonic()-before,.5)
            with self.assertRaisesRegex(ValueError,'already active'): manager.start('spot','BTCUSDT',0,60)
            manager.cancel();manager.close()
            self.assertEqual(manager.status()['status'],'cancelled')
            self.assertNotIn('dataset_id',manager.status())

    def test_success_and_error_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            manager=DownloadManager(Path(root))
            with patch('terminal.downloads.prepare_dataset',return_value={'id':'valid'}):
                manager.start('spot','BTCUSDT',0,60);manager.thread.join(2)
                self.assertEqual(manager.status()['status'],'completed')
                self.assertEqual(manager.status()['dataset_id'],'valid')
            with patch('terminal.downloads.prepare_dataset',side_effect=ValueError('Coverage unavailable')):
                manager.start('spot','BTCUSDT',0,60);manager.thread.join(2)
                self.assertEqual(manager.status()['status'],'failed')
                self.assertNotIn('dataset_id',manager.status())
