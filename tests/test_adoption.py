import copy
from pathlib import Path
import tempfile
import unittest

from dcc_harness.adoption import apply, plan_identities, preview, validate_plan, verify_applied_plan
from dcc_harness.evidence import file_hash, write_json


def obj(name, mesh='Mesh', **properties):
    return {'name': name, 'scope': True, 'properties': properties, 'read_only': False,
            'type': 'MESH', 'mesh': mesh, 'scenes': ['Scene']}


def fixture():
    return {'scene': 'Scene', 'objects': [obj('A'), obj('B')], 'materials': [
        {'name': 'Wood', 'scope': True, 'properties': {}, 'read_only': False, 'outside_users': []}]}


SOURCE = {'path': 'fixture.blend', 'sha256': 'a' * 64}


class AdoptionTests(unittest.TestCase):
    def test_shared_mesh_gets_one_asset_and_distinct_instances(self):
        inventory = fixture()
        before = copy.deepcopy(inventory)
        plan = plan_identities(inventory, SOURCE)
        assets = [a['value'] for a in plan['assignments'] if a['property'] == 'dcc_asset_id']
        instances = [a['value'] for a in plan['assignments'] if a['property'] == 'dcc_instance_id']
        self.assertEqual(plan['status'], 'READY')
        self.assertEqual(len(set(assets)), 1)
        self.assertEqual(len(set(instances)), 2)
        self.assertEqual(inventory, before)
        validate_plan(plan, inventory, SOURCE)

    def test_existing_ids_preserved_and_missing_shared_asset_inherits(self):
        inventory = fixture()
        inventory['objects'][0]['properties'] = {'dcc_instance_id': 'artist.a', 'dcc_asset_id': 'bench'}
        plan = plan_identities(inventory, SOURCE)
        self.assertFalse(any(a['name'] == 'A' for a in plan['assignments']))
        self.assertEqual(next(a['value'] for a in plan['assignments'] if a['property'] == 'dcc_asset_id'), 'bench')

    def test_distinct_meshes_have_distinct_new_asset_ids(self):
        inventory = fixture()
        inventory['objects'][1]['mesh'] = 'OtherMesh'
        plan = plan_identities(inventory, SOURCE)
        self.assertEqual(len({a['value'] for a in plan['assignments'] if a['property'] == 'dcc_asset_id'}), 2)

    def test_explicit_grouping_across_meshes_is_preserved(self):
        inventory = fixture()
        for index, item in enumerate(inventory['objects']):
            item['mesh'] = str(index)
            item['properties'] = {'dcc_instance_id': str(index), 'dcc_asset_id': 'group'}
        inventory['materials'][0]['properties']['dcc_material_id'] = 'wood'
        self.assertEqual(plan_identities(inventory, SOURCE)['assignments'], [])

    def test_duplicate_ids_block_entire_plan(self):
        for kind, prop in [('objects', 'dcc_instance_id'), ('materials', 'dcc_material_id')]:
            with self.subTest(kind=kind):
                inventory = fixture()
                inventory[kind] = [copy.deepcopy(inventory[kind][0]) for _ in range(2)]
                for i, record in enumerate(inventory[kind]):
                    record['name'] = str(i)
                    record['properties'][prop] = 'duplicate'
                plan = plan_identities(inventory, SOURCE)
                self.assertEqual(plan['status'], 'BLOCKED')
                self.assertEqual(plan['assignments'], [])
                self.assertIn('Duplicate', ' '.join(plan['issues']))

    def test_invalid_present_id_is_never_repaired(self):
        for invalid in ('', '  ', 3, None, {'invalid_type': 'IDPropertyArray'}):
            inventory = fixture()
            inventory['objects'][0]['properties']['dcc_asset_id'] = invalid
            plan = plan_identities(inventory, SOURCE)
            self.assertEqual(plan['status'], 'BLOCKED')
            self.assertEqual(plan['assignments'], [])

    def test_missing_shared_asset_with_conflicting_owners_blocks(self):
        inventory = fixture()
        inventory['objects'] += [obj('C')]
        inventory['objects'][0]['properties']['dcc_asset_id'] = 'one'
        inventory['objects'][1]['properties']['dcc_asset_id'] = 'two'
        self.assertIn('ambiguous', ' '.join(plan_identities(inventory, SOURCE)['issues']))

    def test_existing_distinct_assets_on_shared_mesh_need_no_guess(self):
        inventory = fixture()
        for item in inventory['objects']:
            item['properties']['dcc_asset_id'] = item['name']
        self.assertEqual(plan_identities(inventory, SOURCE)['status'], 'READY')

    def test_outside_scene_users_and_linked_targets_block_before_assignment(self):
        for field, value in [('scenes', ['Scene', 'Another']), ('read_only', True)]:
            inventory = fixture()
            inventory['objects'][0][field] = value
            self.assertEqual(plan_identities(inventory, SOURCE)['assignments'], [])
        inventory = fixture()
        inventory['materials'][0]['outside_users'] = ['UnscopedObject']
        self.assertEqual(plan_identities(inventory, SOURCE)['status'], 'BLOCKED')

    def test_outside_scope_duplicate_of_active_id_is_detected(self):
        inventory = fixture()
        inventory['objects'][0]['properties']['dcc_instance_id'] = 'duplicate'
        inventory['objects'][1].update(scope=False, scenes=['Other'])
        inventory['objects'][1]['properties']['dcc_instance_id'] = 'duplicate'
        self.assertEqual(plan_identities(inventory, SOURCE)['status'], 'BLOCKED')

    def test_empty_scene_blocks(self):
        inventory = fixture()
        inventory['objects'] = []
        self.assertEqual(plan_identities(inventory, SOURCE)['status'], 'BLOCKED')

    def test_stale_inventory_and_edited_assignments_are_rejected(self):
        original = fixture()
        plan = plan_identities(original, SOURCE)
        changed = copy.deepcopy(original)
        changed['objects'][0]['name'] = 'renamed'
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            validate_plan(plan, changed, SOURCE)
        changed_plan = copy.deepcopy(plan)
        changed_plan['assignments'][0]['property'] = 'arbitrary'
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            validate_plan(changed_plan, original, SOURCE)

    def test_changed_source_rejected_without_launch_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.blend'
            source.write_bytes(b'synthetic, not Blender qualification')
            plan = plan_identities(fixture(), {'path': str(source), 'sha256': file_hash(source)})
            path = root / 'plan.json'
            write_json(path, plan)
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                apply(path, root / 'result', 'no-blender-should-launch')
            self.assertFalse((root / 'result').exists())

    def test_existing_output_directory_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.blend'
            source.write_bytes(b'synthetic, not Blender qualification')
            before = source.read_bytes()
            with self.assertRaises(FileExistsError):
                preview(source, root, 'no-blender-should-launch')
            self.assertEqual(source.read_bytes(), before)

    def test_saved_verifier_requires_exact_new_and_preserved_identities(self):
        inventory = fixture()
        inventory['objects'][0]['properties']['dcc_instance_id'] = 'artist-id'
        plan = plan_identities(inventory, SOURCE)
        applied = copy.deepcopy(inventory)
        for row in plan['assignments']:
            records = applied['objects' if row['kind'] == 'object' else 'materials']
            next(r for r in records if r['name'] == row['name'])['properties'][row['property']] = row['value']
        verify_applied_plan(plan, applied)
        with self.assertRaisesRegex(ValueError, 'Saved identities'):
            verify_applied_plan(plan, inventory)
        applied['objects'][0]['properties']['dcc_instance_id'] = 'wrong-but-valid'
        with self.assertRaisesRegex(ValueError, 'Saved identities'):
            verify_applied_plan(plan, applied)
