import unittest
from dcc_harness.craft import wall_sections


class ConstructionTests(unittest.TestCase):
    def test_openings_empty_and_volume_conserved_across_revision(self):
        for door_width in (.95, 1.2):
            openings = [{'x': 4, 'z': 0, 'width': door_width, 'height': 2.1},
                        {'x': .8, 'z': 1.15, 'width': 1.5, 'height': 1.1}]
            panels = wall_sections(6, 3, .24, openings)
            volume = sum(p['dimensions'][0]*p['dimensions'][1]*p['dimensions'][2] for p in panels)
            self.assertAlmostEqual(volume, (18-door_width*2.1-1.5*1.1)*.24)
            for p in panels:
                x, _, z = p['center']
                for o in openings:
                    self.assertFalse(o['x'] < x < o['x']+o['width'] and o['z'] < z < o['z']+o['height'])

    def test_reject_impossible_or_ambiguous_construction(self):
        for openings in ([{'x': 5.5, 'z': 0, 'width': 1, 'height': 2}],
                         [{'x': 0, 'z': 0, 'width': 6, 'height': 3}],
                         [{'x': 1, 'z': 0, 'width': 2, 'height': 2}, {'x': 2, 'z': 0, 'width': 2, 'height': 2}]):
            with self.assertRaises(ValueError):
                wall_sections(6, 3, .24, openings)
        for size in (0, -1, float('nan'), True):
            with self.assertRaises(ValueError):
                wall_sections(size, 3, .24, [])
