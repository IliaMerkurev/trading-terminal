"""Run the local browser adapter with this checkout's verified Python runtime."""
from pathlib import Path
import os
import subprocess
import sys

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, 'scripts/verify_runtime.py'], cwd=root, check=True)
    os.chdir(root)
    os.execv(sys.executable, [sys.executable, '-m', 'terminal.browser_host', *sys.argv[1:]])
