"""Create a geometry-free comparison starter in a fresh background Blender process."""
import argparse
from pathlib import Path
import sys
import math
import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
p.add_argument('--kit', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.out).resolve()
kit = Path(args.kit).resolve()
if out.exists():
    raise ValueError('Starter already exists')
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'Courtyard'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.seed = 0
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
stone = bpy.data.materials.new('Stone')
stone.use_nodes = True
stone.use_fake_user = True
stone['dcc_material_id'] = 'stone'
stone.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.55,.47,.36,1)
stone.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .72
stone.diffuse_color = (.55,.47,.36,1)
world = bpy.data.worlds.new('CourtyardSky')
world.use_nodes = True
scene.world = world
env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(str(kit/'kloppenheim_06_puresky_1k.hdr'))
env.image.pack()
env.image.filepath = '//assets/kloppenheim_06_puresky_1k.hdr'
world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs['Color'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
for iid,pos,target,lens in (
    ('camera.hero',(11,-15,9),(0,.5,1.4),47),
    ('camera.reverse',(-10,-10,6),(0,1.1,1.5),48),
    ('camera.detail',(4,-6,3.5),(-1.2,1.2,.9),57),
):
    obj = bpy.data.objects.new(iid,bpy.data.cameras.new(iid))
    scene.collection.objects.link(obj)
    obj['dcc_instance_id'] = iid
    obj.location = pos
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    obj.data.lens = lens
    if iid == 'camera.hero': scene.camera = obj
sun = bpy.data.objects.new('Sun',bpy.data.lights.new('Sun','SUN'))
scene.collection.objects.link(sun)
sun['dcc_instance_id'] = 'light.sun'
sun.data.energy = 2.1
sun.data.angle = .12
sun.data.color = (1,.84,.64)
sun.rotation_euler = tuple(math.radians(n) for n in (28,-24,-25))
assert len(scene.objects) == 4 and not any(o.type=='MESH' for o in scene.objects)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print('DCC_BLIND_STARTER '+str(out))
