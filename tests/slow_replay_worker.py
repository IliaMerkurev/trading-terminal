"""Synthetic slow worker used only by the bounded Replay lifecycle test."""
import json
from pathlib import Path
import sys
import time

if __name__=='__main__':
    request=json.loads(sys.stdin.buffer.readline(1024*1024+1))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from terminal.live_store import LiveSession
    from terminal.worker import replay
    original=LiveSession.verify_replay
    def slow(self,progress=None):
        if progress:progress(0,1)
        time.sleep(31)
        return original(self,progress)
    LiveSession.verify_replay=slow
    replay(request)
