"""Exercise start/reserve/reconcile/publish from a real saved Blender scene."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
p.add_argument('--source', required=True)
p.add_argument('--runtime', default=str(Path(__file__).resolve().parents[1]))
p.add_argument('--compact-after', action='store_true', help='Qualify a plain baseline followed by compact observations')
p.add_argument('--blender', default='C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
a = p.parse_args()
sys.path.insert(0, a.runtime)
from dcc_harness import workflow
from dcc_harness.evidence import file_hash, read_json, write_json

root = Path(a.out).resolve(); root.mkdir(parents=True, exist_ok=False)
source = Path(a.source).resolve(); source_sha = file_hash(source)
probe = Path(__file__).with_name('workflow_native_probe.py').resolve()

def native(action, target, source_path=None, script=probe, compact=False):
    cmd = [a.blender, '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(script),
           '--', action, '--runtime', a.runtime, '--out', str(target)]
    if source_path is not None:
        cmd += ['--source', str(source_path)]
    if compact:
        cmd += ['--compact']
    with (root / (target.name+'.log')).open('x', encoding='utf-8') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Native probe failed: {target}; inspect retained log, do not replay')

native('observe', root/'before', source)
handoff = root/'CONTINUE.md'
handoff.write_text('Qualification branch: preserve the shed, cameras, lighting and all geometry. '
                   'Inspect only shared metal roughness. Not a blind trial or artistic improvement claim.', encoding='utf-8')
state = workflow.start(root/'project', source, root/'before/observation.json', 'Validate everyday continuation on a separate shed copy',
                       {'direction': 'realistic', 'preserve': ['layout', 'cameras', 'lighting', 'geometry']}, handoff)
contract = {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1',
             'required': {'ext.bench.top': {'dimensions': [1.8, .65, .06], 'tolerance': .01}},
             'material_nodes': {'metal': {'Principled BSDF': {'Roughness': .46}}}},
            'allowed_material_inputs': {'metal': {'Principled BSDF': {'Roughness': .46}}}, 'allowed_new_prefixes': []}
write_json(root/'contract.json', contract)
edit = workflow.begin_edit(root/'project', state['active']['id'], source, root/'before/observation.json', probe,
                           root/'contract.json', 'shared-metal-qualification')
write_json(root/'reservation.json', edit)
native('material', root/'candidate', source, script=Path(edit['script']), compact=a.compact_after)
# A fresh OS process sees the unresolved outcome before any publication.
process = subprocess.run([sys.executable, '-c',
    'import sys,json;sys.path.insert(0,sys.argv[1]);from dcc_harness.workflow import resume;print(json.dumps(resume(sys.argv[2])))',
    a.runtime, str(root/'project')], capture_output=True, text=True, check=True)
resumed = json.loads(process.stdout); assert resumed['status'] == 'RECONCILE'
write_json(root/'fresh-context.json', resumed)
native('observe', root/'independent-after', root/'candidate/candidate.blend', compact=a.compact_after)
result = workflow.finish_edit(root/'project', edit['edit'], root/'candidate/candidate.blend',
                             root/'independent-after/observation.json', handoff, {'metal_roughness': .46}, reconciled=True)
assert result['passed'], result['failures']
write_json(root/'result.json', result)
packet = workflow.review(root/'project', ['ext.bench.top']); assert packet['status'] == 'READY_FOR_INSPECTION'
write_json(root/'review.json', packet)
if a.compact_after:
    stored = root/'project/checkpoints/000002/observation.json'
    envelope = json.loads(stored.read_text(encoding='utf-8'))
    assert envelope['schema'] == 'dcc.observation.storage.v1'
    assert file_hash(stored) == file_hash(root/'independent-after/observation.json')
    write_json(root/'compact-storage.json', {'pooled_blocks': len(envelope['uv_blocks']),
               'stored_bytes': stored.stat().st_size, 'published_bytes_preserved': True,
               'plain_baseline_then_compact_revision': True})
native('construction', root/'construction')
assert file_hash(source) == source_sha
write_json(root/'qualification.json', {'passed': True, 'source_unchanged': True, 'source_sha256': source_sha,
           'compact_after': a.compact_after,
           'accepted_steps': packet['active']['sequence'], 'fresh_process_detected_unresolved': True,
           'reconciled_without_redispatch': True, 'native_check_passed': result['passed'],
           'review_packet_bytes': (root/'review.json').stat().st_size,
           'limits': 'Coordinator-authored engineering qualification. No independent agent continuation, visual superiority or true transport-loss injection.'})
print(json.dumps(read_json(root/'qualification.json'), indent=2))
