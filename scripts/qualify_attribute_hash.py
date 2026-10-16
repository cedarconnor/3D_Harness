"""Native qualification of build-plan item P15: the authored attribute hash.

On a flat-shaded bench top, each saved variant changes only data the older hashes leave out (smooth shading, a
sharp edge, a crease, a seam, a colour attribute, a loose edge, one attribute of every type). Checks:
- each variant fails a zero-permission contract, and source_attribute_hash is its only unpermitted change;
- an unchanged scene saved twice observes with the same revision in separate processes;
- a contract permitting source_mesh_hash also permits the attribute change;
- against an observation from --baseline-runtime (0.18.1), which did not measure attributes, the field is skipped;
- optionally, the production garden's observation time.

python scripts/qualify_attribute_hash.py --blender BLENDER --out NEW --baseline-runtime OLD_CHECKOUT [--runtime CHECKOUT]
"""
from pathlib import Path
import subprocess
import sys
import time

from _launcher import REPO, Qualification

q = Qualification(__doc__.splitlines()[0], [('--baseline-runtime', {'required': True})])
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import read_json

fixtures = q.out / 'fixtures'
q.blender('build.log', '--python', Path(__file__).with_name('attribute_hash_native_probe.py').resolve(), '--', '--out', fixtures)
VARIANTS = ('smooth', 'sharp-edge', 'crease', 'seam', 'color', 'loose-edge', 'every-type')


BASELINE = Path(q.args.baseline_runtime).resolve()


def observe(name, baseline=False, source=None):
    """Observe a fixture, or another saved file, with the runtime under test or the baseline runtime."""
    folder = q.out / (('baseline-' if baseline else 'observe-') + name)
    source = source or fixtures / f'{name}.blend'
    if not baseline:
        q.cli('observe', source, '--blender', q.args.blender, '--output-dir', folder)
    else:
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'observe', str(source), '--blender',
                               q.args.blender, '--output-dir', str(folder)], cwd=BASELINE, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr[-1500:]
    return read_json(folder / 'observation.json')


def contract(fields=None):
    c = {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': {
        'probe.bench.top': {'type': 'MESH', 'asset_id': 'probe.bench.top-asset', 'material_ids': ['probe.timber']}}}}
    if fields:
        c['allowed_object_prefixes'] = {'probe.bench.': fields}
    return c


def unpermitted(report):
    return sorted({(c['id'], c['field']) for c in report['preservation']['changes'] if not c['allowed']})


base = observe('base')
assert 'source_attributes' in base['coverage'], base['coverage']
top = base['objects']['probe.bench.top']
again = observe('base-again')
assert again['revision'] == base['revision'], 'An unchanged scene observed differently'
assert evaluate_stage(base, again, contract())['passed']

summary = {'blender': q.args.blender, 'base_revision': base['revision'], 'variants': {}}
for name in VARIANTS:
    after = observe(name)
    changed = after['objects']['probe.bench.top']
    for field in ('source_mesh_hash', 'source_uv_hash', 'geometry_hash', 'uv_hash', 'vertices', 'triangles'):
        assert changed[field] == top[field], (name, field)
    report = evaluate_stage(base, after, contract())
    assert not report['passed'] and unpermitted(report) == [('probe.bench.top', 'source_attribute_hash')], (name, report['failures'], unpermitted(report))
    assert evaluate_stage(base, after, contract(['source_mesh_hash']))['passed'], name
    assert evaluate_stage(base, after, contract(['source_attribute_hash']))['passed'], name
    summary['variants'][name] = 'fails zero-permission contract on source_attribute_hash alone'

# The gap: the baseline runtime sees none of these changes.
old = observe('base', baseline=True)
assert 'source_attributes' not in old['coverage'] and 'source_attribute_hash' not in old['objects']['probe.bench.top']
for name in VARIANTS:
    report = evaluate_stage(old, observe(name, baseline=True), contract())
    assert report['passed'], (name, report['failures'])
summary['baseline_gap'] = 'every variant passes a zero-permission contract when both sides come from the baseline runtime'
seam = read_json(q.out / 'observe-seam' / 'observation.json')
skipped = evaluate_stage(old, seam, contract())
assert skipped['passed'], skipped['failures']
summary['baseline_mixed'] = 'a baseline before and a current after: the field is skipped, as documented'

production = REPO / 'runs/shed-production-2026-10-05/project/checkpoints/000009/checkpoint.blend'
if production.is_file():
    timing = {}
    for label, baseline in (('baseline', True), ('current', False)):
        started = time.time()
        meshes = observe('garden', baseline=baseline, source=production)['objects']
        timing[label + '_seconds'] = round(time.time() - started)
    summary['production'] = {**timing, 'meshes': sum(1 for o in meshes.values() if o['type'] == 'MESH')}

q.finish(summary)
