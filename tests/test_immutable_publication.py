import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from terminal.data import DataError, write_new


def publish_together(path, content, barrier, results):
    # Synchronize after both writers have produced their complete temporary file.
    name = 'rename' if os.name == 'nt' else 'link'
    original = getattr(os, name)
    def publish(source, destination):
        barrier.wait(timeout=10)
        return original(source, destination)
    try:
        with patch('terminal.data.os.' + name, side_effect=publish):
            write_new(path, content)
        results.put('published')
    except DataError:
        results.put('conflict')


class ImmutablePublicationTests(unittest.TestCase):
    def test_existing_bytes_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'snapshot.json'
            write_new(path, b'original')
            write_new(path, b'original')
            with self.assertRaises(DataError):write_new(path, b'changed')
            self.assertEqual(path.read_bytes(), b'original')
            self.assertEqual(list(Path(root).glob('*.partial')), [])

    def test_concurrent_equal_and_conflicting_publication(self):
        context = multiprocessing.get_context('spawn')
        for contents in [(b'A' * 65536, b'A' * 65536), (b'A' * 65536, b'B' * 65536)]:
            with self.subTest(equal=contents[0] == contents[1]), tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'snapshot.json'
                barrier = context.Barrier(2)
                results = context.Queue()
                processes = [context.Process(target=publish_together, args=(path, data, barrier, results)) for data in contents]
                try:
                    for process in processes:process.start()
                    for process in processes:
                        process.join(timeout=15)
                        self.assertEqual(process.exitcode, 0)
                    expected = ['published', 'published'] if contents[0] == contents[1] else ['conflict', 'published']
                    self.assertEqual(sorted(results.get(timeout=2) for _ in processes), expected)
                    self.assertIn(path.read_bytes(), contents)
                    self.assertEqual(list(Path(root).glob('*.partial')), [])
                finally:
                    for process in processes:
                        if process.is_alive():process.terminate()
                        process.join(timeout=5)
                    results.close()
                    results.join_thread()

    def test_temporary_collision_does_not_remove_another_writers_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'snapshot.json'
            other = Path(root) / 'snapshot.json.fixture.partial'
            other.write_bytes(b'another writer')
            with patch('terminal.data.uuid.uuid4') as identity:
                identity.return_value.hex = 'fixture'
                with self.assertRaises(FileExistsError):write_new(path, b'new content')
            self.assertEqual(other.read_bytes(), b'another writer')
            self.assertFalse(path.exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX publication failure path')
    def test_no_overwrite_fallback_on_unsupported_link(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'snapshot.json'
            with patch('terminal.data.os.link', side_effect=OSError('Unsupported fixture filesystem')):
                with self.assertRaises(OSError):write_new(path, b'complete')
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(root).iterdir()), [])
