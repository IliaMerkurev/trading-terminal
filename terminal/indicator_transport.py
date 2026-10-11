"""Immutable disk-backed byte-bounded snapshots, independent of instance count."""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import uuid

PAGE_CHARS = 64 * 1024
INLINE_BYTES = 800 * 1024
MAX_RESULT_BYTES = 64 * 1024 * 1024
RESOURCE_ERROR = 'Indicator data exceeds the 64 MiB resource budget; use a smaller chart window. Settings are not truncated.'
ENCODER = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def check_result_budget(value):
    size = 0
    for part in ENCODER.iterencode(value):
        size += len(part)  # Canonical representation is ASCII.
        if size > MAX_RESULT_BYTES:
            raise ValueError(RESOURCE_ERROR)


class IndicatorTransport:
    def __init__(self):
        self.lock = threading.RLock()
        self.directory = tempfile.TemporaryDirectory(prefix='terminal-indicators-')
        self.snapshots = OrderedDict()
        self.upload = None

    def pack(self, value):
        with self.lock:
            ident = uuid.uuid4().hex
            path = Path(self.directory.name) / ident
            size, digest = 0, hashlib.sha256()
            try:
                with path.open('xb') as stream:
                    for part in ENCODER.iterencode(value):
                        raw = part.encode('ascii'); size += len(raw)
                        if size > MAX_RESULT_BYTES:
                            raise ValueError(RESOURCE_ERROR)
                        stream.write(raw); digest.update(raw)
                if size <= INLINE_BYTES:
                    path.unlink()
                    return value
                descriptor = dict(status='paged', snapshot_id=ident,
                                  sha256=digest.hexdigest(), bytes=size,
                                  pages=(size + PAGE_CHARS - 1) // PAGE_CHARS)
                self.snapshots[ident] = (descriptor, path)
                while len(self.snapshots) > 2:
                    _, (_, old_path) = self.snapshots.popitem(last=False)
                    old_path.unlink(missing_ok=True)
                return descriptor
            except Exception:
                path.unlink(missing_ok=True)
                raise

    def page(self, snapshot_id, index):
        with self.lock:
            value = self.snapshots.get(snapshot_id) if isinstance(snapshot_id, str) else None
            if value is None:
                raise ValueError('Indicator snapshot expired; retry the read')
            descriptor, path = value
            if type(index) is not int or not 0 <= index < descriptor['pages']:
                raise ValueError('Invalid indicator snapshot page')
            with path.open('rb') as stream:
                stream.seek(index * PAGE_CHARS)
                text = stream.read(PAGE_CHARS).decode('ascii')
            return dict(descriptor, index=index, text=text)

    def upload_begin(self, size, sha256):
        if type(size) is not int or not 0 < size <= MAX_RESULT_BYTES:
            raise ValueError('Indicator settings exceed the 64 MiB resource budget; saved settings are unchanged')
        if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in '0123456789abcdef' for c in sha256):
            raise ValueError('Invalid indicator settings upload')
        with self.lock:
            if self.upload:
                self.upload['path'].unlink(missing_ok=True)
            ident = uuid.uuid4().hex
            path = Path(self.directory.name) / ident
            path.touch(exist_ok=False)
            self.upload = dict(upload_id=ident, size=size, sha256=sha256, path=path, offset=0)
            return dict(upload_id=ident)

    def upload_append(self, upload_id, offset, text):
        with self.lock:
            upload = self.upload
            if not upload or upload['upload_id'] != upload_id:
                raise ValueError('Indicator settings upload expired; saved settings are unchanged')
            if type(offset) is not int or offset != upload['offset'] or not isinstance(text, str) or not 0 < len(text) <= PAGE_CHARS:
                raise ValueError('Invalid indicator settings upload page')
            raw = text.encode('utf-8')
            if offset + len(raw) > upload['size']:
                raise ValueError('Indicator settings upload length mismatch')
            with upload['path'].open('ab') as stream:
                stream.write(raw)
            upload['offset'] += len(raw)
            return dict(upload_id=upload_id, offset=upload['offset'])

    def upload_finish(self, upload_id):
        with self.lock:
            upload = self.upload
            if not upload or upload['upload_id'] != upload_id:
                raise ValueError('Indicator settings upload expired; inspect saved settings before retrying')
            self.upload = None
            try:
                with upload['path'].open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if upload['offset'] != upload['size'] or digest != upload['sha256']:
                    raise ValueError('Indicator settings upload checksum or length mismatch')
                with upload['path'].open(encoding='utf-8') as stream:
                    value = json.load(stream)
                if not isinstance(value, dict) or set(value) != {'market', 'symbol', 'source', 'revision', 'instances'}:
                    raise ValueError('Invalid indicator settings upload fields')
                return value
            finally:
                upload['path'].unlink(missing_ok=True)

    def close(self):
        with self.lock:
            self.snapshots.clear(); self.upload = None
            self.directory.cleanup()
