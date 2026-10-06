import copy
import unittest

from dcc_harness.continuity_checks import evaluate_stage, validate_contract
from dcc_harness.evidence import digest


def resign(obs):
    obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
    return obs


def observation():
    mesh = {
        "name": "Table", "type": "MESH", "asset_id": "table", "matrix_world": [[1, 0], [0, 1]],
        "material_ids": ["stone"], "vertices": 8, "triangles": 12,
        "geometry_hash": "evaluated-geometry", "source_mesh_hash": "authored-geometry",
        "source_uv_hash": "authored-uv", "uv_hash": "evaluated-uv", "uv_layers": ["UVMap"],
        "evaluated_uv_values": {"UVMap": [0.0, 0.5, 1.0, 1.0]}, "modifier_settings": [],
        "mesh_datablock": {"name": "TableMesh", "library": None, "type": "Mesh"},
        "bounds": [[-1, -.5, 0], [1, .5, 1]], "dimensions": [2, 1, 1],
    }
    obs = {
        "schema": "dcc.observation.v1", "objects": {"ext.table.top": mesh},
        "materials": {"stone": {"name": "Stone", "diffuse_color": [.5, .5, .5, 1], "graph": {
            "nodes": [{"name": "Principled BSDF", "type": "ShaderNodeBsdfPrincipled",
                       "inputs": {"Base Color": [.5, .5, .5, 1], "Roughness": .4}},
                      {"name": "Material Output", "inputs": {}}],
            "links": [["Principled BSDF", "BSDF", "Material Output", "Surface"]]}}},
        "scene": {"units": {"system": "METRIC", "scale_length": 1}, "world": "fixed",
                  "render": {"samples": 32}, "camera": "camera.hero"},
        "coverage": {"continuity_observation": 1, "not_measured": ["artistic quality"]}, "issues": [],
    }
    return resign(obs)


def contract():
    return {"schema": "dcc.continuity.contract.v1", "spec": {"schema": "dcc.spec.v1",
            "required": {"ext.table.top": {"type": "MESH", "asset_id": "table", "material_ids": ["stone"]}}}}


