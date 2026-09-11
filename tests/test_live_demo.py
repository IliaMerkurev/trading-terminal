import tempfile
import unittest
from pathlib import Path
from terminal.demo_live import prepare


class LiveDemoTests(unittest.TestCase):
    def test_independent_demo_goldens_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            result=prepare(Path(directory))
            self.assertEqual(result[0]['paper_equity'],'1009.79')
            self.assertEqual([r['replay']['checked_events'] for r in result],[2,2,1])
            self.assertEqual(prepare(Path(directory)),result)
