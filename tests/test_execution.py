import copy
import sys
import uuid
import subprocess
import time
import threading
import concurrent.futures
from pathlib import Path
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import execution, workflow
from dcc_harness.evidence import read_json, write_json, file_hash


class ExecutionTests(Fixture):
    def submission(self):
        return {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': self.cp(),
                'deliverables': {'brief': 'Within brief'}, 'evidence': [{'kind': 'direction_record', 'file': self.ref(self.handoff)}],
                'feedback_ids': [], 'note': 'Ready for review'}

    def test_service_submits_and_advances_autonomous_stage_once(self):
        self.managed()
        payload = self.submission()
        result = execution.submit(self.root, payload, self.base)
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(result['completion']['result']['artistic_acceptance'], 'not_evaluated')
        self.assertEqual(execution.submit(self.root, payload, self.base)['status'], 'COMPLETE')

    def test_service_pauses_gated_submission_for_owner(self):
        self.managed('approval_gated')
        result = execution.submit(self.root, self.submission(), self.base)
        self.assertEqual(result['status'], 'AWAITING_APPROVAL')
        self.assertEqual(execution.status(self.root)['status'], 'AWAITING_APPROVAL')

    def test_identical_submission_after_reopen_is_reviewed_again(self):
        self.managed(); payload = self.submission()
        first = execution.submit(self.root, payload, self.base)
        self.apply('stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': 'direction',
                                  'reason': 'Review again', 'authority': self.actor()})
        second = execution.submit(self.root, payload, self.base)
        self.assertNotEqual(first['submission']['revision'], second['submission']['revision'])
        self.assertEqual(execution.status(self.root)['stages'][0]['state'], 'complete')

    def test_stage_completed_between_admission_and_reservation_cannot_execute(self):
        self.managed()
        original = workflow.begin_edit
        def complete_then_begin(*args, **kwargs):
            self.complete(self.submit())
            return original(*args, **kwargs)
        with mock.patch('dcc_harness.workflow.begin_edit', side_effect=complete_then_begin), mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker):
            result = self.execute()
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def managed(self, mode='autonomous', **kwargs):
        self.bind()
        return execution.create(self.root, mode, **kwargs)

    def execute(self, stage='direction', operation_id=None):
        return execution.execute(self.root, stage, operation_id or str(uuid.uuid4()), self.script,
                                 self.contract, self.handoff, 'blender', self.packet['active']['id'], timeout=30)

    def native_worker(self, blender, folder, worker, action, request, **kwargs):
        # Native process boundary only; the actual journal/check/publication code runs.
        if action == 'execute':
            Path(request['output']).write_bytes(b'owned native candidate')
        elif action == 'observe':
            obs = copy.deepcopy(self.obs)
            obs['checkpoint_sha256'] = file_hash(request['source']['path'])
            write_json(Path(request['out']) / 'observation.json', obs)
        else:
            raise AssertionError(action)

    def test_owned_execution_publishes_once_and_replay_does_not_dispatch(self):
        self.managed()
        op = str(uuid.uuid4())
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker):
            result = self.execute(operation_id=op)
        self.assertEqual(result['status'], 'PUBLISHED')
        again = self.execute(operation_id=op)
        self.assertEqual(again, result)
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)
        self.script.write_text('# changed')
        with self.assertRaisesRegex(ValueError, 'different content'):
            self.execute(operation_id=op)

    def test_gated_mode_requires_owner_review_before_next_stage(self):
        self.managed('approval_gated')
        submitted = self.submit()
        with self.assertRaisesRegex(ValueError, 'Artist review'):
            self.complete(submitted)
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            self.execute('delivery')
        self.complete(submitted, owner=True, reviewer=self.actor('artist'))
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker):
            self.assertEqual(self.execute('delivery')['status'], 'PUBLISHED')

    def test_autonomous_mode_advances_with_agent_review_but_keeps_technical_checks(self):
        self.managed()
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            self.execute('delivery')
        self.complete(self.submit())
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker):
            self.assertEqual(self.execute('delivery')['status'], 'PUBLISHED')

    def test_direct_workflow_and_legacy_journal_cannot_bypass_managed_admission(self):
        self.managed()
        with self.assertRaisesRegex(RuntimeError, 'managed execution'):
            self.begin()
        with self.assertRaisesRegex(RuntimeError, 'managed execution'):
            workflow.Continuity(self.root).project.begin('bypass', self.script)

    def test_unknown_outcome_is_never_redispatched_and_can_be_rejected(self):
        self.managed()
        op = str(uuid.uuid4())
        with mock.patch('dcc_harness.execution.run_worker', side_effect=RuntimeError('lost worker')):
            result = self.execute(operation_id=op)
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        with self.assertRaisesRegex(RuntimeError, 'reconcile'):
            self.execute()
        recovered = execution.reconcile(self.root, op, accept=False, reason='No candidate; discard owned attempt')
        self.assertEqual(recovered['status'], 'REJECTED')
        self.assertFalse(workflow.Continuity(self.root).status()['pending'])

    def test_budget_and_cancel_block_dispatch(self):
        self.managed(max_operations=1)
        op = str(uuid.uuid4())
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker):
            self.execute(operation_id=op)
        with self.assertRaisesRegex(RuntimeError, 'budget'):
            self.execute()
        execution.cancel(self.root)
        self.assertEqual(execution.status(self.root)['status'], 'CANCELLED')

    def test_cancellation_during_work_never_publishes(self):
        self.managed()
        def worker(*args, **kwargs):
            self.native_worker(*args, **kwargs)
            execution.cancel(self.root)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=worker):
            result = self.execute()
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_reopening_predecessor_during_work_blocks_publication(self):
        self.managed(); self.complete(self.submit())
        def worker(*args, **kwargs):
            self.native_worker(*args, **kwargs)
            if args[3] == 'observe':
                self.apply('stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': 'direction',
                                          'reason': 'Direction changed', 'authority': self.actor()})
        with mock.patch('dcc_harness.execution.run_worker', side_effect=worker):
            result = self.execute('delivery')
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_failure_before_reservation_can_be_rejected(self):
        self.managed(); op = str(uuid.uuid4())
        with mock.patch('dcc_harness.workflow.begin_edit', side_effect=RuntimeError('before reservation')):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(execution.reconcile(self.root, op, accept=False, reason='No reservation made')['status'], 'REJECTED')

    def test_interruption_after_native_check_recovers_without_running_script(self):
        self.managed(); op = str(uuid.uuid4())
        real_write = workflow.write_json
        def interrupted(path, value, **kwargs):
            if Path(path).name == 'native-outcome.json':
                raise RuntimeError('interrupted after check')
            return real_write(path, value, **kwargs)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker), mock.patch('dcc_harness.workflow.write_json', side_effect=interrupted):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        result = execution.reconcile(self.root, op, accept=True, reason='Inspected independently reopened candidate')
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)

    def test_interruption_after_publication_recovers_receipt_without_duplicate_checkpoint(self):
        self.managed(); op = str(uuid.uuid4())
        real_write = workflow.write_json
        def interrupted(path, value, **kwargs):
            if Path(path).name == 'outcome.json':
                raise RuntimeError('interrupted after publication')
            return real_write(path, value, **kwargs)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=self.native_worker), mock.patch('dcc_harness.workflow.write_json', side_effect=interrupted):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        result = execution.reconcile(self.root, op, accept=True, reason='Recover committed checkpoint')
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)

    def test_interruption_before_operation_pointer_recovers_from_journal(self):
        self.managed(); op = str(uuid.uuid4())
        real_write = workflow.write_json
        def interrupted(path, value, **kwargs):
            if Path(path).name == 'operation.json':
                raise RuntimeError('journal committed; pointer not written')
            return real_write(path, value, **kwargs)
        with mock.patch('dcc_harness.workflow.write_json', side_effect=interrupted):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(execution.reconcile(self.root, op, accept=False, reason='No native dispatch')['status'], 'REJECTED')
        self.assertFalse(workflow.Continuity(self.root).status()['pending'])

    def test_controller_process_death_leaves_reconcilable_attempt_and_releases_lock(self):
        self.managed(); op = str(uuid.uuid4()); marker = self.base / 'dispatched.txt'
        code = ("from dcc_harness import execution; from pathlib import Path; import time\n"
                "def worker(*args, **kwargs):\n"
                f"    Path({str(marker)!r}).write_text('reserved before dispatch')\n"
                "    time.sleep(60)\n"
                "execution.run_worker = worker\n"
                f"execution.execute({str(self.root)!r}, 'direction', {op!r}, {str(self.script)!r}, "
                f"{str(self.contract)!r}, {str(self.handoff)!r}, 'blender', {self.packet['active']['id']!r}, timeout=30)\n")
        with subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
            deadline = time.monotonic() + 15
            try:
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(marker.exists(), 'Controller did not reach reserved dispatch')
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=10)
        self.assertEqual(execution.status(self.root)['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(execution.reconcile(self.root, op, accept=False, reason='Controller killed before native work')['status'], 'REJECTED')

    def test_concurrent_controller_cannot_dispatch_second_attempt(self):
        self.managed(); entered = threading.Event(); release = threading.Event()
        def worker(*args, **kwargs):
            if args[3] == 'execute':
                entered.set()
                if not release.wait(10):
                    raise RuntimeError('Test controller was not released')
            self.native_worker(*args, **kwargs)
        with mock.patch('dcc_harness.execution.run_worker', side_effect=worker), concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(self.execute)
            try:
                self.assertTrue(entered.wait(10))
                with self.assertRaisesRegex(RuntimeError, 'already active'):
                    self.execute()
            finally:
                release.set()
            self.assertEqual(future.result(timeout=15)['status'], 'PUBLISHED')
        self.assertEqual(len(execution.status(self.root)['operations']), 1)


class ProcessTests(__import__('unittest').TestCase):
    def test_timeout_terminates_and_reaps_owned_process(self):
        from dcc_harness.native import run_process
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(TimeoutError):
                run_process([sys.executable, '-c', 'import time; time.sleep(30)'], Path(folder) / 'log', timeout=.1)

    def test_cancel_terminates_owned_process(self):
        from dcc_harness.native import run_process
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                run_process([sys.executable, '-c', 'import time; time.sleep(30)'], Path(folder) / 'log', cancelled=lambda: True)
