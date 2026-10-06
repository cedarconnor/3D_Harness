"""Metric, seeded broadleaf studies; not a botanical or collision simulator.

Structure is independent of Blender. Parent indices and attachment fractions
make the intended branch/petiole connections testable before meshing.
"""
import math
import random


def _metric(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(a, value):
    return tuple(x * value for x in a)


def _lerp(a, b, t):
    return _add(_mul(a, 1 - t), _mul(b, t))


def leaf_surface(length=.055, width=.024, *, arch=.09, droop=.12, segments=6):
    """Return a single-sided curved leaf, base at origin, length along +Y.

    Dimensions are meters; arch/droop are length fractions. Each vertex has
    explicit 0..1 UVs. Open edges are intentional, not a watertight mesh.
    Width describes the envelope; the sampled surface may be slightly narrower.
    """
    _metric(length, 'length')
    _metric(width, 'width')
    if type(segments) is not int or not 3 <= segments <= 32:
        raise ValueError('segments must be an integer from 3 to 32')
    if any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1 for x in (arch, droop)):
        raise ValueError('arch and droop must be finite fractions in [-1, 1]')
    vertices, uvs, faces = [(0., 0., 0.)], [(.5, 0.)], []
    for i in range(1, segments):
        t = i / segments
        half = width * .5 * math.sin(math.pi * t) ** .8
        z = length * (arch * math.sin(math.pi * t) - droop * t * t)
        vertices.extend([(-half, length*t, z-half*.16), (0., length*t, z), (half, length*t, z-half*.16)])
        uvs.extend([(0., t), (.5, t), (1., t)])
    tip = len(vertices)
    vertices.append((0., length, -length*droop)); uvs.append((.5, 1.))
    faces.extend([(0, 2, 1), (0, 3, 2)])
    for i in range(segments - 2):
        a, b = 1 + i*3, 4 + i*3
        faces.extend([(a, a+1, b), (a+1, b+1, b), (a+1, a+2, b+1), (a+2, b+2, b+1)])
    a = tip - 3
    faces.extend([(a, a+1, tip), (a+1, a+2, tip)])
    return {'vertices': vertices, 'faces': faces, 'uvs': uvs}


def shrub_structure(seed=41, height=1.2, *, leaf_scale=1.0):
    """A seven-cane garden shrub study with attached shoots and petioles.

    Height is the woody leader height, not the final leaf-inclusive bounding
    box. Leaf size stays at about 3.8..7.5 cm across shrub heights. Supported study
    scale is 0.6..2 m. A local RNG never changes the caller's random state.
    leaf_scale (0.5..1.5) changes the blades without moving their attachments
    or adding polygons; assess crown coverage in the destination scene.
    """
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    _metric(height, 'height')
    if not .6 <= height <= 2:
        raise ValueError('height must be within the qualified study range 0.6..2 m')
    _metric(leaf_scale, 'leaf_scale')
    if not .5 <= leaf_scale <= 1.5:
        raise ValueError('leaf_scale must be within 0.5..1.5')
    rng = random.Random(seed)
    stems, leaves = [], []

    def stem(parent, t, end, radius, kind, end_radius=None):
        start = (0., 0., 0.) if parent is None else _lerp(stems[parent]['start'], stems[parent]['end'], t)
        index = len(stems)
        stems.append({'parent': parent, 'attachment': t, 'start': start, 'end': end,
                      'radius': radius, 'end_radius': radius*.5 if end_radius is None else end_radius, 'kind': kind})
        return index

    for cane in range(7):
        angle = cane * math.tau / 7 + rng.uniform(-.23, .23)
        top = (math.cos(angle)*height*.22, math.sin(angle)*height*.22, height*rng.uniform(.88, 1.))
        breaks = [0., .46, .76, 1.]
        leaders = []
        for part in range(3):
            t = breaks[part+1]
            bend = (top[0]*t*t, top[1]*t*t, top[2]*t)
            leaders.append(stem(leaders[-1] if leaders else None, 1., bend,
                                height*(.009, .005, .0025)[part], 'leader',
                                height*(.005, .0025, .0005)[part]))
        for tier in range(6):
            global_t = .23 + tier*.139 + rng.uniform(-.02, .02)
            part = next(i for i in range(3) if global_t <= breaks[i+1])
            leader = leaders[part]
            t = (global_t-breaks[part])/(breaks[part+1]-breaks[part])
            start = _lerp(stems[leader]['start'], stems[leader]['end'], t)
            azimuth = angle + rng.uniform(-.7, .7) + (tier % 2 - .5)*.8
            reach = height * (.32 - tier*.023) * rng.uniform(.85, 1.15)
            end = _add(start, (math.cos(azimuth)*reach, math.sin(azimuth)*reach, reach*.43))
            branch = stem(leader, t, end, height*.004, 'branch')
            for twig in range(5):
                fraction = .18 + twig*.20
                twig_start = _lerp(start, end, fraction)
                heading = azimuth + (1 if twig % 2 else -1)*rng.uniform(.65, 1.15)
                reach2 = height*rng.uniform(.13, .21)
                twig_end = _add(twig_start, (math.cos(heading)*reach2, math.sin(heading)*reach2, reach2*rng.uniform(.35, .8)))
                shoot = stem(branch, fraction, twig_end, .0015, 'shoot')
                for node in range(10):
                    attach = .12 + node*.095
                    base = _lerp(twig_start, twig_end, attach)
                    leaf_angle = heading + (1 if node % 2 else -1)*rng.uniform(.8, 1.4)
                    elevation = rng.uniform(-.12, .62)
                    direction = (math.cos(leaf_angle)*math.cos(elevation), math.sin(leaf_angle)*math.cos(elevation), math.sin(elevation))
                    petiole_end = _add(base, _mul(direction, rng.uniform(.005, .009)))
                    petiole = stem(shoot, attach, petiole_end, .00045, 'petiole')
                    length = rng.uniform(.045, .075) * (1 - node*.018) * leaf_scale
                    leaves.append({'parent': petiole, 'base': petiole_end, 'direction': direction,
                                   'length': length, 'width': length*rng.uniform(.45, .62),
                                   'arch': rng.uniform(.055, .13), 'droop': rng.uniform(.04, .20),
                                   'shade': rng.randrange(4)})
    return {'schema': 'dcc.shrub-study.v1', 'seed': seed, 'height': height, 'leaf_scale': leaf_scale, 'stems': stems, 'leaves': leaves}
