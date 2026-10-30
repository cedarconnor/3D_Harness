"""Owned offline shader/async qualification provider; never an artist add-on."""
bl_info = {'name':'Shader async fixture','version':(1,0,0),'blender':(5,1,0),
           'dcc_harness':{'network':'offline','dependencies':[], 'preferences':{'quality':'integer'}}}
import time
import uuid
import bpy

JOBS = {}
COUNTS = {'submit':0, 'poll':0, 'cancel':0, 'collect':0}
QUALITY = []


class SHADER_ASYNC_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    quality: bpy.props.IntProperty(default=2, min=1, max=8)


def quality():
    value = bpy.context.preferences.addons[__package__].preferences.quality
    QUALITY.append(value)
    if value != 3: raise RuntimeError('Fixture preference scope expired between callbacks')


def bind_owned_material(obj, slot, material):
    prior=obj.material_slots[slot].material if slot<len(obj.material_slots) else None
    if prior is not None and prior!=material and prior.users<=1:
        # Retain the displaced artist data for independent saved-file protection.
        prior.use_fake_user=True
    while len(obj.data.materials)<=slot:obj.data.materials.append(None)
    obj.material_slots[slot].material=material


def material_for(context, effect_id):
    obj = context['target']; selector = context['recipe']['effect']; name = context['effect_name']
    if selector['kind'] == 'material':
        material = next((m for m in bpy.data.materials if m.get('dcc_material_id') == name), None)
        if material is None:
            material = bpy.data.materials.new(name)
            material['dcc_material_id'] = name; material['dcc_effect_id'] = effect_id
        material.use_nodes = True
        bind_owned_material(obj,selector['slot'],material)
    elif selector['material_id']=='{effect_name}':
        material = next((m for m in bpy.data.materials if m.get('dcc_material_id')==name),None)
        if material is None:
            original=obj.material_slots[selector['slot']].material
            material=original.copy();material.name=name
            material['dcc_material_id']=name;material['dcc_effect_id']=effect_id
        bind_owned_material(obj,selector['slot'],material)
    else:
        material_id = selector['material_id'].replace('{effect_name}', name)
        material = next(m for m in bpy.data.materials if m.get('dcc_material_id') == material_id)
    return material


def mark(context, parameters, effect_id):
    quality()
    behavior = parameters['behavior']
    if behavior == 'noop': return {'status':'FINISHED'}
    material = material_for(context, effect_id); tree = material.node_tree
    amount = parameters['amount']; color = (amount, .08, 1-amount, 1)
    if context['recipe']['effect']['kind'] == 'material':
        bsdf = next(n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = .3
    else:
        name = context['effect_name']; node = tree.nodes.get(name)
        if node is None:
            node = tree.nodes.new('ShaderNodeGroup'); node.name = name
            node['dcc_effect_id'] = effect_id
            group = bpy.data.node_groups.new(name+'::Tree','ShaderNodeTree')
            group.interface.new_socket(name='Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
            output = group.nodes.new('NodeGroupOutput')
            nested = group.nodes.new('ShaderNodeGroup')
            inner = bpy.data.node_groups.new(name+'::Inner','ShaderNodeTree')
            inner.interface.new_socket(name='Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
            inner_output = inner.nodes.new('NodeGroupOutput')
            shader = inner.nodes.new('ShaderNodeBsdfPrincipled')
            inner.links.new(shader.outputs['BSDF'],inner_output.inputs['Shader'])
            nested.node_tree = inner
            group.links.new(nested.outputs['Shader'], output.inputs['Shader'])
            node.node_tree = group
        nested = next(n for n in node.node_tree.nodes if n.type == 'GROUP')
        bsdf = next(n for n in nested.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = color
        output = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
        tree.links.new(node.outputs['Shader'], output.inputs['Surface'])
        if behavior == 'shared_group':
            # Mutate an existing group referenced by another material and a world.
            protected = bpy.data.node_groups['ProtectedSharedGroup']
            nested.node_tree = protected
            protected.nodes['Value'].outputs[0].default_value = amount
    if behavior == 'mutate_fail': raise RuntimeError('Fixture mutation then failure')
    return {'status':'FINISHED'}


def submit(context, parameters, effect_id):
    quality(); COUNTS['submit'] += 1
    handle = {'id':uuid.uuid4().hex}
    job = {'context':context, 'parameters':dict(parameters), 'effect_id':effect_id,
           'started':time.monotonic(), 'state':'pending', 'ticks':0}
    JOBS[handle['id']] = job
    if not bpy.app.background:
        def advance():
            job['ticks'] += 1
            if job['state'] != 'pending': return None
            if time.monotonic()-job['started'] < parameters['delay']: return .025
            finish(job); return None
        bpy.app.timers.register(advance, first_interval=.025)
    return handle


def finish(job):
    behavior = job['parameters']['behavior']
    if behavior in ('hang','cancel_refuses'): return
    if behavior == 'fail': job['state'] = 'failed'; return
    try:
        if not bpy.app.background:
            mark(job['context'],job['parameters'],job['effect_id'])
            job['applied'] = True
        job['state'] = 'succeeded'
    except Exception as exc:
        job['state'] = 'failed'; job['error'] = str(exc)


def poll(context, handle):
    quality(); COUNTS['poll'] += 1
    job = JOBS[handle['id']]
    if bpy.app.background and job['state']=='pending' and time.monotonic()-job['started'] >= job['parameters']['delay']:
        finish(job)
    return {'state':job['state'].upper(), 'progress':min(.99,(time.monotonic()-job['started'])/max(.01,job['parameters']['delay'])),
            'error':job.get('error',''), 'timer_ticks':job['ticks']}


def cancel(context, handle):
    quality(); COUNTS['cancel'] += 1
    job = JOBS[handle['id']]
    if job['parameters']['behavior'] != 'cancel_refuses': job['state'] = 'cancelled'
    return {'state':job['state'].upper()}


def collect(context, handle):
    quality(); COUNTS['collect'] += 1
    job = JOBS[handle['id']]
    if job['state'] != 'succeeded': raise RuntimeError('Collect before successful provider termination')
    if not job.get('applied'):
        mark(job['context'],job['parameters'],job['effect_id'])
        job['applied'] = True
    return {'status':'FINISHED'}


def register(): bpy.utils.register_class(SHADER_ASYNC_preferences)
def unregister(): bpy.utils.unregister_class(SHADER_ASYNC_preferences)
