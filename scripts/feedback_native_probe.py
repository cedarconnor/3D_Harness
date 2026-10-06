"""Disposable micro-environment for feedback tests. Background Blender only."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('action', choices=['fixtures', 'observe', 'render'])
p.add_argument('--runtime', required=True); p.add_argument('--out', required=True); p.add_argument('--source')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.runtime)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json, file_hash, digest

out = Path(a.out)
if a.action == 'fixtures':
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 20
    scene.render.resolution_x = 640; scene.render.resolution_y = 400; scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('World'); scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.20, .25, .32, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
    def material(name, rgb, roughness):
        mat = bpy.data.materials.new(name); mat.use_nodes = True; mat['dcc_material_id'] = name
        bsdf = mat.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = (*rgb, 1)
        bsdf.inputs['Roughness'].default_value = roughness
        return mat
    timber = material('timber', (.24, .10, .035), .15)
    plaster = material('plaster', (.44, .49, .42), .8)
    stone = material('stone', (.22, .23, .22), .7)
    def box(iid, loc, dims, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object; obj.name = iid; obj.dimensions = dims
        obj['dcc_instance_id'] = iid; obj['dcc_asset_id'] = iid
        obj.data.materials.append(mat)
        bevel = obj.modifiers.new('Edge', 'BEVEL'); bevel.width = .012; bevel.segments = 2
        return obj
    top = box('bench.top', (0, 0, .9), (1.6, .65, .09), timber)
    box('ground', (0, 0, -.08), (4.8, 4.0, .16), stone)
    box('wall', (0, .85, 1.2), (4.8, .15, 2.4), plaster)
    for index, (x, y) in enumerate([(-.68, -.23), (.68, -.23), (-.68, .23), (.68, .23)]):
        box(f'bench.leg.{index}', (x, y, .43), (.09, .09, .86), timber)
    box('shelf', (.9, .68, 1.62), (1.0, .32, .06), timber)
    box('crate', (-1.5, .15, .2), (.45, .5, .4), timber)
    bpy.ops.object.camera_add(location=(3.7, -5.8, 3.25))
    camera = bpy.context.object; camera['dcc_instance_id'] = 'review.camera'
    camera.rotation_euler = (Vector((0, .25, .9)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = 48; scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(-2, -2.4, 4.5))
    lamp = bpy.context.object; lamp['dcc_instance_id'] = 'light.key'; lamp.data.energy = 550; lamp.data.shape = 'DISK'; lamp.data.size = 3
    lamp.rotation_euler = (Vector((0, 0, .8)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'baseline.blend'))
    top.dimensions.x = 2.0
    timber.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'revised.blend'))
    lamp.data.energy = 2000
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'bad-light.blend'))
else:
    bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False)
    if a.action == 'observe':
        write_json(out, observe(), compact_observation=True)
    else:
        out.mkdir(parents=True, exist_ok=False)
        scene = bpy.context.scene
        native_sha = file_hash(a.source)
        views = {}
        settings = {'camera_matrix': [list(row) for row in scene.camera.matrix_world], 'lens': scene.camera.data.lens,
                    'resolution': [scene.render.resolution_x, scene.render.resolution_y], 'engine': scene.render.engine,
                    'samples': scene.cycles.samples, 'view_transform': scene.view_settings.view_transform,
                    'exposure': scene.view_settings.exposure, 'frame': scene.frame_current}
        scene.render.filepath = str(out / 'whole.png')
        bpy.ops.render.render(write_still=True)
        views['REVIEW_WHOLE'] = {'path': 'whole.png', 'sha256': file_hash(out / 'whole.png')}
        # A fixed cropped detail from the same camera, with the crop included in view settings.
        scene.render.use_border = True; scene.render.use_crop_to_border = True
        scene.render.border_min_x = .18; scene.render.border_max_x = .77
        scene.render.border_min_y = .15; scene.render.border_max_y = .66
        settings['detail_border'] = [.18, .77, .15, .66]
        scene.render.filepath = str(out / 'detail.png')
        bpy.ops.render.render(write_still=True)
        views['REVIEW_DETAIL'] = {'path': 'detail.png', 'sha256': file_hash(out / 'detail.png')}
        write_json(out / 'views.json', settings)
        write_json(out / 'receipt.json', {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': native_sha,
                                        'views_digest': digest(settings), 'images': views})
        assert file_hash(a.source) == native_sha
