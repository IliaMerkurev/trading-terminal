import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from terminal.process_lifecycle import LinuxJob, lock_workspace, unlock_workspace


@unittest.skipUnless(sys.platform == 'linux', 'Linux lifecycle acceptance check')
class LinuxLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.probe = Path(__file__).with_name('linux_lifecycle_probe.py')

    def wait_file(self, name):
        path = self.root / name
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if path.exists() and path.read_text():
                return path.read_text()
            time.sleep(.02)
        self.fail(f'Fixture did not publish {name}')

    def stopped(self, pid):
        path = Path(f'/proc/{pid}/stat')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                state = path.read_text().split(') ', 1)[1].split()[0]
                if state == 'Z':return
            except FileNotFoundError:
                return
            time.sleep(.02)
        self.fail(f'Owned fixture process {pid} survived cleanup')

    def spawn(self, lock, behavior='wait'):
        job = LinuxJob(lock)
        process = subprocess.Popen([sys.executable, str(self.probe), 'supervisor', str(self.root), behavior],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **job.popen_options())
        job.assign(process)
        self.addCleanup(process.stderr.close)
        self.addCleanup(process.stdin.close)
        def cleanup():
            job.close()
            process.wait(timeout=8)
        self.addCleanup(cleanup)
        return job, process

    def test_bootstrap_cancel_before_go_never_starts_worker(self):
        with (self.root / 'instance.lock').open('a+b') as lock:
            lock_workspace(lock)
            job, process = self.spawn(lock)
            job.terminate()
            self.assertEqual(process.wait(timeout=8), 130)
            self.assertFalse((self.root / 'worker.pid').exists())
            unlock_workspace(lock)

    def test_cancel_and_normal_exit_stop_worker_descendants(self):
        for behavior, expected in [('wait', 130), ('exit', 0)]:
            with self.subTest(behavior=behavior):
                for name in ('worker.pid', 'descendant.pid', 'ready'):
                    (self.root / name).unlink(missing_ok=True)
                with (self.root / 'instance.lock').open('a+b') as lock:
                    lock_workspace(lock)
                    job, process = self.spawn(lock, behavior)
                    process.stdin.write(b'{"version":1,"command":"run"}\n')
                    process.stdin.close()
                    self.wait_file('ready')
                    worker = int(self.wait_file('worker.pid'))
                    child = int(self.wait_file('descendant.pid'))
                    if behavior == 'wait':job.terminate()
                    self.assertEqual(process.wait(timeout=8), expected, process.stderr.read().decode())
                    self.stopped(worker)
                    self.stopped(child)
                    unlock_workspace(lock)

    def test_service_crash_retains_lock_until_supervisor_cleans_up(self):
        owner = subprocess.Popen([sys.executable, str(self.probe), 'owner', str(self.root), 'wait'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        supervisor = None
        try:
            self.wait_file('ready')
            supervisor = int(self.wait_file('supervisor.pid'))
            worker = int(self.wait_file('worker.pid'))
            child = int(self.wait_file('descendant.pid'))
            os.kill(supervisor, signal.SIGSTOP)
            owner.kill()
            owner.wait(timeout=5)
            with (self.root / 'instance.lock').open('a+b') as lock:
                with self.assertRaises(BlockingIOError):lock_workspace(lock)
                os.kill(supervisor, signal.SIGCONT)
                self.stopped(worker)
                self.stopped(child)
                self.stopped(supervisor)
                lock_workspace(lock)
                unlock_workspace(lock)
        finally:
            if supervisor is not None:
                try:os.kill(supervisor, signal.SIGCONT)
                except ProcessLookupError:pass
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=5)
