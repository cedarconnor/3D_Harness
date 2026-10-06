import copy
import unittest

from dcc_harness.continuity_checks import evaluate_stage
from test_continuity_checks import observation, contract, resign


def observed(version=1):
    obs = observation()
    obs['coverage']['continuity_observation'] = version
    if version == 2:
        obs['coverage']['dimensions_measurement'] = 'world_linear_extents_v2'
    return resign(obs)


class ExtentVersionTests(unittest.TestCase):
    def test_matching_known_versions_pass(self):
        for version in (1, 2):
            obs = observed(version)
            self.assertTrue(evaluate_stage(obs, obs, contract())['passed'])

    def test_mixed_versions_fail_both_directions(self):
        for old, new in ((1, 2), (2, 1)):
            result = evaluate_stage(observed(old), observed(new), contract())
            self.assertFalse(result['passed'])
            self.assertFalse(result['preservation']['coverage_matches'])

    def test_unknown_and_malformed_versions_fail_even_when_equal(self):
        for version in (0, 3, -1, None, True, False, 1.0, 2.0, '1', '2', [], {}):
            obs = observed()
            obs['coverage']['continuity_observation'] = version
            resign(obs)
            with self.subTest(version=version):
                self.assertFalse(evaluate_stage(obs, obs, contract())['passed'])

    def test_missing_or_malformed_v2_measurement_fails(self):
        for value in (None, '', 'world_aabb', 2, True, {}, []):
            obs = observed(2)
            obs['coverage']['dimensions_measurement'] = value
            resign(obs)
            self.assertFalse(evaluate_stage(obs, obs, contract())['passed'])
        obs = observed(2)
        del obs['coverage']['dimensions_measurement']
        resign(obs)
        self.assertFalse(evaluate_stage(obs, obs, contract())['passed'])

    def test_legacy_cannot_claim_v2_measurement(self):
        obs = observed()
        obs['coverage']['dimensions_measurement'] = 'world_linear_extents_v2'
        resign(obs)
        self.assertFalse(evaluate_stage(obs, obs, contract())['passed'])

    def test_v2_has_no_dimension_tolerance_or_waiver(self):
        before = observed(2)
        after = copy.deepcopy(before)
        after['objects']['ext.table.top']['dimensions'][0] += 1e-7
        result = evaluate_stage(before, resign(after), contract())
        self.assertFalse(result['passed'])
        self.assertIn({'category': 'objects', 'id': 'ext.table.top', 'field': 'dimensions', 'allowed': False},
                      result['preservation']['changes'])


if __name__ == '__main__':
    unittest.main()
