"""Add only fixed review cameras to an owned copy of the preferred checkpoint."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--out',required=True)
p.add_argument('--repo',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(a.out).resolve()
if out.exists(): raise FileExistsError(out)
out.mkdir(parents=True)
for name,position,target,lens in (
    ('overview',(18,-22,16),(3,-2,0),43),
    ('garden',(13,-9,6),(7.4,0,1),46),
    ('forecourt',(-10,-17,10),(3,-4,0.8),43)):
    iid='camera.'+name
    if any(o.get('dcc_instance_id')==iid for o in bpy.context.scene.objects):
        raise ValueError('Camera already exists: '+iid)
    data=bpy.data.cameras.new(iid)
    camera=bpy.data.objects.new(iid,data)
    bpy.context.scene.collection.objects.link(camera)
    camera['dcc_instance_id']=iid
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens
bpy.context.scene.camera=next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id')=='camera.hero')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'start.blend'))
sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json
write_json(out/'observation.json',observe())
print('CONTINUITY_STARTER',str(out/'start.blend'))
