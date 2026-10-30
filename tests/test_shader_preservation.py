import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


class Material(dict):
    def __init__(self, name, identity, graph):
        super().__init__(dcc_material_id=identity)
        self.name = self.name_full = name
        self.node_tree = graph
        self.diffuse_color = (.8, .8, .8, 1.)

    def as_pointer(self):
        return id(self)


class ShaderPreservationTests(unittest.TestCase):
    def setUp(self):
        self.name = 'DCC::' + 'a'*48
        self.shader = Material('ArtistShader', 'shader', {'nodes': [
            {'name': 'Artist', 'type': 'ShaderNodeBsdfPrincipled', 'inputs': {'roughness': .5}},
            {'name': 'Output', 'type': 'ShaderNodeOutputMaterial', 'inputs': {}}],
            'links': [['Artist', 'BSDF', 'Output', 'Surface']]})
        self.other = Material('Other', 'other', {'nodes': [], 'links': []})
        self.materials = [self.shader, self.other]
        self.worlds = []
        self.raw = {'objects': {'target': {'material_ids': ['shader', 'other'], 'matrix_world': [1]},
                                'other_user': {'material_ids': ['other']}},
                    'materials': {}, 'scene': {}, 'coverage': {}, 'issues': []}
        self.target = types.SimpleNamespace(material_slots=[types.SimpleNamespace(material=m) for m in self.materials])
        self.context = {'scene': object(), 'target': self.target, 'target_id': 'target',
                        'effect_id': 'a'*64, 'effect_name': self.name,
                        'recipe': {'effect': {'kind': 'shader_nodes', 'material_id': 'shader',
                                              'slot': 0, 'nodes': ['{effect_name}']},
                                   'coverage': {'writes': ['nodes']}}}
        package = types.ModuleType('_preservation_test')
        package.__path__ = []
        modules = {'_preservation_test': package, '_preservation_test.inspection': types.ModuleType('inspection'),
            'bpy': types.SimpleNamespace(data=types.SimpleNamespace(materials=self.materials, worlds=self.worlds))}
        for key, attrs in {
            'effect_evidence': {'selector': lambda s, effect: s.replace('{effect_name}', 'DCC::'+effect[:48])},
            'continuity_blender': {'measure_live': lambda scene: copy.deepcopy(self.raw)},
            'blender': {'graph': copy.deepcopy},
        }.items():
            module = types.ModuleType('_preservation_test.' + key)
            module.__dict__.update(attrs)
            modules[module.__name__] = module
        self.patch = mock.patch.dict(sys.modules, modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        path = Path(__file__).parents[1] / 'dcc_harness/data/bridge/recipe_effects.py'
        spec = importlib.util.spec_from_file_location('_preservation_test.recipe_effects', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def preserved(self):
        return self.module.preserved(self.context, self.module.allowed_materials(self.context))

    def test_owned_nodes_and_output_rewire_are_permitted(self):
        before = self.preserved()
        self.shader.node_tree['nodes'].append({'name': self.name, 'type': 'ShaderNodeGroup', 'inputs': {}})
        self.shader.node_tree['links'] = [[self.name, 'Shader', 'Output', 'Surface']]
        self.assertEqual(before, self.preserved())

    def test_other_nodes_other_materials_and_other_slots_stay_protected(self):
        before = self.preserved()
        self.shader.node_tree['nodes'][0]['inputs']['roughness'] = .9
        self.assertNotEqual(before, self.preserved())
        self.shader.node_tree['nodes'][0]['inputs']['roughness'] = .5
        self.other.diffuse_color = (1., 0., 0., 1.)
        self.assertNotEqual(before, self.preserved())
        self.other.diffuse_color = (.8, .8, .8, 1.)
        self.raw['objects']['target']['material_ids'][1] = 'shader'
        self.assertNotEqual(before, self.preserved())

    def test_selected_slot_binding_can_change_to_existing_global_material(self):
        self.raw['objects']['target']['material_ids'][0] = 'other'
        before = self.preserved()
        self.raw['objects']['target']['material_ids'][0] = 'shader'
        self.assertEqual(before, self.preserved())

    def test_material_effect_preserves_replaced_artist_material(self):
        self.context['recipe']['effect'] = {'kind': 'material', 'material_id': '{effect_name}', 'slot': 0}
        before = self.preserved()
        material = Material(self.name, self.name, {'nodes': [], 'links': []})
        material['dcc_effect_id'] = self.context['effect_id']
        self.materials.append(material)
        self.raw['objects']['target']['material_ids'][0] = self.name
        self.assertEqual(before, self.preserved())
        self.shader.diffuse_color = (0., 1., 0., 1.)
        self.assertNotEqual(before, self.preserved())

    def test_unsupported_unused_material_graph_is_refused(self):
        self.other.node_tree['unsupported'] = ['Other/Curve.mapping: unsupported RNA POINTER']
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_COVERAGE'):
            self.preserved()

    def test_shared_nested_group_in_other_material_remains_protected(self):
        before = self.preserved()
        self.other.node_tree['nodes'].append({'name': 'Shared', 'graph': {'nodes': [
            {'name': 'Value', 'outputs': {'Value': .5}}], 'links': []}})
        self.assertNotEqual(before, self.preserved())

    def test_worlds_remain_protected_and_unknown_state_is_refused(self):
        world = types.SimpleNamespace(name_full='OtherWorld', node_tree={'nodes': [], 'links': []})
        self.worlds.append(world)
        before = self.preserved()
        world.node_tree['nodes'].append({'name': 'Value', 'outputs': {'Value': .2}})
        self.assertNotEqual(before, self.preserved())
        world.node_tree['unsupported'] = ['OtherWorld/Curve.mapping: unsupported RNA POINTER']
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_COVERAGE'):
            self.preserved()

    def test_unowned_connections_and_socket_defaults_remain_protected(self):
        self.shader.node_tree['nodes'][0]['sockets'] = {
            'outputs': [{'identifier': 'BSDF', 'is_linked': True, 'is_inactive': False}],
            'inputs': [{'identifier': 'Roughness', 'default_value': .5}]}
        before = self.preserved()
        sockets = self.shader.node_tree['nodes'][0]['sockets']
        sockets['outputs'][0]['is_linked'] = False
        sockets['outputs'][0]['is_inactive'] = True
        self.assertEqual(before, self.preserved())
        sockets['inputs'][0]['default_value'] = .9
        self.assertNotEqual(before, self.preserved())
        sockets['inputs'][0]['default_value'] = .5
        self.shader.node_tree['links'].append(['Artist', 'BSDF', 'OtherArtist', 'Shader'])
        self.assertNotEqual(before, self.preserved())

    def test_padding_empty_selected_slot_does_not_unlock_other_slots(self):
        self.context['recipe']['effect']['slot'] = 2
        before = self.preserved()
        self.raw['objects']['target']['material_ids'].append('shader')
        self.assertEqual(before, self.preserved())
        self.raw['objects']['target']['material_ids'][0] = 'other'
        self.assertNotEqual(before, self.preserved())

    def test_modifier_write_keeps_other_effect_ownership_markers(self):
        self.context['recipe']['effect'] = {'kind': 'modifier'}
        self.context['recipe']['coverage']['writes'] = ['modifiers']
        owners = {'OtherModifier': 'other-effect'}
        self.target.get = lambda key, default=None: owners if key == 'dcc_modifier_effects' else default
        before = self.preserved()
        owners[self.name] = 'a'*64
        self.assertEqual(before, self.preserved())
        owners['OtherModifier'] = 'stolen'
        self.assertNotEqual(before, self.preserved())

    def test_owned_shader_container_creation_preserves_original_artist_material(self):
        self.context['recipe']['effect']['material_id'] = '{effect_name}'
        before = self.preserved()
        copied = Material(self.name, self.name, copy.deepcopy(self.shader.node_tree))
        copied['dcc_effect_id'] = self.context['effect_id']
        copied.node_tree['nodes'].append({'name': self.name, 'type': 'ShaderNodeGroup', 'inputs': {}})
        self.materials.append(copied)
        self.raw['objects']['target']['material_ids'][0] = self.name
        self.assertEqual(before, self.preserved())
        self.shader.node_tree['nodes'][0]['inputs']['roughness'] = .9
        self.assertNotEqual(before, self.preserved())

    def test_existing_unowned_shader_container_is_rejected(self):
        self.context['recipe']['effect']['material_id'] = '{effect_name}'
        material = Material(self.name, self.name, types.SimpleNamespace(nodes=[]))
        self.materials.append(material)
        with self.assertRaisesRegex(ValueError, 'unowned'):
            self.module.ownership_before(self.context)

    def test_new_shader_container_and_nodes_are_claimed_together(self):
        self.context['recipe']['effect']['material_id'] = '{effect_name}'
        self.assertEqual(self.module.ownership_before(self.context), set())
        class Node(dict):
            name = self.name
            def as_pointer(self):
                return id(self)
        node = Node()
        material = Material(self.name, self.name, types.SimpleNamespace(nodes=[node]))
        self.materials.append(material)
        self.module.claim(self.context, set())
        self.assertEqual(material.get('dcc_effect_id'), self.context['effect_id'])
        self.assertEqual(node.get('dcc_effect_id'), self.context['effect_id'])

    def test_no_write_scope_does_not_mask_owned_shader_progress(self):
        self.context['recipe']['coverage']['writes']=[]
        before=self.preserved()
        self.shader.node_tree['nodes'].append({'name':self.name,'type':'ShaderNodeValue','inputs':{}})
        self.assertNotEqual(before,self.preserved())


if __name__ == '__main__':
    unittest.main()
