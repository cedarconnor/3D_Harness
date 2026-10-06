"""Read-only opaque-geometry visibility samples in a saved Blender scene.

This measures primary geometric occlusion, not rendered alpha, refraction,
volumes, motion blur, depth of field, perception or exact pixel coverage.
"""
from collections import Counter
import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .evidence import file_hash


def _included_objects(scene):
    # Respect render-disabled collections and excluded view-layer branches.
    included = set()
    def visit(layer, hidden=False):
        hidden = hidden or layer.exclude or layer.collection.hide_render
        if not hidden:
            included.update(layer.collection.objects)
        for child in layer.children:
            visit(child, hidden)
    visit(bpy.context.view_layer.layer_collection)
    return [o for o in scene.objects if o in included and not o.hide_render and getattr(o, 'visible_camera', True)]


class GeometryVisibility:
    """One evaluated triangle snapshot, reusable for several fixed-view queries."""
    def __init__(self):
        self.scene = bpy.context.scene
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        if any(instance.is_instance for instance in deps.object_instances):
            raise ValueError('Instanced geometry is not covered by this visibility version')
        self.parts = {}
        vertices, faces, self.owners = [], [], []
        for obj in _included_objects(self.scene):
            if obj.type in ('CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME', 'POINTCLOUD'):
                raise ValueError(f'Unsupported potential occluder: {obj.name} ({obj.type})')
            if obj.type != 'MESH':
                continue
            # This depsgraph is evaluated for the viewport, even in background
            # Blender. Never present a divergent viewport mesh as render proof.
            if not obj.visible_get(view_layer=bpy.context.view_layer):
                raise ValueError(f'Render-visible mesh is viewport-hidden: {obj.name}')
            if obj.show_instancer_for_render != obj.show_instancer_for_viewport:
                raise ValueError(f'Instancer display differs for render: {obj.name}')
            for modifier in obj.modifiers:
                if modifier.show_render != modifier.show_viewport:
                    raise ValueError(f'Modifier viewport/render visibility differs: {obj.name}/{modifier.name}')
                if modifier.show_render and modifier.type not in {
                        'BEVEL', 'WEIGHTED_NORMAL', 'SOLIDIFY', 'ARRAY', 'MIRROR', 'TRIANGULATE'}:
                    raise ValueError(f'Modifier render equivalence is not covered: {obj.name}/{modifier.type}')
            iid = obj.get('dcc_instance_id')
            if not isinstance(iid, str) or not iid or iid in self.parts:
                raise ValueError('Visible meshes require distinct dcc_instance_id values')
            evaluated = obj.evaluated_get(deps)
            mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
            try:
                mesh.calc_loop_triangles()
                points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
                if any(not math.isfinite(x) for p in points for x in p):
                    raise ValueError('Nonfinite visibility geometry')
                triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
                self.parts[iid] = (points, triangles)
                offset = len(vertices)
                vertices.extend(points)
                faces.extend(tuple(i + offset for i in tri) for tri in triangles)
                self.owners.extend([iid] * len(triangles))
            finally:
                evaluated.to_mesh_clear()
        if not faces:
            raise ValueError('No visible triangles')
        self.tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)

    def measure(self, camera_id, target_ids, grid=64):
        if type(grid) is not int or not 8 <= grid <= 256:
            raise ValueError('Grid must be an integer from 8 to 256')
        if not isinstance(target_ids, list) or not target_ids or len(set(target_ids)) != len(target_ids):
            raise ValueError('Specify distinct target IDs')
        cameras = [o for o in self.scene.objects if o.get('dcc_instance_id') == camera_id and o.type == 'CAMERA']
        if len(cameras) != 1 or cameras[0].data.type not in ('PERSP', 'ORTHO'):
            raise ValueError('Exactly one perspective or orthographic camera is required')
        camera = cameras[0]
        if any(abs(v - 1) > 1e-6 for v in camera.matrix_world.to_scale()):
            raise ValueError('Scaled cameras are not supported by this visibility version')
        if any(i not in self.parts for i in target_ids):
            raise ValueError('Missing or render-excluded visibility target')
        points, triangles = [], []
        for iid in target_ids:
            vertices, faces = self.parts[iid]
            offset = len(points)
            points.extend(vertices)
            triangles.extend(tuple(i + offset for i in tri) for tri in faces)
        if not triangles:
            raise ValueError('Visibility target has no triangles')
        projected = [world_to_camera_view(self.scene, camera, p) for p in points]
        if any(p.z <= camera.data.clip_start for p in projected):
            raise ValueError('Target crosses or lies behind the near plane; unsupported ROI')
        roi = [max(0.0, min(p.x for p in projected)), max(0.0, min(p.y for p in projected)),
               min(1.0, max(p.x for p in projected)), min(1.0, max(p.y for p in projected))]
        if roi[0] >= roi[2] or roi[1] >= roi[3]:
            raise ValueError('Visibility target is outside the camera frame')
        target_tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
        frame = camera.data.view_frame(scene=self.scene)
        xmin, xmax = min(p.x for p in frame), max(p.x for p in frame)
        ymin, ymax = min(p.y for p in frame), max(p.y for p in frame)
        rotation = camera.matrix_world.to_quaternion()
        target_hits, visible = 0, 0
        blockers = Counter()
        for iy in range(grid):
            v = roi[1] + (iy + .5) / grid * (roi[3] - roi[1])
            for ix in range(grid):
                u = roi[0] + (ix + .5) / grid * (roi[2] - roi[0])
                x, y = xmin + u * (xmax - xmin), ymin + v * (ymax - ymin)
                if camera.data.type == 'PERSP':
                    local = Vector((x, y, frame[0].z)).normalized()
                    origin = camera.matrix_world.translation.copy()
                else:
                    local = Vector((0, 0, -1))
                    origin = camera.matrix_world @ Vector((x, y, 0))
                direction = rotation @ local
                near = camera.data.clip_start / -local.z
                distance = (camera.data.clip_end - camera.data.clip_start) / -local.z
                origin += direction * near
                hit = target_tree.ray_cast(origin, direction, distance)
                if hit[2] is None:
                    continue
                target_hits += 1
                full = self.tree.ray_cast(origin, direction, distance)
                if full[2] is None:
                    raise RuntimeError('Target hit absent from complete geometry snapshot')
                owner = self.owners[full[2]]
                if owner in target_ids:
                    visible += 1
                else:
                    blockers[owner] += 1
        if not target_hits:
            raise ValueError('No sampled target coverage; do not treat as fully visible')
        return {'camera_id': camera_id, 'target_ids': target_ids, 'grid': grid,
                'target_samples': target_hits, 'visible_samples': visible,
                'visible_fraction': visible / target_hits, 'blockers': dict(blockers), 'roi': roi,
                'camera_matrix': [list(row) for row in camera.matrix_world],
                'camera_type': camera.data.type, 'frame': self.scene.frame_current}


def observe_visibility(queries, observation):
    if bpy.data.is_dirty or not bpy.data.filepath:
        raise ValueError('Visibility receipt requires a saved, unmodified native checkpoint')
    sha = file_hash(bpy.data.filepath)
    if observation['checkpoint_sha256'] != sha:
        raise ValueError('Observation belongs to a different checkpoint')
    snapshot = GeometryVisibility()
    results = {}
    for key, query in queries.items():
        if set(query) != {'camera_id', 'target_ids', 'grid'}:
            raise ValueError('Unsupported visibility query')
        results[key] = snapshot.measure(**query)
    return {'schema': 'dcc.visibility.v1', 'checkpoint_sha256': sha, 'revision': observation['revision'],
            'native_dirty': False, 'queries': results, 'blender': bpy.app.version_string,
            'limits': 'Opaque evaluated triangles and primary camera rays on a uniform projected-ROI grid. Render/viewport visibility differences and unsupported modifiers are rejected. Excludes material alpha/transmission, volumes, motion blur, DOF, instances, perception and unsampled features.'}
