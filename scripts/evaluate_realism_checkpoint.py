"""Independent saved-file realism evaluation. Exit 0 means evaluation completed."""
import argparse,sys,time
from pathlib import Path
import bpy
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--before',required=True);p.add_argument('--contract',required=True);p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--observe-only',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import file_hash,read_json,write_json
assert bpy.app.background
source=Path(a.source);sha=file_hash(source);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
before=read_json(a.before);obs=observe();write_json(out/'observation.json',obs)
contract=read_json(a.contract);check=evaluate_stage(before,obs,contract);write_json(out/'check.json',check)
failures=[];s=bpy.context.scene
if len(bpy.data.scenes)!=1 or len(bpy.data.libraries):failures.append('Expected one scene and no linked libraries')
if len(s.objects)>2000:failures.append('Object budget exceeded')
if sum(o.get('triangles',0) for o in obs['objects'].values())>2500000:failures.append('Evaluated triangle budget exceeded')
if {o.get('dcc_instance_id') for o in s.objects if o.type=='CAMERA'}!={'camera.hero','camera.context','camera.detail'}:failures.append('Camera identities differ')
if {o.get('dcc_instance_id') for o in s.objects if o.type=='LIGHT'}!={'light.sun'}:failures.append('Light identities differ')
image_records=[]
for im in bpy.data.images:
    if im.source!='FILE' or not im.users:continue
    packed=bool(im.packed_file or im.packed_files)
    image_records.append({'name':im.name,'packed':packed,'colorspace':im.colorspace_settings.name})
    if any(tag in im.name.lower() for tag in ('_rough','_nor_gl','_disp','_alpha')) and im.colorspace_settings.name!='Non-Color':
        failures.append('Data map is not Non-Color: '+im.name)
    if not packed:failures.append('Unpacked used image: '+im.name)
    else:im.filepath=str(out/'absent-external-path'/Path(im.filepath).name)
# Real native binding, not just a named material in bpy.data.
native={o.get('dcc_instance_id'):o for o in s.objects}
for iid in ('ext.bench.top','ext.building.facade','ext.building.door','ext.fern.hero'):
    o=native.get(iid)
    if o is None or o.type!='MESH' or not o.data.polygons:failures.append('Missing substantive target '+iid);continue
    if not any(slot.material and slot.material.use_nodes for slot in o.material_slots):failures.append('No actual node material on '+iid)
metal=next((m for m in bpy.data.materials if m.get('dcc_material_id')=='metal'),None)
node=metal.node_tree.nodes.get('Principled BSDF') if metal and metal.use_nodes else None
if node is None or node.inputs['Roughness'].is_linked:failures.append('Shared metal scalar roughness control missing/linked')
if metal and not any(o.type=='MESH' and any(slot.material==metal for slot in o.material_slots) and any(poly.material_index==idx for poly in o.data.polygons) for o in s.objects for idx,slot in enumerate(o.material_slots) if slot.material==metal):failures.append('Metal has no assigned faces')
for iid,prefix in (('ext.building.facade','red_brick'),('ext.bench.top','weathered_brown_planks'),('ext.ground','forest_ground_04')):
    o=native.get(iid); reachable_images=set()
    if o and o.type=='MESH':
        for idx,slot in enumerate(o.material_slots):
            mat=slot.material
            if not mat or not mat.use_nodes or not any(f.material_index==idx for f in o.data.polygons):continue
            pending=[n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output];seen=set()
            while pending:
                n=pending.pop()
                if n in seen:continue
                seen.add(n)
                if n.type=='TEX_IMAGE' and n.image:reachable_images.add(n.image.name)
                pending.extend(link.from_node for socket in n.inputs for link in socket.links)
    if not any(n.startswith(prefix) and '_diff' in n.lower() for n in reachable_images):failures.append('Required PBR color image not in used material output graph: '+iid)
captures=[]
if not a.observe_only:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    s.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
    for view in ('hero','context','detail'):
        cam=native.get('camera.'+view)
        if cam is None:continue
        s.camera=cam;s.render.filepath=str(out/(view+'.png'));start=time.perf_counter();bpy.ops.render.render(write_still=True)
        captures.append({'view':view,'path':view+'.png','sha256':file_hash(out/(view+'.png')),'seconds':time.perf_counter()-start,'matrix':[list(row) for row in cam.matrix_world],'lens':cam.data.lens})
assert file_hash(source)==sha
write_json(out/'report.json',{'passed':check['passed'] and not failures,'check_passed':check['passed'],'extra_failures':failures,'source_sha256':sha,'source_unchanged':True,'native_saves':0,'blender':bpy.app.version_string,'evaluator_sha256':file_hash(__file__),'contract_sha256':file_hash(a.contract),'before_sha256':file_hash(a.before),'images':image_records,'captures':captures,'limits':'Scoped observed preservation and named requirements; not general topology, UV quality, collision, material realism, visual quality or artist acceptance. Packed-image paths are invalidated in the disposable renderer only.'})
print('REALISM_EVALUATED',check['passed'] and not failures,len(captures))
