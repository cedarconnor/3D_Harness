"""Native qualification of coverage gaps (build-plan item G2).

Builds a scene with a shader group nested in another group, a scatter Geometry Nodes tree and an
empty material slot, then five variants. The base scene must observe READY with two listed gaps
(the nested shader group is fully measured and is not one), start a project, and publish an edit
with the gaps listed in its outcome. Changing the nested shader group, the scatter tree, a scatter
input or the empty slot must each fail a contract that does not grant it. A missing texture still
refuses, and an observation without gap records still reads.
"""
from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, out = q.args, q.out
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import coverage_gaps, read_json, write_json

q.blender('scenes.log', '--python', REPO / 'scripts/coverage_gaps_native_probe.py', '--', '--out', out / 'scenes')
NAMES = ('base', 'group-changed', 'scatter-changed', 'scatter-input', 'slot-filled', 'missing-texture')
reports = {name: q.cli('observe', out / 'scenes' / f'{name}.blend', '--blender', a.blender, '--output-dir', out / f'observe-{name}',
                       expect=1 if name == 'missing-texture' else 0) for name in NAMES}
observed = {name: reports[name]['observation'] for name in NAMES}
obs = {name: read_json(observed[name]) for name in NAMES}
summary = {'blender': obs['base']['blender']}

# Two gaps, no issues; the nested shader group is measured, not a gap.
base = reports['base']
assert base['status'] == 'READY' and base['issues'] == [], base
gaps = {(g['code'], g['object']) for g in base['coverage_gaps']}
assert gaps == {('EMPTY_MATERIAL_SLOT', 'crate'), ('GEOMETRY_NODES_UNDESCRIBED', 'bed')}, gaps
scatter = next(g for g in base['coverage_gaps'] if g['code'] == 'GEOMETRY_NODES_UNDESCRIBED')
assert scatter['hash_complete'] is True and len(scatter['opaque_sha256']) == 64, scatter
wear = next(n for n in obs['base']['materials']['worn']['graph']['nodes'] if n['name'] == 'Wear')
assert wear['graph']['nodes'] and any(n.get('graph') for n in wear['graph']['nodes']), 'nested shader group was not recorded'
summary['base'] = {'status': base['status'], 'gaps': sorted(map(list, gaps))}

# A missing texture is an integrity problem and keeps refusing.
missing = reports['missing-texture']
assert missing['status'] == 'HAS_ISSUES' and any(i.startswith('Missing image') for i in missing['issues']), missing
summary['missing_texture'] = missing['issues']

# Each change fails a contract that grants nothing, and passes once its field is granted.
REQUIRED = {'bench': {'type': 'MESH'}, 'bed': {'type': 'MESH'}, 'crate': {'type': 'MESH'}, 'ground': {'type': 'MESH'}}


def stage(candidate, **rules):
    return evaluate_stage(obs['base'], obs[candidate], {'schema': 'dcc.continuity.contract.v1',
                                                        'spec': {'schema': 'dcc.spec.v1', 'required': REQUIRED}, **rules})


def changed(candidate):
    return sorted((c['category'], c['id'], c['field']) for c in stage(candidate)['preservation']['changes'])


assert stage('base')['passed'] and len(stage('base')['coverage_gaps']) == 2
expected = {'group-changed': [('materials', 'worn', 'graph')],
            'scatter-changed': [('objects', 'bed', 'modifier_settings')],
            'scatter-input': [('objects', 'bed', 'modifier_settings')],
            'slot-filled': [('objects', 'crate', 'material_ids')]}
for name, fields in expected.items():
    result = stage(name)
    assert not result['passed'] and changed(name) == fields, (name, changed(name))
assert stage('scatter-changed', allowed_object_prefixes={'bed': ['modifier_settings']})['passed']
assert stage('slot-filled', allowed_object_prefixes={'crate': ['material_ids']})['passed']
assert len(stage('slot-filled', allowed_object_prefixes={'crate': ['material_ids']})['coverage_gaps']) == 1
summary['detected'] = {name: [list(f) for f in fields] for name, fields in expected.items()}

# An observation without gap records still reads and compares as before.
legacy = read_json(observed['base'])
legacy['coverage'].pop('gaps')
assert coverage_gaps(legacy) == []

# A project starts on the gapped scene, refuses an ungranted scatter change and publishes a granted one.
(out / 'BRIEF.md').write_text('A bench, a scattered bed and a crate; qualification fixture.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the saved scene.\n', encoding='utf-8')
write_json(out / 'decisions.json', {})
write_json(out / 'updates.json', {})
(out / 'edit.py').write_text('# Reserved for qualification; the candidates were built beforehand.\n', encoding='utf-8')
project = out / 'project'
q.cli('start', project, '--checkpoint', out / 'scenes/base.blend', '--observation', observed['base'], '--brief-file', out / 'BRIEF.md',
      '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')


def edit(label, candidate, rules, expect):
    contract = out / f'contract-{label}.json'
    write_json(contract, {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': REQUIRED}, **rules})
    state = q.cli('next', project)['active']
    reserved = q.cli('begin-edit', project, '--parent', state['id'], '--current', out / 'scenes/base.blend', '--observation',
                     observed['base'], '--script', out / 'edit.py', '--contract', contract, '--label', label)
    outcome = q.cli('finish-edit', project, reserved['edit'], '--checkpoint', out / 'scenes' / f'{candidate}.blend', '--observation',
                    observed[candidate], '--handoff', out / 'HANDOFF.md', '--updates', out / 'updates.json',
                    expect=0 if expect == 'PUBLISHED' else 1)
    assert outcome['status'] == expect, (label, outcome['status'], outcome.get('failures'))
    return outcome


edit('scatter-refused', 'scatter-changed', {}, 'REJECTED_RETAINED')
edit('scatter-density', 'scatter-changed', {'allowed_object_prefixes': {'bed': ['modifier_settings']}}, 'PUBLISHED')
summary['project'] = {'ungranted': 'REJECTED_RETAINED', 'granted': 'PUBLISHED'}
q.finish(summary)
