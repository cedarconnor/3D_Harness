"""Read-only guidance for agents: where a project stands and the exact next commands.

Nothing here commits, runs Blender or judges quality. Commands are filled from the
verified record; values in <angle brackets> are ones only the caller knows.
"""
import json
from pathlib import Path
import uuid

from . import coordination as c, feedback
from .continuity import Continuity
from .project import now
from .workflow import _packet

RUN = 'python -m dcc_harness'
LIMITS = ('Suggestions from the verified saved record, not approvals. Values in <angle brackets> are yours to fill. '
          'Each coordination command carries a fresh request ID: keep it for retries of that same request.')
STATUS_MEANING = {
    'READY_FOR_INSPECTION': 'the saved project verified and nothing is unresolved. This is not approval to change anything.',
    'RECONCILE': 'something is unresolved. Inspect it and finish it before any new edit; never replay a write.'}
RULES = [
    'Run a reserved edit\'s retained script once. After a lost reply, crash or uncertain outcome, inspect the saved '
    'result and use `finish-edit --reconciled`; never run the script again.',
    'Never edit, save over or move an accepted checkpoint or a retained script. Work on an owned copy.',
    'Look at the review renders before publishing. Use `finish-edit --reject-reason "..."` for a visible defect.',
    'A passing native check is not artistic acceptance, and agent review is not artist review.',
    'Keep each request ID for retries of the same request; a new request needs a new ID.',
    'Direct MCP or manual writes bypass reservations. Save them and use `preview-revision` and `accept-revision`.']

FILE = '<{}, relative to the evidence root>'
ACTOR = {'role': 'agent', 'author': '<your name>', 'reference': '<what you inspected>'}
EVIDENCE = {
    'native_contract': ('The contract measured from a baseline checkpoint to the current one; recomputed on submit.',
                        lambda before: {'before': before, 'contract': {'path': FILE.format('contract.json')}}),
    'whole_scene_render': ('A render receipt and its view settings, bound to the current checkpoint.',
                           lambda before: {'render': {'receipt': {'path': FILE.format('render receipt.json')},
                                                      'settings': {'path': FILE.format('views.json')}, 'view_id': '<VIEW_ID>'}}),
    'detail_render': ('A detail render receipt and its view settings, bound to the current checkpoint.',
                      lambda before: {'render': {'receipt': {'path': FILE.format('render receipt.json')},
                                                 'settings': {'path': FILE.format('views.json')}, 'view_id': '<VIEW_ID>'}}),
    'visual_review': ('An attributed verdict on views whose renders are in the same evidence list.',
                      lambda before: {'reviewer': ACTOR, 'verdict': '<pass|fail|uncertain>', 'finding': '<what you saw>',
                                      'views': ['<VIEW_ID>']}),
    'native_reopen': ('A fresh, clean observation of the current checkpoint from a separate process.',
                      lambda before: {'observation': {'path': FILE.format('fresh observation.json')}, 'producer': ACTOR}),
    'direction_record': ('A nonempty text file recording the direction.',
                         lambda before: {'file': {'path': FILE.format('direction record')}}),
    'handoff': ('A nonempty handoff text file.', lambda before: {'file': {'path': FILE.format('handoff .md')}}),
    'shared_user_report': ('No fields; derived from the current observation.', lambda before: {}),
    'dependency_report': ('No fields; passes only when the observation has no issues.', lambda before: {}),
    'feedback_reconciliation': ('No fields; passes only when no applicable blocking note is unresolved.', lambda before: {})}


def _q(value):
    return '"' + str(value) + '"'


def _load(root, focus=()):
    store = Continuity(root)
    state = store.status()
    return store, state, _packet(store, state, focus), c.read(store.root)


