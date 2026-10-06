"""Explicit world-space support snapshots of evaluated Blender mesh surfaces."""
import math


class SurfaceSampler:
    """Read-only BVH snapshot of explicitly supplied mesh objects.

    Snapshot geometry includes evaluated modifiers and world transforms. Rebuild
    after editing a supplied surface. No scene-wide fallback or zero-height
    fallback: missing support returns None. This is a ray sample, not collision
    or footprint support certification.
    """
    def __init__(self, objects):
        import bpy
        from mathutils.bvhtree import BVHTree
        objects=list(objects)
        ids=[o.get('dcc_instance_id') for o in objects]
        if not objects or any(o.type!='MESH' for o in objects) or any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Supply nonempty mesh surfaces with unique stable identities')
        deps=bpy.context.evaluated_depsgraph_get();self._surfaces=[]
        for obj,iid in zip(objects,ids):
            evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
            try:
                points=[evaluated.matrix_world@v.co for v in mesh.vertices]
                if not points or not mesh.polygons or any(not math.isfinite(c) for p in points for c in p):
                    raise ValueError('Support surface must have finite polygonal geometry')
                tree=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in mesh.polygons])
                self._surfaces.append((iid,tree))
            finally:evaluated.to_mesh_clear()

    def sample(self, x, y, *, top=10., bottom=-10.):
        from mathutils import Vector
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,y,top,bottom)) or top<=bottom:
            raise ValueError('Require finite coordinates and top > bottom')
        hits=[]
        for iid,tree in self._surfaces:
            point,normal,face,distance=tree.ray_cast(Vector((x,y,top)),Vector((0,0,-1)),top-bottom)
            if point is not None:
                hits.append({'surface':iid,'position':tuple(point),'normal':tuple(normal),'distance':distance})
        return min(hits,key=lambda h:h['distance']) if hits else None
