import copy
import unittest
from types import SimpleNamespace as NS

from dcc_harness.shader_graph import graph, graph_issues


def prop(name, kind='STRING'):
    return NS(identifier=name, type=kind)


def rna(**attrs):
    attrs['bl_rna'] = NS(properties=[prop(k, 'POINTER' if isinstance(v, NS) else
                                            'COLLECTION' if isinstance(v, list) else
                                            'BOOLEAN' if isinstance(v, bool) else
                                            'FLOAT' if isinstance(v, float) else 'STRING')
                                      for k, v in attrs.items()])
    return NS(**attrs)


def socket(name, default=0.0):
    return rna(identifier=name, name=name, default_value=default, type='VALUE')


def node(name='Node', **extra):
    return rna(name=name, bl_idname='ShaderNodeValue', inputs=[], outputs=[socket('Value')],
               mute=False, **extra)


def tree(nodes=(), **extra):
    return rna(name='Tree', nodes=list(nodes), links=[], **extra)


class ShaderGraphTests(unittest.TestCase):
    def test_nested_values_and_outputs_change_evidence(self):
        inner = tree([node()])
        outer = tree([node('Group', node_tree=inner)])
        first = graph(outer)
        inner.nodes[0].outputs[0].default_value = 0.6
        self.assertNotEqual(first, graph(outer))
        self.assertEqual(first['nodes'][0]['group'], 'Tree')
        self.assertFalse(graph_issues(first))

    def test_interface_defaults_and_ramp_settings(self):
        item = rna(identifier='Socket_0', item_type='SOCKET', in_out='INPUT',
                   default_value=0.2, socket_type='NodeSocketFloat')
        ramp = rna(interpolation='LINEAR', color_mode='RGB', hue_interpolation='NEAR',
                   elements=[rna(position=0.0, color=(0., 0., 0., 1.))])
        data = tree([node(color_ramp=ramp)], interface=NS(items_tree=[item]))
        first = graph(data)
        item.default_value = 0.4
        self.assertNotEqual(first, graph(data))
        first = graph(data)
        ramp.interpolation = 'CONSTANT'
        self.assertNotEqual(first, graph(data))
        self.assertFalse(graph_issues(first))

    def test_generic_primitive_settings_and_mute_are_measured(self):
        data = tree([node(distribution='GGX', custom_strength=0.25)])
        first = graph(data)
        data.nodes[0].custom_strength = 0.5
        self.assertNotEqual(first, graph(data))
        first = graph(data)
        data.nodes[0].mute = True
        self.assertNotEqual(first, graph(data))

    def test_unknown_pointer_and_unserializable_value_fail_closed(self):
        data = tree([node(mapping=NS(curves=[]), mystery=object())])
        issues = graph_issues(graph(data))
        self.assertTrue(any('mapping' in item for item in issues))
        self.assertTrue(any('mystery' in item for item in issues))

    def test_cycle_and_depth_and_total_limits(self):
        data = tree([])
        data.nodes.append(node(node_tree=data))
        self.assertTrue(any('cycle' in x for x in graph_issues(graph(data))))
        data = tree([node(node_tree=tree([node()]))])
        self.assertTrue(graph_issues(graph(data, max_depth=0)))
        self.assertTrue(graph_issues(graph(data, max_nodes=1)))

    def test_images_links_and_deterministic_order(self):
        a, b = node('A', image=NS(name='image')), node('B')
        data = tree([b, a])
        data.links = [NS(from_node=a, from_socket=a.outputs[0], to_node=b,
                         to_socket=socket('Input'), is_muted=False, is_valid=True)]
        image = {'name': 'image', 'exists': True, 'sha256': 'a'}
        first = graph(data, image_record=lambda _: copy.deepcopy(image))
        data.nodes.reverse()
        self.assertEqual(first, graph(data, image_record=lambda _: copy.deepcopy(image)))
        image['sha256'] = 'b'
        self.assertNotEqual(first, graph(data, image_record=lambda _: copy.deepcopy(image)))
        image['sha256'] = None
        self.assertTrue(graph_issues(graph(data, image_record=lambda _: image)))

    def test_legacy_unsupported_markers_propagate(self):
        self.assertTrue(graph_issues({'nodes': [{'name': 'Group', 'group': 'Old',
                                                'unsupported_group': True}], 'links': []}))

    def test_ui_changes_do_not_change_graph(self):
        item = node(location_absolute=(0., 0.), label='A')
        item.outputs[0].select = False
        item.outputs[0].bl_rna.properties.append(prop('select', 'BOOLEAN'))
        data = tree([item])
        first = graph(data)
        item.location_absolute = (1., 2.)
        item.label = 'B'
        item.outputs[0].select = True
        self.assertEqual(first, graph(data))

    def test_texture_mapping_and_image_user_state(self):
        item = node(texture_mapping=rna(scale=(1., 1., 1.)),
                    image_user=rna(frame_offset=0))
        data = tree([item])
        first = graph(data)
        self.assertFalse(graph_issues(first))
        item.image_user.frame_offset = 5
        self.assertNotEqual(first, graph(data))

    def test_image_interpretation_and_unpersisted_pixels_are_not_silent(self):
        image = NS(name='Image', source='FILE', alpha_mode='STRAIGHT', is_dirty=False)
        data = tree([node(image=image)])
        capture = lambda _: {'exists': True, 'sha256': 'abc'}
        first = graph(data, image_record=capture)
        image.alpha_mode = 'PREMUL'
        self.assertNotEqual(first, graph(data, image_record=capture))
        image.is_dirty = True
        self.assertTrue(graph_issues(graph(data, image_record=capture)))

    def test_ownership_identity_is_measured_when_present(self):
        item = node()
        data = tree([item])
        before = graph(data)
        item.get = lambda key: 'effect:abc' if key == 'dcc_effect_id' else None
        after = graph(data)
        self.assertNotIn('dcc_effect_id', before['nodes'][0])
        self.assertEqual(after['nodes'][0]['dcc_effect_id'], 'effect:abc')


if __name__ == '__main__':
    unittest.main()
