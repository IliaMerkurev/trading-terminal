"""Prepare pinned project dependencies; never install or alter system packages."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from verify_runtime import runtime_lock


def main():
    root = Path(__file__).resolve().parents[1]
    if runtime_lock() != 'runtime-linux-py312.lock':
        raise SystemExit('Use setup.ps1 on Windows')
    env = os.environ.copy()
    tools = {}
    for name, expected in (('node', 'v24.19.0'), ('pnpm', '11.19.0'), ('cargo', 'cargo 1.98.1')):
        tool = shutil.which(name)
        if not tool:
            raise SystemExit(f'{name} must be installed and available in PATH; see docs/DEVELOPMENT.md')
        actual = subprocess.check_output([tool, '--version'], text=True).strip()
        if actual != expected and not (name == 'cargo' and actual.startswith(expected + ' ')):
            raise SystemExit(f'Expected {name} {expected}; found {actual}. Existing tools were not changed.')
        tools[name] = tool
    pkg_config = shutil.which('pkg-config')
    if not pkg_config:
        raise SystemExit('pkg-config and the Tauri Linux system prerequisites must be installed first')
    subprocess.run([pkg_config, '--exists', 'gtk+-3.0', 'webkit2gtk-4.1'], check=True)
    python = root / '.venv/bin/python'
    if not (root / '.venv').exists():
        subprocess.run([sys.executable, '-m', 'venv', str(root / '.venv')], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:',
                        '--index-url', 'https://pypi.org/simple', '--cache-dir', str(root / '.local-tools/pip-cache'),
                        '--requirement', str(root / 'requirements/runtime-linux-py312.lock'),
                        '--disable-pip-version-check'], check=True)
    subprocess.run([str(python), 'scripts/verify_runtime.py'], cwd=root, check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], cwd=root, check=True)
    subprocess.run([tools['pnpm'], 'install', '--frozen-lockfile', '--ignore-scripts',
                    '--store-dir', '.local-tools/pnpm-store'], cwd=root, check=True)
    env.setdefault('CARGO_HOME', str(root / '.local-tools/cargo-home'))
    subprocess.run([tools['cargo'], 'fetch', '--locked', '--target', 'x86_64-unknown-linux-gnu',
                    '--manifest-path', 'src-tauri/Cargo.toml'], cwd=root, env=env, check=True)
    print('Dependencies prepared. Run .venv/bin/python scripts/desktop.py --build with an isolated --data-root for tests.')


if __name__ == '__main__':
    main()
