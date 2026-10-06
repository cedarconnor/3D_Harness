import concurrent.futures
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dcc_harness import workflow
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from test_continuity_checks import observation, contract


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'state'
        self.native = self.base / 'input.blend'
        self.native.write_bytes(b'synthetic native - not Blender qualification')
        self.obs = observation()
        self.obs['scene']['world'] = {'nodes': [{'name': 'Background', 'inputs': {'Strength': .5}}], 'links': []}
        self.obs['native_dirty'] = False
        self.obs['coverage']['measured'] = ['geometry', 'materials']
        self.obs['checkpoint_sha256'] = file_hash(self.native)
        self.obs_path = self.base / 'input.json'
        self.save_observation(self.obs_path, self.obs)
        self.script = self.base / 'edit.py'
        self.script.write_text('# retained script', encoding='utf-8')
        self.contract = self.base / 'contract.json'
        write_json(self.contract, contract())
        self.handoff = self.base / 'CONTINUE.md'
        self.handoff.write_text('Keep the layout and inspect material response.', encoding='utf-8')
        self.packet = workflow.start(self.root, self.native, self.obs_path, 'Garden', {'palette': 'warm'}, self.handoff)

    def save_observation(self, path, obs):
        obs['revision'] = digest({k: obs[k] for k in ('objects', 'materials', 'scene', 'coverage', 'issues')})
        write_json(path, obs)

    def begin(self, **kwargs):
        args = dict(root=self.root, expected_parent=self.packet['active']['id'], current=self.native,
                    observation=self.obs_path, script=self.script, contract=self.contract, label='material-review')
        args.update(kwargs)
        return workflow.begin_edit(**args)

    def candidate(self, mutated=False):
        native = self.base / 'candidate.blend'
        native.write_bytes(b'new synthetic native')
        obs = copy.deepcopy(self.obs)
        obs['checkpoint_sha256'] = file_hash(native)
        if mutated:
            obs['scene']['world']['nodes'][0]['inputs']['Strength'] = 2
        path = self.base / 'candidate.json'
        self.save_observation(path, obs)
        return native, path

    def test_compact_resume_focus_and_fresh_cli(self):
        packet = workflow.resume(self.root, ['ext.table.top'])
        self.assertEqual(packet['counts']['objects'], 1)
        self.assertEqual(packet['focus']['ext.table.top']['material_users']['stone'], ['ext.table.top'])
        self.assertNotIn('evaluated_uv_values', json.dumps(packet))
        result = subprocess.run([sys.executable, '-m', 'dcc_harness', 'resume', str(self.root)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['decisions']['palette'], 'warm')

    def test_start_cannot_replace_existing_project(self):
        with self.assertRaises(ValueError):
            workflow.start(self.root, self.native, self.obs_path, 'overwrite', {})
        self.assertEqual(workflow.resume(self.root)['decisions'], {'palette': 'warm'})

    def test_stale_parent_and_changed_file_rejected_before_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'Stale parent'):
            self.begin(expected_parent='old')
        self.native.write_bytes(b'manual change')
        with self.assertRaises(ValueError):
            self.begin()
        self.assertEqual(workflow.resume(self.root)['pending'], [])

    def test_dirty_observation_blocks_even_matching_saved_bytes(self):
        obs = copy.deepcopy(self.obs)
        obs['native_dirty'] = True
        path = self.base / 'dirty.json'
        write_json(path, obs)
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.begin(observation=path)

    def test_changed_observation_and_unknown_focus_block(self):
        obs = copy.deepcopy(self.obs)
        obs['scene']['world']['nodes'][0]['inputs']['Strength'] = 2
        path = self.base / 'drift.json'
        self.save_observation(path, obs)
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.begin(observation=path)
        with self.assertRaisesRegex(ValueError, 'Unknown focus'):
            workflow.resume(self.root, ['missing'])

    def test_concurrent_reservations_have_only_one_winner(self):
        def attempt(_):
            try:
                return self.begin()
            except RuntimeError:
                return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(workflow.resume(self.root)['status'], 'RECONCILE')

    def test_source_script_changes_do_not_change_reserved_script(self):
        edit = self.begin()
        self.script.write_text('# changed outside reservation', encoding='utf-8')
        self.assertEqual(Path(edit['script']).read_text(), '# retained script')
        Path(edit['script']).write_text('# tampered retained script', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed'):
            workflow.resume(self.root)

    def test_reconciled_result_publishes_and_replay_is_refused(self):
        edit = self.begin()
        native, obs = self.candidate()
        result = workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {'phase': 'surface'}, reconciled=True)
        self.assertEqual(result['status'], 'PUBLISHED')
        packet = workflow.resume(self.root)
        self.assertEqual(packet['active']['sequence'], 2)
        self.assertEqual(packet['decisions']['phase'], 'surface')
        self.assertEqual(packet['status'], 'READY_FOR_INSPECTION')
        with self.assertRaisesRegex(RuntimeError, 'already recorded'):
            workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {})

    def test_failed_preservation_retains_candidate_and_parent(self):
        edit = self.begin()
        native, obs = self.candidate(mutated=True)
        result = workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {})
        self.assertEqual(result['status'], 'REJECTED_RETAINED')
        self.assertEqual(workflow.resume(self.root)['active']['id'], self.packet['active']['id'])
        self.assertEqual(workflow.resume(self.root)['recent_edits'][-1]['status'], 'REJECTED_RETAINED')
        self.assertTrue(native.exists())
        self.assertTrue((Path(edit['script']).parent / 'check.json').exists())

    def test_unsupported_spec_rejected_before_reservation(self):
        rules = contract(); rules['spec']['unsupported'] = True
        path = self.base / 'bad-contract.json'; write_json(path, rules)
        with self.assertRaisesRegex(ValueError, 'Unsupported spec'):
            self.begin(contract=path)
        self.assertEqual(workflow.resume(self.root)['pending'], [])

    def test_visual_rejection_does_not_publish_native_passing_candidate(self):
        edit = self.begin(); native, obs = self.candidate()
        result = workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff,
                                      {'palette': 'unaccepted'}, reject_reason='Sparse detached-looking foliage')
        self.assertTrue(result['native_check_passed'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['status'], 'REJECTED_VISUAL')
        packet = workflow.resume(self.root)
        self.assertEqual(packet['active']['id'], self.packet['active']['id'])
        self.assertEqual(packet['decisions'], {'palette': 'warm'})
        self.assertEqual(packet['recent_edits'][-1]['failures'], ['Sparse detached-looking foliage'])
        self.assertEqual(packet['status'], 'READY_FOR_INSPECTION')
        next_edit = self.begin(label='foliage-repair')
        self.assertEqual(next_edit['status'], 'RESERVED_NOT_EXECUTED')

    def test_empty_rejection_reason_leaves_operation_pending(self):
        edit = self.begin(); native, obs = self.candidate()
        with self.assertRaisesRegex(ValueError, 'nonempty reason'):
            workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {}, reject_reason=' ')
        self.assertEqual(workflow.resume(self.root)['status'], 'RECONCILE')

    def test_partial_lock_or_reservation_does_not_auto_expire(self):
        (self.root / 'workflow.lock').write_text('{}')
        self.assertEqual(workflow.resume(self.root)['status'], 'RECONCILE')
        with self.assertRaisesRegex(RuntimeError, 'lock exists'):
            self.begin()
        (self.root / 'workflow.lock').unlink()
        (self.root / 'edits' / 'partial').mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, 'Partial edit'):
            workflow.resume(self.root)


if __name__ == '__main__':
    unittest.main()
