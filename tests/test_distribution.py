import tempfile
import unittest
from pathlib import Path

from dcc_harness import distribution


class DistributionTests(unittest.TestCase):
    def test_recursive_capability_schema_manifest_and_missing_runtime(self):
        import json, zipfile
        from dcc_harness.bridge_integrity import verify_contents
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bridge.zip'; distribution.export_addon(path)
            with zipfile.ZipFile(path) as archive:
                contents={name.split('/',1)[1]:archive.read(name) for name in archive.namelist()}
            self.assertIn('capabilities/policy.schema.json',contents)
            verify_contents(contents,distribution.bridge_manifest())
            contents.pop('recipes.py')
            with self.assertRaises(ValueError): verify_contents(contents,distribution.bridge_manifest())

    def test_recursive_manifest_accepts_only_canonical_safe_members(self):
        import json,hashlib
        from dcc_harness.bridge_integrity import verify_contents
        for name in ('nested/recipe.json','../escape.json','a/../escape.json','a//b','a\\b','C:/bad'):
            contents={name:b'{}'}
            contents['manifest.json']=json.dumps({'schema':'dcc.blender.bridge.manifest.v1',
                'files':{name:hashlib.sha256(b'{}').hexdigest()}}).encode()
            if name=='nested/recipe.json': verify_contents(contents)
            else:
                with self.assertRaises(ValueError): verify_contents(contents)

    def test_external_directory_contents_do_not_change_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / '.agents/skills/demo/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('[Historical evidence](../../../runs/example/)')
            for name in distribution.SEEDS:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('guide')
            before = distribution.source_rules(root)
            artifact = root / 'runs/example/CONTINUE.md'
            artifact.parent.mkdir(parents=True); artifact.write_text('Local diagnostic')
            self.assertEqual(distribution.source_rules(root), before)

    def test_rules_export_is_complete_verified_and_exclusive(self):
        catalog = distribution.catalog()
        self.assertIn('.agents/skills/dcc-harness/SKILL.md', catalog['files'])
        self.assertIn('docs/guides/MANAGED_EXECUTION.md', catalog['files'])
        self.assertIn('docs/guides/COMBINED_MCP.md', catalog['files'])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'rules'
            distribution.export_rules(target)
            distribution.verify_rules(target)
            with self.assertRaises(FileExistsError):
                distribution.export_rules(target)
            (target / 'docs/guides/MANAGED_EXECUTION.md').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'changed'):
                distribution.verify_rules(target)

    def test_unknown_and_traversing_resource_paths_refused(self):
        for name in ('../pyproject.toml', '/etc/passwd', 'C:/secret', 'missing.md'):
            with self.assertRaises(ValueError):
                distribution.read_rule(name)

    def test_addon_contains_pinned_derivative_and_notice(self):
        import zipfile
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bridge.zip'
            result = distribution.export_addon(path)
            with zipfile.ZipFile(path) as archive:
                self.assertIn('dcc_harness_bridge/LICENSE.upstream', archive.namelist())
                self.assertEqual(hashlib.sha256(archive.read('dcc_harness_bridge/upstream.py')).hexdigest(),
                                 result['upstream']['addon_sha256'])
                self.assertEqual(result['upstream']['upstream_addon_sha256'],
                                 '229ee114f0504b486bdd24bbc8b08fa9b22112f5e831ef8b2e9cc507e9ccbbfe')
                self.assertNotEqual(result['upstream']['addon_sha256'],
                                    result['upstream']['upstream_addon_sha256'])
            with self.assertRaises(FileExistsError):
                distribution.export_addon(path)

    def test_exported_bridge_has_only_observation_dependencies(self):
        import ast
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bridge.zip'
            distribution.export_addon(path)
            with zipfile.ZipFile(path) as archive:
                source = archive.read('dcc_harness_bridge/upstream.py').decode('utf-8')
                tree = ast.parse(source)
                imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                           for alias in node.names}
                self.assertEqual(imports, {'bpy', 'mathutils', 'queue', 'socket', 'threading', 'time', 'traceback'})
                self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))
                classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
                self.assertEqual([node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
                                 ['_object_detail'])
                self.assertEqual([node.name for node in classes], ['BlenderMCPServer'])
                self.assertEqual({node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)},
                                 {'__init__', 'start', 'stop', '_server_loop', 'get_scene_info',
                                  'list_scene_items', '_get_aabb', 'get_object_info'})
                for name in archive.namelist():
                    if name.endswith('.py'):
                        text = archive.read(name).decode('utf-8').lower()
                        for forbidden in ('telemetry', 'usereditrecorder', 'edit_capture', 'human_activity',
                                          'utm_', '?ref=', 'supabase', 'posthog', 'sentry', 'requests',
                                          'undo_post', 'redo_post', 'depsgraph_update_post'):
                            self.assertNotIn(forbidden, text, (name, forbidden))
