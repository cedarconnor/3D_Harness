"""Only retained, qualified bundles may reach invocation. Discovery stays import-free."""
from contextlib import contextmanager
import importlib
import copy
from pathlib import Path
import types
import bpy
from . import addons, inspection
try:
    from .recipe_store import load
    from .recipe_schema import validate_parameters, sha
    from .capability_projection import observed_scope
    from .evidence import digest
    from .continuity_blender import measure_live
    from .files import file_hash, io_path, reject_links
except ModuleNotFoundError:
    from dcc_harness.recipe_store import load
    from dcc_harness.recipe_schema import validate_parameters, sha
    from dcc_harness.capability_projection import observed_scope
    from dcc_harness.evidence import digest
    from dcc_harness.continuity_blender import measure_live
    from dcc_harness.files import file_hash, io_path, reject_links

# Evidence of completed calls, never a validation cache: every use still measures
# current bytes/state. Cross-process reuse belongs to verified host receipts.
PROVEN_INVOCATIONS = {}


def inspect_bundle(root, recipe_id, identity):
    return load(root, recipe_id, identity)


def validate_managed(request, project):
    """Check retained host qualification without running activation or adapter code."""
    import json
    cap=request['capability']; selected=cap['resolution']['selected']
    root=reject_links(cap['root']).resolve()
    if root!=Path(project).resolve() or request['live']['parameters']['operation_id']!=request['operation_id']:
        raise ValueError('Capability scope differs from managed project/operation')
    req=cap['requirement']
    if req['target_id']!=request['live']['target'] or req['context']!='live': raise ValueError('Capability target/context mismatch')
    bundle=load(root,selected['recipe_id'],selected['recipe_digest'])
    reference=cap['resolution']['qualification']; report_path=reject_links(reference['report']).resolve()
    if not report_path.is_relative_to(root / 'capabilities/qualifications') or file_hash(report_path)!=reference['sha256']:
        raise ValueError('Qualification reference changed or escaped project')
    record=reject_links(root / 'capabilities/registered' / (sha(reference['sha256'])+'.json'))
    if json.loads(io_path(record).read_text(encoding='utf-8'))!=reference: raise ValueError('Qualification registration changed')
    report=json.loads(io_path(report_path).read_text(encoding='utf-8'))
    if (report['passed'] is not True or report['recipe_digest']!=selected['recipe_digest']
            or report['profile_digest']!=selected['profile_digest'] or 'live' not in report['contexts']):
        raise ValueError('Recipe is not qualified for this live profile')
    profile=addons.provider_sources.load_profile(request['profile'])
    if request['profile']['digest']!=selected['profile_digest'] or not Path(request['profile']['path']).resolve().is_relative_to(root / 'capabilities/profiles'):
        raise ValueError('Capability profile mismatch')
    addons.provider_sources.validate_profile(profile,addons.inventory(addons.roots_for(profile)))
    validate_parameters(bundle['recipe'],cap['parameters'])
    sha(cap['effect_id'])
    return bundle,profile


def managed_args(request, profile, scene):
    cap=request['capability']; selected=cap['resolution']['selected']
    return [cap['root'],selected['recipe_id'],selected['recipe_digest'],profile,scene,
            cap['requirement']['target_id'],cap['parameters'],cap['effect_id']]


def measurements(scene, target_id, fields):
    obj = inspection.target(scene, target_id)
    current = measure_live(scene); record = current['objects'][target_id]
    if current['issues']: raise ValueError('UNSUPPORTED_COVERAGE: ' + '; '.join(current['issues']))
    # Whole-scene issues remain a preservation admission boundary. Projection itself
    # is target-scoped and identical to independent checkpoint observations.
    result = observed_scope(current, target_id, fields)
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
    source = io_path(reject_links(bundle['adapter'])).read_bytes()
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
        if 'arguments' in invocation:
            sources={'target':context['target'],'effect_name':context['effect_name'],
                     'effect_id':context['effect_id'],'parameters':context['parameters'],'context':context}
            sources.update({'parameter:'+key:value for key,value in context['parameters'].items()})
            return function(**{name:sources[source] for name,source in invocation['arguments'].items()})
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


