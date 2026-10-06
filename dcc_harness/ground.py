"""Plan-view distances for declared working/circulation corridors, in meters.

These masks support material transitions and scatter exclusion. They do not
establish navigability, surface contact, or clearance from undeclared objects.
"""
import math


def _point(value):
    if not isinstance(value,(list,tuple)) or len(value)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):
        raise ValueError('Expected two finite numeric coordinates')
    return tuple(value)


def corridor_distance(point, path):
    """Distance to a polyline, including rounded end caps and corners."""
    x,y=_point(point)
    if not isinstance(path,(list,tuple)) or len(path)<2:
        raise ValueError('A corridor needs at least two points')
    path=[_point(p) for p in path]
    distances=[]
    for (ax,ay),(bx,by) in zip(path,path[1:]):
        dx,dy=bx-ax,by-ay;length2=dx*dx+dy*dy
        if not math.isfinite(length2):raise ValueError('Corridor coordinates overflow')
        if length2==0:continue
        t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/length2))
        distance=math.hypot(x-ax-t*dx,y-ay-t*dy)
        if not math.isfinite(distance):raise ValueError('Distance overflow')
        distances.append(distance)
    if not distances:raise ValueError('A corridor needs a nonzero segment')
    return min(distances)


def corridor_mask(point, path, half_width, feather):
    """One inside the cleared core, smoothly falling to zero outside its edge."""
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (half_width,feather)):
        raise ValueError('Half width and feather must be finite and positive')
    t=max(0,min(1,(corridor_distance(point,path)-half_width)/feather))
    return 1-t*t*(3-2*t)
