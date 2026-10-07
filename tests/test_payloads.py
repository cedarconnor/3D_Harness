"""fill-hashes fills and verifies payload file references without trusting stale hashes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.payloads import fill_hashes


class FillHashesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        (self.base / 'before').mkdir()
        self.receipt = self.base / 'before' / 'receipt.json'
        self.receipt.write_text('{"receipt": 1}', encoding='utf-8')
        self.settings = self.base / 'before' / 'views.json'
        self.settings.write_text('{"views": 1}', encoding='utf-8')

    def payload(self, value, name='note.json'):
        path = self.base / name
        write_json(path, value)
        return path

    def test_missing_hashes_in_nested_references_are_filled_into_a_new_file(self):
        source = self.payload({'anchor': {'render': {'receipt': {'path': 'before/receipt.json'},
                                                     'settings': {'path': 'before/views.json', 'sha256': None},
                                                     'view_id': 'DETAIL'}},
                               'evidence': [{'kind': 'handoff', 'file': {'path': 'before/receipt.json', 'sha256': ''}}]})
        result = fill_hashes(source, self.base / 'filled.json')
        filled = read_json(self.base / 'filled.json')
        self.assertEqual(filled['anchor']['render']['receipt']['sha256'], file_hash(self.receipt))
        self.assertEqual(filled['anchor']['render']['settings']['sha256'], file_hash(self.settings))
        self.assertEqual(filled['evidence'][0]['file']['sha256'], file_hash(self.receipt))
        self.assertEqual(len(result['filled']), 3)
        self.assertNotIn('sha256', read_json(source)['anchor']['render']['receipt'])

    def test_present_hash_is_verified(self):
        source = self.payload({'file': {'path': 'before/receipt.json', 'sha256': file_hash(self.receipt)}})
        result = fill_hashes(source, self.base / 'verified.json')
        self.assertEqual(result['verified'], ['before/receipt.json'])
        self.assertEqual(result['filled'], [])

    def test_stale_hash_is_rejected_and_nothing_is_written(self):
        source = self.payload({'file': {'path': 'before/receipt.json', 'sha256': '0' * 64}})
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            fill_hashes(source, self.base / 'never.json')
        self.assertFalse((self.base / 'never.json').exists())

    def test_paths_must_stay_inside_the_base(self):
        names = ('../outside.json', 'C:/outside.json', '/outside.json', 'before\\receipt.json',
                 'before/../before/receipt.json')
        for index, name in enumerate(names):
            source = self.payload({'file': {'path': name}}, name=f'bad-{index}.json')
            with self.assertRaises(ValueError, msg=name):
                fill_hashes(source, self.base / 'never.json')
        self.assertFalse((self.base / 'never.json').exists())

    def test_missing_file_is_rejected(self):
        source = self.payload({'file': {'path': 'before/missing.json'}})
        with self.assertRaisesRegex(ValueError, 'not found'):
            fill_hashes(source, self.base / 'never.json')

    def test_objects_that_are_not_pure_references_are_left_alone(self):
        value = {'note': {'path': 'before/receipt.json', 'reason': 'mentions a path'}, 'text': 'before/receipt.json'}
        result = fill_hashes(self.payload(value), self.base / 'same.json')
        self.assertEqual(read_json(self.base / 'same.json'), value)
        self.assertEqual(result['filled'], [])

    def test_existing_destination_is_never_overwritten(self):
        source = self.payload({'file': {'path': 'before/receipt.json'}})
        taken = self.base / 'taken.json'
        taken.write_text('keep', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            fill_hashes(source, taken)
        self.assertEqual(taken.read_text(encoding='utf-8'), 'keep')

    def test_evidence_root_selects_another_base(self):
        source = self.payload({'file': {'path': 'receipt.json'}})
        fill_hashes(source, self.base / 'rooted.json', base=self.base / 'before')
        self.assertEqual(read_json(self.base / 'rooted.json')['file']['sha256'], file_hash(self.receipt))

    @unittest.skipUnless(sys.platform == 'win32', 'Directory junctions are a Windows feature')
    def test_destination_through_a_junction_is_rejected(self):
        import _winapi
        source = self.payload({'file': {'path': 'before/receipt.json'}})
        (self.base / 'real').mkdir()
        link = self.base / 'link'
        _winapi.CreateJunction(str(self.base / 'real'), str(link))
        self.addCleanup(lambda: link.exists() and __import__('os').rmdir(link))
        with self.assertRaisesRegex(ValueError, 'Links/reparse points'):
            fill_hashes(source, link / 'filled.json')
        self.assertFalse((self.base / 'real' / 'filled.json').exists())

    def test_cli_prints_summary_and_writes_destination(self):
        source = self.payload({'file': {'path': 'before/receipt.json'}})
        result = subprocess.run([sys.executable, '-m', 'dcc_harness', 'fill-hashes', str(source),
                                 str(self.base / 'cli.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['filled'], ['before/receipt.json'])
        self.assertEqual(read_json(self.base / 'cli.json')['file']['sha256'], file_hash(self.receipt))


if __name__ == '__main__':
    unittest.main()
