"""Private fresh-process worker for blockout.py; never run in an artist editor.

`build` creates the spec's primitives in an owned, tagged collection and saves a new file; the
source, if any, is opened and never written. `measure` reads the bounding box of the objects each
part names in a saved file, in the part's yaw frame, and never saves.
"""
import fnmatch
import hashlib
import json
import math
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
import numpy as np
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.visibility_blender import _included_objects

SEGMENTS, RINGS = 32, 16
BOX = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
GEOMETRY = ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META')


def primitive(kind, w, d, h):
    """Vertices and outward-facing faces at true size, with the origin at the centre of the base."""
    x, y = w / 2, d / 2
    if kind == 'box':
        return [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0), (-x, -y, h), (x, -y, h), (x, y, h), (-x, y, h)], BOX
    if kind == 'plane':
        return [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0)], [(0, 1, 2, 3)]
    if kind == 'wedge':   # a ramp rising toward +Y
        return [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0), (x, y, h), (-x, y, h)], [(0, 3, 2, 1), (2, 3, 5, 4), (0, 1, 4, 5), (0, 5, 3), (1, 2, 4)]
    ring = [(x * math.cos(2 * math.pi * i / SEGMENTS), y * math.sin(2 * math.pi * i / SEGMENTS)) for i in range(SEGMENTS)]
    after = [(i + 1) % SEGMENTS for i in range(SEGMENTS)]
    if kind == 'cylinder':
        vertices = [(a, b, 0) for a, b in ring] + [(a, b, h) for a, b in ring]
        faces = [(i, after[i], SEGMENTS + after[i], SEGMENTS + i) for i in range(SEGMENTS)]
        return vertices, faces + [tuple(reversed(range(SEGMENTS))), tuple(range(SEGMENTS, 2 * SEGMENTS))]
    if kind == 'cone':
        vertices = [(a, b, 0) for a, b in ring] + [(0, 0, h)]
        return vertices, [(i, after[i], SEGMENTS) for i in range(SEGMENTS)] + [tuple(reversed(range(SEGMENTS)))]
    vertices = []
    for r in range(1, RINGS):
        polar = math.pi * r / RINGS
        vertices += [(a * math.sin(polar), b * math.sin(polar), h / 2 - h / 2 * math.cos(polar)) for a, b in ring]
    low, high = len(vertices), len(vertices) + 1
    vertices += [(0, 0, 0), (0, 0, h)]
    faces = [(r * SEGMENTS + i, r * SEGMENTS + after[i], (r + 1) * SEGMENTS + after[i], (r + 1) * SEGMENTS + i)
             for r in range(RINGS - 2) for i in range(SEGMENTS)]
    top = (RINGS - 2) * SEGMENTS
    return vertices, faces + [(after[i], i, low) for i in range(SEGMENTS)] + [(top + i, top + after[i], high) for i in range(SEGMENTS)]


