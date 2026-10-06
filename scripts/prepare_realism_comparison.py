"""Freeze four paired creative packets, without launching agents."""
import copy,json,random,secrets,shutil,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
root=repo/'runs/realism-heldout-2026-10-05'; templates=repo/'experiments/realism-heldout'
private=root/'private';private.mkdir(exist_ok=False)
spec={'schema':'dcc.spec.v1','required':{'ext.bench.top':{'type':'MESH','asset_id':'bench','dimensions':[1.8,.65,.06],'tolerance':.01,'min_triangles':12},'ext.building.facade':{'type':'MESH','min_triangles':12,'material_ids':['brick']},'ext.building.door':{'type':'MESH','min_triangles':12},'ext.fern.hero':{'type':'MESH','min_triangles':100},'ext.ground':{'type':'MESH','material_ids':['ground']},**{'camera.'+v:{'type':'CAMERA'} for v in ('hero','context','detail')},'light.sun':{'type':'LIGHT'}},'min_asset_definitions':7,'required_materials':['brick','timber','ground','metal'],'units':{'system':'METRIC','scale_length':1.0},'material_nodes':{'metal':{'Principled BSDF':{'Roughness':.38}}}}
pre={'schema':'dcc.continuity.contract.v1','spec':spec,'allowed_new_prefixes':['ext.'],'allowed_object_prefixes':{}}
post=copy.deepcopy(pre);post['spec']['required']['ext.bench.top']['dimensions'][0]=2.1;post['spec']['material_nodes']['metal']['Principled BSDF']['Roughness']=.58
post['allowed_new_prefixes']=['ext.bench.'];post['allowed_object_prefixes']={'ext.bench.':['matrix_world','bounds','dimensions','vertices','triangles','geometry_hash','uv_hash','source_mesh_hash','source_uv_hash','uv_layers','evaluated_uv_values','modifier_settings','mesh_datablock']};post['allowed_material_inputs']={'metal':{'Principled BSDF':{'Roughness':.58}}};post['preserve_centers']=['ext.bench.top'];post['center_tolerance']=.001
write_json(root/'contract-pre.json',pre);write_json(private/'contract-post.json',post);shutil.copyfile(templates/'REVISION.md',private/'REVISION.md')
runtime=root/'evaluation-runtime/dcc_harness';runtime.mkdir(parents=True)
for f in (repo/'dcc_harness').glob('*.py'):shutil.copyfile(f,runtime/f.name)
shutil.copyfile(repo/'scripts/evaluate_realism_checkpoint.py',root/'evaluation-runtime/evaluate_realism_checkpoint.py')
write_json(root/'evaluation-runtime/manifest.json',{'files':{p.relative_to(root/'evaluation-runtime').as_posix():file_hash(p) for p in (root/'evaluation-runtime').rglob('*') if p.is_file()}})
runs=[]
for block in (1,2):
    methods=['plain','harness'];random.SystemRandom().shuffle(methods)
    for method in methods:
        run_id='t-'+secrets.token_hex(6);packet=root/'trials'/run_id;packet.mkdir(parents=True);(packet/'output').mkdir()
        shutil.copyfile(root/'starter.blend',packet/'starter.blend');shutil.copyfile(root/'starter-observation.json',packet/'source-observation.json')
        shutil.copytree(root/'assets',packet/'assets');shutil.copytree(root/'references',packet/'references');shutil.copyfile(root/'kit-native-inspection.json',packet/'kit-native-inspection.json')
        shutil.copyfile(templates/'BRIEF.md',packet/'BRIEF.md');write_json(packet/'contract.json',pre)
        extra='Use your normal Blender problem-solving workflow. No project process skills or harness runtime are included in this packet.'
        if method=='harness':
            shutil.copytree(root/'evaluation-runtime/dcc_harness',packet/'runtime/dcc_harness');shutil.copyfile(templates/'METHOD-H.md',packet/'METHOD.md')
            for name in ('dcc-plan-environment','dcc-build-revise','dcc-review-continue'):
                dest=packet/'skills'/name;dest.mkdir(parents=True);shutil.copyfile(repo/'.agents/skills'/name/'SKILL.md',dest/'SKILL.md')
            extra='Read METHOD.md and use the included skills/runtime.'
        (packet/'PROMPT.md').write_text('''You are an independent Blender environment builder. Read BRIEF.md, contract.json, kit-native-inspection.json and both reference images in this packet. '''+extra+'''

You own only output/ in this packet. You are not alone in the repository: preserve all others' work. Frozen inputs must not change. Do not read parent/sibling directories, repository source, prior chats, other runs, global skills, private manifests or evaluator reports. Do not spawn or message agents. Record unavoidable ambient skill/tool metadata exposure in your handoff. This is procedural isolation on a shared filesystem.

The coordinator grants you a separate owned background Blender writer, starting from starter.blend. Use C:/Program Files/Blender Foundation/Blender 5.1/blender.exe with --background --factory-startup --python-exit-code 1 --python YOUR_SCRIPT -- ARGS. Confirm bpy.app.background and loaded file ownership before authoring. Do not call live MCP or touch the user's editor. Use local shell/file/image tools only within this packet; no network or other scene imports. You may import the included fern library. Keep source scripts and failures; new attempts use new filenames. Render in your own process and inspect images. No postprocessing or AI image replacement.

Save output/pre.blend and output/CONTINUE.md, list assets actually used, preview count, repair count and uncertainty. All scripts/reports go under output/. A late revision will use a different context. Return paths and honest completion status without artist scores or guessing your method assignment. Budget is 45 minutes and 8 preview images from dispatch.
''',encoding='utf-8')
        manifest={p.relative_to(packet).as_posix():file_hash(p) for p in packet.rglob('*') if p.is_file()};write_json(packet/'manifest.json',{'files':manifest})
        runs.append({'id':run_id,'block':block,'method':method,'packet':str(packet),'manifest_sha256':file_hash(packet/'manifest.json')})
write_json(private/'manifest.json',{'schema':'dcc.realism.comparison.v1','runs':runs,'method_question':'Plain workflow versus skills plus retained-method/native-check package; two repeats, fresh late revision for each. Same kit/cameras/budgets/evaluator. Not long-term autonomy or statistical superiority.','budgets':{'build_minutes':45,'revision_minutes':20,'build_previews':8,'revision_previews':4},'external_generation':False,'model_settings':'Inherited unchanged; exact token/cost metering unavailable.'})
print(json.dumps(runs,indent=2))
