"""Bind a prepared design to saved candidates; build a local comparison page."""
import argparse
import html
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root")
parser.add_argument("candidates", nargs="+")
parser.add_argument("--package-root", help="Explicit independently qualified runtime; default is this checkout")
args = parser.parse_args()
sys.path.insert(0, args.package_root or str(Path(__file__).resolve().parents[1]))
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.quality import audit
root = Path(args.root).resolve()


def ref(path):
    return {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}


design = read_json(root / "design.json")
spatial = 'visibility_contract' in design
spec = {"schema": "dcc.quality.round.v2" if spatial else "dcc.quality.round.v1", "design": ref(root / "design.json"), **design,
        "candidates": [{"id": name, "checkpoint": ref(root / name / "scene.blend"),
                        "observation": ref(root / name / "observation.json"), "renders": ref(root / name / "renders.json")}
                       for name in args.candidates]}
if spatial:
    for candidate in spec['candidates']:
        candidate['visibility'] = ref(root / candidate['id'] / 'visibility.json')
write_json(root / "round.json", spec)
report = audit(root / "round.json")
write_json(root / "audit.json", report)
rows = []
for view in spec["views"]:
    cells = []
    for candidate in spec["candidates"]:
        receipt = read_json(root / candidate["renders"]["path"])
        image = receipt["images"][view["id"]]["path"]
        name = html.escape(candidate["id"])
        status = "Native checks pass" if report["candidates"][candidate["id"]]["eligible"] else "Gate failed — inspect audit"
        cells.append(f'<figure><a href="{html.escape(image, quote=True)}"><img src="{html.escape(image, quote=True)}" alt="{name}: {html.escape(view["id"])}"></a><figcaption><b>{name}</b><br>{status}</figcaption></figure>')
    rows.append(f'<h2>{html.escape(view["id"])} · {view["purpose"]}</h2><div class="row">{"".join(cells)}</div>')
refs = ''
for r in spec['references']:
    path = html.escape(r['file']['path'], quote=True)
    media = f'<img src="{path}" alt="{html.escape(r["id"])}">' if Path(path).suffix.lower() in ('.png','.jpg','.jpeg','.webp') else f'<a href="{path}">{html.escape(r["id"])}</a>'
    refs += f'<figure>{media}<figcaption>{html.escape(r["intent"])}</figcaption></figure>'
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Courtyard layout study</title>
<style>body{background:#141a20;color:#e9e5dc;font:16px/1.5 system-ui;margin:0;padding:32px;max-width:1800px}h1{font-size:36px;margin-bottom:4px}p{max-width:1000px;color:#c7c7c5}h2{margin-top:40px;font-size:20px}.row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}figure{margin:0;background:#222b33;border-radius:8px;overflow:hidden}img{display:block;width:100%;height:auto}figcaption{padding:12px;font-size:14px}a{color:#94d9d0}@media(max-width:900px){.row{grid-template-columns:1fr}body{padding:16px}}</style>
<h1>Courtyard layout study</h1><p>Unchanged and two bounded composition edits. Same whole-scene and garden cameras, lighting and render settings. Worktop view follows the table with a fixed offset. Click an image for full resolution.</p><p>This is an authored engineering exercise, not a blind agent comparison or artist approval. Native gates check declared preservation and reserved space; they do not grade taste.</p>
<p><a href="audit.json">Native audit</a> · <a href="design.json">Saved design</a></p>
'''+''.join(rows)+'<h2>Reference board</h2><p>Each reference has a declared role and intent in the saved design. Construction guidance does not certify engineering safety.</p><div class="row">'+refs+'</div></html>'
(root / "index.html").write_text(page, encoding="utf-8")
print({k: {"eligible": v["eligible"], "failures": v["check"]["failures"], "conflicts": v["reserved_space"]["findings"], 'visibility':v.get('visibility',{}).get('results')}
       for k, v in report["candidates"].items()})
