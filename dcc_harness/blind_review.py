"""Anonymous, immutable six-entry image reviews; no native scene access."""
from __future__ import annotations

import copy
import hashlib
import html
import json
from pathlib import Path
import secrets
import struct
import zlib

from .evidence import write_json


CAMERAS = ("hero", "reverse", "detail")
PHASES = ("pre", "post")
CRITERIA = ("composition", "proportion", "materials", "lighting")
_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"sRGB", b"gAMA", b"cHRM", b"iCCP", b"tRNS"}
_MAX_BYTES = 128 * 1024 * 1024


def _chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def _inflate(data, limit):
    try:
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(data, limit + 1)
    except zlib.error as exc:
        raise ValueError("Invalid compressed PNG data") from exc
    if len(decoded) > limit or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid or excessive compressed PNG data")
    return decoded


def _clean_iccp(payload, color):
    """Neutralize only the PNG keyword; never rewrite a color profile."""
    name, separator, compressed = payload.partition(b"\0")
    if not separator or not 1 <= len(name) <= 79 or not compressed or compressed[0] != 0:
        raise ValueError("Invalid iCCP header")
    if any(c < 32 or 126 < c < 161 for c in name) or name.strip(b" ") != name or b"  " in name:
        raise ValueError("Invalid iCCP keyword")
    profile = _inflate(compressed[1:], 16 * 1024 * 1024)
    if len(profile) < 132 or struct.unpack_from(">I", profile)[0] != len(profile) or profile[36:40] != b"acsp":
        raise ValueError("Invalid ICC profile")
    if profile[16:20] != (b"GRAY" if color in (0, 4) else b"RGB "):
        raise ValueError("ICC color space differs from PNG")
    count = struct.unpack_from(">I", profile, 128)[0]
    if count > (len(profile) - 132) // 12:
        raise ValueError("Invalid ICC tag table")
    seen = set()
    for index in range(count):
        signature, offset, size = struct.unpack_from(">4sII", profile, 132 + index * 12)
        if signature in seen or offset % 4 or offset < 132 + count * 12 or size < 8 or offset + size > len(profile):
            raise ValueError("Invalid ICC tag")
        seen.add(signature)
        tag = profile[offset:offset + size]
        if tag[:4] in {b"text", b"desc", b"mluc", b"dict"} or signature in {b"meta", b"targ"}:
            raise ValueError("ICC descriptive metadata cannot be published anonymously without rewriting the profile")
    return b"ICC\0\0" + compressed[1:]


