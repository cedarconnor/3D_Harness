import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dcc_harness.evidence import digest, file_hash, write_json
from dcc_harness.quality import audit, reserved_space, select
from test_continuity_checks import observation, contract, resign


def reservation():
    return [{"id": "plaque", "bounds": [[-.25, -.15, .95], [.25, .15, 1.1]],
             "obstacle_prefixes": ["ext.table."], "exempt_ids": [], "tolerance": 1e-6}]


class ReservedSpaceTests(unittest.TestCase):
    def test_conflict_needs_scope_decision(self):
        result = reserved_space(observation(), reservation())
        self.assertFalse(result["passed"])
        self.assertEqual(result["findings"][0]["resolution"], "requires_scope_decision")

    def test_editable_is_not_exempt(self):
        result = reserved_space(observation(), reservation(), ["ext.table."])
        self.assertFalse(result["passed"])
        self.assertEqual(result["findings"][0]["resolution"], "within_edit_scope")

    def test_touching_allowed_and_clearance_passes(self):
        rules = reservation()
        for z in (1, 2):
            rules[0]["bounds"] = [[-.25, -.15, z], [.25, .15, z + .1]]
            self.assertTrue(reserved_space(observation(), rules)["passed"])

    def test_missing_obstacles_and_bounds_fail(self):
        rules = reservation()
        rules[0]["obstacle_prefixes"] = ["missing"]
        self.assertFalse(reserved_space(observation(), rules)["passed"])
        obs = observation()
        del obs["objects"]["ext.table.top"]["bounds"]
        self.assertFalse(reserved_space(resign(obs), reservation())["passed"])

    def test_invalid_rules_rejected(self):
        for edit in ({"tolerance": float("nan")}, {"bounds": [[1, 0, 0], [0, 1, 1]]},
                     {"obstacle_prefixes": []}, {"exempt_ids": ["missing"]}, {"allow_collision": True}):
            rules = reservation(); rules[0].update(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                reserved_space(observation(), rules)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "round.json"
        (self.root / "scene.blend").write_bytes(b"fixture only; not a native validation")
        (self.root / "image.png").write_bytes(b"fixture only; not a visual validation")
        obs = observation()
        obs["scene"]["world"] = None
        obs["coverage"]["measured"] = ["fixture objects"]
        obs.update(checkpoint_sha256=file_hash(self.root / "scene.blend"), native_dirty=False)
        write_json(self.root / "obs.json", resign(obs))
        views = [{"id": key, "purpose": key, "camera": {"id": key}, "render": {"samples": 32}}
                 for key in ("whole", "detail")]
        write_json(self.root / "renders.json", {"schema": "dcc.quality.renders.v1",
                   "checkpoint_sha256": obs["checkpoint_sha256"], "views_digest": digest(views),
                   "images": {key: self.ref("image.png") for key in ("whole", "detail")}})
        self.spec = {"schema": "dcc.quality.round.v1", "brief": "Keep construction coherent",
                     "methods": {"timber": "Reuse shared surface"},
                     "references": [{"id": "ref", "file": self.ref("image.png"), "role": "mood", "intent": "Palette"}],
                     "targets": [{"id": "layout", "intent": "Clear focal point", "reference_ids": ["ref"]}],
                     "views": views, "contract": contract(), "reservations": [],
                     "candidates": [{"id": key, "checkpoint": self.ref("scene.blend"),
                                     "observation": self.ref("obs.json"), "renders": self.ref("renders.json")}
                                    for key in ("unchanged", "edit")]}
        self.save()

    def ref(self, name):
        return {"path": name, "sha256": file_hash(self.root / name)}

    def save(self):
        # Fixtures intentionally rewritten; production CLI evidence writes use x.
        import json
        design = {k: v for k, v in self.spec.items() if k not in ("schema", "design", "candidates")}
        (self.root / "design.json").write_text(json.dumps(design), encoding="utf-8")
        self.spec["design"] = self.ref("design.json")
        self.path.write_text(json.dumps(self.spec), encoding="utf-8")

    def review(self):
        return {"schema": "dcc.quality.review.v1", "evidence_id": audit(self.path)["evidence_id"],
                "critic": {"author": "critic", "findings": [{"candidate": "unchanged", "target": "layout",
                           "view": "whole", "problem": "Rigid row", "remedy": "Group two pots"}]},
                "verifier": {"author": "verifier", "assessments": {key: {"layout": {
                    "result": "unchanged", "view": "whole", "evidence": "Both retain same arrangement"}}
                    for key in ("unchanged", "edit")}, "unresolved_blockers": []},
                "selected": "unchanged", "reasons": {"unchanged": "No demonstrated gain", "edit": "No visible change"}}

    def test_no_change_can_win_without_artist_acceptance(self):
        result = select(self.path, self.review())
        self.assertEqual(result["selected"], "unchanged")
        self.assertEqual(result["artist_acceptance"], "not_requested")
        self.assertEqual(result["native_adoption"], "not_performed")

    def test_changed_image_native_observation_or_receipt_rejected(self):
        for name in ("image.png", "scene.blend", "obs.json", "renders.json"):
            path = self.root / name; original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(name=name), self.assertRaises(ValueError):
                audit(self.path)
            path.write_bytes(original)

    def test_stale_review_rejected(self):
        review = self.review()
        self.spec["brief"] += " and new intent"; self.save()
        with self.assertRaises(ValueError):
            select(self.path, review)

    def test_changed_observation_loader_invalidates_review(self):
        review = self.review()
        for module in ("continuity.py", "observation_storage.py"):
            def changed_hash(path):
                return "0" * 64 if Path(path).name == module else file_hash(path)
            with self.subTest(module=module), patch("dcc_harness.quality.file_hash", changed_hash):
                self.assertNotEqual(audit(self.path)["evidence_id"], review["evidence_id"])
                with self.assertRaises(ValueError):
                    select(self.path, review)
        self.assertEqual(select(self.path, review)["selected"], "unchanged")

    def test_camera_change_requires_new_render_receipt(self):
        self.spec["views"][0]["camera"]["lens"] = 80; self.save()
        with self.assertRaises(ValueError):
            audit(self.path)

    def test_round_cannot_silently_replace_retained_intent(self):
        import json
        self.spec["brief"] = "Different after-the-fact goal"
        self.path.write_text(json.dumps(self.spec), encoding="utf-8")
        with self.assertRaises(ValueError):
            audit(self.path)

    def test_failed_native_gate_cannot_win(self):
        self.spec["contract"]["spec"]["required"]["missing"] = {"type": "MESH"}; self.save()
        self.assertFalse(audit(self.path)["passed"])
        with self.assertRaises(ValueError):
            select(self.path, self.review())

    def test_failed_alternative_retained_while_unchanged_can_win(self):
        import json
        obs = json.loads((self.root / "obs.json").read_text())
        obs["objects"]["ext.table.top"]["dimensions"] = [8, 1, 1]
        write_json(self.root / "failed.json", resign(obs))
        self.spec["candidates"][1]["observation"] = self.ref("failed.json"); self.save()
        result = select(self.path, self.review())
        self.assertFalse(result["audit"]["candidates"]["edit"]["eligible"])
        self.assertEqual(result["selected"], "unchanged")

    def test_rehashed_but_wrong_native_binding_or_dirty_observation_rejected(self):
        import json
        old = json.loads((self.root / "obs.json").read_text())
        for changes in ({"native_dirty": True}, {"checkpoint_sha256": "0" * 64}):
            obj = {**old, **changes}
            (self.root / "obs.json").write_text(json.dumps(obj), encoding="utf-8")
            for candidate in self.spec["candidates"]:
                candidate["observation"] = self.ref("obs.json")
            self.save()
            with self.assertRaises(ValueError):
                audit(self.path)

    def test_bad_review_coverage_and_unresolved_blockers_rejected(self):
        baseline = self.review()
        variants = [copy.deepcopy(baseline) for _ in range(3)]
        del variants[0]["verifier"]["assessments"]["unchanged"]
        variants[1]["verifier"]["unresolved_blockers"] = ["plaque blocked"]
        variants[2]["critic"]["findings"][0]["view"] = "missing"
        for value in variants:
            with self.assertRaises(ValueError):
                select(self.path, value)

    def test_single_reviewer_is_disclosed(self):
        review = self.review(); review["verifier"]["author"] = "critic"
        self.assertEqual(select(self.path, review)["review_independence"], "same_author")

    def test_paths_cannot_escape_round(self):
        self.spec["references"][0]["file"]["path"] = "../outside.png"; self.save()
        with self.assertRaises(ValueError):
            audit(self.path)

    def test_missing_reference_or_unchanged_rejected(self):
        self.spec["targets"][0]["reference_ids"] = ["unknown"]; self.save()
        with self.assertRaises(ValueError):
            audit(self.path)
        self.spec["targets"][0]["reference_ids"] = ["ref"]
        self.spec["candidates"][0]["id"] = "other"; self.save()
        with self.assertRaises(ValueError):
            audit(self.path)

    def spatial_round(self):
        import json
        obs = json.loads((self.root / 'obs.json').read_text())
        obs['objects']['camera'] = {'name':'Camera','type':'CAMERA','asset_id':None,'material_ids':[]}
        resign(obs)
        (self.root / 'obs.json').write_text(json.dumps(obs), encoding='utf-8')
        query = {'camera_id':'camera','target_ids':['ext.table.top'],'grid':64}
        self.spec['schema'] = 'dcc.quality.round.v2'
        self.spec['visibility_contract'] = {'schema':'dcc.visibility.contract.v1','requirements':{
            'subject':{'query':query,'minimum_visible_fraction':.75,'minimum_target_samples':100}}}
        for candidate in self.spec['candidates']:
            candidate['observation'] = self.ref('obs.json')
            # No blocking meshes in this synthetic packet: every sampled hit is clear.
            report = {'schema':'dcc.visibility.v1','checkpoint_sha256':obs['checkpoint_sha256'],
                'revision':obs['revision'],'native_dirty':False,'queries':{'subject':{**query,
                'target_samples':1000,'visible_samples':1000,'visible_fraction':1.0,'blockers':{}}}}
            name = candidate['id']+'-visibility.json'
            write_json(self.root/name,report); candidate['visibility'] = self.ref(name)
        self.save()

    def test_v2_visibility_admission_and_missing_receipt_rejection(self):
        self.spatial_round()
        self.assertTrue(audit(self.path)['passed'])
        self.spec['visibility_contract']['requirements']['subject']['minimum_target_samples'] = 1001
        self.save()
        self.assertFalse(audit(self.path)['candidates']['edit']['eligible'])
        with self.assertRaises(ValueError):
            select(self.path,self.review())
        del self.spec['candidates'][1]['visibility']; self.save()
        with self.assertRaises(ValueError):
            audit(self.path)

    def test_v2_stale_visibility_binding_rejected_even_after_file_rehash(self):
        import json
        self.spatial_round()
        path = self.root/'edit-visibility.json'
        report = json.loads(path.read_text()); report['revision'] = 'wrong'
        path.write_text(json.dumps(report),encoding='utf-8')
        self.spec['candidates'][1]['visibility'] = self.ref(path.name); self.save()
        with self.assertRaises(ValueError):
            audit(self.path)
if __name__ == "__main__":
    unittest.main()
