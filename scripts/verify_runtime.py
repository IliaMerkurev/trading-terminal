"""Read-only validation of the platform-specific, pinned runtime."""
import importlib.metadata
from pathlib import Path
import platform
import re
import sys


def runtime_lock(system=None, machine=None, python_version=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    python_version = python_version or sys.version_info[:2]
    if tuple(python_version) != (3, 12) or machine not in ('amd64', 'x86_64'):
        raise ValueError('This runtime requires x64 and CPython 3.12')
    if system not in ('Windows', 'Linux'):
        raise ValueError('This runtime supports Windows x64 or Linux x86_64 only')
    if system == 'Linux':
        name, version = platform.libc_ver()
        if name != 'glibc' or tuple(int(p) for p in version.split('.')[:2]) < (2, 35):
            raise ValueError('The pinned Linux wheels require glibc 2.35 or later')
    return f'runtime-{system.lower()}-py312.lock'


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        lock = runtime_lock()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    problems = []
    for line in (root / 'requirements' / lock).read_text().splitlines():
        match = re.match(r'([A-Za-z0-9_-]+)==([^ ]+)', line)
        if not match:
            continue
        package, expected = match.groups()
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = 'missing'
        if actual != expected:
            problems.append(f'{package}: expected {expected}, found {actual}')
    if problems:
        raise SystemExit('\n'.join(problems) + '\nExisting packages were not changed. Review the environment before reinstalling.')
    print(f'{platform.system()} runtime verified: Python {platform.python_version()}, NautilusTrader {importlib.metadata.version("nautilus_trader")}')


if __name__ == '__main__':
    main()
