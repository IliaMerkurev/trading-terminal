import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from terminal.graph import example_graph
from terminal.live_store import LiveSession
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class ReplayJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=AppService(self.temp.name);self.addCleanup(self.service.close)
        self.sid=self.service.live.journal.create(example_graph(),Profile(primary_minutes=1),'fixture','Replay fixture')
        session=LiveSession(self.service.live.journal,self.sid)
        for i,p in enumerate([100,110,120,90,100]):
            session.ingest(Candle(i*60,p,p,p,p,1),(i+1)*60000,'warmup' if i==0 else 'recovered')
        self.expected={'match':True,'checked_events':3}

    def call(self,command,**params):
        response=self.service.handle({'version':1,'id':'fixture','command':command,'params':params})
        self.assertEqual(response['type'],'result',response)
        return response['result']

    def wait(self,replay_id,timeout=15,progress=False):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=self.call('replay_status',replay_id=replay_id)
            if progress and value['progress'] or value['status'] not in ('running','cancel_requested'):return value
            time.sleep(.05)
        self.fail('Replay did not reach the bounded checkpoint')

    def slow_worker(self):
        original=subprocess.Popen
        def spawn(args,**kwargs):
            if args[1:]==['-m','terminal.worker']:
                args=[args[0],str(Path(__file__).with_name('slow_replay_worker.py'))]
            return original(args,**kwargs)
        return patch('terminal.jobs.subprocess.Popen',side_effect=spawn)

    def test_slow_replay_exceeds_old_timeout_while_ipc_remains_responsive(self):
        with self.slow_worker():
            begin=time.monotonic();job=self.call('live_replay',session_id=self.sid)['replay_id']
            self.assertLess(time.monotonic()-begin,2)
        self.wait(job,progress=True)
        while time.monotonic()-begin<30.2:
            start=time.monotonic();self.call('list_runs');self.call('live_status')
            self.assertLess(time.monotonic()-start,2)
            time.sleep(.2)
        self.assertEqual(self.call('replay_status',replay_id=job)['status'],'running')
        result=self.wait(job)
        self.assertEqual(result['status'],'completed');self.assertEqual(result['result'],self.expected)
        self.assertEqual(result['progress']['processed'],5)
        self.assertEqual(self.service.live.journal.get(self.sid)['status'],'PAUSED')

    def test_cancel_never_publishes_success_and_releases_shared_worker_slot(self):
        with self.slow_worker():job=self.call('live_replay',session_id=self.sid)['replay_id']
        self.assertEqual(self.wait(job,progress=True)['status'],'running')
        with self.assertRaisesRegex(ValueError,'already active'):self.service.jobs.start_replay(self.sid)
        self.call('replay_cancel',replay_id=job)
        result=self.wait(job);self.assertEqual(result['status'],'cancelled');self.assertIsNone(result['result'])
        self.assertFalse((Path(self.temp.name)/'replays'/job/'worker-result.json').exists())
        again=self.call('live_replay',session_id=self.sid)['replay_id']
        self.assertEqual(self.wait(again)['result'],self.expected)
        with self.service.store.connect() as db:
            self.assertEqual(db.execute('SELECT result FROM replay_jobs WHERE id=?',(job,)).fetchone()[0],None)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_worker_error_and_mismatch_are_distinct_and_shutdown_cancels(self):
        with self.service.store.connect() as db:db.execute('DELETE FROM live_signals WHERE session_id=?',(self.sid,))
        mismatch=self.wait(self.call('live_replay',session_id=self.sid)['replay_id'])
        self.assertEqual(mismatch['status'],'completed');self.assertFalse(mismatch['result']['match'])
        with self.service.store.connect() as db:
            snapshot=self.service.live.journal.get(self.sid)['snapshot'];snapshot['graph']={}
            db.execute('UPDATE live_sessions SET snapshot=? WHERE id=?',(json.dumps(snapshot),self.sid))
        failure=self.wait(self.call('live_replay',session_id=self.sid)['replay_id'])
        self.assertEqual(failure['status'],'failed');self.assertTrue(failure['error']);self.assertIsNone(failure['result'])
        with self.service.store.connect() as db:
            snapshot['graph']=example_graph()
            db.execute('UPDATE live_sessions SET snapshot=? WHERE id=?',(json.dumps(snapshot),self.sid))
        with self.slow_worker():job=self.call('live_replay',session_id=self.sid)['replay_id']
        self.wait(job,progress=True);self.service.jobs.close()
        self.assertEqual(self.call('replay_status',replay_id=job)['status'],'cancelled')
