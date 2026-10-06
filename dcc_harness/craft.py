"""Small metric construction recipes, independent of the DCC runtime."""
import math


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def wall_sections(width, height, depth, openings):
    """Partition a rectangular wall around rectangular door/window apertures.

    Local X runs left to right from 0 to width; Z starts at the floor. An
    opening is {x, z, width, height}, measured from its lower-left corner.
    Returns touching cuboids, not a welded/manifold single wall or a boolean.
    """
    if not all(_positive(v) for v in (width, height, depth)):
        raise ValueError('Wall dimensions must be finite and positive')
    rects = []
    for o in openings:
        if set(o) != {'x', 'z', 'width', 'height'}:
            raise ValueError('Openings require x, z, width, height')
        if not all(type(o[k]) in (int, float) and math.isfinite(o[k]) for k in o):
            raise ValueError('Opening coordinates must be finite numbers')
        x, z, w, h = (o[k] for k in ('x', 'z', 'width', 'height'))
        if not _positive(w) or not _positive(h) or x < 0 or z < 0 or x+w > width or z+h > height:
            raise ValueError('Opening falls outside wall or has nonpositive size')
        r = (x, z, x+w, z+h)
        if any(min(r[2], p[2]) > max(r[0], p[0]) and min(r[3], p[3]) > max(r[1], p[1]) for p in rects):
            raise ValueError('Overlapping openings require an explicit combined design')
        rects.append(r)
    xs = sorted({0, width, *(v for r in rects for v in (r[0], r[2]))})
    zs = sorted({0, height, *(v for r in rects for v in (r[1], r[3]))})
    sections = []
    for loz, hiz in zip(zs, zs[1:]):
        for lox, hix in zip(xs, xs[1:]):
            x, z = (lox+hix)/2, (loz+hiz)/2
            if any(r[0] < x < r[2] and r[1] < z < r[3] for r in rects):
                continue
            sections.append({'center': [x, 0, z], 'dimensions': [hix-lox, depth, hiz-loz]})
    if not sections:
        raise ValueError('Openings remove the whole wall')
    return sections
