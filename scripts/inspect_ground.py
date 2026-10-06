"""Read-only saved-garden ground checks; this is a bounded scene qualification."""
import argparse,sys,math,hashlib
from pathlib import Path
import bpy
p=argparse.ArgumentParser()
for name in ('repo','source','receipt','out'):p.add_argument('--'+name,required=True)
p.add_argument('--inject-blade-gap',action='store_true',help='Disposable in-memory 10 mm fault; never saves the blend file')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,a.repo)
from dcc_harness.ground_blender import SurfaceSampler
from dcc_harness.ground import corridor_mask
from dcc_harness.evidence import read_json,write_json,file_hash
assert bpy.app.background
sha=file_hash(a.source);receipt=read_json(a.receipt)
bpy.ops.wm.open_mainfile(filepath=a.source,load_ui=False)
native={o.get('dcc_instance_id'):o for o in bpy.context.scene.objects}
original=SurfaceSampler([native['ext.ground'],native['ext.site.terrain']]);surface=native['ext.site.groundcover.surface'];blades=native['ext.site.groundcover.blades']
cover=SurfaceSampler([surface]);failures=[]
if a.inject_blade_gap:blades.data.vertices[0].co.z+=.01
source_knots={}
evaluated=native['ext.site.terrain'].evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
try:
    for v in mesh.vertices:
        x,y,z=evaluated.matrix_world@v.co;key=(round(x,7),round(y,7))
        source_knots[key]=max(z,source_knots.get(key,-math.inf))
finally:evaluated.to_mesh_clear()
def expected_weight(x,y):
    d=math.hypot(max(abs(x)-3.65,0),max(-.75-y,y-6.25,0));t=min(1,d/1.45)
    clear=max(1-t*t*(3-2*t),corridor_mask((x,y),[(0,-39.5),(0,-6),(0,1.6)],.82,.55),corridor_mask((x,y),[(-3.6,.85),(-4.3,1.4),(-4.7,1.8),(-4.9,2.85),(-5.4,3.2),(-6.5,3.2)],.48,.48))
    c=1-clear;return max(0,min(1,c+.16*math.sin(x*2.3+y*.6)*math.sin(y*1.9-x*.5)*4*c*(1-c)))
roots=[o.location for iid,o in native.items() if iid and iid.startswith('ext.site.broadleaf.') and iid.endswith('.wood')]
support_errors=[];expected=[]
for v in surface.data.vertices:
    x,y,z=surface.matrix_world@v.co;hit=original.sample(x,y)
    if hit is None:failures.append('Missing source support');continue
    support_errors.append(abs(z-max(hit['position'][2],source_knots.get((x,y),-math.inf))-.003))
    d=min(math.hypot(x-r.x,y-r.y) for r in roots);expected.append((expected_weight(x,y),.85*math.exp(-d*d/1.1)))
if not support_errors or max(support_errors)>2e-6:failures.append('Surface vertex support differs')
mask=surface.data.uv_layers.get('SurfaceMask');metric=surface.data.uv_layers.get('MetricUV')
mask_errors=[];metric_errors=[]
if mask is None or metric is None:failures.append('Required UV layers missing')
else:
    for loop in surface.data.loops:
        vertex=surface.data.vertices[loop.vertex_index].co
        mask_errors.extend(abs(x-y) for x,y in zip(mask.data[loop.index].uv,expected[loop.vertex_index]))
        metric_errors.extend(abs(x-y/3.15) for x,y in zip(metric.data[loop.index].uv,vertex[:2]))
    if max(mask_errors)>2e-6:failures.append('Ground transition mask differs')
    if max(metric_errors)>2e-6:failures.append('Soil texture scale differs')
mat=surface.data.materials[0]
node=mat.node_tree.nodes.get('Ground transition mask')
if node is None or getattr(node,'uv_map',None)!='SurfaceMask':failures.append('Shader reads wrong mask UV')
if surface.data.uv_layers.active is None or surface.data.uv_layers.active.name!='MetricUV' or metric is None or not metric.active_render:failures.append('Active metric UV differs')
# Sampling source vertices alone misses interpolation through an open boundary.
clearances=[]
for j in range(260):
    for i in range(260):
        x=-16.1875+i*.125;y=-16.1875+j*.125
        old=original.sample(x,y);new=cover.sample(x,y)
        if old is None or new is None:failures.append('Missing interior support');continue
        clearances.append(new['position'][2]-old['position'][2])