def _strip_png_metadata(data):
    """Validate a PNG and retain encoded pixels, transparency and color semantics.

    Both noninterlaced and Adam7 images are supported. APNG is rejected because
    silently dropping its animation chunks would alter the visual content.
    """
    if not isinstance(data, bytes) or len(data) > _MAX_BYTES or not data.startswith(_SIGNATURE):
        raise ValueError("Invalid PNG signature or size")
    position, chunks, seen, compressed = 8, [], set(), bytearray()
    width = height = depth = color = interlace = palette_size = None
    ended_idat = False
    while position < len(data):
        if len(data) - position < 12:
            raise ValueError("Truncated PNG chunk")
        length = struct.unpack_from(">I", data, position)[0]
        kind = data[position + 4:position + 8]
        end = position + 12 + length
        if length > 0x7fffffff or end > len(data) or any(not (65 <= c <= 90 or 97 <= c <= 122) for c in kind) or kind[2] & 32:
            raise ValueError("Invalid PNG chunk")
        payload = data[position + 8:end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from(">I", data, end - 4)[0]:
            raise ValueError("PNG CRC mismatch")
        if not chunks and kind != b"IHDR":
            raise ValueError("IHDR must be first")
        if kind[0] & 32 == 0 and kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"}:
            raise ValueError("Unsupported critical PNG chunk")
        if kind in {b"acTL", b"fcTL", b"fdAT"}:
            raise ValueError("Animated PNG is unsupported")
        if kind in _KEEP - {b"IDAT"} and kind in seen:
            raise ValueError("Duplicate PNG chunk")
        if b"IDAT" in seen and kind != b"IDAT":
            ended_idat = True
        if kind == b"IHDR":
            if length != 13:
                raise ValueError("Invalid IHDR size")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            allowed = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if not 0 < width <= 0x7fffffff or not 0 < height <= 0x7fffffff or depth not in allowed.get(color, ()) or compression or filtering or interlace not in (0, 1):
                raise ValueError("Invalid PNG dimensions or encoding")
        elif kind == b"PLTE":
            if b"IDAT" in seen or b"tRNS" in seen or color in (0, 4) or not length or length % 3 or length > 768:
                raise ValueError("Invalid PNG palette or order")
            palette_size = length // 3
            if color == 3 and palette_size > 2 ** depth:
                raise ValueError("Palette exceeds bit depth")
        elif kind in {b"sRGB", b"gAMA", b"cHRM", b"iCCP"}:
            if b"PLTE" in seen or b"IDAT" in seen:
                raise ValueError("Invalid PNG color chunk order")
            if kind == b"sRGB" and (length != 1 or payload[0] > 3 or b"iCCP" in seen):
                raise ValueError("Invalid sRGB chunk")
            if kind == b"gAMA" and (length != 4 or struct.unpack(">I", payload)[0] == 0):
                raise ValueError("Invalid gAMA chunk")
            if kind == b"cHRM" and length != 32:
                raise ValueError("Invalid cHRM chunk")
            if kind == b"iCCP":
                if b"sRGB" in seen:
                    raise ValueError("Conflicting PNG color profiles")
                payload = _clean_iccp(payload, color)
        elif kind == b"tRNS":
            if b"IDAT" in seen or color not in (0, 2, 3):
                raise ValueError("Invalid PNG transparency or order")
            if color == 3 and (palette_size is None or not 1 <= length <= palette_size):
                raise ValueError("Invalid indexed transparency")
            if color in (0, 2):
                if length != (2 if color == 0 else 6) or any(sample > (1 << depth) - 1 for sample in struct.unpack(">" + "H" * (length // 2), payload)):
                    raise ValueError("Invalid PNG transparency samples")
        elif kind == b"IDAT":
            if ended_idat or color == 3 and palette_size is None:
                raise ValueError("Invalid PNG image data order")
            compressed.extend(payload)
        elif kind == b"IEND":
            if length or b"IDAT" not in seen or end != len(data):
                raise ValueError("Invalid PNG ending or trailing data")
        if kind in _KEEP:
            chunks.append(_chunk(kind, payload))
        seen.add(kind)
        position = end
    if b"IEND" not in seen:
        raise ValueError("Missing PNG ending")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    passes = ((0, 0, 1, 1),) if not interlace else ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
    rows = []
    for x, y, dx, dy in passes:
        columns = max(0, (width - x + dx - 1) // dx)
        count = max(0, (height - y + dy - 1) // dy)
        if columns and count:
            rows.append((count, (columns * depth * channels + 7) // 8 + 1))
    expected = sum(count * size for count, size in rows)
    if expected > _MAX_BYTES:
        raise ValueError("PNG decoded image is too large")
    pixels = _inflate(bytes(compressed), expected)
    if len(pixels) != expected:
        raise ValueError("PNG scanline length differs from dimensions")
    position = 0
    for count, size in rows:
        for _ in range(count):
            if pixels[position] > 4:
                raise ValueError("Invalid PNG row filter")
            position += size
    return _SIGNATURE + b"".join(chunks)


def _gallery(document):
    sections = []
    for index, review in enumerate(document["reviews"]):
        rows = []
        for phase in PHASES:
            cells = []
            for camera in CAMERAS:
                path = review["images"][phase][camera]
                safe_path = html.escape(path, quote=True) if path else None
                content = f'<a href="{safe_path}" target="_blank" rel="noopener"><img src="{safe_path}" alt="{phase} {camera} view"></a>' if path else '<div class="missing">Image unavailable</div>'
                cells.append(f"<td>{content}</td>")
            rows.append(f'<tr><th scope="row">{phase.title()}</th>{"".join(cells)}</tr>')
        controls = []
        for phase in PHASES:
            fields = []
            for criterion in CRITERIA:
                options = '<option value="">Unscored</option>' + ''.join(f'<option value="{score}">{score}</option>' for score in range(1, 6))
                fields.append(f'<label>{criterion.title()} <select data-index="{index}" data-phase="{phase}" data-criterion="{criterion}">{options}</select></label>')
            controls.append(f'<fieldset><legend>{phase.title()} scores</legend>{"".join(fields)}<p>Editability: unassessed; requires later native inspection.</p></fieldset>')
        sections.append(f'<section><h2>{review["label"]}</h2><table><thead><tr><th>Stage</th><th>Hero</th><th>Reverse</th><th>Detail</th></tr></thead><tbody>{"".join(rows)}</tbody></table><div class="scores">{"".join(controls)}</div></section>')
    data = json.dumps(document, allow_nan=False).replace("<", "\\u003c")
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Artist image review</title><style>
body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1500px;padding:0 1rem;background:#17191e;color:#eee}
section{padding:1rem;margin:2rem 0;background:#242730;border-radius:8px}table{width:100%;table-layout:fixed;border-collapse:collapse}
th:first-child{width:4rem}td,th{padding:.4rem}img{width:100%;height:260px;object-fit:contain;background:#101216}
.missing{height:260px;display:grid;place-items:center;background:#101216;color:#bbb}.scores{display:flex;gap:1rem;flex-wrap:wrap}
fieldset{flex:1;min-width:260px}label{display:inline-block;padding:.5rem}select,button{font:inherit;padding:.4rem}button{cursor:pointer}
</style></head><body><h1>Artist image review</h1>
<p>Review the same three camera views before and after each revision. Score composition, proportion, materials and lighting from 1 to 5.</p>
<p>1: substantial rework; 2: major cleanup; 3: moderate cleanup; <strong>4: usable with minor cleanup</strong>; 5: ready to use.</p>
<p>Editability remains unassessed until later native inspection. Leave unavailable or unassessed criteria unscored. Missing images do not imply a score.</p>
<button id="export" type="button">Download scores JSON</button><p>Scores stay in this page until downloaded. Reloading clears entered scores.</p>
''' + ('<p><strong>Export smoke test only.</strong> These repeated fixture images establish neither independent creative performance nor artist acceptance.</p>' if document.get('scope') == 'smoke' else '') + "".join(sections) + '''<script>
const review = ''' + data + ''';
document.querySelectorAll('select').forEach(field => field.addEventListener('change', () => {
  review.reviews[Number(field.dataset.index)].scores[field.dataset.phase][field.dataset.criterion] = field.value === '' ? null : Number(field.value);
}));
document.getElementById('export').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2) + '\\n'], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'artist-scores.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
</script></body></html>
'''


def export_review(entries, out, private_receipt, *, scope="trial"):
    """Create a new public gallery plus a separate new private mapping receipt.

    Exactly six unique run IDs are required. Omitted/None pre/post camera paths,
    unreadable files and invalid PNGs retain their review position as missing
    cells. Entry/schema errors fail before publication. The return value contains
    local paths and is private; distribute only the output directory.
    """
    if scope not in {"trial", "smoke"}:
        raise ValueError("Review scope must be trial or smoke")
    if not isinstance(entries, list) or len(entries) != 6:
        raise ValueError("Exactly six review entries are required")
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("run_id"), str) or not entry["run_id"].strip():
            raise ValueError("Every entry requires a nonempty run_id")
        if entry["run_id"] in ids:
            raise ValueError("Duplicate run_id")
        ids.add(entry["run_id"])
        for phase in PHASES:
            views = entry.get(phase)
            if views is not None and (not isinstance(views, dict) or set(views) - set(CAMERAS)):
                raise ValueError("Invalid review camera map")
            for source in (views or {}).values():
                if source is not None and not isinstance(source, (str, Path)):
                    raise ValueError("Camera paths must be strings, Paths or None")
    out, private_receipt = Path(out).resolve(), Path(private_receipt).resolve()
    if private_receipt == out or out in private_receipt.parents:
        raise ValueError("Private receipt must be outside public output")
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    if private_receipt.exists() or private_receipt.is_symlink():
        raise FileExistsError(private_receipt)
    shuffled = list(entries)
    secrets.SystemRandom().shuffle(shuffled)
    document = {"schema": "dcc.artist-review.v1", "scope": scope, "scale": {"1": "substantial rework", "2": "major cleanup", "3": "moderate cleanup", "4": "usable with minor cleanup", "5": "ready to use"}, "reviews": []}
    receipt = {"schema": "dcc.private-artist-review.v1", "reviews": []}
    files, labels = {}, set()
    for entry in shuffled:
        label = "R-" + secrets.token_hex(8)
        while label in labels:
            label = "R-" + secrets.token_hex(8)
        labels.add(label)
        scores = {criterion: None for criterion in (*CRITERIA, "editability")}
        review = {"label": label, "images": {}, "scores": {phase: copy.copy(scores) for phase in PHASES}, "editability_status": "unassessed; requires later native inspection"}
        mapping = {"label": label, "run_id": entry["run_id"], "images": {}}
        for phase in PHASES:
            review["images"][phase], mapping["images"][phase] = {}, {}
            for camera in CAMERAS:
                source = (entry.get(phase) or {}).get(camera)
                detail = {"source": str(source) if source is not None else None, "status": "missing"}
                destination = None
                if source is not None:
                    try:
                        with Path(source).open("rb") as stream:
                            data = stream.read(_MAX_BYTES + 1)
                        clean = _strip_png_metadata(data)
                    except (OSError, ValueError) as exc:
                        detail["reason"] = str(exc)
                    else:
                        destination = f"images/{label}-{phase}-{camera}.png"
                        files[destination] = clean
                        detail["status"] = "available"
                        detail["source_sha256"] = hashlib.sha256(data).hexdigest()
                        detail["published_sha256"] = hashlib.sha256(clean).hexdigest()
                review["images"][phase][camera] = destination
                mapping["images"][phase][camera] = detail
        document["reviews"].append(review)
        receipt["reviews"].append(mapping)
    # Reserve both names exclusively before publishing any public file. Failure
    # leaves an explicit, empty reserved output rather than replacing evidence.
    out.mkdir(parents=True, exist_ok=False)
    write_json(private_receipt, receipt)
    (out / "images").mkdir()
    for name, data in files.items():
        with (out / name).open("xb") as stream:
            stream.write(data)
    write_json(out / "scores.json", document)
    with (out / "index.html").open("x", encoding="utf-8") as stream:
        stream.write(_gallery(document))
    return {"gallery": str(out / "index.html"), "scores": str(out / "scores.json"), "private_receipt": str(private_receipt)}
