"""Private fresh-process worker for uv_report.py; never run in an artist editor and never saves.

For each mesh object with a stable ID: evaluated triangles on the active render UV layer, world
and UV areas, a grid estimate of UV self-overlap, the share of UV area outside the unit square and
the largest texture its materials use.
"""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
import numpy as np
from dcc_harness.evidence import file_hash, read_json, write_json

GRID = 256
OVERLAP_BUDGET = 200_000  # triangles; above this the overlap estimate is skipped and said so
SMALL = 4                 # triangles spanning at most SMALL x SMALL cells are rasterized together


def texture_px(obj):
    sizes = []
    for slot in obj.material_slots:
        tree = slot.material.node_tree if slot.material and slot.material.use_nodes else None
        for node in (tree.nodes if tree else []):
            image = getattr(node, 'image', None)
            if image is not None and image.size[0] and image.size[1]:
                sizes.append(max(image.size))
    return max(sizes) if sizes else None


def overlap(uv):
    """Share of covered grid cells that more than one triangle covers, sampling cell centres."""
    low, high = uv.reshape(-1, 2).min(axis=0), uv.reshape(-1, 2).max(axis=0)
    span = np.maximum(high - low, 1e-9)
    cells = (uv - low) / span * GRID                     # triangles in grid units, shape (n, 3, 2)
    counts = np.zeros((GRID, GRID), dtype=np.int32)
    lo = np.clip(np.floor(cells.min(axis=1)).astype(int), 0, GRID - 1)
    hi = np.clip(np.floor(cells.max(axis=1)).astype(int), 0, GRID - 1)
    size = hi - lo + 1
    small = (size[:, 0] <= SMALL) & (size[:, 1] <= SMALL)

    def inside(tri, px, py):
        ax, ay, bx, by, cx, cy = (tri[..., k, d] for k in range(3) for d in range(2))
        d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
        d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
        d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
        # Strictly inside: a centre on an edge shared by two triangles is counted by neither, never twice.
        return ((d1 > 0) & (d2 > 0) & (d3 > 0)) | ((d1 < 0) & (d2 < 0) & (d3 < 0))

    if small.any():
        tris, base = cells[small], lo[small]
        offsets = np.stack(np.meshgrid(np.arange(SMALL), np.arange(SMALL), indexing='ij'), -1).reshape(-1, 2)
        ix = base[:, None, 0] + offsets[None, :, 0]
        iy = base[:, None, 1] + offsets[None, :, 1]
        keep = (ix <= hi[small][:, None, 0]) & (iy <= hi[small][:, None, 1])
        hit = keep & inside(tris[:, None], ix + 0.5, iy + 0.5)
        np.add.at(counts, (ix[hit], iy[hit]), 1)
    for index in np.nonzero(~small)[0]:
        xs, ys = np.meshgrid(np.arange(lo[index, 0], hi[index, 0] + 1), np.arange(lo[index, 1], hi[index, 1] + 1), indexing='ij')
        hit = inside(cells[index], xs + 0.5, ys + 0.5)
        counts[xs[hit], ys[hit]] += 1
    covered = int((counts >= 1).sum())
    return round(float((counts >= 2).sum()) / covered, 6) if covered else 0.0


def measure(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        layer = next((l for l in mesh.uv_layers if l.active_render), None) or mesh.uv_layers.active
        mesh.calc_loop_triangles()
        n = len(mesh.loop_triangles)
        record = {'uv_layer': layer.name if layer else None, 'triangles': n, 'texture_px': texture_px(obj)}
        if layer is None or n == 0:
            return {**record, 'world_area': 0.0, 'uv_area': 0.0, 'uv_per_m': None, 'overlap': None, 'outside': 0.0,
                    'overlap_note': 'no UV layer' if layer is None else 'no triangles'}
        loops = np.empty(n * 3, dtype=np.int64); mesh.loop_triangles.foreach_get('loops', loops)
        vertex_of_loop = np.empty(len(mesh.loops), dtype=np.int64); mesh.loops.foreach_get('vertex_index', vertex_of_loop)
        co = np.empty(len(mesh.vertices) * 3); mesh.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        matrix = np.array(evaluated.matrix_world)
        world = co @ matrix[:3, :3].T + matrix[:3, 3]
        uv = np.empty(len(mesh.loops) * 2); layer.data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2)
        tri_world = world[vertex_of_loop[loops]].reshape(n, 3, 3)
        tri_uv = uv[loops].reshape(n, 3, 2)
        world_areas = 0.5 * np.linalg.norm(np.cross(tri_world[:, 1] - tri_world[:, 0], tri_world[:, 2] - tri_world[:, 0]), axis=1)
        e1, e2 = tri_uv[:, 1] - tri_uv[:, 0], tri_uv[:, 2] - tri_uv[:, 0]
        uv_areas = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
        world_area, uv_area = float(world_areas.sum()), float(uv_areas.sum())
        centres = tri_uv.mean(axis=1)
        outside_mask = (centres < 0).any(axis=1) | (centres > 1).any(axis=1)
        record.update(world_area=round(world_area, 6), uv_area=round(uv_area, 9),
                      uv_per_m=round(float(np.sqrt(uv_area / world_area)), 6) if world_area > 0 else None,
                      outside=round(float(uv_areas[outside_mask].sum() / uv_area), 6) if uv_area > 0 else 0.0)
        if n > OVERLAP_BUDGET:
            record.update(overlap=None, overlap_note=f'over the {OVERLAP_BUDGET}-triangle budget')
        else:
            record.update(overlap=overlap(tri_uv), overlap_note=None)
        return record
    finally:
        evaluated.to_mesh_clear()


def main():
    if not bpy.app.background:
        raise RuntimeError('UV measurement requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'measure':
        raise ValueError('Unknown UV worker action')
    request = read_json(request_path)
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = {}
    for obj in bpy.context.scene.objects:
        iid = obj.get('dcc_instance_id')
        if obj.type == 'MESH' and isinstance(iid, str) and iid:
            objects[iid] = measure(obj, depsgraph)
    write_json(Path(request['out']) / 'measurement.json', {'schema': 'dcc.uv.measurement.v1', 'checkpoint_sha256': source['sha256'],
                                                           'grid': GRID, 'overlap_budget': OVERLAP_BUDGET, 'objects': objects})


main()
