"""Owned repair study; move only the existing birdbath assembly."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

p=argparse.ArgumentParser(description=__doc__); p.add_argument('--repo',required=True); p.add_argument('--round',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]); assert bpy.app.background
sys.path.insert(0,a.repo)
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.continuity_checks import validate_contract
from dcc_harness.continuity_blender import observe
from dcc_harness.quality import reserved_space

root=Path(a.round).resolve(); source=root/'unchanged/scene.blend'; sha=file_hash(source)
design=read_json(root/'design.json'); validate_contract(design['contract'])
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
preflight=reserved_space(observe(),design['reservations'],['ext.birdbath.']); write_json(root/'preflight.json',preflight)
if not preflight['passed']: raise RuntimeError('Preflight blocked')
produced={}
for name,delta in {'left_niche':(-1.15,0,0),'left_forward':(-1.6,-.75,0)}.items():
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
    changed=[]
    for obj in bpy.context.scene.objects:
        if obj.get('dcc_instance_id','').startswith('ext.birdbath.'):
            obj.matrix_world=Matrix.Translation(Vector(delta)) @ obj.matrix_world; changed.append(obj['dcc_instance_id'])
    assert len(changed)==3
    bpy.context.view_layer.update(); out=root/name; out.mkdir(exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    produced[name]={'sha256':file_hash(out/'scene.blend'),'delta':delta,'changed':changed}
assert file_hash(source)==sha
write_json(root/'build.json',{'source_unchanged':True,'source_sha256':sha,'candidates':produced,'design_sha256':file_hash(root/'design.json')})
