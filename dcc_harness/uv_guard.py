"""Narrow comparison guard for Blender's evaluated bevel UV float noise.

Authored UVs remain exact. This does not relax geometry or modifier preservation.
The legacy 2e-7 allowance covers small-coordinate extraction drift. Tiled
coordinates can differ by one float32 step larger than that; version 3 also
allows exactly adjacent float32 values, capped at 1e-6 absolute difference.
Authored UV hashes are still compared exactly.
"""
import math
import struct

UV_NOISE_TOLERANCE = 2e-7
UV_ADJACENT_MAX_DELTA = 1e-6


def _noise(x, y):
    if not math.isfinite(x) or not math.isfinite(y):
        return False
    delta = abs(x - y)
    if delta <= UV_NOISE_TOLERANCE:
        return True
    if delta > UV_ADJACENT_MAX_DELTA:
        return False
    try:
        a, b = struct.pack('!f', x), struct.pack('!f', y)
    except (OverflowError, struct.error):
        return False
    # Native arrays are exact float32 values. Do not round arbitrary supplied
    # doubles into an adjacent pair to admit a larger change.
    if struct.unpack('!f', a)[0] != x or struct.unpack('!f', b)[0] != y:
        return False
    return abs(struct.unpack('!I', a)[0] - struct.unpack('!I', b)[0]) == 1


def evaluated_uv_noise_only(before, after):
    for field in ("source_mesh_hash", "source_uv_hash", "modifier_settings", "geometry_hash", "uv_layers"):
        if field not in before or field not in after or before[field] != after[field]:
            return False
    a, b = before.get("evaluated_uv_values"), after.get("evaluated_uv_values")
    if not isinstance(a, dict) or not isinstance(b, dict) or a.keys() != b.keys():
        return False
    for name in a:
        if len(a[name]) != len(b[name]):
            return False
        for x, y in zip(a[name], b[name]):
            if not _noise(x, y):
                return False
    return True
