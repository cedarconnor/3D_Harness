"""Create disposable positive/negative native inputs; no creative trial assets."""
import argparse,sys
from pathlib import Path
import bpy
p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);root=Path(a.root)
assert bpy.app.background
out=root/'evaluator-fixtures';out.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(root/'starter.blend'),load_ui=False)
def mat(mid,asset=None):
    m=bpy.data.materials.new(mid);m.use_nodes=True;m['dcc_material_id']=mid
    if asset:
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(next((root/'assets'/asset).glob('*_diff_2k.*'))));n.image.pack();m.node_tree.links.new(n.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m
materials={'brick':mat('brick','red_brick'),'timber':mat('timber','weathered_brown_planks'),'ground':mat('ground','forest_ground_04'),'metal':mat('metal'),'plain':mat('plain')}
materials['metal'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.38
for iid,aid,mid,size,loc in [('ext.building.facade','building','brick',(6,.25,3),(0,1.4,1.5)),('ext.building.door','building','plain',(.95,.05,2.1),(1.35,1.2,1.05)),('ext.bench.top','bench','timber',(1.8,.65,.06),(-1.2,.25,.87)),('ext.ground','ground','ground',(10,10,.1),(0,0,-.05)),('ext.prop.pot','pot','plain',(.2,.2,.3),(0,0,.15)),('ext.prop.tool','tool','plain',(.3,.1,.05),(0,-1,.05)),('ext.hardware','hardware','metal',(.1,.1,.1),(2,0,.1))]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=iid;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o['dcc_instance_id']=iid;o['dcc_asset_id']=aid;o.data.materials.append(materials[mid])
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.2,location=(1,-1,.2));o=bpy.context.object;o.name='ext.fern.hero';o['dcc_instance_id']='ext.fern.hero';o['dcc_asset_id']='foliage';o.data.materials.append(materials['plain'])
# A real connected data map for the colorspace fault.
m=materials['brick'];n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(next((root/'assets/red_brick').glob('*_nor_gl_2k.*'))));n.image.colorspace_settings.name='Non-Color';n.image.pack();nm=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(n.outputs['Color'],nm.inputs['Color']);m.node_tree.links.new(nm.outputs['Normal'],m.node_tree.nodes['Principled BSDF'].inputs['Normal'])
bpy.ops.wm.save_as_mainfile(filepath=str(out/'valid.blend'))
for name in ('wrong-bench','camera-drift','roughness-drift','metal-decoy','data-colorspace','unpacked-image'):
    bpy.ops.wm.open_mainfile(filepath=str(out/'valid.blend'),load_ui=False)
    if name=='wrong-bench':bpy.data.objects['ext.bench.top'].scale.x=1.2
    elif name=='camera-drift':bpy.data.objects['camera.hero'].location.x+=.2
    elif name=='roughness-drift':bpy.data.materials['metal'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
    elif name=='metal-decoy':bpy.data.objects['ext.hardware'].data.polygons.foreach_set('material_index',[1]*6);bpy.data.objects['ext.hardware'].data.materials.append(bpy.data.materials['plain'])
    elif name=='data-colorspace':next(im for im in bpy.data.images if '_nor_gl' in im.name).colorspace_settings.name='sRGB'
    elif name=='unpacked-image':
        im=next(im for im in bpy.data.images if '_diff' in im.name);im.unpack(method='REMOVE');im.filepath=str(root/'assets/red_brick'/next((root/'assets/red_brick').glob('*_diff_2k.*')).name)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'.blend')))
print('CREATED_REALISM_FIXTURES')