if not clearances or min(clearances)<.00299:failures.append('Terrain protrudes through ground cover between vertices')
blade_errors=[];core_vertices=0
if len(blades.data.vertices)%5:failures.append('Unexpected blade layout')
for i,v in enumerate(blades.data.vertices):
    x,y,z=blades.matrix_world@v.co
    if expected_weight(x,y)<=1e-8:core_vertices+=1
    if i%5<2:
        hit=cover.sample(x,y)
        if hit is None:failures.append('Missing blade support');continue
        blade_errors.append(abs(z-hit['position'][2]-.0008))
if core_vertices:failures.append('Grass vertices enter declared clear core')
if not blade_errors or max(blade_errors)>2e-6:failures.append('Blade root support differs')
surface.data.calc_loop_triangles();blades.data.calc_loop_triangles()
added_triangles=len(surface.data.loop_triangles)+len(blades.data.loop_triangles)
if added_triangles>120000:failures.append('Added triangle budget exceeded')
images=[]
source_files={asset['asset']+'_'+f['channel']+'_2k.jpg':f for asset in receipt['assets'] for f in asset['files']}
for im in bpy.data.images:
    if not im.name.startswith(('grass_ground_','leafy_grass_')):continue
    packed=bool(im.packed_file);expected_color='sRGB' if '_Diffuse' in im.name else 'Non-Color'
    if not packed or im.colorspace_settings.name!=expected_color:failures.append('New image is not correctly packed/tagged')
    digest=hashlib.sha256(bytes(im.packed_file.data)).hexdigest() if packed else None
    record=source_files.get(im.name)
    if record is None or digest!=record['sha256']:failures.append('Packed image differs from source receipt')
    images.append({'name':im.name,'packed':packed,'colorspace':im.colorspace_settings.name,'sha256':digest})
if len(images)!=6:failures.append('Expected six packed source maps')
for asset in receipt['assets']:
    for record in asset['files']:
        texture=mat.node_tree.nodes.get(asset['asset']+'.'+record['channel'])
        incoming=texture.inputs['Vector'].links if texture and texture.type=='TEX_IMAGE' else []
        scale=incoming[0].from_node if incoming else None
        if scale is None or scale.type!='VECT_MATH' or scale.operation!='SCALE' or abs(scale.inputs[3].default_value-1/asset['tile_m'])>1e-6:
            failures.append('World texture scale differs from source receipt')
        elif not scale.inputs[0].links or scale.inputs[0].links[0].from_node.type!='NEW_GEOMETRY' or scale.inputs[0].links[0].from_socket.name!='Position':
            failures.append('Texture scaling does not read world position')
assert file_hash(a.source)==sha
write_json(a.out,{'passed':not failures,'failures':sorted(set(failures)),'checkpoint_sha256':sha,'blender':bpy.app.version_string,
 'surface_vertices_tested':len(support_errors),'max_surface_support_error_m':max(support_errors,default=None),
 'mask_components_tested':len(mask_errors),'max_mask_error':max(mask_errors,default=None),'max_metric_uv_error':max(metric_errors,default=None),
 'blade_base_vertices_tested':len(blade_errors),'max_blade_support_error_m':max(blade_errors,default=None),'grass_vertices_in_clear_core':core_vertices,
 'added_triangles':added_triangles,'new_images':images,'native_saves':0,
 'interior_samples':len(clearances),'minimum_interior_clearance_m':min(clearances,default=None),'intentional_blade_gap':a.inject_blade_gap,
 'limits':'Declared vertex and interior samples, UV mask, shader binding and source images only. Not continuous surface proof, arbitrary collision, navigation, botanical or artist acceptance.'})
print('GROUND_NATIVE',not failures,sorted(set(failures)),added_triangles)
if failures:raise RuntimeError('Ground validation failed')