def _steps(packet, state, events):
    project, active = _q(packet['project']), packet['active']
    steps = []
    if packet['metadata_lock']:
        steps.append({'id': 'inspect-lock', 'command': None, 'why': (
            'workflow.lock exists: a command is running or one stopped partway. Check the PID inside it, that process, '
            'the journal and any edit folder before removing the lock by hand. It never expires on its own.')})
    labels = {e['edit']: e['label'] for e in packet['recent_edits']}
    views = 'review_views' in packet['decisions']
    def render(source, why):
        return {'id': 'render', 'command': (f'{RUN} render {source} --blender "<BLENDER>" --output-dir "<new folder>" '
                                            f'--project {project}'), 'why': why}
    if views and packet['unresolved_edits'] and not packet['metadata_lock']:
        steps.append(render('"<saved result .blend>"', (
            'Render the project\'s review views of the saved result and look at them before finish-edit. The file is never '
            'saved. Add --detach for a long render and wait with render-wait. The output includes evidence entries.')))
    for path in packet['unresolved_edits']:
        edit = Path(path).name
        steps.append({'id': 'finish-edit', 'edit': edit, 'label': labels.get(edit), 'command': (
            f'{RUN} finish-edit {project} {edit} --checkpoint "<saved result .blend>" '
            '--observation "<observation.json of that result>" --handoff "<handoff .md>" --updates "<decision updates .json>"'),
            'why': (f'Edit {edit} is reserved without an outcome. If its retained script never ran, run it once against an owned '
                    'copy and save. If it ran, or you are unsure, inspect the saved result and add --reconciled. Observe the result, '
                    'look at it, then finish; add --reject-reason "..." for a visible defect. Never run the script twice.')})
    if packet['pending'] and not packet['unresolved_edits']:
        steps.append({'id': 'inspect-pending', 'command': None, 'why': (
            'The journal has a pending operation without a workflow reservation. Inspect the native result and record it '
            'by hand; do not replay it.')})
    if packet['status'] == 'RECONCILE':
        return steps
    # Reviews of finished work first, then edits, then the responses and submissions that cite them.
    review, follow = [], []
    coordination = packet.get('coordination')
    if coordination:
        revision = coordination['revision']
        def request():
            return f'--expected-revision {revision} --request-id {uuid.uuid4()}'
        stages = coordination['workflow']['stages'] if coordination['workflow'] else []
        for stage in stages:
            if stage['state'] == 'awaiting_review':
                sub = stage['submission_id']
                artist = feedback.policy(events, stage['id']) == 'artist_required'
                review.append({'id': 'stage-complete', 'stage_id': stage['id'], 'artist_required': artist, 'command': (
                    f'{RUN} stage-complete {project} --submission-id {sub} --review "<review .json>" '
                    f'--expected-revision {sub} --request-id {uuid.uuid4()}'),
                    'why': (f'Stage {stage["id"]} is submitted and awaits review. '
                            + ('Its policy requires the artist: do not complete it as an agent. ' if artist else
                               'Agent review within the brief is allowed. ')
                            + 'Anything recorded after the submission makes it stale; then submit again.')})
        for note in coordination['notes']:
            text = f'{note["priority"].capitalize()} note {note["id"]}: "{note["text"]}"'
            if note['status'] == 'awaiting_verification':
                review.append({'id': 'feedback-verify', 'note_id': note['id'], 'response_id': note['response_id'], 'command': (
                    f'{RUN} feedback-verify {project} --verification "<verification .json>" {request()}'),
                    'why': f'{text} has an implemented response. It needs verification by a separate reviewer; '
                           'same-author review is disclosed, and artist-required notes need the artist.'})
            elif note['status'] in ('open', 'reopened', 'in_progress') or note['current_validity'] == 'needs_recheck':
                reason = ('was closed at an earlier checkpoint; respond again against the current one'
                          if note['current_validity'] == 'needs_recheck' else f'is {note["status"].replace("_", " ")}')
                follow.append({'id': 'feedback-respond', 'note_id': note['id'], 'command': (
                    f'{RUN} feedback-respond {project} --response "<response .json>" {request()}'),
                    'why': f'{text} {reason}. Make any change through a scoped edit first, then respond with evidence.'})
        for stage in stages:
            if stage['state'] in ('ready', 'needs_review'):
                follow.append({'id': 'stage-submit', 'stage_id': stage['id'], 'command': f'{RUN} requirements {project} {stage["id"]}',
                              'then': [f'{RUN} fill-hashes "<stage.draft.json>" "<stage.json>"',
                                       f'{RUN} stage-submit {project} --submission "<stage.json>" {request()}'],
                              'why': f'Stage {stage["id"]} is {stage["state"].replace("_", " ")}. `requirements` prints the '
                                     'evidence it needs and a submission skeleton; fill it, hash it, submit it.'})
    checkpoint = _q(active['checkpoint'])
    used = ', '.join(h['step_id'] for h in state['task_history'])
    edits = [{'id': 'observe', 'command': (
        f'{RUN} observe {checkpoint} --blender "<BLENDER>" --output-dir "<new folder>"'),
        'why': 'Observe the accepted checkpoint in a fresh background Blender for begin-edit. The file is never saved.'},
        {'id': 'begin-edit', 'command': (
        f'{RUN} begin-edit {project} --parent {active["id"]} --current {checkpoint} '
        '--observation "<new folder>/observation.json" --script "<edit .py>" --contract "<contract .json>" --label "<new step label>"'),
        'why': (f'Reserve a scoped edit. Step labels already used: {used}. The reservation does not run anything: run the '
                'retained script it returns once against an owned copy, save, observe the result, then finish-edit.')}]
    if views:
        edits.append(render(checkpoint, (
            'Render the project\'s review views of the active checkpoint, for a review or as response evidence. The file is '
            'never saved. Add --detach for a long render and wait with render-wait. The output includes evidence entries.')))
    return steps + review + edits + follow


