import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from terminal.notifications import NotificationError, Telegram, WindowsCredentials
from terminal.service import AppService
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.native import load_trusted, trust_identity
from tests.test_native_import import native_document


@unittest.skipUnless(sys.platform == 'linux', 'Linux capability acceptance check')
class LinuxBackendTests(unittest.TestCase):
    def test_research_startup_and_secret_integrations_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            service = AppService(root)
            try:
                def call(command, params=None):
                    return service.handle({'version':1, 'id':'fixture', 'command':command, 'params':params or {}})
                capabilities = call('platform_capabilities')['result']
                self.assertEqual(capabilities['platform'], 'linux')
                self.assertFalse(capabilities['native_execution']['available'])
                self.assertTrue(all(not value['available'] for value in capabilities['notifications'].values()))
                self.assertEqual(call('list_runs')['result'], [])
                status = call('live_status')['result']['telegram']
                self.assertFalse(status['configured'])
                self.assertFalse(status['available'])
                for command, params in [('telegram_configure', {'token':'invalid fixture', 'chat_id':'invalid fixture'}),
                        ('telegram_clear', {}), *[('notification_test', {'channel':channel}) for channel in ('telegram','windows','sound')]]:
                    response = call(command, params)
                    self.assertEqual(response['type'], 'error', response)
                    self.assertIn('unavailable', response['error']['message'])
                self.assertTrue(service.live.delivery_queue.empty())
                self.assertEqual(list(Path(root).glob('**/*credential*')), [])
                opener = Mock()
                with self.assertRaisesRegex(NotificationError, 'unavailable'):
                    Telegram(WindowsCredentials(root), opener).send('Synthetic fixture')
                opener.open.assert_not_called()
            finally:
                service.close()

    def test_trusted_native_library_row_is_unavailable_during_preflight(self):
        from terminal.library import prepare
        with tempfile.TemporaryDirectory() as root:
            service = AppService(root)
            try:
                selection = {'entry_id':'native-ema-cross', 'version':2, 'minutes':1, 'parameters':{}}
                document = prepare(**selection)['document']
                service.store.trust_native(trust_identity(document))
                bars = [Candle(i * 60, 100, 101, 99, 100, 100) for i in range(120)]
                data = service.datasets.save('linear', 'BTCUSDT', 0, 7200, bars, bars, {}, metadata={}, provenance=[])
                report = service.library_batches.preview(selections=[selection], dataset_id=data['id'],
                    profile=Profile(market='linear', primary_minutes=1, funding_mode='assumed_zero').snapshot(),
                    start=1800, end=7200, interval='daily', spot_dataset_id=None)
                self.assertIn('Native Python execution is unavailable', report['rows'][0]['error'])
                self.assertEqual(service.store.recent(), [])
            finally:
                service.close()

    def test_failure_after_go_waits_for_supervisor_without_killing_it(self):
        import threading
        with tempfile.TemporaryDirectory() as root:
            service = AppService(root)
            captured = []
            original = threading.Thread.start
            def start(thread):
                if getattr(thread._target, '__name__', None) == '_monitor':
                    process = thread._args[1]
                    process.terminate = Mock(side_effect=AssertionError('Do not kill the supervisor before cleanup'))
                    captured.append(process)
                    raise RuntimeError('Synthetic failure after bootstrap')
                return original(thread)
            try:
                bars = [Candle(i * 60, 100, 101, 99, 100, 100) for i in range(120)]
                data = service.datasets.save('spot', 'BTCUSDT', 0, 7200, bars, [], {}, metadata={}, provenance=[])
                with patch('terminal.jobs.threading.Thread.start', start):
                    with self.assertRaisesRegex(RuntimeError, 'Synthetic failure after bootstrap'):
                        service.jobs.start(example_graph(), Profile(primary_minutes=1), data['id'])
                self.assertEqual(len(captured), 1)
                self.assertIsNotNone(captured[0].poll())
                captured[0].terminate.assert_not_called()
                self.assertIsNone(service.jobs.active)
                self.assertEqual(service.store.recent()[0]['status'], 'failed')
            finally:
                service.close()
            reopened = AppService(root)
            reopened.close()

    def test_native_preview_trust_and_reopening_do_not_enable_execution(self):
        with tempfile.TemporaryDirectory() as root:
            service = AppService(root)
            try:
                sentinel = Path(root) / 'must-not-execute'
                document = native_document(f'from pathlib import Path\nPath({str(sentinel)!r}).touch()\n')
                response = service.handle({'version':1, 'id':'fixture', 'command':'trust_native', 'params':{
                    'document':document, 'expected_sha256':trust_identity(document), 'acknowledge_user_permissions':True}})
                self.assertEqual(response['type'], 'result', response)
                self.assertFalse(sentinel.exists())
                with self.assertRaisesRegex(ValueError, 'Native Python execution is unavailable'):
                    service.jobs.start(document, {}, 'unused')
                with self.assertRaisesRegex(ValueError, 'Native Python execution is unavailable'):
                    load_trusted(document, Path(root), None)
                self.assertFalse(sentinel.exists())
                self.assertEqual(service.store.recent(), [])
            finally:
                service.close()


class BridgeBoundaryTests(unittest.TestCase):
    def invoke(self, payload, *, code=None):
        with tempfile.TemporaryDirectory() as root:
            command = ([sys.executable, '-c', code, '--data-root', root] if code else
                       [sys.executable, '-m', 'terminal.bridge', '--data-root', root])
            process = subprocess.run(command, input=payload, capture_output=True, timeout=20,
                cwd=Path(__file__).resolve().parents[1])
            return process, [json.loads(line) for line in process.stdout.splitlines()]

    def test_import_failure_is_a_startup_error_envelope(self):
        code = '''import builtins
from terminal.bridge import main
original = builtins.__import__
def injected(name, *args, **kwargs):
    if name == "terminal.service":
        raise ImportError("Synthetic unavailable runtime dependency")
    return original(name, *args, **kwargs)
builtins.__import__ = injected
raise SystemExit(main())
'''
        process, messages = self.invoke(b'', code=code)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['error']['code'], 'STARTUP_FAILED')
        self.assertIn('Synthetic unavailable', messages[0]['error']['message'])

    def test_invalid_json_utf8_and_eof_preserve_protocol(self):
        valid = b'{"version":1,"id":"after","command":"list_runs","params":{}}\n'
        process, messages = self.invoke(b'not JSON\n\xff\n' + valid)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(messages[0]['type'], 'ready')
        self.assertEqual([value['error']['code'] for value in messages[1:3]], ['INVALID_JSON', 'INVALID_JSON'])
        self.assertEqual(messages[3]['id'], 'after')
        self.assertEqual(messages[3]['result'], [])

    def test_oversized_line_stops_before_remainder_can_be_a_request(self):
        process, messages = self.invoke(b'x' * (1024 * 1024 + 1) + b'\n' +
            b'{"version":1,"id":"never","command":"list_runs","params":{}}\n')
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]['error']['code'], 'TOO_LARGE')
