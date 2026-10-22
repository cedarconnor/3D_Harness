"""Private fresh-process worker for relations.py; never run in an artist editor and never saves."""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.ground_blender import SurfaceSampler

REACH = 10.0  # metres above and below each footprint point searched for the support surface


def world_points(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ v.co for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def measure(rule, objects, depsgraph, scale=1.0):
    wanted = rule['subjects'] + rule['support']
    missing = [i for i in wanted if i not in objects or objects[i].type != 'MESH']
    if missing:
        return {'missing': missing, 'subjects': {}}
    sampler = SurfaceSampler([objects[i] for i in rule['support']])
    support_points = {i: world_points(objects[i], depsgraph) for i in rule['support']}
    support_boxes = [(min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts), max(p.z for p in pts))
                     for pts in support_points.values() if pts]
    subjects = {}
    for sid in rule['subjects']:
        points = world_points(objects[sid], depsgraph)
        if not points:
            subjects[sid] = {'footprint_points': 0, 'hits': 0, 'min_distance': None, 'max_distance': None, 'bounds_gap': None}
            continue
        lowest = min(p.z for p in points)
        footprint = {}
        for p in points:
            if p.z <= lowest + rule['footprint'] / scale:
                footprint.setdefault((round(p.x, 6), round(p.y, 6)), p)
        distances = []
        for p in footprint.values():
            hit = sampler.sample(p.x, p.y, top=p.z + REACH / scale, bottom=p.z - REACH / scale)
            if hit is not None:
                distances.append((p.z - hit['position'][2]) * scale)
        x0, x1 = min(p.x for p in points), max(p.x for p in points)
        y0, y1 = min(p.y for p in points), max(p.y for p in points)
        under = [top for bx0, bx1, by0, by1, top in support_boxes if bx0 <= x1 and x0 <= bx1 and by0 <= y1 and y0 <= by1]
        subjects[sid] = {'footprint_points': len(footprint), 'hits': len(distances),
                         'min_distance': min(distances) if distances else None,
                         'max_distance': max(distances) if distances else None,
                         'bounds_gap': (lowest - max(under)) * scale if under else None}
    return {'missing': [], 'subjects': subjects}


def main():
    if not bpy.app.background:
        raise RuntimeError('Relation measurement requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'relations':
        raise ValueError('Unknown relations worker action')
    request = read_json(request_path)
    source, definition = request['source'], request['definition']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed during native open')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = {}
    for obj in bpy.context.scene.objects:
        iid = obj.get('dcc_instance_id')
        if iid in objects:
            raise ValueError(f'Duplicate dcc_instance_id, so a measurement could hide another object: {iid}')
        if iid:
            objects[iid] = obj
    scale = bpy.context.scene.unit_settings.scale_length
    from dcc_harness.evidence import finite_number
    finite_number(scale, nonnegative=True)
    if scale == 0:
        raise ValueError('Scene unit scale must be positive')
    measured = {rule['id']: measure(rule, objects, depsgraph, scale) for rule in definition['relations']}
    write_json(Path(request['out']) / 'measurement.json', {
        'schema': 'dcc.relations.measurement.v1', 'checkpoint_sha256': source['sha256'], 'spec_digest': digest(definition),
        'blender': bpy.app.version_string, 'reach': REACH, 'units': 'metres', 'metres_per_blender_unit': scale, 'relations': measured})
    if file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')


if __name__ == '__main__':
    main()
