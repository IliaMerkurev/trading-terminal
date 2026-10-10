"""Platform selection and unchanged Windows/runtime contract checks."""
import importlib.util
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_runtime', ROOT / 'scripts/verify_runtime.py')
verify_runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_runtime)


class RuntimeSelectionTests(unittest.TestCase):
    def test_windows_selects_original_lock_without_linux_requirement(self):
        with patch.object(verify_runtime.platform, 'libc_ver', side_effect=AssertionError):
            self.assertEqual(verify_runtime.runtime_lock('Windows', 'AMD64', (3, 12)), 'runtime-windows-py312.lock')

    def test_linux_selects_own_lock(self):
        with patch.object(verify_runtime.platform, 'libc_ver', return_value=('glibc', '2.35')):
            self.assertEqual(verify_runtime.runtime_lock('Linux', 'x86_64', (3, 12)), 'runtime-linux-py312.lock')

    def test_unsupported_platforms_fail_closed(self):
        for system, machine, version in [('Darwin', 'x86_64', (3, 12)), ('Linux', 'aarch64', (3, 12)), ('Windows', 'AMD64', (3, 13))]:
            with self.subTest(system=system, machine=machine, version=version), self.assertRaises(ValueError):
                verify_runtime.runtime_lock(system, machine, version)
        for libc in [('musl', '1.2'), ('glibc', '2.34')]:
            with patch.object(verify_runtime.platform, 'libc_ver', return_value=libc), self.assertRaises(ValueError):
                verify_runtime.runtime_lock('Linux', 'x86_64', (3, 12))

    def test_shared_packages_keep_exact_windows_versions(self):
        def pins(name):
            return dict(re.findall(r'^([\w-]+)==([^ ]+)', (ROOT / 'requirements' / name).read_text(), re.M))
        windows = pins('runtime-windows-py312.lock')
        linux = pins('runtime-linux-py312.lock')
        self.assertEqual({name: linux[name] for name in windows}, windows)
        self.assertEqual(set(linux) - set(windows), {'uvloop'})
        for line in (ROOT / 'requirements/runtime-linux-py312.lock').read_text().splitlines():
            if line and not line.startswith('#'):
                self.assertRegex(line, r'^\w[\w-]*==\S+ --hash=sha256:[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
