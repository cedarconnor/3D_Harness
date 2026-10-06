"""Prepare a file-only workbench continuation from a selected saved candidate."""
import argparse
import copy
from pathlib import Path
import shutil
import sys
repo=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.continuity_checks import validate_contract
p=argparse.ArgumentParser(description=__doc__); p.add_argument('source_candidate'); a=p.parse_args()
source=Path(a.source_candidate).resolve(); prior=source.parent
root=repo/'runs/overnight-eval-2026-10-04/04-activity'
root.mkdir(exist_ok=False); (root/'unchanged').mkdir(); (root/'references').mkdir(); (root/'worker').mkdir()
shutil.copyfile(source/'scene.blend',root/'unchanged/scene.blend')
shutil.copyfile(source/'observation.json',root/'source-observation.json')
for view in ('overview','garden','worktop'): shutil.copyfile(source/f'{view}.png',root/f'references/{view}.png')
runtime=root/'runtime'; runtime.mkdir(); (runtime/'scripts').mkdir()
shutil.copytree(repo/'dcc_harness',runtime/'dcc_harness',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('evaluate_quality_candidate.py','assemble_quality_round.py'):
    shutil.copyfile(repo/'scripts'/name,runtime/'scripts'/name)
design=copy.deepcopy(read_json(prior/'design.json')); obs=read_json(root/'source-observation.json')
design['brief']='Give the potting bench a believable gardening activity, comparing an active transplant with prepared herb cuttings. Preserve every inherited object and surface. Clarify the blank bronze plaque with small readable mesh lettering. Keep a useful clear work patch and add restrained useful supplies below.'
design['contract']['spec']['required']={iid:{'type':o['type'],'asset_id':o['asset_id'],'material_ids':o['material_ids']} for iid,o in obs['objects'].items() if o['type']=='MESH'}
design['contract']['allowed_object_prefixes']={}; design['contract']['allowed_deleted_ids']=[]
design['contract']['allowed_new_prefixes']=['ext.worktask.']; validate_contract(design['contract'])
design['methods']={'continuation':'Native checkpoint and current observations are authoritative. Add only new scoped mesh objects; preserve existing transforms, mesh definitions, material graphs, cameras and lights.',
 'story':'One specific gardening task with reachable tools, convincing support/contact and restraint. Reuse the inherited terracotta, timber, soil and leaf materials.',
 'review':'Same fixed overview/garden and asset-relative worktop view; visibility requirements remain unchanged.'}
design['references']=[{'id':v,'role':'mood' if v!='worktop' else 'construction','intent':'Preserve inherited composition, color, materials and assets.','file':{'path':f'references/{v}.png','sha256':file_hash(root/f'references/{v}.png')}} for v in ('overview','garden','worktop')]
design['targets']=[{'id':'activity','intent':'A specific gardening task is legible, with useful supplies and some clear work surface.','reference_ids':['worktop']},
 {'id':'continuity','intent':'Preserve the garden, foreground, canopy, birdbath, lighting and palette.','reference_ids':['overview','garden']},
 {'id':'craft','intent':'Small pots, plants, soil and lettering have convincing scale, construction and contact without decorative clutter.','reference_ids':['worktop','garden']}]
design['reservations'].append({'id':'clear_work_patch','bounds':[[.65,-5.96,.95005],[1.2,-5.74,1.7]],'obstacle_prefixes':['ext.'],'exempt_ids':[],'tolerance':1e-5})
write_json(root/'design.json',design)
write_json(root/'scope.json',{'new_prefix':'ext.worktask.','bounds':[[-.35,-5.98,.31999],[2.35,-5.22,1.6]],'minimum_new_meshes':3,'maximum_new_meshes':100,'maximum_new_triangles':60000,'reuse_materials_only':True,'candidate_ids':['potting_in_progress','prepared_cuttings'],'maximum_author_preview_renders':6,'maximum_repairs_per_candidate':2})
(root/'PROMPT.md').write_text('''# Fresh-context workbench continuation

Read design.json, scope.json, source-observation.json and the three reference images. Open only unchanged/scene.blend as your source. You are a new worker receiving files, not the earlier agent's conversation. Create two alternatives from this same source:

- potting_in_progress: show one herb transplant in progress with a small planting pot/plant and a restrained amount of loose soil, tools already within reach, and useful supplies below.
- prepared_cuttings: show a coherent small propagation task with herb cuttings or young plants and restrained lower-shelf supplies. This should be a materially different arrangement, not the same objects shifted a few centimeters.

The goal is readable activity and natural arrangement, not maximal clutter. Clarify the existing blank bronze plaque with tiny mesh lettering such as HERB NURSERY; preserve its base. Leave the exact clear_work_patch in design.json empty. The tabletop top is Z=.95 and shelf top is Z=.32. Use the observation to avoid existing tools, watering can, seed tray, legs and braces. Physically support additions on the tabletop or shelf; record support reasoning in your handoff.

All existing objects are protected: no transform, material, mesh, light, camera or scene changes; no deletion. New real mesh objects use unique dcc_instance_id beginning ext.worktask. and meaningful dcc_asset_id. Reuse existing material datablocks by dcc_material_id with no graph edits or new materials. Keep all added geometry inside scope.json's volume and budget. Convert temporary text/curves to meshes; remove unneeded temporary objects before saving. Do not use instances, simulations or geometry nodes. Existing Bevel/Weighted Normal/Solidify, and matching-display Array/Mirror/Triangulate modifiers are supported by the independent visibility evaluator.

Native executable: C:/Program Files/Blender Foundation/Blender 5.1/blender.exe. Use --background --factory-startup --python-exit-code 1 --python your_script.py. Work only in worker/ plus final potting_in_progress/scene.blend and prepared_cuttings/scene.blend. Do not touch the live Blender editor or other repository paths. You are not alone in this workspace: preserve everyone else's work. No Git operations or external publishing.

Budget: two candidates, at most six preview renders total, at most two materially different repairs per candidate. Keep failures and scripts. Preview at Cycles 32 samples, 960x540, seed 0, denoising, existing color settings; use GPU if available. Independent evaluation later renders all three views. Save and pack each candidate to a new final file; hash the source before/after and never save over it.

Use the frozen runtime/dcc_harness helpers for observations and your own continuity checks. Journal native author dispatches with Project under worker/journal; record observed evidence afterward. Failed or interrupted dispatches require inspection and explicit reconciliation before another write. Do not blindly replay or alter runtime/design/scope/references/unchanged. Keep packet isolation: do not inspect sibling runs or previous agents' history.

Finish with worker/REPORT.md and worker/CONTINUE.md covering both designs, exact files, checks actually executed, source preservation, preview count, support/contact reasoning and limitations. Do not claim artist acceptance. The coordinator independently verifies output and obtains anonymous image critique after you stop.
''',encoding='utf-8')
files=[root/'design.json',root/'scope.json',root/'PROMPT.md',root/'source-observation.json',root/'unchanged/scene.blend',*sorted((root/'references').iterdir()),*sorted(runtime.rglob('*.py'))]
write_json(root/'packet-manifest.json',{'files':{p.relative_to(root).as_posix():file_hash(p) for p in files},'history':'fresh context; procedural isolation','native_writer':'assigned workbench worker only'})
print(root)
