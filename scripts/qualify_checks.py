"""Native qualification of learned checks: propose, approve, pin and run, on the relations probe's bench scenes.

Project A starts on the raised bench. An artist note says it floats; an over-correction sinks the
legs and a second note says so; a third edit fixes it. The agent proposes a supported_by check
(measured natively on the raised and fixed checkpoints) and an object_field check, and a field
check against the floating note is refused because it passes there. Approval from this agent
session is refused; a scripted console stands in for the owner's terminal. Project B starts on the
sunk bench and pins the library: its assembly submission fails both checks and completion is
refused; a note there counts a repeat; after the fix, both pass and the stage completes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout; omit for installed package testing')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
import dcc_harness
from dcc_harness import checks, owner
from dcc_harness.evidence import read_json, write_json

runtime = Path(dcc_harness.__file__).resolve().parent.parent
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
assert any(os.environ.get(m) for m in owner.AGENT_MARKERS), 'Run this from an agent session'
library = out / 'library'
summary = {'runtime': str(runtime), 'version': dcc_harness.__version__}


def run(*args):
    return subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], cwd=runtime, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def cli(*args, expect=0):
    proc = run(*args)
    assert proc.returncode == expect, (args, proc.returncode, proc.stderr[-2000:])
    return json.loads(proc.stdout)


def refused(args, message):
    proc = run(*args)
    assert proc.returncode != 0 and message in proc.stderr, (args, proc.stderr[-1500:])
    return proc.stderr.strip().splitlines()[-1].split(': ', 1)[-1]


class ScriptedOwner:
    environ, shown = {}, []

    def isatty(self):
        return True

    def ask(self, text):
        self.shown.append(text)
        return re.search(r'Type ([A-Z0-9]{4})', text).group(1)


probe = REPO / 'scripts/relations_native_probe.py'
with (out / 'scenes.log').open('x', encoding='utf-8') as log:
    subprocess.run([a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                    '--python', str(probe), '--', '--out', str(out / 'scenes')], stdout=log, stderr=subprocess.STDOUT, check=True)
observed = {name: cli('observe', out / 'scenes' / f'{name}.blend', '--blender', a.blender, '--output-dir', out / f'observe-{name}')['observation']
            for name in ('raised', 'sunk', 'flat')}
(out / 'edit.py').write_text('# Reserved for qualification; the candidates were built by the probe.\n', encoding='utf-8')
write_json(out / 'contract.json', {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
           'allowed_object_prefixes': {'bench.': ['matrix_world', 'bounds']},
           'spec': {'schema': 'dcc.spec.v1', 'required': {'bench.top': {'type': 'MESH'}, 'ground': {'type': 'MESH'}}}})
write_json(out / 'updates.json', {})


def start(project, scene, brief):
    (out / f'{project.name}-BRIEF.md').write_text(brief + '\n', encoding='utf-8')
    (out / f'{project.name}-HANDOFF.md').write_text('Started from the saved scene.\n', encoding='utf-8')
    write_json(out / f'{project.name}-decisions.json', {})
    cli('start', project, '--checkpoint', out / 'scenes' / f'{scene}.blend', '--observation', observed[scene],
        '--brief-file', out / f'{project.name}-BRIEF.md', '--decisions', out / f'{project.name}-decisions.json', '--handoff', out / f'{project.name}-HANDOFF.md')


def edit(project, current, candidate, label):
    parent = cli('next', project)['active']['id']
    reserved = cli('begin-edit', project, '--parent', parent, '--current', out / 'scenes' / f'{current}.blend', '--observation', observed[current],
                   '--script', out / 'edit.py', '--contract', out / 'contract.json', '--label', label)
    (out / f'handoff-{label}.md').write_text(f'Moved the bench: {current} to {candidate}.\n', encoding='utf-8')
    outcome = cli('finish-edit', project, reserved['edit'], '--checkpoint', out / 'scenes' / f'{candidate}.blend', '--observation', observed[candidate],
                  '--handoff', out / f'handoff-{label}.md', '--updates', out / 'updates.json')
    assert outcome['status'] == 'PUBLISHED', outcome
    return active(project)


def revision(project):
    return cli('next', project)['revision'] or 'none'


def active(project):
    state = cli('next', project)['active']
    return {'checkpoint_id': state['id'], 'checkpoint_sha256': state['checkpoint_sha256']}


def note(project, at, text):
    path = out / f'note-{uuid.uuid4().hex[:8]}.json'
    write_json(path, {'schema': 'dcc.feedback.note.v1', 'source': {'role': 'artist', 'author': 'Qualification artist', 'reference': 'Review'},
                      'stage_id': None, 'category': 'technical', 'priority': 'advisory', 'text': text,
                      'acceptance': 'Every leg rests on the ground', 'anchor': {**at, 'instance_ids': [f'bench.leg.{i}' for i in range(4)]}})
    return cli('feedback-add', project, '--note', path, '--expected-revision', revision(project),
               '--request-id', uuid.uuid4())['result']['note']['id']


def checkpoint_file(project, ref):
    from dcc_harness.continuity import Continuity
    return next(Path(e['checkpoint']) for e in Continuity(project).status()['task_history'] if e['id'] == ref['checkpoint_id'])


def observation_of(project, ref):
    from dcc_harness.continuity import Continuity
    return read_json(next(e['observation'] for e in Continuity(project).status()['task_history'] if e['id'] == ref['checkpoint_id']))


LEGS = {'schema': 'dcc.check.rule.v1', 'kind': 'supported_by', 'subjects': {'id': 'bench.leg.*'}, 'support': {'id': 'ground'},
        'max_gap': 0.005, 'max_penetration': 0.01, 'footprint': 0.002}
BELOW = {'schema': 'dcc.check.rule.v1', 'kind': 'object_field', 'select': {'type': 'MESH', 'id': 'bench.*'}, 'field': 'bounds.min.z', 'min': -0.005}

# Project A: the errors and their fixes.
project_a = out / 'project-a'
start(project_a, 'raised', 'A bench standing on flat ground.')
raised = active(project_a)
floats = note(project_a, raised, 'The bench floats above the ground')
sunk = edit(project_a, 'raised', 'sunk', 'lower-bench')
sinks = note(project_a, sunk, 'The legs now sink into the ground')
fixed = edit(project_a, 'sunk', 'flat', 'rest-bench')
inputs = out / 'proposals'
inputs.mkdir()
spec = checks.resolve('bench-legs-on-ground', LEGS, observation_of(project_a, raised))
write_json(inputs / 'legs-spec.json', spec)
for side, ref, expect in (('fails', raised, 1), ('passes', fixed, 0)):
    cli('relations', checkpoint_file(project_a, ref), '--blender', a.blender, '--output-dir', inputs / f'legs-{side}', '--spec', inputs / 'legs-spec.json', expect=expect)


def propose(project, payload, name, expect_refusal=None):
    write_json(inputs / f'{name}.draft.json', payload)
    cli('fill-hashes', inputs / f'{name}.draft.json', inputs / f'{name}.json')
    args = ('check-propose', project, '--proposal', inputs / f'{name}.json', '--expected-revision', revision(project),
            '--request-id', uuid.uuid4())
    if expect_refusal:
        return refused(args, expect_refusal)
    return cli(*args)


proposer = {'role': 'agent', 'author': 'qualification', 'reference': 'Checks qualification'}
legs = propose(project_a, {'schema': 'dcc.check.proposal.v1', 'id': 'bench-legs-on-ground', 'note_id': floats, 'classification': 'error',
                           'rule': LEGS, 'stages': ['assembly'], 'rationale': 'Furniture legs rest on the ground: no gap, no penetration',
                           'proposer': proposer,
                           'fails': {'checkpoint': raised, 'measurement': {'path': 'legs-fails/measurement.json'}},
                           'passes': {'checkpoint': fixed, 'measurement': {'path': 'legs-passes/measurement.json'}}}, 'legs')
assert legs['result']['results']['fails']['status'] == 'FAIL' and legs['result']['results']['passes']['status'] == 'PASS'
below = {'schema': 'dcc.check.proposal.v1', 'id': 'nothing-below-ground', 'note_id': floats, 'classification': 'error', 'rule': BELOW,
         'stages': ['assembly'], 'rationale': 'No part of the furniture goes below the ground plane', 'proposer': proposer,
         'fails': {'checkpoint': raised}, 'passes': {'checkpoint': fixed}}
summary['refused_proposals'] = {
    'field_check_on_the_floating_note': propose(project_a, below, 'below-wrong', 'The rule does not fail on the note'),
    'taste': propose(project_a, {**below, 'note_id': sinks, 'fails': {'checkpoint': sunk}, 'classification': 'taste'}, 'below-taste', 'Taste stays')}
below_ok = propose(project_a, {**below, 'note_id': sinks, 'fails': {'checkpoint': sunk}}, 'below')
summary['proposals'] = {x['result']['check_id']: {s: x['result']['results'][s]['status'] for s in ('fails', 'passes')} for x in (legs, below_ok)}

# Approval: refused from the agent session, then the scripted owner.
summary['refused_approval'] = refused(('check-approve', library, '--project', project_a, '--proposal', legs['revision'], '--expected-version', 0),
                                      'agent session')
assert not (library / 'versions').exists()
console = ScriptedOwner()
for proposal in (legs, below_ok):
    approved = checks.approve(library, project_a, proposal['revision'], checks.read_library(library)['version'], console)
    assert approved['status'] == 'APPROVED', approved
listed = cli('checks', library, '--export', out / 'pinned-library.json')
assert listed['version'] == 2 and {x['id'] for x in listed['checks']} == {'bench-legs-on-ground', 'nothing-below-ground'}, listed
summary['library'] = {'version': 2, 'prompt': console.shown[0]}

# Project B: a new project pins the library and makes the same mistake.
project_b = out / 'project-b'
start(project_b, 'sunk', 'A bench standing on flat ground, second project.')
bind_in = out / 'bind-b'
bind_in.mkdir()
manifest = {'schema': 'dcc.environment.workflow.v1', 'id': 'environment', 'version': 1, 'description': 'Checks qualification',
            'default_review_policy': 'agent_within_brief', 'stages': [
                {'id': 'assembly', 'after': [], 'skills': ['dcc-environment-assembly'], 'deliverables': ['layout'], 'evidence': ['direction_record'], 'review': 'agent_within_brief'},
                {'id': 'delivery', 'after': ['assembly'], 'skills': ['dcc-review-continue'], 'deliverables': ['native'],
                 'evidence': ['native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'], 'review': 'agent_within_brief'}]}
write_json(bind_in / 'manifest.json', manifest)
for skill in ('dcc-environment-assembly', 'dcc-review-continue'):
    (bind_in / 'skills' / skill).mkdir(parents=True)
    shutil.copyfile(REPO / '.agents/skills' / skill / 'SKILL.md', bind_in / 'skills' / skill / 'SKILL.md')
shutil.copyfile(out / 'pinned-library.json', bind_in / 'library.json')
write_json(bind_in / 'binding.draft.json', {'schema': 'dcc.environment.binding.v1', 'checkpoint': active(project_b),
           'authority': proposer, 'review_policies': {}, 'inherited': {}, 'references': [],
           'skill_files': {s: [{'path': f'skills/{s}/SKILL.md'}] for s in ('dcc-environment-assembly', 'dcc-review-continue')},
           'checks': {'path': 'library.json'}})
cli('fill-hashes', bind_in / 'binding.draft.json', bind_in / 'binding.json')
bound = cli('workflow-bind', project_b, '--binding', bind_in / 'binding.json', '--manifest', bind_in / 'manifest.json',
            '--expected-revision', revision(project_b), '--request-id', uuid.uuid4())
assert bound['result']['checks']['version'] == 2, bound['result']['checks']


def submit(project, label):
    folder = out / f'submit-{label}'
    folder.mkdir()
    needed = cli('requirements', project, 'assembly')
    statuses = {x['id']: x['now'] for x in needed['checks']}
    relation = next(x for x in needed['checks'] if x['id'] == 'bench-legs-on-ground')
    write_json(folder / 'spec.json', relation['spec'])
    command = (relation['command'].replace('<BLENDER>', a.blender).replace('<new folder>', (folder / 'legs').as_posix())
               .replace('<this spec saved as .json>', (folder / 'spec.json').as_posix()))
    assert '<' not in command, command
    measured = cli(*shlex.split(command)[3:], expect=0 if label == 'fixed' else 1)
    (folder / 'layout.md').write_text('Bench placed on the ground.\n', encoding='utf-8')
    skeleton = needed['skeleton']
    skeleton.update(deliverables={'layout': 'Bench on the ground'}, evidence=[{'kind': 'direction_record', 'file': {'path': 'layout.md'}}],
                    note='Assembly for review', check_measurements={'bench-legs-on-ground': {'path': 'legs/measurement.json'}})
    write_json(folder / 'stage.draft.json', skeleton)
    cli('fill-hashes', folder / 'stage.draft.json', folder / 'stage.json')
    submitted = cli('stage-submit', project, '--submission', folder / 'stage.json', '--expected-revision', revision(project),
                    '--request-id', uuid.uuid4())
    write_json(folder / 'review.json', {'reviewer': proposer, 'verdict': 'pass', 'finding': 'Checked the layout'})
    args = ('stage-complete', project, '--submission-id', submitted['revision'], '--review', folder / 'review.json',
            '--expected-revision', submitted['revision'], '--request-id', uuid.uuid4())
    return statuses, measured['passed'], submitted, args


statuses, measured, submitted, complete = submit(project_b, 'sunk')
assert statuses == {'bench-legs-on-ground': 'NOT_MEASURED', 'nothing-below-ground': 'FAIL'}, statuses
assert submitted['result']['failed_checks'] == ['bench-legs-on-ground', 'nothing-below-ground'], submitted['result']['failed_checks']
summary['project_b_sunk'] = {'requirements': statuses, 'failed_checks': submitted['result']['failed_checks'],
                             'findings': {r['id']: [(f['id'], f['code'], f['value']) for f in r['findings']][:2] for r in submitted['result']['checks']},
                             'completion': refused(complete, 'Pinned library checks failed')}
repeat = note(project_b, active(project_b), 'The legs sink into the ground here too')
counted = cli('check-occurrence', library, '--project', project_b, '--note', repeat, '--check', 'nothing-below-ground')
ranked = cli('checks', library)['checks']
assert [(x['id'], x['count']) for x in ranked] == [('nothing-below-ground', 2), ('bench-legs-on-ground', 1)], ranked
summary['occurrence'] = {'recorded': counted['sequence'], 'ranking': [(x['id'], x['count']) for x in ranked]}
edit(project_b, 'sunk', 'flat', 'rest-bench')
statuses, measured, submitted, complete = submit(project_b, 'fixed')
assert submitted['result']['failed_checks'] == [] and measured, submitted['result']
done = cli(*complete)
assert done['status'] == 'COMMITTED', done
summary['project_b_fixed'] = {'checks': {r['id']: r['status'] for r in submitted['result']['checks']}, 'completion': done['status']}
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