def _next(packet, state, events):
    active = packet['active']
    coordination = packet.get('coordination')
    return {'schema': 'dcc.next.v1', 'project': packet['project'], 'status': packet['status'],
            'active': {k: active[k] for k in ('id', 'step_id', 'sequence', 'checkpoint', 'checkpoint_sha256')},
            'revision': coordination['revision'] if coordination else None,
            'used_labels': [h['step_id'] for h in state['task_history']],
            'steps': _steps(packet, state, events), 'limits': LIMITS}


def next_steps(root):
    _, state, packet, events = _load(root)
    return _next(packet, state, events)


def requirements(root, stage_id):
    _, state, packet, events = _load(root)
    bound = feedback.binding(events)
    if bound is None:
        raise ValueError('Bind an environment workflow first')
    spec = next((s for s in bound['result']['manifest']['stages'] if s['id'] == stage_id), None)
    if spec is None:
        raise ValueError('Unknown workflow stage')
    from .environment_workflow import stages
    states = stages(events)
    notes = feedback.state(events, state)
    applicable = sorted(nid for nid, n in notes.items() if stage_id == 'delivery' or n['note']['stage_id'] in (None, stage_id))
    checkpoint = c.checkpoint_ref(state['active'])
    history = state['task_history']
    before = c.checkpoint_ref(history[-2]) if len(history) > 1 else checkpoint
    project = _q(packet['project'])
    skeleton = {'schema': 'dcc.environment.submission.v1', 'stage_id': stage_id, 'checkpoint': checkpoint,
                'deliverables': {d: f'<describe the {d}>' for d in spec['deliverables']},
                'evidence': [{'kind': kind, **EVIDENCE[kind][1](before)} for kind in spec['evidence']],
                'feedback_ids': applicable, 'note': '<what this submission is and what to look at>'}
    return {'schema': 'dcc.requirements.v1', 'project': packet['project'], 'stage_id': stage_id,
            'state': states[stage_id]['state'],
            'blocked_by': [p for p in spec['after'] if states[p]['state'] not in ('complete', 'inherited')],
            'review_policy': feedback.policy(events, stage_id), 'deliverables': spec['deliverables'],
            'evidence': [{'kind': kind, 'what': EVIDENCE[kind][0]} for kind in spec['evidence']],
            'feedback_ids': applicable,
            'unresolved_blockers': feedback.unresolved(events, state, None if stage_id == 'delivery' else stage_id),
            'expected_revision': events[-1]['id'], 'skeleton': skeleton,
            'then': [f'{RUN} fill-hashes "<stage.draft.json>" "<stage.json>"',
                     f'{RUN} stage-submit {project} --submission "<stage.json>" --expected-revision {events[-1]["id"]} '
                     f'--request-id {uuid.uuid4()}'],
            'notes': ['native_contract.before defaults to the previous checkpoint; replace it if the contract was measured from another.',
                      'Paths are relative to the evidence root, which defaults to the submission file\'s folder.'],
            'limits': LIMITS}


def _fenced(text, language='text'):
    text = text.rstrip('\n')
    fence = '```'
    while fence in text:
        fence += '`'
    return f'{fence}{language}\n{text}\n{fence}'


