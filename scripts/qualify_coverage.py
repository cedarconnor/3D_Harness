"""Native qualification of contract coverage and dependency-aware rechecks (build-plan item P6).

Builds the relations probe's bench scenes, then lit copies of the flat and sunk benches that add a
lamp (ext.lamp.light) and change the world background. A project starts on the flat bench with a
technical note on one leg, answered and verified. The lit edit is refused without permissions,
then published with allowed_new_lights and allowed_scene_fields; the note stays current because
its leg did not change. Moving the bench into the ground then makes it need a recheck.
"""
import uuid

from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
from dcc_harness.evidence import write_json

q.blender('scenes.log', '--python', REPO / 'scripts/relations_native_probe.py', '--', '--out', out / 'scenes')
lighter = out / 'add_lamp.py'
lighter.write_text(
    "import bpy, sys\n"
    "target = sys.argv[sys.argv.index('--') + 1]\n"
    "data = bpy.data.lights.new('lamp', 'POINT'); data.energy = 40\n"
    "lamp = bpy.data.objects.new('lamp', data); bpy.context.scene.collection.objects.link(lamp)\n"
    "lamp.location = (1.2, -1.0, 1.4); lamp['dcc_instance_id'] = 'ext.lamp.light'\n"
    "bpy.context.scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target)\n", encoding='utf-8')
for name in ('flat', 'sunk'):
    q.blender(f'lit-{name}.log', out / 'scenes' / f'{name}.blend', '--python', lighter, '--', out / 'scenes' / f'lit-{name}.blend')
observed = {name: q.cli('observe', out / 'scenes' / f'{name}.blend', '--blender', a.blender, '--output-dir', out / f'observe-{name}')['observation']
            for name in ('flat', 'lit-flat', 'lit-sunk')}
(out / 'BRIEF.md').write_text('A bench on flat ground; qualification fixture.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the saved scene.\n', encoding='utf-8')
write_json(out / 'decisions.json', {})
project = out / 'project'
q.cli('start', project, '--checkpoint', out / 'scenes/flat.blend', '--observation', observed['flat'], '--brief-file', out / 'BRIEF.md',
      '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
(out / 'edit.py').write_text('# Reserved for qualification; the candidates were built beforehand.\n', encoding='utf-8')
write_json(out / 'updates.json', {})
REQUIRED = {'bench.top': {'type': 'MESH'}, 'bench.leg.0': {'type': 'MESH'}, 'ground': {'type': 'MESH'}}


def revision():
    return q.cli('next', project)['revision'] or 'none'


def active():
    state = q.cli('next', project)['active']
    return {'checkpoint_id': state['id'], 'checkpoint_sha256': state['checkpoint_sha256']}, state


def edit(label, current, candidate, rules, expect):
    contract = out / f'contract-{label}.json'
    write_json(contract, {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': REQUIRED}, **rules})
    _, state = active()
    reserved = q.cli('begin-edit', project, '--parent', state['id'], '--current', out / 'scenes' / f'{current}.blend', '--observation',
                     observed[current], '--script', out / 'edit.py', '--contract', contract, '--label', label)
    outcome = q.cli('finish-edit', project, reserved['edit'], '--checkpoint', out / 'scenes' / f'{candidate}.blend', '--observation',
                    observed[candidate], '--handoff', out / 'HANDOFF.md', '--updates', out / 'updates.json', expect=0 if expect == 'PUBLISHED' else 1)
    assert outcome['status'] == expect, (label, outcome['status'], outcome.get('failures'))
    return outcome


def note_validity():
    note = q.cli('resume', project)['coordination']['notes'][0]
    return note['current_validity'], note['validity_reason']


# A technical note on one leg, answered with a contract and verified.
start, _ = active()
write_json(out / 'note.json', {'schema': 'dcc.feedback.note.v1', 'source': {'role': 'agent', 'author': 'qualification', 'reference': 'P6'},
           'stage_id': None, 'category': 'technical', 'priority': 'advisory', 'text': 'Keep the front-left leg exactly as built',
           'acceptance': 'The leg is unchanged', 'anchor': {**start, 'instance_ids': ['bench.leg.0']}})
nid = q.cli('feedback-add', project, '--note', out / 'note.json', '--expected-revision', revision(), '--request-id', uuid.uuid4())['result']['note']['id']
write_json(out / 'keep.json', {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': REQUIRED}})
write_json(out / 'response.draft.json', {'schema': 'dcc.feedback.response.v1', 'note_id': nid, 'author': 'qualification builder',
           'disposition': 'implemented', 'change': 'Inspected; the leg is as built', 'result': start,
           'evidence': [{'kind': 'native_contract', 'before': start, 'contract': {'path': 'keep.json'}}]})
q.cli('fill-hashes', out / 'response.draft.json', out / 'response.json')
response = q.cli('feedback-respond', project, '--response', out / 'response.json', '--expected-revision', revision(), '--request-id', uuid.uuid4())
write_json(out / 'verify.json', {'schema': 'dcc.feedback.verification.v1', 'note_id': nid, 'response_id': response['revision'],
           'reviewer': {'role': 'agent', 'author': 'qualification reviewer', 'reference': 'P6'}, 'finding': 'Contract recomputed',
           'verdict': 'pass', 'views': []})
q.cli('feedback-verify', project, '--verification', out / 'verify.json', '--expected-revision', revision(), '--request-id', uuid.uuid4())
summary = {'note': note_validity()}

# The lit edit: refused without permissions, published with them.
refused = edit('lamp-refused', 'flat', 'lit-flat', {'allowed_new_prefixes': ['ext.lamp.']}, 'REJECTED_RETAINED')
reasons = refused.get('failures') or refused.get('reasons') or []
summary['without_permissions'] = reasons[:3]
edit('lamp', 'flat', 'lit-flat', {'allowed_new_prefixes': ['ext.lamp.'], 'allowed_new_lights': ['ext.lamp.'], 'allowed_scene_fields': ['world']},
     'PUBLISHED')
summary['after_lamp'] = note_validity()
assert summary['after_lamp'] == ('current', 'targets unchanged since verification'), summary['after_lamp']

# Sinking the bench moves the leg: the note needs a recheck.
edit('sink', 'lit-flat', 'lit-sunk', {'allowed_object_prefixes': {'bench.': ['matrix_world', 'bounds']}}, 'PUBLISHED')
summary['after_sink'] = note_validity()
assert summary['after_sink'][0] == 'needs_recheck', summary['after_sink']
q.finish(summary)