def native_effect(measured, target, effect_id, *, required=True):
    """Resolve the claimed identity from native RNA measurement, never adapter JSON.

    Modifier editor expansion/activation are UI state, not provider output work.
    They remain in the full preservation measurements checked around the call.
    """
    name='DCC::'+effect_id[:48]
    matches=[(index,row) for index,row in enumerate(measured['modifiers'])
             if row['settings'].get('name')==name]
    if not matches and not required: return None
    if len(matches)!=1: raise ValueError('Claimed output requires exactly one measured owned effect (native modifier)')
    index,row=matches[0]; state=copy.deepcopy(row)
    for field in ('show_expanded','is_active'): state['settings'].pop(field,None)
    return {'kind':'modifier','target_id':target,'name':name,'stack_index':index,'state':state}


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
    prior_effect = native_effect(before,target,effect_id,required=False)
    protected_materials = other_materials(scene,target) if recipe['update']['shared_materials']=='single_user_copy' else None
    shared = [(index,slot.material) for index,slot in enumerate(context['target'].material_slots) if slot.material
              and any(o != context['target'] and any(s.material == slot.material for s in o.material_slots) for o in bpy.data.objects)]
    adapter = adapter_for(bundle); called = []
    proof_key=digest({'root':str(Path(root).resolve()),'recipe':identity,'profile':profile,
        'target':target,'effect_id':effect_id,'parameters':parameters,'invocation':recipe['invocation']})
    def invoke(**kwargs):
        if called: raise ValueError('Exactly one declared provider invocation is supported')
        if measurements(scene,target,scope)!=before:
            raise ValueError('Adapter changed measured state before provider invocation')
        try:
            output_record(adapter,context)
        except ValueError:
            pass  # Initial invocation may have no owned effect yet.
        if measurements(scene,target,scope)!=before:
            raise ValueError('Output inspector mutated state before provider invocation')
        intent=digest({'declared':proof_key,'arguments':kwargs})
        existing={m.as_pointer() for m in context['target'].modifiers}
        returned=invoke_declared(context, **kwargs)
        # Ordinary APIs may return an untagged native modifier. Only a modifier
        # actually returned by the declared provider can receive the effect name.
        if isinstance(returned,bpy.types.Modifier):
            if not any(m==returned for m in context['target'].modifiers):
                raise ValueError('Provider invocation returned a foreign modifier')
            if returned.as_pointer() in existing and returned.name!=context['effect_name']:
                raise ValueError('Provider invocation cannot adopt an unowned existing modifier')
            returned.name=context['effect_name']
        bpy.context.view_layer.update()
        after=measurements(scene,target,scope)
        effect=native_effect(after,target,effect_id)
        output=output_record(adapter,context)
        if measurements(scene,target,scope)!=after:
            raise ValueError('Output inspector mutated state after provider invocation')
        proven=PROVEN_INVOCATIONS.get(intent)==digest({'after':after,'output':output,'native_effect':effect})
        if prior_effect==effect and after!=before:
            raise ValueError('Provider changed unrelated measured state but not the claimed output')
        if prior_effect==effect and not proven:
            raise ValueError('Unchanged provider invocation has no prior exact successful proof')
        called.append({'invocation':recipe['invocation'], 'output':output,'after':after,'intent':intent,
                       'native_effect_before':prior_effect,'native_effect_after':effect})
        return returned
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
        if output!=called[0]['output'] or measurements(scene,target,scope)!=called[0]['after']:
            raise ValueError('Claimed output changed outside the declared provider invocation')
        if protected_materials is not None:
            slots = context['target'].material_slots
            if (any(index >= len(slots) or not slots[index].material or slots[index].material == original
                    or any(o != context['target'] and any(s.material == slots[index].material for s in o.material_slots) for o in bpy.data.objects)
                    for index,original in shared) or other_materials(scene,target) != protected_materials):
                raise ValueError('Shared material copy policy requires isolated copies and unchanged other users')
    addons.assert_profile(profile); load(root,recipe_id,identity)
    after = measurements(scene,target,scope)
    effect=native_effect(after,target,effect_id)
    PROVEN_INVOCATIONS[called[0]['intent']]=digest({'after':after,'output':output,'native_effect':effect})
    return {'output':output, 'before':before, 'after':after, 'invocations':[row['invocation'] for row in called],
            'invocation_evidence':called,'native_effect':effect,
            'output_fingerprint':digest(output), 'changed':before != after}


@addons.offline_call
def verify(root, recipe_id, identity, profile, scene, target, parameters, effect_id, expected):
    bundle, context = prepare_context(root,recipe_id,identity,profile,scene,target,parameters,effect_id,verify=True)
    adapter = adapter_for(bundle)
    scope=sorted(set(sum(bundle['recipe']['coverage'].values(),[])))
    before=measurements(scene,target,scope)
    output = output_record(adapter,context)
    observed = measurements(scene,target,scope)
    effect=native_effect(observed,target,effect_id)
    if observed!=before: raise ValueError('Output inspector mutated saved state')
    if effect!=expected.get('native_effect'): raise ValueError('Saved native modifier effect differs from applied evidence; requalify legacy output')
    if output != expected['output'] or observed != expected['after']: raise ValueError('Saved output differs from applied measurements')
    validation = adapter.verify_saved(observed,output)
    if not isinstance(validation,dict) or validation.get('passed') is not True: raise ValueError('Saved output validator failed')
    addons.assert_profile(profile); load(root,recipe_id,identity)
    return {'passed':True,'output':output,'native_effect':effect,'measurements':observed,'output_fingerprint':digest(output)}
