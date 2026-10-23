"""Exercise both managed policies with owned Blender processes and disposable projects."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import time
import concurrent.futures
import copy

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True); p.add_argument('--runtime', required=True); p.add_argument('--out', required=True)
a = p.parse_args()
sys.path.insert(0, str(Path(a.runtime).resolve()))
from dcc_harness import execution, workflow, observe, environment_workflow as ew, coordination as c, owner
from dcc_harness.evidence import file_hash, write_json

out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=False)
fixture = out / 'fixture.py'
fixture.write_text('''import bpy, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1)
obj=bpy.context.object
obj['dcc_instance_id']='asset.cube'
obj['dcc_asset_id']='asset.cube'
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
''', encoding='utf-8')
source = out / 'source.blend'
with (out / 'fixture.log').open('x') as log:
    subprocess.run([a.blender, '--background', '--offline-mode', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                    '--python', str(fixture), '--', str(source)], stdout=log, stderr=subprocess.STDOUT, check=True)
sha = file_hash(source)
observed = observe.observe_file(source, out / 'initial-observation', a.blender)
script = out / 'edit.py'; script.write_text("import bpy\nassert bpy.app.background\nbpy.data.objects['Cube'].location.x += .25\n", encoding='utf-8')
contract = out / 'contract.json'
write_json(contract, {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1',
                     'required': {'asset.cube': {'type': 'MESH', 'dimensions': [1, 1, 1]}}}, 'allowed_new_prefixes': [],
                     'allowed_object_prefixes': {'asset.': ['matrix_world', 'bounds']}})
handoff = out / 'handoff.md'; handoff.write_text('Disposable native execution qualification.', encoding='utf-8')
skill = out / 'skills/dcc-plan-environment/SKILL.md'
skill.parent.mkdir(parents=True)
skill.write_text('---\nname: dcc-plan-environment\ndescription: Synthetic qualification fixture\n---\nNot artist production evidence.', encoding='utf-8')
ref = lambda path: {'path': path.relative_to(out).as_posix(), 'sha256': file_hash(path)}
actor = {'role': 'agent', 'author': 'native qualification', 'reference': 'Disposable fixture'}

class SyntheticOwnerConsole:
    """Authority-path fixture ONLY, never used on an artist project."""
    environ = {}
    def isatty(self): return True
    def ask(self, text): return re.search(r'Type ([A-Z0-9]{4})', text).group(1)

results = []
for mode in ('autonomous', 'approval_gated'):
    root = out / mode
    workflow.start(root, source, observed['observation'], 'Native execution qualification', {}, handoff)
    manifest = {'schema': 'dcc.environment.workflow.v1', 'id': 'environment', 'version': 1,
                'description': 'Native execution fixture', 'default_review_policy': 'agent_within_brief', 'stages': [
        {'id': 'direction', 'after': [], 'skills': ['dcc-plan-environment'], 'deliverables': ['brief'],
         'evidence': ['direction_record'], 'review': 'agent_within_brief'},
        {'id': 'delivery', 'after': ['direction'], 'skills': ['dcc-plan-environment'], 'deliverables': ['native'],
         'evidence': ['native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'], 'review': 'agent_within_brief'}]}
    binding = {'schema': 'dcc.environment.binding.v1', 'checkpoint': c.checkpoint_ref(workflow.resume(root)['active']),
               'authority': actor, 'review_policies': {}, 'inherited': {}, 'skill_files': {'dcc-plan-environment': [ref(skill)]}, 'references': []}
    ew.apply(root, 'workflow.bind', {'manifest': manifest, 'binding': binding}, 'none', str(uuid.uuid4()), out)
    execution.create(root, mode, max_operations=4, seconds=600)
    for stage in ('direction', 'delivery'):
        active = workflow.resume(root)['active']; op = str(uuid.uuid4())
        result = execution.execute(root, stage, op, script, contract, handoff, a.blender, active['id'], timeout=90)
        assert result['status'] == 'PUBLISHED', result
        assert execution.execute(root, stage, op, script, contract, handoff, a.blender, active['id'], timeout=90) == result
        current = workflow.resume(root)['active']
        evidence = [{'kind': 'direction_record', 'file': ref(handoff)}] if stage == 'direction' else [
            {'kind': 'native_reopen', 'observation': ref(root / 'execution/operations' / op / 'observation.json'), 'producer': actor},
            {'kind': 'native_contract', 'before': c.checkpoint_ref(active), 'contract': ref(contract)},
            {'kind': 'feedback_reconciliation'}, {'kind': 'handoff', 'file': ref(handoff)}]
        submission = {'schema': 'dcc.environment.submission.v1', 'stage_id': stage, 'checkpoint': c.checkpoint_ref(current),
                      'deliverables': {'brief' if stage == 'direction' else 'native': 'Verified fixture'},
                      'evidence': evidence, 'feedback_ids': [], 'note': 'Ready'}
        submitted = ew.apply(root, 'stage.submit', submission, c.read(root)[-1]['id'], str(uuid.uuid4()), out)
        review = {'submission_id': submitted['revision'], 'review': {'reviewer': actor, 'verdict': 'pass', 'finding': 'Verified native fixture'}}
        approval = None
        effective_policy = ew.review_policy(root, c.read(root), stage)
        if effective_policy == 'artist_required':
            try:
                ew.apply(root, 'stage.complete', review, submitted['revision'], str(uuid.uuid4()), out)
                raise AssertionError('Agent bypassed owner gate')
            except ValueError as exc:
                assert 'Artist review' in str(exc)
            if stage == 'direction':
                try:
                    execution.execute(root, 'delivery', str(uuid.uuid4()), script, contract, handoff, a.blender, current['id'])
                    raise AssertionError('Unapproved predecessor admitted')
                except ValueError as exc:
                    assert 'dependencies' in str(exc)
            review['review']['reviewer'] = {**actor, 'role': 'artist', 'reference': 'SYNTHETIC OWNER FIXTURE, not a human approval'}
            approval = owner.confirm('stage.complete', review, SyntheticOwnerConsole())
        ew.apply(root, 'stage.complete', review, submitted['revision'], str(uuid.uuid4()), out, approval=approval)
    assert execution.status(root)['status'] == 'COMPLETE'
    from dcc_harness.evidence import read_json
    final_observation = read_json(workflow.resume(root)['active']['observation'])
    assert abs(final_observation['objects']['asset.cube']['bounds'][0][0]) < 1e-6
    assert file_hash(source) == sha
    results.append({'mode': mode, 'passed': True, 'native_publications': 2, 'replay_safe': True,
                    'owner_gate': 'synthetic authority path only' if mode == 'approval_gated' else 'not required'})
    if mode == 'autonomous':
        ew.apply(root, 'stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': 'direction',
                 'reason': 'Qualify failure handling', 'authority': actor}, c.read(root)[-1]['id'], str(uuid.uuid4()), out)
        active = workflow.resume(root)['active']
        sleeping = out / 'sleep.py'; sleeping.write_text('import time\ntime.sleep(30)\n', encoding='utf-8')
        op = str(uuid.uuid4())
        timed = execution.execute(root, 'direction', op, sleeping, contract, handoff, a.blender, active['id'], timeout=3)
        assert timed['status'] == 'NEEDS_RECONCILIATION' and 'timed out' in timed['reason'], timed
        assert workflow.resume(root)['active']['id'] == active['id']
        assert execution.reconcile(root, op, accept=False, reason='Timed out native fixture')['status'] == 'REJECTED'
        marker = out / 'native-started.txt'
        cancelling = out / 'cancel.py'
        cancelling.write_text(f'from pathlib import Path\nimport time\nPath({str(marker)!r}).write_text("started")\ntime.sleep(30)\n', encoding='utf-8')
        op = str(uuid.uuid4())
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(execution.execute, root, 'direction', op, cancelling, contract, handoff, a.blender, active['id'], timeout=60)
            deadline = time.monotonic() + 30
            while not marker.exists() and not future.done() and time.monotonic() < deadline:
                time.sleep(.05)
            execution.cancel(root)
            cancelled = future.result(timeout=15)
        assert marker.exists() and cancelled['status'] == 'NEEDS_RECONCILIATION', cancelled
        assert workflow.resume(root)['active']['id'] == active['id']
        assert execution.reconcile(root, op, accept=False, reason='Cancelled native fixture')['status'] == 'REJECTED'
        results[-1].update(timeout_retains_checkpoint=True, cancellation_retains_checkpoint=True)

# Explicit artist policies must survive either managed mode. These extra cases
# use only the owned saved source/candidate and the synthetic owner-path fixture.
for mode in ('autonomous', 'approval_gated'):
    for policy_source in ('manifest', 'binding'):
        root = out / ('artist-policy-' + mode + '-' + policy_source)
        workflow.start(root, source, observed['observation'], 'Native artist-policy fixture', {}, handoff)
        required_manifest = copy.deepcopy(manifest)
        required_manifest['stages'][0]['review'] = ('artist_required' if policy_source == 'manifest' else 'agent_within_brief')
        required_binding = {**copy.deepcopy(binding), 'checkpoint': c.checkpoint_ref(workflow.resume(root)['active']),
            'authority': {**actor, 'role': 'artist', 'reference': 'SYNTHETIC OWNER FIXTURE, not a human approval'},
            'review_policies': {'direction': 'artist_required'} if policy_source == 'binding' else {}}
        policy_payload = {'manifest': required_manifest, 'binding': required_binding}
        approval = owner.confirm('workflow.bind', policy_payload, SyntheticOwnerConsole())
        ew.apply(root, 'workflow.bind', policy_payload, 'none', str(uuid.uuid4()), out, approval=approval)
        execution.create(root, mode, max_operations=2, seconds=300)
        effective_policy = ew.review_policy(root, c.read(root), 'direction')
        assert effective_policy == 'artist_required', (mode, policy_source, effective_policy)
        active = workflow.resume(root)['active']
        edited = execution.execute(root, 'direction', str(uuid.uuid4()), script, contract, handoff,
                                   a.blender, active['id'], timeout=90)
        assert edited['status'] == 'PUBLISHED', edited
        current = workflow.resume(root)['active']
        submitted = execution.submit(root, {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction',
            'checkpoint': c.checkpoint_ref(current), 'deliverables': {'brief': 'Native artist-policy fixture'},
            'evidence': [{'kind': 'direction_record', 'file': ref(handoff)}], 'feedback_ids': [],
            'note': 'Ready for required owner review'}, out)
        assert submitted['status'] == 'AWAITING_APPROVAL', submitted
        assert execution.status(root)['status'] == 'AWAITING_APPROVAL'
        review = {'submission_id': submitted['submission']['revision'],
                  'review': {'reviewer': actor, 'verdict': 'pass', 'finding': 'Agent cannot provide artist acceptance'}}
        try:
            ew.apply(root, 'stage.complete', review, c.read(root)[-1]['id'], str(uuid.uuid4()), out)
            raise AssertionError('Managed mode weakened an artist-bound stage')
        except ValueError as exc:
            assert 'Artist review' in str(exc), exc
        review['review']['reviewer'] = {**actor, 'role': 'artist', 'reference': 'SYNTHETIC OWNER FIXTURE, not a human approval'}
        approval = owner.confirm('stage.complete', review, SyntheticOwnerConsole())
        ew.apply(root, 'stage.complete', review, c.read(root)[-1]['id'], str(uuid.uuid4()), out, approval=approval)
        assert ew.stages(c.read(root), c.Continuity(root).status())['direction']['state'] == 'complete'
        assert file_hash(source) == sha
        results.append({'mode': mode, 'policy_source': policy_source, 'effective_review_policy': effective_policy,
                        'submission': 'AWAITING_APPROVAL', 'passed': True, 'native_publications': 1,
                        'owner_gate': 'synthetic authority path only'})
write_json(out / 'VERIFICATION.json', {'passed': True, 'source_unchanged': sha, 'results': results})
print(json.dumps(results))
