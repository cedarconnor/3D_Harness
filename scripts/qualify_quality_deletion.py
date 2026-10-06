"""Native saved-file regression for exact deletion and preserved revisions."""
import argparse
from pathlib import Path
import sys
import struct
import bpy
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',required=True);p.add_argument('--source',required=True);p.add_argument('--before',required=True);p.add_argument('--contract',required=True);p.add_argument('--out',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]); assert bpy.app.background
sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import read_json,write_json,file_hash
source=Path(a.source);sha=file_hash(source);out=Path(a.out);out.mkdir(exist_ok=False)
before=read_json(a.before);contract=read_json(a.contract);cases=[]
def load(): bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
def check(name,expected):
    result=evaluate_stage(before,observe(),contract)
    write_json(out/(name+'.json'),result)
    assert result['passed'] is expected,(name,result['failures'])
    cases.append({'name':name,'expected':expected,'observed':result['passed']})
load();check('approved-revision-persists',True)
protected=next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id')=='door.board.00')
bpy.data.objects.remove(protected,do_unlink=True);check('protected-deletion-rejected',False)
load(); obj=next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id')=='ext.table.top')
obj.location.x+=.05;check('unrelated-furniture-drift-rejected',False)
load();obj=next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id','').startswith('ext.foreground.'))
obj['dcc_instance_id']='ext.escaped.scope';check('new-prefix-escape-rejected',False)
load();obj=next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id')=='camera.garden')
obj.data.lens+=1;check('review-camera-drift-rejected',False)
load()
uv_target=next((o,loop,axis) for o in bpy.context.scene.objects if o.type=='MESH' and o.data.uv_layers.active
               for loop in o.data.uv_layers.active.data for axis in (0,1) if .25<=abs(loop.uv[axis])<16)
obj,loop,axis=uv_target; old=float(loop.uv[axis])
bits=struct.unpack('!I',struct.pack('!f',old))[0]
loop.uv[axis]=struct.unpack('!f',struct.pack('!I',bits+1))[0]
delta=abs(float(loop.uv[axis])-old); assert 0<delta<=1e-6
check('tiny-authored-uv-change-rejected',False)
cases[-1].update(target=obj['dcc_instance_id'],authored_delta=delta)
load();check('restored-native-checkpoint-passes',True)
assert file_hash(source)==sha
write_json(out/'qualification.json',{'passed':True,'cases':cases,'source_sha256':sha,'native_saves':0,'blender':bpy.app.version_string})
print('NATIVE_QUALITY_SCOPE_QUALIFIED',len(cases))
