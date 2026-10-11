"""Native qualification of collection instances and linked libraries (P3).

Builds scenes and libraries with scripts/instances_native_probe.py, then checks observation,
compatibility with the previous runtime, the stored-copy library limit, scoped edits that move or
swap instances, an in-place library edit, the issue paths and adoption of an instanced collection.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from _launcher import Qualification
q = Qualification(__doc__, [('--baseline-runtime', {'required': True, 'help': 'Folder holding the previous release, for the compatibility check'})])
a, runtime, out = q.args, q.runtime, q.out
import dcc_harness
from dcc_harness.evidence import file_hash, read_json, write_json

REPO = Path(__file__).resolve().parents[1]
probe = Path(__file__).with_name('instances_native_probe.py').resolve()


cli = q.call


def blender_probe(action, folder):
    with (out / f'probe-{action}-{folder.name}.log').open('x', encoding='utf-8') as log:
        subprocess.run([a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                        '--python', str(probe), '--', action, '--out', str(folder)], stdout=log, stderr=subprocess.STDOUT, check=True)


def observe(name, folder=None, expect=0):
    folder = folder or work
    cached = out / f'observe-{folder.name}-{name}/observation.json'
    if cached.exists():
        return {'status': 'READY', 'observation': str(cached)}
    result, _ = cli('observe', folder / (name + '.blend'), '--blender', a.blender, '--output-dir', out / f'observe-{folder.name}-{name}',
                    expect=expect)
    return result


summary = {'runtime': str(runtime), 'version': dcc_harness.__version__}
work = out / 'work'
blender_probe('build', work)
shutil.copytree(work, out / 'inplace')
(work / 'lib/vanishing.blend').unlink()
sources = {p.name: file_hash(p) for p in work.glob('*.blend')}

# Observation of the instanced scene: identity, library provenance and world extent.
scene = observe('scene')
assert scene['status'] == 'READY', scene
objects = read_json(scene['observation'])['objects']
bench_a, bench_b, crate, pair = (objects[i] for i in ('bench.a', 'bench.b', 'crate.a', 'set.a'))
assert bench_a['bounds'] == [[-0.8, -0.3, 0.0], [0.8, 0.3, 0.9]] and bench_b['bounds'] == [[2.2, -0.3, 0.0], [3.8, 0.3, 0.9]], (bench_a, bench_b)
assert bench_a['instance']['definition_hash'] == bench_b['instance']['definition_hash'] and bench_a['asset_id'] == 'bench'
library = crate['instance']['library']
assert library == {'path': '//lib/crate-v1.blend', 'relative': True, 'exists': True, 'sha256': file_hash(work / 'lib/crate-v1.blend')}, library
assert crate['asset_id'] == 'crate' and crate['bounds'] == [[4.75, -0.25, 0.0], [5.25, 0.25, 0.5]]
assert pair['asset_id'] == 'bench-pair' and pair['instance']['triangles'] == 72 and abs(pair['bounds'][1][1] - 7.8) < 1e-5
assert bench_a['dimensions'] == bench_b['dimensions'] == [1.6, 0.6, 0.9], (bench_a['dimensions'], bench_b['dimensions'])
summary['observe'] = {'status': 'READY', 'instances': 4, 'library': library['path'], 'nested_triangles': 72}

# Issues that still block.
for name, expected in (('missing-library', 'Missing library: //lib/vanishing.blend'), ('verts', 'Unsupported instancer: scatter'),
                       ('override', 'Unsupported library override:'), ('no-asset-id', 'Missing asset ID: collection bench-asset')):
    result = observe(name, expect=1)
    assert result['status'] == 'HAS_ISSUES' and any(issue.startswith(expected) for issue in result['issues']), (name, result['issues'])
summary['issues'] = 'missing library, vertex instancer, library override and missing collection asset ID reported'

# Compatibility: a scene without instances observes with the same revision as the previous release.
fixture = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project/checkpoints/000002/checkpoint.blend'
current, _ = cli('observe', fixture, '--blender', a.blender, '--output-dir', out / 'compat-current')
proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'observe', str(fixture), '--blender', a.blender, '--output-dir',
                       str(out / 'compat-previous')], cwd=a.baseline_runtime, capture_output=True, text=True, check=True)
previous = json.loads(proc.stdout)
# Two Blender processes can differ by float noise in evaluated UVs; the qualified comparator accepts
# exactly that and nothing else, so compatibility means equal apart from qualified noise.
from dcc_harness.uv_guard import evaluated_uv_noise_only
now_obs, old_obs = read_json(current['observation']), read_json(previous['observation'])
differing = sorted(i for i in now_obs['objects'].keys() | old_obs['objects'].keys()
                   if now_obs['objects'].get(i) != old_obs['objects'].get(i))
assert now_obs['objects'].keys() == old_obs['objects'].keys(), 'object sets differ'
assert all(evaluated_uv_noise_only(old_obs['objects'][i], now_obs['objects'][i]) for i in differing), differing
assert all(now_obs[k] == old_obs[k] for k in ('materials', 'scene', 'coverage', 'issues'))
summary['compatibility'] = {'previous_runtime': str(a.baseline_runtime),
                            'same_revision': current['revision'] == previous['revision'],
                            'uv_noise_only_objects': differing}

# A project on the instanced scene. The stored checkpoint copy cannot reach its relative library.
(out / 'BRIEF.md').write_text('Instanced garden fixture; not a production scene.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the instanced scene.\n', encoding='utf-8')
write_json(out / 'decisions.json', {})
cli('start', out / 'project', '--checkpoint', work / 'scene.blend', '--observation', scene['observation'], '--brief-file', out / 'BRIEF.md',
    '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
stored, _ = cli('observe', out / 'project/checkpoints/000001/checkpoint.blend', '--blender', a.blender, '--output-dir', out / 'observe-stored', expect=1)
assert 'Missing library: //lib/crate-v1.blend' in stored['issues'], stored['issues']
steps = {s['id']: s for s in cli('next', out / 'project')[0]['steps']}
assert '"<your working copy beside its libraries .blend>"' in steps['begin-edit']['command'] and 'linked libraries' in steps['observe']['why']
summary['stored_copy'] = 'reports Missing library; next points native commands at the working copy'

(out / 'edit.py').write_text('# Reserved for qualification; the candidates were built by the probe.\n', encoding='utf-8')
required = {'bench.a': {'type': 'EMPTY'}, 'bench.b': {'type': 'EMPTY'}, 'crate.a': {'type': 'EMPTY'}, 'ground': {'type': 'MESH'}}


def edit(label, current, candidate, allowed, expect):
    contract = out / f'contract-{label}.json'
    write_json(contract, {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [], 'allowed_object_prefixes': allowed,
                          'spec': {'schema': 'dcc.spec.v1', 'required': required}})
    parent = cli('next', out / 'project')[0]['active']['id']
    reserved, _ = cli('begin-edit', out / 'project', '--parent', parent, '--current', work / (current + '.blend'), '--observation',
                      observe(current)['observation'], '--script', out / 'edit.py',
                      '--contract', contract, '--label', label)
    (out / f'handoff-{label}.md').write_text(f'{label}\n', encoding='utf-8')
    write_json(out / f'updates-{label}.json', {})
    candidate_obs = observe(candidate)['observation']
    outcome, _ = cli('finish-edit', out / 'project', reserved['edit'], '--checkpoint', work / (candidate + '.blend'), '--observation',
                     candidate_obs, '--handoff', out / f'handoff-{label}.md', '--updates', out / f'updates-{label}.json',
                     expect=0 if expect == 'PUBLISHED' else 1)
    assert outcome['status'] == expect, (label, outcome)
    return outcome


edit('move-bench-a', 'scene', 'moved-a', {'bench.a': ['matrix_world', 'bounds']}, 'PUBLISHED')
rejected = edit('move-both', 'moved-a', 'moved-ab', {'bench.a': ['matrix_world', 'bounds']}, 'REJECTED_RETAINED')
unpermitted = edit('swap-unpermitted', 'moved-a', 'swapped', {}, 'REJECTED_RETAINED')
edit('swap-crate-v2', 'moved-a', 'swapped', {'crate.a': ['instance', 'bounds', 'dimensions']}, 'PUBLISHED')
disallowed = {}
for check in (out / 'project/edits').glob('*/check.json'):
    label = read_json(check.parent / 'request.json')['label']
    disallowed[label] = sorted((c['id'], c['field']) for c in read_json(check)['preservation']['changes'] if not c['allowed'])
assert disallowed['move-both'] == [('bench.b', 'bounds'), ('bench.b', 'matrix_world')], disallowed
assert disallowed['swap-unpermitted'] == [('crate.a', 'bounds'), ('crate.a', 'dimensions'), ('crate.a', 'instance')], disallowed
summary['edits'] = {'move permitted instance': 'PUBLISHED', 'move protected instance': 'REJECTED_RETAINED',
                    'swap library without instance permission': 'REJECTED_RETAINED', 'swap to crate-v2 with instance permission': 'PUBLISHED'}

# Editing a library in place is caught at the next reservation.
inplace = out / 'inplace'
baseline = observe('scene', folder=inplace)
cli('start', out / 'project-inplace', '--checkpoint', inplace / 'scene.blend', '--observation', baseline['observation'],
    '--brief-file', out / 'BRIEF.md', '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
scene_sha = file_hash(inplace / 'scene.blend')
blender_probe('edit-library', inplace)
assert file_hash(inplace / 'scene.blend') == scene_sha
changed, _ = cli('observe', inplace / 'scene.blend', '--blender', a.blender, '--output-dir', out / 'observe-inplace-after')
after = read_json(changed['observation'])['objects']['crate.a']['instance']
assert after['library']['sha256'] != library['sha256'] and after['definition_hash'] != crate['instance']['definition_hash']
parent = cli('next', out / 'project-inplace')[0]['active']['id']
write_json(out / 'contract-inplace.json', {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
                                           'spec': {'schema': 'dcc.spec.v1', 'required': required}})
_, error = cli('begin-edit', out / 'project-inplace', '--parent', parent, '--current', inplace / 'scene.blend', '--observation',
               changed['observation'], '--script', out / 'edit.py', '--contract', out / 'contract-inplace.json', '--label', 'after-library-edit',
               expect=None)
assert 'differs from the accepted baseline' in error, error[-500:]
summary['in_place_library_edit'] = 'scene bytes unchanged; library hash and definition changed; begin-edit refused'

# Adoption assigns an asset ID to a local instanced collection.
plan, _ = cli('adopt-preview', work / 'no-asset-id.blend', '--blender', a.blender, '--output-dir', out / 'adopt-preview')
rows = read_json(out / 'adopt-preview/plan.json')['assignments']
assert plan['status'] == 'READY' and any(r['kind'] == 'collection' and r['name'] == 'bench-asset' for r in rows), plan
applied, _ = cli('adopt-apply', out / 'adopt-preview/plan.json', '--blender', a.blender, '--output-dir', out / 'adopt-apply')
assert applied['status'] == 'READY_FOR_START', applied
summary['adoption'] = {'collection_assignment': True, 'status': applied['status']}

assert {p.name: file_hash(p) for p in work.glob('*.blend')} == sources, 'a source scene changed'
summary['sources_unchanged'] = True
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
