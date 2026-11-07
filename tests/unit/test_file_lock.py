import errno
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from utils.file_lock import exclusive_file_lock


class FileLockTests(unittest.TestCase):
    def windows_backend(self):
        return SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=Mock())

    def test_windows_locks_same_byte_and_preserves_existing_utf8_records(self):
        backend = self.windows_backend()
        positions = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metrics.jsonl'
            path.write_text('registro previo\n', encoding='utf-8')
            with path.open('a', encoding='utf-8') as sink:
                backend.locking.side_effect = lambda *args: positions.append(sink.tell())
                with patch('utils.file_lock.os.name', 'nt'), \
                     patch.dict(sys.modules, {'msvcrt': backend, 'fcntl': None}):
                    with exclusive_file_lock(sink):
                        sink.write('próximo registro\n')
            self.assertEqual(path.read_text(encoding='utf-8'), 'registro previo\npróximo registro\n')
        self.assertEqual(positions, [0, 0])
        self.assertEqual([call.args[1:] for call in backend.locking.call_args_list], [(1, 1), (2, 1)])

    def test_windows_empty_file_waits_for_busy_lock(self):
        backend = self.windows_backend()
        backend.locking.side_effect = [OSError(errno.EACCES, 'busy'), None, None]
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as sink, \
             patch('utils.file_lock.os.name', 'nt'), \
             patch.dict(sys.modules, {'msvcrt': backend, 'fcntl': None}), \
             patch('utils.file_lock.time.sleep') as sleep:
            with exclusive_file_lock(sink):
                sink.write('first record\n')
            sink.seek(0)
            self.assertEqual(sink.read(), 'first record\n')
            self.assertEqual(backend.locking.call_count, 3)
            sleep.assert_called_once_with(0.05)

    def test_windows_unexpected_error_propagates_without_retry(self):
        backend = self.windows_backend()
        backend.locking.side_effect = OSError(errno.EBADF, 'invalid handle')
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as sink, \
             patch('utils.file_lock.os.name', 'nt'), \
             patch.dict(sys.modules, {'msvcrt': backend}), \
             patch('utils.file_lock.time.sleep') as sleep:
            with self.assertRaises(OSError):
                with exclusive_file_lock(sink):
                    self.fail('Writing requires a successful lock')
            self.assertEqual(backend.locking.call_count, 1)
            sleep.assert_not_called()

    def test_both_platforms_release_lock_after_body_failure(self):
        for system in ['nt', 'posix']:
            windows = self.windows_backend()
            unix = SimpleNamespace(LOCK_EX=1, LOCK_UN=2, flock=Mock())
            with self.subTest(system=system), \
                 tempfile.TemporaryFile(mode='w+', encoding='utf-8') as sink, \
                 patch('utils.file_lock.os.name', system), \
                 patch.dict(sys.modules, {'msvcrt': windows, 'fcntl': unix}):
                with self.assertRaisesRegex(RuntimeError, 'write failed'):
                    with exclusive_file_lock(sink):
                        raise RuntimeError('write failed')
                calls = windows.locking.call_args_list if system == 'nt' else unix.flock.call_args_list
                self.assertEqual([call.args[1] for call in calls], [1, 2])

    def test_both_platforms_release_lock_after_flush_failure(self):
        for system in ['nt', 'posix']:
            windows = self.windows_backend()
            unix = SimpleNamespace(LOCK_EX=1, LOCK_UN=2, flock=Mock())
            sink = Mock()
            sink.flush.side_effect = OSError('flush failed')
            with self.subTest(system=system), patch('utils.file_lock.os.name', system), \
                 patch.dict(sys.modules, {'msvcrt': windows, 'fcntl': unix}):
                with self.assertRaises(OSError):
                    with exclusive_file_lock(sink):
                        pass
                calls = windows.locking.call_args_list if system == 'nt' else unix.flock.call_args_list
                self.assertEqual([call.args[1] for call in calls], [1, 2])

    def test_metrics_remain_valid_with_concurrent_processes(self):
        script = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from utils import metrics
metrics.METRICS_DIR = Path(sys.argv[2])
for i in range(12):
    metrics._persist_metrics({
        'timestamp': '2026-11-07T12:00:00+00:00', 'provider': 'gemini',
        'model': sys.argv[3] + '_' + str(i) + '_' + 'á' * 10000,
        'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2,
        'latency_s': 1, 'cost_usd': None,
    }, 'input')
'''
        root = Path(__file__).resolve().parents[2]
        processes = []
        with tempfile.TemporaryDirectory() as directory:
            try:
                for worker in range(4):
                    processes.append(subprocess.Popen(
                        [sys.executable, '-B', '-c', script, str(root / 'src'), directory, str(worker)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    ))
                for process in processes:
                    _, stderr = process.communicate(timeout=30)
                    self.assertEqual(process.returncode, 0, stderr)
                rows = [json.loads(line) for line in (Path(directory) / 'input_moderation.jsonl').read_text(encoding='utf-8').splitlines()]
                self.assertEqual(len(rows), 48)
                self.assertEqual(len({row['model'] for row in rows}), 48)
                self.assertTrue(all(row['total_tokens'] == 2 for row in rows))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()
