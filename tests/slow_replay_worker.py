"""Synthetic slow worker used only by the bounded Replay lifecycle test."""
import json
import os
import subprocess
from pathlib import Path
import sys
import time

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    if sys.platform=='linux' and os.environ.get('_TRADING_TERMINAL_SUPERVISOR')=='1':
        from terminal.linux_worker import supervise
        from unittest.mock import patch
        original=subprocess.Popen
        def spawn(command,**kwargs):
            assert command[1:]==['-m','terminal.worker']
            return original([sys.executable,__file__],**kwargs)
        with patch('terminal.linux_worker.subprocess.Popen',side_effect=spawn):
            raise SystemExit(supervise())
    request=json.loads(sys.stdin.buffer.readline(1024*1024+1))
    from terminal.live_store import LiveSession
    from terminal.worker import replay
    original=LiveSession.verify_replay
    def slow(self,progress=None):
        def delayed(processed,total):
            if progress:progress(processed,total)
            if processed==0:time.sleep(31)  # Hold the actual SQLite read transaction.
        return original(self,delayed)
    LiveSession.verify_replay=slow
    replay(request)
