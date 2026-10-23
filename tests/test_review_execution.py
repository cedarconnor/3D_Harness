"""External review regressions for authority and durable managed outcomes."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest import mock

from coordination_helpers import Fixture
import test_execution
from dcc_harness import execution, environment_workflow as ew, workflow, capabilities, bootstrap, distribution
from dcc_harness.evidence import read_json, write_json, file_hash


class ReviewExecutionTests(Fixture):
    managed = test_execution.ExecutionTests.managed
    execute = test_execution.ExecutionTests.execute
    native_worker = test_execution.ExecutionTests.native_worker
    submission = test_execution.ExecutionTests.submission

    def test_autonomous_preserves_artist_stage_and_binding_policy(self):
        manifest = self.manifest(); manifest['stages'][0]['review'] = 'artist_required'
        self.bind(manifest)
        execution.create(self.root, 'autonomous')
        result = execution.submit(self.root, self.submission(), self.base)
        self.assertEqual(result['status'], 'AWAITING_APPROVAL')
        self.assertEqual(execution.status(self.root)['status'], 'AWAITING_APPROVAL')
        with self.assertRaisesRegex(ValueError, 'Artist review'):
            self.complete({'revision': result['submission']['revision']})

    def test_autonomous_preserves_binding_override(self):
        self.bind(review_policies={'direction': 'artist_required'}, owner=True)
        execution.create(self.root, 'autonomous')
        self.assertEqual(execution.submit(self.root, self.submission(), self.base)['status'], 'AWAITING_APPROVAL')

    def test_cancelled_new_submission_is_refused(self):
        self.managed(); execution.cancel(self.root)
        before = self.revision()
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            execution.submit(self.root, self.submission(), self.base)
        self.assertEqual(self.revision(), before)

    def test_cancelled_pending_submission_cannot_resume_agent_completion(self):
        self.managed(); payload = self.submission()
        self.apply('stage.submit', payload)
        execution.cancel(self.root)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            execution.submit(self.root, payload, self.base)

    def test_expired_new_submission_is_refused_but_completed_retry_is_readable(self):
        self.managed(); payload = self.submission()
        with mock.patch('dcc_harness.execution.time.time', return_value=execution.configuration(self.root)['deadline'] + 1):
            with self.assertRaisesRegex(RuntimeError, 'budget'):
                execution.submit(self.root, payload, self.base)
        first = execution.submit(self.root, payload, self.base)
        execution.cancel(self.root)
        again = execution.submit(self.root, payload, self.base)
        self.assertEqual(again['status'], 'COMPLETE')
        self.assertEqual(again['completion']['revision'], first['completion']['revision'])

    def interrupted(self):
        self.managed(); op = str(uuid.uuid4())
        real = workflow.write_json
        def fail(path, value, **kwargs):
            if Path(path).name == 'native-outcome.json':
                raise RuntimeError('interrupted after check')
            return real(path, value, **kwargs)
        with mock.patch.object(execution, 'run_worker', side_effect=self.native_worker), mock.patch.object(workflow, 'write_json', side_effect=fail):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        return op

    def test_runtime_mismatch_cannot_reconcile(self):
        op = self.interrupted()
        with mock.patch.object(ew, 'runtime_stamp', return_value={'version': 'different'}):
            with self.assertRaisesRegex(ValueError, 'runtime'):
                execution.reconcile(self.root, op, accept=True, reason='Inspected')

    def test_verified_reconcile_can_publish_after_deadline_without_dispatch(self):
        op = self.interrupted()
        with mock.patch('dcc_harness.execution.time.time', return_value=execution.configuration(self.root)['deadline'] + 1), mock.patch.object(execution, 'run_worker', side_effect=AssertionError('must not dispatch')):
            result = execution.reconcile(self.root, op, accept=True, reason='Inspected verified candidate')
        self.assertEqual(result['status'], 'PUBLISHED')

    def test_unresolved_operation_precedes_terminal_cancel(self):
        op = self.interrupted(); execution.cancel(self.root)
        self.assertEqual(execution.status(self.root)['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(execution.reconcile(self.root, op, accept=False, reason='Discard')['status'], 'REJECTED')
        self.assertEqual(execution.status(self.root)['status'], 'CANCELLED')

    def test_operation_cancel_can_reconcile_and_run_remains_usable(self):
        self.managed(); op = str(uuid.uuid4())
        def cancel(*args, **kwargs):
            self.native_worker(*args, **kwargs)
            execution.cancel_operation(self.root, op)
        with mock.patch.object(execution, 'run_worker', side_effect=cancel):
            self.assertEqual(self.execute(operation_id=op)['status'], 'NEEDS_RECONCILIATION')
        self.assertFalse((self.root / 'execution/cancel.json').exists())
        execution.reconcile(self.root, op, accept=False, reason='Discard interrupted attempt')
        with mock.patch.object(execution, 'run_worker', side_effect=self.native_worker):
            self.assertEqual(self.execute()['status'], 'PUBLISHED')

    def test_unknown_operation_and_incomplete_configuration_have_explicit_errors(self):
        self.managed()
        with self.assertRaisesRegex(ValueError, 'Unknown managed operation'):
            execution.reconcile(self.root, str(uuid.uuid4()), accept=False, reason='Unknown')
        (self.root / 'execution/run.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Incomplete managed execution configuration'):
            execution.configuration(self.root)

    def test_failed_creation_does_not_publish_partial_run(self):
        self.bind()
        with mock.patch.object(execution, 'write_json', side_effect=RuntimeError('interrupted creation')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted creation'):
                execution.create(self.root, 'autonomous')
        self.assertIsNone(execution.configuration(self.root))
        self.assertEqual(execution.create(self.root, 'autonomous')['status'], 'READY')

    def test_failed_staging_copy_is_retained_with_diagnostic(self):
        self.managed()
        with mock.patch.object(execution, 'copy_verified', side_effect=RuntimeError('copy failed')):
            with self.assertRaisesRegex(RuntimeError, 'copy failed'):
                self.execute()
        staged = list((self.root / 'execution/staging').iterdir())
        self.assertEqual(len(staged), 1)
        self.assertEqual(read_json(staged[0] / 'failure.json')['error'], 'copy failed')
        self.assertEqual(execution.status(self.root)['staging'][0]['status'], 'FAILED_BEFORE_DISPATCH')

    def test_live_status_invalid_binding_is_explicit(self):
        self.managed(backend='live')
        with mock.patch('dcc_harness.live.read_binding', return_value={}):
            self.assertEqual(execution.status(self.root)['live_state'], 'UNBOUND')

    def capability_request(self):
        from test_capabilities import policy
        from dcc_harness import coordination as c
        self.bind()
        capabilities.bind_policy(self.root, policy(), expected_revision=self.revision(), request_id=str(uuid.uuid4()), authority=self.actor())
        execution.create(self.root, 'autonomous')
        req = capabilities.requirements(self.root, 'direction', self.obs)[0]
        return {'schema': 'dcc.execution.operation.v2', 'backend': 'background', 'stage': 'direction',
            'operation_id': str(uuid.uuid4()), 'script': str(self.script), 'contract': str(self.contract),
            'handoff': str(self.handoff), 'blender': 'blender', 'expected_parent': self.packet['active']['id'], 'timeout': 30,
            'capability': {'root': str(self.root), 'requirement': req,
                'resolution': {'selected': req['rule']['candidates'][0], 'state': 'RESOLVED'},
                'parameters': req['rule']['parameters'],
                'effect_id': capabilities.effect_key(req['rule']['capability'], req['target_id'], req['rule']['slot'])}}

    def capability_worker(self, blender, folder, worker, action, payload, **kwargs):
        from dcc_harness.evidence import digest
        if action == 'execute':
            self.native_worker(blender, folder, worker, action, payload, **kwargs)
            measured = capabilities.observed_scope(self.obs, 'ext.table.top', ['geometry', 'materials'])
            output = {'effect_id': payload['capability']['effect_id'], 'effect_count': 1, 'measurements': measured}
            write_json(folder / 'capability-output.json', {'after': measured, 'output': output, 'output_fingerprint': digest(output)})
        elif action == 'capability-verify':
            value = read_json(folder / 'capability-output.json')
            write_json(folder / 'capability-verified.json', {'passed': True, 'output': value['output'],
                'measurements': value['after'], 'output_fingerprint': value['output_fingerprint']})
        else:
            self.native_worker(blender, folder, worker, action, payload, **kwargs)

    def run_capability(self, request):
        with mock.patch.object(capabilities, 'admit'), mock.patch.object(capabilities, 'reuse', return_value=None), \
             mock.patch('dcc_harness.recipes.require_qualified', return_value={'recipe': {'coverage': {'reads': ['geometry', 'materials'], 'writes': [], 'dependencies': []}}}), \
             mock.patch.object(execution, 'run_worker', side_effect=self.capability_worker):
            return execution.execute_operation(self.root, request)

    def test_capability_verification_failure_blocks_checkpoint_publication(self):
        request = self.capability_request(); real = self.capability_worker
        def corrupt(*args, **kwargs):
            if args[3] == 'capability-verify':
                write_json(args[1] / 'capability-verified.json', {'passed': False})
            else:
                real(*args, **kwargs)
        with mock.patch.object(self, 'capability_worker', side_effect=corrupt):
            result = self.run_capability(request)
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_capability_policy_change_under_publication_lock_refuses_commit(self):
        request = self.capability_request(); real = workflow.finish_edit
        def changed(*args, **kwargs):
            with mock.patch.object(capabilities, 'requirements', return_value=[]):
                return real(*args, **kwargs)
        with mock.patch.object(workflow, 'finish_edit', side_effect=changed):
            result = self.run_capability(request)
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)

    def test_capability_receipt_persistence_recovers_without_duplicate_publication(self):
        request = self.capability_request()
        with mock.patch.object(capabilities, 'record_operation', side_effect=RuntimeError('interrupted receipt persistence')):
            result = self.run_capability(request)
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)
        with mock.patch.object(execution, 'run_worker', side_effect=AssertionError('never redispatch')):
            recovered = execution.reconcile(self.root, request['operation_id'], accept=True, reason='Recover committed receipt')
        folder = self.root / 'execution/operations' / request['operation_id']
        self.assertEqual(recovered['capability_receipt']['sha256'], file_hash(folder / 'capability-receipt.json'))
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)

    def test_managed_saved_revision_requires_explicit_stage_then_retains_review(self):
        from dcc_harness import revisions
        manifest = self.manifest(); manifest['stages'][0]['review'] = 'artist_required'
        self.bind(manifest); execution.create(self.root, 'autonomous')
        checkpoint, observation = self.candidate()
        preview = revisions.preview_revision(self.root, self.packet['active']['id'], checkpoint, observation,
            self.contract, self.handoff, {}, 'artist-revision', 'Saved artist adjustment', self.base / 'revision-preview')
        with self.assertRaisesRegex(ValueError, 'stage'):
            revisions.accept_revision(self.root, preview['preview'], preview['preview_sha256'], 'Reviewed')
        result = revisions.accept_revision(self.root, preview['preview'], preview['preview_sha256'], 'Reviewed', stage='direction')
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(result['artistic_acceptance'], 'caller_review_recorded_not_authenticated')
        self.assertNotEqual(execution.status(self.root)['stages'][0]['state'], 'complete')

    def saved_revision(self):
        from dcc_harness import revisions
        checkpoint, observation = self.candidate()
        return revisions.preview_revision(self.root, self.packet['active']['id'], checkpoint, observation,
            self.contract, self.handoff, {}, 'saved-revision', 'Saved adjustment', self.base / 'revision-preview')

    def test_saved_revision_invalidates_pending_stage_review_and_counts_budget(self):
        from dcc_harness import revisions
        self.managed(max_operations=1)
        execution.submit(self.root, self.submission(), self.base)  # Completed stages require explicit reopen.
        self.apply('stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': 'direction',
                                  'reason': 'Accept revised direction', 'authority': self.actor()})
        self.submit()
        preview = self.saved_revision()
        args = (self.root, preview['preview'], preview['preview_sha256'], 'Reviewed saved evidence')
        self.assertEqual(revisions.accept_revision(*args, stage='direction')['status'], 'PUBLISHED')
        self.assertEqual(execution.status(self.root)['stages'][0]['state'], 'needs_review')
        self.assertEqual(revisions.accept_revision(*args, stage='direction')['status'], 'ALREADY_PUBLISHED')
        self.assertEqual(len(execution.status(self.root)['operations']), 1)
        with self.assertRaisesRegex(RuntimeError, 'budget'):
            self.execute()

    def test_saved_revision_cancel_and_live_backend_refuse_before_import(self):
        from dcc_harness import revisions
        self.managed(); preview = self.saved_revision(); execution.cancel(self.root)
        args = (self.root, preview['preview'], preview['preview_sha256'], 'Reviewed')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            revisions.accept_revision(*args, stage='direction')
        config = execution.configuration(self.root)
        with mock.patch.object(execution, 'configuration', return_value={**config, 'backend': 'live'}):
            with self.assertRaisesRegex(ValueError, 'live refresh/recovery'):
                revisions.accept_revision(*args, stage='direction')

    def test_saved_revision_lost_ack_recovers_without_new_checkpoint(self):
        from dcc_harness import revisions
        self.managed(); preview = self.saved_revision(); real = revisions._accept_revision
        def lost(*args, **kwargs):
            real(*args, **kwargs)
            raise RuntimeError('lost acknowledgement')
        args = (self.root, preview['preview'], preview['preview_sha256'], 'Reviewed')
        with mock.patch.object(revisions, '_accept_revision', side_effect=lost):
            with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
                revisions.accept_revision(*args, stage='direction')
        self.assertEqual(execution.status(self.root)['status'], 'NEEDS_RECONCILIATION')
        operation_id = execution.status(self.root)['operations'][0]['operation_id']
        with self.assertRaisesRegex(RuntimeError, 'already published'):
            execution.reconcile(self.root, operation_id, accept=False, reason='Cannot reject a committed import')
        result = revisions.accept_revision(*args, stage='direction')
        self.assertEqual(result['status'], 'ALREADY_PUBLISHED')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)

    def test_cancelled_saved_revision_before_publication_can_be_rejected(self):
        from dcc_harness import revisions
        self.managed(); preview = self.saved_revision(); real = revisions._accept_revision
        def cancelled(*args, **kwargs):
            execution.cancel(self.root)
            return real(*args, **kwargs)
        with mock.patch.object(revisions, '_accept_revision', side_effect=cancelled):
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                revisions.accept_revision(self.root, preview['preview'], preview['preview_sha256'], 'Reviewed', stage='direction')
        operation_id = execution.status(self.root)['operations'][0]['operation_id']
        result = execution.reconcile(self.root, operation_id, accept=False, reason='No checkpoint committed; discard import')
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(execution.status(self.root)['status'], 'CANCELLED')


class ReviewMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_nonzero_structured_cli_outcome_is_returned(self):
        from dcc_harness.mcp_server import run_cli
        with tempfile.TemporaryDirectory() as tmp:
            actual = asyncio.create_subprocess_exec
            async def child(*args, **kwargs):
                return await actual(getattr(sys, '_base_executable', sys.executable), '-c',
                    'import json; print(json.dumps({"passed": False, "failures": ["fixture failure"]})); raise SystemExit(1)', **kwargs)
            with mock.patch('asyncio.create_subprocess_exec', side_effect=child):
                result = await run_cli(['workflow-template'], Path(tmp))
            self.assertEqual(result['exit_code'], 1)
            self.assertEqual(result['result']['failures'], ['fixture failure'])

    async def test_capability_bind_missing_keys_is_validated_before_owner_lookup(self):
        from dcc_harness.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'; write_json(path, {})
            with mock.patch.object(sys, 'argv', ['dcc-harness', 'capability-bind', '--request', str(path)]):
                with self.assertRaises(ValueError):
                    main()


class ReviewRulesTests(unittest.TestCase):
    def test_interrupted_rules_export_retries_same_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); request = str(uuid.uuid4()); target = root / '.harness-mcp/rules' / request
            target.mkdir(parents=True); (target / 'partial').write_text('interrupted export')
            # Binding itself is out of scope here; prove retry reaches it with a complete verified export.
            with mock.patch('dcc_harness.workflow.resume', return_value={'active': {'id': 'a'*64, 'checkpoint_sha256': 'b'*64}}), mock.patch.object(ew, 'apply', return_value={'status': 'COMMITTED'}):
                self.assertEqual(bootstrap.bind_rules('state', root, 'none', request)['status'], 'COMMITTED')
                self.assertEqual(bootstrap.bind_rules('state', root, 'none', request)['status'], 'COMMITTED')
            self.assertEqual(distribution.verify_rules(target), distribution.catalog())

    def test_truncated_rules_index_is_preserved_and_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / 'rules'
            target.mkdir(); (target / 'index.json').write_text('{')
            bootstrap._bound_rules(target)
            self.assertEqual(distribution.verify_rules(target), distribution.catalog())
            preserved = list(root.glob('rules-incomplete-*'))
            self.assertEqual(len(preserved), 1)
            self.assertEqual((preserved[0] / 'index.json').read_text(), '{')
