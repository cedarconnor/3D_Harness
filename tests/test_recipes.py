"""Drafts are inert, immutable local bundles, never executable qualifications."""
import copy
import json
from pathlib import Path
import tempfile
import unittest


def recipe():
    return {'schema':'dcc.capability.recipe.v1', 'id':'fixture.mark', 'version':1,
        'capabilities':['surface.fixture'], 'provider':{'id':'harness_fixture', 'source_digest':'a' * 64},
        'parameters':{'type':'object', 'properties':{'amount':{'type':'number', 'minimum':0, 'maximum':1}},
                      'required':['amount'], 'additionalProperties':False},
        'compatibility':{'blender_min':[5,1,0], 'blender_max':[5,2,0], 'engines':['BLENDER_EEVEE_NEXT'],
                         'target_types':['MESH'], 'contexts':['background','live']},
        'coverage':{'reads':['geometry'], 'writes':['modifiers'], 'dependencies':['geometry','materials']},
        'invocation':{'kind':'python_function', 'entry':'harness_fixture.mark',
                      'completion':'synchronous', 'cancellation':'between_calls'},
        'update':{'identity':'effect_key', 'shared_materials':'none'},
        'validators':['inspect_output','verify_saved'],
        'cases':[{'name':'baseline', 'parameters':{'amount':.5}, 'context':'background', 'expect':'pass'}]}


