import hashlib
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from terminal.chart_presets import ChartPresets
from terminal.data import canonical
from terminal.display_indicators import CONTRACT, DisplayIndicators
from terminal.service import AppService
from terminal.storage import RunStore
from terminal.vumanchu_indicators import DEFAULTS


def item(ident='ema'):
    return dict(id=ident, type='ema', params={'period': 9}, color='#123abc', visible=False)


class PresetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RunStore(Path(self.temp.name))
        self.display = DisplayIndicators(SimpleNamespace(store=self.store))
        self.presets = ChartPresets(self.display)

    def tearDown(self):
        self.display.close()
        self.temp.cleanup()

    def save(self, name='Research', revision=0, source='bybit'):
        return self.presets.save_current(name, source, 'spot', 'BTCUSDT', revision)

    def get(self, meta):
        return self.presets.get(meta['id'], meta['revision'])

    def test_exact_snapshot_restart_and_workspace_namespace_isolation(self):
        items = [dict(id='cipher', type='vmc_cipher_b', params=dict(DEFAULTS['vmc_cipher_b'], wt_hidden=True), color='#aabbcc', visible=False),
                 dict(id='native', type='volume', params={}, color='#ffffff', visible=True, placement='pane'), item()]
        settings = self.display.save('spot', 'BTCUSDT', items, 0)
        settings['origins'] = {'1': dict(time=60, generation=2, contract=CONTRACT)}
        self.display._write('spot', 'BTCUSDT', settings)
        other = self.display.save('spot', 'BTCUSDT', [], 0, 'okx')
        before = canonical(settings)
        meta = self.save('  Research  ', 1)
        self.assertEqual(meta['name'], 'Research')
        self.assertEqual(meta['instance_count'], 3)
        self.assertEqual(self.get(meta)['instance_count'], 3)
        self.assertEqual(self.get(meta)['content'], dict(version=1, instances=items, extensions={}))
        self.assertEqual(canonical(self.display.settings('spot', 'BTCUSDT')), before)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT', 'okx'), other)
        empty = self.save('Empty', 1, 'okx')
        self.assertEqual(self.get(empty)['content']['instances'], [])
        self.display.close()
        self.display = DisplayIndicators(SimpleNamespace(store=RunStore(Path(self.temp.name))))
        self.presets = ChartPresets(self.display)
        self.assertEqual(self.get(meta)['content']['instances'], items)
        self.assertEqual(len(self.presets.list(False)['presets']), 2)
        with tempfile.TemporaryDirectory() as second:
            alternate = DisplayIndicators(SimpleNamespace(store=RunStore(Path(second))))
            try:
                self.assertEqual(ChartPresets(alternate).list(False), dict(version=1, presets=[]))
            finally:
                alternate.close()

    def test_staged_apply_keeps_destination_origin_and_source_unchanged(self):
        source = self.display.save('spot', 'BTCUSDT', [item()], 0)
        source['origins'] = {'1': dict(time=60, generation=2, contract=CONTRACT)}
        self.display._write('spot', 'BTCUSDT', source)
        destination = self.display.save('linear', 'ETHUSDT', [], 0, 'okx')
        destination['origins'] = {'5': dict(time=600, generation=7, contract=CONTRACT)}
        key = self.display.key('linear', 'ETHUSDT', 'okx')
        self.display._write(*key, destination)
        preset = self.save(revision=1)
        staged = self.get(preset)['content']['instances']
        self.assertEqual(self.display.settings('linear', 'ETHUSDT', 'okx'), destination)
        applied = self.display.save('linear', 'ETHUSDT', staged, 1, 'okx')
        self.assertEqual(applied['origins'], destination['origins'])
        self.assertEqual(applied['instances'], [item()])
        self.assertEqual(applied['revision'], 2)
        self.assertEqual(self.display.settings('spot', 'BTCUSDT'), source)
        self.assertEqual(self.get(preset)['content'], dict(version=1, instances=[item()], extensions={}))

    def test_immutable_duplicate_and_future_extensions_survive_metadata(self):
        self.display.save('spot', 'BTCUSDT', [item()], 0)
        meta = self.save(revision=1)
        content = self.get(meta)['content']
        content['extensions'] = {'presentation': {'version': 9, 'panes': [{'id': 'future', 'weight': 130, 'instance_ids': ['ema']}]}}
        raw = json.dumps(content, indent=2)
        with self.store.connect() as db:
            db.execute('UPDATE chart_presets_v1 SET content=? WHERE id=?', (raw, meta['id']))
        duplicate = self.presets.duplicate(meta['id'], 1, 'Independent')
        renamed = self.presets.rename(meta['id'], 1, 'Renamed')
        trashed = self.presets.trash(meta['id'], 2)
        restored = self.presets.restore(meta['id'], 3)
        self.display.save('spot', 'BTCUSDT', [], 1)
        self.assertEqual(self.get(duplicate)['content'], content)
        self.assertEqual(self.get(restored)['content'], content)
        self.assertNotEqual(duplicate['id'], restored['id'])
        self.assertEqual((renamed['revision'], trashed['revision'], restored['revision']), (2, 3, 4))
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in db.execute('SELECT content FROM chart_presets_v1')], [raw, raw])

    def test_trash_name_reuse_restore_collision_and_durability(self):
        first = self.save('Straße')
        with self.assertRaisesRegex(ValueError, 'already uses'):
            self.save('STRASSE')
        trashed = self.presets.trash(first['id'], 1)
        second = self.save('strasse')
        with self.assertRaisesRegex(ValueError, 'already uses'):
            self.presets.restore(first['id'], 2)
        self.assertEqual(self.presets.list(True)['presets'], [trashed])
        self.presets = ChartPresets(self.display)
        self.assertTrue(self.get(trashed)['deleted'])
        self.assertEqual(self.presets.list(False)['presets'], [second])
        self.presets.rename(second['id'], 1, 'Other')
        self.assertFalse(self.presets.restore(first['id'], 2)['deleted'])

    def test_revision_conflicts_and_input_validation_do_not_mutate(self):
        meta = self.save()
        for operation in (lambda: self.presets.get(meta['id'], 0),
                          lambda: self.presets.rename(meta['id'], 0, 'Oops'),
                          lambda: self.presets.duplicate(meta['id'], 0, 'Oops'),
                          lambda: self.presets.trash(meta['id'], 0),
                          lambda: self.presets.restore(meta['id'], 0)):
            with self.assertRaisesRegex(ValueError, 'changed'):
                operation()
        self.display.save('spot', 'BTCUSDT', [], 0)
        with self.assertRaisesRegex(ValueError, 'settings changed'):
            self.save('Stale', 0)
        for name in ('', '  ', 'x'*121, 'bad\n', 'bad\x7f', 'bad\u0085', None, 9):
            with self.assertRaises(ValueError):
                self.save(name, 1)
            with self.assertRaises(ValueError):
                self.presets.rename(meta['id'], 1, name)
        with self.assertRaises(ValueError):
            self.save('Bool', True)
        with self.assertRaises(ValueError):
            self.presets.list(0)
        self.assertEqual(self.presets.list(False)['presets'], [meta])

    def test_corrupt_unsupported_applied_state_never_saves_defaults(self):
        valid = self.display.save('spot', 'BTCUSDT', [item()], 0)
        malformed = ['{', '[]', json.dumps(dict(valid, version=2)), json.dumps(dict(valid, instances=[dict(item(), type='future')])), json.dumps(dict(valid, origins={'1': {}}))]
        for raw in malformed:
            with self.store.connect() as db:
                db.execute('UPDATE chart_presentation_v1 SET document=?', (raw,))
            with self.assertRaisesRegex(ValueError, 'invalid or unsupported'):
                self.save('Corrupt', 0)
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT document FROM chart_presentation_v1').fetchone()[0], raw)
        self.assertEqual(self.presets.list(False)['presets'], [])

    def test_corrupt_unsupported_preset_rejects_get_and_duplicate(self):
        meta = self.save()
        for raw in ('{', '{"version":2,"instances":[],"extensions":{}}', '{"version":1,"instances":[{}],"extensions":{}}'):
            with self.store.connect() as db:
                db.execute('UPDATE chart_presets_v1 SET content=?', (raw,))
            with self.assertRaisesRegex(ValueError, 'invalid or unsupported'):
                self.get(meta)
            with self.assertRaisesRegex(ValueError, 'invalid or unsupported'):
                self.presets.duplicate(meta['id'], 1, 'Bad copy')
        self.assertEqual(len(self.presets.list(False)['presets']), 1)

    def test_no_count_cap_and_resource_failure_atomic(self):
        items = [item('i'+str(i)) for i in range(1025)]
        self.display.save('spot', 'BTCUSDT', items, 0)
        meta = self.save(revision=1)
        self.assertEqual(self.get(meta)['content']['instances'], items)
        for i in range(130):
            self.presets.duplicate(meta['id'], 1, 'Copy '+str(i))
        self.assertEqual(len(self.presets.list(False)['presets']), 131)
        with patch('terminal.indicator_transport.MAX_RESULT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'resource budget'):
                self.save('Too large', 1)
            with self.assertRaisesRegex(ValueError, 'resource budget'):
                self.presets.duplicate(meta['id'], 1, 'Too large')
        self.assertEqual(len(self.presets.list(False)['presets']), 131)

    def test_database_snapshot_blocks_competing_settings_writer_until_commit(self):
        self.display.save('spot', 'BTCUSDT', [item()], 0)
        start, attempted, finished = threading.Event(), threading.Event(), threading.Event()
        errors = []
        replacement = dict(version=1, revision=2, instances=[], origins={})
        def writer():
            try:
                start.wait(5)
                with self.store.connect() as db:
                    attempted.set()
                    db.execute('UPDATE chart_presentation_v1 SET document=?', (canonical(replacement).decode(),))
                finished.set()
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=writer)
        original = self.presets._insert
        def insert(*args):
            start.set()
            self.assertTrue(attempted.wait(5))
            self.assertFalse(finished.wait(.05))
            return original(*args)
        thread.start()
        try:
            with patch.object(self.presets, '_insert', side_effect=insert):
                meta = self.save(revision=1)
        finally:
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.get(meta)['content']['instances'], [item()])
        self.assertEqual(self.display.settings('spot', 'BTCUSDT'), replacement)
        with self.assertRaisesRegex(ValueError, 'settings changed'):
            self.save('Stale after writer', 1)

    def test_concurrent_metadata_revision_is_guarded_transactionally(self):
        meta = self.save()
        barrier = threading.Barrier(2)
        results, errors = [], []
        def rename(name):
            barrier.wait()
            try:
                results.append(self.presets.rename(meta['id'], 1, name))
            except ValueError as exc:
                errors.append(str(exc))
        threads = [threading.Thread(target=rename, args=(name,)) for name in ('First', 'Second')]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn('changed', errors[0])
        self.assertEqual(self.presets.list(False)['presets'], results)