def state(obj):
    """What the build left on an object; any later edit to its shape, place or modifiers changes this."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', co)
    record = {'co': np.round(co, 5).tolist(), 'matrix': [round(v, 5) for row in obj.matrix_world for v in row],
              'faces': len(obj.data.polygons), 'modifiers': len(obj.modifiers)}
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode('utf-8')).hexdigest()


def check_owned(collection, spec_name):
    """Refuse to replace a collection that is not exactly what an earlier build left."""
    problems = []
    if collection.get('dcc_blockout') != spec_name:
        problems.append('the collection is not tagged as this spec\'s blockout')
    if collection.children:
        problems.append('it holds child collections')
    recorded = set(json.loads(collection.get('dcc_blockout_parts', '[]')))
    present = set()
    for obj in collection.objects:
        iid = obj.get('dcc_instance_id')
        if obj.get('dcc_blockout') != spec_name or iid not in recorded or obj.type != 'MESH':
            problems.append(f'{obj.name} was not built by the blockout')
        elif obj.get('dcc_blockout_state') != state(obj):
            problems.append(f'{obj.name} was edited after it was built')
        else:
            present.add(iid)
    if recorded - present and not problems:
        problems.append('built parts were removed: ' + ', '.join(sorted(recorded - present)))
    if problems:
        raise ValueError('BLOCKOUT_EDITED: refusing to rebuild; ' + '; '.join(problems)
                         + '. Keep the edited collection under another name, or rebuild into a file without it.')


def build(request):
    spec, source, output = request['spec'], request['source'], request['output']
    if source is None:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length = 'METRIC', 1.0
    else:
        if file_hash(source['path']) != source['sha256']:
            raise ValueError('Source changed before native open')
        bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    scene = bpy.context.scene
    unit = scene.unit_settings.scale_length
    if not unit > 0:
        raise ValueError(f'Unsupported scene unit scale: {unit}')
    name = 'dcc.blockout.' + spec['name']
    old = bpy.data.collections.get(name)
    if old is not None:
        check_owned(old, spec['name'])
    mine = set(old.objects) if old is not None else set()
    wanted = {part['name'] for part in spec['parts']}
    taken = sorted({o.get('dcc_instance_id') for o in bpy.data.objects if o not in mine and o.get('dcc_instance_id') in wanted})
    if taken:
        raise ValueError('Stable IDs already used outside the blockout: ' + ', '.join(taken))
    # Stage the new collection completely before the old one goes.
    staged = bpy.data.collections.new(name + '.staged')
    scene.collection.children.link(staged)
    for part in spec['parts']:
        vertices, faces = primitive(part['primitive'], *(v / unit for v in part['size']))
        mesh = bpy.data.meshes.new('blockout.' + part['name'])
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(part['name'], mesh)
        staged.objects.link(obj)
        obj.location = [v / unit for v in part['position']]
        obj.rotation_euler = (0, 0, math.radians(part.get('yaw', 0)))
        obj['dcc_instance_id'], obj['dcc_asset_id'], obj['dcc_blockout'] = part['name'], 'blockout.' + part['name'], spec['name']
        obj['dcc_blockout_category'] = part['category']
    bpy.context.view_layer.update()
    for obj in staged.objects:
        obj['dcc_blockout_state'] = state(obj)
    staged['dcc_blockout'], staged['dcc_blockout_parts'] = spec['name'], json.dumps(sorted(wanted))
    staged['dcc_blockout_digest'] = request['spec_digest']
    if old is not None:
        for obj in list(old.objects):
            mesh = obj.data
            bpy.data.objects.remove(obj)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(old)
    staged.name = name
    bpy.ops.wm.save_as_mainfile(filepath=output)
    if source is not None and file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')
    write_json(Path(request['out']) / 'receipt.json', {
        'schema': 'dcc.blockout.receipt.v1', 'spec_digest': request['spec_digest'], 'collection': name, 'parts': sorted(wanted),
        'replaced': old is not None, 'output_sha256': file_hash(output), 'source': source, 'blender': bpy.app.version_string})


def measure(request):
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    scene = bpy.context.scene
    unit = scene.unit_settings.scale_length
    if not unit > 0:
        raise ValueError(f'Unsupported scene unit scale: {unit}')
    candidates = {}
    for obj in _included_objects(scene):
        iid = obj.get('dcc_instance_id')
        if obj.type in GEOMETRY and isinstance(iid, str) and iid:
            if iid in candidates:
                raise ValueError(f'Duplicate dcc_instance_id, so a part could measure the wrong object: {iid}')
            candidates[iid] = obj
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cache = {}

    def points(iid):
        if iid not in cache:
            evaluated = candidates[iid].evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                co = np.empty(len(mesh.vertices) * 3)
                if len(mesh.vertices):
                    mesh.vertices.foreach_get('co', co)
                matrix = np.array(evaluated.matrix_world)
                cache[iid] = (co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]) * unit
            finally:
                evaluated.to_mesh_clear()
        return cache[iid]

    parts = {}
    for part in request['parts']:
        ids = sorted(i for i in candidates if any(fnmatch.fnmatchcase(i, g) for g in part['ids']))
        cloud = [points(i) for i in ids]
        cloud = np.concatenate(cloud) if cloud else np.zeros((0, 3))
        if not len(cloud):
            parts[part['name']] = {'objects': 0}
            continue
        angle = math.radians(part['yaw'])
        c, s = math.cos(angle), math.sin(angle)
        local = np.stack([cloud[:, 0] * c + cloud[:, 1] * s, -cloud[:, 0] * s + cloud[:, 1] * c, cloud[:, 2]], axis=1)
        low, high = local.min(axis=0), local.max(axis=0)
        mid = (low + high) / 2
        parts[part['name']] = {
            'objects': len(ids), 'ids': ids[:20], 'size': [round(float(v), 6) for v in high - low],
            'base': [round(float(mid[0] * c - mid[1] * s), 6), round(float(mid[0] * s + mid[1] * c), 6), round(float(low[2]), 6)],
            'world': {'min': [round(float(v), 6) for v in cloud.min(axis=0)], 'max': [round(float(v), 6) for v in cloud.max(axis=0)]}}
    write_json(Path(request['out']) / 'measurement.json', {'schema': 'dcc.blockout.measurement.v1', 'checkpoint_sha256': source['sha256'],
                                                           'spec_digest': request['spec_digest'], 'unit_scale': unit, 'parts': parts})


def main():
    if not bpy.app.background:
        raise RuntimeError('Blockout work requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action not in ('build', 'measure'):
        raise ValueError('Unknown blockout worker action')
    (build if action == 'build' else measure)(read_json(request_path))


main()
