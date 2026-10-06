"""Disposable Blender probe for the everyday workflow and craft recipes."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('action', choices=['observe', 'material', 'construction'])
p.add_argument('--runtime', required=True)
p.add_argument('--source')
p.add_argument('--out', required=True)
p.add_argument('--compact', action='store_true', help='Write opt-in compact observation storage')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
assert bpy.app.background, 'Qualification must never run in the artist editor'
sys.path.insert(0, a.runtime)
from dcc_harness.continuity_blender import observe
from dcc_harness.craft import wall_sections
from dcc_harness.craft_blender import set_material_scalar
from dcc_harness.evidence import file_hash, write_json

out = Path(a.out)
out.mkdir(parents=True, exist_ok=False)
if a.action in ('observe', 'material'):
    source = Path(a.source).resolve()
    before_sha = file_hash(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    if a.action == 'material':
        before = observe()
        mat = next(m for m in bpy.data.materials if m.get('dcc_material_id') == 'metal')
        users = [o.get('dcc_instance_id') for o in bpy.data.objects if any(s.material == mat for s in o.material_slots)]
        previous = float(mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value)
        try:
            set_material_scalar('metal', 'Principled BSDF', 'Roughness', .46, [])
            raise AssertionError('Omitted material users were accepted')
        except ValueError:
            assert mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value == previous
        result = set_material_scalar('metal', 'Principled BSDF', 'Roughness', .46, users)
        write_json(out / 'material-recipe.json', {'change': result, 'omitted_users_rejected_without_mutation': True})
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'candidate.blend'))
    write_json(out / 'observation.json', observe(), compact_observation=a.compact)
    assert file_hash(source) == before_sha
    write_json(out / 'source-integrity.json', {'source': str(source), 'sha256': before_sha, 'unchanged': True})
else:
    results = []
    for index, width in enumerate((.95, 1.2)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        openings = [{'x': 4, 'z': 0, 'width': width, 'height': 2.1},
                    {'x': .8, 'z': 1.15, 'width': 1.5, 'height': 1.1}]
        for number, panel in enumerate(wall_sections(6, 3, .24, openings)):
            bpy.ops.mesh.primitive_cube_add(size=1, location=panel['center'])
            o = bpy.context.object
            o.name = f'WallPanel_{number}'
            o['dcc_instance_id'] = f'ext.wall.panel.{number}'
            o['dcc_asset_id'] = 'wall'
            o.dimensions = panel['dimensions']
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        rays = []
        for opening in openings:
            for fx in (.1, .5, .9):
                for fz in (.1, .5, .9):
                    hit = bpy.context.scene.ray_cast(deps, Vector((opening['x']+opening['width']*fx, -1,
                                                          opening['z']+opening['height']*fz)), Vector((0, 1, 0)), distance=2)[0]
                    rays.append(not hit)
        wall_hit = bpy.context.scene.ray_cast(deps, Vector((.2, -1, 1)), Vector((0, 1, 0)), distance=2)[0]
        assert all(rays) and wall_hit
        bounds = [o.matrix_world @ Vector(v) for o in bpy.context.scene.objects for v in o.bound_box]
        dimensions = [max(v[i] for v in bounds)-min(v[i] for v in bounds) for i in range(3)]
        assert all(abs(x-y)<1e-5 for x,y in zip(dimensions, (6, .24, 3)))
        bpy.ops.wm.save_as_mainfile(filepath=str(out / f'wall-{index}.blend'))
        results.append({'door_width': width, 'aperture_rays_clear': sum(rays), 'wall_control_hit': wall_hit,
                        'bounds_dimensions': dimensions, 'objects': len(bpy.context.scene.objects)})
    # Guard a linked input and unexpected extra material user in this empty fixture.
    mat = bpy.data.materials.new('ScalarFixture'); mat.use_nodes = True; mat['dcc_material_id'] = 'fixture'
    obj = next(iter(bpy.context.scene.objects)); obj.data.materials.append(mat)
    user = obj['dcc_instance_id']; node = mat.node_tree.nodes['Principled BSDF']
    val = mat.node_tree.nodes.new('ShaderNodeValue')
    mat.node_tree.links.new(val.outputs[0], node.inputs['Roughness'])
    try:
        set_material_scalar('fixture', node.name, 'Roughness', .5, [user])
        raise AssertionError('Linked control accepted')
    except ValueError:
        pass
    write_json(out / 'qualification.json', {'passed': True, 'walls': results, 'linked_input_rejected': True,
               'limits': 'Rectangular wall recipe and native aperture ray samples; no visual quality, welded topology or structural engineering claim.'})
print('WORKFLOW_NATIVE_PROBE_OK', a.action)
