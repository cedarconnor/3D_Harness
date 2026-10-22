"""Provider discovery is metadata; only explicit pinned profiles activate code."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

FIXTURES = Path(__file__).parent / 'fixtures/addons'
BLENDER = {'version':[5, 1, 1], 'build_hash':'fixture-build', 'background':True}


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(FIXTURES, self.root / 'addons')
        self.roots = [{'path':str(self.root / 'addons/legacy'), 'namespace':''},
                      {'path':str(self.root / 'addons/extensions'), 'namespace':'bl_ext.fixture'}]

    def scan(self, **kwargs):
        from dcc_harness import provider_sources
        return provider_sources.scan(self.roots, BLENDER, **kwargs)

    def item(self, inventory, name):
        return next(p for p in inventory['providers'] if p['id'] == name)

    def test_inventory_does_not_import_disabled_legacy_or_extension(self):
        result = self.scan()
        self.assertNotIn('import_sentinel', sys.modules)
        self.assertNotIn('bl_ext.fixture.example_extension', sys.modules)
        legacy = self.item(result, 'harness_fixture')
        extension = self.item(result, 'bl_ext.fixture.example_extension')
        self.assertTrue(legacy['installed'] and legacy['compatible'])
        self.assertFalse(legacy['enabled'])
        self.assertEqual(extension['kind'], 'extension')
        self.assertTrue(extension['compatible'])
        self.assertEqual(legacy['loaded_identity'], 'not_loaded')

    def test_enabled_state_and_shadowed_ownership_are_separate(self):
        path = str(self.root / 'addons/legacy/harness_fixture/__init__.py')
        result = self.scan(enabled={'harness_fixture':{'path':path, 'source_digest':None}})
        item = self.item(result, 'harness_fixture')
        self.assertTrue(item['enabled'])
        self.assertEqual(item['loaded_identity'], 'unknown')
        self.roots.append({'path':str(self.root / 'addons/conflict'), 'namespace':''})
        result = self.scan(enabled={'harness_fixture':{'path':path, 'source_digest':None}},
                           operators=[{'id':'object.fixture', 'module':'harness_fixture'}])
        self.assertEqual(self.item(result, 'harness_fixture')['availability'], 'AMBIGUOUS')
        self.assertIsNone(result['operators'][0]['provider'])

    def test_source_change_without_version_change_invalidates_profile(self):
        from dcc_harness import environments
        inventory = self.scan()
        ref = environments.create_profile(self.root / 'project', inventory, ['harness_fixture'], {'harness_fixture':{'quality':3}})
        profile = environments.load_profile(ref)
        environments.validate_profile(profile, inventory)
        source = self.root / 'addons/legacy/harness_fixture/__init__.py'
        source.write_text(source.read_text() + '\n# changed without version bump\n')
        changed = self.scan()
        self.assertEqual(self.item(inventory, 'harness_fixture')['version'], self.item(changed, 'harness_fixture')['version'])
        with self.assertRaisesRegex(ValueError, 'source|STALE'):
            environments.validate_profile(profile, changed)
        self.assertEqual(environments.create_profile(self.root / 'project', inventory, ['harness_fixture'], {'harness_fixture':{'quality':3}}), ref)

    def test_missing_dependency_and_incompatible_blender_are_refused(self):
        from dcc_harness import environments
        inventory = self.scan(); item = self.item(inventory, 'harness_fixture')
        item['dependencies'] = ['missing_provider']
        with self.assertRaisesRegex(ValueError, 'dependency'):
            environments.create_profile(self.root / 'project', inventory, ['harness_fixture'], {})
        inventory = self.scan(); self.item(inventory, 'harness_fixture')['compatible'] = False
        with self.assertRaisesRegex(ValueError, 'compatible'):
            environments.create_profile(self.root / 'project', inventory, ['harness_fixture'], {})

    def test_secrets_are_not_inventory_or_profile_preferences(self):
        from dcc_harness import environments
        result = self.scan(enabled={'harness_fixture':{'path':'unused', 'source_digest':None, 'api_key':'NEVER_DISCLOSE'}})
        self.assertNotIn('NEVER_DISCLOSE', json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'preference|secret'):
            environments.create_profile(self.root / 'project', self.scan(), ['harness_fixture'], {'harness_fixture':{'api_key':'NEVER_DISCLOSE'}})
        self.assertFalse((self.root / 'project/capabilities/profiles').exists())

    def test_network_license_configuration_and_profile_tampering(self):
        from dcc_harness import environments
        inventory = self.scan(); item = self.item(inventory, 'network_license')
        self.assertEqual(item['network'], 'required')
        self.assertTrue(item['license_required'])
        with self.assertRaisesRegex(ValueError, 'offline|license'):
            environments.create_profile(self.root / 'project', inventory, ['network_license'], {})
        ref = environments.create_profile(self.root / 'project', inventory, ['harness_fixture'], {})
        path = Path(ref['path']); path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed|digest'):
            environments.load_profile(ref)

    def test_extension_wheels_do_not_trigger_automatic_dependency_installation(self):
        from dcc_harness import environments
        manifest = self.root / 'addons/extensions/example_extension/blender_manifest.toml'
        manifest.write_text(manifest.read_text() + '\nwheels = ["./wheels/dependency.whl"]\n')
        with self.assertRaisesRegex(ValueError, 'dependency'):
            environments.create_profile(self.root / 'project', self.scan(), ['bl_ext.fixture.example_extension'], {})

    def test_invalid_metadata_does_not_abort_other_discovery(self):
        source = self.root / 'addons/legacy/import_sentinel.py'
        for metadata in ("{'name':'Broken','blender':(1e309,1,0)}",
                         "{'name':'Broken','blender':(5,1,0),'dcc_harness':[]}"):
            source.write_text('bl_info = ' + metadata)
            result = self.scan()
            self.assertEqual(self.item(result, 'import_sentinel')['availability'], 'UNKNOWN')
            self.assertTrue(self.item(result, 'harness_fixture')['compatible'])

    def test_offline_scope_blocks_only_explicit_managed_calls(self):
        import socket
        from dcc_harness.offline import scope
        attempts = []
        with socket.socket() as server:
            server.bind(('127.0.0.1',0)); server.listen(1)
            with scope(attempts), socket.socket() as client:
                with self.assertRaisesRegex(RuntimeError,'Offline provider'):
                    client.connect(server.getsockname())
            self.assertEqual(len(attempts),1)
            with socket.create_connection(server.getsockname()):
                connection,_ = server.accept(); connection.close()
            self.assertEqual(len(attempts),1)
