"""Retain failed canopy attempts, then freeze a narrowly expanded repair scope."""
import copy
from pathlib import Path
import shutil
import sys
repo=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash

night=repo/'runs/overnight-eval-2026-10-04'; prior=night/'01-canopy'; root=night/'02-birdbath'
root.mkdir(exist_ok=False); (root/'unchanged').mkdir(); shutil.copytree(prior/'references',root/'references')
shutil.copyfile(prior/'open_timber/scene.blend',root/'unchanged/scene.blend')
design=copy.deepcopy(read_json(prior/'design.json'))
design['brief']='Repair the failed birdbath visibility requirement by comparing two modest assembly relocations. The inherited open-timber canopy is an unaccepted intermediate from the previous failed stage. Preserve its structure plus the workshop layout, original courtyard, beds, paving, lighting, cameras and materials. Keep both failed canopy candidates and their evidence.'
obs=read_json(prior/'open_timber/observation.json')
design['contract']['spec']['required']={iid:{'type':o['type'],'asset_id':o['asset_id'],'material_ids':o['material_ids']} for iid,o in obs['objects'].items() if o['type']=='MESH'}
design['contract']['allowed_object_prefixes']={'ext.birdbath.':['matrix_world','bounds','dimensions']}
design['contract']['allowed_deleted_ids']=[]
design['methods']['repair']='Translate bowl, pedestal and water rigidly as one assembly; preserve Z/support height, meshes, shared materials and all non-birdbath objects.'
design['methods']['lineage']='The previous two canopy variants failed the .55 geometric visibility rule. No tolerance change or original-result replacement. A combined original-to-repair preservation check is required before master publication.'
for ref in design['references']:
    ref['file']['sha256']=file_hash(root/ref['file']['path'])
write_json(root/'design.json',design)
write_json(root/'source.json',{'path':str(prior/'open_timber/scene.blend'),'sha256':file_hash(prior/'open_timber/scene.blend'),
 'previous_stage_accepted':False,'budget':'Two assembly relocations plus unchanged; no other edits.'})
print(root)
