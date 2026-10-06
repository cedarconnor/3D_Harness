"""Read-only final presentation and packed-dependency reopen on a saved file."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Vector
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',required=True);p.add_argument('--source',required=True);p.add_argument('--design',required=True);p.add_argument('--out',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert bpy.app.background
sys.path.insert(0,a.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import read_json,write_json,file_hash
out=Path(a.out);out.mkdir(exist_ok=False);source=Path(a.source);sha=file_hash(source)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
obs=observe();write_json(out/'observation.json',obs)
assert not obs['issues'],obs['issues']
assert len(bpy.data.scenes)==1 and len(bpy.data.libraries)==0
images=[]
for im in bpy.data.images:
    if im.source!='FILE': continue
    packed=bool(im.packed_file or im.packed_files)
    assert packed,('Unpacked dependency',im.name)
    missing=out/'intentionally-absent'/Path(im.filepath).name
    assert not missing.exists()
    images.append({'name':im.name,'packed':packed,'original_path':im.filepath,'test_path':str(missing)})
    im.filepath=str(missing)
scene=bpy.context.scene;prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.seed=0;scene.cycles.use_denoising=True
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
captures={}
views=list(read_json(a.design)['views'])
views.append({'id':'foreground-detail','camera':{'target':[7.81,-7.13,.22],'offset':[1.8,-4.4,3.2],'lens':35}})
for view in views:
    definition=view['camera']
    if 'object_id' in definition:
        cam=next(o for o in scene.objects if o.get('dcc_instance_id')==definition['object_id'])
    else:
        if 'target' in definition:
            center=Vector(definition['target'])
        else:
            box=obs['objects'][definition['anchor_id']]['bounds'];center=Vector([(box[0][i]+box[1][i])/2 for i in range(3)])
        cam=bpy.data.objects.new('PresentationOnly',bpy.data.cameras.new('PresentationOnly'));scene.collection.objects.link(cam)
        cam.location=center+Vector(definition['offset']);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=definition['lens']
    scene.camera=cam;path=out/(view['id']+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    captures[view['id']]={'path':path.name,'sha256':file_hash(path),'matrix':[list(row) for row in cam.matrix_world],'lens':cam.data.lens}
assert file_hash(source)==sha
write_json(out/'presentation.json',{'checkpoint_sha256':sha,'observed_revision':obs['revision'],'source_unchanged':True,'native_saves':0,
 'blender':bpy.app.version_string,'images':images,'captures':captures,'resolution':[1920,1080],'samples':64,'device':scene.cycles.device,
 'limits':'Read-only presentation renders; image paths were intentionally invalidated in memory to check packed dependencies. Higher resolution is not a quality score. No artist or export acceptance.'})
print('PRESENTATION_AND_PACKING_PASS',len(captures),len(images))
