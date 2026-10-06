"""Metric cross-section for repeated lapped rectangular panels, without a DCC."""
import math


def lapped_course_profile(roof_pitch, gauge, tile_length, thickness, clearance):
    """Return a shallower tile pitch with a declared normal gap between courses.

    Pitch is radians above horizontal; gauge is measured ALONG the roof slope.
    Other lengths share a unit. Centers advance on a plane parallel to the roof.
    The deck offset is measured along the roof normal from its top plane to a
    tile center. This is rectangular cross-section geometry, not a complete
    roof design, arbitrary-mesh contact solver or building specification.
    """
    values=(roof_pitch,gauge,tile_length,thickness,clearance)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('All profile parameters must be finite numbers')
    if not 0<roof_pitch<math.pi/2 or min(gauge,tile_length,thickness)<=0 or clearance<0:
        raise ValueError('Require an upward roof pitch, positive dimensions and nonnegative clearance')
    step=thickness+clearance
    if not math.isfinite(step) or step>=gauge:
        raise ValueError('Thickness plus clearance must be smaller than the course gauge')
    tilt=math.asin(step/gauge)
    tile_pitch=roof_pitch-tilt
    overlap=tile_length-gauge*math.cos(tilt)
    offset=thickness*.5*math.cos(tilt)+tile_length*.5*math.sin(tilt)+clearance
    if tile_pitch<=0 or overlap<=0 or not all(math.isfinite(v) for v in (overlap,offset)):
        raise ValueError('Profile must retain positive uphill pitch and overlap')
    return {'tile_pitch':tile_pitch,'tilt':tilt,'overlap':overlap,
            'normal_step':step,'deck_center_offset':offset}
