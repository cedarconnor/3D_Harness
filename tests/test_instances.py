"""Portable checks for collection instances: contracts, comparison coverage and adoption."""
import copy
import unittest

from dcc_harness.adoption import plan_identities, validate_plan, verify_applied_plan
from dcc_harness.continuity_checks import evaluate_stage, validate_contract
from dcc_harness.evidence import compare
from test_continuity_checks import contract, observation, resign

INSTANCE = {'collection': 'bench-asset', 'asset_id': 'bench', 'asset_id_source': 'collection', 'library': None,
            'definition_hash': 'd' * 64, 'members': 2, 'triangles': 24}
COVERAGE = {'version': 1, 'measured': ['collection instance placement, definition hash and library provenance'],
            'not_measured': ['Geometry Nodes, particle and vertex or face instancing']}


def with_instances(*placements):
    obs = observation()
    for iid, x in placements:
        obs['objects'][iid] = {'name': iid, 'type': 'EMPTY', 'asset_id': 'bench', 'matrix_world': [[1, 0, 0, x]],
                               'material_ids': [], 'instance': copy.deepcopy(INSTANCE), 'vertices': 16, 'triangles': 24,
                               'bounds': [[x - 1, -.3, 0], [x + 1, .3, .9]], 'dimensions': [2, .6, .9]}
    obs['coverage']['collection_instances'] = copy.deepcopy(COVERAGE)
    return resign(obs)


class InstanceContractTests(unittest.TestCase):
    def test_contracts_may_permit_the_instance_field(self):
        validate_contract({**contract(), 'allowed_object_prefixes': {'set.': ['instance', 'matrix_world']}})

    def test_moving_a_permitted_instance_passes_and_a_protected_one_fails(self):
        before = with_instances(('set.bench.a', 0), ('set.bench.b', 3))
        after = copy.deepcopy(before)
        after['objects']['set.bench.a']['matrix_world'] = [[1, 0, 0, 1]]
        after['objects']['set.bench.a']['bounds'] = [[0, -.3, 0], [2, .3, .9]]
        resign(after)
        allowed = {**contract(), 'allowed_object_prefixes': {'set.bench.a': ['matrix_world', 'bounds']}}
        self.assertTrue(evaluate_stage(before, after, allowed)['passed'])
        protected = {**contract(), 'allowed_object_prefixes': {'set.bench.b': ['matrix_world', 'bounds']}}
        self.assertFalse(evaluate_stage(before, after, protected)['passed'])

    def test_a_changed_library_or_definition_fails_unless_instance_is_permitted(self):
        before = with_instances(('set.bench.a', 0))
        after = copy.deepcopy(before)
        after['objects']['set.bench.a']['instance']['definition_hash'] = 'e' * 64
        resign(after)
        self.assertFalse(evaluate_stage(before, after, contract())['passed'])
        allowed = {**contract(), 'allowed_object_prefixes': {'set.bench.a': ['instance']}}
        self.assertTrue(evaluate_stage(before, after, allowed)['passed'])

    def test_exact_asset_counts_include_instances(self):
        obs = with_instances(('set.bench.a', 0), ('set.bench.b', 3))
        self.assertTrue(evaluate_stage(obs, obs, {**contract(), 'exact_asset_counts': {'bench': 2, 'table': 1}})['passed'])
        self.assertFalse(evaluate_stage(obs, obs, {**contract(), 'exact_asset_counts': {'bench': 3}})['passed'])


class CoverageComparisonTests(unittest.TestCase):
    def test_adding_the_first_instance_still_compares(self):
        before = observation()
        after = with_instances(('set.bench.a', 0))
        delta = compare(before, after, {'objects': {'set.bench.a': ['created']}})
        self.assertTrue(delta['coverage_matches'])
        self.assertTrue(delta['passed'])

    def test_other_coverage_differences_still_fail(self):
        before = with_instances(('set.bench.a', 0))
        after = copy.deepcopy(before)
        after['coverage']['collection_instances']['version'] = 2
        self.assertFalse(compare(before, resign(after))['coverage_matches'])
        after = copy.deepcopy(before)
        after['coverage']['continuity_observation'] = 3
        self.assertFalse(compare(before, resign(after))['coverage_matches'])


def collection(name, read_only=False, scope=True, **properties):
    return {'name': name, 'scope': scope, 'properties': properties, 'read_only': read_only}


