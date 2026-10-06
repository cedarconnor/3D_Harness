"""Native positive/negative projection and occluder qualification fixtures."""
import argparse
from pathlib import Path
import sys
import bpy

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo', required=True); p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.repo)
from dcc_harness.visibility_blender import GeometryVisibility
from dcc_harness.evidence import write_json

out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x = 512; scene.render.resolution_y = 512
data = bpy.data.cameras.new('camera')
cam = bpy.data.objects.new('camera', data); scene.collection.objects.link(cam)
cam['dcc_instance_id'] = 'camera'; cam.location.z = 5; scene.camera = cam

def plane(name, left, right, z, half_height=1):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(left,-half_height,z),(right,-half_height,z),(right,half_height,z),(left,half_height,z)], [], [(0,1,2,3)])
    obj = bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj)
    obj['dcc_instance_id'] = name; obj['dcc_asset_id'] = name
    return obj

target = plane('target', -1, 1, 0)
blocker = plane('blocker', -.8, 0, 1, .8)
cases = []
def measure(name, low, high):
    result = GeometryVisibility().measure('camera', ['target'], 64)
    assert low <= result['visible_fraction'] <= high, (name,result)
    cases.append({'name': name, 'passed': True, 'fraction': result['visible_fraction'], 'target_samples': result['target_samples']})

measure('perspective-half-covered', .48, .52)
array = blocker.modifiers.new('Render divergence fixture', 'ARRAY')
array.use_relative_offset = False; array.use_constant_offset = True
array.constant_offset_displace = (.8,0,0); array.count = 2
array.show_viewport = False
try:
    GeometryVisibility()
except ValueError as exc:
    cases.append({'name':'modifier-render-viewport-mismatch-rejected','passed':True,'rejected':str(exc)})
else:
    raise AssertionError('Viewport-only geometry must not be used as render evidence')
array.show_viewport = True
measure('matched-array-fully-covered', 0, 0)
blocker.modifiers.remove(array)
subsurf = blocker.modifiers.new('Unsupported evaluation mode fixture', 'SUBSURF')
try:
    GeometryVisibility()
except ValueError as exc:
    cases.append({'name':'unsupported-modifier-rejected','passed':True,'rejected':str(exc)})
else:
    raise AssertionError('Unqualified modifier must be explicit')
blocker.modifiers.remove(subsurf)
blocker.hide_set(True)
try:
    GeometryVisibility()
except ValueError as exc:
    cases.append({'name':'viewport-hidden-render-visible-rejected','passed':True,'rejected':str(exc)})
else:
    raise AssertionError('Viewport-hidden render geometry must not be silently measured')
blocker.hide_set(False)
blocker.hide_render = True
measure('hidden-render-occluder-excluded', 1, 1)
blocker.hide_render = False; blocker.visible_camera = False
measure('camera-invisible-occluder-excluded', 1, 1)
blocker.visible_camera = True
group = bpy.data.collections.new('Occluder group'); scene.collection.children.link(group)
scene.collection.objects.unlink(blocker); group.objects.link(blocker); group.hide_render = True
measure('render-hidden-collection-excluded', 1, 1)
group.hide_render = False
scene.view_layers[0].layer_collection.children[group.name].exclude = True
measure('excluded-view-layer-branch', 1, 1)
scene.view_layers[0].layer_collection.children[group.name].exclude = False
data.type = 'ORTHO'; data.ortho_scale = 4
blocker.scale.x = 1.25; blocker.scale.y = 1.25
measure('orthographic-half-covered', .48, .52)
blocker.scale.x = 2.5; blocker.location.x = 1
measure('orthographic-fully-covered', 0, 0)
blocker.hide_render = True
data.shift_x = .12; data.shift_y = -.1
measure('shifted-orthographic-camera', 1, 1)
data.type = 'PERSP'
measure('shifted-perspective-camera', 1, 1)
cam.scale.x = 2
try:
    GeometryVisibility().measure('camera', ['target'], 64)
except ValueError as exc:
    cases.append({'name': 'scaled-camera-rejected', 'passed': True, 'rejected': str(exc)})
else:
    raise AssertionError('Scaled camera must not return misleading coverage')
cam.scale.x = 1
for name, change, ids in (
    ('missing-target', lambda: None, ['missing']),
    ('hidden-target', lambda: setattr(target,'hide_render',True), ['target']),
    ('outside-frame', lambda: (setattr(target,'hide_render',False), setattr(target.location,'x',100)), ['target']),
    ('behind-camera', lambda: (setattr(target.location,'x',0), setattr(target.location,'z',10)), ['target'])):
    change()
    try:
        GeometryVisibility().measure('camera', ids, 64)
    except ValueError as exc:
        cases.append({'name': name, 'passed': True, 'rejected': str(exc)})
    else:
        raise AssertionError('Expected rejection: '+name)
write_json(out / 'qualification.json', {'passed': True, 'cases': cases, 'blender': bpy.app.version_string, 'native_saves': 0})
print('VISIBILITY_QUALIFIED', len(cases))
