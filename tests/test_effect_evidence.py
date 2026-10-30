import copy
import unittest


class EffectEvidenceTests(unittest.TestCase):
    def sample(self, kind='shader_nodes'):
        name = 'DCC::' + 'a' * 48
        recipe = {'effect': {'kind': kind, 'material_id': 'stone', 'slot': 0,
                             'nodes': ['{effect_name}']}}
        graph = {'nodes': [{'name': name, 'type': 'ShaderNodeValue', 'inputs': {}, 'value': .4},
                           {'name': 'Output', 'type': 'ShaderNodeOutputMaterial', 'inputs': {}}],
                 'links': [[name, 'Value', 'Output', 'Surface']]}
        measured = {'materials': {'stone': {'name': 'Stone', 'graph': graph}},
                    'material_bindings': ['stone'], 'material_users': {'stone': ['Cube']}}
        return recipe, measured

    def test_standalone_shader_proves_owned_nodes_and_connections_without_modifier(self):
        from dcc_harness.effect_evidence import native_effect
        recipe, measured = self.sample()
        result = native_effect(measured, 'Cube', 'a'*64, recipe=recipe)
        self.assertEqual(result['kind'], 'shader_nodes')
        self.assertEqual(len(result['state']['nodes']), 1)
        self.assertEqual(len(result['state']['links']), 1)
        changed = copy.deepcopy(measured)
        changed['materials']['stone']['graph']['nodes'][0]['value'] = .8
        self.assertNotEqual(result, native_effect(changed, 'Cube', 'a'*64, recipe=recipe))

    def test_wrong_slot_duplicate_missing_and_disconnected_nodes_cannot_prove_effect(self):
        from dcc_harness.effect_evidence import native_effect
        recipe, measured = self.sample()
        for edit in ('slot', 'duplicate', 'missing', 'disconnected'):
            candidate = copy.deepcopy(measured)
            graph = candidate['materials']['stone']['graph']
            if edit == 'slot': candidate['material_bindings'] = ['other']
            if edit == 'duplicate': graph['nodes'].append(graph['nodes'][0])
            if edit == 'missing': graph['nodes'].pop(0)
            if edit == 'disconnected': graph['links'] = []
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                native_effect(candidate, 'Cube', 'a'*64, recipe=recipe)

    def test_material_identity_and_bindings_are_native_output(self):
        from dcc_harness.effect_evidence import native_effect
        recipe, measured = self.sample()
        name = 'DCC::'+'a'*48
        recipe['effect'] = {'kind':'material','material_id':'{effect_name}','slot':0}
        self.assertIsNone(native_effect(measured,'Cube','a'*64,recipe=recipe,required=False))
        measured['materials'][name] = measured['materials'].pop('stone')
        measured['materials'][name]['name'] = name
        measured['material_bindings'] = [name]
        self.assertEqual(native_effect(measured,'Cube','a'*64,recipe=recipe)['kind'],'material')

    def test_v1_modifier_evidence_remains_compatible(self):
        from dcc_harness.effect_evidence import native_effect
        measured = {'modifiers':[{'type':'BEVEL','settings':{'name':'DCC::'+'a'*48,
                                                  'width':.1,'show_expanded':True}}]}
        effect = native_effect(measured,'Cube','a'*64)
        self.assertEqual(effect['kind'],'modifier')
        self.assertNotIn('show_expanded',effect['state']['settings'])

    def test_muted_or_invalid_connection_cannot_establish_shader_contribution(self):
        from dcc_harness.effect_evidence import native_effect
        recipe,measured=self.sample()
        graph=measured['materials']['stone']['graph']
        graph['link_flags']=[{'link':graph['links'][0],'muted':True,'valid':True}]
        with self.assertRaisesRegex(ValueError,'disconnected'):
            native_effect(measured,'Cube','a'*64,recipe=recipe)

    def test_muted_owned_node_cannot_establish_shader_contribution(self):
        from dcc_harness.effect_evidence import native_effect
        recipe,measured=self.sample()
        measured['materials']['stone']['graph']['nodes'][0]['mute']=True
        with self.assertRaisesRegex(ValueError,'disconnected'):
            native_effect(measured,'Cube','a'*64,recipe=recipe)
