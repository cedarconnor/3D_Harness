import copy
import unittest

from dcc_harness.spatial import check_visibility
from dcc_harness.continuity_checks import evaluate_stage, validate_contract
from test_continuity_checks import observation, contract, resign


class VisibilityChecks(unittest.TestCase):
    def setUp(self):
        self.obs = {'checkpoint_sha256': 'native', 'revision': 'rev', 'objects': {
            'camera': {'type': 'CAMERA'}, 'target': {'type': 'MESH'}, 'blocker': {'type': 'MESH'}}}
        self.query = {'camera_id': 'camera', 'target_ids': ['target'], 'grid': 64}
        self.report = {'schema': 'dcc.visibility.v1', 'checkpoint_sha256': 'native', 'revision': 'rev',
            'native_dirty': False, 'queries': {'visible': {**self.query, 'target_samples': 1000,
            'visible_samples': 600, 'visible_fraction': .6, 'blockers': {'blocker': 400}}}}
        self.contract = {'schema': 'dcc.visibility.contract.v1', 'requirements': {
            'visible': {'query': self.query, 'minimum_visible_fraction': .6, 'minimum_target_samples': 500}}}

    def test_exact_boundary_passes_and_below_fails(self):
        self.assertTrue(check_visibility(self.report, self.contract, self.obs)['passed'])
        self.contract['requirements']['visible']['minimum_visible_fraction'] = .601
        self.assertFalse(check_visibility(self.report, self.contract, self.obs)['passed'])

    def test_missing_sample_coverage_is_not_green(self):
        self.contract['requirements']['visible']['minimum_target_samples'] = 1001
        self.assertFalse(check_visibility(self.report, self.contract, self.obs)['passed'])

    def test_wrong_checkpoint_revision_camera_or_query_rejected(self):
        variants = [{'checkpoint_sha256': 'wrong'}, {'revision': 'wrong'}, {'native_dirty': True}, {'queries': {}}]
        for edit in variants:
            with self.assertRaises(ValueError):
                check_visibility({**self.report, **edit}, self.contract, self.obs)
        for edit in ({'grid': 32}, {'target_ids': ['blocker']}, {'camera_id': 'other'}):
            report = copy.deepcopy(self.report); report['queries']['visible'].update(edit)
            with self.assertRaises(ValueError):
                check_visibility(report, self.contract, self.obs)

    def test_forged_fraction_and_counts_rejected(self):
        for edit in ({'visible_fraction': .9}, {'visible_samples': 1001}, {'target_samples': True},
                     {'blockers': {}}, {'blockers': {'missing': 400}}, {'visible_samples': -1}):
            report = copy.deepcopy(self.report); report['queries']['visible'].update(edit)
            with self.assertRaises(ValueError):
                check_visibility(report, self.contract, self.obs)

    def test_invalid_contract_rejected(self):
        for edit in ({'minimum_visible_fraction': float('nan')}, {'minimum_visible_fraction': 1.1},
                     {'minimum_target_samples': 0}, {'minimum_target_samples': True}, {'unknown': 1}):
            contract = copy.deepcopy(self.contract); contract['requirements']['visible'].update(edit)
            with self.assertRaises(ValueError):
                check_visibility(self.report, contract, self.obs)


class ExactDeletionTests(unittest.TestCase):
    def setUp(self):
        self.before = observation()
        self.before['objects']['ext.removable'] = copy.deepcopy(self.before['objects']['ext.table.top'])
        resign(self.before)
        self.after = copy.deepcopy(self.before); del self.after['objects']['ext.removable']; resign(self.after)

    def test_exact_deletion_allowed_and_other_objects_protected(self):
        c = contract(); c['allowed_deleted_ids'] = ['ext.removable']
        self.assertTrue(evaluate_stage(self.before, self.after, c)['passed'])
        self.assertFalse(evaluate_stage(self.before, self.after, contract())['passed'])
        c['allowed_deleted_ids'] = ['ext.missing']
        self.assertFalse(evaluate_stage(self.before, self.after, c)['passed'])

    def test_contradictory_required_and_deleted_ids_rejected(self):
        c = contract(); c['allowed_deleted_ids'] = ['ext.table.top']
        with self.assertRaises(ValueError):
            validate_contract(c)

    def test_deletion_cannot_be_a_prefix_permission(self):
        c = contract(); c['allowed_deleted_ids'] = ['ext.']
        self.assertFalse(evaluate_stage(self.before, self.after, c)['passed'])


if __name__ == '__main__': unittest.main()
