"""Native qualification of render and render-wait on the comparison fixture.

Renders the fixture's active checkpoint twice and a copy with a moved camera, checks
determinism and the settings digest, commits a feedback response citing the evidence
entries, renders from a project's review_views decision through the command `next`
prints, runs two detached jobs that must not overlap, and checks the failure paths.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
PREPARED = REPO / 'runs/step-cost-comparison-2026-10-06/prepared'
NOTE = '7e016b63-3642-49ba-a4d1-caf2380d6824'

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout; omit for installed package testing')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
import dcc_harness
from dcc_harness.evidence import file_hash, read_json, write_json

runtime = Path(dcc_harness.__file__).resolve().parent.parent
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)


def cli(*args, expect=0):
    proc = subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], cwd=runtime, capture_output=True, text=True)
    assert proc.returncode == expect if expect is not None else proc.returncode != 0, (args, proc.returncode, proc.stderr[-2000:])
    return json.loads(proc.stdout) if proc.stdout.strip() else None, proc.stderr


VIEWS = {'schema': 'dcc.review.views.v1', 'render': {'engine': 'CYCLES', 'resolution': [320, 200], 'samples': 8, 'seed': 0},
         'views': [{'id': 'REVIEW_WHOLE', 'purpose': 'whole', 'camera': {'object_id': 'review.camera'}},
                   {'id': 'REVIEW_DETAIL', 'purpose': 'detail', 'camera': {'object_id': 'review.camera'}, 'border': [0.18, 0.77, 0.15, 0.66]},
                   {'id': 'BENCH', 'purpose': 'detail', 'camera': {'lens': 35, 'location': [3.0, -4.0, 2.0], 'target': [0.0, 0.0, 0.6]}}]}
summary = {'runtime': str(runtime), 'version': dcc_harness.__version__}
project = out / 'project'
shutil.copytree(PREPARED / 'project', project)
scene = out / 'scene.blend'
shutil.copyfile(project / 'checkpoints/000002/checkpoint.blend', scene)
source_sha = file_hash(scene)
write_json(out / 'views.json', VIEWS)

# Two renders of the same saved file: bound, complete and identical.
first, _ = cli('render', scene, '--blender', a.blender, '--output-dir', out / 'r1', '--views', out / 'views.json')
second, _ = cli('render', scene, '--blender', a.blender, '--output-dir', out / 'r2', '--views', out / 'views.json')
assert first['status'] == 'RENDERED' and first['source_unchanged'] and file_hash(scene) == source_sha, first
receipt = read_json(first['receipt'])
assert receipt['checkpoint_sha256'] == source_sha and set(receipt['images']) == {'REVIEW_WHOLE', 'REVIEW_DETAIL', 'BENCH'}
for path in first['images'].values():
    assert Path(path).read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', path
settings = read_json(first['settings'])
assert settings['resolved']['views']['BENCH']['review_only_camera'] is True
same_images = {v: file_hash(first['images'][v]) == file_hash(second['images'][v]) for v in first['images']}
summary['repeat'] = {'same_digest': first['views_digest'] == second['views_digest'], 'same_images': same_images,
                     'seconds': [first['seconds'], second['seconds']]}
assert summary['repeat']['same_digest'] and all(same_images.values()), summary['repeat']

# A moved camera changes the settings digest and the camera's images.
moved = out / 'moved.blend'
expression = ('import bpy; o = next(o for o in bpy.data.objects if o.get("dcc_instance_id") == "review.camera"); '
              f'o.location.x += 0.5; bpy.ops.wm.save_as_mainfile(filepath={str(moved)!r}, copy=True)')
subprocess.run([a.blender, '--background', '--factory-startup', '--disable-autoexec', str(scene), '--python-exit-code', '1',
                '--python-expr', expression], check=True, capture_output=True)
shifted, _ = cli('render', moved, '--blender', a.blender, '--output-dir', out / 'r-moved', '--views', out / 'views.json')
assert shifted['views_digest'] != first['views_digest']
assert file_hash(shifted['images']['REVIEW_WHOLE']) != file_hash(first['images']['REVIEW_WHOLE'])
assert file_hash(shifted['images']['BENCH']) == file_hash(first['images']['BENCH']), 'review-only camera should not move'
summary['moved_camera'] = {'digest_changed': True, 'whole_changed': True, 'review_only_unchanged': True}

# EEVEE under the name Blender 5.1 accepts.
eevee = {**VIEWS, 'render': {'engine': 'BLENDER_EEVEE', 'resolution': [320, 200], 'samples': 4, 'seed': 0}, 'views': VIEWS['views'][:1]}
write_json(out / 'views-eevee.json', eevee)
result, _ = cli('render', scene, '--blender', a.blender, '--output-dir', out / 'r-eevee', '--views', out / 'views-eevee.json')
summary['eevee'] = result['status']

# Failure paths: a missing camera fails in Blender with a plain message; an existing folder fails first.
missing = {**VIEWS, 'views': [{'id': 'NOPE', 'purpose': 'whole', 'camera': {'object_id': 'no.such.camera'}}]}
write_json(out / 'views-missing.json', missing)
cli('render', scene, '--blender', a.blender, '--output-dir', out / 'r-missing', '--views', out / 'views-missing.json', expect=None)
status = read_json(out / 'r-missing/status.json')
log = (out / 'r-missing/render.log').read_text(encoding='utf-8', errors='replace')
assert status['state'] == 'failed' and 'no camera with stable ID no.such.camera' in log, status
_, error = cli('render', scene, '--blender', 'no-blender-should-launch', '--output-dir', out / 'r1', '--views', out / 'views.json', expect=None)
assert 'FileExistsError' in error and not (out / 'r1/render.log.1').exists()
summary['failures'] = {'missing_camera': 'failed in Blender with a plain message', 'existing_folder': 'refused before launch'}

# The evidence entries commit in a feedback response on the fixture project (its active checkpoint is scene.blend).
plan, _ = cli('next', project)
active = plan['active']
assert active['checkpoint_sha256'] == source_sha
write_json(out / 'response.draft.json', {
    'schema': 'dcc.feedback.response.v1', 'note_id': NOTE, 'author': 'render-qualification', 'disposition': 'partial',
    'change': 'Qualification only: rendered the unchanged checkpoint with the packaged render command; no edit was made.',
    'result': {'checkpoint_id': active['id'], 'checkpoint_sha256': active['checkpoint_sha256']},
    'evidence': [e for e in first['evidence'] if e['render']['view_id'] in ('REVIEW_WHOLE', 'REVIEW_DETAIL')]})
cli('fill-hashes', out / 'response.draft.json', out / 'response.json')
committed, _ = cli('feedback-respond', project, '--response', out / 'response.json', '--expected-revision', plan['revision'],
                   '--request-id', uuid.uuid4())
assert committed['status'] == 'COMMITTED' and all(r['passed'] for r in committed['result']['reports']), committed
summary['response'] = {'status': committed['status'], 'reports': [r['kind'] for r in committed['result']['reports']]}

# A project whose decisions carry review_views: run the render command that `next` prints.
observed, _ = cli('observe', scene, '--blender', a.blender, '--output-dir', out / 'observe-scene')
(out / 'BRIEF.md').write_text('Render qualification project; not a production scene.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Render the review views; nothing else.\n', encoding='utf-8')
write_json(out / 'decisions.json', {'review_views': VIEWS})
cli('start', out / 'views-project', '--checkpoint', scene, '--observation', observed['observation'], '--brief-file',
    out / 'BRIEF.md', '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
steps = {s['id']: s for s in cli('next', out / 'views-project')[0]['steps']}
command = steps['render']['command'].replace('<BLENDER>', a.blender).replace('<new folder>', (out / 'r-project').as_posix())
assert '<' not in command, command
printed, _ = cli(*shlex.split(command)[3:])
assert printed['status'] == 'RENDERED' and printed['views_digest'] == first['views_digest'], printed
summary['project_views'] = {'status': printed['status'], 'same_digest_as_views_file': True}

# Two detached jobs started together run one after the other.
jobs = []
for name in ('j1', 'j2'):
    queued, _ = cli('render', scene, '--blender', a.blender, '--output-dir', out / name, '--views', out / 'views.json', '--detach')
    assert queued['status'] == 'QUEUED', queued
    jobs.append(queued['job'])
finals = []
for job in jobs:
    for _ in range(12):
        state, _ = cli('render-wait', job, '--timeout', 30)
        if state['state'] in ('done', 'failed'):
            break
    assert state['state'] == 'done', state
    finals.append(state)
spans = sorted((f['started_at'], f['finished_at']) for f in finals)
assert spans[0][1] <= spans[1][0], spans
assert all(f['result']['views_digest'] == first['views_digest'] for f in finals)
summary['detached'] = {'states': [f['state'] for f in finals], 'spans': spans, 'overlap': False}

summary['source_unchanged'] = file_hash(scene) == source_sha
assert summary['source_unchanged']
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
