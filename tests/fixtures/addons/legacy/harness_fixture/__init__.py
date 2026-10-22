"""Synthetic offline provider used only by owned qualification fixtures."""
bl_info = {'name':'Harness fixture', 'version':(1, 0, 0), 'blender':(5, 1, 0), 'category':'Object',
           'dcc_harness':{'network':'offline', 'dependencies':[], 'preferences':{'quality':'integer'}}}

import bpy


class HARNESS_FIXTURE_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    quality: bpy.props.IntProperty(default=2, min=1, max=8)


class HARNESS_FIXTURE_mark(bpy.types.Operator):
    bl_idname = 'object.harness_fixture_mark'
    bl_label = 'Mark owned profile fixture'

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'OBJECT'

    def execute(self, context):
        context.object['profile_fixture'] = 1
        return {'FINISHED'}


def register():
    bpy.utils.register_class(HARNESS_FIXTURE_preferences)
    bpy.utils.register_class(HARNESS_FIXTURE_mark)


def unregister():
    bpy.utils.unregister_class(HARNESS_FIXTURE_mark)
    bpy.utils.unregister_class(HARNESS_FIXTURE_preferences)
