"""Freeze a late shared-tool construction/material revision."""
import copy
from pathlib import Path
import shutil
import sys
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.continuity_checks import validate_contract
night=repo/'runs/overnight-eval-2026-10-04';prior=night/'04-activity';source=prior/'potting_in_progress';root=night/'05-tools'
root.mkdir(exist_ok=False);(root/'unchanged').mkdir();(root/'references').mkdir();(root/'worker').mkdir()
shutil.copyfile(source/'scene.blend',root/'unchanged/scene.blend');shutil.copyfile(source/'observation.json',root/'source-observation.json')
for v in ('overview','garden','worktop'):shutil.copyfile(source/f'{v}.png',root/f'references/{v}.png')
runtime=root/'runtime';runtime.mkdir();(runtime/'scripts').mkdir()
shutil.copytree(repo/'dcc_harness',runtime/'dcc_harness',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('evaluate_quality_candidate.py','assemble_quality_round.py'):shutil.copyfile(repo/'scripts'/name,runtime/'scripts'/name)
d=copy.deepcopy(read_json(prior/'design.json'));obs=read_json(root/'source-observation.json')
targets=['ext.tool.trowel','ext.tool.fork','ext.tool.watering_can.rose']
fields=['vertices','triangles','geometry_hash','uv_hash','source_mesh_hash','source_uv_hash','uv_layers','evaluated_uv_values','modifier_settings','mesh_datablock','bounds','dimensions','material_ids']
d['brief']='Refine the inherited trowel, hand fork and watering-can rose so their construction reads clearly in the worktop view. Compare improved geometry in the existing palette against the same geometry with one restrained shared steel material. Keep the completed environment and transplant activity intact.'
d['contract']['spec']['required']={i:{'type':o['type'],'asset_id':o['asset_id'],**({} if i in targets else {'material_ids':o['material_ids']})} for i,o in obs['objects'].items() if o['type']=='MESH'}
d['contract']['allowed_new_prefixes']=[];d['contract']['allowed_deleted_ids']=[]
d['contract']['allowed_object_prefixes']={i:fields for i in targets};validate_contract(d['contract'])
d['methods']={'modeling':'Revise only three existing meshes. Preserve object transforms, IDs, asset identity and supports; inspect shared-data users before replacing a mesh.',
 'materials':'Never edit inherited material graphs. craft_only keeps the current material IDs; readable_metal may add exactly one shared tool.steel material for the three metal heads, retaining wood handles.',
 'continuity':'Every inherited object outside the three exact IDs is protected, including all previous additions. Bounds and triangle budgets are independently checked.'}
d['targets']=[{'id':'construction','intent':'Readable fork shoulder and splayed tines, a concave trowel blade, and modeled rose openings appropriate at close-view scale.','reference_ids':['worktop']},
 {'id':'material_readability','intent':'Metal heads are distinguishable from timber handles without clashing with the warm restrained palette.','reference_ids':['worktop','overview']},
 {'id':'continuity','intent':'Preserve the whole scene and all previous accepted layout/activity decisions.','reference_ids':['overview','garden']}]
d['references']=[{'id':v,'role':'construction' if v=='worktop' else 'mood','intent':'Preserve established scale, placement, lighting and palette.','file':{'path':f'references/{v}.png','sha256':file_hash(root/f'references/{v}.png')}} for v in ('overview','garden','worktop')]
write_json(root/'design.json',d)
edited={}
for i in targets:
    b=obs['objects'][i]['bounds'];limits=[[b[0][k]-.012 for k in range(3)],[b[1][k]+.012 for k in range(3)]]
    if i!='ext.tool.watering_can.rose':limits[0][2]=.95
    edited[i]={'bounds_limits':limits,'maximum_triangles':20000,'allowed_material_ids':obs['objects'][i]['material_ids']+['tool.steel']}
write_json(root/'scope.json',{'new_prefix':'ext.tool.','bounds':[[0,-6,.95],[2.4,-5.2,1.6]],'minimum_new_meshes':0,'maximum_new_meshes':0,'maximum_new_triangles':0,
 'reuse_materials_only':False,'allowed_new_material_ids':['tool.steel'],'edited_objects':edited,'candidate_ids':['craft_only','readable_metal'],'maximum_author_preview_renders':4,'maximum_repairs_per_candidate':2})
(root/'PROMPT.md').write_text('''# Fresh-context inherited-tool revision

Read this packet's design.json, scope.json, source-observation.json and reference images. Open only unchanged/scene.blend. This is a late edit to a completed courtyard checkpoint; all its accumulated decisions are protected.

Produce two alternatives from the same source:

- craft_only: refine only ext.tool.trowel, ext.tool.fork and ext.tool.watering_can.rose while keeping their current material IDs. Give the fork a readable head/shoulder and slightly splayed useful tines, the trowel a concave shaped blade with a clear handle connection, and the rose genuine modeled openings instead of a smooth bulb.
- readable_metal: use the same refined geometry and one new shared tool.steel material on the metal heads. Choose restrained muted steel with convincing roughness, not chrome; retain timber handles. This isolates the material choice from the construction change.

Preserve each existing object's instance ID, asset ID, name, matrix, parent and collection. Rebuild the existing mesh in its original object coordinates; do not reset transforms to make authoring easier. Inspect source datablock users first; replace with a private mesh if needed instead of changing a shared mesh used elsewhere. No object may be added or deleted in the saved candidates. Temporary modeling objects are allowed only if removed before save. Every other mesh, material graph, camera, light and scene setting stays identical. All other tool pieces, the foreground planting and workbench additions are protected. Scope.json supplies expanded world bounds and per-object triangle/material limits. Tabletop tools must not penetrate below Z=.95 or float above the support without explanation. Do not enter the reserved clear-work patch.

New material: only readable_metal may add tool.steel with that dcc_material_id. Use it as one shared datablock; never edit inherited bronze/wood/paint materials. craft_only must retain existing bindings. No texture downloads, generated assets, lights, simulations or nodes that require external services. Finish all geometry as mesh; apply any unsupported authoring modifiers before saving. Native visibility currently supports Bevel/Weighted Normal/Solidify/Array/Mirror/Triangulate with matching render/viewport display.

Budget: two candidates, four preview renders total, at most two materially different repairs per candidate. Inspect worktop at the frozen camera/preset; the coordinator independently renders all three views afterward. Keep failed versions, scripts and evidence. Save craft_only/scene.blend and readable_metal/scene.blend. No source overwrite. Record source hashes and explicit native checks. Frozen runtime is version 0.3.1, with a qualified one-adjacent-float32 UV guard; do not change it or grant broad exemptions if a check fails.

Use background Blender only: C:/Program Files/Blender Foundation/Blender 5.1/blender.exe with --background --factory-startup --python-exit-code 1 --python your_script.py. You own only worker/ and the two final candidate directories here. You are not alone in the repository; preserve all other work and the live editor. Do not inspect other runs or history. Journal each native author dispatch with Project under worker/journal, preserve script hashes and complete it with observed JSON evidence. On failure, inspect and reconcile before another write; never blindly replay.

Finish with worker/REPORT.md and worker/CONTINUE.md describing shapes, material choice, exact checks, support reasoning, preview/repair counts and limitations. Do not claim artist acceptance or general topology certification. No Git operations or external publication.
''',encoding='utf-8')
files=[root/'design.json',root/'scope.json',root/'PROMPT.md',root/'source-observation.json',root/'unchanged/scene.blend',*sorted((root/'references').iterdir()),*sorted(runtime.rglob('*.py'))]
write_json(root/'packet-manifest.json',{'files':{p.relative_to(root).as_posix():file_hash(p) for p in files},'history':'fresh context; procedural isolation','native_writer':'assigned tool worker only'})
print(root)
