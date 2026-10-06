"""Bounded terrain extension outside a protected square, in scene units.

These scalar recipes do not sample support or certify mesh intersections.
Apply in a declared coordinate frame; verify protected native geometry and UVs.
"""
import math


def _finite(*values):
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Terrain parameters must be finite numbers')


def expand_axis(value, protected_extent, source_extent, target_extent):
    """Expand either side of an axis with unchanged coordinates inside the core.

    The mapping is monotonic, odd, and has derivative one at the core edge.
    Extents are positive half-widths; input must lie inside the source extent.
    """
    _finite(value, protected_extent, source_extent, target_extent)
    if not 0 < protected_extent < source_extent <= target_extent or abs(value) > source_extent:
        raise ValueError('Require 0 < protected < source <= target and a bounded coordinate')
    if abs(value) <= protected_extent:
        return value
    t = (abs(value) - protected_extent) / (source_extent - protected_extent)
    result = abs(value) + (target_extent - source_extent) * t * t
    if not math.isfinite(result):
        raise ValueError('Terrain expansion overflow')
    return math.copysign(result, value)


def surrounding_height(x, y, protected_extent, feather, hills):
    """Nonnegative Gaussian landforms fading to zero at a protected square.

    Each hill is (center_x, center_y, radius_x, radius_y, height). Radii are
    Gaussian standard deviations. Returned value is an elevation DELTA to add
    to the existing surface, not a measured ground height.
    """
    _finite(x, y, protected_extent, feather)
    if protected_extent <= 0 or feather <= 0 or not isinstance(hills, (list, tuple)) or not hills:
        raise ValueError('Positive core/feather and at least one hill are required')
    for hill in hills:
        if not isinstance(hill, (list, tuple)) or len(hill) != 5:
            raise ValueError('A hill needs center XY, radii XY and height')
        _finite(*hill)
        if hill[2] <= 0 or hill[3] <= 0 or hill[4] < 0:
            raise ValueError('Hill radii must be positive and height nonnegative')
    distance = max(abs(x), abs(y)) - protected_extent
    if distance <= 0:
        return 0.0
    t = min(1.0, distance / feather)
    weight = t*t*(3-2*t)
    height = 0.0
    for cx, cy, rx, ry, amplitude in hills:
        nx, ny = (x-cx)/rx, (y-cy)/ry
        # Multiplication can produce inf safely: exp(-inf) means a distant hill.
        height += amplitude * math.exp(-.5*(nx*nx + ny*ny))
    result = weight * height
    if not math.isfinite(result):
        raise ValueError('Landform height overflow')
    return result
