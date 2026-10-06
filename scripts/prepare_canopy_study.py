"""Freeze the next bounded design and its references before native authoring."""
import copy
from pathlib import Path
import shutil
import sys
import urllib.request

repo = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json, write_json, file_hash
root = repo/'runs/overnight-eval-2026-10-04/01-canopy'; root.mkdir(parents=True,exist_ok=False)
prior = repo/'runs/quality-loop-2026-10-04-v2'
(root/'unchanged').mkdir(); (root/'references').mkdir()
shutil.copyfile(prior/'workshop/scene.blend',root/'unchanged/scene.blend')
for view in ('overview','garden','worktop'):
    shutil.copyfile(prior/f'workshop/{view}.png',root/f'references/{view}.png')
image_url = 'https://assets.rhs.org.uk/05836e9f-2692-012f-b4fe-e3f22d127fa9/4fb4c3ed-2669-4055-87b0-31b16182ab81/pergola.jpg?auto=format&fit=clip&fm=jpg&w=400'
request = urllib.request.Request(image_url, headers={'User-Agent':'3D-Harness local research'})
with urllib.request.urlopen(request,timeout=30) as response:
    (root/'references/rhs-pergola.jpg').write_bytes(response.read())
(root/'references/construction.md').write_text('''# Pergola construction reference
Source: https://www.rhs.org.uk/garden-features/pergolas (read 2026-10-04).
The RHS describes an open timber canopy with uprights, crossbeams and spaced laterals. It suggests roughly 2.7 m uprights to leave room for trailing plants and circulation. Use this as construction/proportion guidance, not engineering certification. Our inference: restore headroom and reduce overhead density instead of compressing the entire frame vertically.
The downloaded RHS photograph is retained for this local research exercise only. Copyright remains with its owner; it is not included in the distributable package.
''',encoding='utf-8')
def ref(name): return {'path':name,'sha256':file_hash(root/name)}
old = read_json(prior/'design.json'); obs = read_json(prior/'workshop/observation.json')
deleted = [f'ext.pergola.rafter.{i:02d}' for i in (1,3,4,5,7)]+['ext.pergola.batten.01','ext.pergola.batten.02']
contract = copy.deepcopy(old['contract'])
contract['allowed_object_prefixes'] = {'ext.pergola.':['matrix_world','bounds','dimensions']}
contract['allowed_deleted_ids'] = deleted
for iid in deleted: contract['spec']['required'].pop(iid)
queries = read_json(root.parent/'queries.json')
design = {'brief':'Improve birdbath visibility and canopy openness while preserving the selected workshop layout, original courtyard, lighting, cameras and all materials. Compare unchanged with two explicit timber arrangements. No change to birdbath, beds, furniture or paving in this stage.',
    'references':[{'id':key,'file':ref(path),'role':role,'intent':intent} for key,path,role,intent in (
        ('layout','references/overview.png','mood','Preserve workshop activity layout and arched-entry hierarchy.'),
        ('joinery','references/worktop.png','construction','Retain timber material vocabulary and coherent detailing.'),
        ('rhs-photo','references/rhs-pergola.jpg','construction','External example of an open timber garden structure.'),
        ('rhs-guidance','references/construction.md','construction','Headroom and spaced upper members; not structural certification.'))],
    'targets':[{'id':key,'intent':intent,'reference_ids':refs} for key,intent,refs in (
        ('hierarchy','Keep the inherited entrance visually primary while opening the overhead timber.',['layout','rhs-photo']),
        ('visibility','Make the birdbath recognizable from the existing garden and overview cameras.',['layout','rhs-guidance']),
        ('continuity','Preserve the selected activity layout, construction language and surfaces.',['layout','joinery']))],
    'methods':{'canopy':'Restore original vertical proportions, narrow total X span by 7%, compare five evenly spaced rafters with a central opening. Remove only explicit redundant members. Maintain end supports and knee braces.',
               'preservation':'All non-pergola native fields and all material definitions remain fixed. Source mesh definitions on retained members remain unchanged.',
               'measurement':'64x64 uniform grid over projected birdbath silhouette; opaque geometry only. Native metric is paired with real renders.'},
    'views':old['views'], 'contract':contract, 'reservations':old['reservations'],
    'visibility_contract':{'schema':'dcc.visibility.contract.v1','requirements':{
        key:{'query':query,'minimum_visible_fraction':.55,'minimum_target_samples':500} for key,query in queries.items()}}}
write_json(root/'design.json',design)
write_json(root/'source.json',{'path':str(prior/'workshop/scene.blend'),'sha256':file_hash(prior/'workshop/scene.blend'),
    'external_reference_url':image_url,'budget':'Two canopy edits plus unchanged; failures retained; no paid generation.'})
print(root)
