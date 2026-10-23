"""Regressions from the fresh P21 whole-branch review."""
import asyncio
import contextlib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

from dcc_harness import distribution, live_recovery
from dcc_harness.evidence import write_json


STUBS = '''
import sys, types
bpy = types.ModuleType('bpy')
bpy.types = types.SimpleNamespace(Operator=type('Operator', (), {}), Panel=type('Panel', (), {}))
bpy.app = types.SimpleNamespace(handlers=types.SimpleNamespace(persistent=lambda f:f), version_string='fixture')
sys.modules['bpy'] = bpy
mathutils = types.ModuleType('mathutils'); mathutils.Matrix = object; mathutils.Vector = object
sys.modules['mathutils'] = mathutils
'''


class BridgeImportTests(unittest.TestCase):
    def run_isolated(self, code):
        result = subprocess.run([sys.executable, '-c', STUBS + code], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_independent_verifier_package_import(self):
        self.run_isolated('from dcc_harness.data.bridge import attachment, operations\n')

    def test_loaded_bridge_refuses_disk_replacement(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp); distribution.export_addon(out / 'bridge.zip')
            with zipfile.ZipFile(out / 'bridge.zip') as archive:
                archive.extractall(out)
            self.run_isolated('''
import json, hashlib
from pathlib import Path
sys.path.insert(0, %r)
import dcc_harness_bridge as bridge
server = bridge.ObservationServer()
assert server.execute_command({'type':'get_addon_info', 'params':{}})['status'] == 'success'
folder = Path(bridge.__file__).parent
target = folder / 'jobs.py'; target.write_bytes(target.read_bytes() + b'\\n# new runtime\\n')
manifest = json.loads((folder / 'manifest.json').read_text())
manifest['files']['jobs.py'] = hashlib.sha256(target.read_bytes()).hexdigest()
(folder / 'manifest.json').write_text(json.dumps(manifest))
result = server.execute_command({'type':'get_addon_info', 'params':{}})
assert result['status'] == 'error', result
assert 'restart' in result['message'].lower(), result
''' % tmp)


class PrivateReaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_reader_refuses_private_descriptor_and_content_copy(self):
        from dcc_harness.mcp_server import create_server
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / '.harness-mcp/bridge'; folder.mkdir(parents=True)
            token = 'private-fixture-' + 'x' * 48
            contents = json.dumps({'schema':'dcc.blender.session.v1', 'token':token})
            for path in (folder / 'session.json', root / 'copied-descriptor.txt'):
                path.write_text(contents)
                try:
                    result = await create_server(tmp).call_tool('harness_read', {'path':str(path)})
                except Exception as error:
                    result = str(error)
                self.assertNotIn(token, str(result))
            normal = root / 'evidence.txt'; normal.write_text('ordinary evidence')
            self.assertIn('ordinary evidence', str(await create_server(tmp).call_tool('harness_read', {'path':str(normal)})))


class RecoveryRefusalTests(unittest.TestCase):
    def test_known_refusal_permits_new_explicit_attempt_but_unknown_never_replays(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp); op = str(uuid.uuid4()); folder = root / 'execution/operations' / op
            folder.mkdir(parents=True); write_json(folder / 'request.json', {'backend':'live', 'stage':'direction'})
            stack.enter_context(mock.patch.object(live_recovery.execution, 'configuration', return_value={'backend':'live', 'runtime':'pin'}))
            stack.enter_context(mock.patch.object(live_recovery.ew, 'runtime_stamp', return_value='pin'))
            stack.enter_context(mock.patch.object(live_recovery.execution, '_exclusive', side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live_recovery.execution, '_authorized', side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch('dcc_harness.live.read_binding', return_value={'descriptor':'private', 'session_id':'s', 'generation':'g'}))
            captures = []
            def call(command, payload, **kwargs):
                if command == 'attach_check': return {'fingerprint':'a' * 64}
                captures.append(payload)
                if len(captures) == 1:
                    return {'state':'REFUSED_BEFORE_MUTATION', 'request':payload, 'reason':'BUSY: still running'}
                raise ConnectionError('Lost reply after possible mutation')
            native = stack.enter_context(mock.patch.object(live_recovery.blender_bridge, 'call', side_effect=call))
            with self.assertRaisesRegex(RuntimeError, 'BUSY'):
                live_recovery.reconcile(root, op, 'keep-current', 'a' * 64)
            with self.assertRaisesRegex(ConnectionError, 'Lost reply'):
                live_recovery.reconcile(root, op, 'keep-current', 'a' * 64)
            self.assertEqual(len(captures), 2)
            self.assertNotEqual(captures[0]['attempt_id'], captures[1]['attempt_id'])
            native.reset_mock()
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                live_recovery.reconcile(root, op, 'keep-current', 'a' * 64)
            native.assert_not_called()
