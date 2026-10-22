"""Private fresh-process worker for delivery.py; never run in an artist editor and never saves.

`export` opens the saved source, records what it will deliver and writes delivery.glb.
`reimport` starts from an empty scene, imports the GLB and records what arrived.
"""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.evidence import file_hash, read_json, write_json

DELIVERED = {'MESH', 'EMPTY'}
SKIPPED = {'CAMERA': 'cameras are not delivered', 'LIGHT': 'lights are not delivered'}
SETTINGS = {'export_format': 'GLB', 'export_extras': True, 'export_apply': True, 'export_yup': True,
            'export_cameras': False, 'export_lights': False, 'use_selection': False, 'use_visible': False}


def stable_id(obj):
    value = obj.get('dcc_instance_id')
    return value if isinstance(value, str) and value else 'name:' + obj.name


def record(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    triangles, corners = 0, [evaluated.matrix_world.translation.copy()]
    if obj.type == 'MESH':
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            triangles = len(mesh.loop_triangles)
            if len(mesh.vertices):
                corners = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        finally:
            evaluated.to_mesh_clear()
    low = [round(min(c[i] for c in corners), 6) for i in range(3)]
    high = [round(max(c[i] for c in corners), 6) for i in range(3)]
    materials = [slot.material.name for slot in obj.material_slots if slot.material] if obj.type == 'MESH' else []
    ancestors, parent = [], obj.parent
    while parent is not None:
        ancestors.append(stable_id(parent)); parent = parent.parent
    return {'id': stable_id(obj), 'type': obj.type, 'triangles': triangles, 'bounds': [low, high], 'materials': materials,
            'parent': ancestors[0] if ancestors else None, 'ancestors': ancestors}


def addon_version():
    import addon_utils
    module = next((m for m in addon_utils.modules() if m.__name__ == 'io_scene_gltf2'), None)
    return '.'.join(map(str, module.bl_info.get('version', ()))) if module else 'unknown'


def export(request):
    source, out = request['source'], Path(request['out'])
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    if abs(bpy.context.scene.unit_settings.scale_length - 1.0) > 1e-8:
        raise ValueError('GLB delivery requires unit scale 1 metre per Blender unit; physical scale conversion is not qualified')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects, skipped = [], []
    for obj in sorted(bpy.context.scene.objects, key=stable_id):
        if obj.type in DELIVERED and obj.instance_type != 'COLLECTION':
            objects.append(record(obj, depsgraph))
        else:
            instance = obj.instance_type == 'COLLECTION'
            reason = SKIPPED.get(obj.type, 'collection instances are written as the exporter chooses; identity is not checked'
                                 if instance else f'{obj.type} objects are not delivered')
            skipped.append({'id': stable_id(obj), 'type': obj.type, 'reason': reason, **({'instance': True} if instance else {})})
    bpy.ops.export_scene.gltf(filepath=str(out / 'delivery.glb'), **SETTINGS)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed during export')
    write_json(out / 'export.json', {'objects': objects, 'not_exported': skipped, 'settings': SETTINGS, 'units': 'metres',
                                     'blender': bpy.app.version_string, 'exporter': addon_version(),
                                     'source_sha256': source['sha256']})


def reimport(request):
    glb = Path(request['glb'])
    if file_hash(glb) != request['glb_sha256']:
        raise ValueError('GLB changed before import')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = [record(obj, depsgraph) for obj in sorted(bpy.context.scene.objects, key=stable_id)]
    write_json(Path(request['out']) / 'import.json', {'objects': objects, 'blender': bpy.app.version_string})


def main():
    if not bpy.app.background:
        raise RuntimeError('Delivery requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    request = read_json(request_path)
    {'export': export, 'reimport': reimport}[action](request)


main()
