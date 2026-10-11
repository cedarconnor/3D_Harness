"""Native qualification of brief, next and requirements on copies of real projects.

Runs the printed commands themselves where they need no agent input: the observe and
begin-edit steps from `next` are filled in and executed, then `next` must offer only the
reserved edit's finish. Every other command must leave the copied stores unchanged.
"""
import hashlib
import json
from pathlib import Path
import shlex
import shutil

REPO = Path(__file__).resolve().parents[1]
NOTES = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project'
BOUND = REPO / 'runs/feedback-2026-10-06/source/project'

from _launcher import Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
import dcc_harness



def cli(*args):
    proc = q.run(*args)
    return proc.returncode, proc.stdout, proc.stderr


def tree(root):
    return {q.relative_to(root).as_posix(): hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(root.rglob('*')) if q.is_file()}


def run_printed(command, **values):
    for key, value in values.items():
        command = command.replace(key, str(value))
    assert '<' not in command, command
    args = shlex.split(command)
    assert args[:3] == ['python', '-m', 'dcc_harness'], args
    return cli(*args[3:])


summary = {'runtime': str(runtime), 'version': dcc_harness.__version__}
notes, bound = out / 'notes-project', out / 'bound-project'
shutil.copytree(NOTES, notes)
shutil.copytree(BOUND, bound)
before = {'notes': tree(notes), 'bound': tree(bound)}

# Read-only commands on a project with open notes and no bound workflow.
code, text, error = cli('brief', notes, '--out', out / 'notes-brief.md')
assert code == 0 and text.startswith('# 3D Harness project brief'), (code, error)
assert '### Note 7e016b63-3642-49ba-a4d1-caf2380d6824' in text and 'Acceptance:' in text, text
code, raw, error = cli('next', notes)
assert code == 0, error
plan = json.loads(raw)
assert [s['id'] for s in plan['steps']] == ['observe', 'begin-edit', 'feedback-respond'], plan['steps']
code, raw, error = cli('requirements', notes, 'materials')
assert code != 0 and 'Bind an environment workflow first' in error, (code, error)
summary['notes'] = {'status': plan['status'], 'steps': [s['id'] for s in plan['steps']]}

# Read-only commands on a project with a bound workflow whose materials stage was reopened by a note.
code, text, error = cli('brief', bound, '--out', out / 'bound-brief.md')
assert code == 0 and '| materials | needs_review |' in text and '| delivery | blocked |' in text, (code, error)
code, raw, error = cli('requirements', bound, 'materials')
assert code == 0, error
materials = json.loads(raw)
assert materials['state'] == 'needs_review' and not materials['blocked_by'], materials
assert materials['skeleton']['checkpoint']['checkpoint_id'] == json.loads(cli('next', bound)[1])['active']['id']
code, raw, error = cli('requirements', bound, 'delivery')
assert code == 0, error
delivery = json.loads(raw)
assert delivery['state'] == 'blocked' and 'lighting' in delivery['blocked_by'], delivery
assert {'native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'} <= {e['kind'] for e in delivery['evidence']}
code, raw, error = cli('next', bound)
assert code == 0, error
bound_steps = json.loads(raw)['steps']
assert {('feedback-respond', s.get('note_id')) for s in bound_steps if s['id'] == 'feedback-respond'} == {
    ('feedback-respond', '254aac0d-2509-4b65-8c57-5e07200b14e6')}, bound_steps
assert [s.get('stage_id') for s in bound_steps if s['id'] == 'stage-submit'] == ['materials'], bound_steps
summary['bound'] = {'status': json.loads(raw)['status'], 'steps': [s['id'] for s in bound_steps],
                    'materials_feedback_ids': len(materials['feedback_ids']), 'delivery_blocked_by': delivery['blocked_by']}
assert tree(notes) == before['notes'] and tree(bound) == before['bound'], 'a read-only command changed a store'

# Execute the printed observe and begin-edit commands, then next must offer only the finish.
work = out / 'work'
work.mkdir()
(work / 'edit.py').write_text('# Reserved for qualification; never executed.\n', encoding='utf-8')
(work / 'contract.json').write_text(json.dumps({'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
    'spec': {'schema': 'dcc.spec.v1', 'required': {'bench.top': {'type': 'MESH'}}}}), encoding='utf-8')
steps = {s['id']: s for s in plan['steps']}
code, raw, error = run_printed(steps['observe']['command'], **{'<BLENDER>': a.blender, '<new folder>': (work / 'observe').as_posix()})
assert code == 0 and json.loads(raw)['status'] == 'READY', (code, error)
code, raw, error = run_printed(steps['begin-edit']['command'], **{'<new folder>': (work / 'observe').as_posix(),
    '<edit .py>': (work / 'edit.py').as_posix(), '<contract .json>': (work / 'contract.json').as_posix(),
    '<new step label>': 'guidance-qualification'})
assert code == 0, error
edit = json.loads(raw)['edit']
code, raw, error = cli('next', notes)
reserved = json.loads(raw)
assert reserved['status'] == 'RECONCILE' and [s['id'] for s in reserved['steps']] == ['finish-edit'], reserved
assert reserved['steps'][0]['edit'] == edit and ' ' + edit + ' ' in reserved['steps'][0]['command']
code, text, error = cli('brief', notes)
assert code == 0 and '`RECONCILE`' in text and 'finish-edit' in text, (code, error)
summary['reserved'] = {'edit': edit, 'steps': [s['id'] for s in reserved['steps']]}

summary['passed'] = True
(out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
