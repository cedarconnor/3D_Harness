"""Portable store tests use synthetic native bytes, not Blender qualification."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dcc_harness.continuity import Continuity
from dcc_harness.evidence import digest, evaluate, file_hash, read_json, write_json


def resign(obs):
    obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
    return obs


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Continuity(self.root / "store")
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.counter = 0

    def evidence(self, width=1.0):
        self.counter += 1
        prefix = self.inputs / str(self.counter)
        prefix.mkdir()
        native = prefix / "scene.blend"
        native.write_bytes(f"synthetic checkpoint {self.counter}".encode())
        obj = {"name": "Bench", "type": "MESH", "asset_id": "bench", "parent": None,
               "material_ids": ["stone", "stone"], "collections": ["Courtyard"],
               "dimensions": [width, .5, .9], "triangles": 100}
        obs = resign({"schema": "dcc.observation.v1", "checkpoint_sha256": file_hash(native),
                      "objects": {"bench-1": obj, "bench-2": {**obj, "name": "Bench copy", "parent": "bench-1"}},
                      "materials": {"stone": {"name": "Stone", "graph": {"nodes": [
                          {"name": "texture", "image": {"name": "Surface", "path": "historical/image.png", "packed": True,
                                                        "exists": True, "sha256": "a" * 64}}]}}},
                      "scene": {"units": {"system": "METRIC", "scale_length": 1}},
                      "coverage": {"measured": ["objects", "materials"], "not_measured": ["artistic quality"]},
                      "issues": []})
        observation = prefix / "observation.json"
        write_json(observation, obs)
        handoff = prefix / "CONTINUE.md"
        handoff.write_text("Keep the shared stone. Inspect both benches before changing them.", encoding="utf-8")
        check = prefix / "check.json"
        write_json(check, evaluate(obs, {"schema": "dcc.spec.v1", "required": {"bench-1": {"dimensions": [width, .5, .9]}}}))
        return native, observation, handoff, check

    def initialize(self):
        native, observation, handoff, _ = self.evidence()
        return self.store.initialize(native, observation, "A coherent courtyard", {"palette": "warm", "preserve": ["camera"]}, handoff=handoff)

    def publish(self, parent, step="widen-bench", updates=None):
        native, observation, handoff, check = self.evidence(1.2)
        return self.store.publish(step, parent, native, observation, handoff,
                                  {"bench_width": 1.2} if updates is None else updates, check)

    def test_fresh_process_continues_decisions_and_registry(self):
        state = self.initialize()
        native, observation, handoff, check = self.evidence(1.2)
        program = """
import json, sys
from dcc_harness.continuity import Continuity
root, parent, native, observation, handoff, check = sys.argv[1:]
store = Continuity(root)
result = store.publish('widen', parent, native, observation, handoff,
                       {'bench_width': 1.2, 'palette': 'cool'}, check)
