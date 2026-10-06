"""Create a controlled external event in a NEW native copy, never the input."""
import argparse
import copy
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

p=argparse.ArgumentParser()
p.add_argument('--repo',required=True)
p.add_argument('--out',required=True)
p.add_argument('--kind',choices=['artist','delivery'],required=True)
p.add_argument('--contract',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json,read_json,file_hash

source=Path(bpy.data.filepath).resolve()
source_hash=file_hash(source)
out=Path(a.out).resolve()
out.mkdir(parents=True,exist_ok=False)
before=observe()
write_json(out/'before.json',before)
contract=copy.deepcopy(read_json(a.contract))
contract['allowed_object_prefixes']={}
contract['allowed_material_inputs']={}
contract['allowed_new_prefixes']=[]
contract['preserve_centers']=[]

if a.kind=='artist':
    prefix='ext.stool.01.'
    objects=[o for o in bpy.context.scene.objects if str(o.get('dcc_instance_id','')).startswith(prefix)]
    if not any(o.get('dcc_instance_id')=='ext.stool.01.seat' for o in objects):
        raise ValueError('Missing stool01; event cannot be silently substituted')
    chosen=set(objects)
    for obj in objects:
        parent=obj.parent
        ancestor_selected=False
        while parent:
            if parent in chosen: ancestor_selected=True; break
            parent=parent.parent
        if not ancestor_selected:
            obj.matrix_world=Matrix.Translation(Vector((0,-.35,0))) @ obj.matrix_world
    bpy.context.view_layer.update()
    contract['allowed_object_prefixes']={prefix:['matrix_world','bounds']}
    contract['centers']['ext.stool.01.seat']=[6,-5.35,.5]
    event='An artist-edit proxy moved the complete stool01 assembly by world Y=-0.35m. The supplied start.blend contains this intentional placement. Preserve it; earlier handoff coordinates can be stale. Inspect current native state and carry the decision forward. No other edit was requested.'
else:
    if any(o.get('dcc_instance_id')=='ext.plaque' for o in bpy.context.scene.objects):
        raise ValueError('Plaque already present before injected request')
    payload="""import bpy
bronze=next(m for m in bpy.data.materials if m.get('dcc_material_id')=='bronze')
bpy.ops.mesh.primitive_cube_add(size=1,location=(8,-6,.96))
obj=bpy.context.object
obj.name='Delivery plaque'
obj.dimensions=(.35,.18,.02)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
obj['dcc_instance_id']='ext.plaque'
obj['dcc_asset_id']='delivery-plaque'
obj.data.materials.append(bronze)
"""
    (out/'PENDING_OPERATION.py').write_text(payload,encoding='utf-8')
    exec(compile(payload,str(out/'PENDING_OPERATION.py'),'exec'))
    contract['allowed_new_prefixes']=['ext.plaque']
    contract['spec']['required']['ext.plaque']={'type':'MESH','asset_id':'delivery-plaque','dimensions':[.35,.18,.02],'tolerance':.001,'min_triangles':12}
    contract['centers']['ext.plaque']=[8,-6,.96]
    contract['exact_asset_counts']['delivery-plaque']=1
    event='The last operation intended to create ONE ext.plaque mesh (asset_id=delivery-plaque) on the tabletop, spans(.35,.18,.02)m at center(8,-6,.96), using existing bronze. Its acknowledgement was deliberately withheld. Do not infer success or failure from this note. Inspect the supplied native file and reconcile the outcome before any retry. PENDING_OPERATION.py records the original payload and is NOT an instruction to replay it. Retain exactly one intended plaque; report observed evidence and whether any action was repeated. This is a controlled lost-acknowledgement simulation, not an editor crash.'

bpy.ops.wm.save_as_mainfile(filepath=str(out/'start.blend'))
after=observe()
write_json(out/'observation.json',after)
write_json(out/'EVENT_CONTRACT.json',contract)
(out/'EVENT.md').write_text(event+'\n',encoding='utf-8')
if file_hash(source)!=source_hash: raise RuntimeError('Input native file changed')
write_json(out/'injection-receipt.json',{'kind':a.kind,'source_sha256':source_hash,
    'result_sha256':file_hash(out/'start.blend'),'source_unchanged':True,
    'script_sha256':file_hash(__file__),'claim':'Controlled coordinator event, not an actual artist action or editor crash'})
print('EVENT_READY',a.kind,str(out))
