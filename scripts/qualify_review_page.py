"""Native qualification of review-page and review-import on a copy of the 0.6.0 comparison project.

Renders both checkpoints in Blender, re-observes the after checkpoint, checks the page's changes,
notes and verification, then imports an export shaped exactly as the page's script writes it (a
pinned note on the after render) and replays it. Finally binds a small workflow, submits a stage
with owner questions, rebuilds the page and imports an approval that changes one answer. Since 0.12.0
the approval needs the owner, so a scripted console stands in for the owner's terminal.
The browser interactions themselves are checked by hand; see the 0.11.0 report.
"""
import json
from pathlib import Path
import shutil
import uuid

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project'

from _launcher import Qualification, ScriptedOwner
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
import dcc_harness
from dcc_harness import coordination as c, review_page
from dcc_harness.evidence import read_json, write_json

project = out / 'project'
shutil.copytree(FIXTURE, project)


cli = q.cli


write_json(out / 'views.json', {'schema': 'dcc.review.views.v1', 'render': {'engine': 'CYCLES', 'resolution': [320, 200], 'samples': 8, 'seed': 0},
           'views': [{'id': 'REVIEW_WHOLE', 'purpose': 'whole', 'camera': {'object_id': 'review.camera'}},
                     {'id': 'REVIEW_DETAIL', 'purpose': 'detail', 'camera': {'object_id': 'review.camera'}, 'border': [0.18, 0.77, 0.15, 0.66]}]})
built = cli('review-page', project, '--output-dir', out / 'page', '--blender', a.blender, '--views', out / 'views.json', '--reopen')
data = read_json(out / 'page/page.json')
assert [o['id'] for o in data['changes']['changed']] == ['bench.top'] and data['changes']['materials'][0]['id'] == 'timber', data['changes']
assert data['views_match'] and [v['id'] for v in data['views']] == ['REVIEW_DETAIL', 'REVIEW_WHOLE'], data['views']
assert data['verification']['reopened'].startswith('matches the stored observation'), data['verification']
assert len(data['notes']) == 3 and any(n['view_id'] == 'REVIEW_DETAIL' for n in data['notes'])
summary = {'runtime': str(runtime), 'version': dcc_harness.__version__,
           'page': {'changed': ['bench.top'], 'materials': ['timber'], 'views': 2, 'reopened': data['verification']['reopened']}}


def export(page_data, digest, review=None, notes=()):
    path = out / f'export-{digest[:12]}.json'
    path.write_text(json.dumps({'schema': 'dcc.review.export.v1', 'page': digest, 'review': review, 'notes': list(notes)}, indent=2), encoding='utf-8')
    return path


source = {'role': 'artist', 'author': 'Qualification reviewer', 'reference': 'Review page ' + built['page_digest'][:12]}
note = {'schema': 'dcc.feedback.note.v1', 'source': source, 'stage_id': None, 'category': 'visual', 'priority': 'advisory',
        'text': 'The bench top edge still catches a bright highlight', 'acceptance': 'The edge reads as matte timber in the detail view',
        'anchor': {'checkpoint_id': data['to']['id'], 'checkpoint_sha256': data['to']['checkpoint_sha256'], 'instance_ids': ['bench.top'],
                   'render': {**data['after_render'], 'view_id': 'REVIEW_DETAIL', 'pin': {'x': 0.397, 'y': 0.5978}}}}
path = export(data, built['page_digest'], notes=[note])
first = cli('review-import', project, path, '--page', out / 'page')
again = cli('review-import', project, path, '--page', out / 'page')
assert [r['status'] for r in first['results']] == ['COMMITTED'] and [r['status'] for r in again['results']] == ['ALREADY_COMMITTED']
rebuilt = cli('review-page', project, '--output-dir', out / 'page-2', '--before-views', out / 'page/renders/before', '--after-views', out / 'page/renders/after')
pinned = [n for n in read_json(out / 'page-2/page.json')['notes'] if n['pin']]
assert len(pinned) == 1 and pinned[0]['side'] == 'after' and pinned[0]['view_id'] == 'REVIEW_DETAIL', pinned
summary['note_import'] = {'first': 'COMMITTED', 'replay': 'ALREADY_COMMITTED', 'pinned_on_rebuilt_page': True}

# A stage waiting for review, with owner questions.
inputs = out / 'submission-input'
inputs.mkdir()
manifest = {'schema': 'dcc.environment.workflow.v1', 'id': 'environment', 'version': 1, 'description': 'Review page qualification',
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
write_json(inputs / 'binding.draft.json', {'schema': 'dcc.environment.binding.v1',
           'checkpoint': {'checkpoint_id': active['id'], 'checkpoint_sha256': active['checkpoint_sha256']},
           'authority': {'role': 'agent', 'author': 'qualification', 'reference': 'Review page qualification'},
           'review_policies': {}, 'inherited': {}, 'references': [], 'skill_files': {s: [{'path': f'skills/{s}/SKILL.md'}] for s in skills}})
cli('fill-hashes', inputs / 'binding.draft.json', inputs / 'binding.json')
cli('workflow-bind', project, '--binding', inputs / 'binding.json', '--manifest', inputs / 'manifest.json',
    '--expected-revision', cli('next', project)['revision'], '--request-id', uuid.uuid4())
(inputs / 'direction.md').write_text('A small workbench corner: matte timber, soft key light.\n', encoding='utf-8')
skeleton = cli('requirements', project, 'direction')['skeleton']
skeleton.update(deliverables={'brief': 'Direction for the workbench corner'}, evidence=[{'kind': 'direction_record', 'file': {'path': 'direction.md'}}],
                note='Direction with two choices to confirm.',
                questions=[{'id': 'finish', 'text': 'Timber finish?', 'choices': ['Oiled', 'Raw'], 'default': 'Oiled'},
                           {'id': 'light', 'text': 'Key light warmth?', 'choices': ['Neutral', 'Warm'], 'default': 'Neutral'}])
write_json(inputs / 'stage.draft.json', skeleton)
cli('fill-hashes', inputs / 'stage.draft.json', inputs / 'stage.json')
submitted = cli('stage-submit', project, '--submission', inputs / 'stage.json', '--expected-revision', cli('next', project)['revision'],
                '--request-id', uuid.uuid4())
page3 = cli('review-page', project, '--output-dir', out / 'page-3', '--before-views', out / 'page/renders/before', '--after-views', out / 'page/renders/after')
assert page3['submission'] == submitted['revision']
review = {'reviewer': {**source, 'reference': 'Review page ' + page3['page_digest'][:12]}, 'verdict': 'pass',
          'finding': 'Direction reads well; warmer key light preferred', 'answers': {'light': 'Warm'}}
imported = review_page.import_review(project, export(None, page3['page_digest'], review=review), out / 'page-3', ScriptedOwner())
assert [(r['kind'], r['status']) for r in imported['results']] == [('stage.complete', 'COMMITTED')], imported
completed = c.read(project)[-1]['result']
assert [(x['id'], x['answer'], x['used_default']) for x in completed['answers']] == [('finish', 'Oiled', True), ('light', 'Warm', False)]
assert completed['artistic_acceptance'] == 'artist_confirmed' and completed['owner_approval']['channel'] == 'owner_terminal'
summary['stage_review'] = {'stage': 'direction', 'answers': completed['answers'], 'status': 'COMMITTED'}
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
