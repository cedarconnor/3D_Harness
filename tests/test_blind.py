import collections
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dcc_harness.blind import HELPER_FILES, prepare_round, release_revision, verify_packet, accept_revision


class BlindPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "round"
        self.starter = self.base / "starter.blend"
        # These are packaging fixtures, not claims of native Blender validation.
        self.starter.write_bytes(b"BLENDER-fixture-starter")
        self.kit = self.base / "kit"
        self.kit.mkdir()
        (self.kit / "stone.bin").write_bytes(b"fixed-texture-bytes")
        self.templates = self.base / "templates"
        (self.templates / "common").mkdir(parents=True)
        (self.templates / "common" / "BRIEF.md").write_text("Build a courtyard.", encoding="utf-8")
        (self.templates / "common" / "contract.json").write_text('{"hero_width": 1.9}', encoding="utf-8")
        for skill in ("plan", "build", "continue"):
            folder = self.templates / "skills" / skill
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(f"Method: {skill}", encoding="utf-8")
        (self.templates / "build.txt").write_text("Use the common brief.", encoding="utf-8")
        (self.templates / "revision.txt").write_bytes(b"Change stone tint and hero width to 2.1.\r\nKeep lighting.")
        (self.templates / "measured.txt").write_text("Use native measurements.", encoding="utf-8")
        self.helper = self.base / "dcc_harness"
        self.helper.mkdir()
        for name in HELPER_FILES:
            (self.helper / name).write_text(f"# Runtime helper {name}\n", encoding="utf-8")
        (self.helper / "blind.py").write_text("PRIVATE EXPERIMENT COORDINATOR", encoding="utf-8")
        (self.helper / "unlisted.py").write_text("NOT A PERMITTED HELPER", encoding="utf-8")

    def prepare(self):
        return prepare_round(self.root, self.starter, self.kit, self.templates, self.helper, seed=42)

    def handoff(self, run_id):
        output = self.root / "trials" / run_id / "output"
        (output / "pre.blend").write_bytes(b"BLENDER-fixture-completed")
        (output / "CONTINUE.md").write_text("Saved courtyard. Preserve lights.", encoding="utf-8")
        return output

    def test_six_balanced_runs_have_identical_common_inputs(self):
        manifest = self.prepare()
        self.assertEqual(len(manifest["runs"]), 6)
        self.assertEqual(len({run["run_id"] for run in manifest["runs"]}), 6)
        self.assertEqual(collections.Counter(run["condition"] for run in manifest["runs"]), {"A": 2, "B": 2, "C": 2})
        for block in (1, 2):
            self.assertEqual({run["condition"] for run in manifest["runs"] if run["block"] == block}, set("ABC"))
        hashes = []
        for run in manifest["runs"]:
            self.assertTrue(verify_packet(self.root, run["run_id"])["verified"])
            hashes.append({name: value for name, value in run["build_hashes"].items()
                           if name.startswith(("common/", "assets/")) or name == "starter.blend"})
        self.assertTrue(all(item == hashes[0] for item in hashes))

    def test_method_boundaries_do_not_copy_coordinator_or_revision_request(self):
        manifest = self.prepare()
        for run in manifest["runs"]:
            packet = self.root / "trials" / run["run_id"]
            condition = run["condition"]
            self.assertEqual((packet / "skills").exists(), condition in {"B", "C"})
            self.assertEqual((packet / "helper").exists(), condition == "C")
            self.assertEqual((packet / "measured.txt").exists(), condition == "C")
            self.assertFalse((packet / "revision.txt").exists())
            self.assertFalse((packet / "REVISION.md").exists())
            self.assertFalse((packet / "private").exists())
            prompt = (packet / "PROMPT.md").read_text(encoding="utf-8")
            self.assertNotIn("2.1", prompt)
            self.assertNotIn("condition", prompt.lower())
            if condition == "C":
                self.assertEqual({path.name for path in (packet / "helper" / "dcc_harness").iterdir()}, set(HELPER_FILES))
            self.assertFalse(list(packet.rglob("blind.py")))

    def test_modifications_deletions_and_unlisted_inputs_fail_verification(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        packet = self.root / "trials" / run_id
        original = (packet / "starter.blend").read_bytes()
        (packet / "starter.blend").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Frozen files changed"):
            verify_packet(self.root, run_id)
        (packet / "starter.blend").write_bytes(original)
        extra = packet / "another-run.txt"
        extra.write_text("leaked input", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_packet(self.root, run_id)
        extra.unlink()
        (packet / "common" / "BRIEF.md").unlink()
        with self.assertRaises(ValueError):
            verify_packet(self.root, run_id)

    def test_mutable_outputs_do_not_change_the_input_seal(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        output = self.handoff(run_id)
        (output / "work.py").write_text("# run-owned work", encoding="utf-8")
        self.assertTrue(verify_packet(self.root, run_id)["verified"])

    def test_missing_or_empty_handoff_refuses_release_without_publication(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        output = self.root / "trials" / run_id / "output"
        for missing in ("both", "CONTINUE.md", "empty"):
            if missing == "CONTINUE.md":
                (output / "pre.blend").write_bytes(b"BLENDER-native-fixture")
            elif missing == "empty":
                (output / "CONTINUE.md").write_text("", encoding="utf-8")
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                release_revision(self.root, run_id)
            self.assertFalse((self.root / "revisions" / run_id).exists())
            self.assertFalse((self.root / "private" / "accepted" / run_id).exists())

    def test_revision_context_contains_only_frozen_inputs_and_accepted_handoff(self):
        manifest = self.prepare()
        revision_bytes = (self.templates / "revision.txt").read_bytes()
        for run in manifest["runs"]:
            run_id = run["run_id"]
            output = self.handoff(run_id)
            for name in ("builder-transcript.json", "operations.jsonl", "build.py", "pre.png"):
                (output / name).write_text("MUST NOT TRANSFER", encoding="utf-8")
            revision = release_revision(self.root, run_id)
            self.assertEqual(revision, self.root / "revisions" / run_id)
            self.assertEqual((revision / "REVISION.md").read_bytes(), revision_bytes)
            self.assertEqual((revision / "pre.blend").read_bytes(), b"BLENDER-fixture-completed")
            self.assertEqual(list((revision / "output").iterdir()), [])
            self.assertEqual((revision / "skills").exists(), run["condition"] in {"B", "C"})
            self.assertEqual((revision / "helper").exists(), run["condition"] == "C")
            for name in ("builder-transcript.json", "operations.jsonl", "build.py", "pre.png", "starter.blend"):
                self.assertFalse((revision / name).exists())
            self.assertTrue(verify_packet(self.root, run_id, "revision")["verified"])
            # Subsequent builder-output writes cannot alter the accepted native copy.
            (output / "pre.blend").write_bytes(b"later-unaccepted-output")
            self.assertTrue(verify_packet(self.root, run_id, "revision")["verified"])

    def test_duplicate_round_and_revision_publications_are_refused(self):
        manifest = self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        self.handoff(run_id)
        revision = release_revision(self.root, run_id)
        before = (revision / "pre.blend").read_bytes()
        with self.assertRaises(FileExistsError):
            release_revision(self.root, run_id)
        self.assertEqual((revision / "pre.blend").read_bytes(), before)

    def test_tampered_accepted_checkpoint_and_private_frozen_inputs_are_detected(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        self.handoff(run_id)
        release_revision(self.root, run_id)
        (self.root / "private" / "accepted" / run_id / "pre.blend").write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            verify_packet(self.root, run_id, "revision")
        (self.root / "private" / "frozen" / "revision.txt").write_text("changed request", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_packet(self.root, run_id)

    def test_traversal_and_unknown_identifiers_are_rejected(self):
        self.prepare()
        for run_id in ("../private", "..\\private", "/tmp", "C:\\private", "t-0123456789ab/..", "t-0123456789ab"):
            with self.subTest(run_id=run_id):
                with self.assertRaises(ValueError):
                    verify_packet(self.root, run_id)
                with self.assertRaises(ValueError):
                    release_revision(self.root, run_id)

    def test_symlinked_handoff_is_rejected_when_host_supports_symlinks(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        output = self.handoff(run_id)
        (output / "pre.blend").unlink()
        try:
            (output / "pre.blend").symlink_to(self.starter)
        except OSError as exc:
            self.skipTest(f"Host symlink permission unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "Linked/reparse"):
            release_revision(self.root, run_id)

    def test_cli_verify_returns_only_neutral_receipt(self):
        manifest = self.prepare()
        run_id = manifest["runs"][0]["run_id"]
        result = subprocess.run(
            [sys.executable, "-m", "dcc_harness.blind", "verify", "--root", str(self.root), "--run-id", run_id],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True,
        )
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["verified"])
        self.assertNotIn("condition", receipt)
        self.assertNotIn("frozen_hashes", receipt)

    def test_final_snapshot_is_isolated_and_duplicate_publication_refused(self):
        run_id = self.prepare()["runs"][0]["run_id"]
        self.handoff(run_id)
        packet = release_revision(self.root, run_id)
        (packet / "output" / "post.blend").write_bytes(b"revised native fixture")
        (packet / "output" / "CONTINUE.md").write_text("Saved result", encoding="utf-8")
        (packet / "output" / "secret-log.json").write_text("not a handoff", encoding="utf-8")
        snapshot = accept_revision(self.root, run_id)
        self.assertEqual({p.name for p in snapshot.iterdir()}, {"post.blend", "CONTINUE.md"})
        (packet / "output" / "post.blend").write_bytes(b"later changed output")
        self.assertEqual((snapshot / "post.blend").read_bytes(), b"revised native fixture")
        with self.assertRaises(FileExistsError):
            accept_revision(self.root, run_id)

    def test_final_snapshot_rejects_missing_result_or_changed_input(self):
        run_id = self.prepare()["runs"][0]["run_id"]
        self.handoff(run_id)
        packet = release_revision(self.root, run_id)
        with self.assertRaises(ValueError):
            accept_revision(self.root, run_id)
        self.assertFalse((self.root / "private" / "completed" / run_id).exists())
        (packet / "output" / "post.blend").write_bytes(b"revised native fixture")
        (packet / "output" / "CONTINUE.md").write_text("Saved result", encoding="utf-8")
        (packet / "pre.blend").write_bytes(b"changed input")
        with self.assertRaises(ValueError):
            accept_revision(self.root, run_id)
        self.assertFalse((self.root / "private" / "completed" / run_id).exists())


if __name__ == "__main__":
    unittest.main()