class ContinuityCheckTests(unittest.TestCase):
    def test_allowed_geometry_edit_only(self):
        before = observation()
        after = copy.deepcopy(before)
        after["objects"]["ext.table.top"]["dimensions"] = [2.5, 1, 1]
        c = contract()
        c["allowed_object_prefixes"] = {"ext.table.": ["dimensions"]}
        result = evaluate_stage(before, resign(after), c)
        self.assertTrue(result["passed"])
        self.assertEqual(result["revision"], after["revision"])
        self.assertEqual(result["native_runtime_validation"], "not_performed")
        after["objects"]["ext.table.top"]["matrix_world"] = [[2, 0], [0, 1]]
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])
        c["allowed_object_prefixes"]["ext.table."].append("matrix_world")
        self.assertTrue(evaluate_stage(before, resign(after), c)["passed"])

    def test_unintended_object_material_and_scene_changes_fail(self):
        before = observation()
        for mutate in (
                lambda a: a["objects"]["ext.table.top"].update(source_mesh_hash="edited"),
                lambda a: a["materials"]["stone"].update(diffuse_color=[1, 0, 0, 1]),
                lambda a: a["scene"].update(world="changed")):
            after = copy.deepcopy(before)
            mutate(after)
            self.assertFalse(evaluate_stage(before, resign(after), contract())["passed"])

    def test_old_objects_and_materials_cannot_be_deleted(self):
        before = observation()
        for category, name in (("objects", "ext.table.top"), ("materials", "stone")):
            after = copy.deepcopy(before)
            del after[category][name]
            result = evaluate_stage(before, resign(after), contract())
            self.assertFalse(result["passed"])
            self.assertFalse(result["preservation"]["passed"])

    def test_missing_cumulative_required_target_fails(self):
        before = observation()
        c = contract()
        c["spec"]["required"]["ext.previous.stage"] = {"type": "MESH"}
        self.assertIn("Missing target: ext.previous.stage", evaluate_stage(before, before, c)["failures"])

    def test_new_objects_scoped_and_new_materials_permitted(self):
        before = observation()
        after = copy.deepcopy(before)
        after["objects"]["ext.new"] = copy.deepcopy(after["objects"]["ext.table.top"])
        after["materials"]["new"] = copy.deepcopy(after["materials"]["stone"])
        self.assertTrue(evaluate_stage(before, resign(after), contract())["passed"])
        after["objects"]["outside.scope"] = after["objects"].pop("ext.new")
        self.assertFalse(evaluate_stage(before, resign(after), contract())["passed"])

    def test_new_light_rejected_even_with_allowed_creation_prefix(self):
        before = observation()
        after = copy.deepcopy(before)
        after["objects"]["ext.entry_lantern.light"] = {
            "name": "Unrequested Light", "type": "LIGHT", "asset_id": None,
            "material_ids": [], "light": {"energy": 100},
        }
        result = evaluate_stage(before, resign(after), contract())
        self.assertFalse(result["passed"])
        self.assertTrue(any("New light" in failure for failure in result["failures"]))

    def test_late_stage_creation_prefixes_reject_unrelated_geometry(self):
        before = observation()
        after = copy.deepcopy(before)
        after["objects"]["ext.entry_lantern.body"] = copy.deepcopy(after["objects"]["ext.table.top"])
        c = contract()
        c["allowed_new_prefixes"] = ["ext.entry_lantern.", "ext.sign."]
        self.assertTrue(evaluate_stage(before, resign(after), c)["passed"])
        after["objects"]["ext.unrelated"] = after["objects"].pop("ext.entry_lantern.body")
        result = evaluate_stage(before, resign(after), c)
        self.assertFalse(result["passed"])
        self.assertIn({"category": "objects", "id": "ext.unrelated", "field": "created", "allowed": False},
                      result["preservation"]["changes"])

    def test_unknown_contract_keys_rules_and_wildcards_rejected(self):
        variants = (
            {"magic_quality": True}, {"allowed_object_prefixes": {"ext.": ["*"]}},
            {"allowed_object_prefixes": {"ext.": ["deleted"]}},
            {"allowed_object_prefixes": {"ext.*": ["bounds"]}},
            {"allowed_new_prefixes": [""]}, {"allowed_new_prefixes": ["camera."]},
            {"preserve_centers": [""]}, {"exact_asset_counts": {"table": True}},
            {"sharing_groups": [["ext.table.top", "ext.table.top"]]},
            {"center_tolerance": float("nan")}, {"centers": {"ext.table.top": [0, 0]}},
        )
        for changed in variants:
            c = contract()
            c.update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_contract(c)
        c = contract()
        c["spec"]["required"]["ext.table.top"]["magic"] = 1
        with self.assertRaises(ValueError):
            evaluate_stage(observation(), observation(), c)

    def test_exact_requested_shader_input_does_not_allow_other_graph_change(self):
        before = observation()
        after = copy.deepcopy(before)
        desired = [.38, .43, .48, 1]
        c = contract()
        c["allowed_material_inputs"] = {"stone": {"Principled BSDF": {"Base Color": desired}}}
        self.assertFalse(evaluate_stage(before, after, c)["passed"])
        after["materials"]["stone"]["graph"]["nodes"][0]["inputs"]["Base Color"] = desired
        self.assertTrue(evaluate_stage(before, resign(after), c)["passed"])
        after["materials"]["stone"]["graph"]["nodes"][0]["inputs"]["Roughness"] = .2
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])
        after = copy.deepcopy(before)
        after["materials"]["stone"]["graph"]["nodes"][0]["inputs"]["Base Color"] = desired
        after["materials"]["stone"]["graph"]["links"] = []
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])

    def test_linked_or_missing_shader_inputs_fail(self):
        before = observation()
        before["materials"]["stone"]["graph"]["links"].append(["Tint", "Color", "Principled BSDF", "Base Color"])
        resign(before)
        c = contract()
        c["allowed_material_inputs"] = {"stone": {"Principled BSDF": {"Base Color": [.5, .5, .5, 1]}}}
        self.assertFalse(evaluate_stage(before, before, c)["passed"])
        c["allowed_material_inputs"] = {"stone": {"Principled BSDF": {"Unknown": 1}}}
        self.assertFalse(evaluate_stage(before, before, c)["passed"])

    def test_uv_float_noise_is_narrow_and_authored_changes_fail(self):
        before = observation()
        after = copy.deepcopy(before)
        obj = after["objects"]["ext.table.top"]
        obj["uv_hash"] = "noise"
        obj["evaluated_uv_values"]["UVMap"][0] += 1.2e-7
        result = evaluate_stage(before, resign(after), contract())
        self.assertTrue(result["passed"])
        self.assertEqual(result["evaluated_uv_noise"]["objects"], ["ext.table.top"])
        for field, value in (("source_uv_hash", "authored-edit"), ("source_mesh_hash", "source-edit"),
                             ("modifier_settings", [{"new": True}]), ("geometry_hash", "geometry-edit")):
            bad = copy.deepcopy(after)
            bad["objects"]["ext.table.top"][field] = value
            self.assertFalse(evaluate_stage(before, resign(bad), contract())["passed"])
        obj["evaluated_uv_values"]["UVMap"][0] = 2.1e-7
        self.assertFalse(evaluate_stage(before, resign(after), contract())["passed"])

    def test_centers_and_counts_enforced_beyond_allowed_geometry(self):
        before = observation()
        c = contract()
        c.update(allowed_object_prefixes={"ext.table.": ["bounds", "dimensions"]},
                 centers={"ext.table.top": [0, 0, .5]}, preserve_centers=["ext.table."],
                 exact_asset_counts={"table": 1})
        after = copy.deepcopy(before)
        after["objects"]["ext.table.top"].update(bounds=[[-1.5, -.5, 0], [1.5, .5, 1]], dimensions=[3, 1, 1])
        self.assertTrue(evaluate_stage(before, resign(after), c)["passed"])
        after["objects"]["ext.table.top"]["bounds"][1][0] += .01
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])
        after = copy.deepcopy(before)
        after["objects"]["ext.duplicate"] = copy.deepcopy(after["objects"]["ext.table.top"])
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])
        c["preserve_centers"] = ["ext.nonexistent."]
        self.assertFalse(evaluate_stage(before, before, c)["passed"])

    def test_sharing_requires_two_actual_observed_mesh_identities(self):
        before = observation()
        before["objects"]["ext.table.second"] = copy.deepcopy(before["objects"]["ext.table.top"])
        resign(before)
        c = contract()
        c["sharing_groups"] = [["ext.table.top", "ext.table.second"]]
        self.assertTrue(evaluate_stage(before, before, c)["passed"])
        after = copy.deepcopy(before)
        after["objects"]["ext.table.second"]["mesh_datablock"]["name"] = "CopiedMesh"
        self.assertFalse(evaluate_stage(before, resign(after), c)["passed"])

    def test_bad_coverage_issues_and_tampering_cannot_pass(self):
        before = observation()
        for mutate in (
                lambda a: a["coverage"].pop("continuity_observation"),
                lambda a: a["objects"]["ext.table.top"].pop("source_uv_hash"),
                lambda a: a["issues"].append("Duplicate identity")):
            after = copy.deepcopy(before)
            mutate(after)
            self.assertFalse(evaluate_stage(before, resign(after), contract())["passed"])
        after = copy.deepcopy(before)
        after["scene"]["world"] = "not-resigned"
        with self.assertRaises(ValueError):
            evaluate_stage(before, after, contract())


if __name__ == "__main__":
    unittest.main()
