"""Immutable presentation-only indicator snapshots in the local workspace."""
import json
import sqlite3
import unicodedata
import uuid

from terminal.data import canonical
from terminal.display_indicators import default_settings, parse_settings_document, validate_instances
from terminal.indicator_transport import check_result_budget
from terminal.storage import identifier


def preset_name(value):
    if not isinstance(value, str) or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Preset names must contain printable characters')
    value = unicodedata.normalize('NFC', value.strip())
    if not 1 <= len(value) <= 120:
        raise ValueError('Use 1 to 120 characters for a preset name')
    return value


def expected_revision(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid preset or settings revision')


def metadata(row):
    return dict(id=row['id'], name=row['name'], revision=row['revision'],
                deleted=bool(row['deleted']), instance_count=row['instance_count'])


def content_document(raw):
    try:
        doc = json.loads(raw)
        if not isinstance(doc, dict) or set(doc) != {'version', 'instances', 'extensions'} or type(doc['version']) is not int or doc['version'] != 1 or not isinstance(doc['extensions'], dict):
            raise ValueError()
        validate_instances(doc['instances'])
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError('Saved preset content is invalid or unsupported; existing data was preserved') from exc
    check_result_budget(doc)
    return doc


class ChartPresets:
    def __init__(self, display):
        self.display = display
        self.store = display.store
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS chart_presets_v1(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL,
                    revision INTEGER NOT NULL, deleted INTEGER NOT NULL,
                    instance_count INTEGER NOT NULL, content TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS chart_presets_active_name_v1
                    ON chart_presets_v1(name_key) WHERE deleted=0;
            ''')

    def list(self, trashed):
        if type(trashed) is not bool:
            raise ValueError('Invalid preset trash filter')
        with self.store.connect() as db:
            rows = db.execute('SELECT id,name,revision,deleted,instance_count FROM chart_presets_v1 WHERE deleted=? ORDER BY name_key,id', (int(trashed),))
            result = dict(version=1, presets=[metadata(row) for row in rows])
        check_result_budget(result)
        return result

    def _row(self, db, preset_id, revision):
        identifier(preset_id)
        expected_revision(revision)
        row = db.execute('SELECT * FROM chart_presets_v1 WHERE id=?', (preset_id,)).fetchone()
        if row is None:
            raise ValueError('Preset not found; reload the preset library')
        if row['revision'] != revision:
            raise ValueError('Preset changed; reload the preset library')
        return row

    def get(self, preset_id, revision):
        with self.store.connect() as db:
            row = self._row(db, preset_id, revision)
        return dict(metadata(row), content=content_document(row['content']))

    def _insert(self, db, name, raw, count):
        ident = uuid.uuid4().hex
        try:
            db.execute('INSERT INTO chart_presets_v1 VALUES(?,?,?,1,0,?,?)',
                       (ident, name, name.casefold(), count, raw))
        except sqlite3.IntegrityError as exc:
            raise ValueError('An active preset already uses that name') from exc
        return dict(id=ident, name=name, revision=1, deleted=False, instance_count=count)

    def save_current(self, name, source, market, symbol, revision):
        name = preset_name(name)
        expected_revision(revision)
        key = self.display.key(market, symbol, source)
        # Same lock order as display save. Read and preset insertion share a
        # SQLite write transaction, including against other database writers.
        with self.display.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT document FROM chart_presentation_v1 WHERE market=? AND symbol=?', key).fetchone()
            try:
                doc = parse_settings_document(row[0]) if row else default_settings()
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError('Saved indicator settings are invalid or unsupported; cannot save a preset') from exc
            if doc['revision'] != revision:
                raise ValueError('Indicator settings changed; reopen Indicators before saving a preset')
            content = dict(version=1, instances=doc['instances'], extensions={'pane_layout': doc['pane_layout']} if 'pane_layout' in doc else {})
            check_result_budget(content)
            return self._insert(db, name, canonical(content).decode(), len(content['instances']))

    def duplicate(self, preset_id, revision, name):
        name = preset_name(name)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, preset_id, revision)
            if row['deleted']:
                raise ValueError('Restore the trashed preset before duplicating it')
            content = content_document(row['content'])
            return self._insert(db, name, row['content'], len(content['instances']))

    def _change(self, preset_id, revision, *, name=None, deleted=None):
        if name is not None:
            name = preset_name(name)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, preset_id, revision)
            if deleted is None and row['deleted']:
                raise ValueError('Restore the trashed preset before renaming it')
            if deleted is not None and bool(row['deleted']) == deleted:
                raise ValueError('Preset is already trashed' if deleted else 'Preset is already active')
            result = metadata(row)
            result.update(name=row['name'] if name is None else name,
                          deleted=bool(row['deleted']) if deleted is None else deleted,
                          revision=revision + 1)
            try:
                db.execute('UPDATE chart_presets_v1 SET name=?,name_key=?,revision=?,deleted=? WHERE id=?',
                           (result['name'], result['name'].casefold(), result['revision'], int(result['deleted']), preset_id))
            except sqlite3.IntegrityError as exc:
                raise ValueError('An active preset already uses that name; rename the active preset before restoring') from exc
            return result

    def rename(self, preset_id, revision, name):
        return self._change(preset_id, revision, name=preset_name(name))

    def trash(self, preset_id, revision):
        return self._change(preset_id, revision, deleted=True)

    def restore(self, preset_id, revision):
        return self._change(preset_id, revision, deleted=False)
