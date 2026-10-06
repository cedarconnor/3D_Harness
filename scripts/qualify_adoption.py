"""Exercise preview/apply/start/resume against real disposable Blender files."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout or installed site-packages; defaults to installed package')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
from dcc_harness import adoption, workflow
from dcc_harness.evidence import file_hash, read_json, write_json

out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
runtime = Path(adoption.__file__).resolve().parent.parent
probe = Path(__file__).with_name('adoption_native_probe.py').resolve()


def native(action, target, source=None):
    cmd = [a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
           '--python', str(probe), '--', action, '--runtime', str(runtime), '--out', str(target)]
    if source:
        cmd += ['--source', str(source)]
    with (out / (target.stem + '-probe.log')).open('x', encoding='utf-8') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)


native('fixtures', out / 'fixtures')
base = out / 'fixtures' / 'base.blend'
hashes = {str(f): file_hash(f) for f in (out / 'fixtures').glob('*.blend')}
native('snapshot', out / 'before.json', base)
preview = adoption.preview(base, out / 'preview', a.blender)
assert preview['passed'], preview
assert {(r['name'], r['property']) for r in read_json(preview['plan'])['assignments']} == {
    ('LinkedCube', 'dcc_instance_id'), ('LinkedCube', 'dcc_asset_id'),
    ('SeparateSphere', 'dcc_instance_id'), ('SeparateSphere', 'dcc_asset_id'),
    ('Camera', 'dcc_instance_id'), ('Area', 'dcc_instance_id'), ('ArtistMaterial', 'dcc_material_id')}
adopted = adoption.apply(preview['plan'], out / 'applied', a.blender)
assert adopted['status'] == 'READY_FOR_START', adopted
obs = read_json(adopted['observation'])
assert not obs['issues'] and obs['native_dirty'] is False
linked = next(r for r in obs['objects'].values() if r['name'] == 'LinkedCube')
assert linked['asset_id'] == 'artist.shared-cube'
assert obs['objects']['artist.cube']['asset_id'] == 'artist.shared-cube'
native('snapshot', out / 'after.json', adopted['checkpoint'])
assert read_json(out / 'before.json') == read_json(out / 'after.json')
started = workflow.start(out / 'state', adopted['checkpoint'], adopted['observation'],
                         'Disposable identity adoption qualification', {'preserve': 'artist-authored geometry'})
fresh = subprocess.run([sys.executable, '-m', 'dcc_harness', 'resume', str(out / 'state')],
                       cwd=runtime, capture_output=True, text=True, check=True)
resumed = json.loads(fresh.stdout)
assert resumed['active']['id'] == started['active']['id']
assert resumed['pending'] == []
noop = adoption.preview(adopted['checkpoint'], out / 'noop', a.blender)
assert noop['passed'] and noop['assignments'] == 0

# A self-consistent but false inventory must still fail against the reopened native file.
real_plan = read_json(preview['plan'])
false_inventory = copy.deepcopy(real_plan['inventory'])
next(r for r in false_inventory['objects'] if r['name'] == 'ArtistCube')['properties'] = {}
false_plan = adoption.plan_identities(false_inventory, real_plan['source'])
write_json(out / 'false-plan.json', false_plan)
try:
    adoption.apply(out / 'false-plan.json', out / 'false-plan-apply', a.blender)
    raise AssertionError('Native preflight accepted a false inventory')
except RuntimeError:
    assert not (out / 'false-plan-apply' / 'checkpoint.blend').exists()
    assert 'stale or altered' in (out / 'false-plan-apply' / 'apply.log').read_text()

blocked = []
for case in ('duplicate-instance', 'duplicate-material', 'invalid-id', 'ambiguous-asset',
             'shared-object', 'shared-material', 'shared-material-object', 'node-material-user', 'linked-object'):
    result = adoption.preview(out / 'fixtures' / (case + '.blend'), out / case, a.blender)
    assert not result['passed'] and result['assignments'] == 0, (case, result)
    try:
        adoption.apply(result['plan'], out / (case + '-apply'), a.blender)
        raise AssertionError('Blocked plan was applied')
    except ValueError:
        assert not (out / (case + '-apply')).exists()
    blocked.append({'case': case, 'issues': result['issues']})

# Identity completeness is distinct from observer support and start readiness.
unsupported = adoption.preview(out / 'fixtures' / 'unsupported-instance.blend', out / 'unsupported', a.blender)
assert unsupported['passed']
repair = adoption.apply(unsupported['plan'], out / 'unsupported-applied', a.blender)
assert repair['status'] == 'NEEDS_REPAIR' and not repair['passed'] and repair['issues']
assert not (out / 'unsupported-applied' / 'state').exists()

# Real CLI routing and output reservation, including paths with spaces.
cli_preview = out / 'cli preview with spaces'
cli = subprocess.run([sys.executable, '-m', 'dcc_harness', 'adopt-preview', str(base), '--blender', a.blender,
                      '--output-dir', str(cli_preview)], cwd=runtime, capture_output=True, text=True, check=True)
assert json.loads(cli.stdout)['passed']
replay = subprocess.run([sys.executable, '-m', 'dcc_harness', 'adopt-apply', preview['plan'], '--blender', a.blender,
                         '--output-dir', str(out / 'applied')], cwd=runtime, capture_output=True, text=True)
assert replay.returncode != 0 and 'FileExistsError' in replay.stderr
assert {str(f): file_hash(f) for f in (out / 'fixtures').glob('*.blend')} == hashes

result = {'passed': True, 'runtime': str(runtime), 'assigned_properties': adopted['assignments'],
          'fresh_start_resume': True, 'independent_native_snapshot_equal': True,
          'existing_id_and_shared_asset_preserved': True, 'repeat_preview_assignments': noop['assignments'],
          'negative_cases': blocked, 'unsupported_observation_status': repair['status'],
          'cli_with_spaces': True, 'existing_output_replay_rejected': True,
          'false_inventory_rejected_before_save': True,
          'all_fixture_files_unchanged': hashes, 'active': resumed['active']['id']}
write_json(out / 'VERIFICATION.json', result)
print(json.dumps(result, indent=2))