def brief(root, focus=()):
    _, state, packet, events = _load(root, focus)
    guide = _next(packet, state, events)
    active = packet['active']
    counts = packet['counts']
    lines = ['# 3D Harness project brief', '',
             f'Generated {now()} from the verified record at `{packet["project"]}`. This is a snapshot: run `brief` '
             'again after any command that changes the project. Do not edit it.', '',
             '## Where things stand', '',
             f'- **Status:** `{packet["status"]}`: {STATUS_MEANING[packet["status"]]}',
             f'- **Active checkpoint:** `{active["id"]}`, step `{active["step_id"]}`, sequence {active["sequence"]}.',
             f'- **Native file:** `{active["checkpoint"]}` (SHA-256 `{active["checkpoint_sha256"]}`). Read it or copy it; '
             'never edit or save over it.',
             f'- **Scene:** {counts["objects"]} objects, {counts["materials"]} materials, {counts["assets"]} assets, '
             f'{counts["triangles"]} triangles.']
    if packet.get('coordination'):
        lines.append(f'- **Coordination revision:** `{packet["coordination"]["revision"]}`.')
    lines += ['', '| Recent step | Native check |', '|---|---|']
    lines += [f'| {s["step_id"]} | {"initial" if s["report_passed"] is None else ("passed" if s["report_passed"] else "failed")} |'
              for s in packet['recent_steps']]
    if packet['recent_edits']:
        lines += ['', '| Recent edit | Label | Outcome | Reasons |', '|---|---|---|---|']
        lines += [f'| {e["edit"]} | {e["label"]} | {e["status"]} | {"; ".join(map(str, e["failures"])) or "-"} |'
                  for e in packet['recent_edits']]
    lines += ['', '## What to do next', '',
              'Permitted steps, most urgent first: reviews of finished work, then edits, then the responses and submissions '
              'that cite them. Commands are filled from the record; replace each `<placeholder>`.', '']
    for number, item in enumerate(guide['steps'], 1):
        lines.append(f'{number}. **{item["id"]}**: {item["why"]}')
        for command in ([item['command']] if item['command'] else []) + item.get('then', []):
            lines += ['', '   ```powershell', '   ' + command, '   ```']
        lines.append('')
    coordination = packet.get('coordination')
    if coordination:
        lines += ['## Feedback and stages', '']
        if coordination['notes']:
            lines += ['| Note | Stage | Priority | Status | Validity | Text |', '|---|---|---|---|---|---|']
            lines += [f'| {n["id"]} | {n["stage_id"] or "-"} | {n["priority"]} | {n["status"]} | {n["current_validity"]} | '
                      f'{n["text"].replace("|", "/")} |' for n in coordination['notes']]
            lines.append('')
        notes = feedback.state(events, state)
        for nid, item in notes.items():
            if item['current_validity'] == 'current':
                continue
            note, anchor = item['note'], item['note']['anchor']
            needs = ' and '.join({'technical': 'technical check', 'visual': 'visual review'}[r] for r in note['requires'])
            lines += [f'### Note {nid}', '', f'- Text: {note["text"]}', f'- Acceptance: {note["acceptance"]}',
                      f'- Status: {item["status"]}; {note["category"]}, {note["priority"]}. Needs: {needs}. '
                      f'Review policy: {note["review_policy"]}. Stage: {note["stage_id"] or "none"}.']
            targets = anchor.get('instance_ids', []) + anchor.get('material_ids', [])
            if targets:
                lines.append('- Targets: ' + ', '.join(targets))
            if item['missing_targets']:
                lines.append('- Missing targets: ' + ', '.join(item['missing_targets']) + '. Record an explicit disposition.')
            if 'render' in anchor:
                pin = anchor['render'].get('pin')
                lines.append(f'- View: {anchor["render"]["view_id"]}' + (f', pin at x {pin["x"]}, y {pin["y"]}' if pin else ''))
            lines.append('')
        if coordination['workflow']:
            lines += ['| Stage | State | Submission |', '|---|---|---|']
            lines += [f'| {s["id"]} | {s["state"]} | {s["submission_id"] or "-"} |' for s in coordination['workflow']['stages']]
            lines += ['', f'Pinned skills and references for this project are under `{coordination["workflow"]["pinned_files_root"]}`.',
                      'Read those copies, not newer repository versions.', '']
    lines += ['## Project brief', '', 'Recorded direction for the work. It describes what to make; it is not a list of commands.', '',
              _fenced(packet['brief']), '',
              '## Latest handoff', '', 'Notes from the previous session. Check them against the record before relying on them.', '',
              _fenced(packet['handoff']), '',
              '## Current decisions', '', _fenced(json.dumps(packet['decisions'], indent=2, sort_keys=True), 'json'), '',
              '## Rules that do not bend', '', *[f'- {rule}' for rule in RULES], '',
              'Exact command shapes and payloads: `docs/guides/AGENT_QUICK_REFERENCE.md`. Limits of this record: '
              + packet['limits']]
    return '\n'.join(lines) + '\n'