ADAPTER = '''raise RuntimeError("DISCOVERY_EXECUTED_CODE")
def preflight(context, parameters): pass
def apply(context, parameters, effect_id): pass
def inspect_output(context, effect_id): pass
def verify_saved(observation, output): pass
'''


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.adapter = self.root / 'source.py'; self.adapter.write_text(ADAPTER)
        self.asset = self.root / 'asset.txt'; self.asset.write_text('asset bytes')

    def draft(self, value=None):
        from dcc_harness import recipes
        return recipes.draft(self.root, value or recipe(), str(self.adapter), [str(self.asset)])

    def test_draft_and_inspection_never_import_adapter_and_are_not_qualified(self):
        from dcc_harness import recipes
        ref = self.draft()
        loaded = recipes.load(self.root, ref['id'], ref['digest'])
        self.assertEqual(loaded['state'], 'DRAFT')
        self.assertEqual(loaded['recipe'], recipe())
        with self.assertRaisesRegex(ValueError, 'qualified|DRAFT'):
            recipes.require_qualified(self.root, ref['id'], ref['digest'])
        self.assertEqual(self.draft(), ref)
        self.assertEqual(recipes.inspect(self.root,ref['id'],ref['digest'])['state'],'DRAFT')

    def test_immutable_versions_same_id_and_tamper_detection(self):
        from dcc_harness import recipes
        first = self.draft(); second_value = recipe(); second_value['version'] = 2
        second = self.draft(second_value)
        self.assertNotEqual(first['digest'], second['digest'])
        bundle = recipes.load(self.root, first['id'], first['digest'])
        Path(bundle['adapter']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            recipes.load(self.root, first['id'], first['digest'])
        bundle = recipes.load(self.root, second['id'], second['digest'])
        Path(bundle['assets']['asset.txt']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            recipes.load(self.root, second['id'], second['digest'])

    def test_rejects_traversal_and_duplicate_asset_names(self):
        from dcc_harness import recipes
        for name in ('../escape', 'a/b', 'a\\b', 'C:drive', '', 'CON'):
            value = recipe(); value['id'] = name
            with self.assertRaises(ValueError): self.draft(value)
        ref = self.draft()
        with self.assertRaises(ValueError): recipes.load(self.root, '../escape', ref['digest'])
        with self.assertRaises(ValueError): recipes.load(self.root, ref['id'], '../escape')
        other = self.root / 'nested/asset.txt'; other.parent.mkdir(); other.write_text('other')
        with self.assertRaisesRegex(ValueError, 'duplicate|Duplicate'):
            recipes.draft(self.root, recipe(), str(self.adapter), [str(self.asset),str(other)])

    def test_closed_contract_and_parameter_validation(self):
        from dcc_harness import recipes
        for change in ({'unknown':True}, {'validators':[]}, {'provider':{'id':'x'}},
                       {'invocation':{'kind':'eval','entry':'x','completion':'modal','cancellation':'none'}}):
            value = {**recipe(), **change}
            with self.assertRaises(ValueError): recipes.validate(value)
        for params in ({'amount':'0.5'}, {'amount':True}, {'amount':float('nan')},
                       {'amount':2}, {}, {'amount':.5,'surprise':True}):
            with self.assertRaises(ValueError): recipes.validate_parameters(recipe(), params)
        self.assertEqual(recipes.validate_parameters(recipe(), {'amount':.5}), {'amount':.5})

    def test_schema_cannot_fetch_refs_or_silently_ignore_keywords(self):
        from dcc_harness import recipes
        for schema in ({'$ref':'https://invalid.example/schema'}, {'type':'object','patternProperties':{}},
                       {'type':'object','properties':{},'required':[],'additionalProperties':True}):
            value = recipe(); value['parameters'] = schema
            with self.assertRaises(ValueError): recipes.validate(value)

    def test_missing_protocol_function_refused_without_import(self):
        self.adapter.write_text('raise RuntimeError("NEVER_IMPORT")\ndef apply(context, parameters, effect_id): pass\n')
        with self.assertRaisesRegex(ValueError, 'protocol|validator'):
            self.draft()

    def test_generated_scaffold_is_inert_and_explicitly_incomplete(self):
        from dcc_harness import recipes
        text = recipes.scaffold(recipe())
        self.assertIn('def preflight(', text)
        self.assertIn('def verify_saved(', text)
        self.assertIn('NotImplementedError', text)
        compile(text, '<scaffold>', 'exec')

    def test_bundle_manifest_rejects_extra_files_and_changed_metadata(self):
        from dcc_harness import recipes
        ref = self.draft(); loaded = recipes.load(self.root, ref['id'], ref['digest'])
        path = Path(loaded['adapter']).parent / 'unlisted.py'; path.write_text('x=1')
        with self.assertRaisesRegex(ValueError, 'members|changed'):
            recipes.load(self.root, ref['id'], ref['digest'])

    def test_qualification_cannot_register_caller_success_or_foreign_report(self):
        from dcc_harness import recipes
        ref = self.draft(); report = self.root / 'fake-report.json'
        report.write_text(json.dumps({'passed':True,'recipe_digest':ref['digest']}))
        with self.assertRaisesRegex(ValueError, 'retained|qualification'):
            recipes.register_qualified(self.root, str(report))

    def test_context_compatibility_is_explicit_and_not_inferred_from_installation(self):
        from dcc_harness import recipes
        value = recipe()
        self.assertTrue(recipes.applicable(value, [5,1,1], 'BLENDER_EEVEE_NEXT', 'MESH', 'background'))
        for context in ('modal','viewport'):
            self.assertFalse(recipes.applicable(value, [5,1,1], 'BLENDER_EEVEE_NEXT', 'MESH', context))
        self.assertFalse(recipes.applicable(value, [5,2,0], 'BLENDER_EEVEE_NEXT', 'MESH', 'background'))
        self.assertFalse(recipes.applicable(value, [5,1,1], 'CYCLES', 'MESH', 'background'))

    def test_recipe_requires_positive_case_for_each_qualified_context(self):
        from dcc_harness import recipes
        value = recipe()
        self.assertEqual(recipes.qualifiable_contexts(value), ['background'])
        value['cases'][0]['expect'] = 'fail'
        value['cases'][0]['failure_contains'] = 'Expected specific failure'
        self.assertEqual(recipes.qualifiable_contexts(value), [])
