"""Native qualification of the observe command on positive and negative saved scenes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout; omit for installed package testing')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
from dcc_harness import observe as observe_module
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import file_hash, read_json, write_json

runtime = Path(observe_module.__file__).resolve().parent.parent
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
probe = Path(__file__).with_name('observe_native_probe.py').resolve()
fixtures = out / 'fixtures'


def cli(*args):
    proc = subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)],
                          cwd=runtime, capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else None, proc.stderr


command = [a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
           '--python', str(probe), '--', 'fixtures', '--runtime', str(runtime), '--out', str(fixtures)]
with (out / 'fixtures.log').open('x', encoding='utf-8') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
spaced = out / 'path with spaces' / 'clean copy.blend'
spaced.parent.mkdir()
shutil.copyfile(fixtures / 'clean.blend', spaced)
sources = {path: file_hash(path) for path in [*fixtures.glob('*.blend'), spaced]}

results = {}
for name, source, code_expected, status in [('clean', fixtures / 'clean.blend', 0, 'READY'),
                                            ('spaces', spaced, 0, 'READY'),
                                            ('missing-asset', fixtures / 'missing-asset.blend', 1, 'HAS_ISSUES'),
                                            ('instancer', fixtures / 'instancer.blend', 1, 'HAS_ISSUES')]:
    code, result, error = cli('observe', source, '--blender', a.blender, '--output-dir', out / ('observe-' + name))
    assert code == code_expected and result and result['status'] == status, (name, code, result, error)
    results[name] = result
assert any('Missing asset ID' in issue for issue in results['missing-asset']['issues']), results['missing-asset']
assert any('Unsupported instancer' in issue for issue in results['instancer']['issues']), results['instancer']

# An existing output folder is refused before any Blender process starts.
code, result, error = cli('observe', fixtures / 'clean.blend', '--blender', 'no-blender-should-launch',
                          '--output-dir', out / 'observe-clean')
assert code != 0 and result is None and 'FileExistsError' in error, (code, error)

# The fresh-process observation agrees with an in-process observation of the same saved file.
reference = read_json(fixtures / 'reference.json')
observed = read_json(results['clean']['observation'])
guarded = evaluate_stage(reference, observed, {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
                                               'spec': {'schema': 'dcc.spec.v1', 'required': {'probe.cube': {}}}})
assert guarded['passed'], guarded['failures']
assert sources == {path: file_hash(path) for path in sources}, 'A source file changed'

# The command's output starts a project directly; no ad hoc observation script is needed.
brief = out / 'BRIEF.md'
brief.write_text('Observe-command qualification fixture; no production art.', encoding='utf-8')
decisions = out / 'decisions.json'
write_json(decisions, {})
code, started, error = cli('start', out / 'project', '--checkpoint', fixtures / 'clean.blend', '--observation',
                           results['clean']['observation'], '--brief-file', brief, '--decisions', decisions)
assert code == 0 and started['status'] == 'READY_FOR_INSPECTION', (code, started, error)

write_json(out / 'VERIFICATION.json', {
    'passed': True, 'runtime': str(runtime), 'statuses': {name: r['status'] for name, r in results.items()},
    'missing_asset_issues': results['missing-asset']['issues'], 'instancer_issues': results['instancer']['issues'],
    'existing_output_rejected_before_launch': True,
    'reference_revision_equal': reference['revision'] == observed['revision'],
    'guarded_preservation_passed': True, 'sources_unchanged': True, 'start_from_observe_output': True,
    'limits': 'Owned synthetic fixtures; saved-file observation only; no live editor or visual-quality claim.'})
print('PASSED: observe command native qualification')
