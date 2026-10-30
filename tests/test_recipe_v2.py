"""Versioned effect selectors and cooperative invocation are closed portable contracts."""
import copy
import json
from pathlib import Path
import unittest

from dcc_harness.recipe_schema import validate
from test_recipes import recipe

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None


def v2(kind='shader_nodes', asynchronous=False):
    value = recipe()
    value['schema'] = 'dcc.capability.recipe.v2'
    value['effect'] = {'kind':kind}
    if kind != 'modifier':
        value['effect'].update(material_id='{effect_name}', slot=0)
        if kind == 'shader_nodes':
            value['effect']['nodes'] = ['{effect_name}', '{effect_name}::BSDF']
        value['coverage']['writes'] = ['materials' if kind == 'material' else 'nodes']
        value['update']['shared_materials'] = 'single_user_copy'
    if asynchronous:
        value['invocation'] = {'kind':'python_function', 'entry':'provider.submit',
            'completion':'asynchronous', 'cancellation':'cooperative',
            'poll':'provider.poll', 'cancel':'provider.cancel', 'collect':'provider.collect',
            'poll_interval':0.05, 'timeout':0.1, 'cancel_grace':0.1,
            'arguments':{'target':'target', 'amount':'parameter:amount'}}
    return value


class RecipeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads((Path(__file__).resolve().parents[1] /
            'dcc_harness/data/capabilities/recipe.schema.json').read_text())
        cls.serialized = Draft202012Validator(schema) if Draft202012Validator else None

    def accepted(self, value):
        self.assertEqual(validate(value), value)
        if self.serialized:
            self.serialized.validate(value)

    def rejected(self, value):
        with self.assertRaises(ValueError):
            validate(value)
        if self.serialized:
            self.assertFalse(self.serialized.is_valid(value), value)

    def test_v1_remains_closed_modifier_and_synchronous_only(self):
        self.accepted(recipe())
        value = recipe(); value['effect'] = {'kind':'modifier'}; self.rejected(value)
        value = recipe(); value['coverage']['writes'] = ['materials']; self.rejected(value)
        value = v2('modifier', True); value.pop('effect'); value['schema'] = 'dcc.capability.recipe.v1'
        self.rejected(value)

    def test_v2_all_effects_support_sync_and_async(self):
        for kind in ('modifier', 'material', 'shader_nodes'):
            for asynchronous in (False, True):
                with self.subTest(kind=kind, asynchronous=asynchronous):
                    self.accepted(v2(kind, asynchronous))
        value = v2('shader_nodes'); value['effect']['material_id'] = 'material.fixture'
        self.accepted(value)

    def test_effect_fields_are_exact(self):
        for kind in ('modifier', 'material', 'shader_nodes'):
            original = v2(kind)
            for key in original['effect']:
                value = copy.deepcopy(original); del value['effect'][key]; self.rejected(value)
            value = copy.deepcopy(original); value['effect']['extra'] = True; self.rejected(value)
        value = v2(); del value['effect']; self.rejected(value)
        value = v2(); value['effect']['kind'] = 'geometry'; self.rejected(value)

    def test_effect_selector_bounds_and_types(self):
        for slot in (-1, True, 0.5, '0', None, 1024, 10**100):
            value = v2(); value['effect']['slot'] = slot; self.rejected(value)
        for material in ('../artist', 'CON', 'x.', '', '{effect_name}suffix', 'x'*129, 'fixture\n'):
            value = v2(); value['effect']['material_id'] = material; self.rejected(value)
        for nodes in ([], ['{effect_name}']*2, ['Artist'], ['{effect_name}\n'],
                      ['{effect_name}' + 'x'*11], ['{effect_name}é'*10], ['x']*257):
            value = v2(); value['effect']['nodes'] = nodes; self.rejected(value)
        value = v2(); value['effect']['nodes'] = ['{effect_name}'+'x'*10]; self.accepted(value)

    def test_effect_coverage_and_material_scope(self):
        for kind in ('modifier', 'material', 'shader_nodes'):
            value = v2(kind); value['coverage']['writes'] = ['geometry']; self.rejected(value)
        for kind in ('material', 'shader_nodes'):
            value = v2(kind); value['update']['shared_materials'] = 'none'; self.rejected(value)
        value = v2('modifier'); value['coverage']['writes'].append('nodes'); self.rejected(value)
        # A material or node effect may declare either native material measurement domain.
        value = v2('material'); value['coverage']['writes'] = ['nodes']; self.accepted(value)
        value = v2('material'); value['effect']['material_id'] = 'artist_material'; self.rejected(value)

    def test_async_lifecycle_is_exact_and_python_only(self):
        original = v2(asynchronous=True)
        for key in original['invocation']:
            if key == 'arguments':
                continue
            value = copy.deepcopy(original); del value['invocation'][key]; self.rejected(value)
        for key, item in (('extra',True), ('kind','operator'), ('kind','node_asset'),
                          ('cancellation','between_calls')):
            value = copy.deepcopy(original); value['invocation'][key] = item; self.rejected(value)
        value = v2(); value['invocation']['poll'] = 'provider.poll'; self.rejected(value)
        value = copy.deepcopy(original); del value['invocation']['arguments']; self.accepted(value)

    def test_lifecycle_callable_and_timing_bounds(self):
        original = v2(asynchronous=True)
        for key in ('entry','poll','cancel','collect'):
            for bad in ('bare','provider.call()','provider..call','x.'+'x'*127,'provider.call\n',None):
                value = copy.deepcopy(original); value['invocation'][key] = bad; self.rejected(value)
        for key, low, high in (('poll_interval',.05,5), ('timeout',.1,3600), ('cancel_grace',.1,60)):
            for bad in (low-.001, high+.001, True, '1', None):
                value = copy.deepcopy(original); value['invocation'][key] = bad; self.rejected(value)
            for good in (low, high):
                value = copy.deepcopy(original); value['invocation'][key] = good; self.accepted(value)

    def test_async_argument_mapping_uses_submit_parameters(self):
        for args in ({'bad-name':'target'}, {'amount':'parameter:missing'}, {'amount':'handle'}, []):
            value = v2(asynchronous=True); value['invocation']['arguments'] = args
            with self.assertRaises(ValueError): validate(value)
        self.accepted(v2(asynchronous=True))


if __name__ == '__main__':
    unittest.main()

