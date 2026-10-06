"""Anonymous image export tests; no browser or native production-file access."""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from dcc_harness.blind_review import _chunk, _strip_png_metadata
from dcc_harness.continuity_review import CRITERIA, STAGES, VIEWS, export_review


SECRET = "PRIVATE_METHOD_CONTEXT_DO_NOT_PUBLISH"


def png():
    header = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    pixels = b"\0\xff\0\0\0\xff\0\0\0\0\xff\xff\xff\xff"
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header)
            + _chunk(b"sRGB", b"\0")
            + _chunk(b"tEXt", b"Author\0" + SECRET.encode())
            + _chunk(b"IDAT", zlib.compress(pixels)) + _chunk(b"IEND", b""))


def chunks(data):
    offset, result = 8, []
    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        result.append((data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]))
        offset += length + 12
    return result


class ContinuityReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.out = self.base / "review"
        self.receipt = self.base / "private" / "mapping.json"
        self.source = self.base / f"{SECRET}.png"
        self.source.write_bytes(png())
        self.entries = [{"run_id": f"PRIVATE_RUN_{n}", "stages": {
            stage: {view: self.source for view in VIEWS} for stage in STAGES}} for n in range(4)]

    def publish(self, entries=None, baseline=None):
        return export_review(self.entries if entries is None else entries, self.out, self.receipt, baseline)

    def document(self):
        return json.loads((self.out / "scores.json").read_text(encoding="utf-8"))

    def test_four_labels_96_slots_and_optional_six_view_baseline(self):
        result = self.publish(baseline={view: self.source for view in VIEWS})
        document = self.document()
        labels = [review["label"] for review in document["reviews"]]
        self.assertEqual(len(set(labels)), 4)
        self.assertTrue(all(re.fullmatch(r"R-[0-9a-f]{16}", label) for label in labels))
        self.assertEqual(result["trial_slots"], 96)
        self.assertEqual(result["baseline_slots"], 6)
        self.assertEqual(result["available_images"], 102)
        self.assertEqual(len(list((self.out / "images").iterdir())), 102)
        self.assertEqual(set(document["baseline"]["images"]), set(VIEWS))
        self.assertEqual(set(document["stage_descriptions"]), set(STAGES))
        for review in document["reviews"]:
            self.assertEqual(set(review["images"]), set(STAGES))
            self.assertEqual(set(review["scores"]), set(STAGES))
            for stage in STAGES:
                self.assertEqual(set(review["images"][stage]), set(VIEWS))
                self.assertEqual(set(review["scores"][stage]), {*CRITERIA, "editability"})
                self.assertTrue(all(score is None for score in review["scores"][stage].values()))
            self.assertIn("unassessed", review["editability_status"])
            self.assertEqual(review["continuity_notes"], "")

    def test_missing_stages_and_invalid_images_retain_all_slots(self):
        invalid = self.base / "PRIVATE_INVALID_IMAGE.png"
        invalid.write_bytes(b"not a PNG")
        entries = [{"run_id": "missing-workflow"},
                   {"run_id": "partial-workflow", "stages": {"s01": {"hero": self.source}}},
                   {"run_id": "failed-workflow", "stages": None},
                   {"run_id": "invalid-image-workflow", "stages": {
                       "s02": {"hero": invalid, "reverse": self.base / "PRIVATE_MISSING.png", "detail": None},
                       "s03": {"hero": self.base}, "s04": None}}]
        result = self.publish(entries, baseline={})
        document = self.document()
        slots = [value for review in document["reviews"] for views in review["images"].values() for value in views.values()]
        self.assertEqual(len(slots), 96)
        self.assertEqual(sum(value is not None for value in slots), 1)
        self.assertTrue(all(value is None for value in document["baseline"]["images"].values()))
        self.assertEqual(result["available_images"], 1)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        bad = next(r for r in receipt["reviews"] if r["run_id"] == "invalid-image-workflow")
        self.assertEqual(bad["images"]["s02"]["hero"]["status"], "missing")
        self.assertEqual(bad["images"]["s02"]["hero"]["source_sha256"], hashlib.sha256(invalid.read_bytes()).hexdigest())
        self.assertIn("reason", bad["images"]["s02"]["hero"])
        public = (self.out / "scores.json").read_text(encoding="utf-8") + (self.out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE_INVALID_IMAGE", public)
        self.assertNotIn("PRIVATE_MISSING", public)
        self.assertNotIn("Invalid PNG", public)
        self.assertEqual(public.count("Image unavailable"), 101)

    def test_anonymous_public_text_and_metadata_with_private_mapping(self):
        self.entries[0]["run_id"] = '<script>alert("PRIVATE_RUN")</script>'
        self.publish()
        contents = b"\n".join(path.read_bytes() for path in self.out.rglob("*") if path.is_file())
        for secret in (SECRET, "PRIVATE_RUN", str(self.base), str(self.receipt), "source_sha256", "published_sha256", "run_id"):
            self.assertNotIn(secret.encode(), contents)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual({entry["run_id"] for entry in receipt["reviews"]}, {entry["run_id"] for entry in self.entries})
        self.assertEqual({entry["label"] for entry in receipt["reviews"]}, {entry["label"] for entry in self.document()["reviews"]})
        self.assertIn(SECRET, self.receipt.read_text(encoding="utf-8"))
        self.assertFalse(self.receipt.is_relative_to(self.out))

    def test_existing_stripper_keeps_encoded_pixels_colors_and_source_bytes(self):
        before = self.source.read_bytes()
        self.publish()
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        mapping = receipt["reviews"][0]["images"]["s01"]["hero"]
        cleaned = (self.out / mapping["published"]).read_bytes()
        self.assertEqual(cleaned, _strip_png_metadata(before))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(mapping["source_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(mapping["published_sha256"], hashlib.sha256(cleaned).hexdigest())
        original_chunks, clean_chunks = chunks(before), chunks(cleaned)
        self.assertEqual([p for k, p in original_chunks if k == b"IDAT"], [p for k, p in clean_chunks if k == b"IDAT"])
        self.assertEqual([p for k, p in original_chunks if k == b"sRGB"], [p for k, p in clean_chunks if k == b"sRGB"])
        self.assertNotIn(b"tEXt", {k for k, _ in clean_chunks})
        self.assertEqual(zlib.decompress(b"".join(p for k, p in original_chunks if k == b"IDAT")),
                         zlib.decompress(b"".join(p for k, p in clean_chunks if k == b"IDAT")))

    def test_gallery_has_full_size_links_controls_and_local_download_source(self):
        self.publish()
        source = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertEqual(source.count('<figure>'), 96)
        self.assertEqual(source.count('<select '), 4 * 4 * len(CRITERIA))
        self.assertEqual(source.count('<textarea '), 4)
        self.assertIn('Download scores JSON', source)
        self.assertIn('URL.createObjectURL', source)
        self.assertIn("link.download = 'continuity-scores.json'", source)
        self.assertNotIn('fetch(', source)
        self.assertNotIn('http://', source)
        self.assertNotIn('https://', source)
        for review in self.document()["reviews"]:
            for views in review["images"].values():
                for relative in views.values():
                    self.assertIn(f'href="{relative}"', source)
                    self.assertIn(f'src="{relative}"', source)
        self.assertIsNone(self.document()["baseline"])

    def test_schema_and_type_errors_fail_before_publication(self):
        cases = []
        cases.append(self.entries[:3])
        cases.append(tuple(self.entries))
        duplicate = copy.deepcopy(self.entries)
        duplicate[1]["run_id"] = duplicate[0]["run_id"]
        cases.append(duplicate)
        for mutate in (
            lambda e: e[0].update(run_id=" "),
            lambda e: e[0].update(run_id=12),
            lambda e: e[0].update(condition="H"),
            lambda e: e[0].update(stages=[]),
            lambda e: e[0].update(stages={"s05": {}}),
            lambda e: e[0].update(stages={"s01": []}),
            lambda e: e[0].update(stages={"s01": {"secret-camera": None}}),
            lambda e: e[0].update(stages={"s01": {"hero": 5}}),
            lambda e: e[0].update(stages={"s01": {"hero": ""}}),
        ):
            value = copy.deepcopy(self.entries)
            mutate(value)
            cases.append(value)
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.publish(entries)
            self.assertFalse(self.out.exists())
            self.assertFalse(self.receipt.exists())
        for baseline in ([], {"outside": self.source}, {"hero": True}):
            with self.subTest(baseline=baseline), self.assertRaises(ValueError):
                self.publish(baseline=baseline)
            self.assertFalse(self.out.exists())

    def test_receipt_and_public_paths_must_be_separate_and_typed(self):
        for receipt in (self.out, self.out / "private.json", self.out.parent / "review" / "nested" / "private.json"):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                export_review(self.entries, self.out, receipt)
            self.assertFalse(self.out.exists())
        with self.assertRaises(ValueError):
            export_review(self.entries, self.base / "file.json" / "review", self.base / "file.json")
        for bad in (None, True, 3, ""):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                export_review(self.entries, bad, self.receipt)
            with self.subTest(path=bad), self.assertRaises(ValueError):
                export_review(self.entries, self.out, bad)

    def test_existing_files_and_partial_publications_are_never_overwritten(self):
        self.out.mkdir()
        marker = self.out / "partial.txt"
        marker.write_text("retain partial publication", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.publish()
        self.assertEqual(marker.read_text(encoding="utf-8"), "retain partial publication")
        self.out = self.base / "another-review"
        self.receipt.parent.mkdir()
        self.receipt.write_text("existing private record", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.publish()
        self.assertFalse(self.out.exists())
        self.assertEqual(self.receipt.read_text(encoding="utf-8"), "existing private record")

    def test_symlink_sources_and_outputs_are_rejected_before_publication(self):
        linked = self.base / "linked.png"
        try:
            linked.symlink_to(self.source)
        except OSError:
            self.skipTest("Host does not permit test symlinks")
        self.entries[0]["stages"]["s01"]["hero"] = linked
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.out.exists())
        self.entries[0]["stages"]["s01"]["hero"] = self.source
        self.out.symlink_to(self.base / "missing-folder", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.publish()

    def test_size_budget_failure_precedes_publication(self):
        with patch("dcc_harness.continuity_review._MAX_EXPORT_BYTES", len(_strip_png_metadata(png()))):
            with self.assertRaisesRegex(ValueError, "memory budget"):
                self.publish()
        self.assertFalse(self.out.exists())
        self.assertFalse(self.receipt.exists())

    def test_colliding_random_label_is_replaced(self):
        with patch("dcc_harness.continuity_review.secrets.token_hex", side_effect=["1" * 16, "1" * 16, "2" * 16, "3" * 16, "4" * 16]):
            self.publish()
        self.assertEqual({r["label"] for r in self.document()["reviews"]}, {"R-" + n * 16 for n in "1234"})


if __name__ == "__main__":
    unittest.main()
