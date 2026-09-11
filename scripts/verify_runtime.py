"""Read-only validation of the pinned Windows environment."""
import importlib.metadata
from pathlib import Path
import platform
import re
import sys

root=Path(__file__).resolve().parents[1]
if sys.version_info[:2]!=(3,12) or platform.system()!='Windows' or platform.machine().lower() not in ('amd64','x86_64'):
    raise SystemExit('This validated runtime requires Windows x64 and CPython 3.12')
problems=[]
for line in (root/'requirements/runtime-windows-py312.lock').read_text().splitlines():
    match=re.match(r'([A-Za-z0-9_-]+)==([^ ]+)',line)
    if not match:continue
    package,expected=match.groups()
    try:actual=importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:actual='missing'
    if actual!=expected:problems.append(f'{package}: expected {expected}, found {actual}')
if problems:raise SystemExit('\n'.join(problems)+'\nExisting packages were not changed. Review the environment before reinstalling.')
print(f'Windows runtime verified: Python {platform.python_version()}, NautilusTrader {importlib.metadata.version("nautilus_trader")}')
