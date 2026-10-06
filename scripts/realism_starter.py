"""Create cameras/lighting only; inspect the imported kit in a disposable file."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--repo',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);root=Path(a.root);sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json
assert bpy.app.background and not (root/'starter.blend').exists()
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name='PottingShed'
s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.seed=0;s.cycles.use_denoising=True
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0;s.view_settings.gamma=1
world=bpy.data.worlds.new('AfterRainSky');world.use_nodes=True;s.world=world
env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
env.image=bpy.data.images.load(str(next((root/'assets/kloofendal_48d_partly_cloudy').glob('*.hdr'))));env.image.pack()
world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs['Color']);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
for name,pos,target,lens in [('hero',(5.5,-8.5,1.75),(0,1.35,1.4),45),('context',(-6,-5.5,2.2),(0,1.25,1.35),43),('detail',(-3.6,-3.4,1.65),(-1.2,.2,.95),50)]:
    o=bpy.data.objects.new('camera.'+name,bpy.data.cameras.new(name));s.collection.objects.link(o);o['dcc_instance_id']='camera.'+name
    o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens
    if name=='hero':s.camera=o
sun=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun','SUN'));s.collection.objects.link(sun);sun['dcc_instance_id']='light.sun'
sun.data.energy=1.4;sun.data.angle=.12;sun.data.color=(1,.94,.84);sun.rotation_euler=tuple(math.radians(v) for v in (32,-25,-28))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'starter.blend'));write_json(root/'starter-observation.json',observe())
# Read the fern library after saving the empty starter; do not resave it.
fern=root/'assets/fern_02/fern_02_2k.blend'
with bpy.data.libraries.load(str(fern),link=False) as (src,dst):dst.objects=src.objects
rows=[]
for o in dst.objects:
    if o is None:continue
    s.collection.objects.link(o);bpy.context.view_layer.update()
    rows.append({'name':o.name,'type':o.type,'dimensions':list(o.dimensions),'materials':[m.name if m else None for m in o.data.materials] if o.type=='MESH' else [],'vertices':len(o.data.vertices) if o.type=='MESH' else None})
images=[{'name':im.name,'path':im.filepath,'exists':Path(bpy.path.abspath(im.filepath)).is_file(),'packed':bool(im.packed_file)} for im in bpy.data.images if im.source=='FILE']
write_json(root/'kit-native-inspection.json',{'objects':rows,'images':images,'blender':bpy.app.version_string,'starter_has_geometry':False})
print('REALISM_STARTER_AND_KIT',len(rows))
