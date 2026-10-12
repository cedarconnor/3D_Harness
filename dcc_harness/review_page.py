"""Before/after review page over two verified checkpoints, and import of what the reviewer exports.

Only the review-page and review-import commands import this module; it uses the standard library
only. The page is a local folder: index.html, page.json and the bound renders it shows. Building it
reads the project; importing an export commits a stage review and feedback notes through the
ordinary coordination commands, with request IDs derived from the export so a retry replays.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import uuid

from . import coordination as c, feedback
from .continuity import Continuity, _plain
from .evidence import compare, digest, file_hash, read_json, write_json
from .files import copy_verified
from .project import now

PLACEMENT = {'matrix_world', 'bounds'}
NAMESPACE = uuid.UUID('6b1d1a52-58a4-4c1e-9a4e-6f1f7d0a9c31')


def _center(record):
    bounds = record.get('bounds')
    if not isinstance(bounds, list) or len(bounds) != 2:
        return None
    return [(bounds[0][i] + bounds[1][i]) / 2 for i in range(3)]


def changes(before, after):
    """Objects added, removed, moved and changed between two observations, by stable ID."""
    delta = compare(before, after)
    fields = {}
    for change in delta['changes']:
        fields.setdefault((change['category'], change['id']), []).append(change['field'])
    result = {'added': [], 'removed': [], 'moved': [], 'changed': [], 'materials': [], 'scene': []}
    for (category, key), names in sorted(fields.items()):
        if category == 'scene':
            result['scene'].extend(names)
            continue
        if category == 'materials':
            change = 'added' if 'created' in names else 'removed' if 'deleted' in names else 'changed'
            result['materials'].append({'id': key, 'change': change, 'fields': sorted(set(names) - {'created', 'deleted'})})
            continue
        if 'created' in names:
            record = after['objects'][key]
            result['added'].append({'id': key, 'type': record.get('type'), 'asset_id': record.get('asset_id')})
        elif 'deleted' in names:
            record = before['objects'][key]
            result['removed'].append({'id': key, 'type': record.get('type'), 'asset_id': record.get('asset_id')})
        else:
            old, new = _center(before['objects'][key]), _center(after['objects'][key])
            distance = round(math.dist(old, new), 4) if old and new else None
            item = {'id': key, 'type': after['objects'][key].get('type'), 'fields': sorted(set(names)), 'distance': distance}
            (result['moved'] if set(names) <= PLACEMENT else result['changed']).append(item)
    touched = {key for category, key in fields if category == 'objects'}
    result['unchanged'] = len((before['objects'].keys() & after['objects'].keys()) - touched)
    result['scene'] = sorted(set(result['scene']))
    return result


def _check_views(source, entry, side):
    """A render folder bound to its checkpoint, whose images are contained files matching the receipt."""
    source = _plain(source)
    receipt = read_json(source / 'receipt.json')
    if receipt.get('schema') != 'dcc.quality.renders.v1' or receipt.get('checkpoint_sha256') != entry['checkpoint_sha256']:
        raise ValueError(f'Render receipt is not bound to the {side} checkpoint {entry["id"]}')
    settings = read_json(source / 'views.json')
    if digest(settings) != receipt['views_digest']:
        raise ValueError(f'The {side} view settings changed after their receipt')
    images = receipt.get('images')
    if not isinstance(images, dict) or any(not isinstance(i, dict) or not isinstance(i.get('sha256'), str) for i in images.values()):
        raise ValueError(f'The {side} render receipt does not list its images')
    files = {'receipt.json': file_hash(source / 'receipt.json'), 'views.json': file_hash(source / 'views.json')}
    for view, image in images.items():
        try:
            path = c.relative(source, image.get('path'))
        except ValueError:
            raise ValueError(f'The {side} image for {view} is not a contained relative path') from None
        if any(name != image['path'] and name.casefold() == image['path'].casefold() for name in files) or image['path'] in ('receipt.json', 'views.json'):
            raise ValueError(f'The {side} image for {view} collides with another file in the render folder')
        if files.setdefault(image['path'], image['sha256']) != image['sha256'] or file_hash(path) != image['sha256']:
            raise ValueError(f'The {side} image for {view} changed after its receipt')
    return source, receipt, settings, files


def _bind_views(checked, side, folder):
    """Copy a checked render folder into the page, each file new and verified against its hash."""
    source, receipt, settings, files = checked
    target = folder / 'renders' / side
    target.mkdir(parents=True)
    for name, sha in files.items():
        copy_verified(c.relative(source, name), c.relative(target, name), sha, f'The {side} render folder changed while it was copied')
    purposes = {}
    definition = settings.get('definition') if isinstance(settings, dict) else None
    if isinstance(definition, dict):
        purposes = {v['id']: v.get('purpose') for v in definition.get('views', []) if isinstance(v, dict) and 'id' in v}
    return {'digest': receipt['views_digest'], 'purposes': purposes,
            'images': {view: f'renders/{side}/{image["path"]}' for view, image in receipt['images'].items()},
            'receipt': {'path': f'renders/{side}/receipt.json', 'sha256': files['receipt.json']},
            'settings': {'path': f'renders/{side}/views.json', 'sha256': files['views.json']}}


def _entry(history, key, label):
    found = next((e for e in history if e['id'] == key), None)
    if found is None:
        raise ValueError(f'Unknown {label} checkpoint: {key}')
    return found


def _summary(entry):
    return {k: entry[k] for k in ('id', 'step_id', 'sequence', 'checkpoint_sha256')}


def build(root, out, *, from_id=None, to_id=None, before_views=None, after_views=None, blender=None, views=None, reopen=False):
    """Write a review page comparing two checkpoints; returns where it is and its digest."""
    if (before_views is None) != (after_views is None):
        raise ValueError('Give render folders for both sides, or neither')
    if reopen and blender is None:
        raise ValueError('Reopening the after checkpoint needs --blender')
    state = Continuity(root).status()
    history = state['task_history']
    after = _entry(history, to_id, 'after') if to_id else history[-1]
    if from_id:
        before = _entry(history, from_id, 'before')
    else:
        earlier = [e for e in history if e['sequence'] < after['sequence']]
        if not earlier:
            raise ValueError('Comparing needs two checkpoints; pass --from and --to')
        before = earlier[-1]
    if before['id'] == after['id']:
        raise ValueError('Comparing needs two checkpoints; pass --from and --to')
    # Given render folders are checked before anything is written.
    checked = {} if before_views is None else {'before': _check_views(before_views, before, 'before'),
                                               'after': _check_views(after_views, after, 'after')}
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    before_obs, after_obs = read_json(before['observation']), read_json(after['observation'])
    rendered = {}
    if checked:
        rendered = {side: _bind_views(checked[side], side, folder) for side in ('before', 'after')}
    elif blender is not None:
        from .render import render_file
        project = None if views is not None else root
        for side, entry in (('before', before), ('after', after)):
            render_file(entry['checkpoint'], folder / 'work' / side, blender, project=project, views=views)
            rendered[side] = _bind_views(_check_views(folder / 'work' / side, entry, side), side, folder)
    view_rows = []
    if rendered:
        ids = sorted(set(rendered['before']['images']) | set(rendered['after']['images']))
        purposes = {**rendered['before']['purposes'], **rendered['after']['purposes']}
        view_rows = [{'id': v, 'purpose': purposes.get(v), 'before': rendered['before']['images'].get(v),
                      'after': rendered['after']['images'].get(v)} for v in ids]
    events = c.read(root)
    notes = []
    for nid, item in (feedback.state(events, state).items() if events else []):
        note, anchor = item['note'], item['note']['anchor']
        render = anchor.get('render') or {}
        side = 'before' if anchor['checkpoint_id'] == before['id'] else 'after' if anchor['checkpoint_id'] == after['id'] else None
        notes.append({'id': nid, 'text': note['text'], 'acceptance': note['acceptance'], 'priority': note['priority'],
                      'category': note['category'], 'stage_id': note['stage_id'], 'status': item['status'],
                      'validity': item['current_validity'], 'targets': anchor.get('instance_ids', []) + anchor.get('material_ids', []),
                      'checkpoint_id': anchor['checkpoint_id'], 'side': side, 'view_id': render.get('view_id'), 'pin': render.get('pin')})
    submission, elsewhere = None, []
    if events and feedback.binding(events) is not None:
        from .environment_workflow import stages
        for stage in stages(events).values():
            if stage['state'] == 'awaiting_review':
                event = next(e for e in events if e['id'] == stage['submission_id'])
                value = event['result']['submission']
                if value['checkpoint'] != c.checkpoint_ref(after):
                    # Approval is offered only for the checkpoint this page shows.
                    elsewhere.append({'stage_id': value['stage_id'], 'checkpoint_id': value['checkpoint']['checkpoint_id']})
                    continue
                submission = {'id': event['id'], 'stage_id': value['stage_id'], 'note': value['note'], 'checkpoint': value['checkpoint'],
                              'deliverables': value['deliverables'], 'questions': value.get('questions', []),
                              'review_policy': feedback.policy(events, value['stage_id']), 'current': events[-1]['id'] == event['id']}
    reopened = 'not run'
    if reopen:
        from .observe import observe_file
        fresh = observe_file(after['checkpoint'], folder / 'work' / 'reopen', blender)
        if fresh['revision'] == after_obs['revision']:
            reopened = 'matches the stored observation exactly'
        else:
            # The qualified comparator, as native_reopen evidence uses: evaluated UVs may differ by float noise between processes.
            from .continuity_checks import evaluate_stage
            required = next(iter(after_obs['objects']))
            check = evaluate_stage(after_obs, read_json(fresh['observation']), {'schema': 'dcc.continuity.contract.v1',
                                   'spec': {'schema': 'dcc.spec.v1', 'required': {required: {}}}, 'allowed_new_prefixes': []})
            noise = check['evaluated_uv_noise']['objects']
            reopened = (f'matches the stored observation within float noise in the evaluated UVs of {len(noise)} objects' if check['passed']
                        else 'differs from the stored observation: ' + '; '.join(check['failures'][:5]))
    data = {'schema': 'dcc.review.page.v1', 'project': str(Path(root).resolve()), 'generated': now(),
            'from': _summary(before), 'to': _summary(after), 'changes': changes(before_obs, after_obs), 'notes': notes,
            'views': view_rows, 'views_match': bool(rendered) and rendered['before']['digest'] == rendered['after']['digest'],
            'after_render': {k: rendered['after'][k] for k in ('receipt', 'settings')} if rendered else None,
            'objects': sorted(after_obs['objects']), 'submission': submission,
            'verification': {'chain_verified': True, 'receipts_bound': bool(rendered), 'reopened': reopened}}
    write_json(folder / 'page.json', data)
    page_digest = digest(data)
    text = (TEMPLATE.replace('__DIGEST__', page_digest)
            .replace('__DATA__', json.dumps(data, sort_keys=True).replace('</', '<\\/')))
    (folder / 'index.html').write_text(text, encoding='utf-8', newline='\n')
    return {'schema': 'dcc.review.page.result.v1', 'page': str(folder / 'index.html'), 'page_digest': page_digest,
            'from': data['from'], 'to': data['to'], 'views': len(view_rows), 'views_match': data['views_match'],
            'counts': {k: len(v) for k, v in data['changes'].items() if isinstance(v, list)},
            'submission': submission and submission['id'], 'submissions_not_shown': elsewhere, 'reopened': reopened,
            'next_action': f'Open the page. Import its export with: python -m dcc_harness review-import "{root}" "<export .json>" --page "{folder}"'}


def import_review(root, export, page, console=None):
    """Commit a page export: the stage review first, then each note. A retry replays.

    An artist's stage review needs the owner's confirmation before anything is committed.
    """
    from . import environment_workflow, owner
    page = _plain(page)
    value = read_json(_plain(export))
    if not isinstance(value, dict) or value.get('schema') != 'dcc.review.export.v1' or not isinstance(value.get('notes'), list):
        raise ValueError('Not a review page export')
    data = read_json(page / 'page.json')
    if value.get('page') != digest(data):
        raise ValueError('This export came from another review page or a changed one; regenerate the page and review again')
    key = digest(value)
    results = []
    if value.get('review') is not None:
        submission = data.get('submission')
        if submission is None:
            raise ValueError('The page had no stage submission to review')
        shown = {'checkpoint_id': data['to']['id'], 'checkpoint_sha256': data['to']['checkpoint_sha256']}
        event = next((e for e in c.read(root) if e['id'] == submission['id'] and e['kind'] == 'stage.submit'), None)
        if event is None or event['result']['submission']['checkpoint'] != shown or submission.get('checkpoint') != shown:
            raise ValueError('The stage submission is not for the checkpoint this page shows; build a page for its checkpoint and review again')
        payload, request = {'submission_id': submission['id'], 'review': value['review']}, str(uuid.uuid5(NAMESPACE, key + ':review'))
        approval = owner.authorize(root, 'stage.complete', payload, request, console)
        outcome = environment_workflow.apply(root, 'stage.complete', payload, submission['id'], request, page, approval=approval)
        results.append({'kind': 'stage.complete', 'status': outcome['status'], 'revision': outcome['revision']})
    for index, note in enumerate(value['notes']):
        events = c.read(root)
        outcome = feedback.apply(root, 'feedback.add', note, events[-1]['id'] if events else 'none',
                                 str(uuid.uuid5(NAMESPACE, f'{key}:note:{index}')), page)
        results.append({'kind': 'feedback.add', 'status': outcome['status'], 'revision': outcome['revision'],
                        'note_id': outcome['result']['note']['id']})
    return {'schema': 'dcc.review.import.v1', 'page': value['page'], 'results': results}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Checkpoint review</title>
<style>
:root{--bg:#f6f5f2;--panel:#fff;--ink:#1d1f22;--muted:#5d6168;--line:#dcdad4;--accent:#1f5fbf;--ok:#1f7a4d;--warn:#a1520c;--bad:#b3261e;--pin:#e0412b}
@media (prefers-color-scheme:dark){:root{--bg:#141517;--panel:#1d1f23;--ink:#ececec;--muted:#a3a7ae;--line:#33363c;--accent:#7fb0ff;--ok:#5fd09a;--warn:#f0a35a;--bad:#ff8a80;--pin:#ff6b52}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1240px;margin:0 auto;padding:24px 16px 80px}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 12px}
.muted{color:var(--muted)}#subtitle,code,td{overflow-wrap:anywhere}.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.badge{border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:13px}
.badge.ok{color:var(--ok);border-color:var(--ok)}.badge.warn{color:var(--warn);border-color:var(--warn)}
.sheet{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr));gap:12px}.sheet figure{margin:0;cursor:pointer}
.sheet img{width:100%;border-radius:8px;border:1px solid var(--line);display:block}figcaption{font-size:13px;color:var(--muted);margin-top:4px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media (max-width:760px){.pair{grid-template-columns:1fr}}
.frame{position:relative}.frame img{width:100%;display:block;border-radius:8px;border:1px solid var(--line)}.frame.pinning img{cursor:crosshair}
.pin{position:absolute;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:var(--pin);color:#fff;font-size:12px;font-weight:700;display:grid;place-items:center;border:2px solid #fff}
.pin.draft{background:var(--accent)}button{font:inherit;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px}code{font-size:13px}
label{display:block;margin:8px 0 2px;font-size:14px}input[type=text],textarea,select{width:100%;font:inherit;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.choices label{display:inline-flex;gap:6px;margin-right:16px;align-items:center}.note{border-left:3px solid var(--line);padding:4px 10px;margin:8px 0}.note.blocking{border-color:var(--bad)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
</style>
</head>
<body>
<main>
<h1>Checkpoint review</h1>
<p class="muted" id="subtitle"></p>
<div class="badges" id="badges"></div>
<section id="submission" hidden><h2>Stage waiting for your review</h2><div class="panel" id="submission-body"></div></section>
<section id="sheet-section"><h2>All review views</h2><p class="muted">The after checkpoint, every view. Select one to compare.</p><div class="sheet" id="sheet"></div></section>
<section id="compare-section"><h2>Before and after</h2><p class="muted">Hold <b>Show before</b> to swap in the earlier image. To pin a new note, press <b>Pin a note</b>, then click the after image.</p><div id="compare"></div></section>
<section><h2>What changed</h2><div class="panel" id="changes"></div></section>
<section><h2>Feedback notes</h2><div id="notes"></div></section>
<section><h2>Add a note</h2><div class="panel">
<label for="n-text">What should change?</label><textarea id="n-text" rows="2"></textarea>
<label for="n-accept">What would make it right?</label><textarea id="n-accept" rows="2"></textarea>
<div class="row"><div><label for="n-cat">Kind</label><select id="n-cat"><option value="visual">Visual</option><option value="technical">Technical</option><option value="preference">Preference</option></select></div>
<div><label for="n-pri">Priority</label><select id="n-pri"><option value="advisory">Advisory</option><option value="blocking">Blocking</option></select></div>
<div style="flex:1"><label for="n-obj">Object (optional)</label><input type="text" id="n-obj" list="objects" placeholder="stable ID"></div></div>
<datalist id="objects"></datalist><p class="muted" id="n-pin">No pin. Use Pin a note on a view to add one.</p>
<button id="n-add">Add note</button><div id="drafts"></div></div></section>
<section><h2>Export</h2><div class="panel">
<label for="who">Your name</label><input type="text" id="who" placeholder="Shown with your notes and review">
<p class="muted" id="export-help"></p><button class="primary" id="export">Download review export</button></div></section>
<p class="muted">Page <code>__DIGEST__</code></p>
</main>
<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
const data=JSON.parse(document.getElementById('data').textContent);const digest='__DIGEST__';
const el=(tag,props,...kids)=>{const n=document.createElement(tag);Object.assign(n,props||{});kids.flat().forEach(k=>n.append(k));return n;};
const short=s=>s?String(s).slice(0,12):'';let pinning=null;let draftPin=null;const drafts=[];
document.getElementById('subtitle').textContent=`Before: ${data.from.step_id} (sequence ${data.from.sequence}) · After: ${data.to.step_id} (sequence ${data.to.sequence}) · ${data.project}`;
const v=data.verification,badges=document.getElementById('badges');
const badge=(text,cls)=>badges.append(el('span',{className:'badge '+(cls||''),textContent:text}));
badge('Checkpoint chain verified','ok');badge(v.receipts_bound?'Renders bound to both checkpoints':'No renders on this page',v.receipts_bound?'ok':'warn');
if(data.views.length)badge(data.views_match?'Same view settings on both sides':'View settings differ between sides',data.views_match?'ok':'warn');
badge('Reopened: '+v.reopened,v.reopened.startsWith('matches')?'ok':v.reopened==='not run'?'':'warn');
const objects=document.getElementById('objects');data.objects.forEach(o=>objects.append(el('option',{value:o})));
if(data.submission){const s=data.submission,body=document.getElementById('submission-body');document.getElementById('submission').hidden=false;
 body.append(el('p',{},el('b',{textContent:`Stage ${s.stage_id}`}),` · review policy ${s.review_policy}`+(s.current?'':' · newer activity exists, so completing may be refused as stale')));
 body.append(el('p',{textContent:s.note}));const dl=el('ul');Object.entries(s.deliverables).forEach(([k,d])=>dl.append(el('li',{},el('b',{textContent:k+': '}),d)));body.append(dl);
 s.questions.forEach(q=>{const box=el('div',{className:'panel'});box.append(el('div',{},el('b',{textContent:q.text})));
  const choices=el('div',{className:'choices'});(q.choices||[]).forEach(c=>{const r=el('input',{type:'radio',name:'q-'+q.id,value:c,checked:c===q.default});choices.append(el('label',{},r,c));});
  const other=el('input',{type:'text',id:'q-'+q.id+'-other',placeholder:q.choices?'Or write another answer':(q.default?`Default: ${q.default}`:'Your answer (required)')});
  box.append(choices,other);body.append(box);});
 body.append(el('label',{htmlFor:'finding',textContent:'Your finding'}),el('textarea',{id:'finding',rows:2,placeholder:'What you looked at and what you decided'}));
 const approve=el('input',{type:'checkbox',id:'approve'});body.append(el('label',{},approve,' Approve this stage'));
 body.append(el('button',{textContent:'Accept every default and approve',onclick:()=>{s.questions.forEach(q=>{document.querySelectorAll(`input[name="q-${q.id}"]`).forEach(r=>r.checked=r.value===q.default);document.getElementById('q-'+q.id+'-other').value='';});approve.checked=true;}}));}
const pinsFor=(view,side)=>data.notes.filter(n=>n.view_id===view&&n.side===side&&n.pin);
const frame=(src,view,side)=>{const f=el('div',{className:'frame'});if(!src){f.append(el('p',{className:'muted',textContent:`No ${side} image`}));return f;}
 const img=el('img',{src,alt:`${view} ${side}`});f.append(img);
 pinsFor(view,side).forEach((n,i)=>f.append(el('span',{className:'pin',title:n.text,textContent:String(data.notes.indexOf(n)+1),style:`left:${n.pin.x*100}%;top:${n.pin.y*100}%`})));
 if(side==='after')img.addEventListener('click',e=>{if(pinning!==view)return;const r=img.getBoundingClientRect();draftPin={view,x:+((e.clientX-r.left)/r.width).toFixed(4),y:+((e.clientY-r.top)/r.height).toFixed(4)};
  f.querySelectorAll('.pin.draft').forEach(p=>p.remove());f.append(el('span',{className:'pin draft',textContent:'+',style:`left:${draftPin.x*100}%;top:${draftPin.y*100}%`}));
  document.getElementById('n-pin').textContent=`Pinned on ${view} at x ${draftPin.x}, y ${draftPin.y}.`;pinning=null;f.classList.remove('pinning');});return f;};
const sheet=document.getElementById('sheet'),compare=document.getElementById('compare');
if(!data.views.length){document.getElementById('sheet-section').hidden=true;document.getElementById('compare-section').hidden=true;}
data.views.forEach(view=>{const src=view.after||view.before;sheet.append(el('figure',{onclick:()=>document.getElementById('view-'+view.id).scrollIntoView({behavior:'smooth'})},el('img',{src,alt:view.id}),el('figcaption',{textContent:view.id+(view.purpose?` · ${view.purpose}`:'')})));
 const after=frame(view.after,view.id,'after'),before=frame(view.before,view.id,'before');const afterImg=after.querySelector('img');
 const hold=el('button',{textContent:'Show before'});const swap=on=>{if(afterImg&&view.before)afterImg.src=on?view.before:view.after;};
 ['pointerdown','keydown'].forEach(t=>hold.addEventListener(t,e=>{if(t==='keydown'&&e.key!==' '&&e.key!=='Enter')return;swap(true);}));['pointerup','pointerleave','keyup','blur'].forEach(t=>hold.addEventListener(t,()=>swap(false)));
 const pin=el('button',{textContent:'Pin a note',onclick:()=>{pinning=view.id;after.classList.add('pinning');document.getElementById('n-pin').textContent=`Click the after image of ${view.id} to place the pin.`;}});
 const anchored=data.notes.filter(n=>n.view_id===view.id).map(n=>`#${data.notes.indexOf(n)+1} ${n.text}`+(n.side?` (${n.side}${n.pin?', pinned':''})`:' (another checkpoint)'));
 compare.append(el('div',{className:'panel',id:'view-'+view.id},el('div',{className:'row'},el('b',{textContent:view.id}),hold,pin),el('div',{className:'pair'},el('div',{},el('div',{className:'muted',textContent:'Before'}),before),el('div',{},el('div',{className:'muted',textContent:'After'}),after)),
  anchored.length?el('p',{className:'muted',textContent:'Notes on this view: '+anchored.join('; ')}):''));});
const ch=data.changes,box=document.getElementById('changes');const notesFor=id=>data.notes.filter(n=>n.targets.includes(id)).map(n=>'#'+(data.notes.indexOf(n)+1)).join(' ');
const table=(title,rows,cols)=>{if(!rows.length)return;box.append(el('h3',{textContent:`${title} (${rows.length})`}));const t=el('table');t.append(el('tr',{},cols.map(c=>el('th',{textContent:c[0]}))));
 rows.forEach(r=>t.append(el('tr',{},cols.map(c=>el('td',{textContent:c[1](r)??''})))));box.append(t);};
table('Moved',ch.moved,[['Object',r=>r.id],['Moved by (m)',r=>r.distance],['Notes',r=>notesFor(r.id)]]);
table('Changed',ch.changed,[['Object',r=>r.id],['Fields',r=>r.fields.join(', ')],['Notes',r=>notesFor(r.id)]]);
table('Added',ch.added,[['Object',r=>r.id],['Type',r=>r.type],['Asset',r=>r.asset_id]]);table('Removed',ch.removed,[['Object',r=>r.id],['Type',r=>r.type],['Asset',r=>r.asset_id]]);
table('Materials',ch.materials,[['Material',r=>r.id],['Change',r=>r.change],['Fields',r=>r.fields.join(', ')]]);
if(ch.scene.length)box.append(el('p',{textContent:'Scene settings changed: '+ch.scene.join(', ')}));box.append(el('p',{className:'muted',textContent:`${ch.unchanged} objects unchanged.`}));
const notes=document.getElementById('notes');if(!data.notes.length)notes.append(el('p',{className:'muted',textContent:'No feedback notes recorded.'}));
data.notes.forEach((n,i)=>notes.append(el('div',{className:'note '+n.priority},el('b',{textContent:`#${i+1} ${n.text}`}),el('div',{className:'muted',textContent:`${n.priority} ${n.category} · ${n.status} · ${n.validity}`+(n.targets.length?` · ${n.targets.join(', ')}`:'')+(n.view_id?` · view ${n.view_id}`:'')}),el('div',{textContent:'Acceptance: '+n.acceptance}))));
const draftsBox=document.getElementById('drafts');
document.getElementById('n-add').onclick=()=>{const text=document.getElementById('n-text').value.trim(),acceptance=document.getElementById('n-accept').value.trim();
 if(!text||!acceptance){alert('Write what should change and what would make it right.');return;}const obj=document.getElementById('n-obj').value.trim();
 if(obj&&!data.objects.includes(obj)){alert('That object is not in the after checkpoint.');return;}
 const anchor={checkpoint_id:data.to.id,checkpoint_sha256:data.to.checkpoint_sha256};if(obj)anchor.instance_ids=[obj];
 if(draftPin&&data.after_render)anchor.render={receipt:data.after_render.receipt,settings:data.after_render.settings,view_id:draftPin.view,pin:{x:draftPin.x,y:draftPin.y}};
 drafts.push({text,acceptance,category:document.getElementById('n-cat').value,priority:document.getElementById('n-pri').value,anchor});
 draftsBox.append(el('div',{className:'note'},el('b',{textContent:`New: ${text}`}),el('div',{className:'muted',textContent:(obj?obj+' · ':'')+(anchor.render?`pinned on ${anchor.render.view_id}`:'no pin')})));
 ['n-text','n-accept','n-obj'].forEach(id=>document.getElementById(id).value='');draftPin=null;document.getElementById('n-pin').textContent='No pin. Use Pin a note on a view to add one.';};
document.getElementById('export-help').textContent=`The export holds your notes${data.submission?' and, if you approve, the stage review with your answers':''}. Import it with review-import, passing --page for this folder.`;
document.getElementById('export').onclick=()=>{const who=document.getElementById('who').value.trim();if(!who){alert('Add your name first.');return;}
 const source={role:'artist',author:who,reference:'Review page '+short(digest)};let review=null;
 if(data.submission&&document.getElementById('approve').checked){const answers={};
  for(const q of data.submission.questions){const other=document.getElementById('q-'+q.id+'-other').value.trim();const picked=document.querySelector(`input[name="q-${q.id}"]:checked`);
   const value=other||(picked?picked.value:'');if(!value&&q.default===undefined){alert('Answer: '+q.text);return;}if(value&&value!==q.default)answers[q.id]=value;}
  const finding=document.getElementById('finding').value.trim();if(!finding){alert('Write your finding before approving.');return;}
  review={reviewer:source,verdict:'pass',finding,answers};}
 const notesOut=drafts.map(d=>({schema:'dcc.feedback.note.v1',source,stage_id:null,category:d.category,priority:d.priority,text:d.text,acceptance:d.acceptance,anchor:d.anchor}));
 if(!review&&!notesOut.length){alert('Nothing to export: approve the stage or add a note.');return;}
 const blob=new Blob([JSON.stringify({schema:'dcc.review.export.v1',page:digest,review,notes:notesOut},null,2)],{type:'application/json'});
 const a=el('a',{href:URL.createObjectURL(blob),download:'review-export-'+short(digest)+'.json'});document.body.append(a);a.click();a.remove();};
})();
</script>
</body>
</html>
"""