print(json.dumps(result))
"""
        command = [sys.executable, "-c", program, str(self.store.root), state["active"]["id"],
                   *map(str, (native, observation, handoff, check))]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        resumed = json.loads(result.stdout)
        self.assertEqual(resumed["decisions"], {"palette": "cool", "preserve": ["camera"], "bench_width": 1.2})
        self.assertEqual([s["step_id"] for s in resumed["task_history"]], ["initial", "widen"])
        self.assertEqual(resumed["decision_history"][0]["updates"]["palette"], "warm")
        registry = resumed["registry"]
        self.assertEqual(registry["assets"]["bench"], {"instances": ["bench-1", "bench-2"], "material_ids": ["stone"]})
        self.assertEqual(registry["materials"]["stone"], {"users": ["bench-1", "bench-2"], "asset_ids": ["bench"]})
        self.assertEqual(registry["dependencies"]["parents"], {"bench-1": ["bench-2"]})
        self.assertEqual(next(iter(registry["dependencies"]["images"].values()))["users"], ["material:stone"])
        self.assertEqual(resumed["artistic_acceptance"], "not_evaluated")
        self.assertIsNone(resumed["task_history"][0]["report_passed"])

    def test_relocated_store_continues_without_historical_sources(self):
        first = self.initialize()
        script = self.inputs / "operation.py"
        script.write_text("# declared native change", encoding="utf-8")
        op = self.store.project.begin("change", script)
        receipt = self.inputs / "receipt.json"
        write_json(receipt, {"observed": True})
        self.store.project.finish(op, receipt)
        accepted = self.publish(first["active"]["id"])
        moved = self.root / "moved-store"
        shutil.copytree(self.store.root, moved)
        self.store.root.rename(self.root / "old-store")
        self.inputs.rename(self.root / "old-inputs")
        self.inputs.mkdir()
        self.store = Continuity(moved)
        self.assertEqual(self.store.status()["active"]["id"], accepted["active"]["id"])
        final = self.publish(accepted["active"]["id"], "fresh-agent", {"lighting": "unchanged"})
        self.assertEqual(final["decisions"]["palette"], "warm")
        self.assertTrue(Path(final["active"]["checkpoint"]).is_relative_to(moved))
        self.assertEqual(final["accepted_journal_events"], 2)
        manifest = read_json(moved / "checkpoints" / "000002" / "manifest.json")
        self.assertTrue(all("/" not in name and "\\" not in name for name in manifest["files"]))

    def test_stale_parent_and_duplicate_step_leave_commits_unchanged(self):
        first = self.initialize()
        second = self.publish(first["active"]["id"])
        with self.assertRaisesRegex(ValueError, "Stale parent"):
            self.publish(first["active"]["id"], "next")
        with self.assertRaisesRegex(ValueError, "already been accepted"):
            self.publish(second["active"]["id"], "widen-bench")
        self.assertEqual(self.store.status()["active"]["id"], second["active"]["id"])
        self.assertEqual(len(list((self.store.root / "checkpoints").iterdir())), 2)

    def test_pending_operation_blocks_publication_until_explicit_reconciliation(self):
        first = self.initialize()
        script = self.inputs / "op.py"
        script.write_text("# uncertain native write", encoding="utf-8")
        op = self.store.project.begin("uncertain", script)
        self.assertEqual(self.store.status()["pending"][0]["id"], op)
        with self.assertRaisesRegex(RuntimeError, "Unresolved Project operation"):
            self.publish(first["active"]["id"])
        inspection = self.inputs / "inspection.json"
        write_json(inspection, {"native_readback": "write completed"})
        self.store.project.finish(op, inspection, reconciled=True)
        result = self.publish(first["active"]["id"])
        self.assertFalse(result["pending"])
        self.assertEqual(result["accepted_journal_events"], 2)

    def test_changed_journal_script_or_evidence_blocks_acceptance(self):
        for changed in ("script", "receipt"):
            with self.subTest(changed=changed):
                self.store = Continuity(self.root / changed)
                first = self.initialize()
                script = self.inputs / f"op-{changed}.py"
                script.write_text("# original", encoding="utf-8")
                op = self.store.project.begin("change", script)
                receipt = self.inputs / f"receipt-{changed}.json"
                write_json(receipt, {"observed": True})
                self.store.project.finish(op, receipt)
                (script if changed == "script" else receipt).write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "source/evidence changed"):
                    self.publish(first["active"]["id"])

    def test_corrupted_retained_native_observation_handoff_or_manifest_fails_closed(self):
        for filename in ("checkpoint.blend", "observation.json", "handoff.md", "manifest.json"):
            with self.subTest(filename=filename):
                self.store = Continuity(self.root / filename.replace(".", "-"))
                self.initialize()
                target = self.store.root / "checkpoints" / "000001" / filename
                target.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    self.store.status()

    def test_observation_revision_native_hash_and_structure_are_required(self):
        mutations = (
            lambda o: o.update(checkpoint_sha256="b" * 64),
            lambda o: o["objects"]["bench-1"].update(dimensions=[8, 8, 8]),
            lambda o: resign({**o, "issues": ["Missing instance ID"]}),
            lambda o: resign({**o, "coverage": {"measured": [], "not_measured": []}}),
            lambda o: resign({**o, "objects": {"bench-1": {**o["objects"]["bench-1"], "material_ids": ["missing"]}}}),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                native, observation, _, _ = self.evidence()
                value = read_json(observation)
                updated = mutation(value)
                observation.write_text(json.dumps(updated if updated is not None else value), encoding="utf-8")
                with self.assertRaises(ValueError):
                    Continuity(self.root / f"invalid-{index}").initialize(native, observation, "brief", {})

    def test_report_must_pass_and_match_real_checked_targets_and_revision(self):
        first = self.initialize()
        for changes in ({"passed": False}, {"passed": 1}, {"revision": "a" * 64},
                        {"failures": ["regression"]}, {"checked_targets": []}, {"checked_targets": ["invented"]}):
            native, observation, handoff, check = self.evidence()
            report = read_json(check)
            report.update(changes)
            check.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Check report"):
                self.store.publish("change", first["active"]["id"], native, observation, handoff, {}, check)
        self.assertEqual(len(self.store.status()["task_history"]), 1)

    def test_partial_bundle_blocks_reads_and_further_publication(self):
        first = self.initialize()
        partial = self.store.root / "checkpoints" / "000002"
        partial.mkdir()
        (partial / "checkpoint.blend").write_bytes(b"interrupted")
        with self.assertRaisesRegex(RuntimeError, "Incomplete/unexpected publication"):
            self.store.status()
        with self.assertRaisesRegex(RuntimeError, "inspect and reconcile"):
            self.publish(first["active"]["id"])

    def test_failure_writing_last_manifest_leaves_explicit_partial_bundle(self):
        first = self.initialize()
        import dcc_harness.continuity as module
        real_write = module._write

        def fail_manifest(path, data):
            if path.name == "manifest.json":
                raise OSError("simulated power interruption")
            return real_write(path, data)

        with patch.object(module, "_write", side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError, "power interruption"):
                self.publish(first["active"]["id"])
        self.assertFalse((self.store.root / "checkpoints" / "000002" / "manifest.json").exists())
        self.assertTrue((self.store.root / "checkpoints" / "000002" / "observation.json").exists())
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            self.store.verify()

    def test_native_source_changes_during_copy_leave_uncommitted_stop(self):
        first = self.initialize()
        native, observation, handoff, check = self.evidence()
        real_copy = shutil.copyfileobj

        def copy_then_mutate(incoming, outgoing, *args):
            result = real_copy(incoming, outgoing, *args)
            if Path(incoming.name) == native:
                native.write_bytes(b"concurrent native save")
            return result

        with patch("dcc_harness.continuity.shutil.copyfileobj", side_effect=copy_then_mutate):
            with self.assertRaisesRegex(ValueError, "Source changed"):
                self.store.publish("change", first["active"]["id"], native, observation, handoff, {}, check)
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            self.store.status()

    def test_retained_journal_bytes_and_accepted_prefix_cannot_change(self):
        first = self.initialize()
        script = self.inputs / "op.py"
        script.write_text("# operation", encoding="utf-8")
        op = self.store.project.begin("change", script)
        receipt = self.inputs / "receipt.json"
        write_json(receipt, {"observed": True})
        self.store.project.finish(op, receipt)
        self.publish(first["active"]["id"])
        journal = self.store.root / "operations.jsonl"
        original = journal.read_text(encoding="utf-8")
        events = [json.loads(line) for line in original.splitlines()]
        events[0]["label"] = "rewritten history"
        journal.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "journal changed"):
            self.store.status()
        journal.write_text(original, encoding="utf-8")
        (self.store.root / "checkpoints" / "000002" / "journal-000000-script").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Retained evidence hash changed"):
            self.store.status()

    def test_torn_journal_blocks_status(self):
        self.initialize()
        (self.store.root / "operations.jsonl").write_text('{"event":"begin"', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Journal damaged"):
            self.store.status()

    def test_reader_rechecks_semantic_binding_even_if_inventory_hash_is_updated(self):
        self.initialize()
        bundle = self.store.root / "checkpoints" / "000001"
        obs = read_json(bundle / "observation.json")
        obs["objects"]["bench-1"]["dimensions"] = [9, 9, 9]
        (bundle / "observation.json").write_text(json.dumps(obs), encoding="utf-8")
        manifest = read_json(bundle / "manifest.json")
        manifest["files"]["observation.json"] = file_hash(bundle / "observation.json")
        (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "revision does not match"):
            self.store.status()

    def test_nonfinite_observation_payload_and_extra_metadata_are_rejected(self):
        # Extra metadata is outside the revision digest but must remain valid JSON.
        for location in ('payload', 'metadata'):
            for token in ('NaN', 'Infinity', '-Infinity', '1e999'):
                with self.subTest(location=location, token=token):
                    native, observation, _, _ = self.evidence()
                    obs = read_json(observation)
                    target = obs['objects']['bench-1'] if location == 'payload' else obs
                    target['diagnostic'] = {'nested': ['NONFINITE_SENTINEL']}
                    resign(obs)
                    text = json.dumps(obs).replace('"NONFINITE_SENTINEL"', token)
                    observation.write_text(text, encoding='utf-8')
                    store = Continuity(self.root / f'invalid-number-{self.counter}')
                    with self.assertRaises(ValueError):
                        store.initialize(native, observation, 'brief', {})
                    self.assertEqual(list((store.root / 'checkpoints').iterdir()), [])

    def test_observation_mapping_shapes_checked_after_valid_revision(self):
        mutations = (
            lambda o: o.update({'': 'invalid top-level key'}),
            lambda o: o.update(objects={'': o['objects']['bench-1']}),
            lambda o: o['objects']['bench-1'].update({'': 'invalid object key'}),
            lambda o: o['objects'].update({'bench-1': []}),
            lambda o: o['materials'].update({'stone': []}),
            lambda o: o['materials']['stone'].update({'': 'invalid material key'}),
            lambda o: o.update(scene=[]),
            lambda o: o.update(coverage=[]),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                native, observation, _, _ = self.evidence()
                obs = read_json(observation)
                mutation(obs)
                observation.write_text(json.dumps(resign(obs)), encoding='utf-8')
                with self.assertRaises(ValueError):
                    Continuity(self.root / f'invalid-shape-{index}').initialize(native, observation, 'brief', {})

    def test_registry_is_rederived_even_if_inventory_hash_is_updated(self):
        self.initialize()
        bundle = self.store.root / 'checkpoints' / '000001'
        registry = read_json(bundle / 'registry.json')
        registry['materials']['stone']['users'] = ['invented-user']
        (bundle / 'registry.json').write_text(json.dumps(registry), encoding='utf-8')
        manifest = read_json(bundle / 'manifest.json')
        manifest['files']['registry.json'] = file_hash(bundle / 'registry.json')
        (bundle / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Registry differs'):
            self.store.status()

    def test_warm_reader_rechecks_old_native_bytes_with_unchanged_size_and_mtime(self):
        first = self.initialize()
        self.publish(first['active']['id'])
        self.store.status()
        old_native = self.store.root / 'checkpoints' / '000001' / 'checkpoint.blend'
        stat = old_native.stat()
        original = old_native.read_bytes()
        old_native.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        os.utime(old_native, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(old_native.stat().st_size, stat.st_size)
        self.assertEqual(old_native.stat().st_mtime_ns, stat.st_mtime_ns)
        with self.assertRaisesRegex(ValueError, 'Retained evidence hash changed'):
            self.store.status()

    def test_cli_verify_returns_failure_for_corrupted_store(self):
        self.initialize()
        command = [sys.executable, "-m", "dcc_harness.continuity", "verify", "--root", str(self.store.root)]
        good = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["artistic_acceptance"], "not_evaluated")
        Path(self.store.status()["active"]["checkpoint"]).write_bytes(b"changed")
        bad = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("verification failed", bad.stderr)


if __name__ == "__main__":
    unittest.main()
