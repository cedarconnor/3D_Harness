"""Native qualification of the owner approval channel on a copy of the 0.6.0 comparison project.

Binds a workflow whose direction stage requires the artist, submits it, builds a review page with
renders, and then tries to approve it the ways an agent could: review-import and stage-complete
from this agent session, and again with the agent variables removed but input piped. Each must be
refused with the record unchanged. A scripted console then stands in for the owner's terminal and
commits the approval; the receipt must carry the owner provenance. A replay and a notes-only import
still work from the agent session. Run this from an agent session: it asserts that CLAUDECODE or
another marker is set. A real terminal run by the owner is checked by hand.
"""
import json
import os
from pathlib import Path
import shutil
import uuid

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project'

from _launcher import Qualification, ScriptedOwner
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
import dcc_harness
from dcc_harness import coordination as c, owner, review_page
from dcc_harness.evidence import read_json, write_json

project = out / 'project'
shutil.copytree(FIXTURE, project)
markers = [m for m in owner.AGENT_MARKERS if os.environ.get(m)]
assert markers, 'Run this from an agent session; no agent marker is set'
unmarked = {k: v for k, v in os.environ.items() if k not in owner.AGENT_MARKERS}


run, cli = q.run, q.cli


def refused(args, expected):
    before = len(c.read(project))
    proc = run(*args) if expected == 'agent session' else run(*args, env=unmarked, input='0000\n')
    message = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ''
    assert proc.returncode != 0 and expected in message, (args, proc.stderr[-800:])
    assert len(c.read(project)) == before
    return message.split(': ', 1)[-1]


# A workflow whose direction stage requires the artist, and a submission waiting for review.
inputs = out / 'inputs'
inputs.mkdir()
manifest = {'schema': 'dcc.environment.workflow.v1', 'id': 'environment', 'version': 1, 'description': 'Owner channel qualification',
            'default_review_policy': 'agent_within_brief', 'stages': [
                {'id': 'direction', 'after': [], 'skills': ['dcc-plan-environment'], 'deliverables': ['brief'], 'evidence': ['direction_record'], 'review': 'artist_required'},
                {'id': 'materials', 'after': ['direction'], 'skills': ['dcc-materials'], 'deliverables': ['materials'], 'evidence': ['visual_review'], 'review': 'agent_within_brief'},
                {'id': 'delivery', 'after': ['materials'], 'skills': ['dcc-review-continue'], 'deliverables': ['native'],
                 'evidence': ['native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'], 'review': 'agent_within_brief'}]}
write_json(inputs / 'manifest.json', manifest)
skills = ('dcc-plan-environment', 'dcc-materials', 'dcc-review-continue')
for skill in skills:
    (inputs / 'skills' / skill).mkdir(parents=True)
    shutil.copyfile(REPO / '.agents/skills' / skill / 'SKILL.md', inputs / 'skills' / skill / 'SKILL.md')
active = cli('next', project)['active']
binding = {'schema': 'dcc.environment.binding.v1', 'checkpoint': {'checkpoint_id': active['id'], 'checkpoint_sha256': active['checkpoint_sha256']},
           'authority': {'role': 'agent', 'author': 'qualification', 'reference': 'Owner channel qualification'},
           'review_policies': {}, 'inherited': {}, 'references': [], 'skill_files': {s: [{'path': f'skills/{s}/SKILL.md'}] for s in skills}}
write_json(inputs / 'binding.draft.json', binding)
cli('fill-hashes', inputs / 'binding.draft.json', inputs / 'binding.json')
relaxed = json.loads((inputs / 'binding.json').read_text(encoding='utf-8'))
relaxed['review_policies'] = {'direction': 'agent_within_brief'}
write_json(inputs / 'binding.relaxed.json', relaxed)
summary = {'runtime': str(runtime), 'version': dcc_harness.__version__, 'agent_markers_set': markers}
proc = run('workflow-bind', project, '--binding', inputs / 'binding.relaxed.json', '--manifest', inputs / 'manifest.json',
           '--expected-revision', cli('next', project)['revision'], '--request-id', uuid.uuid4())
assert proc.returncode != 0 and 'Relaxing an artist-required stage' in proc.stderr, proc.stderr[-800:]
summary['relaxing_binding_by_agent'] = 'refused'
cli('workflow-bind', project, '--binding', inputs / 'binding.json', '--manifest', inputs / 'manifest.json',
    '--expected-revision', cli('next', project)['revision'], '--request-id', uuid.uuid4())
(inputs / 'direction.md').write_text('A small workbench corner: matte timber, soft key light.\n', encoding='utf-8')
skeleton = cli('requirements', project, 'direction')['skeleton']
skeleton.update(deliverables={'brief': 'Direction for the workbench corner'}, evidence=[{'kind': 'direction_record', 'file': {'path': 'direction.md'}}],
                note='Direction for the artist to approve.', questions=[{'id': 'finish', 'text': 'Timber finish?', 'choices': ['Oiled', 'Raw'], 'default': 'Oiled'}])
