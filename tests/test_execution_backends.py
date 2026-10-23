import copy
import uuid
from pathlib import Path
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import execution, workflow
from dcc_harness.evidence import read_json, write_json, file_hash


class BackendTests(Fixture):
    def test_fresh_capability_reuses_before_mutation_only_admission(self):
        from dcc_harness import capabilities
        self.start(); request=self.request(); request['capability']={'requirement':{},'resolution':{},'parameters':{}}
        with mock.patch.object(capabilities,'admit'),mock.patch.object(capabilities,'reuse',return_value={'status':'REUSED'}), \
             mock.patch.object(execution,'_admit',side_effect=AssertionError('No mutation admission for reuse')):
            self.assertEqual(execution.execute_operation(self.root,request)['status'],'REUSED')
        self.assertFalse((self.root/'execution/operations').exists())

    def test_capability_uses_same_reservation_budget_and_independent_verifier(self):
        from dcc_harness import capabilities, environments, provider_sources
        self.start(); request=self.request(); request['capability']={'requirement':{},'resolution':{},'parameters':{}}
        inventory=provider_sources.scan([{'path':str(Path(__file__).parent / 'fixtures/addons/legacy'),'namespace':''}],
                    {'version':[5,1,1],'build_hash':'fixture','background':True})
        request['profile']=environments.create_profile(self.root,inventory,['harness_fixture'],{})
        def worker(blender,folder,worker,action,payload,**kwargs):
            if action=='execute': self.assertEqual(Path(worker).name,'_capability_blender.py')
            if action=='capability-verify':
                write_json(folder / 'capability-verified.json',{'passed':True})
            else: self.worker(blender,folder,worker,action,payload,**kwargs)
        with mock.patch.object(capabilities,'admit',return_value=request['capability']), \
             mock.patch.object(capabilities,'reuse',return_value=None), \
             mock.patch.object(capabilities,'prepare_operation_receipt'), \
             mock.patch.object(capabilities,'record_operation',return_value={'sha256':'a'*64}), \
             mock.patch('dcc_harness.execution.run_worker',side_effect=worker) as native:
            first=execution.execute_operation(self.root,request)
            second=execution.execute_operation(self.root,request)
        self.assertEqual(first['status'],'PUBLISHED'); self.assertEqual(second,first)
        self.assertEqual([call.args[3] for call in native.call_args_list],['execute','observe','capability-verify'])
        self.assertEqual(len(execution._operations(self.root)),1)

    def test_profile_is_pinned_and_applied_to_execution_and_observer(self):
        from dcc_harness import environments, provider_sources
        self.start(); request = self.request()
        inventory = provider_sources.scan([{'path':str(Path(__file__).parent / 'fixtures/addons/legacy'), 'namespace':''}],
            {'version':[5, 1, 1], 'build_hash':'fixture', 'background':True})
        profile = environments.create_profile(self.root, inventory, ['harness_fixture'], {})
        request['profile'] = profile
        def worker(*args, **kwargs):
            self.assertEqual(kwargs['profile'], profile)
            self.worker(*args, **kwargs)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=worker) as native:
            result = execution.execute_operation(self.root, request)
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual([c.args[3] for c in native.call_args_list], ['execute', 'observe'])
        folder = self.root / 'execution/operations' / request['operation_id']
        self.assertEqual(read_json(folder / 'request.json')['profile'], profile)

    def test_changed_profile_fails_before_reservation(self):
        from dcc_harness import environments, provider_sources
        self.start(); request = self.request()
        inventory = provider_sources.scan([{'path':str(Path(__file__).parent / 'fixtures/addons/legacy'), 'namespace':''}],
            {'version':[5, 1, 1], 'build_hash':'fixture', 'background':True})
        request['profile'] = environments.create_profile(self.root, inventory, ['harness_fixture'], {})
        Path(request['profile']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Profile file changed'):
            execution.execute_operation(self.root, request)
        self.assertFalse((self.root / 'execution/operations').exists())

    def request(self, operation_id=None):
        return {'schema': 'dcc.execution.operation.v2', 'backend': 'background',
                'operation_id': operation_id or str(uuid.uuid4()), 'stage': 'direction',
                'script': str(self.script), 'contract': str(self.contract), 'handoff': str(self.handoff),
                'blender': 'fixture', 'expected_parent': self.packet['active']['id'], 'timeout': 30}

    def start(self):
        self.assertTrue(callable(getattr(execution, 'execute_operation', None)), 'shared operation API missing')
        self.bind()
        execution.create(self.root, 'autonomous')

    def worker(self, blender, folder, worker, action, payload, **kwargs):
        if action == 'execute':
            Path(payload['output']).write_bytes(b'backend result')
        elif action == 'observe':
            obs = copy.deepcopy(self.obs)
            obs['checkpoint_sha256'] = file_hash(payload['source']['path'])
            write_json(Path(payload['out']) / 'observation.json', obs)
        else:
            self.fail(action)

    def test_background_api_preserved(self):
        self.start()
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.worker):
            result = execution.execute(self.root, 'direction', str(uuid.uuid4()), self.script,
                                       self.contract, self.handoff, 'fixture', self.packet['active']['id'])
        self.assertEqual(result['status'], 'PUBLISHED')
        config = execution.configuration(self.root)
        self.assertEqual(config['schema'], 'dcc.execution.run.v2')
        self.assertEqual(config['backend'], 'background')

    def test_duplicate_uuid_dispatches_once(self):
        self.start(); request = self.request()
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.worker) as native:
            first = execution.execute_operation(self.root, request)
            second = execution.execute_operation(self.root, request)
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'PUBLISHED')
        self.assertEqual(sum(c.args[3] == 'execute' for c in native.call_args_list), 1)
        folder = self.root / 'execution/operations' / request['operation_id']
        self.assertTrue((folder / 'dispatched.json').exists())
        self.assertEqual(read_json(folder / 'backend-saved.json')['state'], 'SAVED')

    def test_changed_request_refused(self):
        self.start(); request = self.request()
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.worker):
            execution.execute_operation(self.root, request)
        request['timeout'] = 10
        with self.assertRaisesRegex(ValueError, 'different content'):
            execution.execute_operation(self.root, request)

    def test_restart_after_dispatch_needs_reconciliation(self):
        self.start(); request = self.request()
        with mock.patch('dcc_harness.execution.run_worker', side_effect=RuntimeError('lost connection')) as native:
            first = execution.execute_operation(self.root, request)
            second = execution.execute_operation(self.root, request)
        self.assertEqual(first['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(second['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(native.call_count, 1)
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_v1_read_does_not_rewrite(self):
        self.start()
        path = self.root / 'execution/run.json'
        config = read_json(path); config['schema'] = 'dcc.execution.run.v1'; config.pop('backend')
        import json
        path.write_text(json.dumps(config))
        original = path.read_bytes()
        self.assertEqual(execution.configuration(self.root), config)
        self.assertEqual(path.read_bytes(), original)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.worker):
            self.assertEqual(execution.execute_operation(self.root, self.request())['status'], 'PUBLISHED')

    def test_backend_mismatch_is_rejected_before_reserving(self):
        self.start(); request = self.request(); request['backend'] = 'live'
        with self.assertRaisesRegex(ValueError, 'backend'):
            execution.execute_operation(self.root, request)
        self.assertFalse((self.root / 'execution/operations').exists())

    def test_live_cancel_does_not_kill_an_owned_process(self):
        self.assertTrue(callable(getattr(execution, 'execute_operation', None)))
        self.bind(); execution.create(self.root, 'autonomous', backend='live')
        request = self.request(); request['backend'] = 'live'
        fixture = self
        class FakeLive:
            def prepare(self, value):
                return {'operation_id': value['operation_id']}
            def submit(self, value, prepared):
                return value['operation_id']
            def status(self, operation_id):
                execution.cancel(fixture.root)
                return {'operation_id': operation_id, 'state': 'RUNNING'}
            def cancel(self, operation_id):
                self.cancelled = operation_id
        backend = FakeLive()
        with mock.patch('subprocess.Popen.kill') as kill:
            with mock.patch('dcc_harness.execution.make_backend', return_value=backend), mock.patch('dcc_harness.live.ensure_aligned'):
                result = execution.execute_operation(self.root, request)
        kill.assert_not_called()
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(backend.cancelled, request['operation_id'])
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)
        self.assertTrue((self.root / 'execution/cancel.json').exists())
