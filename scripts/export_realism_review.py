"""Create a neutral image review; private mapping stays outside the artist ZIP."""
import argparse,hashlib,html,json,random,secrets,sys,zipfile
from pathlib import Path
from html.parser import HTMLParser
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.blind_review import _strip_png_metadata
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
root=Path(a.root).resolve();out=Path(a.out).resolve();out.mkdir(exist_ok=False);(out/'images').mkdir()
runs=list(read_json(root/'private/manifest.json')['runs']);random.SystemRandom().shuffle(runs)
mapping={};entries=[];audit=[]
for run in runs:
    label='E-'+secrets.token_hex(4);mapping[label]=run['id'];phases={}
    for stage in ('pre','post'):
        folder=root/'private/completed'/run['id']/stage/'evaluation';images={}
        report=read_json(folder/'report.json') if (folder/'report.json').is_file() else None
        receipts={c['view']:c for c in report['captures']} if report else {}
        for view in ('hero','context','detail'):
            source=folder/(view+'.png');name=f'images/{label}-{stage}-{view}.png'
            if not source.is_file():images[view]=None;continue
            if view not in receipts or file_hash(source)!=receipts[view]['sha256']:raise ValueError('Unbound capture '+str(source))
            clean=_strip_png_metadata(source.read_bytes());target=out/name;target.write_bytes(clean)
            with Image.open(source) as x,Image.open(target) as y:
                assert x.mode==y.mode and x.size==y.size and x.tobytes()==y.tobytes()
            images[view]=name;audit.append({'source':str(source),'source_sha256':file_hash(source),'published':name,'published_sha256':file_hash(target),'decoded_pixels_equal':True})
        phases[stage]=images
    entries.append({'id':label,'phases':phases})
write_json(out/'review.json',{'schema':'dcc.realism.image_review.v1','entries':entries,'limits':'Anonymous image-only assessment; missing captures remain missing. No native or artist acceptance is implied.'})
write_json(root/'private'/('mapping-'+out.name+'.json'),{'mapping':mapping,'audit':audit})
style='body{margin:30px auto;max-width:1600px;padding:0 24px;background:#172126;color:#edf0e9;font:16px/1.5 system-ui}h1{font-size:32px}a{color:#b6d9e5}.views{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}figure{margin:0}img{width:100%;height:auto}section{border-top:1px solid #526169;margin-top:36px}figcaption{padding:6px 0}.missing{padding:70px 10px;background:#343f43}p{max-width:88ch}@media(max-width:900px){.views{grid-template-columns:1fr}}'
parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Realistic potting shed comparison</title><style>'+style+'</style><body><h1>Realistic potting shed comparison</h1><p>Four independent versions, each followed by a fresh-context revision. Review the native renders for believable construction, materials, planting, purposeful arrangement and consistency. Pre is the initial build; post widens the bench and makes shared metal less polished. The camera and lighting brief is common. Click for full-size images. Missing images are retained as missing.</p>']
for entry in entries:
    parts.append('<section><h2>'+entry['id']+'</h2>')
    for stage in ('pre','post'):
        parts.append('<h3>'+stage.title()+'</h3><div class="views">')
        for view,path in entry['phases'][stage].items():
            content=f'<a href="{path}"><img src="{path}" alt="{entry["id"]} {stage} {view}" loading="lazy"></a>' if path else '<div class="missing">Image unavailable</div>'
            parts.append('<figure>'+content+'<figcaption>'+view.title()+'</figcaption></figure>')
        parts.append('</div>')
    parts.append('</section>')
parts.append('<p>Image-only review; technical checks, method labels and native editability remain separate.</p></body></html>')
(out/'index.html').write_text('\n'.join(parts),encoding='utf-8')
(out/'README.md').write_text('''# Anonymous realism comparison

Open index.html. Rank final outputs, allowing ties, against a realistic architectural/environment still brief. Score real scale/construction, material scale/response, vegetation/contact, purposeful composition/activity, and consistency across views. 1 unusable, 2 blockout, 3 coherent draft needing substantial refinement, 4 usable with minor cleanup, 5 finished. Do not reward object count alone. Compare pre/post for intended bench widening and less polished shared metal, plus unintended changes. Image scores cannot establish native topology, exact dimensions, editability or method superiority.

All images are direct Blender renders at 1280x720, 48 Cycles samples, seed 0; no AI image replacement or postprocessing. Descriptive PNG metadata is removed with encoded pixels/color semantics preserved and decoded pixels verified identical. The shared HDRI, fern model and material scans are from Poly Haven, CC0. Private reference photographs are excluded from this archive. Source/evaluator/authoring metadata and mapping remain in the coordinator's evidence directory.
''',encoding='utf-8')
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('href','src'):assert (out/value).is_file(),value
Links().feed((out/'index.html').read_text(encoding='utf-8'))
files={f.relative_to(out).as_posix():file_hash(f) for f in out.rglob('*') if f.is_file()};write_json(out/'manifest.json',{'files':files})
archive=out.with_suffix('.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(out.rglob('*')):
        if f.is_file():z.write(f,f.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,sha in files.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha
write_json(root/'private'/('integrity-'+out.name+'.json'),{'images':len(audit),'slots':24,'files':len(files)+1,'zip_sha256':file_hash(archive),'archive_bytes':archive.stat().st_size,'static_links_passed':True,'decoded_pixels_equal':True,'browser_interaction_tested':False})
print('EXPORTED_REALISM_REVIEW',len(audit),archive)
