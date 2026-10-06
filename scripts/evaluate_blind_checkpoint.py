"""Independent native checks; identical procedure for every trial, never edits source.

blender --background CHECKPOINT --python-exit-code 1 --python THIS --
  --repo REPO --out NEWDIR --spec SPEC [--before OBSERVATION] [--starter OBSERVATION]
Evaluates even failed builds. Renders available fixed cameras under a common preset.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import bpy

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--out', required=True)
p.add_argument('--spec', required=True)
p.add_argument('--before')
p.add_argument('--starter')
p.add_argument('--observe-only', action='store_true')
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, args.repo)
from dcc_harness.blender import observe, value
from dcc_harness.evidence import read_json, write_json, file_hash, evaluate, compare, digest, validate_observation
from dcc_harness.uv_guard import evaluated_uv_noise_only, UV_NOISE_TOLERANCE
from scripts.blind_uv_snapshot import supplement

def comparable(raw):
    """Packed content hashes, not resolved locations, establish dependency identity."""
    validate_observation(raw)
    data = copy.deepcopy(raw)
    def walk(item):
        if isinstance(item, dict):
            if item.get('packed') is True and item.get('sha256'):
                item['path'] = '<packed>'
            for v in item.values(): walk(v)
        elif isinstance(item, list):
            for v in item: walk(v)
    walk(data)
    data['revision'] = digest({k:data[k] for k in ('objects','materials','scene','coverage','issues')})
    return data

out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=False)
source = Path(bpy.data.filepath)
source_hash = file_hash(source)
scene = bpy.context.scene
raw = observe()
write_json(out/'raw-observation.json', raw)
obs = comparable(supplement(copy.deepcopy(raw)))
write_json(out/'observation.json', obs)
checks = evaluate(obs, read_json(args.spec))
extra = []
assets = {v['asset_id'] for v in obs['objects'].values() if v['type']=='MESH'}
if len(assets)>8: extra.append('More than eight mesh asset families')
if len(obs['materials'])<3: extra.append('Fewer than three used material families')
if sum('stone' in o['material_ids'] for o in obs['objects'].values())<3:
    extra.append('Shared stone is used on fewer than three objects')
mesh_counts = {}
for o in scene.objects:
    if o.type == 'MESH': mesh_counts[o.data.as_pointer()] = mesh_counts.get(o.data.as_pointer(), 0) + 1
if not any(count > 1 for count in mesh_counts.values()):
    extra.append('No repeated placements share mesh data')
if sum(o.type == 'CAMERA' for o in scene.objects) != 3:
    extra.append('Expected exactly three cameras')
stone_name = obs['materials'].get('stone', {}).get('name')
stone = bpy.data.materials.get(stone_name) if stone_name else None
shader = stone.node_tree.nodes.get('Principled BSDF') if stone and stone.node_tree else None
color_input = shader.inputs.get('Base Color') if shader else None
if shader is None or shader.bl_idname != 'ShaderNodeBsdfPrincipled' or color_input is None or color_input.is_linked:
    extra.append('Stone Base Color is missing or linked')
if len(bpy.data.scenes)!=1: extra.append('Expected one scene')
if any(not i.packed_file for i in bpy.data.images if i.source=='FILE' and i.users):
    extra.append('Used image dependency is not packed')
if not scene.cycles.use_denoising or scene.cycles.seed != 0:
    extra.append('Denoising or Cycles seed differs from fixed preset')
if scene.render.image_settings.file_format!='PNG': extra.append('Output format differs')
if scene.camera is None or scene.camera.get('dcc_instance_id')!='camera.hero':
    extra.append('Final active camera is not camera.hero')

if args.starter:
    starter = comparable(read_json(args.starter))
    for iid in ('camera.hero','camera.reverse','camera.detail','light.sun'):
        if obs['objects'].get(iid)!=starter['objects'].get(iid):
            extra.append('Starter object changed: '+iid)
    for field in ('world','render','color','units','fps','frame'):
        if obs['scene'][field]!=starter['scene'][field]: extra.append('Starter scene field changed: '+field)
preservation = None
if args.before:
    before = comparable(read_json(args.before))
    allow = {'objects':{}, 'materials':{'stone':['graph']}}
    uv_noise = []
    for iid,obj in before['objects'].items():
        if obj.get('asset_id')=='bench' and obj['type']=='MESH':
            allow['objects'][iid]=['geometry_hash','bounds','dimensions','uv_hash','vertices','triangles',
                                   'source_mesh_hash','source_uv_hash','evaluated_uv_values']
        elif obj['type']=='MESH' and evaluated_uv_noise_only(obj, obs['objects'].get(iid, {})):
            allow['objects'][iid]=['uv_hash','evaluated_uv_values']
            if any(obj.get(k)!=obs['objects'][iid].get(k) for k in ('uv_hash','evaluated_uv_values')):
                uv_noise.append(iid)
    preservation = compare(before, obs, allow)
    if not preservation['passed']: extra.append('Observed preservation check failed')
    prior = copy.deepcopy(before['materials'].get('stone',{}))
    for node in (prior.get('graph') or {}).get('nodes',[]):
        if node['name']=='Principled BSDF': node['inputs']['Base Color']=[.38,.43,.48,1.0]
    if prior!=obs['materials'].get('stone'): extra.append('Stone changed beyond the requested base color')
    # Geometry changes can move world bounds without changing transforms; require fixed seat center.
    a,b=before['objects'].get('hero.seat',{}),obs['objects'].get('hero.seat',{})
    if a.get('bounds') and b.get('bounds'):
        if any(abs(sum(x[i] for x in a['bounds'])-sum(x[i] for x in b['bounds']))>.0001 for i in range(3)):
            extra.append('Seat center moved')
    write_json(out/'preservation.json', preservation)
    write_json(out/'uv-noise.json', {'objects':uv_noise,'tolerance':UV_NOISE_TOLERANCE,
               'gates':'Exact authored UV/mesh, evaluated geometry and modifier settings; matching layers/array lengths'})
report = {'source_sha256':source_hash,'evaluator_sha256':file_hash(__file__),
          'uv_snapshot_sha256':file_hash(Path(args.repo)/'scripts/blind_uv_snapshot.py'),
          'uv_guard_sha256':file_hash(Path(args.repo)/'dcc_harness/uv_guard.py'),
          'blender':bpy.app.version_string,'check':checks,'extra_failures':extra,
          'captures':[],'artistic_acceptance':'not_evaluated',
          'dependency_comparison':'Packed image paths normalized; content/color space/name retained',
          'unmeasured':obs['coverage']['not_measured']}
if not args.observe_only:
    # Observe actual settings first. Normalize only the disposable render, never repair the checkpoint.
    scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.seed=0
    scene.cycles.use_denoising=True
    scene.render.resolution_x=960; scene.render.resolution_y=540; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=0; scene.view_settings.gamma=1
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX'; prefs.get_devices()
        for d in prefs.devices: d.use=d.type=='OPTIX'
        scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
    except Exception:
        scene.cycles.device='CPU'
    for view in ('hero','reverse','detail'):
        camera=next((o for o in scene.objects if o.get('dcc_instance_id')=='camera.'+view and o.type=='CAMERA'),None)
        if camera is None:
            extra.append('Cannot capture camera.'+view)
            continue
        scene.camera=camera
        scene.render.filepath=str(out/(view+'.png'))
        start=time.monotonic()
        bpy.ops.render.render(write_still=True)
        report['captures'].append({'view':view,'seconds':round(time.monotonic()-start,3),
                                   'sha256':file_hash(out/(view+'.png'))})
report['source_unchanged']=file_hash(source)==source_hash
report['passed']=checks['passed'] and not extra and report['source_unchanged']
write_json(out/'report.json',report)
print('DCC_BLIND_CHECK '+json.dumps({'passed':report['passed'],'failures':checks['failures']+extra}))
