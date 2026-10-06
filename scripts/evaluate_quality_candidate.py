"""Observe, measure and render one immutable quality candidate in fresh Blender."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Vector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo', required=True); p.add_argument('--round', required=True); p.add_argument('--candidate', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.repo)
from dcc_harness.evidence import read_json, write_json, file_hash, digest
from dcc_harness.continuity_blender import observe
from dcc_harness.visibility_blender import observe_visibility

root = Path(a.round).resolve(); out = root / a.candidate
assert out.resolve().is_relative_to(root) and out.is_dir()
source = out / 'scene.blend'; native_hash = file_hash(source)
design = read_json(root / 'design.json')
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
obs = observe(); write_json(out / 'observation.json', obs)
if 'visibility_contract' in design:
    queries = {key: rule['query'] for key,rule in design['visibility_contract']['requirements'].items()}
    write_json(out / 'visibility.json', observe_visibility(queries, obs))
scene = bpy.context.scene
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for d in prefs.devices: d.use = d.type == 'OPTIX'
scene.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
images, captures = {}, {}
for view in design['views']:
    settings, camera = view['render'], view['camera']
    scene.render.engine = settings['engine']
    scene.render.resolution_x, scene.render.resolution_y = settings['resolution']
    scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = 'PNG'
    scene.cycles.samples = settings['samples']; scene.cycles.seed = settings['seed']
    scene.cycles.use_denoising = settings['denoising']
    if 'object_id' in camera:
        cam = next(o for o in scene.objects if o.get('dcc_instance_id') == camera['object_id'])
    else:
        box = obs['objects'][camera['anchor_id']]['bounds']
        center = Vector([(box[0][i]+box[1][i])/2 for i in range(3)])
        cam = bpy.data.objects.new('ReviewOnly', bpy.data.cameras.new('ReviewOnly'))
        scene.collection.objects.link(cam); cam.location = center + Vector(camera['offset'])
        cam.rotation_euler = (center-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens = camera['lens']
    scene.camera = cam
    path = out / (view['id']+'.png')
    if path.exists(): raise FileExistsError(path)
    scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    images[view['id']] = {'path': path.relative_to(root).as_posix(), 'sha256': file_hash(path)}
    captures[view['id']] = {'matrix': [list(row) for row in cam.matrix_world], 'lens': cam.data.lens,
                            'settings': settings, 'color': obs['scene']['color'], 'device': scene.cycles.device}
assert file_hash(source) == native_hash
write_json(out / 'captures.json', captures)
write_json(out / 'renders.json', {'schema':'dcc.quality.renders.v1','checkpoint_sha256':native_hash,
                                'views_digest':digest(design['views']), 'images':images})
print('QUALITY_EVALUATED', a.candidate)
