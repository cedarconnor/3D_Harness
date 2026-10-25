"""Recovery must distinguish rejected evidence, unsent requests and durable results."""
import contextlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

from dcc_harness import blender_bridge, execution, live, live_recovery, workflow
from dcc_harness.evidence import digest, read_json, write_json, file_hash
import test_execution
import test_review_live
from coordination_helpers import Fixture
from test_live_protocol import bridge_leaf
from test_live_review import STUBS


class RejectedCandidateTests(Fixture):
    managed = test_execution.ExecutionTests.managed
    execute = test_execution.ExecutionTests.execute
    native_worker = test_execution.ExecutionTests.native_worker
    def test_invalid_candidate_can_be_rejected_without_changing_accepted_checkpoint(self):
        self.managed()
        operation = str(uuid.uuid4())

        def invalid_worker(*args, **kwargs):
            self.native_worker(*args, **kwargs)
            if args[3] == 'observe':
                path = Path(args[4]['out']) / 'observation.json'
                observed = read_json(path)
                observed['issues'].append('Object Cube has no dcc_instance_id')
                observed['revision'] = digest({k: observed[k] for k in ('objects', 'materials', 'scene', 'coverage', 'issues')})
                path.unlink()
                write_json(path, observed)

        with mock.patch.object(execution, 'run_worker', side_effect=invalid_worker):
            self.assertEqual(self.execute(operation_id=operation)['status'], 'NEEDS_RECONCILIATION')
        folder = self.root / 'execution/operations' / operation
        retained = {p.name: file_hash(p) for p in (folder / 'candidate.blend', folder / 'observation.json')}
        with self.assertRaises(ValueError):
            execution.reconcile(self.root, operation, accept=True, reason='Invalid evidence must not be accepted')
        result = execution.reconcile(self.root, operation, accept=False, reason='Discard invalid candidate')
        self.assertEqual(result['status'], 'REJECTED')
        state = workflow.Continuity(self.root).status()
        self.assertEqual(state['active']['id'], self.packet['active']['id'])
        self.assertFalse(state['pending'])
        self.assertEqual(retained, {p.name: file_hash(p) for p in (folder / 'candidate.blend', folder / 'observation.json')})
        with mock.patch.object(execution, 'run_worker', side_effect=self.native_worker):
            self.assertEqual(self.execute()['status'], 'PUBLISHED')

    def test_reject_retains_already_frozen_candidate_check(self):
        self.managed()
        operation = str(uuid.uuid4())
        original = workflow.write_json

        def interrupt(path, value, **kwargs):
            if Path(path).name == 'native-outcome.json':
                raise RuntimeError('interrupted after check')
            return original(path, value, **kwargs)

        with mock.patch.object(execution, 'run_worker', side_effect=self.native_worker), \
                mock.patch.object(workflow, 'write_json', side_effect=interrupt):
            self.assertEqual(self.execute(operation_id=operation)['status'], 'NEEDS_RECONCILIATION')
        folder = self.root / 'execution/operations' / operation
        edit = self.root / 'edits' / read_json(folder / 'reservation.json')['edit']
        original_check = (edit / 'check.json').read_bytes()
        self.assertEqual(execution.reconcile(self.root, operation, accept=False, reason='Discard')['status'], 'REJECTED')
        self.assertEqual((edit / 'check.json').read_bytes(), original_check)
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_interrupted_invalid_candidate_rejection_keeps_accepted_inputs(self):
        self.managed()
        operation = str(uuid.uuid4())
        with mock.patch.object(execution, 'run_worker', side_effect=RuntimeError('worker failed')):
            self.execute(operation_id=operation)
        folder = self.root / 'execution/operations' / operation
        (folder / 'candidate.blend').write_bytes(b'invalid candidate')
        write_json(folder / 'observation.json', {'invalid': True})
        original = workflow.write_json

        def interrupt(path, value, **kwargs):
            if Path(path).name == 'native-outcome.json': raise RuntimeError('interrupted rejection')
            return original(path, value, **kwargs)

        with mock.patch.object(workflow, 'write_json', side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, 'interrupted rejection'):
                execution.reconcile(self.root, operation, accept=False, reason='Discard')
        self.assertEqual(execution.reconcile(self.root, operation, accept=False, reason='Discard')['status'], 'REJECTED')
        self.assertFalse(workflow.Continuity(self.root).status()['pending'])


