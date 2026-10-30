"""Disposable recipe qualification process. Never dispatched into an artist editor."""
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.data.bridge import recipes, addons
from dcc_harness.evidence import read_json,write_json,file_hash,digest
from dcc_harness.environments import load_profile


def preview(folder, label, *, shader=False):
    scene = bpy.context.scene; render = scene.render
    if scene.camera is None: raise ValueError('Qualification fixture camera missing')
    keys = ('engine','resolution_x','resolution_y','resolution_percentage','filepath')
    old = {key:getattr(render,key) for key in keys}
    samples=scene.cycles.samples
    try:
        if shader and render.engine not in ('CYCLES','BLENDER_EEVEE','BLENDER_EEVEE_NEXT'):
            raise ValueError('Shader qualification requires a shader-capable declared render engine')
        render.engine = render.engine if shader else 'BLENDER_WORKBENCH'
        scene.cycles.samples=8
        render.resolution_x = render.resolution_y = 96
        render.resolution_percentage = 100; render.filepath = str(folder / (label + '.png'))
        bpy.ops.render.render(write_still=True)
    finally:
        for key,value in old.items(): setattr(render,key,value)
        scene.cycles.samples=samples


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
        effect=bundle['recipe'].get('effect',{})
        if effect.get('kind')=='shader_nodes' and effect['material_id']!='{effect_name}':
            # Seed the declared input identity in this owned factory fixture.
            # Never pre-create a template-owned output (that would be adoption).
            while len(target.data.materials)<=effect['slot']:
                target.data.materials.append(None)
            if target.material_slots[effect['slot']].material is None:
                material=bpy.data.materials.new('Qualification input')
                material.use_nodes=True
                target.material_slots[effect['slot']].material=material
            target.material_slots[effect['slot']].material['dcc_material_id']=effect['material_id']
        # A shared material fixture tests explicit scope; other cases stay single-user.
        if request['case']['name'].startswith('shared'):
            shared = target.copy(); shared.data = target.data.copy(); scene.collection.objects.link(shared)
            shared['dcc_instance_id'] = 'Shared'; shared['dcc_asset_id'] = 'Shared'
            shared.location.x = 3
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'before.blend'))
        # The qualifier operates on a saved input, just like managed execution.
        # Factory startup may contain unused zero-user data absent from a saved
        # file (for example Dots Stroke); it is not part of that input contract.
        bpy.ops.wm.open_mainfile(filepath=str(folder / 'before.blend'),load_ui=False)
        scene=bpy.context.scene
        target=scene.objects['Cube']
        if not bpy.app.background:
            yield .1  # Resume operators only after the loaded UI context settles.
        shader=bundle['recipe'].get('effect',{}).get('kind') in ('material','shader_nodes')
        preview(folder,'before',shader=shader)
        selected = sorted(o.name for o in bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
        result = yield from apply_steps(args,scene,request,folder / 'first-async')
        if not result['changed']: raise ValueError('No measured effect from initial invocation')
        if selected != sorted(o.name for o in bpy.context.selected_objects) or active != (bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None):
            raise ValueError('Temporary context was not restored')
        repeat = yield from apply_steps(args,scene,request,folder / 'repeat-async')
        if repeat['output'] != result['output'] or repeat['after'] != result['after']:
            raise ValueError('Repeated application changed or duplicated the owned effect')
        preview(folder,'after',shader=shader)
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


def apply_steps(args,scene,request,folder):
    call=(*args,scene,'Cube',request['case']['parameters'],request['effect_id'])
    bundle=recipes.inspect_bundle(*args[:3])
    if bundle['recipe']['invocation']['completion']=='synchronous':
        return recipes.apply(*call)
    from dcc_harness.data.bridge import recipe_v2
    execution=recipe_v2.start(*call,folder=folder)
    while True:
        status=execution.step()
        if status['state']=='SUCCEEDED':
            return status['result']
        if status['state']!='PENDING':
            raise ValueError('Asynchronous qualification '+status['state']+': '+status.get('error',status.get('reason','')))
        yield status['poll_interval']


action, path = sys.argv[sys.argv.index('--') + 1:]
request = read_json(path); folder = Path(path).parent; start = time.monotonic()
pending=main(action,request,folder)


def quit_owned_gui():
    """Quit on a fresh UI tick with a window that survived file loading.

    open_mainfile invalidates the invoking timer's context. Calling quit in that
    same callback can pass a null window to Blender's delayed-exit scheduler.
    Only this disposable owned process uses the callback; artist editors do not.
    """
    manager = bpy.context.window_manager
    window = next((window for window in manager.windows if window.screen is not None), None) if manager else None
    if window is None:
        return .1
    with bpy.context.temp_override(window=window):
        bpy.ops.wm.quit_blender()
    return None


def advance():
    try:
        return next(pending)
    except StopIteration as done:
        result=done.value
    except Exception as exc:
        result={'passed':False,'error':str(exc),'error_type':type(exc).__name__}
        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'failed.blend'))
            result['failed_scene']=str(folder / 'failed.blend')
        except Exception:
            result['failed_scene']=None
    result.update(elapsed_seconds=time.monotonic()-start,action=action,blender=addons.build(),
                  outbound_attempts=addons.NETWORK_ATTEMPTS)
    if addons.NETWORK_ATTEMPTS: result['passed']=False
    write_json(folder / (action+'-result.json'),result)
    if not bpy.app.background:
        bpy.app.timers.register(quit_owned_gui,first_interval=.1)
    return None


if bpy.app.background:
    interval=advance()
    while interval is not None:
        time.sleep(interval)
        interval=advance()
else:
    bpy.app.timers.register(advance,first_interval=.1,persistent=True)
