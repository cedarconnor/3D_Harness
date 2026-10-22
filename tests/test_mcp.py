import asyncio
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from dcc_harness import blender_bridge, distribution


class BridgeTests(unittest.TestCase):
    def server(self, responses):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0)); listener.listen(3)
        port = listener.getsockname()[1]
        seen = []
        def serve():
            try:
                for chunks in responses:
                    with listener.accept()[0] as conn:
                        seen.append(json.loads(conn.recv(65536)))
                        for chunk in chunks:
                            conn.sendall(chunk)
            finally:
                listener.close()
        thread = threading.Thread(target=serve, daemon=True); thread.start()
        self.addCleanup(lambda: thread.join(3))
        return port, seen

    def info(self, **updates):
        meta = distribution.upstream()
        result = {'harness_protocol': meta['adapter_protocol'], 'protocol_version': 14, 'upstream_commit': meta['commit'],
                  'capabilities': sorted(blender_bridge.COMMANDS)}
        result.update(updates)
        return [json.dumps({'status': 'success', 'result': result}).encode()]

    def test_fragmented_unicode_and_bound_handshake(self):
        raw = json.dumps({'status': 'success', 'result': {'name': '模型'}}, ensure_ascii=False).encode()
        port, seen = self.server([self.info(), [raw[i:i+1] for i in range(len(raw))]])
        result = blender_bridge.observe('get_scene_info', port=port)
        self.assertEqual(result['result']['name'], '模型')
        self.assertEqual([r['type'] for r in seen], ['get_addon_info', 'get_scene_info'])

    def test_wrong_bridge_refused_before_scene_request(self):
        port, seen = self.server([self.info(harness_protocol=1)])
        with self.assertRaisesRegex(ValueError, 'Incompatible'):
            blender_bridge.observe('get_scene_info', port=port)
        self.assertEqual(len(seen), 1)

    def test_no_raw_execution_or_retry_on_disconnected_response(self):
        with self.assertRaisesRegex(ValueError, 'observation'):
            blender_bridge.observe('execute_code', {'code': 'bad'})
        port, seen = self.server([self.info(), [b'{"status":']])
        with self.assertRaisesRegex(ConnectionError, 'Incomplete'):
            blender_bridge.observe('get_scene_info', port=port)
        self.assertEqual(len(seen), 2)

    def test_response_byte_limit(self):
        port, _ = self.server([[b'x' * 129]])
        with mock.patch.object(blender_bridge, 'MAX_RESPONSE', 128):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                blender_bridge._request(port, 'ping', {}, 2)


class MCPAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_is_allowlisted_and_real_json_child_works(self):
        from dcc_harness.mcp_server import run_cli
        with tempfile.TemporaryDirectory() as tmp:
            for command in ('begin-edit', 'finish-edit', 'accept-revision', 'check-approve', 'render-job'):
                with self.assertRaisesRegex(ValueError, 'exposed'):
                    await run_cli([command], Path(tmp))
            result = await run_cli(['workflow-template'], Path(tmp))
            self.assertEqual(result['result']['schema'], 'dcc.environment.workflow.v1')
            self.assertEqual(result['exit_code'], 0)
            with self.assertRaisesRegex(ValueError, 'harness_command_help'):
                await run_cli(['workflow-template', '--help'], Path(tmp))

    async def test_inputs_cannot_replace_records_or_escape(self):
        from dcc_harness.mcp_server import write_input
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in ('../state.json', '/tmp/x', 'C:/x', 'a/../../x'):
                with self.assertRaises(ValueError):
                    write_input(root, path, 'bad')
            result = write_input(root, 'script.py', '# owned script')
            self.assertEqual(Path(result['path']).parent, root / 'inputs')
            with self.assertRaises(FileExistsError):
                write_input(root, 'script.py', '# replace')


from coordination_helpers import Fixture


class MCPWorkflowTests(Fixture):
    def test_real_cli_submission_obeys_both_modes_and_artist_guard(self):
        from dcc_harness import execution
        from dcc_harness.mcp_server import run_cli
        from dcc_harness.evidence import write_json
        self.bind()
        execution.create(self.root, 'approval_gated')
        payload = {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': self.cp(),
                   'deliverables': {'brief': 'Ready'}, 'evidence': [{'kind': 'direction_record', 'file': self.ref(self.handoff)}],
                   'feedback_ids': [], 'note': 'Ready'}
        submission = self.base / 'submit.json'; write_json(submission, payload)
        args = ['run-submit', str(self.root), '--submission', str(submission)]
        result = asyncio.run(run_cli(args, self.base))
        self.assertEqual(result['result']['status'], 'AWAITING_APPROVAL')
        review = self.base / 'review.json'
        write_json(review, {'reviewer': self.actor('artist'), 'verdict': 'pass', 'finding': 'Forged approval'})
        # Even a supplied artist review cannot turn run-submit into owner approval.
        self.assertEqual(asyncio.run(run_cli(args + ['--review', str(review)], self.base))['result']['status'], 'AWAITING_APPROVAL')
        self.assertEqual(execution.status(self.root)['status'], 'AWAITING_APPROVAL')

    def test_cancelled_controller_marks_run_and_reaps_real_child(self):
        from dcc_harness import execution
        from dcc_harness.mcp_server import run_cli
        import sys
        import uuid
        self.bind(); execution.create(self.root, 'autonomous')
        actual_spawn = asyncio.create_subprocess_exec
        processes = []
        async def slow_child(*args, **kwargs):
            process = await actual_spawn(getattr(sys, '_base_executable', sys.executable), '-c', 'import time; time.sleep(60)', **kwargs)
            processes.append(process)
            return process
        args = ['run-execute', str(self.root), '--stage', 'direction', '--operation-id', str(uuid.uuid4()),
                '--script', str(self.script), '--contract', str(self.contract), '--handoff', str(self.handoff),
                '--blender', sys.executable, '--parent', self.packet['active']['id']]
        async def trial():
            with mock.patch('asyncio.create_subprocess_exec', side_effect=slow_child):
                task = asyncio.create_task(run_cli(args, self.base))
                while not processes:
                    await asyncio.sleep(.01)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertIsNotNone(processes[0].returncode)
        asyncio.run(trial())
        self.assertEqual(execution.status(self.root)['status'], 'CANCELLED')