class PresetServiceTests(unittest.TestCase):
    def test_strict_commands_and_exact_paged_get_and_list(self):
        with tempfile.TemporaryDirectory() as root:
            service = AppService(Path(root))
            def call(command, **params):
                return service.handle(dict(version=1, id='preset-test', command=command, params=params))
            def unpack(result):
                if result.get('status') != 'paged': return result
                pages = [call('chart_indicator_page', snapshot_id=result['snapshot_id'], index=i)['result']['text'] for i in range(result['pages'])]
                raw = ''.join(pages).encode()
                self.assertEqual(len(raw), result['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), result['sha256'])
                return json.loads(raw)
            try:
                items = [item('i'+str(i)) for i in range(13000)]
                service.display_indicators.save('spot', 'BTCUSDT', items, 0)
                meta = call('chart_preset_save_current', name='Many', source='bybit', market='spot', symbol='BTCUSDT', revision=1)['result']
                result = call('chart_preset_get', preset_id=meta['id'], revision=1)['result']
                self.assertEqual(result['status'], 'paged')
                self.assertEqual(unpack(result)['content']['instances'], items)
                with patch('terminal.indicator_transport.INLINE_BYTES', 10):
                    listing = call('chart_preset_list', trashed=False)['result']
                self.assertEqual(listing['status'], 'paged')
                self.assertEqual(unpack(listing), dict(version=1, presets=[meta]))
                for command, params in [('chart_preset_list', {}), ('chart_preset_get', {'preset_id': meta['id']}), ('chart_preset_save_current', {'name': 'No revision'}), ('chart_preset_overwrite', {})]:
                    self.assertEqual(call(command, **params)['type'], 'error')
                duplicate = call('chart_preset_duplicate', preset_id=meta['id'], revision=1, name='Copy')['result']
                renamed = call('chart_preset_rename', preset_id=duplicate['id'], revision=1, name='Renamed')['result']
                trashed = call('chart_preset_trash', preset_id=duplicate['id'], revision=2)['result']
                restored = call('chart_preset_restore', preset_id=duplicate['id'], revision=3)['result']
                self.assertEqual((renamed['revision'], trashed['deleted'], restored['revision']), (2, True, 4))
            finally:
                service.close()
