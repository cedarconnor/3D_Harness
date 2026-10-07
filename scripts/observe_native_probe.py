"""Create disposable saved scenes and an in-process reference observation for qualify_observe.py."""
import argparse
from pathlib import Path
import sys

import bpy

p = argparse.ArgumentParser()
p.add_argument('action', choices=['fixtures'])
p.add_argument('--runtime', required=True)
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.runtime)
from dcc_harness.evidence import write_json

out = Path(a.out)
out.mkdir(parents=True, exist_ok=False)


def clean_scene():
    """A cube with stable instance, asset and material IDs, plus an identified camera and light."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    cube.name = 'ProbeCube'
    cube['dcc_instance_id'] = 'probe.cube'
    cube['dcc_asset_id'] = 'probe.cube-asset'
    material = bpy.data.materials.new('ProbeMaterial')
    material.use_nodes = True
    material['dcc_material_id'] = 'probe.material'
    cube.data.materials.append(material)
    camera = bpy.data.objects.new('ProbeCamera', bpy.data.cameras.new('ProbeCamera'))
    camera['dcc_instance_id'] = 'probe.camera'
    camera.location = (4, -4, 3)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    light = bpy.data.objects.new('ProbeLight', bpy.data.lights.new('ProbeLight', 'SUN'))
    light['dcc_instance_id'] = 'probe.light'
    bpy.context.scene.collection.objects.link(light)
    return cube


def save(name):
    bpy.ops.wm.save_as_mainfile(filepath=str(out / name))


clean_scene()
save('clean.blend')

cube = clean_scene()
del cube['dcc_asset_id']
save('missing-asset.blend')

clean_scene()
group = bpy.data.collections.new('ProbeGroup')
template = bpy.data.objects.new('ProbeTemplate', bpy.data.meshes.new('ProbeTemplateMesh'))
group.objects.link(template)
instancer = bpy.data.objects.new('ProbeInstancer', None)
instancer['dcc_instance_id'] = 'probe.instancer'
instancer.instance_type = 'COLLECTION'
instancer.instance_collection = group
bpy.context.scene.collection.objects.link(instancer)
save('instancer.blend')

# Reference: reopen the saved clean file in this process and observe it directly.
bpy.ops.wm.open_mainfile(filepath=str(out / 'clean.blend'), load_ui=False)
from dcc_harness.continuity_blender import observe
write_json(out / 'reference.json', observe())
