"""Publication races and recovery must preserve the live scene's separate state."""
import copy
from pathlib import Path
import uuid
import unittest
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import execution, workflow
from dcc_harness.evidence import file_hash, write_json


class LivePublicationTests(Fixture):
    def request(self):
        return {'schema': 'dcc.execution.operation.v2', 'backend': 'live',
                'operation_id': str(uuid.uuid4()), 'stage': 'direction', 'script': str(self.script),
                'contract': str(self.contract), 'handoff': str(self.handoff), 'blender': 'fixture',
                'expected_parent': self.packet['active']['id'], 'timeout': 30,
                'live': {'recipe': 'object.transform', 'target': 'fixture', 'parameters': {'location': [1, 0, 0]}}}

    def backend(self, before=False, after=False, lost=False):
        fixture = self
        class Fake:
            dispatches = 0
            def prepare(self, request):
                self.request = request
                return {'operation_id': request['operation_id']}
            def submit(self, request, prepared):
                self.dispatches += 1
                Path(request['output']).write_bytes(b'live changed')
                if lost:
                    raise ConnectionError('lost response after mutation')
                return request['operation_id']
            def status(self, operation_id):
                return {'operation_id': operation_id, 'state': 'SAVED', 'candidate': self.request['output'],
                        'sha256': file_hash(self.request['output'])}
            def verify(self, receipt):
                obs = copy.deepcopy(fixture.obs)
                obs['checkpoint_sha256'] = receipt['sha256']
                write_json(Path(receipt['candidate']).parent / 'observation.json', obs)
            def before_publish(self, receipt):
                if before:
                    raise ValueError('LIVE_DIVERGED before publication')
            def published(self, result, receipt):
                return {'live_state': 'LIVE_DIVERGED' if after else 'READY'}
            def cancel(self, operation_id):
                return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED'}
        return Fake()

    def start(self):
        self.bind(); execution.create(self.root, 'autonomous', backend='live')
        patch = mock.patch('dcc_harness.live.ensure_aligned', return_value={'state': 'READY'})
        patch.start(); self.addCleanup(patch.stop)

    def test_next_operation_refuses_divergence_before_reservation(self):
        self.start()
        with mock.patch('dcc_harness.live.ensure_aligned', side_effect=ValueError('LIVE_DIVERGED')):
            with self.assertRaisesRegex(ValueError, 'LIVE_DIVERGED'):
                execution.execute_operation(self.root, self.request())
        self.assertFalse((self.root / 'execution/operations').exists())

    def test_edit_during_verification_blocks_publication(self):
        self.start(); request = self.request(); backend = self.backend(before=True)
        with mock.patch('dcc_harness.execution.make_backend', return_value=backend):
            result = execution.execute_operation(self.root, request)
        self.assertEqual(result['status'], 'NEEDS_RECONCILIATION')
        self.assertIn('LIVE_DIVERGED', result.get('reason', ''))
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 1)
        self.assertTrue((self.root / 'execution/operations' / request['operation_id'] / 'candidate.blend').exists())

    def test_post_publication_race_preserves_saved_checkpoint_and_reports_divergence(self):
        self.start(); request = self.request(); backend = self.backend(after=True)
        with mock.patch('dcc_harness.execution.make_backend', return_value=backend):
            result = execution.execute_operation(self.root, request)
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(result['live_state'], 'LIVE_DIVERGED')
        self.assertEqual(len(workflow.Continuity(self.root).status()['task_history']), 2)

    def test_lost_reply_is_status_only(self):
        self.start(); request = self.request(); backend = self.backend(lost=True)
        with mock.patch('dcc_harness.execution.make_backend', return_value=backend):
            first = execution.execute_operation(self.root, request)
            second = execution.execute_operation(self.root, request)
        self.assertEqual(first['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(second['status'], 'NEEDS_RECONCILIATION')
        self.assertEqual(backend.dispatches, 1)

    def test_background_recovery_cannot_assume_live_scene_is_unchanged(self):
        self.start(); request = self.request(); backend = self.backend(lost=True)
        with mock.patch('dcc_harness.execution.make_backend', return_value=backend):
            execution.execute_operation(self.root, request)
        with self.assertRaisesRegex(ValueError, 'live'):
            execution.reconcile(self.root, request['operation_id'], accept=False, reason='Unknown mutation')


class LiveGateTests(Fixture):
    def test_direct_stage_submission_also_checks_live_alignment(self):
        self.bind(); execution.create(self.root, 'autonomous', backend='live')
        payload = {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': self.cp(),
                   'deliverables': {'brief': 'Within brief'},
                   'evidence': [{'kind': 'direction_record', 'file': self.ref(self.handoff)}],
                   'feedback_ids': [], 'note': 'Ready'}
        with mock.patch('dcc_harness.live.ensure_aligned', side_effect=ValueError('LIVE_DIVERGED')):
            with self.assertRaisesRegex(ValueError, 'LIVE_DIVERGED'):
                self.apply('stage.submit', payload)

    def test_owner_completion_cannot_override_changed_live_scene(self):
        self.bind(); execution.create(self.root, 'approval_gated', backend='live')
        with mock.patch('dcc_harness.live.ensure_aligned', return_value={'state': 'READY'}):
            submission = self.submit()
        with mock.patch('dcc_harness.live.ensure_aligned', side_effect=ValueError('LIVE_DIVERGED')):
            with self.assertRaisesRegex(ValueError, 'LIVE_DIVERGED'):
                self.complete(submission, owner=True, reviewer=self.actor('artist'))


class RecipeAdmissionTests(unittest.TestCase):
    def validate(self, value):
        from dcc_harness import live_contracts
        self.assertTrue(callable(getattr(live_contracts, 'validate_live_recipe', None)), 'Live recipe validator missing')
        return live_contracts.validate_live_recipe(value)

    def test_unknown_operator_and_code_are_not_recipes(self):
        for value in ({'recipe': 'execute_code', 'code': 'pass'},
                      {'recipe': 'bpy.ops.object.delete', 'target': 'x', 'parameters': {}}):
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_transform_requires_finite_explicit_values(self):
        for bad in ([1, 2], [1, 2, float('nan')], ['x', 2, 3], [True, 2, 3]):
            with self.assertRaises(ValueError):
                self.validate({'recipe': 'object.transform', 'target': 'object.example', 'parameters': {'location': bad}})

    def test_supported_transform_is_retained_exactly(self):
        value = {'recipe': 'object.transform', 'target': 'object.example', 'parameters': {'location': [1, 2, 3]}}
        self.assertEqual(self.validate(value), value)

    def test_modifier_only_accepts_qualified_properties(self):
        with self.assertRaises(ValueError):
            self.validate({'recipe': 'modifier.settings', 'target': 'object.example',
                           'parameters': {'name': 'Bevel', 'type': 'BEVEL', 'settings': {'anything': 2}}})

    def test_material_requires_explicit_shared_user_scope(self):
        with self.assertRaises(ValueError):
            self.validate({'recipe': 'material.input', 'target': 'object.example',
                           'parameters': {'material_id': 'material.x', 'node': 'Principled BSDF',
                                          'socket': 'Roughness', 'value': 0.2}})
