"""Portable checks for review-sheet: the PNG writer and reader, argument refusals and the CLI."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dcc_harness import review_sheet


class PngTests(unittest.TestCase):
    def test_pixels_survive_a_round_trip_and_equal_pixels_give_equal_bytes(self):
        pixels = bytes(range(256)) * 3 + bytes(96)          # 12 x 24 RGB
        data = review_sheet.encode_png(12, 24, pixels)
        self.assertEqual(review_sheet.decode_png(data), (12, 24, pixels))
        self.assertEqual(data, review_sheet.encode_png(12, 24, pixels))
        self.assertNotIn(b'tEXt', data)

    def test_wrong_sizes_and_other_images_are_refused(self):
        with self.assertRaises(ValueError):
            review_sheet.encode_png(2, 2, bytes(11))
        with self.assertRaises(ValueError):
            review_sheet.decode_png(b'GIF89a')
        truncated = review_sheet.encode_png(2, 2, bytes(12))[:-30]
        with self.assertRaises(Exception):
            review_sheet.decode_png(truncated)


class ArgumentTests(unittest.TestCase):
    def test_bad_arguments_are_refused_before_blender_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'scene.blend'
            source.write_bytes(b'BLENDER')
            out = Path(folder) / 'out'
            cases = [{'views': 5}, {'colour': 'rainbow'}, {'width': 200}, {'width': 4000}, {'width': True}, {'targets': ['a', 'a']}, {'targets': ['']}]
            for options in cases:
                with self.subTest(options), self.assertRaises(ValueError):
                    review_sheet.sheet_file(source, out, 'blender', **options)
            self.assertFalse(out.exists())
            with self.assertRaises(ValueError):
                review_sheet.sheet_file(Path(folder) / 'absent.blend', out, 'blender')

    def test_every_row_says_what_it_shows(self):
        self.assertEqual(list(review_sheet.ROWS), ['silhouette', 'clay', 'wireframe', 'backface'])
        self.assertTrue(all(review_sheet.ROWS.values()))

    def test_cli_lists_the_command(self):
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'review-sheet', '--help'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        for option in ('--targets', '--views', '--color', '--width'):
            self.assertIn(option, proc.stdout)


if __name__ == '__main__':
    unittest.main()
