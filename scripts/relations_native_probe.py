"""Disposable bench scenes for supported_by qualification. Background Blender only.

blender --background --factory-startup --python-exit-code 1 --python THIS -- --out NEW_FOLDER

The ground is one quad whose height is SLOPE * y (zero for flat scenes), so expected contact
values are exact: legs are 0.09 m boxes at y = +/-0.23, and their footprints span y +/- 0.045.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
out = Path(a.out)
out.mkdir(parents=True, exist_ok=False)
SLOPE = 0.1
LEGS = [(-.68, -.23), (.68, -.23), (-.68, .23), (.68, .23)]
LEG_TOP = 0.86


def material(name, rgb):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; mat['dcc_material_id'] = name
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*rgb, 1)
    return mat


def box(iid, center, dims, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object; obj.name = iid; obj.dimensions = dims
    obj['dcc_instance_id'] = iid; obj['dcc_asset_id'] = iid
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def build(name, *, slope=0.0, lift=0.0, fitted=False, off_edge=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 16
    scene.world = bpy.data.worlds.new('World'); scene.world.use_nodes = True
    timber, stone = material('timber', (.24, .10, .035)), material('stone', (.22, .23, .22))
    mesh = bpy.data.meshes.new('ground')
    mesh.from_pydata([(-2.4, -2, -2 * slope), (2.4, -2, -2 * slope), (2.4, 2, 2 * slope), (-2.4, 2, 2 * slope)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new('ground', mesh); scene.collection.objects.link(ground)
    ground['dcc_instance_id'] = 'ground'; ground['dcc_asset_id'] = 'ground'; mesh.materials.append(stone)
    box('bench.top', (0, 0, 0.9 + lift), (1.6, .65, .09), timber)
    for index, (x, y) in enumerate(LEGS):
        bottom = slope * (y + .045) if fitted else lift
        if off_edge and index == 0:
            x = -2.6
        box(f'bench.leg.{index}', (x, y, (bottom + LEG_TOP + lift) / 2), (.09, .09, LEG_TOP + lift - bottom), timber)
    bpy.ops.object.camera_add(location=(3.7, -5.8, 3.25))
    camera = bpy.context.object; camera['dcc_instance_id'] = 'review.camera'
    camera.rotation_euler = (Vector((0, 0, .6)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.lens = 40; scene.camera = camera
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 5))
    sun = bpy.context.object; sun['dcc_instance_id'] = 'light.sun'; sun.data.energy = 3
    bpy.ops.wm.save_as_mainfile(filepath=str(out / (name + '.blend')))


SCENES = {
    'flat': {}, 'raised': {'lift': .03}, 'sunk': {'lift': -.03}, 'off-edge': {'off_edge': True},
    'slope-fitted': {'slope': SLOPE, 'fitted': True}, 'slope-equal': {'slope': SLOPE},
    'slope-lowered': {'slope': SLOPE, 'lift': -.04}, 'slope-raised': {'slope': SLOPE, 'lift': .04}}
for name, options in SCENES.items():
    build(name, **options)
(out / 'scenes.json').write_text(json.dumps({'slope': SLOPE, 'scenes': SCENES}, indent=2), encoding='utf-8')
print('DCC_SCENES', len(SCENES))
