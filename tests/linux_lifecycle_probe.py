"""Independently authored, stdlib-only fixtures for Linux lifecycle tests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

# Executed by filename in a child with only this tests directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    mode, root_text, behavior = sys.argv[1:]
    root = Path(root_text)
    if mode == 'descendant':
        (root / 'descendant.pid').write_text(str(os.getpid()))
        while True:
            time.sleep(1)
    if mode == 'worker':
        json.loads(sys.stdin.buffer.readline())
        (root / 'worker.pid').write_text(str(os.getpid()))
        subprocess.Popen([sys.executable, __file__, 'descendant', str(root), behavior])
        deadline = time.monotonic() + 5
        while not (root / 'descendant.pid').exists() and time.monotonic() < deadline:
            time.sleep(.01)
        (root / 'ready').write_text('ready')
        if behavior == 'exit':
            return 0
        while True:
            time.sleep(1)
    if mode == 'supervisor':
        from terminal.linux_worker import supervise
        original = subprocess.Popen
        def spawn(command, **kwargs):
            assert command[1:] == ['-m', 'terminal.worker']
            return original([sys.executable, __file__, 'worker', str(root), behavior], **kwargs)
        with patch('terminal.linux_worker.subprocess.Popen', side_effect=spawn):
            return supervise()
    if mode == 'owner':
        from terminal.process_lifecycle import LinuxJob, lock_workspace
        with (root / 'instance.lock').open('a+b') as lock:
            lock_workspace(lock)
            job = LinuxJob(lock)
            process = subprocess.Popen([sys.executable, __file__, 'supervisor', str(root), behavior],
                stdin=subprocess.PIPE, **job.popen_options())
            job.assign(process)
            (root / 'supervisor.pid').write_text(str(process.pid))
            process.stdin.write(b'{"version":1,"command":"run"}\n')
            process.stdin.close()
            while True:
                time.sleep(1)
    raise ValueError('Unknown fixture mode')


if __name__ == '__main__':
    raise SystemExit(main())
