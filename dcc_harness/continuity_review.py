"""Anonymous four-workflow, four-stage image review; no native scene access.

Only distribute public_folder. The separate receipt retains source identities
and export diagnostics. Missing images remain explicit slots, never exclusions.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import secrets

from .blind import _absolute, _write_json, _write_text
from .blind_review import _MAX_BYTES, _strip_png_metadata


VIEWS = ("hero", "reverse", "detail", "overview", "garden", "forecourt")
STAGES = ("s01", "s02", "s03", "s04")
CRITERIA = ("composition", "proportion", "materials", "lighting", "coherence")
STAGE_DESCRIPTIONS = {
    "s01": {"title": "1 · Connected areas and furniture", "request":
        "Add the new connected areas and furniture while preserving the existing environment."},
    "s02": {"title": "2 · Garden props", "request":
        "Develop the garden with props that share the environment's materials, scale and visual direction."},
    "s03": {"title": "3 · Shared materials and proportions", "request":
        "Make the shared stone warmer and widen the table and stools. Preserve the artist's stool placement and unrelated work."},
    "s04": {"title": "4 · Delivery and final details", "request":
        "Resolve the interrupted delivery so exactly one plaque remains. Add lanterns and revise the sign while preserving earlier decisions."},
}
SCALE = {"1": "substantial rework", "2": "major cleanup", "3": "moderate cleanup",
         "4": "usable with minor cleanup", "5": "ready to use"}
_MAX_EXPORT_BYTES = 512 * 1024 * 1024


def _path(value, label):
    if not isinstance(value, (str, Path)) or isinstance(value, str) and not value.strip():
        raise ValueError(f"{label} must be a nonempty path string or Path")
    return _absolute(value)


def _views(value):
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - set(VIEWS):
        raise ValueError("Invalid six-view image map")
    return {view: _path(source, "Image source") if source is not None else None
            for view, source in value.items()}


def _capture(views, prefix, files):
    images, details = {}, {}
    for view in VIEWS:
        source = views.get(view)
        detail = {"source": str(source) if source is not None else None,
                  "status": "missing", "source_sha256": None, "published_sha256": None}
        published = None
        if source is not None:
            try:
                if not source.is_file():
                    raise ValueError("Image source is missing or not a regular file")
                with source.open("rb") as stream:
                    data = stream.read(_MAX_BYTES + 1)
                # A full bounded read receives a source digest even when the
                # PNG fails validation. Oversized files have no misleading hash.
                if len(data) <= _MAX_BYTES:
                    detail["source_sha256"] = hashlib.sha256(data).hexdigest()
                clean = _strip_png_metadata(data)
            except (OSError, ValueError) as exc:
                detail["reason"] = str(exc)
            else:
                if sum(map(len, files.values())) + len(clean) > _MAX_EXPORT_BYTES:
                    raise ValueError("Combined PNG export exceeds the supported memory budget")
                published = f"images/{prefix}-{view}.png"
                files[published] = clean
                detail.update(status="available", published=published,
                              published_sha256=hashlib.sha256(clean).hexdigest())
        images[view], details[view] = published, detail
    return images, details


def _image_grid(images, description):
    cells = []
    for view in VIEWS:
        image = images[view]
        if image is None:
            content = '<div class="missing">Image unavailable</div>'
        else:
            safe = html.escape(image, quote=True)
            alt = html.escape(f"{description}: {view} view", quote=True)
            content = f'<a href="{safe}" target="_blank" rel="noopener"><img src="{safe}" alt="{alt}" loading="lazy"></a>'
        cells.append(f'<figure>{content}<figcaption>{view.title()}</figcaption></figure>')
    return '<div class="views">' + "".join(cells) + '</div>'


def _gallery(document):
    sections = []
    baseline = document["baseline"]
    if baseline is not None:
        sections.append('<section id="baseline"><h2>Shared starting environment</h2><p>This is the common starting point for every entry.</p>'
                        + _image_grid(baseline["images"], "Shared baseline") + '</section>')
    for index, review in enumerate(document["reviews"]):
        rows = []
        for stage in STAGES:
            description = STAGE_DESCRIPTIONS[stage]
            controls = []
            for criterion in CRITERIA:
                options = '<option value="">Unscored</option>' + ''.join(
                    f'<option value="{score}">{score}</option>' for score in range(1, 6))
                controls.append(f'<label>{criterion.title()} <select data-index="{index}" data-stage="{stage}" data-criterion="{criterion}">{options}</select></label>')
            rows.append(f'<article><h3>{description["title"]}</h3><p>{description["request"]}</p>'
                        + _image_grid(review["images"][stage], f'{review["label"]} {description["title"]}')
                        + f'<fieldset><legend>Visual scores · stage {stage[-1]}</legend>{"".join(controls)}</fieldset></article>')
        label = review["label"]
        sections.append(f'<section id="{label}"><h2>{label}</h2>{"".join(rows)}'
                        + f'<label class="notes">Continuity observations<textarea data-index="{index}" rows="3" placeholder="Describe visible changes, strengths or drift across stages."></textarea></label>'
                        + '<p>Native editability: unassessed. Recovery behavior cannot be established from still images.</p></section>')
    navigation = ('<a href="#baseline">Starting point</a>' if baseline is not None else '') + ''.join(
        f'<a href="#{review["label"]}">{review["label"]}</a>' for review in document["reviews"])
    data = json.dumps(document, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Environment continuity review</title><style>
*{box-sizing:border-box}body{font:16px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:1600px;padding:0 1rem;background:#17191e;color:#eee}
a{color:#b5d8ff}nav{display:flex;gap:1rem;flex-wrap:wrap;padding:1rem;background:#242730;border-radius:8px}h2{overflow-wrap:anywhere}h3{margin-bottom:.4rem}
section{padding:1.2rem;margin:2rem 0;background:#242730;border-radius:8px}article{border-top:1px solid #52565f;padding:1rem 0 1.5rem}
.views{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem}figure{margin:0}figcaption{padding:.25rem .2rem;color:#c8cbd2}
img,.missing{width:100%;aspect-ratio:16/9;object-fit:contain;background:#101216}img{display:block}.missing{display:grid;place-items:center;color:#bbb}
fieldset{margin-top:1rem;border:1px solid #777}label{display:inline-block;margin:.35rem .65rem .35rem 0}select,button,textarea{font:inherit;padding:.45rem}
button{cursor:pointer}.notes{display:block}textarea{display:block;width:100%;max-width:900px;margin-top:.4rem}a:focus-visible,button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #e8c56a;outline-offset:3px}
@media(max-width:800px){.views{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:480px){.views{grid-template-columns:1fr}body{padding:0 .5rem}section{padding:.8rem}}
</style></head><body><h1>Environment continuity review</h1>
<p>Compare four anonymous environments as each develops through the same four stages. The requested changes below describe the task; they are not claims that an entry completed it.</p>
<p>Score visible composition, proportion, materials, lighting and coherence from 1 to 5. Coherence concerns how the environment's parts fit together. Use the notes to describe visible continuity or drift across stages.</p>
<p>1: substantial rework; 2: major cleanup; 3: moderate cleanup; <strong>4: usable with minor cleanup</strong>; 5: ready to use.</p>
<p>Leave unavailable or unassessed criteria unscored. Missing images do not imply a score. Still images do not establish native editability or successful recovery from an interrupted operation.</p>
<button id="export" type="button">Download scores JSON</button><p>Scores stay in this page until downloaded. Reloading clears entered scores. Click any image to open its full size.</p>
<nav aria-label="Review entries">''' + navigation + '</nav>' + ''.join(sections) + '''<script>
const review = ''' + data + ''';
document.querySelectorAll('select').forEach(field => field.addEventListener('change', () => {
  review.reviews[Number(field.dataset.index)].scores[field.dataset.stage][field.dataset.criterion] = field.value === '' ? null : Number(field.value);
}));
document.querySelectorAll('textarea').forEach(field => field.addEventListener('input', () => {
  review.reviews[Number(field.dataset.index)].continuity_notes = field.value;
}));
document.getElementById('export').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2) + '\\n'], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'continuity-scores.json';
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
</script></body></html>
'''


def export_review(entries, public_folder, private_receipt, baseline=None):
    """Publish four randomized anonymous entries and an optional common baseline.

    entries is a list of four unique {run_id, stages} records. stages maps
    s01..s04 to six-view maps. Omitted/None stages or views, unreadable sources and
    invalid PNGs stay as unavailable slots. Unsupported fields/types and unsafe
    paths fail before publication. Existing or partial destinations are refused.

    Native validity, artistic acceptance and recovery are not graded. Pixel and
    color data are preserved by the existing PNG sanitizer; descriptive metadata
    is stripped. Burned-in scene content is not analyzed or redacted.
    """
    if not isinstance(entries, list) or len(entries) != 4:
        raise ValueError("Exactly four review entries are required")
    ids, validated = set(), []
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) - {"run_id", "stages"}
                or not isinstance(entry.get("run_id"), str) or not entry["run_id"].strip()):
            raise ValueError("Every entry requires a nonempty run_id and only the supported stages field")
        if entry["run_id"] in ids:
            raise ValueError("Duplicate run_id")
        ids.add(entry["run_id"])
        stages = entry.get("stages")
        if stages is not None and (not isinstance(stages, dict) or set(stages) - set(STAGES)):
            raise ValueError("Invalid four-stage map")
        validated.append({"run_id": entry["run_id"],
                          "stages": {stage: _views((stages or {}).get(stage)) for stage in STAGES}})
    baseline_views = _views(baseline) if baseline is not None else None
    out, private = _path(public_folder, "Public folder"), _path(private_receipt, "Private receipt")
    if private.is_relative_to(out) or out.is_relative_to(private):
        raise ValueError("Private receipt must be outside and separate from public output")
    if out.exists():
        raise FileExistsError(out)
    if private.exists():
        raise FileExistsError(private)
    # Build and validate the entire export in memory before reserving outputs.
    secrets.SystemRandom().shuffle(validated)
    document = {"schema": "dcc.continuity-artist-review.v1", "scale": dict(SCALE),
                "stage_descriptions": STAGE_DESCRIPTIONS, "baseline": None, "reviews": []}
    receipt = {"schema": "dcc.private-continuity-review.v1", "baseline": None, "reviews": [],
               "limitations": "Image-only export; no native/artistic grades or burned-in identifier detection."}
    files, labels = {}, set()
    if baseline_views is not None:
        images, details = _capture(baseline_views, "baseline", files)
        document["baseline"], receipt["baseline"] = {"images": images}, {"images": details}
    for entry in validated:
        label = "R-" + secrets.token_hex(8)
        while label in labels:
            label = "R-" + secrets.token_hex(8)
        labels.add(label)
        review = {"label": label, "images": {}, "scores": {}, "continuity_notes": "",
                  "editability_status": "unassessed; requires native inspection"}
        mapping = {"label": label, "run_id": entry["run_id"], "images": {}}
        for stage in STAGES:
            images, details = _capture(entry["stages"][stage], f"{label}-{stage}", files)
            review["images"][stage], mapping["images"][stage] = images, details
            review["scores"][stage] = {criterion: None for criterion in (*CRITERIA, "editability")}
        document["reviews"].append(review)
        receipt["reviews"].append(mapping)
    gallery = _gallery(document)
    # A failed publication is left visible for reconciliation, never overwritten
    # or silently retried. These reservations do not claim cross-file atomicity.
    out.mkdir(parents=True, exist_ok=False)
    _write_json(private, receipt)
    (out / "images").mkdir()
    for name, data in files.items():
        with (out / name).open("xb") as stream:
            stream.write(data)
    _write_json(out / "scores.json", document)
    _write_text(out / "index.html", gallery)
    return {"gallery": str(out / "index.html"), "scores": str(out / "scores.json"),
            "private_receipt": str(private), "trial_slots": 96,
            "baseline_slots": 6 if baseline_views is not None else 0,
            "available_images": len(files)}