class LiveRejectedCandidateTests(Fixture):
    request = test_review_live.HostRefusalTests.request
    start = test_review_live.HostRefusalTests.start
    backend = test_review_live.HostRefusalTests.backend
    binding = test_review_live.HostRefusalTests.binding
    external_recovery = test_review_live.HostRefusalTests.external_recovery

    def test_interrupted_live_rejection_keeps_accepted_inputs(self):
        request, receipt, worker = self.external_recovery()
        operation = request['operation_id']
        folder = self.root / 'execution/operations' / operation
        (folder / 'candidate.blend').write_bytes(b'invalid candidate')
        write_json(folder / 'observation.json', {'invalid': True})
        original = workflow.write_json

        def interrupt(path, value, **kwargs):
            if Path(path).name == 'native-outcome.json': raise RuntimeError('interrupted rejection')
            return original(path, value, **kwargs)

        with mock.patch.object(live_recovery, 'run_worker', side_effect=worker), \
                mock.patch.object(blender_bridge, 'call', return_value={'matches': True}):
            with mock.patch.object(workflow, 'write_json', side_effect=interrupt):
                with self.assertRaisesRegex(RuntimeError, 'interrupted rejection'):
                    live_recovery.reconcile(self.root, operation, 'keep-current', 'a' * 64)
            result = live_recovery.reconcile(self.root, operation, 'keep-current', 'a' * 64)
        self.assertEqual(result['live_state'], 'READY')
        self.assertFalse(workflow.Continuity(self.root).status()['pending'])


class RecoveryDispatchTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            session = bridge_leaf('session').Session(tmp, 9878)
            root = Path(tmp) / 'state'
            operation = str(uuid.uuid4())
            folder = root / 'execution/operations' / operation
            folder.mkdir(parents=True)
            write_json(folder / 'request.json', {'backend': 'live', 'stage': 'direction'})
            binding = {'descriptor': str(session.descriptor_path), 'session_id': session.session_id,
                       'generation': session.generation}
            for target, name, value in ((execution, 'configuration', {'backend': 'live', 'runtime': 'pin'}),
                                        (live_recovery.ew, 'runtime_stamp', 'pin'), (live, 'read_binding', binding)):
                stack.enter_context(mock.patch.object(target, name, return_value=value))
            stack.enter_context(mock.patch.object(execution, '_exclusive', side_effect=lambda *a: contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(execution, '_authorized', side_effect=lambda *a: contextlib.nullcontext()))
            info = {'harness_protocol': 3, 'protocol_version': 14,
                    'upstream_commit': blender_bridge.upstream()['commit'], 'features': list(blender_bridge.FEATURES),
                    'paired_commands': list(blender_bridge.PAIRED_COMMANDS), 'bridge_manifest': blender_bridge.bridge_manifest()}
            yield root, operation, folder, info

    def test_failed_recovery_handshake_does_not_poison_later_attempt(self):
        with self.fixture() as (root, operation, folder, info):
            handshakes, captures = [], []

            def wire(port, command, params, timeout, **kwargs):
                if command == 'get_addon_info':
                    handshakes.append(command)
                    if len(handshakes) == 2:
                        raise ConnectionRefusedError('Blender closed before recovery handshake')
                    return info
                if command == 'attach_check':
                    return {'fingerprint': 'a' * 64}
                if kwargs.get('before_send'):
                    kwargs['before_send']()
                captures.append(params['payload'])
                return {'state': 'REFUSED_BEFORE_MUTATION', 'request': params['payload'], 'reason': 'BUSY: confirmed unsent mutation'}

            with mock.patch.object(blender_bridge, '_request', side_effect=wire):
                with self.assertRaisesRegex(blender_bridge.BridgeTransportError, 'before recovery handshake'):
                    live_recovery.reconcile(root, operation, 'keep-current', 'a' * 64)
                with self.assertRaisesRegex(RuntimeError, 'BUSY: confirmed'):
                    live_recovery.reconcile(root, operation, 'keep-current', 'a' * 64)
            self.assertEqual(len(captures), 1)

    def test_socket_connect_failure_does_not_record_dispatch(self):
        called = mock.Mock()
        with mock.patch.object(blender_bridge.socket, 'create_connection', side_effect=ConnectionRefusedError):
            with self.assertRaises(ConnectionRefusedError):
                blender_bridge._request(9878, 'recovery_capture', {}, 180, before_send=called)
        called.assert_not_called()

    def test_ambiguous_sent_capture_is_never_repeated(self):
        with self.fixture() as (root, operation, folder, info):
            captures = []

            def wire(port, command, params, timeout, **kwargs):
                if command == 'get_addon_info': return info
                if command == 'attach_check': return {'fingerprint': 'a' * 64}
                kwargs['before_send']()
                captures.append(params['payload'])
                raise TimeoutError('Lost after dispatch')

            with mock.patch.object(blender_bridge, '_request', side_effect=wire):
                with self.assertRaisesRegex(blender_bridge.BridgeTransportError, 'Lost after dispatch'):
                    live_recovery.reconcile(root, operation, 'keep-current', 'a' * 64)
                with self.assertRaisesRegex(RuntimeError, 'never repeat'):
                    live_recovery.reconcile(root, operation, 'keep-current', 'a' * 64)
            self.assertEqual(len(captures), 1)

    def test_snapshot_commands_have_save_sized_deadline_but_short_handshake(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = bridge_leaf('session').Session(tmp, 9878)
            info = {'harness_protocol': 3, 'protocol_version': 14,
                    'upstream_commit': blender_bridge.upstream()['commit'], 'features': list(blender_bridge.FEATURES),
                    'paired_commands': list(blender_bridge.PAIRED_COMMANDS), 'bridge_manifest': blender_bridge.bridge_manifest()}
            for command in ('attach_check', 'attach_acknowledge', 'attach_rebind', 'job_submit',
                            'job_check', 'job_acknowledge', 'recovery_acknowledge'):
                with self.subTest(command=command), mock.patch.object(blender_bridge, '_request', side_effect=[info, {}]) as wire:
                    blender_bridge.call(command, {}, binding=session.descriptor_path)
                    self.assertEqual(wire.call_args_list[0].args[3], 10)
                    self.assertEqual(wire.call_args_list[1].args[3], 180)


class NativeBridgeBoundaryTests(unittest.TestCase):
    def isolated(self, code):
        result = subprocess.run([sys.executable, '-c', STUBS + code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_large_durable_result_survives_wire_limit_without_redispatch(self):
        self.isolated('''
import tempfile, uuid
from unittest import mock
from dcc_harness import blender_bridge
from dcc_harness.data.bridge import ObservationServer, recovery
with tempfile.TemporaryDirectory() as tmp:
    server = ObservationServer(workspace=tmp)
    private = blender_bridge.descriptor(server.session.descriptor_path)
    payload = {'operation_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()),
               'decision': 'keep-current', 'expected_fingerprint': 'a'*64}
    saved = {'inventory': 'x'*(8*1024*1024), 'operation_id': payload['operation_id']}
    with mock.patch.object(recovery, 'capture', return_value=saved) as capture:
        response = server.execute_command({'type': 'recovery_capture', 'params': {
            'auth': {k: private[k] for k in ('token','session_id','generation')}, 'payload': payload}})
    assert response['status'] == 'error' and 'byte limit' in response['message'], response
    assert blender_bridge.retained_outcome('recovery_capture', payload, private) == saved
    with mock.patch.object(blender_bridge, '_request', side_effect=AssertionError('Must not redispatch')):
        assert blender_bridge.call('recovery_capture', payload, binding=server.session.descriptor_path) == saved
    capture.assert_called_once()
''')

    def test_reload_refusal_is_durable_before_recovery_handler(self):
        self.isolated('''
import tempfile, uuid
from unittest import mock
from dcc_harness import blender_bridge
from dcc_harness.data.bridge import ObservationServer, recovery
with tempfile.TemporaryDirectory() as tmp:
    server = ObservationServer(workspace=tmp)
    private = blender_bridge.descriptor(server.session.descriptor_path)
    payload = {'operation_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()),
               'decision': 'keep-current', 'expected_fingerprint': 'a'*64}
    server.session.invalidate('file reloaded after host handshake')
    with mock.patch.object(recovery, 'capture', side_effect=AssertionError('Must not mutate')) as capture:
        response = server.execute_command({'type': 'recovery_capture', 'params': {
            'auth': {k: private[k] for k in ('token','session_id','generation')}, 'payload': payload}})
    assert response['status'] == 'success', response
    assert response['result']['state'] == 'REFUSED_BEFORE_MUTATION', response
    assert blender_bridge.retained_outcome('recovery_capture', payload, private) == response['result']
    capture.assert_not_called()
''')

    def test_read_only_runtime_error_is_a_retained_refusal(self):
        self.isolated('''
import tempfile, uuid
from unittest import mock
from dcc_harness import blender_bridge
from dcc_harness.data.bridge import ObservationServer
with tempfile.TemporaryDirectory() as tmp:
    server = ObservationServer(workspace=tmp)
    private = blender_bridge.descriptor(server.session.descriptor_path)
    payload = {'operation_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()),
               'decision': 'keep-current', 'expected_fingerprint': 'a'*64}
    with mock.patch.object(server.jobs, 'folder', side_effect=RuntimeError('Scene unavailable before capture')):
        response = server.execute_command({'type': 'recovery_capture', 'params': {
            'auth': {k: private[k] for k in ('token','session_id','generation')}, 'payload': payload}})
    assert response['status'] == 'success', response
    assert response['result']['state'] == 'REFUSED_BEFORE_MUTATION', response
    assert blender_bridge.retained_outcome('recovery_capture', payload, private) == response['result']
''')

    def test_server_queue_deadlines_match_client_for_all_commands(self):
        self.isolated('''
import json
from unittest import mock
from dcc_harness import blender_bridge
from dcc_harness.data import bridge
server = bridge.ObservationServer()
server.running = True
assert set(bridge.SCENE_COMMANDS) == blender_bridge.SCENE_COMMANDS
for command in bridge.PAIRED_COMMANDS:
    client = mock.Mock()
    client.recv.return_value = json.dumps({'type': command, 'params': {}}).encode()
    event = mock.Mock()
    with mock.patch.object(bridge.threading, 'Event', return_value=event), mock.patch.object(bridge.time, 'monotonic', return_value=100):
        server._handle_client(client)
    queued = server.command_queue.get_nowait()
    duration = 180 if command in blender_bridge.SCENE_COMMANDS else 10
    assert queued[3] == 100 + duration, (command, queued[3])
    event.wait.assert_called_once_with(duration)
''')
