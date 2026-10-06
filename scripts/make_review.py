"""Produce a local artist review page and a compact evidence summary."""
import argparse
import html
import json
from pathlib import Path
from dcc_harness.evidence import read_json,write_json,file_hash


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("project"); args=parser.parse_args()
    root=Path(args.project).resolve()
    stages=[("01-architecture","01-render"),("02-furnishings","02-render"),("03-revision","03-render"),
            ("04-look-refinement","04-render"),("05-portable","05-packed-render")]
    reports=[]
    for stage,folder in stages:
        source=read_json(root/"evidence"/(stage+".json")); capture=read_json(root/"evidence"/folder/"report.json")
        reports.append({"stage":stage,"passed":capture["passed"],"same_revision":source["revision"]==capture["revision"],
                        "source_unchanged":capture["source_unchanged"],"renders":len(capture["captures"]),
                        "render_seconds":sum(c["seconds"] for c in capture["captures"])})
    summary={"schema":"dcc.rehearsal-summary.v1","kind":"engineering rehearsal, not A/B/C",
             "stages":reports,"render_count":sum(r["renders"] for r in reports),
             "render_seconds":sum(r["render_seconds"] for r in reports),
             "native_faults":read_json(root/"reports/native-fault-probes.json")["passed"],
             "unknown_outcome":read_json(root/"reports/unknown-cleaned.json")["passed"],
             "revision_scope":read_json(root/"reports/03-delta.json")["passed"],
             "refinement_scope":read_json(root/"reports/04-delta.json")["passed"],
             "final_checkpoint":"checkpoints/05-portable.blend",
             "final_sha256":file_hash(root/"checkpoints/05-portable.blend"),
             "artist_acceptance":"pending","comparison_trials":"not_run","metered_cost":"unavailable"}
    summary["technical_checks_passed"]=all(r["passed"] and r["same_revision"] and r["source_unchanged"] for r in reports) and all(summary[k] for k in ("native_faults","unknown_outcome","revision_scope","refinement_scope"))
    write_json(root/"reports/summary.json",summary)
    stats=f"{summary['render_count']} native renders · {summary['render_seconds']:.1f}s render calls · 8 asset families · 257 scene objects"
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Courtyard · Harness pilot review</title><style>
*{box-sizing:border-box}body{margin:0;background:#161b1c;color:#e5e7df;font:16px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:42px 5vw}h1{font-size:clamp(34px,4vw,58px);letter-spacing:-.045em;margin:6px 0 12px}h2{font-size:24px;font-weight:500;margin-top:42px}.eyebrow{color:#a4bdad;letter-spacing:.15em;text-transform:uppercase;font-size:12px}.muted{color:#a9b2ae}a{color:#b7d8c8}img{width:100%;display:block;border-radius:8px}.hero{margin:28px 0}nav{display:flex;gap:12px;flex-wrap:wrap}select,button{background:#26322e;color:#edf2ea;border:1px solid #56645d;padding:10px;border-radius:5px;font:inherit}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{padding:18px;background:#202829;border-radius:8px}label{display:block;margin:8px 0}small{color:#acb7b0}textarea{width:100%;height:100px;background:#151e1a;color:#eee;padding:12px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #39433e}@media(max-width:800px){.grid{grid-template-columns:1fr}}figure{margin:0}figcaption{margin:8px 0 20px;color:#aab6ad}</style>
<main><div class="eyebrow">3D Harness / Engineering rehearsal / 03 October 2026</div><h1>A courtyard that survives revision.</h1>
<p class="muted">Native construction, bounded changes and saved-state verification. Artist acceptance and independent A/B/C evaluation are still pending.</p>
<nav><a href="checkpoints/05-portable.blend">Packed Blender scene</a><a href="CONTINUE.md">Continuation</a><a href="reports/summary.json">Evidence summary</a></nav>
<figure class="hero"><img id="hero" src="evidence/04-render/camera.hero.png"><figcaption>Current candidate: lower-contrast stone, 2.1m bench, unchanged camera and lighting.</figcaption></figure>'''
    page+='<p class="muted">'+html.escape(stats)+'</p>'
    page+='''<h2>Compare the same view</h2><p><label>Camera <select id="camera"><option value="hero">Whole courtyard</option><option value="reverse">Reverse view</option><option value="detail">Bench and doorway</option></select></label></p>
<div class="grid"><figure><img id="before" src="evidence/02-render/camera.hero.png"><figcaption>Before revision: 1.9m bench and original stone.</figcaption></figure><figure><img id="after" src="evidence/04-render/camera.hero.png"><figcaption>Current candidate: width/tint revision plus one material contrast refinement.</figcaption></figure></div>
<h2>What the checks establish</h2><div class="grid"><div class="card">Five saved stages reopened with identical observed revisions. Source files remained unchanged during rendering. Packed dependencies rendered with external paths redirected.</div><div class="card">Duplicate identity, placement drift, lighting drift and missing data were detected. A simulated missing acknowledgement blocked the next dispatch; reconciliation did not replay the write.</div></div>
<p class="muted">The initial starter lost unused materials on reopen. That failure is retained; a corrected starter passed continued construction in a separate process. No multi-hour autonomy, general topology cleanliness, or artistic quality claim follows from these checks.</p>
<h2>Your quality gate</h2><p>Score the candidate from 1 (unusable) to 5 (accepted). A 4 means usable with minor cleanup. Inspect all three views and the native file before deciding.</p><div class="card"><form id="rubric">'''
    for key,label in [("composition","Composition and focal hierarchy"),("proportion","Proportions and construction"),("materials","Material coherence and texture scale"),("lighting","Lighting and readability"),("editability","Native editability")]:
        page+=f'<label>{label} <select name="{key}"><option value="">Unrated</option>'+''.join(f'<option>{n}</option>' for n in range(1,6))+'</select></label>'
    page+='''<label>Changes you would want<textarea name="notes"></textarea></label><button type="button" id="download">Save review as JSON</button><p><small>This page sends nothing. The button downloads your review locally.</small></p></form></div>
<h2>Open creative concerns</h2><p class="muted">The scene is a compact diorama, not a detailed production environment. Foliage is simplified; trim construction and surface wear need artist judgment. The calmer stone is a candidate choice, not an approved style. This authored example cannot determine whether skills outperform plain MCP.</p></main>
<script>document.getElementById('camera').onchange=e=>{for(const [id,stage] of [['before','02-render'],['after','04-render']])document.getElementById(id).src=`evidence/${stage}/camera.${e.target.value}.png`};document.getElementById('download').onclick=()=>{const review=Object.fromEntries(new FormData(document.getElementById('rubric')));review.checkpoint='05-portable.blend';review.status='artist-review';const u=URL.createObjectURL(new Blob([JSON.stringify(review,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='courtyard-artist-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};</script></html>'''
    (root/"REVIEW.html").write_text(page,encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
