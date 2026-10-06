import math
import unittest
from dcc_harness.ground import corridor_distance,corridor_mask


class CorridorTests(unittest.TestCase):
    def test_segments_corners_and_caps(self):
        path=[(0,0),(4,0),(4,3)]
        for point,expected in [((2,1),1),((-1,0),1),((4,4),1),((5,-1),math.sqrt(2)),((4,2),0)]:
            self.assertAlmostEqual(corridor_distance(point,path),expected)
            self.assertAlmostEqual(corridor_distance(point,list(reversed(path))),expected)

    def test_mask_core_transition_and_outer_edge(self):
        path=[(0,0),(5,0)]
        for y,expected in [(0,1),(.5,1),(1,.5),(1.5,0),(2,0)]:
            self.assertAlmostEqual(corridor_mask((2,y),path,.5,1),expected)
        values=[corridor_mask((2,i/100),path,.5,1) for i in range(201)]
        self.assertTrue(all(0<=v<=1 for v in values));self.assertEqual(values,sorted(values,reverse=True))

    def test_translation_and_duplicate_points_do_not_change_distance(self):
        a=corridor_distance((1,2),[(0,0),(0,0),(4,0)])
        b=corridor_distance((101,-48),[(100,-50),(104,-50)])
        self.assertEqual(a,b)

    def test_refuse_ambiguous_nonfinite_and_zero_extent(self):
        for path in ([],[(0,0)],[(1,2),(1,2)],[(0,0),(True,1)],[(0,0),(float('inf'),1)],[(1e308,0),(-1e308,0)]):
            with self.assertRaises(ValueError):corridor_distance((0,0),path)
        for value in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError):corridor_mask((0,0),[(0,0),(1,0)],value,1)
        with self.assertRaises(ValueError):corridor_distance((float('nan'),0),[(0,0),(1,0)])
