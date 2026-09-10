import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest

from terminal.windows_job import WindowsJob


@unittest.skipUnless(os.name == "nt", "Windows lifecycle acceptance check")
class WindowsWorkerTests(unittest.TestCase):
    def test_cancel_stops_engine_worker_and_its_child(self):
        project = Path(__file__).resolve().parents[1]
        with WindowsJob() as job:
            process = subprocess.Popen([sys.executable, str(project / "tests/worker_probe.py")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, cwd=project, creationflags=subprocess.CREATE_NO_WINDOW)
            child_handle = None
            try:
                job.assign(process)
                process.stdin.write("GO\n")
                process.stdin.flush()
                lines = queue.Queue()
                reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
                reader.start()
                child_pid = int(lines.get(timeout=20).strip())
                child_handle = job.api.OpenProcess(0x00100000, False, child_pid)
                self.assertTrue(child_handle, "Child process must exist before cancellation")
                self.assertEqual(job.api.WaitForSingleObject(child_handle, 0), 258)
                job.terminate()
                self.assertEqual(process.wait(timeout=5), 130)
                self.assertEqual(job.api.WaitForSingleObject(child_handle, 5000), 0,
                                 "Cancelling the worker must also terminate its child")
                reader.join(timeout=1)
            finally:
                job.terminate()
                process.wait(timeout=5)
                process.stdin.close()
                process.stdout.close()
                if child_handle:
                    job.api.CloseHandle(child_handle)
