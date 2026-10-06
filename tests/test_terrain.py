import math
import unittest

from dcc_harness.terrain import expand_axis, surrounding_height


class TerrainTests(unittest.TestCase):
    def test_core_and_outer_boundary_are_exact(self):
        for x in (-16, -3.5, 0, 7, 16):
            self.assertEqual(expand_axis(x, 16, 40, 180), x)
        for sign in (-1, 1):
            self.assertEqual(expand_axis(sign*40, 16, 40, 180), sign*180)

    def test_expansion_cannot_fold_grid_and_is_symmetric(self):
        values = [expand_axis(x/10, 16, 40, 180) for x in range(-400, 401)]
        self.assertTrue(all(b > a for a, b in zip(values, values[1:])))
        self.assertEqual(values, [-x for x in reversed(values)])
        eps = 1e-5
        self.assertAlmostEqual((expand_axis(16+eps, 16, 40, 180)-16)/eps, 1, places=4)

    def test_landform_preserves_core_and_has_smooth_join(self):
        hills = [(0, 40, 30, 20, 5)]
        for x, y in ((0, 0), (16, 16), (-16, 8), (3, -16)):
            self.assertEqual(surrounding_height(x, y, 16, 10, hills), 0)
        eps = 1e-5
        self.assertLess(surrounding_height(0, 16+eps, 16, 10, hills)/eps, 1e-4)

    def test_hills_have_metric_peak_and_never_lower_surface(self):
        hills = [(4, 50, 12, 15, 7)]
        self.assertAlmostEqual(surrounding_height(4, 50, 16, 10, hills), 7)
        self.assertAlmostEqual(surrounding_height(16, 50, 16, 10, hills), 7*math.exp(-.5))
        for x in range(-80, 81, 8):
            for y in range(-80, 81, 8):
                self.assertGreaterEqual(surrounding_height(x, y, 16, 10, hills), 0)

    def test_invalid_parameters_are_rejected_even_inside_core(self):
        for args in ((0, 16, 16, 180), (0, 16, 40, 30), (41, 16, 40, 180),
                     (True, 16, 40, 180), (0, -1, 40, 180), (float('nan'), 16, 40, 180)):
            with self.assertRaises(ValueError): expand_axis(*args)
        for hills in ([], [(0, 50, 0, 12, 3)], [(0, 50, 12, 12, -1)],
                      [(0, 50, 12, 12, float('inf'))], [(0, 50)]):
            with self.assertRaises(ValueError): surrounding_height(0, 0, 16, 10, hills)


if __name__ == '__main__':
    unittest.main()
