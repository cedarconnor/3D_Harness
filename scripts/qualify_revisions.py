"""Native external-edit adoption plus fresh-process continuation and acknowledgement recovery."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import sys
from unittest.mock import patch

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout; omit for installed package testing')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
from dcc_harness import revisions, workflow
from dcc_harness.continuity import Continuity
from dcc_harness.evidence import file_hash, read_json, write_json

runtime = Path(revisions.__file__).resolve().parent.parent
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
probe = Path(__file__).with_name('revision_native_probe.py').resolve()


def native(action, target, source=None):
    cmd = [a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
           '--python', str(probe), '--', action, '--runtime', str(runtime), '--out', str(target)]
    if source:
        cmd += ['--source', str(source)]
    with (out / (target.stem + '.log')).open('x', encoding='utf-8') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)


def cli(*args):
    proc = subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)],
                          cwd=runtime, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def tree(root):
    return {str(f.relative_to(root)): file_hash(f) for f in root.rglob('*') if f.is_file()}


native('fixtures', out / 'fixtures')
fixture_hashes = tree(out / 'fixtures')
for name in ('baseline', 'artist-material', 'unrequested-light', 'duplicate-id', 'external-baseline', 'external-candidate'):
    native('observe', out / (name + '.json'), out / 'fixtures' / (name + '.blend'))
root = out / 'project'
state = workflow.start(root, out / 'fixtures/baseline.blend', out / 'baseline.json',
                       'External revision qualification', {'stone_roughness': .4})
parent = state['active']['id']
original = tree(root)
before = read_json(out / 'baseline.json')
rules = {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1',
         'required': {iid: {'type': obj['type']} for iid, obj in before['objects'].items()},
         'material_nodes': {'stone': {'Principled BSDF': {'Roughness': .65}}}},
         'allowed_material_inputs': {'stone': {'Principled BSDF': {'Roughness': .65}}},
         'allowed_new_prefixes': [], 'sharing_groups': [['ext.table.top', 'ext.table.second']]}
write_json(out / 'contract.json', rules)
write_json(out / 'updates.json', {'stone_roughness': .65})
handoff = out / 'CONTINUE.md'
handoff.write_text('Simulated external material edit. Preserve geometry, shared mesh, camera and lighting. '
                   'Engineering qualification, not artist acceptance.', encoding='utf-8')

preview = cli('preview-revision', root, '--parent', parent, '--checkpoint', out / 'fixtures/artist-material.blend',
    '--observation', out / 'artist-material.json', '--contract', out / 'contract.json', '--handoff', handoff,
    '--updates', out / 'updates.json', '--label', 'external-stone-review', '--note', 'Simulated external shared-material edit',
    '--output-dir', out / 'preview with spaces')
assert preview['passed'] and preview['changed_material_users']['stone']['after'] == ['ext.table.second', 'ext.table.top']
assert tree(root) == original
write_json(out / 'preview-result.json', preview)

bad = revisions.preview_revision(root, parent, out / 'fixtures/unrequested-light.blend', out / 'unrequested-light.json',
    out / 'contract.json', handoff, {}, 'bad-light', 'Unrequested light fault', out / 'bad-preview')
assert bad['status'] == 'REJECTED_CONTRACT'
rejected = revisions.accept_revision(root, bad['preview'], bad['preview_sha256'], 'Negative control')
assert rejected['status'] == 'REJECTED_CONTRACT' and workflow.resume(root)['active']['id'] == parent
try:
    revisions.preview_revision(root, parent, out / 'fixtures/duplicate-id.blend', out / 'duplicate-id.json',
        out / 'contract.json', handoff, {}, 'bad-id', 'Duplicated native identity', out / 'duplicate-preview')
    raise AssertionError('Duplicate native identity accepted')
except ValueError as exc:
    assert 'no issues' in str(exc)
    assert not (out / 'duplicate-preview').exists()

# A real relocation control demonstrates why observed external paths are rejected.
control = out / 'relocation-control'
control.mkdir()
shutil.copyfile(out / 'fixtures/external-candidate.blend', control / 'copied.blend')
native('observe', out / 'relocated-external.json', control / 'copied.blend')
assert any('Missing image' in issue for issue in read_json(out / 'relocated-external.json')['issues'])
external_root = out / 'external-project'
external_state = workflow.start(external_root, out / 'fixtures/external-baseline.blend', out / 'external-baseline.json',
                                'Relative dependency negative control', {})
try:
    revisions.preview_revision(external_root, external_state['active']['id'], out / 'fixtures/external-candidate.blend',
        out / 'external-candidate.json', out / 'contract.json', handoff, {}, 'relative-edit', 'Relative-image fault',
        out / 'external-preview')
    raise AssertionError('Relative-image candidate was relocated')
except ValueError as exc:
    assert 'relocation requires packed' in str(exc)
    assert not (out / 'external-preview').exists()

# Inject only acknowledgement loss after the real publication has committed.
publish = Continuity.publish


def lost_ack(*args, **kwargs):
    publish(*args, **kwargs)
    raise RuntimeError('Injected acknowledgement loss after committed publication')


with patch.object(Continuity, 'publish', lost_ack):
    try:
        revisions.accept_revision(root, preview['preview'], preview['preview_sha256'], 'Reviewed native fixture measurements')
        raise AssertionError('Fault injection did not run')
    except RuntimeError as exc:
        assert 'Injected acknowledgement loss' in str(exc)
committed = tree(root)
recovered = cli('accept-revision', root, preview['preview'], '--preview-sha', preview['preview_sha256'],
                '--review-note', 'Recovery request must not replace the recorded review')
assert recovered['status'] == 'ALREADY_PUBLISHED' and tree(root) == committed
packet = cli('resume', root, '--focus', 'ext.table.top')
assert packet['active']['sequence'] == 2 and packet['pending'] == []
assert packet['decisions']['stone_roughness'] == .65
assert packet['focus']['ext.table.top']['shared_mesh_users'] == ['ext.table.second', 'ext.table.top']
review = cli('review', root)
assert review['external_revision']['preview_sha256'] == preview['preview_sha256']
assert review['external_revision']['review_attribution'] == 'caller_supplied'
native('observe', out / 'published.json', packet['active']['checkpoint'])
stored = read_json(packet['active']['observation'])
reopened = read_json(out / 'published.json')
assert reopened['revision'] == stored['revision'] and not reopened['issues']
for name, sha in original.items():
    assert file_hash(root / name) == sha
assert tree(out / 'fixtures') == fixture_hashes
assert not (root / 'operations.jsonl').exists()
report = read_json(Path(packet['active']['checkpoint']).parent / 'check.json')
assert report['external_revision']['contract'] == rules
assert report['external_revision']['review_note'] == 'Reviewed native fixture measurements'
result = {'passed': True, 'runtime': str(runtime), 'shared_material_users': 2,
          'fresh_native_reopen_equal': True, 'fresh_process_resume': True, 'original_checkpoint_files_unchanged': True,
          'unrequested_light_rejected': True, 'duplicate_native_id_rejected': True,
          'relative_image_relocation_fault_reproduced': True, 'unpacked_candidate_rejected_before_copy': True,
          'packed_image_survives_preview_and_publication': True,
          'injected_acknowledgement_loss_recovered_read_only': True, 'published_steps': 2,
          'no_fictional_native_dispatch': True, 'native_fixture_hashes': fixture_hashes,
          'limits': 'Coordinator-authored engineering fixture; no actual human edit, network failure or artistic review.'}
write_json(out / 'VERIFICATION.json', result)
print(json.dumps(result, indent=2))
