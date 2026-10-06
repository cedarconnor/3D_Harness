"""Coordinator file tests use synthetic native bytes, not Blender qualification."""
import collections
from pathlib import Path
import shutil
import tempfile
import unittest

from dcc_harness.continuity import Continuity
from dcc_harness.continuity_trial import (HELPER_FILES, accept_stage, issue_stage,
                                         prepare_round, verify_packet)
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.project import Project


class ContinuityTrialTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / "round"
        self.native = self.base / "starter.blend"
        self.native.write_bytes(b"synthetic native fixture, not a real Blender file")
        self.observation = self.base / "observation.json"
        self.observe(self.native, self.observation)
        self.templates = self.base / "templates"
        (self.templates / "common").mkdir(parents=True)
        (self.templates / "common" / "BRIEF.md").write_text("Build a connected courtyard.", encoding="utf-8")
        write_json(self.templates / "common" / "DECISIONS.json", {"palette": "warm", "preserve": ["lighting"]})
        (self.templates / "METHOD-H.md").write_text("Use continuity checkpoints and reconcile pending operations.", encoding="utf-8")
        for stage in range(1, 5):
            (self.templates / f"stage-{stage:02d}.md").write_text(f"Perform work for stage {stage}.", encoding="utf-8")
            write_json(self.templates / f"contract-{stage:02d}.json", {"stage": stage})
        self.helper = self.base / "dcc_harness"
        self.helper.mkdir()
        for name in HELPER_FILES:
            (self.helper / name).write_text(f"# Frozen helper fixture: {name}\n", encoding="utf-8")
        for name in ("blind.py", "continuity_trial.py", "secret.py"):
            (self.helper / name).write_text("PRIVATE COORDINATOR MUST NOT BE COPIED", encoding="utf-8")

    def observe(self, native, destination):
        obs = {"schema": "dcc.observation.v1", "checkpoint_sha256": file_hash(native),
               "objects": {"bench-1": {"name": "Bench", "type": "MESH", "asset_id": "bench",
                   "parent": None, "material_ids": ["stone"], "collections": ["Courtyard"]}},
               "materials": {"stone": {"name": "Stone"}}, "scene": {}, "issues": [],
               "coverage": {"measured": ["object identities", "material bindings"],
                            "not_measured": ["artistic quality"]}}
        obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
        write_json(destination, obs)
        return destination

    def prepare(self):
        return prepare_round(self.root, self.native, self.observation, self.templates, self.helper, seed=42)

    def run_for(self, method):
        return next(r for r in self.prepare()["runs"] if r["condition"] == method)["run_id"]

    def handoff(self, run_id, stage, *, state=True):
        packet = self.root / "packets" / run_id / f"s{stage:02d}"
        output = packet / "output"
        shutil.copyfile(packet / "start.blend", output / "scene.blend")
        shutil.copyfile(packet / "input-observation.json", output / "observation.json")
        (output / "CONTINUE.md").write_text("Keep lighting. Continue from the saved native scene.", encoding="utf-8")
        write_json(output / "USAGE.json", {"elapsed_seconds": 12, "captures": 0, "tokens": None})
        if state and (packet / "state").is_dir():
            shutil.copytree(packet / "state", output / "state")
        return output

    def test_four_balanced_workflows_with_equal_frozen_common_inputs(self):
        manifest = self.prepare()
        self.assertEqual(len({r["run_id"] for r in manifest["runs"]}), 4)
        self.assertEqual(collections.Counter(r["condition"] for r in manifest["runs"]), {"A": 2, "H": 2})
        self.assertEqual([r["order"] for r in manifest["runs"]], [1, 2, 3, 4])
        for block in (1, 2):
            self.assertEqual({r["condition"] for r in manifest["runs"] if r["block"] == block}, set("AH"))
        for run in manifest["runs"]:
            packet = issue_stage(self.root, run["run_id"], 1)
            self.assertTrue(verify_packet(self.root, run["run_id"], 1)["verified"])
            self.assertEqual(file_hash(packet / "start.blend"), file_hash(self.native))
            self.assertEqual(file_hash(packet / "input-observation.json"), file_hash(self.observation))
            self.assertEqual(file_hash(packet / "common" / "DECISIONS.json"), file_hash(self.templates / "common" / "DECISIONS.json"))
            self.assertEqual((packet / "helper").exists(), run["condition"] == "H")
            self.assertEqual((packet / "state").exists(), run["condition"] == "H")
            self.assertFalse((packet / "private").exists())
            self.assertFalse((packet / "stage-02.md").exists())
            self.assertFalse(list(packet.rglob("blind.py")))
            self.assertFalse(list(packet.rglob("continuity_trial.py")))
            if run["condition"] == "H":
                self.assertEqual({p.name for p in (packet / "helper" / "dcc_harness").iterdir()}, set(HELPER_FILES))
                self.assertEqual(Continuity(packet / "state").status()["decisions"]["palette"], "warm")

    def test_frozen_input_changes_and_unlisted_files_fail_but_outputs_do_not(self):
        run_id = self.run_for("A")
        packet = issue_stage(self.root, run_id, 1)
        (packet / "output" / "diagnostic.log").write_text("mutable", encoding="utf-8")
        self.assertTrue(verify_packet(self.root, run_id, 1)["verified"])
        (packet / "extra.md").write_text("unlisted", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Frozen files changed"):
            verify_packet(self.root, run_id, 1)
        (packet / "extra.md").unlink()
        (packet / "REQUEST.md").write_text("tampered", encoding="utf-8")
        self.handoff(run_id, 1)
        with self.assertRaises(ValueError):
            accept_stage(self.root, run_id, 1)
        self.assertFalse((self.root / "private" / "accepted").exists())

    def test_sequential_packets_transfer_only_accepted_handoff(self):
        run_id = self.run_for("A")
        with self.assertRaises(ValueError):
            issue_stage(self.root, run_id, 2)
        packet = issue_stage(self.root, run_id, 1)
        output = self.handoff(run_id, 1)
        (output / "build.py").write_text("private builder script", encoding="utf-8")
        (output / "transcript.json").write_text("private chat", encoding="utf-8")
        accepted = accept_stage(self.root, run_id, 1)
        saved_hash = file_hash(accepted / "scene.blend")
        (output / "scene.blend").write_bytes(b"later modification")
        next_packet = issue_stage(self.root, run_id, 2)
        self.assertEqual(file_hash(next_packet / "start.blend"), saved_hash)
        self.assertEqual(file_hash(next_packet / "CONTINUE.md"), file_hash(accepted / "CONTINUE.md"))
        self.assertFalse((next_packet / "USAGE.json").exists())
        self.assertFalse(list(next_packet.rglob("build.py")))
        self.assertFalse(list(next_packet.rglob("transcript.json")))
        self.assertEqual(list((next_packet / "output").iterdir()), [])

    def test_duplicate_publications_and_partial_destinations_are_not_overwritten(self):
        run_id = self.run_for("A")
        issue_stage(self.root, run_id, 1)
        with self.assertRaises(FileExistsError):
            issue_stage(self.root, run_id, 1)
        self.handoff(run_id, 1)
        accept_stage(self.root, run_id, 1)
        with self.assertRaises(FileExistsError):
            accept_stage(self.root, run_id, 1)
        (self.root / "packets" / run_id / "s02").mkdir()
        with self.assertRaises(FileExistsError):
            issue_stage(self.root, run_id, 2)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_observation_checkpoint_binding_and_stage_one_are_fixed(self):
        self.native.write_bytes(b"changed after observation")
        with self.assertRaisesRegex(ValueError, "checkpoint_sha256"):
            self.prepare()
        self.assertFalse(self.root.exists())
        self.native.write_bytes(b"synthetic native fixture, not a real Blender file")
        run_id = self.run_for("A")
        with self.assertRaisesRegex(ValueError, "only at stages 3"):
            issue_stage(self.root, run_id, 1, checkpoint=self.native)
        different = self.base / "different.json"
        obs = read_json(self.observation)
        obs["note"] = "changed observation metadata"
        write_json(different, obs)
        with self.assertRaisesRegex(ValueError, "frozen initial observation"):
            issue_stage(self.root, run_id, 1, observation=different)

    def test_missing_usage_or_handoff_refuses_publication(self):
        run_id = self.run_for("A")
        packet = issue_stage(self.root, run_id, 1)
        (packet / "output" / "scene.blend").write_bytes(b"saved result")
        with self.assertRaises(ValueError):
            accept_stage(self.root, run_id, 1)
        (packet / "output" / "CONTINUE.md").write_text("next", encoding="utf-8")
        with self.assertRaises(ValueError):
            accept_stage(self.root, run_id, 1)
        self.assertFalse((self.root / "private" / "accepted").exists())

    def test_missing_agent_observation_can_be_supplied_independently(self):
        run_id = self.run_for("A")
        issue_stage(self.root, run_id, 1)
        output = self.handoff(run_id, 1)
        (output / "observation.json").unlink()
        accept_stage(self.root, run_id, 1)
        with self.assertRaises(ValueError):
            issue_stage(self.root, run_id, 2)
        packet = issue_stage(self.root, run_id, 2, observation=self.observation)
        self.assertTrue((packet / "input-observation.json").is_file())

    def test_h_state_is_copied_and_verified_without_mutating_frozen_state(self):
        run_id = self.run_for("H")
        packet = issue_stage(self.root, run_id, 1)
        self.handoff(run_id, 1)
        accepted = accept_stage(self.root, run_id, 1, observation=self.observation)
        receipt = read_json(self.root / "private" / "results" / run_id / "s01.json")
        self.assertTrue(receipt["continuity_valid"])
        self.assertEqual(receipt["observation_source"], "independent_supplied")
        for relative, sha in receipt["result_hashes"].items():
            self.assertEqual(file_hash(accepted / relative), sha)
        next_packet = issue_stage(self.root, run_id, 2)
        self.assertEqual(Continuity(next_packet / "state").status()["active"]["id"], Continuity(packet / "state").status()["active"]["id"])

    def test_invalid_h_state_is_retained_as_failure(self):
        run_id = self.run_for("H")
        issue_stage(self.root, run_id, 1)
        output = self.handoff(run_id, 1)
        (output / "state" / "project.json").write_text("invalid JSON", encoding="utf-8")
        accepted = accept_stage(self.root, run_id, 1)
        receipt = read_json(self.root / "private" / "results" / run_id / "s01.json")
        self.assertFalse(receipt["continuity_valid"])
        self.assertEqual((accepted / "state" / "project.json").read_text(encoding="utf-8"), "invalid JSON")
        # The next session still receives the failed history, never a selective retry.
        next_packet = issue_stage(self.root, run_id, 2)
        self.assertEqual((next_packet / "state" / "project.json").read_text(encoding="utf-8"), "invalid JSON")

    def test_missing_h_state_does_not_drop_native_result_or_create_new_history(self):
        run_id = self.run_for("H")
        issue_stage(self.root, run_id, 1)
        self.handoff(run_id, 1, state=False)
        accepted = accept_stage(self.root, run_id, 1)
        self.assertTrue((accepted / "scene.blend").is_file())
        receipt = read_json(self.root / "private" / "results" / run_id / "s01.json")
        self.assertFalse(receipt["continuity_valid"])
        next_packet = issue_stage(self.root, run_id, 2)
        self.assertTrue((next_packet / "STATE_UNAVAILABLE.md").is_file())
        self.assertFalse((next_packet / "state").exists())

    def test_reinitialized_h_state_cannot_claim_continuity(self):
        run_id = self.run_for("H")
        packet = issue_stage(self.root, run_id, 1)
        output = self.handoff(run_id, 1, state=False)
        Continuity(output / "state").initialize(output / "scene.blend", output / "observation.json", "replacement history", {})
        accept_stage(self.root, run_id, 1)
        receipt = read_json(self.root / "private" / "results" / run_id / "s01.json")
        self.assertFalse(receipt["continuity_valid"])
        self.assertIn("identity", receipt["continuity_error"])
        self.assertTrue(verify_packet(self.root, run_id, 1)["verified"])

    def test_injected_events_share_information_but_pending_journal_is_h_only(self):
        manifest = self.prepare()
        injected = self.base / "injected.blend"
        injected.write_bytes(b"synthetic post-operation native bytes")
        injected_obs = self.observe(injected, self.base / "injected.json")
        event = self.base / "event.md"
        event.write_text("A delivery plaque operation may already have completed. Inspect before retry.", encoding="utf-8")
        script = self.base / "operation.py"
        script.write_text("# synthetic unknown operation", encoding="utf-8")
        contract = self.base / "event-contract.json"
        write_json(contract, {"allowed": ["delivery plaque"]})
        for run in manifest["runs"]:
            run_id = run["run_id"]
            for stage in (1, 2, 3):
                issue_stage(self.root, run_id, stage)
                self.handoff(run_id, stage)
                accept_stage(self.root, run_id, stage)
            packet = issue_stage(self.root, run_id, 4, checkpoint=injected,
                observation=injected_obs, event=event, pending_script=script, event_contract=contract)
            self.assertEqual(file_hash(packet / "EVENT.md"), file_hash(event))
            self.assertEqual(file_hash(packet / "EVENT_CONTRACT.json"), file_hash(contract))
            self.assertEqual(file_hash(packet / "PENDING_OPERATION.py"), file_hash(script))
            self.assertEqual((packet / "PENDING_OPERATION.json").exists(), run["condition"] == "H")
            if run["condition"] == "H":
                pending = Project(packet / "state").pending()
                self.assertEqual(len(pending), 1)
                self.assertEqual(next(iter(pending.values()))["sha256"], file_hash(script))
            receipt = read_json(self.root / "private" / "issued" / run_id / "s04.json")
            self.assertTrue(receipt["injected_checkpoint"])
            self.assertEqual(receipt["previous_accepted_sha256"], file_hash(self.native))
            self.assertEqual(receipt["input_sha256"], file_hash(injected))
            self.assertNotEqual(receipt["input_sha256"], receipt["previous_accepted_sha256"])
            self.assertTrue(verify_packet(self.root, run_id, 4)["verified"])

    def test_injection_requires_bound_observation_and_previous_acceptance(self):
        run_id = self.run_for("A")
        with self.assertRaisesRegex(ValueError, "requires its observation"):
            issue_stage(self.root, run_id, 3, checkpoint=self.native)
        with self.assertRaisesRegex(ValueError, "only at stage 4"):
            issue_stage(self.root, run_id, 2, pending_script=self.native)
        with self.assertRaises(ValueError):
            issue_stage(self.root, "../escape", 1)
        for bad_stage in (0, 5, True, "1"):
            with self.assertRaises(ValueError):
                issue_stage(self.root, run_id, bad_stage)
        for stage in (1, 2):
            issue_stage(self.root, run_id, stage)
            self.handoff(run_id, stage)
            accept_stage(self.root, run_id, stage)
        wrong_native = self.base / "wrong.blend"
        wrong_native.write_bytes(b"different native bytes")
        event = self.base / "event.md"
        event.write_text("An artist changed placement", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checkpoint_sha256"):
            issue_stage(self.root, run_id, 3, checkpoint=wrong_native, observation=self.observation, event=event)
        self.assertFalse((self.root / "packets" / run_id / "s03").exists())

    def test_accepted_hash_tampering_blocks_next_packet(self):
        run_id = self.run_for("A")
        issue_stage(self.root, run_id, 1)
        self.handoff(run_id, 1)
        accepted = accept_stage(self.root, run_id, 1)
        (accepted / "CONTINUE.md").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Frozen files changed"):
            issue_stage(self.root, run_id, 2)


if __name__ == "__main__":
    unittest.main()
