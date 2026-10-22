"""Managed capability apply/verify worker; no independent journal or publication."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.data.bridge import recipes
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.environments import load_profile,assert_worker_profile

action,path=sys.argv[sys.argv.index('--')+1:]; request=read_json(path); folder=Path(path).parent
if not bpy.app.background: raise ValueError('Managed worker requires owned background process')
assert_worker_profile(request)
source=request['source']
if file_hash(source['path'])!=source['sha256']: raise ValueError('Capability input changed')
bpy.ops.wm.open_mainfile(filepath=source['path'],load_ui=False)
cap=request['capability']; ref=cap['resolution']['selected']; req=cap['requirement']
args=[cap['root'],ref['recipe_id'],ref['recipe_digest'],load_profile(request['profile']),
      bpy.context.scene,req['target_id'],cap['parameters'],cap['effect_id']]
if action=='execute':
    if Path(request['output']).exists(): raise ValueError('Never replay a native capability mutation')
    result=recipes.apply(*args)
    write_json(folder / 'capability-output.json',result)
    bpy.ops.wm.save_as_mainfile(filepath=request['output'])
elif action=='capability-verify':
    result=recipes.verify(*args,read_json(folder / 'capability-output.json'))
    write_json(folder / 'capability-verified.json',result)
else: raise ValueError('Unknown capability worker action')
assert_worker_profile(request)
if file_hash(source['path'])!=source['sha256']: raise ValueError('Capability input changed during work')
