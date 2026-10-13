"""Offline, closed-workspace backup and fresh-destination restore. No app startup."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import sqlite3
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal.process_lifecycle import lock_workspace, unlock_workspace

FORMAT = 'trading-terminal-workspace-v1'
DATABASE = 'terminal.sqlite3'
SIDECARS = (DATABASE, DATABASE + '-wal', DATABASE + '-shm', DATABASE + '-journal')
MAX_ENTRIES = 100_000
MAX_MANIFEST = 32 * 1024 * 1024
CHUNK = 1024 * 1024
EXCLUSIONS = ['instance.lock (transient ownership, recreated on restore)']
LIMITS = [
    'Only the selected data root is included; external browser profiles and credentials are not.',
    'Unsaved memory state, source code, runtimes and files outside the root are not included.',
    'Hashes detect changes, not authenticity. Use only your own trusted local backups.',
    'No migration, application startup, job resume, alert Arm or native execution is performed.',
    'File bytes and empty directories are preserved, not ACLs, ownership or platform metadata.',
]


@contextmanager
def read_regular(path, *, writable=False):
    path = absolute(path)
    before = checked_stat(path)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Expected a regular file')
    flags = (os.O_RDWR if writable else os.O_RDONLY) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'r+b' if writable else 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError('File identity changed before reading')
        yield stream
        after = checked_stat(path)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns):
            raise ValueError('File changed during reading; close all writers')


def digest(path):
    value = hashlib.sha256()
    with read_regular(path) as stream:
        while block := stream.read(CHUNK):
            value.update(block)
    return value.hexdigest()


def safe_path(value):
    """One portable relative path, with no aliases or device/stream names."""
    if not isinstance(value, str) or not value or value == '.' or '\\' in value:
        raise ValueError('Invalid inventory path')
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value:
        raise ValueError('Invalid inventory path')
    for part in path.parts:
        if (part in ('.', '..') or part.endswith((' ', '.')) or
                any(ord(c) < 32 or c in ':<>"|?*' for c in part) or
                re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)):
            raise ValueError('Nonportable inventory path')
    return path


def checked_stat(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Symbolic links and reparse points are not supported')
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError('Only regular files and directories are supported')
    return info


def absolute(path):
    path = Path(os.path.abspath(path))
    for parent in reversed((path, *path.parents)):
        if parent.exists() or parent.is_symlink():
            checked_stat(parent)
    return path


def disjoint(first, second):
    if first == second or first in second.parents or second in first.parents:
        raise ValueError('Source and destination must not overlap')


def fresh(path):
    if path.exists() or path.is_symlink():
        raise ValueError('Destination must not exist; existing data is preserved')
    if not path.parent.is_dir():
        raise ValueError('Destination parent must already exist')


def inventory(root):
    entries = []
    aliases = set()
    def fail(error):
        raise error
    for directory, names, files in os.walk(root, followlinks=False, onerror=fail):
        for name in sorted(names + files):
            path = Path(directory) / name
            info = checked_stat(path)
            relative = path.relative_to(root).as_posix()
            safe_path(relative)
            alias = relative.casefold()
            if alias in aliases:
                raise ValueError('Case-colliding paths are not portable')
            aliases.add(alias)
            if relative == 'instance.lock':
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('Invalid workspace lock')
                continue
            entry = {'path': relative, 'type': 'directory' if stat.S_ISDIR(info.st_mode) else 'file'}
            if entry['type'] == 'file':
                entry.update(size=info.st_size, sha256=digest(path))
                if path.stat().st_size != info.st_size:
                    raise ValueError('Source changed during inventory; close all writers')
            entries.append(entry)
            if len(entries) > MAX_ENTRIES:
                raise ValueError('Workspace inventory exceeds 100,000 entries')
    return sorted(entries, key=lambda item: item['path'])


@contextmanager
def ownership(root, *, create=False):
    path = root / 'instance.lock'
    if create:
        with path.open('xb') as stream:
            stream.write(b'0')
    if not path.exists() or not stat.S_ISREG(checked_stat(path).st_mode) or path.stat().st_size < 1:
        raise ValueError('Existing workspace ownership file is required; never remove a live lock')
    with read_regular(path, writable=True) as stream:
        try:
            lock_workspace(stream)
        except OSError as exc:
            raise ValueError('Workspace is in use; close the application and all workers') from exc
        try:
            yield
        finally:
            unlock_workspace(stream)


def copy_entries(source, destination, entries):
    for entry in entries:
        target = absolute(destination.joinpath(*safe_path(entry['path']).parts))
        if entry['type'] == 'directory':
            target.mkdir()
        else:
            with read_regular(source.joinpath(*safe_path(entry['path']).parts)) as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst, CHUNK)
                dst.flush()
                os.fsync(dst.fileno())


def database_report(root):
    """SQLite may recover/checkpoint only a disposable DB-only copy, never input."""
    if not (root / DATABASE).is_file():
        raise ValueError('Workspace database is missing')
    with tempfile.TemporaryDirectory(prefix='terminal-backup-check-') as directory:
        scratch = Path(directory)
        for name in SIDECARS:
            if (root / name).exists():
                with read_regular(root / name) as src, (scratch / name).open('xb') as dst:
                    shutil.copyfileobj(src, dst, CHUNK)
        # The scratch database is writable solely for SQLite journal recovery.
        db = sqlite3.connect(scratch / DATABASE)
        try:
            db.execute('PRAGMA trusted_schema=OFF')
            db.execute('PRAGMA query_only=ON')
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('SQLite integrity check failed')
            if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
                raise ValueError('SQLite foreign key check failed')
            names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            if not {'runs', 'strategies'}.issubset(names):
                raise ValueError('Database is not a supported Trading Terminal workspace')
            counts = {}
            for name in names:
                quoted = '"' + name.replace('"', '""') + '"'
                counts[name] = db.execute('SELECT count(*) FROM ' + quoted).fetchone()[0]
            completed = 0
            for ident, expected in db.execute("SELECT id,result_hash FROM runs WHERE status='completed' ORDER BY id"):
                if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
                    raise ValueError('Invalid completed run identity')
                path = root / 'runs' / ident / 'result.json'
                if not path.is_file() or digest(path) != expected:
                    raise ValueError('Completed result artifact is missing or has a checksum mismatch')
                completed += 1
            return {'integrity_check': 'ok', 'foreign_key_check': 'ok', 'tables': counts,
                    'completed_results_verified': completed}
        finally:
            db.close()


def write_manifest(path, document):
    raw = (json.dumps(document, sort_keys=True, indent=2) + '\n').encode()
    if len(raw) > MAX_MANIFEST:
        raise ValueError('Manifest exceeds 32 MiB')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def backup(source, destination, *, closed=False):
    if not closed:
        raise ValueError('Confirm the entire application and all writers are closed with --closed')
    source, destination = absolute(source), absolute(destination)
    disjoint(source, destination)
    fresh(destination)
    with ownership(source):
        before = inventory(source)
        destination.mkdir(mode=0o700)
        workspace = destination / 'workspace'
        workspace.mkdir()
        copy_entries(source, workspace, before)
        if inventory(workspace) != before or inventory(source) != before:
            raise ValueError('Workspace changed while copying; partial backup is retained without a manifest')
        report = database_report(workspace)
        document = dict(format=FORMAT, created_at=datetime.now(timezone.utc).isoformat(),
                        source_root=str(source), source_platform=sys.platform,
                        scope='Complete selected data root except transient ownership file',
                        exclusions=EXCLUSIONS, limits=LIMITS, entries=before, database=report)
        write_manifest(destination / 'manifest.json', document)
        return summary(destination, document)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate manifest key')
        result[key] = value
    return result


def validate_entries(entries):
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Invalid inventory entry')
        safe_path(entry.get('path'))
        fields = {'path', 'type'}
        if entry.get('type') == 'file':
            fields |= {'size', 'sha256'}
            if (type(entry.get('size')) is not int or entry['size'] < 0 or
                    not isinstance(entry.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', entry['sha256'])):
                raise ValueError('Invalid inventory file evidence')
        elif entry.get('type') != 'directory':
            raise ValueError('Invalid inventory entry type')
        if set(entry) != fields:
            raise ValueError('Invalid inventory entry fields')


def load_verified(bundle):
    bundle = absolute(bundle)
    if {path.name for path in bundle.iterdir()} != {'manifest.json', 'workspace'}:
        raise ValueError('Backup bundle must contain only manifest.json and workspace')
    workspace = bundle / 'workspace'
    if not stat.S_ISDIR(checked_stat(workspace).st_mode):
        raise ValueError('Backup workspace must be a directory')
    if (workspace / 'instance.lock').exists():
        raise ValueError('Backup was opened as an application workspace; preserve it and use an untouched backup')
    manifest = bundle / 'manifest.json'
    checked_stat(manifest)
    if manifest.stat().st_size > MAX_MANIFEST:
        raise ValueError('Manifest exceeds 32 MiB')
    with read_regular(manifest) as stream:
        raw = stream.read(MAX_MANIFEST + 1)
    if len(raw) > MAX_MANIFEST:
        raise ValueError('Manifest exceeds 32 MiB')
    manifest_hash = hashlib.sha256(raw).hexdigest()
    document = json.loads(raw, object_pairs_hook=unique_keys)
    if (not isinstance(document, dict) or document.get('format') != FORMAT or
            document.get('exclusions') != EXCLUSIONS or document.get('limits') != LIMITS or
            not isinstance(document.get('entries'), list) or len(document['entries']) > MAX_ENTRIES):
        raise ValueError('Unsupported or invalid complete workspace manifest')
    required = {'format', 'created_at', 'source_root', 'source_platform', 'scope',
                'exclusions', 'limits', 'entries', 'database'}
    if (set(document) != required or document['source_platform'] not in ('linux', 'win32') or
            not isinstance(document['source_root'], str) or
            not isinstance(document['scope'], str) or not isinstance(document['created_at'], str)):
        raise ValueError('Invalid manifest safety metadata')
    path_type = PureWindowsPath if document['source_platform'] == 'win32' else PurePosixPath
    if not path_type(document['source_root']).is_absolute() or datetime.fromisoformat(document['created_at']).tzinfo is None:
        raise ValueError('Invalid manifest source identity or timestamp')
    report = document['database']
    if (not isinstance(report, dict) or set(report) != {'integrity_check', 'foreign_key_check', 'tables', 'completed_results_verified'} or
            report['integrity_check'] != 'ok' or report['foreign_key_check'] != 'ok' or
            not isinstance(report['tables'], dict) or
            any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in report['tables'].items()) or
            type(report['completed_results_verified']) is not int or report['completed_results_verified'] < 0):
        raise ValueError('Invalid manifest database evidence')
    validate_entries(document['entries'])
    # Actual traversal is never driven by unchecked manifest paths. An exact
    # inventory comparison also rejects missing, extra, duplicate and alias entries.
    if inventory(workspace) != document['entries']:
        raise ValueError('Backup inventory mismatch; no restore was attempted')
    if database_report(workspace) != document.get('database'):
        raise ValueError('Backup database evidence mismatch')
    if digest(manifest) != manifest_hash:
        raise ValueError('Backup manifest changed during verification')
    return bundle, document, manifest_hash


def summary(bundle, document, manifest_hash=None):
    return {'status': 'verified', 'format': FORMAT, 'manifest_sha256': manifest_hash or digest(bundle / 'manifest.json'),
            'files': sum(item['type'] == 'file' for item in document['entries']),
            'bytes': sum(item.get('size', 0) for item in document['entries']),
            'database': document['database'], 'application_started': False}


def verify(bundle):
    bundle, document, manifest_hash = load_verified(bundle)
    return summary(bundle, document, manifest_hash)


def restore(bundle, destination):
    bundle, destination = absolute(bundle), absolute(destination)
    disjoint(bundle, destination)
    fresh(destination)
    bundle, document, manifest_hash = load_verified(bundle)
    if document.get('source_platform') == sys.platform:
        original = document.get('source_root')
        if not isinstance(original, str) or not Path(original).is_absolute():
            raise ValueError('Invalid original workspace identity')
        disjoint(absolute(original), destination)
    destination.mkdir(mode=0o700)
    with ownership(destination, create=True):
        copy_entries(bundle / 'workspace', destination, document['entries'])
        if inventory(destination) != document['entries']:
            raise ValueError('Restored file mismatch; partial destination is retained')
        if database_report(destination) != document['database']:
            raise ValueError('Restored database evidence mismatch; destination is retained')
        # Recheck the input as well: a changing backup is never a valid restore.
        _, final_document, final_hash = load_verified(bundle)
        if final_document != document or final_hash != manifest_hash:
            raise ValueError('Backup changed during restoration; destination is retained')
        result = summary(bundle, document, manifest_hash)
        result['status'] = 'restored_and_verified'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    save = sub.add_parser('backup', help='Copy a closed data root into a NEW local bundle')
    save.add_argument('source', type=Path)
    save.add_argument('destination', type=Path)
    save.add_argument('--closed', action='store_true', help='Confirm ALL application/browser/worker writers are closed')
    check = sub.add_parser('verify', help='Verify bundle bytes, SQLite and saved result artifacts without opening the app')
    check.add_argument('bundle', type=Path)
    recover = sub.add_parser('restore', help='Restore a verified bundle into a NEW isolated data root, without starting the app')
    recover.add_argument('bundle', type=Path)
    recover.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'backup':
            result = backup(args.source, args.destination, closed=args.closed)
        elif args.command == 'verify':
            result = verify(args.bundle)
        else:
            result = restore(args.bundle, args.destination)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'Workspace recovery failed: {exc}. Original data is preserved; any new partial destination is retained. Do not launch a partial destination.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
