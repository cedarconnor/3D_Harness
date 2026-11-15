"""Native qualification of audit (build-plan item G3).

Builds a clean control (a closed slab and a closed, textured crate standing on it) and one file per
check that differs from it by a single defect. The control must report nothing under every profile.
Each defect file must report its own code and no other, and exit 1 under a profile where that code
is an error. The report must bind to the file's hash. The production garden is audited under the
render profile; its errors were reviewed in Blender and are real (parts built inside out, and flush
parts of different materials), so only those two codes may appear as errors.
"""
import time

from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, out = q.args, q.out
from dcc_harness.evidence import file_hash, read_json

q.blender('scenes.log', '--python', REPO / 'scripts/audit_native_probe.py', '--', '--out', out / 'scenes')
runs = {}


def audit(name, profile, expect, *extra):
    key = f'{name}-{profile}' + ('-select' if extra else '')
    source = out / 'scenes' / f'{name}.blend'
    before = file_hash(source)
    report = q.cli('audit', source, '--blender', a.blender, '--output-dir', out / key, '--profile', profile, *extra, expect=expect)
    assert file_hash(source) == before == report['source']['sha256'] == read_json(out / key / 'measurement.json')['checkpoint_sha256']
    assert report['passed'] is (expect == 0) and report['omitted'] == 0, report
    runs[key] = report['by_code']
    return report


def codes(report):
    return {(f['code'], f['object'] or f.get('material'), f['severity']) for f in report['findings']}


for profile in ('render', 'game', 'print'):
    assert audit('control', profile, 0)['findings'] == [], profile

# name: profile, exit code, the single expected finding
EXPECTED = {
    'flipped-face': ('render', 1, ('NORMALS_INCONSISTENT', 'crate', 'error')),
    'inward': ('render', 1, ('NORMALS_INWARD', 'crate', 'error')),
    'inward-open': ('render', 0, ('NORMALS_INWARD_ESTIMATE', 'crate', 'warning')),
    'open': ('print', 1, ('OPEN_EDGES', 'crate', 'error')),
    'doubled-face': ('game', 1, ('NON_MANIFOLD_EDGES', 'crate', 'error')),
    'loose': ('game', 1, ('LOOSE_GEOMETRY', 'crate', 'error')),
    'zero-area': ('game', 1, ('ZERO_AREA_FACES', 'crate', 'error')),
    'coincident': ('render', 1, ('COINCIDENT_FACES', 'crate', 'error')),
    'coincident-matched': ('render', 0, ('COINCIDENT_FACES_MATCHED', 'crate', 'warning')),
    'sheet-down': ('render', 0, ('BACK_TO_BACK_FACES', 'ground', 'warning')),
    'sheet-up': ('render', 1, ('COINCIDENT_FACES', 'ground', 'error')),
    'floating': ('print', 1, ('FLOATING_PART', 'crate', 'error')),
    'scale-uniform': ('game', 0, ('SCALE_UNAPPLIED', 'crate', 'warning')),
    'scale-nonuniform': ('game', 1, ('SCALE_NONUNIFORM', 'crate', 'error')),
    'scale-negative': ('game', 1, ('SCALE_NEGATIVE', 'crate', 'error')),
    'empty-slot': ('render', 1, ('EMPTY_SLOT_FACES', 'crate', 'error')),
    'data-srgb': ('render', 1, ('DATA_MAP_SRGB', 'Paint', 'error')),
    'no-uv': ('render', 1, ('TEXTURE_WITHOUT_UV', 'crate', 'error')),
}
reports = {}
for name, (profile, expect, finding) in EXPECTED.items():
    reports[name] = audit(name, profile, expect)
    assert codes(reports[name]) == {finding}, (name, codes(reports[name]))

# The values behind the findings. Overlap areas are grid estimates.
first = {name: report['findings'][0] for name, report in reports.items()}
assert first['flipped-face']['edges'] == 4 and first['doubled-face']['edges'] == 4 and first['open']['edges'] == 4
assert first['zero-area']['faces'] == 1 and first['empty-slot']['faces'] == 1 and first['loose']['edges'] == 1
assert first['coincident']['other'] == 'Plate' and first['coincident']['planes'] == 2 and abs(first['coincident']['area'] - 0.18) < 0.01
assert abs(first['sheet-down']['area'] - 0.64) < 0.03 and first['sheet-down']['other'] == 'sheet'
assert first['floating']['parts'] == 1 and first['floating']['examples'][0]['centre'] == [0.0, 0.0, 0.8]
assert first['data-srgb']['image'] == 'relief' and first['data-srgb']['objects'] == ['crate']
assert first['inward-open']['evidence'] == 'bounds_only' and first['inward-open']['permitted'] == 'inspect'
assert all(f['evidence'] == 'native_measurement' and f['permitted'] == 'repair' for n, f in first.items() if n != 'inward-open')
assert all(f['cause'] and f['fix'] for f in first.values())

# Profiles differ: an open crate is nothing under render, and a floating crate only warns there.
assert audit('open', 'render', 0)['findings'] == []
assert codes(audit('floating', 'render', 0)) == {('FLOATING_PART', 'crate', 'warning')}
# A selection reports only the objects it names, and one that names nothing is refused.
assert audit('floating', 'print', 0, '--select', 'ground')['findings'] == []
q.refused(['audit', out / 'scenes/control.blend', '--blender', a.blender, '--output-dir', out / 'none', '--select', 'absent*'], 'Native process failed')
assert 'matches absent*' in (out / 'none/measure.log').read_text(encoding='utf-8')
summary = {'blender': a.blender, 'fixtures': {name: list(EXPECTED[name][:2]) + list(EXPECTED[name][2]) for name in EXPECTED},
           'control': 'no findings under render, game and print', 'by_code': runs}

production = REPO / 'runs/shed-production-2026-10-05/project/checkpoints/000009/checkpoint.blend'
if production.is_file():
    started = time.time()
    garden = q.cli('audit', production, '--blender', a.blender, '--output-dir', out / 'garden', expect=1)
    errors = {f['code'] for f in read_json(out / 'garden/report.json')['findings'] if f['severity'] == 'error'}
    assert errors <= {'NORMALS_INWARD', 'COINCIDENT_FACES'}, errors
    summary['production'] = {'seconds': round(time.time() - started), 'objects': garden['objects_audited'], 'counts': garden['counts'],
                             'by_code': garden['by_code'], 'tolerances': garden['tolerances'], 'notes': garden['notes']}
q.finish(summary)
