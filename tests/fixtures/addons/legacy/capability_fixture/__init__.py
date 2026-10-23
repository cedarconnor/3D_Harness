"""Synthetic qualification provider, not a product adapter."""
bl_info = {'name':'Capability fixture','version':(1,0,0),'blender':(5,1,0),
           'dcc_harness':{'network':'offline','dependencies':[],'preferences':{}}}
import sys
import socket
import bpy
from bpy.app.handlers import persistent


def mark(context, parameters, effect_id):
    behavior = parameters['behavior']; obj = context['target']; name = 'DCC::' + effect_id[:48]
    if behavior == 'noop': return {'status':'FINISHED'}
    if behavior == 'network':
        try:
            with socket.socket() as connection: connection.connect(('127.0.0.1',9))
        except RuntimeError: pass
    mod = obj.modifiers.get(name)
    if behavior == 'duplicate' or mod is None: mod = obj.modifiers.new(name,'BEVEL')
    mod.width = parameters['amount']; mod.segments = 2
    if behavior == 'copy':
        for slot in obj.material_slots:
            if slot.material and slot.material.get('fixture_copy_effect') != effect_id:
                slot.material = slot.material.copy()
                slot.material['fixture_copy_effect'] = effect_id
                slot.material['dcc_material_id'] = 'fixture-copy-' + effect_id
    if behavior == 'mutate_error': raise RuntimeError('Fixture mutated before error')
    if behavior == 'missing_reopen': obj['fixture_missing_reopen'] = True
    return {'status':'FINISHED'}


def mark_adaptive(context, parameters, effect_id):
    """Synthetic scale/finish rule: authored mesh size and roughness drive bevel width."""
    obj = context['target']
    radius = sum(vertex.co.length for vertex in obj.data.vertices) / len(obj.data.vertices)
    roughness = obj.active_material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value
    return mark(context, {**parameters, 'amount': parameters['amount'] * radius * (1 + roughness)}, effect_id)


class FIXTURE_OT_apply(bpy.types.Operator):
    bl_idname = 'object.capability_fixture'; bl_label = 'Synthetic capability'
    amount: bpy.props.FloatProperty(default=.1)
    effect_id: bpy.props.StringProperty()
    behavior: bpy.props.StringProperty(default='normal')

    @classmethod
    def poll(cls, context): return context.object is not None and context.object.mode == 'OBJECT'

    def execute(self, context):
        if self.behavior == 'modal': return {'RUNNING_MODAL'}
        mark({'target':context.object},{'amount':self.amount,'behavior':self.behavior},self.effect_id)
        return {'FINISHED'}


class FIXTURE_OT_viewport(bpy.types.Operator):
    bl_idname = 'object.capability_viewport'; bl_label = 'Synthetic viewport capability'
    amount: bpy.props.FloatProperty(default=.1)
    effect_id: bpy.props.StringProperty()
    behavior: bpy.props.StringProperty(default='normal')
    execute = FIXTURE_OT_apply.execute

    @classmethod
    def poll(cls, context):
        return not bpy.app.background and context.object is not None and context.object.mode == 'OBJECT' and context.area is not None and context.area.type == 'VIEW_3D'


class FIXTURE_OT_never(bpy.types.Operator):
    bl_idname = 'object.capability_never'; bl_label = 'Synthetic unavailable capability'
    amount: bpy.props.FloatProperty(default=.1)
    effect_id: bpy.props.StringProperty()
    behavior: bpy.props.StringProperty(default='normal')
    execute = FIXTURE_OT_apply.execute

    @classmethod
    def poll(cls, context): return False


@persistent
def reopen_dependency(_):
    if any(obj.get('fixture_missing_reopen') for obj in bpy.data.objects):
        sys.modules[__name__].__addon_enabled__ = False


def register():
    for cls in (FIXTURE_OT_apply,FIXTURE_OT_viewport,FIXTURE_OT_never): bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(reopen_dependency)


def unregister():
    if reopen_dependency in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(reopen_dependency)
    for cls in (FIXTURE_OT_never,FIXTURE_OT_viewport,FIXTURE_OT_apply): bpy.utils.unregister_class(cls)
