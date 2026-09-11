import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from terminal.paths import data_root
from terminal.jobs import JobManager


class BridgeTests(unittest.TestCase):
    def invoke(self,root,requests=()):
        payload=b''.join(json.dumps({'version':1,'id':str(i),'command':command,'params':params}).encode()+b'\n' for i,(command,params) in enumerate(requests))
        result=subprocess.run([sys.executable,'-m','terminal.bridge','--data-root',str(root)],input=payload,capture_output=True,timeout=15,cwd=Path(__file__).resolve().parents[1])
        return result.returncode,[json.loads(line) for line in result.stdout.splitlines()]

    def test_readiness_precedes_responses_and_root_is_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'isolated'
            code,messages=self.invoke(root,[('list_runs',{}),('list_strategies',{})])
            self.assertEqual(code,0)
            self.assertEqual(messages[0],{'version':1,'id':'startup','type':'ready'})
            self.assertEqual([m['id'] for m in messages[1:]],['0','1'])
            self.assertEqual([m['result'] for m in messages[1:]],[[],[]])
            self.assertTrue((root/'terminal.sqlite3').exists())

    def test_second_instance_reports_real_startup_error(self):
        with tempfile.TemporaryDirectory() as directory:
            owner=JobManager(directory)
            try:
                code,messages=self.invoke(directory,[('list_runs',{})])
                self.assertEqual(code,1)
                self.assertEqual(len(messages),1)
                self.assertEqual(messages[0]['error']['code'],'STARTUP_FAILED')
                self.assertIn('Another application instance',messages[0]['error']['message'])
            finally:owner.close()
            self.assertEqual(self.invoke(directory)[0],0)

    def test_relative_data_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'absolute'):data_root('relative')
