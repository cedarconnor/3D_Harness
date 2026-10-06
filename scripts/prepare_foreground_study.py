"""Freeze the next independent-worker task; no DCC mutations."""
import copy
from pathlib import Path
import shutil
import sys

repo=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.continuity_checks import validate_contract

night=repo/'runs/overnight-eval-2026-10-04'; prior=night/'02-birdbath'; root=night/'03-foreground'
root.mkdir(exist_ok=False); (root/'unchanged').mkdir(); (root/'references').mkdir(); (root/'worker').mkdir()
shutil.copyfile(prior/'left_forward/scene.blend',root/'unchanged/scene.blend')
shutil.copyfile(prior/'left_forward/observation.json',root/'source-observation.json')
for view in ('overview','garden','worktop'):
    shutil.copyfile(prior/f'left_forward/{view}.png',root/f'references/{view}.png')
runtime=root/'runtime'; runtime.mkdir(); (runtime/'scripts').mkdir()
shutil.copytree(repo/'dcc_harness',runtime/'dcc_harness',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('evaluate_quality_candidate.py','assemble_quality_round.py'):
    shutil.copyfile(repo/'scripts'/name,runtime/'scripts'/name)
design=copy.deepcopy(read_json(prior/'design.json')); obs=read_json(root/'source-observation.json')
deleted=[f'ext.forecourt.field.{r:02d}.{c:02d}' for r in (0,1) for c in range(13,20)]
design['brief']='Refine the inactive front-right foreground with two restrained alternatives: a low planted herb edge, or a crafted paving band. Preserve the workshop, open canopy, visible birdbath, arched entrance, all existing materials, lighting and review cameras. The foreground should frame the garden, not become a new focal point.'
design['contract']['spec']['required']={iid:{'type':o['type'],'asset_id':o['asset_id'],'material_ids':o['material_ids']} for iid,o in obs['objects'].items() if o['type']=='MESH' and iid not in deleted}
design['contract']['allowed_object_prefixes']={}
design['contract']['allowed_deleted_ids']=deleted
design['contract']['allowed_new_prefixes']=['ext.foreground.']
validate_contract(design['contract'])
design['methods']={'preservation':'No existing object may change. Only the 14 exact named pavers may be removed; all new objects must have ext.foreground. IDs and reuse existing materials.',
 'design':'Low cultivated texture versus a deliberate stone/tile edge. Avoid rectangular filler clutter and tall screening.',
 'measurement':'Same .55 geometric birdbath visibility minimum in both fixed views; compare rendered appearance separately.'}
design['references']=[{'id':v,'role':'mood' if v!='worktop' else 'construction','intent':'Preserve inherited proportions, material vocabulary and hierarchy.','file':{'path':f'references/{v}.png','sha256':file_hash(root/f'references/{v}.png')}} for v in ('overview','garden','worktop')]
design['targets']=[{'id':'foreground','intent':'Give the inactive front-right ground a purposeful low edge without competing with the entry.','reference_ids':['overview','garden']},
 {'id':'continuity','intent':'Retain the exact workshop, canopy, birdbath, material definitions, lighting and cameras.','reference_ids':['overview','garden','worktop']},
 {'id':'craft','intent':'Convincing low planting or paving construction at human scale; avoid obvious overlaps and repetitive filler.','reference_ids':['garden','worktop']}]
design['reservations'][0]['obstacle_prefixes']=['ext.']
write_json(root/'design.json',design)
write_json(root/'scope.json',{'new_prefix':'ext.foreground.','bounds':[[5.35,-7.78,-.03],[10.27,-6.48,.65]],'minimum_new_meshes':1,'maximum_new_meshes':200,'maximum_new_triangles':60000,'reuse_materials_only':True,'candidate_ids':['herb_edge','paving_band'],'maximum_author_preview_renders':6,'maximum_repairs_per_candidate':2})
(root/'PROMPT.md').write_text('''# Fresh-context courtyard refinement

Read design.json, scope.json, source-observation.json and the three reference images in this packet. Open only unchanged/scene.blend as the source. All prior history is intentionally omitted. You are the sole native author for this packet; the main coordinator independently evaluates your finished files.

Create two alternatives, each from the same unchanged source:

- herb_edge: a low planted kitchen-herb edge along the front-right court. Use a coherent cluster with crafted edging and readable plant silhouettes, not a row of generic balls.
- paving_band: a restrained geometric band or crafted terrace edge using the inherited stone/tile palette. Keep it low and subordinate to the architecture.

Use the allowed 14 paving tiles as your replacement area. All new geometry must lie inside scope.json bounds. Inlay lines and perimeter tiles remain protected. You may retain or delete only the 14 listed tiles; no other existing object, material, scene, light, camera or setting may change. Reuse material datablocks by dcc_material_id; do not edit them or create new materials. Assign all new objects unique dcc_instance_id beginning ext.foreground. and meaningful dcc_asset_id. Use real mesh objects, not collection/geometry-node instances, curves, or fonts. Avoid altering the current selection/view of the user's Blender; all work is in background processes on owned files.

Budget: two candidates, at most six preview renders total, at most two materially different repairs per candidate. Keep failed versions and scripts. Save herb_edge/scene.blend and paving_band/scene.blend; pack any dependencies. Never save over the source. Record hashes of the source before/after. Current render preset is Cycles 32 samples, 960x540, seed 0, denoising, existing color settings. Use GPU if available. An independent evaluator will render overview, garden and worktop after you finish, so previews may focus on design questions.

Native executable: C:/Program Files/Blender Foundation/Blender 5.1/blender.exe. Invoke --background --factory-startup --python-exit-code 1 --python your_script.py. Load runtime/dcc_harness by adding runtime to sys.path. Log each native author dispatch with Project in worker/journal before execution; finish against an observed JSON receipt afterward. On a failed or interrupted dispatch, inspect artifacts and explicitly reconcile before another author call; never blindly replay. Use continuity_blender.observe and continuity_checks.evaluate_stage for your own checks. The coordinator's independent evaluator is frozen in runtime/scripts; do not modify runtime, design, scope, references or unchanged.

Write all your new scripts, previews, logs and reports only under worker/, plus the two final candidate directories. You are not alone in the repository: do not revert or modify other work. Do not crawl prior runs, read sibling candidates or seek the coordinator's conversation. Existing skill descriptions/tool access do not make this a security sandbox; keep procedural isolation.

Finish with worker/REPORT.md and worker/CONTINUE.md explaining each design, checks actually run, remaining limitations and exact files. Do not claim artist acceptance. The final response should name both candidate paths, native check status, preview count and any blocker. No Git operations or external publication.
''',encoding='utf-8')
files=[root/'design.json',root/'scope.json',root/'PROMPT.md',root/'source-observation.json',root/'unchanged/scene.blend',*sorted((root/'references').iterdir()),*sorted(runtime.rglob('*.py'))]
write_json(root/'packet-manifest.json',{'files':{p.relative_to(root).as_posix():file_hash(p) for p in files},'history':'fresh context; procedural isolation','native_writer':'assigned foreground worker only'})
print(root)
