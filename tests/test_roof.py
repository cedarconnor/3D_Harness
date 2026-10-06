import math
import unittest
from dcc_harness.roof import lapped_course_profile


class RoofProfileTests(unittest.TestCase):
    def test_actual_cross_sections_have_overlap_and_declared_gaps(self):
        for pitch,gauge,length,thick,gap in [(math.radians(21),.31,.45,.006,.0008),
                                           (math.radians(40),.24,.40,.012,.0015),
                                           (math.radians(12),.4,.60,.008,0)]:
            profile=lapped_course_profile(pitch,gauge,length,thick,gap)
            angle=profile['tile_pitch'];tangent=(math.cos(angle),math.sin(angle));normal=(-math.sin(angle),math.cos(angle))
            roof_normal=(-math.sin(pitch),math.cos(pitch))
            centers=[(roof_normal[0]*profile['deck_center_offset']+i*gauge*math.cos(pitch),
                      roof_normal[1]*profile['deck_center_offset']+i*gauge*math.sin(pitch)) for i in range(3)]
            panels=[[(c[0]+a*length/2*tangent[0]+b*thick/2*normal[0],c[1]+a*length/2*tangent[1]+b*thick/2*normal[1]) for a in (-1,1) for b in (-1,1)] for c in centers]
            dot=lambda p,v:sum(x*y for x,y in zip(p,v))
            for lo,hi in zip(panels,panels[1:]):
                self.assertAlmostEqual(min(dot(p,normal) for p in hi)-max(dot(p,normal) for p in lo),gap)
                self.assertGreater(min(max(dot(p,tangent) for p in lo),max(dot(p,tangent) for p in hi))-max(min(dot(p,tangent) for p in lo),min(dot(p,tangent) for p in hi)),0)
            self.assertAlmostEqual(min(dot(p,roof_normal) for panel in panels for p in panel),gap)

    def test_uniform_scale_preserves_angles_and_scales_distances(self):
        a=lapped_course_profile(.4,.3,.45,.006,.001)
        b=lapped_course_profile(.4,3,4.5,.06,.01)
        for key in ('tile_pitch','tilt'):self.assertAlmostEqual(a[key],b[key])
        for key in ('overlap','normal_step','deck_center_offset'):self.assertAlmostEqual(a[key]*10,b[key])

    def test_original_coplanar_layout_is_not_a_valid_lap(self):
        pitch=math.atan2(.84,2.2);advance=(.29,.29*math.tan(pitch))
        separation=-advance[0]*math.sin(pitch)+advance[1]*math.cos(pitch)
        self.assertLess(separation-.022,0)
        repaired=lapped_course_profile(pitch,math.hypot(*advance),.45,.006,.0008)
        self.assertLess(repaired['tile_pitch'],pitch)
        self.assertGreater(repaired['overlap'],.13)

    def test_refuse_invalid_or_unlappable_profiles(self):
        for args in [(0,.3,.45,.006,.001),(.4,0,.45,.006,.001),(.4,.3,.1,.006,.001),
                     (.4,.3,.45,.3,0),(.01,.3,.45,.006,.001),(.4,.3,.45,.006,-1),
                     (math.pi/2,.3,.45,.006,0),(True,.3,.45,.006,0),(.4,.3,float('nan'),.006,0)]:
            with self.assertRaises(ValueError):lapped_course_profile(*args)
