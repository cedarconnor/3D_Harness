"""Only retained, qualified bundles may reach invocation. Discovery stays import-free."""
from contextlib import contextmanager
import importlib
from pathlib import Path
import types
import bpy
from . import addons, inspection
try:
    from .recipe_store import load
    from .recipe_schema import validate_parameters, sha
    from .evidence import digest
    from .continuity_blender import measure_live
    from .files import file_hash, reject_links
except ModuleNotFoundError:
    from dcc_harness.recipe_store import load
    from dcc_harness.recipe_schema import validate_parameters, sha
    from dcc_harness.evidence import digest
    from dcc_harness.continuity_blender import measure_live
    from dcc_harness.files import file_hash, reject_links


def inspect_bundle(root, recipe_id, identity):
    return load(root, recipe_id, identity)


def measurements(scene, target_id, fields):
    obj = inspection.target(scene, target_id)
    current = measure_live(scene); record = current['objects'][target_id]
    if current['issues']: raise ValueError('UNSUPPORTED_COVERAGE: ' + '; '.join(current['issues']))
    result = {}
    for field in fields:
        if field == 'geometry':
            result[field] = {k:record[k] for k in ('source_mesh_hash','source_uv_hash','source_attribute_hash','geometry_hash') if k in record}
        elif field == 'transform': result[field] = [list(row) for row in obj.matrix_world]
        elif field == 'modifiers': result[field] = record.get('modifier_settings', [])
        elif field in ('materials','nodes'):
            result[field] = {mid:current['materials'][mid] for mid in record['material_ids'] if mid is not None}
            result['material_users'] = {mid:sorted(o.get('dcc_instance_id', '') for o in bpy.data.objects
                if any(slot.material and slot.material.get('dcc_material_id') == mid for slot in o.material_slots))
                for mid in result[field]}
        elif field == 'properties':
            result[field] = {key:inspection.plain(value) for key,value in obj.items() if not key.startswith('dcc_')}
        else: raise ValueError('Unsupported measurement scope')
    digest(result)
    return result


@contextmanager
def context_for(scene, obj):
    if scene != bpy.context.scene or obj.mode != 'OBJECT': raise ValueError('UNSUPPORTED_CONTEXT: Object mode required')
    selected = list(bpy.context.selected_objects); active = bpy.context.view_layer.objects.active
    try:
        for item in selected: item.select_set(False)
        obj.select_set(True); bpy.context.view_layer.objects.active = obj
        area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None) if not bpy.app.background and bpy.context.screen else None
        override = {'active_object':obj,'object':obj,'selected_objects':[obj],'selected_editable_objects':[obj]}
        if area:
            override.update(area=area, region=next(r for r in area.regions if r.type == 'WINDOW'))
        with bpy.context.temp_override(**override): yield
    finally:
        for item in list(bpy.context.selected_objects): item.select_set(False)
        for item in selected:
            if item.name in bpy.context.view_layer.objects: item.select_set(True)
        if active and active.name in bpy.context.view_layer.objects: bpy.context.view_layer.objects.active = active
        else: bpy.context.view_layer.objects.active = None


def adapter_for(bundle):
    # Compile retained bytes directly: no pyc writes inside the immutable bundle.
    source = reject_links(bundle['adapter']).read_bytes()
    if file_hash(bundle['adapter']) != bundle['manifest']['files']['adapter.py']: raise ValueError('Adapter changed')
    module = types.ModuleType('dcc_recipe_' + bundle['digest'])
    module.__file__ = bundle['adapter']; exec(compile(source, bundle['adapter'], 'exec'), module.__dict__)
    return module


def prepare_context(root, recipe_id, identity, profile, scene, target, parameters, effect_id, *, verify=False):
    bundle = load(root, recipe_id, identity); recipe = bundle['recipe']
    validate_parameters(recipe, parameters); sha(effect_id)
    addons.assert_profile(profile)
    provider = next((p for p in profile['providers'] if p['id'] == recipe['provider']['id']), None)
    if provider is None or provider['source_digest'] != recipe['provider']['source_digest']:
        raise ValueError('STALE: recipe provider does not match profile')
    compat = recipe['compatibility']; mode = 'background' if bpy.app.background else 'live'
    obj = inspection.target(scene, target)
    if (not compat['blender_min'] <= list(bpy.app.version) < compat['blender_max']
            or scene.render.engine not in compat['engines'] or obj.type not in compat['target_types']
            or (not verify and mode not in compat['contexts'])):
        raise ValueError('UNSUPPORTED_CONTEXT: recipe compatibility')
    context = {'scene':scene, 'target':obj, 'target_id':target, 'assets':bundle['assets'],
               'effect_name':'DCC::' + effect_id[:48],
               'recipe':recipe, 'parameters':parameters, 'effect_id':effect_id, 'provider':provider,
               'mode':mode, 'shared_users':sorted({o.get('dcc_instance_id','') for o in bpy.data.objects
                   if any(s.material and any(t.material == s.material for t in obj.material_slots) for s in o.material_slots)})}
    if recipe['update']['shared_materials'] == 'none' and 'materials' in recipe['coverage']['writes']:
        raise ValueError('Material edits require explicit shared user policy')
    return bundle, context


