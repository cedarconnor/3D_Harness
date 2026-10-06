"""Create a new, owned courtyard quality fixture without changing old trials."""
import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcc_harness.evidence import file_hash, read_json, write_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root")
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
root = Path(args.root).resolve()
root.mkdir(parents=True, exist_ok=False)
(root / "unchanged").mkdir()
(root / "references").mkdir()
trial = repo / "runs/continuity-round-2026-10-04"
source = trial / "private/accepted/t-c335fd0d71f6/s04/scene.blend"
shutil.copyfile(source, root / "unchanged/scene.blend")
for name, view in (("composition", "overview"), ("construction", "garden"), ("palette", "hero")):
    shutil.copyfile(trial / f"review/images/R-0d7440a27c13abf9-s04-{view}.png", root / f"references/{name}.png")

references = [{"id": name, "file": {"path": f"references/{name}.png", "sha256": file_hash(root / f"references/{name}.png")},
               "role": "construction" if name == "construction" else "mood", "intent": intent}
              for name, intent in (("composition", "Preserve the inherited arched entry as the focal feature; change the extension layout."),
                                   ("construction", "Keep the preferred fine masonry and timber joinery; reduce canopy dominance."),
                                   ("palette", "Retain muted stone, terracotta, timber and teal; no new material vocabulary."))]
targets = [{"id": name, "intent": intent, "reference_ids": refs} for name, intent, refs in (
    ("hierarchy", "Lower pergola dominance while preserving original entrance silhouette.", ["composition", "construction"]),
    ("activity", "Group potting furniture and pots into a readable working area instead of an evenly spaced display.", ["composition"]),
    ("craft", "Preserve joinery, material assignments and usable tabletop arrangement.", ["construction", "palette"]))]
render = {"engine": "CYCLES", "resolution": [960, 540], "samples": 32, "seed": 0, "denoising": True}
views = [{"id": name, "purpose": purpose, "camera": cam, "render": render} for name, purpose, cam in (
    ("overview", "whole", {"object_id": "camera.overview"}),
    ("garden", "detail", {"object_id": "camera.garden"}),
    ("worktop", "detail", {"anchor_id": "ext.table.top", "offset": [2.2, -2.8, 2.4], "lens": 48}))]
old = read_json(trial / "private/accepted/t-c335fd0d71f6/s04/observation.json")
prefixes = ["ext.planter.", "ext.stool.", "ext.table.", "ext.tool.", "ext.plaque", "ext.pergola."]
contract = {"schema": "dcc.continuity.contract.v1", "spec": {"schema": "dcc.spec.v1",
            "required": {iid: {"type": obj["type"], "asset_id": obj["asset_id"], "material_ids": obj["material_ids"]}
                         for iid, obj in old["objects"].items() if obj["type"] == "MESH"},
            "units": old["scene"]["units"]},
            "allowed_object_prefixes": {p: ["matrix_world", "bounds", "dimensions"] for p in prefixes},
            "allowed_new_prefixes": []}
design = {"brief": "A bounded layout study, not final environment polish. Compare two activity layouts and lighter pergola proportions against unchanged. New scope permits extension transforms, including moving the earlier artist-offset stool as part of a new layout. Preserve original courtyard, all mesh sources, shared materials, cameras, lighting and render settings. Two authored candidates; no replacement of failed outcomes.",
          "references": references, "targets": targets, "views": views, "contract": contract,
          "methods": {"assembly": "Translate each named asset assembly rigidly, including tabletop props/plaque; preserve stable IDs and mesh sharing.",
                      "timber": "Scale the entire pergola vertically about ground so joints stay connected; this is a composition study, not structural engineering.",
                      "surface": "Reuse all current material graphs and bindings without edits.",
                      "references": "Existing accepted-style scene captures are the reference board for this bounded layout test; not external dimension evidence."},
          "reservations": [{"id": "arrival_gap", "bounds": [[1.2, -3.6, .02], [2.4, -1.9, 2]],
                            "obstacle_prefixes": ["ext.planter.", "ext.stool.", "ext.table.", "ext.tool."],
                            "exempt_ids": [], "tolerance": .00001}]}
write_json(root / "design.json", design)
write_json(root / "source.json", {"path": str(source), "sha256": file_hash(source),
                                 "live_mcp": "unreachable; background processes only", "artist_acceptance": "not_requested"})
print(root)
