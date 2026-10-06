import math
import random
import unittest
from dcc_harness.vegetation import leaf_surface, shrub_structure


class VegetationTests(unittest.TestCase):
    def test_leaf_physical_scale_uvs_and_nonzero_upward_faces(self):
        for segments in (3, 6, 32):
            mesh = leaf_surface(.06, .025, segments=segments)
            self.assertEqual(mesh['vertices'][0], (0., 0., 0.))
            self.assertAlmostEqual(max(v[1] for v in mesh['vertices']), .06)
            self.assertLessEqual(max(v[0] for v in mesh['vertices'])-min(v[0] for v in mesh['vertices']), .025)
            self.assertEqual(len(mesh['uvs']), len(mesh['vertices']))
            self.assertTrue(all(0 <= u <= 1 for uv in mesh['uvs'] for u in uv))
            for face in mesh['faces']:
                a, b, c = [mesh['vertices'][i] for i in face]
                self.assertGreater((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]), 0)

    def test_attached_acyclic_stems_and_leaves_across_scales(self):
        for height in (.6, 1.2, 2):
            tree = shrub_structure(87, height)
            for i, s in enumerate(tree['stems']):
                if s['parent'] is None:
                    self.assertEqual(s['start'], (0., 0., 0.))
                else:
                    self.assertLess(s['parent'], i)
                    parent = tree['stems'][s['parent']]
                    for actual, a, b in zip(s['start'], parent['start'], parent['end']):
                        self.assertAlmostEqual(actual, a*(1-s['attachment'])+b*s['attachment'])
                self.assertTrue(all(math.isfinite(v) for v in (*s['start'], *s['end'], s['radius'])))
                self.assertGreater(math.dist(s['start'], s['end']), 0)
                self.assertGreaterEqual(min(s['start'][2], s['end'][2]), 0)
            for leaf in tree['leaves']:
                self.assertEqual(leaf['base'], tree['stems'][leaf['parent']]['end'])
                self.assertAlmostEqual(sum(v*v for v in leaf['direction']), 1)

    def test_seed_reproduction_without_global_random_mutation(self):
        state = random.getstate()
        a = shrub_structure(41)
        self.assertEqual(a, shrub_structure(41))
        self.assertNotEqual(a, shrub_structure(42))
        self.assertEqual(state, random.getstate())

    def test_leaf_scale_changes_blades_without_moving_attachment_or_adding_geometry(self):
        a, b = shrub_structure(41), shrub_structure(41, leaf_scale=1.4)
        self.assertEqual(a['stems'], b['stems'])
        self.assertEqual(len(a['leaves']),len(b['leaves']))
        for old,new in zip(a['leaves'],b['leaves']):
            self.assertEqual(old['base'],new['base'])
            self.assertAlmostEqual(old['length']*1.4,new['length'])
            self.assertAlmostEqual(old['width']*1.4,new['width'])
        for value in (True,0,.49,1.51,float('nan')):
            with self.assertRaises(ValueError): shrub_structure(leaf_scale=value)

    def test_refuse_invalid_or_unbounded_inputs(self):
        for value in (0, -1, True, float('nan'), float('inf'), '1'):
            with self.assertRaises(ValueError): leaf_surface(length=value)
            with self.assertRaises(ValueError): shrub_structure(height=value)
        for value in (True, 2, 33, 6.5):
            with self.assertRaises(ValueError): leaf_surface(segments=value)
        for value in (float('nan'), 2, True):
            with self.assertRaises(ValueError): leaf_surface(arch=value)
        for value in (True, 1.5, '41'):
            with self.assertRaises(ValueError): shrub_structure(seed=value)
        for value in (.59, 2.01):
            with self.assertRaises(ValueError): shrub_structure(height=value)
