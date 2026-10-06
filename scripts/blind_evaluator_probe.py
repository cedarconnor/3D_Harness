"""Blender-only adversarial fixtures for the independent evaluator, not trial inputs."""
import argparse
import json
from pathlib import Path
import sys
import bpy

p=argparse.ArgumentParser()
p.add_argument('--out',required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
scene=bpy.context.scene
stone=next(m for m in bpy.data.materials if m.get('dcc_material_id')=='stone')
mats=[stone]
for name in ('wood','clay'):
    m=bpy.data.materials.new(name); m.use_nodes=True; m['dcc_material_id']=name; mats.append(m)
for n in range(6):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(n-3,0,.5))
    o=bpy.context.object; o.name='probe-'+str(n)
    o['dcc_instance_id']='hero.seat' if n==0 else 'probe.'+str(n)
    o['dcc_asset_id']='bench' if n==0 else 'family-'+str(n)
    o.data.materials.append(mats[n%3])
    if n==0:
        o.dimensions=(1.9,.5,.12)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
original=next(o for o in scene.objects if o.get('dcc_instance_id')=='probe.3')
duplicate=original.copy(); duplicate['dcc_instance_id']='probe.repeat'; duplicate.location.y=2
scene.collection.objects.link(duplicate)
def save(name):
    scene.camera=next(o for o in scene.objects if o.get('dcc_instance_id')=='camera.hero')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'.blend')))
save('valid-pre')
rgb=stone.node_tree.nodes.new('ShaderNodeRGB')
stone.node_tree.links.new(rgb.outputs[0],stone.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
save('linked-color')
copied_stone=stone.copy()
stone.node_tree.nodes.remove(rgb)
for o in scene.objects:
    for slot in o.material_slots:
        if slot.material==stone: slot.material=copied_stone
save('unused-stone-decoy')
for o in scene.objects:
    for slot in o.material_slots:
        if slot.material==copied_stone: slot.material=stone
bpy.data.materials.remove(copied_stone)
cam=bpy.data.objects.new('extra-camera',bpy.data.cameras.new('extra-camera'))
cam['dcc_instance_id']='camera.extra'; scene.collection.objects.link(cam)
save('extra-camera')
bpy.data.objects.remove(cam,do_unlink=True)
shared=duplicate.data; duplicate.data=shared.copy(); shared.use_fake_user=True
save('fake-sharing')
duplicate.data=shared; shared.use_fake_user=False
seat=next(o for o in scene.objects if o.get('dcc_instance_id')=='hero.seat')
for v in seat.data.vertices: v.co.x*=2.1/1.9
stone.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.38,.43,.48,1)
save('valid-post')
sun=next(o for o in scene.objects if o.get('dcc_instance_id')=='light.sun')
sun.data.energy+=1
save('changed-light')
print('DCC_EVALUATOR_PROBES '+str(out))
