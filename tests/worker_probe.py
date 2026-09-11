"""Vetted synthetic cancellation fixture; only executes when run as a script."""
import sys

if __name__ == "__main__":
    if sys.stdin.readline().strip() != "GO":
        raise SystemExit(2)
    import subprocess
    from test_engine_probe import run_round_trip
    run_round_trip()  # Confirm the actual engine loaded and executed in this worker.
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
    print(child.pid, flush=True)
    while True:
        run_round_trip()
