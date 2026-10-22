"""Public live entry points preserve scope, authority and preview provenance."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from contextlib import nullcontext

from dcc_harness import live


class SurfaceTests(unittest.TestCase):
    def test_preview_rejects_paths_and_unbounded_render_before_native_work(self):
        validate = getattr(live, 'validate_preview', None)
        self.assertTrue(callable(validate), 'Preview validator missing')
        request = self.preview()
        self.assertEqual(validate(request), request)
        for patch in ({'output': '../escape'}, {'session_id': ''}, {'width': 4096},
                      {'width': True}, {'samples': 1000}, {'frame': float('nan')}):
            with self.assertRaises(ValueError):
                validate({**request, **patch})

    @staticmethod
    def preview():
        return {'session_id': '11111111-1111-4111-8111-111111111111',
                'generation': '22222222-2222-4222-8222-222222222222',
                'frame': 1, 'width': 128, 'height': 128, 'samples': 1,
                'camera': {'lens': 50, 'location': [5, -5, 3], 'target': [0, 0, 0]},
                'compare_checkpoint': True}

    def test_session_discovery_does_not_return_pairing_secret(self):
        discover = getattr(live, 'sessions', None)
        self.assertTrue(callable(discover), 'Session discovery missing')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / '.harness-mcp/bridge'; folder.mkdir(parents=True)
            (folder / 'session.json').write_text('{"token":"private"}')
            with mock.patch('dcc_harness.blender_bridge.call', return_value={'session_id': 'public'}):
                result = discover(tmp)
            self.assertNotIn('private', str(result))
            self.assertEqual(result['sessions'][0]['session_id'], 'public')

    def test_inspection_requires_explicit_session_descriptor(self):
        inspect = getattr(live, 'inspect', None)
        self.assertTrue(callable(inspect), 'Public inspection missing')
        with self.assertRaises(ValueError):
            inspect({'scene': 'Scene', 'kind': 'objects'})

    def test_wrong_preview_session_refuses_before_capture(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch('dcc_harness.execution._exclusive', return_value=nullcontext()), \
                mock.patch('dcc_harness.live.read_binding', return_value={'session_id': 'wrong', 'generation': 'wrong'}), \
                mock.patch('dcc_harness.blender_bridge.call') as send:
            with self.assertRaisesRegex(ValueError, 'session'):
                live.preview(tmp, self.preview())
            send.assert_not_called()

    def test_preview_rejects_foreign_capture_path_before_rendering(self):
        from dcc_harness.environment_workflow import runtime_stamp
        request = self.preview()
        binding = {**request, 'descriptor': 'private', 'scene': 'Scene'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch('dcc_harness.execution._exclusive', return_value=nullcontext()), \
                mock.patch('dcc_harness.execution.configuration', return_value={'backend': 'live', 'runtime': runtime_stamp()}), \
                mock.patch('dcc_harness.live.read_binding', return_value=binding), \
                mock.patch('dcc_harness.blender_bridge.call', return_value={'source': {'path': str(Path(tmp) / 'other.blend')}}), \
                mock.patch('dcc_harness.render.render_file') as render:
            with self.assertRaisesRegex(ValueError, 'escaped'):
                live.preview(tmp, request)
            render.assert_not_called()

    def test_status_exposes_current_fingerprint_for_explicit_recovery(self):
        binding = {'state': 'NEEDS_RECONCILIATION', 'session_id': 'session', 'generation': 'generation',
                   'scene': 'Scene', 'descriptor': 'private', 'fingerprint': 'old', 'snapshot': 'old.json'}
        with mock.patch('dcc_harness.execution.status', return_value={'run': {'backend': 'live'}, 'status': 'NEEDS_RECONCILIATION'}), \
                mock.patch('dcc_harness.live.read_binding', return_value=binding), \
                mock.patch('dcc_harness.blender_bridge.call', return_value={'fingerprint': 'current', 'matches': False}):
            self.assertEqual(live.status('unused').get('current_fingerprint'), 'current')


class LiveToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_tools_cannot_approve(self):
        from dcc_harness.mcp_server import create_server
        with tempfile.TemporaryDirectory() as tmp:
            server = create_server(tmp)
            tools = {tool.name for tool in await server.list_tools()}
            self.assertTrue({'blender_session', 'blender_inspect', 'blender_execute',
                             'blender_job', 'blender_preview'} <= tools)
            for name, arguments in (
                ('blender_session', {'action': 'approve', 'payload': {}}),
                ('blender_job', {'action': 'approve', 'operation_id': 'x', 'payload': {}})):
                from mcp.server.fastmcp.exceptions import ToolError
                with self.assertRaises(ToolError):
                    await server.call_tool(name, arguments)
