"""Disposable recipe qualification process. Never dispatched into an artist editor."""
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.data.bridge import recipes, addons
from dcc_harness.evidence import read_json,write_json,file_hash,digest
from dcc_harness.environments import load_profile


def preview(folder, label):
    scene = bpy.context.scene; render = scene.render
    if scene.camera is None: raise ValueError('Qualification fixture camera missing')
    keys = ('engine','resolution_x','resolution_y','resolution_percentage','filepath')
    old = {key:getattr(render,key) for key in keys}
    try:
        render.engine = 'BLENDER_WORKBENCH'; render.resolution_x = render.resolution_y = 96
        render.resolution_percentage = 100; render.filepath = str(folder / (label + '.png'))
        bpy.ops.render.render(write_still=True)
    finally:
        for key,value in old.items(): setattr(render,key,value)


def main(action, request, folder):
    profile = load_profile(request['profile']); addons.assert_profile(profile)
    args = [request['root'],request['id'],request['digest'],profile]
    if action == 'recipe_apply':
        scene = bpy.context.scene
        for obj in scene.objects:
            obj['dcc_instance_id'] = obj.name; obj['dcc_asset_id'] = obj.name
        for material in bpy.data.materials: material['dcc_material_id'] = material.name
        bundle = recipes.inspect_bundle(*args[:3]); scene.render.engine = request['engine']
        target = bpy.data.objects['Cube']
        # A shared material fixture tests explicit scope; other cases stay single-user.
        if request['case']['name'].startswith('shared'):
            shared = target.copy(); shared.data = target.data.copy(); scene.collection.objects.link(shared)
            shared['dcc_instance_id'] = 'Shared'; shared['dcc_asset_id'] = 'Shared'
            shared.location.x = 3
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'before.blend'))
        preview(folder,'before')
        selected = sorted(o.name for o in bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
        result = recipes.apply(*args,scene,'Cube',request['case']['parameters'],request['effect_id'])
        if not result['changed']: raise ValueError('No measured effect from initial invocation')
        if selected != sorted(o.name for o in bpy.context.selected_objects) or active != (bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None):
            raise ValueError('Temporary context was not restored')
        repeat = recipes.apply(*args,scene,'Cube',request['case']['parameters'],request['effect_id'])
        if repeat['output'] != result['output'] or repeat['after'] != result['after']:
            raise ValueError('Repeated application changed or duplicated the owned effect')
        preview(folder,'after')
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'candidate.blend'))
        addons.assert_profile(profile)
        return {'passed':True,'effect_id':request['effect_id'],'result':result,'repeat':repeat,
                'candidate':{'path':str(folder / 'candidate.blend'),'sha256':file_hash(folder / 'candidate.blend')},
                'context_restored':True,'previews':{name:file_hash(folder / name) for name in ('before.png','after.png')}}
    if action == 'recipe_verify':
        source = request['applied']['candidate']
        if file_hash(source['path']) != source['sha256']: raise ValueError('Candidate changed')
        bpy.ops.wm.open_mainfile(filepath=source['path'],load_ui=False)
        return recipes.verify(*args,bpy.context.scene,'Cube',request['case']['parameters'],
                              request['effect_id'],request['applied']['result'])
    raise ValueError('Unknown recipe qualification action')


action, path = sys.argv[sys.argv.index('--') + 1:]
request = read_json(path); folder = Path(path).parent; start = time.monotonic()
try:
    result = main(action,request,folder)
except Exception as exc:
    result = {'passed':False,'error':str(exc),'error_type':type(exc).__name__}
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'failed.blend'))
        result['failed_scene'] = str(folder / 'failed.blend')
    except Exception:
        result['failed_scene'] = None
result.update(elapsed_seconds=time.monotonic()-start, action=action, blender=addons.build(),
              outbound_attempts=addons.NETWORK_ATTEMPTS)
if addons.NETWORK_ATTEMPTS: result['passed'] = False
write_json(folder / (action + '-result.json'),result)
if not bpy.app.background:
    def finish_owned_gui():
        bpy.ops.wm.quit_blender()
        return None
    bpy.app.timers.register(finish_owned_gui, first_interval=.2)
