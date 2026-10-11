"""The shared file helpers, and that the modules which used to duplicate them now use them."""
from pathlib import Path
import tempfile
import unittest

from dcc_harness import continuity, coordination, evidence, files


class FileHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_copy_verified_is_exclusive_and_checks_both_sides(self):
        source = self.base / 'source.bin'
        source.write_bytes(b'checkpoint bytes')
        files.copy_verified(source, self.base / 'out/copy.bin', files.file_hash(source), 'changed')
        self.assertEqual((self.base / 'out/copy.bin').read_bytes(), b'checkpoint bytes')
        with self.assertRaises(FileExistsError):
            files.copy_verified(source, self.base / 'out/copy.bin', files.file_hash(source), 'changed')
        with self.assertRaisesRegex(ValueError, 'Source changed here'):
            files.copy_verified(source, self.base / 'out/other.bin', '0' * 64, 'Source changed here')
        self.assertTrue((self.base / 'out/other.bin').exists(), 'a failed copy stays visible for inspection')

    def test_write_exclusive_and_json_text(self):
        files.write_exclusive(self.base / 'a.json', files.json_bytes({'b': 1, 'a': [1.5]}))
        self.assertEqual((self.base / 'a.json').read_bytes(), b'{\n  "a": [\n    1.5\n  ],\n  "b": 1\n}\n')
        with self.assertRaises(FileExistsError):
            files.write_exclusive(self.base / 'a.json', b'x')
        with self.assertRaises(ValueError):
            files.json_text({'x': float('nan')})
        self.assertEqual(files.json_text({'b': 1, 'a': 2}, compact=True), '{"a":2,"b":1}\n')

    def test_reject_links_returns_the_absolute_path_with_a_chosen_message(self):
        self.assertTrue(files.reject_links(self.base / 'missing/file').is_absolute())

    def test_former_duplicates_are_the_shared_helpers(self):
        self.assertIs(evidence.file_hash, files.file_hash)
        self.assertIs(continuity._plain, files.reject_links)
        self.assertIs(continuity._write, files.write_exclusive)
        self.assertIs(continuity._json_bytes, files.json_bytes)
        self.assertIs(coordination._plain, files.reject_links)


if __name__ == '__main__':
    unittest.main()