write_json(inputs / 'stage.draft.json', skeleton)
cli('fill-hashes', inputs / 'stage.draft.json', inputs / 'stage.json')
submitted = cli('stage-submit', project, '--submission', inputs / 'stage.json', '--expected-revision', cli('next', project)['revision'],
                '--request-id', uuid.uuid4())
step = next(s for s in cli('next', project)['steps'] if s['id'] == 'stage-complete')
assert step['artist_required'] and 'own terminal' in step['why'], step
summary['next_step'] = step['why']

# The page, with renders of both checkpoints.
write_json(out / 'views.json', {'schema': 'dcc.review.views.v1', 'render': {'engine': 'CYCLES', 'resolution': [320, 200], 'samples': 8, 'seed': 0},
           'views': [{'id': 'REVIEW_WHOLE', 'purpose': 'whole', 'camera': {'object_id': 'review.camera'}}]})
built = cli('review-page', project, '--output-dir', out / 'page', '--blender', a.blender, '--views', out / 'views.json')
assert built['submission'] == submitted['revision']
data = read_json(out / 'page/page.json')
source = {'role': 'artist', 'author': 'Qualification reviewer', 'reference': 'Review page ' + built['page_digest'][:12]}
note = {'schema': 'dcc.feedback.note.v1', 'source': source, 'stage_id': None, 'category': 'visual', 'priority': 'advisory',
        'text': 'Soften the key light a little', 'acceptance': 'No hard shadow under the bench top',
        'anchor': {'checkpoint_id': data['to']['id'], 'checkpoint_sha256': data['to']['checkpoint_sha256'], 'instance_ids': ['bench.top']}}
review = {'reviewer': source, 'verdict': 'pass', 'finding': 'Direction approved', 'answers': {'finish': 'Raw'}}


def export(name, review=None, notes=()):
    path = out / name
    path.write_text(json.dumps({'schema': 'dcc.review.export.v1', 'page': built['page_digest'], 'review': review, 'notes': list(notes)}), encoding='utf-8')
    return path


approval = export('export-approval.json', review, [note])
write_json(inputs / 'artist-review.json', review)
complete = ('stage-complete', project, '--submission-id', submitted['revision'], '--review', inputs / 'artist-review.json',
            '--expected-revision', submitted['revision'], '--request-id', uuid.uuid4())
summary['refusals'] = {
    'review_import_in_agent_session': refused(('review-import', project, approval, '--page', out / 'page'), 'agent session'),
    'review_import_piped_without_markers': refused(('review-import', project, approval, '--page', out / 'page'), 'interactive terminal'),
    'stage_complete_in_agent_session': refused(complete, 'agent session'),
    'stage_complete_piped_without_markers': refused(complete, 'interactive terminal')}
write_json(inputs / 'agent-review.json', {**review, 'reviewer': {**source, 'role': 'agent'}})
proc = run('stage-complete', project, '--submission-id', submitted['revision'], '--review', inputs / 'agent-review.json',
           '--expected-revision', submitted['revision'], '--request-id', uuid.uuid4())
assert proc.returncode != 0 and 'Artist review is required' in proc.stderr, proc.stderr[-800:]
summary['refusals']['agent_review_of_artist_stage'] = 'Artist review is required by the stage policy'

# The owner, through a scripted console.
console = ScriptedOwner()
first = review_page.import_review(project, approval, out / 'page', console)
assert [(r['kind'], r['status']) for r in first['results']] == [('stage.complete', 'COMMITTED'), ('feedback.add', 'COMMITTED')], first
completed = c.read(project)[-2]['result']
assert completed['artistic_acceptance'] == 'artist_confirmed' and completed['owner_approval']['channel'] == 'owner_terminal', completed
assert 'Direction approved' in console.shown[0] and "finish" in console.shown[0]
again = cli('review-import', project, approval, '--page', out / 'page')
assert [r['status'] for r in again['results']] == ['ALREADY_COMMITTED', 'ALREADY_COMMITTED'], again
notes_only = cli('review-import', project, export('export-notes.json', None, [{**note, 'text': 'Keep the shelf clear'}]), '--page', out / 'page')
assert [r['status'] for r in notes_only['results']] == ['COMMITTED'], notes_only
summary['owner'] = {'prompt': console.shown[0], 'receipt': {k: completed[k] for k in ('artistic_acceptance', 'owner_approval', 'answers')},
                    'replay_from_agent_session': 'ALREADY_COMMITTED', 'notes_only_from_agent_session': 'COMMITTED'}
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
