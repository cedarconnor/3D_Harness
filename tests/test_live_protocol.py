"""Portable tests of the exported bridge's state machine, without importing bpy."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
import uuid
from unittest import mock

from dcc_harness import distribution
from dcc_harness import blender_bridge


def bridge_leaf(name):
    package = '_harness_bridge_test'
    if package not in sys.modules:
        module = types.ModuleType(package)
        module.__path__ = [str(distribution.DATA / 'bridge')]
        sys.modules[package] = module
    return __import__(package + '.' + name, fromlist=[name])


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((distribution.DATA / 'bridge/session.py').exists(), 'Bridge session implementation missing')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        self.module = bridge_leaf('session')
        self.session = self.module.Session(self.workspace, 9878)
        self.descriptor = json.loads(self.session.descriptor_path.read_text())

    def test_wrong_token_and_session_are_refused_without_disclosure(self):
        token = self.descriptor['token']
        info = self.session.describe()
        self.assertNotIn(token, json.dumps(info))
        for wrong, sid in [('wrong', info['session_id']), (token, str(uuid.uuid4()))]:
            with self.assertRaisesRegex(ValueError, 'Unauthorized') as error:
                self.session.authorize(wrong, sid, info['generation'])
            self.assertNotIn(token, str(error.exception))
        self.session.authorize(token, info['session_id'], info['generation'])

    def test_reload_same_path_invalidates_generation_and_preparation(self):
        old = self.session.describe()
        prepared = self.session.prepare(str(uuid.uuid4()), 'request', 'fingerprint')
        self.session.invalidate('file loaded')
        self.assertNotEqual(self.session.describe()['generation'], old['generation'])
        with self.assertRaisesRegex(ValueError, 'STALE'):
            self.session.consume(prepared, 'request', 'fingerprint')

    def test_preparation_is_one_use_and_binds_request_and_fingerprint(self):
        op = str(uuid.uuid4())
        prepared = self.session.prepare(op, 'request', 'before')
        with self.assertRaisesRegex(ValueError, 'STALE'):
            self.session.consume(prepared, 'changed', 'before')
        with self.assertRaisesRegex(ValueError, 'STALE'):
            self.session.consume(prepared, 'request', 'changed')
        self.session.consume(prepared, 'request', 'before')
        with self.assertRaisesRegex(ValueError, 'STALE'):
            self.session.consume(prepared, 'request', 'before')

    def test_expired_preparation_is_not_consumed(self):
        prepared = self.session.prepare(str(uuid.uuid4()), 'request', 'before')
        with mock.patch.object(self.module.time, 'time', return_value=prepared['expires_at'] + .01):
            with self.assertRaisesRegex(ValueError, 'STALE'):
                self.session.consume(prepared, 'request', 'before')

    def test_one_project_and_one_mutation_at_a_time(self):
        project = self.workspace / 'project'
        self.session.bind(project, 'Scene')
        with self.assertRaisesRegex(ValueError, 'project'):
            self.session.bind(self.workspace / 'other', 'Scene')
        one, two = str(uuid.uuid4()), str(uuid.uuid4())
        self.session.acquire(one)
        with self.assertRaisesRegex(RuntimeError, 'BUSY'):
            self.session.acquire(two)
        self.session.release(one)
        self.session.acquire(two)

    def test_project_paths_cannot_escape_workspace(self):
        with self.assertRaisesRegex(ValueError, 'workspace'):
            self.session.bind(self.workspace.parent / 'outside', 'Scene')


class ExportManifestTests(unittest.TestCase):
    def test_export_hashes_all_bridge_modules(self):
        import hashlib
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bridge.zip'
            distribution.export_addon(path)
            with zipfile.ZipFile(path) as archive:
                prefix = 'dcc_harness_bridge/'
                self.assertIn(prefix + 'manifest.json', archive.namelist())
                manifest = json.loads(archive.read(prefix + 'manifest.json'))
                self.assertIn('session.py', manifest['files'])
                self.assertIn('inspection.py', manifest['files'])
                self.assertEqual(set(archive.namelist()), {prefix + p for p in manifest['files']} | {prefix + 'manifest.json'})
                for name, sha in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(prefix + name)).hexdigest(), sha)


class PairedClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.session = bridge_leaf('session').Session(self.tmp.name, 9878)
        self.private = json.loads(self.session.descriptor_path.read_text())
        self.info = {'harness_protocol': 3, 'protocol_version': 14,
                     'upstream_commit': distribution.upstream()['commit'],
                     'features': list(blender_bridge.FEATURES),
                     'paired_commands': list(blender_bridge.PAIRED_COMMANDS)}

    def test_protocol_two_stays_read_only(self):
        self.info['harness_protocol'] = 2
        with mock.patch.object(blender_bridge, '_request', return_value=self.info) as send:
            with self.assertRaisesRegex(ValueError, 'protocol 3'):
                blender_bridge.call('inspect', {}, binding=self.session.descriptor_path)
        self.assertEqual(send.call_count, 1)

    def test_missing_features_refused_before_authenticated_call(self):
        self.info['features'] = []
        with mock.patch.object(blender_bridge, '_request', return_value=self.info) as send:
            with self.assertRaisesRegex(ValueError, 'features'):
                blender_bridge.call('inspect', {}, binding=self.session.descriptor_path)
        self.assertEqual(send.call_count, 1)

    def test_reload_between_host_steps_cannot_retarget_a_write(self):
        expected = (self.private['session_id'], self.private['generation'])
        self.session.invalidate('same-path reload')
        with mock.patch.object(blender_bridge, '_request') as send:
            with self.assertRaisesRegex(ValueError, 'generation'):
                blender_bridge.call('attach_begin', {}, binding=self.session.descriptor_path, expected=expected)
        send.assert_not_called()

    def test_lost_reply_is_not_retried_and_error_redacts_secret(self):
        token = self.private['token']
        with mock.patch.object(blender_bridge, '_request', side_effect=[self.info, RuntimeError(token)]) as send:
            with self.assertRaisesRegex(RuntimeError, 'redacted') as error:
                blender_bridge.call('inspect', {}, binding=self.session.descriptor_path)
        self.assertNotIn(token, str(error.exception))
        self.assertEqual(send.call_count, 2)

    def test_oversize_request_never_connects(self):
        with mock.patch.object(blender_bridge.socket, 'create_connection') as connect:
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                blender_bridge._request(9878, 'inspect', {'large': 'x' * 65536}, 2)
        connect.assert_not_called()

    def test_concurrent_clients_cannot_acquire_two_jobs(self):
        from concurrent.futures import ThreadPoolExecutor
        def acquire(_):
            try:
                self.session.acquire(str(uuid.uuid4()))
                return True
            except RuntimeError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(acquire, range(2))), 1)

    def test_unmeasured_fields_fail_instead_of_partial_success(self):
        with mock.patch.dict(sys.modules, {'bpy': types.SimpleNamespace()}):
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_COVERAGE'):
                bridge_leaf('inspection').inspect({'kind': 'objects', 'fields': ['animation']})

    def test_target_resolution_never_falls_back_to_names(self):
        module = bridge_leaf('inspection')
        obj = {'dcc_instance_id': 'object.fixture'}
        self.assertIs(module.target(types.SimpleNamespace(objects=[obj]), 'object.fixture'), obj)
        with self.assertRaisesRegex(ValueError, 'missing or ambiguous'):
            module.target(types.SimpleNamespace(objects=[obj, dict(obj)]), 'object.fixture')
