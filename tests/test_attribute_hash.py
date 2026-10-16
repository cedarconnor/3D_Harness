"""P15: the authored attribute hash is compared only when both observations measured it."""
import copy
import unittest

from dcc_harness.continuity_checks import evaluate_stage, validate_contract
from dcc_harness.evidence import compare
from dcc_harness.uv_guard import evaluated_uv_noise_only

from test_continuity_checks import contract, observation, resign

COVERAGE = {"version": 1, "excluded": ["position", "material_index", "UV maps"]}


def measured(attribute_hash="attributes-1"):
    obs = observation()
    obs["coverage"]["source_attributes"] = copy.deepcopy(COVERAGE)
    obs["objects"]["ext.table.top"]["source_attribute_hash"] = attribute_hash
    return resign(obs)


class AttributeHashTests(unittest.TestCase):
    def test_a_changed_attribute_hash_fails_a_protected_mesh(self):
        result = evaluate_stage(measured(), measured("attributes-2"), contract())
        self.assertFalse(result["passed"])
        changed = [c for c in result["preservation"]["changes"] if not c["allowed"]]
        self.assertEqual([(c["id"], c["field"]) for c in changed], [("ext.table.top", "source_attribute_hash")])

    def test_an_unchanged_attribute_hash_passes(self):
        self.assertTrue(evaluate_stage(measured(), measured(), contract())["passed"])

    def test_an_observation_without_the_measurement_skips_it(self):
        for before, after in ((observation(), measured()), (measured(), observation())):
            delta = compare(before, after)
            self.assertTrue(delta["coverage_matches"])
            self.assertEqual(delta["changes"], [])
            self.assertTrue(delta["passed"])
            self.assertTrue(evaluate_stage(before, after, contract())["passed"])

    def test_a_measured_observation_must_carry_the_hash_on_every_mesh(self):
        after = measured()
        del after["objects"]["ext.table.top"]["source_attribute_hash"]
        result = evaluate_stage(measured(), resign(after), contract())
        self.assertFalse(result["passed"])
        self.assertIn("After mesh coverage missing: ext.table.top", result["failures"])

    def test_different_measurement_versions_do_not_match(self):
        after = measured()
        after["coverage"]["source_attributes"]["version"] = 2
        self.assertFalse(compare(measured(), resign(after))["coverage_matches"])

    def test_permitting_the_authored_mesh_permits_its_attributes(self):
        before, after = measured(), measured("attributes-2")
        after["objects"]["ext.table.top"]["source_mesh_hash"] = "edited"
        c = contract()
        c["allowed_object_prefixes"] = {"ext.table.": ["source_mesh_hash"]}
        self.assertTrue(evaluate_stage(before, resign(after), c)["passed"])

    def test_the_attribute_hash_can_be_permitted_alone(self):
        c = contract()
        c["allowed_object_prefixes"] = {"ext.table.": ["source_attribute_hash"]}
        validate_contract(c)
        self.assertTrue(evaluate_stage(measured(), measured("attributes-2"), c)["passed"])
        after = measured("attributes-2")
        after["objects"]["ext.table.top"]["source_mesh_hash"] = "edited"
        self.assertFalse(evaluate_stage(measured(), resign(after), c)["passed"])

    def test_uv_noise_needs_identical_attributes(self):
        before, after = measured()["objects"]["ext.table.top"], measured()["objects"]["ext.table.top"]
        self.assertTrue(evaluated_uv_noise_only(before, after))
        after["source_attribute_hash"] = "attributes-2"
        self.assertFalse(evaluated_uv_noise_only(before, after))
        del after["source_attribute_hash"]
        self.assertTrue(evaluated_uv_noise_only(before, after))


if __name__ == "__main__":
    unittest.main()
