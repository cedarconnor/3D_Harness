"""Filesystem spelling must not change evidence identity or bypass reparse checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from dcc_harness import evidence, files, live_snapshot


class NativePathTests(unittest.TestCase):
    def test_windows_adapter_keeps_drive_and_unc_paths_out_of_device_namespaces(self):
        convert = getattr(files, '_windows_io_path', None)
        self.assertTrue(callable(convert), 'Missing Windows filesystem boundary adapter')
        self.assertEqual(convert('C:/owned/a/../b.json'), '\\\\?\\C:\\owned\\b.json')
        self.assertEqual(convert('//server/share/owned/b.json'), '\\\\?\\UNC\\server\\share\\owned\\b.json')
        for path in ('//?/C:/owned/file', '//./C:/owned/file', '//?/GLOBALROOT/Device/file',
                     'C:/owned/NUL', 'C:/owned/con.txt', 'C:/owned/file:stream',
                     'C:/owned/trailing.', 'C:/owned/trailing '):
            with self.subTest(path=path), self.assertRaises(ValueError):
                convert(path)

    def test_long_roundtrip_preserves_json_bytes_and_logical_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ('a' * 90) / ('b' * 90) / ('c' * 70)
            path = root / 'evidence.json'
            value = {'path': str(path), 'unicode': '\u96ea'}
            identity = evidence.digest(value)
            evidence.write_json(path, value)
            self.assertEqual(evidence.read_json(path), value)
            self.assertEqual(evidence.digest(evidence.read_json(path)), identity)
            self.assertEqual(files.reject_links(path), path)
            with self.assertRaises(FileExistsError):
                evidence.write_json(path, {'changed': True})
            target = root / 'copy/evidence.json'
            self.assertEqual(files.copy_verified(path, target, files.file_hash(path), 'changed'), target)
            self.assertEqual(evidence.read_json(target), value)
            retained = live_snapshot.retain(root, value)
            self.assertEqual(retained, live_snapshot.fingerprint(value))
            self.assertTrue(live_snapshot.matches_retained(root, retained, value))
            self.assertEqual(live_snapshot.retain(root, value), retained)

    def test_link_check_does_not_treat_not_a_directory_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'file'; file.write_bytes(b'file')
            # Windows reports ENOENT for a file used as a directory, so use the
            # explicit OS error at the syscall boundary for portable coverage.
            with mock.patch.object(Path, 'lstat', side_effect=NotADirectoryError('not a directory')):
                with self.assertRaises(NotADirectoryError):
                    files.reject_links(file / 'child')

    def test_inaccessible_component_propagates_original_error(self):
        error = PermissionError('denied component')
        with mock.patch.object(Path, 'lstat', side_effect=error):
            with self.assertRaises(PermissionError) as raised:
                files.reject_links('missing/child')
        self.assertIs(raised.exception, error)

    def test_path_too_long_is_not_missing_even_when_os_uses_file_not_found(self):
        error = FileNotFoundError('path too long'); error.winerror = 206
        with mock.patch.object(Path, 'lstat', side_effect=error):
            with self.assertRaises(FileNotFoundError) as raised:
                files.reject_links('missing/child')
        self.assertIs(raised.exception, error)

    def test_profile_config_guard_precedes_activation_and_worker(self):
        # Host substitute for the native bpy/add-on boundary; run the real
        # bootstrap in a subprocess so its audit hook cannot leak into tests.
        code = '''
import contextlib, runpy, sys, types
from pathlib import Path
runtime, folder, actual = map(Path, sys.argv[1:])
sys.path.insert(0, str(runtime))
sys.modules['bpy'] = types.SimpleNamespace(utils=types.SimpleNamespace(user_resource=lambda _: str(actual)),
                                          app=types.SimpleNamespace(background=True))
sys.modules['dcc_harness.environments'] = types.SimpleNamespace(load_profile=lambda _: {})
def activate(profile): (folder / 'activated').write_text('activated')
addons = types.SimpleNamespace(
    NETWORK_ATTEMPTS=[], LAST_ACTIVATION=None, enable_profile=activate, session_preferences=contextlib.nullcontext)
sys.modules['dcc_harness.data.bridge'] = types.SimpleNamespace(addons=addons)
sys.argv = ['bootstrap', '--', 'verify', str(folder / 'verify-request.json'), str(folder / 'worker.py')]
runpy.run_path(str(runtime / 'dcc_harness/_profile_blender.py'), run_name='__main__')
'''
        runtime = Path(evidence.__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for matched in (False, True):
                folder = root / str(matched); folder.mkdir()
                expected = folder / 'verify-user-config'; expected.mkdir()
                evidence.write_json(folder / 'verify-request.json', {'profile': {}})
                (folder / 'worker.py').write_text('from pathlib import Path\nPath(' + repr(str(folder / 'worked'))
                                                  + ").write_text('worked')\n")
                actual = expected if matched else root
                result = subprocess.run([sys.executable, '-c', code, str(runtime), str(folder), str(actual)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, matched, result.stderr)
                self.assertEqual((folder / 'activated').exists(), matched)
                self.assertEqual((folder / 'worked').exists(), matched)
                if not matched:
                    self.assertIn('Owned worker configuration was not selected', result.stderr)


if __name__ == '__main__':
    unittest.main()