def inventory(*collections):
    empty = {'name': 'Bench.A', 'scope': True, 'properties': {}, 'read_only': False, 'type': 'EMPTY', 'mesh': None, 'scenes': ['Scene']}
    return {'scene': 'Scene', 'objects': [empty], 'materials': [], 'collections': list(collections)}


SOURCE = {'path': 'fixture.blend', 'sha256': 'a' * 64}


class CollectionAdoptionTests(unittest.TestCase):
    def assignments(self, plan, kind='collection'):
        return {(a['name'], a['property']): a['value'] for a in plan['assignments'] if a['kind'] == kind}

    def test_local_instanced_collection_without_asset_id_is_assigned_one(self):
        plan = plan_identities(inventory(collection('bench-asset')), SOURCE)
        self.assertEqual(plan['status'], 'READY')
        value = self.assignments(plan)[('bench-asset', 'dcc_asset_id')]
        self.assertTrue(value.startswith('asset.adopted.'))
        validate_plan(plan, inventory(collection('bench-asset')), SOURCE)

    def test_existing_ids_linked_and_unused_collections_are_left_alone(self):
        plan = plan_identities(inventory(collection('bench-asset', dcc_asset_id='bench'), collection('crate [lib.blend]', read_only=True),
                                         collection('unused', scope=False)), SOURCE)
        self.assertEqual(plan['status'], 'READY')
        self.assertEqual(self.assignments(plan), {})

    def test_duplicate_collection_asset_ids_block(self):
        plan = plan_identities(inventory(collection('a', dcc_asset_id='bench'), collection('b', dcc_asset_id='bench')), SOURCE)
        self.assertEqual(plan['status'], 'BLOCKED')

    def test_verifier_checks_collection_identities(self):
        source = inventory(collection('bench-asset'))
        plan = plan_identities(source, SOURCE)
        applied = copy.deepcopy(source)
        for row in plan['assignments']:
            pool = {'object': 'objects', 'material': 'materials', 'collection': 'collections'}[row['kind']]
            next(r for r in applied[pool] if r['name'] == row['name'])['properties'][row['property']] = row['value']
        verify_applied_plan(plan, applied)
        applied['collections'][0]['properties']['dcc_asset_id'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'Saved identities'):
            verify_applied_plan(plan, applied)

    def test_inventories_without_collections_plan_as_before(self):
        old = inventory()
        del old['collections']
        self.assertEqual(plan_identities(old, SOURCE)['status'], 'READY')


class LibraryGuidanceTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from dcc_harness import workflow
        from dcc_harness.evidence import file_hash
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        native = self.base / 'scene.blend'
        native.write_bytes(b'synthetic native with a linked library - not Blender qualification')
        obs = observation()
        obs['native_dirty'] = False
        obs['scene']['world'] = {'nodes': [], 'links': []}
        obs['coverage']['measured'] = ['geometry', 'materials']
        obs['checkpoint_sha256'] = file_hash(native)
        obs['objects']['crate.a'] = {'name': 'crate.a', 'type': 'EMPTY', 'asset_id': 'crate', 'matrix_world': [[1]], 'material_ids': [],
                                     'instance': {**INSTANCE, 'asset_id': 'crate', 'library': {'path': '//lib/crate-v1.blend', 'relative': True,
                                                                                               'exists': True, 'sha256': 'f' * 64}}}
        obs['coverage']['collection_instances'] = copy.deepcopy(COVERAGE)
        from dcc_harness.evidence import write_json
        write_json(self.base / 'scene.json', resign(obs))
        (self.base / 'BRIEF.md').write_text('Library fixture', encoding='utf-8')
        self.root = self.base / 'state'
        workflow.start(self.root, native, self.base / 'scene.json', 'Library fixture', {})

    def test_library_projects_point_native_commands_at_the_working_copy(self):
        from dcc_harness import guidance
        result = guidance.next_steps(self.root)
        steps = {s['id']: s for s in result['steps']}
        working = '"<your working copy beside its libraries .blend>"'
        self.assertIn('observe ' + working, steps['observe']['command'])
        self.assertIn('--current ' + working, steps['begin-edit']['command'])
        self.assertIn('linked libraries', steps['observe']['why'])
        self.assertIn('//lib/crate-v1.blend', guidance.brief(self.root))


if __name__ == '__main__':
    unittest.main()