def invoke_declared(context, **kwargs):
    recipe = context['recipe']; invocation = recipe['invocation']; entry = invocation['entry']
    provider = context['provider']; kind = invocation['kind']
    if kind == 'python_function':
        module_name, _, name = entry.rpartition('.')
        if module_name != provider['module'] and not module_name.startswith(provider['module'] + '.'):
            raise ValueError('Entry point does not belong to the pinned provider')
        function = getattr(importlib.import_module(module_name), name)
        return function(context, context['parameters'], context['effect_id'])
    if kind == 'operator':
        group,name = entry.split('.')
        operator = getattr(getattr(bpy.ops,group),name)
        cls = bpy.types.Operator.bl_rna_get_subclass_py(operator.get_rna_type().identifier)
        if cls is None or not (cls.__module__ == provider['module'] or cls.__module__.startswith(provider['module'] + '.')):
            raise ValueError('Operator provider ownership is unknown')
        if not operator.poll(): raise ValueError('UNSUPPORTED_CONTEXT: operator poll failed')
        status = operator('EXEC_DEFAULT', **kwargs)
        if status != {'FINISHED'}: raise ValueError('Unsupported incomplete/modal operator result')
        return {'status':'FINISHED'}
    if kind == 'node_asset':
        if set(kwargs) != {'asset'} or kwargs['asset'] not in context['assets']: raise ValueError('Explicit retained node asset required')
        path = context['assets'][kwargs['asset']]; asset_hash = file_hash(path)
        if asset_hash not in provider['files'].values(): raise ValueError('Node asset is not part of the pinned provider')
        obj = context['target']; name = context['effect_name']
        mod = obj.modifiers.get(name)
        if mod and mod.type != 'NODES': raise ValueError('Effect slot belongs to a different modifier')
        if mod is None:
            with bpy.data.libraries.load(path, link=False) as (source, destination):
                if entry not in source.node_groups: raise ValueError('Node asset group is missing')
                destination.node_groups = [entry]
            tree = destination.node_groups[0]
            tree['dcc_asset_source'], tree['dcc_asset_group'] = asset_hash, entry
            mod = obj.modifiers.new(name, 'NODES'); mod.node_group = tree
        if mod.node_group.get('dcc_asset_source') != asset_hash: raise ValueError('Effect source changed')
        return {'status':'FINISHED'}
    raise ValueError('Unsupported invocation kind')


def output_record(adapter, context):
    output = adapter.inspect_output(context, context['effect_id'])
    if (not isinstance(output,dict) or set(output) != {'effect_id','effect_count','measurements'}
            or output['effect_id'] != context['effect_id'] or type(output['effect_count']) is not int
            or output['effect_count'] != 1 or not isinstance(output['measurements'],dict) or not output['measurements']):
        raise ValueError('Actual output needs exactly one measured owned effect')
    digest(output)
    return output


def other_materials(scene, target):
    current = measure_live(scene)
    return {key:{'bindings':record['material_ids'], 'materials':{
        mid:current['materials'][mid] for mid in record['material_ids'] if mid is not None}}
        for key,record in current['objects'].items() if key != target}


@addons.offline_call
def apply(root, recipe_id, identity, profile, scene, target, parameters, effect_id):
    bundle, context = prepare_context(root, recipe_id, identity, profile, scene, target, parameters, effect_id)
    recipe = bundle['recipe']; scope = sorted(set(sum(recipe['coverage'].values(), [])))
    before = measurements(scene, target, scope)
    protected_materials = other_materials(scene,target) if recipe['update']['shared_materials']=='single_user_copy' else None
    shared = [(index,slot.material) for index,slot in enumerate(context['target'].material_slots) if slot.material
              and any(o != context['target'] and any(s.material == slot.material for s in o.material_slots) for o in bpy.data.objects)]
    adapter = adapter_for(bundle); called = []
    def invoke(**kwargs):
        called.append(recipe['invocation']); return invoke_declared(context, **kwargs)
    context['invoke'] = invoke
    with context_for(scene, context['target']):
        preflight = adapter.preflight(context, parameters)
        if measurements(scene,target,scope) != before: raise ValueError('Preflight mutated declared state')
        if not isinstance(preflight,dict) or preflight.get('ready') is not True: raise ValueError('UNSUPPORTED_CONTEXT: adapter preflight')
        if recipe['update']['shared_materials'] == 'all_users' and preflight.get('shared_users') != context['shared_users']:
            raise ValueError('Shared material users differ from preflight scope')
        result = adapter.apply(context,parameters,effect_id)
        if not called or not isinstance(result,dict) or result.get('status') != 'FINISHED':
            raise ValueError('Provider invocation did not finish')
        bpy.context.view_layer.update(); output = output_record(adapter,context)
        if protected_materials is not None:
            slots = context['target'].material_slots
            if (any(index >= len(slots) or not slots[index].material or slots[index].material == original
                    or any(o != context['target'] and any(s.material == slots[index].material for s in o.material_slots) for o in bpy.data.objects)
                    for index,original in shared) or other_materials(scene,target) != protected_materials):
                raise ValueError('Shared material copy policy requires isolated copies and unchanged other users')
    addons.assert_profile(profile); load(root,recipe_id,identity)
    after = measurements(scene,target,scope)
    return {'output':output, 'before':before, 'after':after, 'invocations':called,
            'output_fingerprint':digest(output), 'changed':before != after}


@addons.offline_call
def verify(root, recipe_id, identity, profile, scene, target, parameters, effect_id, expected):
    bundle, context = prepare_context(root,recipe_id,identity,profile,scene,target,parameters,effect_id,verify=True)
    adapter = adapter_for(bundle)
    output = output_record(adapter,context)
    observed = measurements(scene,target,sorted(set(sum(bundle['recipe']['coverage'].values(),[]))))
    if output != expected['output'] or observed != expected['after']: raise ValueError('Saved output differs from applied measurements')
    validation = adapter.verify_saved(observed,output)
    if not isinstance(validation,dict) or validation.get('passed') is not True: raise ValueError('Saved output validator failed')
    addons.assert_profile(profile); load(root,recipe_id,identity)
    return {'passed':True,'output':output,'measurements':observed,'output_fingerprint':digest(output)}
