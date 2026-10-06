import base64
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from dcc_harness.blind_review import CAMERAS, PHASES, _strip_png_metadata, export_review


# Valid 1x1, 8-bit grayscale + alpha PNG. Fixture is deliberately independent
# of the encoder used below to construct malformed or ancillary-chunk cases.
PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def chunks(data):
    result, position = [], 8
    while position < len(data):
        size = struct.unpack_from(">I", data, position)[0]
        result.append((data[position + 4:position + 8], data[position + 8:position + 8 + size]))
        position += size + 12
    return result


def png(parts):
    return SIGNATURE + b"".join(chunk(kind, data) for kind, data in parts)


class PNGTests(unittest.TestCase):
    def test_valid_fixture_has_exact_pixel_and_idat_preservation(self):
        parts = chunks(PIXEL)
        annotated = png(parts[:1] + [(b"tEXt", b"Author\0SECRET-model-run-path"),
                                    (b"zTXt", b"Note\0\0" + zlib.compress(b"SECRET private description")),
                                    (b"sRGB", b"\0"), (b"gAMA", struct.pack(">I", 45455)),
                                    (b"cHRM", struct.pack(">8I", 31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000))] + parts[1:])
        result = _strip_png_metadata(annotated)
        retained = dict(chunks(result))
        self.assertEqual(retained[b"IHDR"], dict(parts)[b"IHDR"])
        self.assertEqual(retained[b"IDAT"], dict(parts)[b"IDAT"])
        self.assertEqual(zlib.decompress(retained[b"IDAT"]), b"\x01\x00\xff")
        for kind in (b"sRGB", b"gAMA", b"cHRM"):
            self.assertEqual(retained[kind], dict(chunks(annotated))[kind])
        self.assertNotIn(b"SECRET", result)
        self.assertNotIn(b"tEXt", retained)
        self.assertEqual(_strip_png_metadata(PIXEL), PIXEL)

    def test_palette_and_transparency_are_preserved(self):
        image = png([(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 3, 0, 0, 0)),
                     (b"PLTE", b"\x11\x22\x33"), (b"tRNS", b"\x80"),
                     (b"IDAT", zlib.compress(b"\0\0")), (b"IEND", b"")])
        self.assertEqual(_strip_png_metadata(image), image)

    def test_adam7_single_pixel_is_preserved(self):
        parts = chunks(PIXEL)
        parts[0] = (b"IHDR", parts[0][1][:-1] + b"\1")
        image = png(parts)
        self.assertEqual(_strip_png_metadata(image), image)

    def test_malformed_crc_dimensions_stream_and_order_rejected(self):
        parts = chunks(PIXEL)
        ihdr, idat, iend = parts
        cases = {
            "signature": b"bad" + PIXEL,
            "truncated": PIXEL[:-1],
            "crc": PIXEL[:29] + bytes([PIXEL[29] ^ 1]) + PIXEL[30:],
            "trailing": PIXEL + b"private note",
            "zero width": png([(b"IHDR", bytes(4) + ihdr[1][4:]), idat, iend]),
            "depth": png([(b"IHDR", ihdr[1][:8] + b"\3" + ihdr[1][9:]), idat, iend]),
            "duplicate header": png([ihdr, ihdr, idat, iend]),
            "first": png([idat, ihdr, iend]),
            "missing end": png([ihdr, idat]),
            "unknown critical": png([ihdr, (b"ABCD", b""), idat, iend]),
            "reserved bit": png([ihdr, (b"abcd", b""), idat, iend]),
            "color order": png([ihdr, idat, (b"gAMA", struct.pack(">I", 45455)), iend]),
            "split idat": png([ihdr, idat, (b"tEXt", b"key\0value"), idat, iend]),
            "broken zlib": png([ihdr, (b"IDAT", b"broken"), iend]),
            "extra scanline": png([ihdr, (b"IDAT", zlib.compress(b"\0\0\xff\0")), iend]),
            "bad filter": png([ihdr, (b"IDAT", zlib.compress(b"\5\0\xff")), iend]),
            "zlib trailing": png([ihdr, (b"IDAT", idat[1] + b"trailing"), iend]),
            "animation": png([ihdr, (b"acTL", struct.pack(">II", 1, 0)), idat, iend]),
        }
        for name, data in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                _strip_png_metadata(data)

    def test_icc_profile_bytes_preserved_or_rejected_without_rewriting(self):
        header = bytearray(128)
        header[16:20], header[36:40] = b"GRAY", b"acsp"
        tag = b"curv" + bytes(4) + struct.pack(">I", 0)
        profile = header + struct.pack(">I4sII", 1, b"kTRC", 144, len(tag)) + tag
        struct.pack_into(">I", profile, 0, len(profile))
        compressed = zlib.compress(profile)
        parts = chunks(PIXEL)
        image = png(parts[:1] + [(b"iCCP", b"SECRET profile name\0\0" + compressed)] + parts[1:])
        result = dict(chunks(_strip_png_metadata(image)))[b"iCCP"]
        self.assertEqual(result, b"ICC\0\0" + compressed)
        profile[144:148] = b"text"
        image = png(parts[:1] + [(b"iCCP", b"profile\0\0" + zlib.compress(profile))] + parts[1:])
        with self.assertRaisesRegex(ValueError, "descriptive metadata"):
            _strip_png_metadata(image)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "PRIVATE-agent-condition-model-source.png"
        parts = chunks(PIXEL)
        self.source.write_bytes(png(parts[:1] + [(b"tEXt", b"Author\0PRIVATE-author-model-condition")] + parts[1:]))
        self.entries = [{"run_id": f"PRIVATE-run-{index}", **{phase: {camera: self.source for camera in CAMERAS} for phase in PHASES}} for index in range(6)]
        self.out, self.receipt = self.root / "public", self.root / "private" / "mapping.json"

    def export(self):
        return export_review(self.entries, self.out, self.receipt)

    def test_anonymized_gallery_receipt_and_null_score_form(self):
        initial = self.source.read_bytes()
        entry_snapshot = copy.deepcopy(self.entries)
        result = self.export()
        document = json.loads((self.out / "scores.json").read_text())
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(len(document["reviews"]), 6)
        self.assertEqual(len(list((self.out / "images").glob("*.png"))), 36)
        labels = {entry["label"] for entry in document["reviews"]}
        self.assertEqual(len(labels), 6)
        self.assertEqual(labels, {entry["label"] for entry in receipt["reviews"]})
        self.assertEqual({entry["run_id"] for entry in receipt["reviews"]}, {entry["run_id"] for entry in self.entries})
        self.assertEqual(result["gallery"], str(self.out / "index.html"))
        for file in self.out.rglob("*"):
            if file.is_file():
                self.assertNotIn(b"PRIVATE", file.read_bytes())
                self.assertNotIn(str(self.root).encode(), file.read_bytes())
                self.assertNotIn(b"run_id", file.read_bytes())
        for entry in document["reviews"]:
            self.assertRegex(entry["label"], r"^R-[a-f0-9]{16}$")
            self.assertIn("unassessed", entry["editability_status"])
            for phase in PHASES:
                self.assertEqual(set(entry["images"][phase]), set(CAMERAS))
                self.assertEqual(entry["scores"][phase], dict.fromkeys(("composition", "proportion", "materials", "lighting", "editability")))
        gallery = (self.out / "index.html").read_text()
        self.assertEqual(gallery.count('<select '), 48)
        self.assertIn("4: usable with minor cleanup", gallery)
        self.assertIn("Download scores JSON", gallery)
        self.assertNotIn('data-criterion="editability"', gallery)
        self.assertEqual(self.source.read_bytes(), initial)
        self.assertEqual(self.entries, entry_snapshot)

    def test_labels_and_display_order_do_not_encode_run_order(self):
        with patch("dcc_harness.blind_review.secrets.SystemRandom") as random_source, patch("dcc_harness.blind_review.secrets.token_hex", side_effect=[f"{index:016x}" for index in range(6)]):
            random_source.return_value.shuffle.side_effect = lambda entries: entries.reverse()
            self.export()
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual([entry["run_id"] for entry in receipt["reviews"]], [entry["run_id"] for entry in reversed(self.entries)])
        self.assertEqual(receipt["reviews"][0]["label"], "R-0000000000000000")

    def test_failed_and_missing_entries_are_retained_as_cells(self):
        self.entries[0] = {"run_id": "PRIVATE-failed-run"}
        self.entries[1]["pre"] = None
        self.entries[2]["post"]["hero"] = self.root / "PRIVATE-missing.png"
        malformed = self.root / "PRIVATE-malformed.png"
        malformed.write_bytes(PIXEL + b"trailing")
        self.entries[3]["post"]["detail"] = malformed
        self.export()
        document = json.loads((self.out / "scores.json").read_text())
        self.assertEqual(len(document["reviews"]), 6)
        self.assertEqual(sum(path is None for entry in document["reviews"] for phase in PHASES for path in entry["images"][phase].values()), 11)
        self.assertEqual((self.out / "index.html").read_text().count('class="missing"'), 11)
        receipt = json.loads(self.receipt.read_text())
        reasons = [cell["reason"] for entry in receipt["reviews"] for phase in PHASES for cell in entry["images"][phase].values() if "reason" in cell]
        self.assertEqual(len(reasons), 2)

    def test_bad_entries_fail_before_output(self):
        variants = [self.entries[:5], self.entries + [self.entries[0]], self.entries[:5] + [self.entries[0]],
                    self.entries[:5] + [{"run_id": ""}], self.entries[:5] + [{"run_id": "unique", "pre": {"unknown": "image"}}]]
        for entries in variants:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                export_review(entries, self.out, self.receipt)
            self.assertFalse(self.out.exists())
            self.assertFalse(self.receipt.exists())

    def test_existing_output_or_receipt_cannot_be_overwritten(self):
        self.export()
        snapshot = {str(path): path.read_bytes() for path in self.out.rglob("*") if path.is_file()}
        old_receipt = self.receipt.read_bytes()
        with self.assertRaises(FileExistsError):
            self.export()
        with self.assertRaises(FileExistsError):
            export_review(self.entries, self.root / "other-public", self.receipt)
        self.assertFalse((self.root / "other-public").exists())
        self.assertEqual(snapshot, {str(path): path.read_bytes() for path in self.out.rglob("*") if path.is_file()})
        self.assertEqual(self.receipt.read_bytes(), old_receipt)

    def test_private_receipt_must_be_outside_public_output(self):
        for receipt in (self.out, self.out / "mapping.json", self.out / "nested" / "mapping.json"):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                export_review(self.entries, self.out, receipt)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
