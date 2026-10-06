import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dcc_harness import workflow
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import digest, file_hash, read_json, validate_observation, write_json
from dcc_harness.observation_storage import SCHEMA, pack_observation, unpack_observation
from test_continuity_checks import observation, contract, resign


def repeated_observation():
    obs = observation()
    item = obs['objects']['ext.table.top']
    item['evaluated_uv_values']['UVMap'] = [0, 0.0, -0.0, .12345678901234567] * 100
    item['evaluated_uv_values']['short'] = [1, 1.0, -0.0]
    obs['objects']['ext.table.other'] = copy.deepcopy(item)
    return resign(obs)


class ObservationStorageTests(unittest.TestCase):
    def test_lossless_revision_types_no_mutation_or_aliasing(self):
        obs = repeated_observation(); original = copy.deepcopy(obs)
        packed = pack_observation(obs)
        self.assertEqual(len(packed['uv_blocks']), 1)
        restored = unpack_observation(json.loads(json.dumps(packed)))
        validate_observation(restored)
        # Canonical JSON distinguishes int/float and signed zero, unlike ==.
        self.assertEqual(digest(restored), digest(original))
        restored['objects']['ext.table.top']['evaluated_uv_values']['UVMap'][0] = 7
        self.assertEqual(unpack_observation(packed), original)
        self.assertEqual(obs, original)
        self.assertEqual(restored['objects']['ext.table.other'], original['objects']['ext.table.other'])

    def test_transport_corruption_and_invalid_envelopes_fail(self):
        packed = pack_observation(repeated_observation())
        key = next(iter(packed['uv_blocks']))
        cases = []
        for mutator in (
            lambda p: p['uv_blocks'][key].__setitem__(0, 9),
            lambda p: p['uv_blocks'].clear(),
            lambda p: p.update(schema='dcc.observation.storage.v2'),
            lambda p: p.update(extra=True),
            lambda p: p['observation']['objects']['ext.table.top']['evaluated_uv_values'].update(UVMap={'uv_block': 'missing'}),
            lambda p: p['observation']['objects']['ext.table.top']['evaluated_uv_values'].update(UVMap={'uv_block': key, 'extra': True}),
            lambda p: p['uv_blocks'].update({digest([3]): [3]}),
        ):
            bad = copy.deepcopy(packed); mutator(bad); cases.append(bad)
        for bad in cases:
            with self.subTest(case=cases.index(bad)), self.assertRaises(ValueError):
                unpack_observation(bad)

    def test_rehashed_pool_cannot_hide_changed_logical_revision(self):
        packed = pack_observation(repeated_observation())
        old = next(iter(packed['uv_blocks']))
        values = packed['uv_blocks'].pop(old); values[0] = 8
        key = digest(values); packed['uv_blocks'][key] = values
        for item in packed['observation']['objects'].values():
            item['evaluated_uv_values']['UVMap']['uv_block'] = key
        with self.assertRaises(ValueError):
            validate_observation(unpack_observation(packed))

    def test_expansion_limit_and_invalid_values(self):
        obs = repeated_observation(); packed = pack_observation(obs)
        # One 400-value block fits; its two references exceed the 600 limit.
        with patch('dcc_harness.observation_storage.MAX_UV_VALUES', 600):
            with self.assertRaises(ValueError): unpack_observation(packed)
            with self.assertRaises(ValueError): pack_observation(obs)
        for value in ([True], [[0]], [float('inf')], [float('nan')], '0'):
            bad = copy.deepcopy(packed)
            bad['observation']['objects']['ext.table.top']['evaluated_uv_values']['short'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): unpack_observation(bad)

    def test_plain_default_legacy_small_and_exclusive_write(self):
        with tempfile.TemporaryDirectory() as folder:
            plain = Path(folder)/'plain.json'; compact = Path(folder)/'compact.json'
            obs = repeated_observation()
            write_json(plain, obs); write_json(compact, obs, compact_observation=True)
            self.assertEqual(json.loads(plain.read_text())['schema'], 'dcc.observation.v1')
            self.assertEqual(json.loads(compact.read_text())['schema'], SCHEMA)
            self.assertEqual(digest(read_json(plain)), digest(read_json(compact)))
            with self.assertRaises(FileExistsError): write_json(compact, obs, compact_observation=True)
            self.assertEqual(pack_observation(observation()), observation())

    def test_cli_preserves_source_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'source.json'; dest = Path(folder)/'packed.json'
            write_json(source, repeated_observation()); before = file_hash(source)
            cmd = [sys.executable, '-m', 'dcc_harness', 'pack-observation', str(source), str(dest)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(result.stdout)['source_unchanged'])
            self.assertEqual(file_hash(source), before)
            self.assertEqual(digest(read_json(source)), digest(read_json(dest)))
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)

    def test_compaction_does_not_change_uv_or_material_failure_results(self):
        before = repeated_observation()
        for kind in ('uv', 'material'):
            after = copy.deepcopy(before)
            if kind == 'uv':
                after['objects']['ext.table.top']['source_uv_hash'] = 'changed'
                after['objects']['ext.table.top']['evaluated_uv_values']['UVMap'][0] = .5
            else:
                after['materials']['stone']['graph']['nodes'][0]['inputs']['Roughness'] = .9
            resign(after)
            plain = evaluate_stage(before, after, contract())
            compact = evaluate_stage(unpack_observation(pack_observation(before)),
                                     unpack_observation(pack_observation(after)), contract())
            self.assertFalse(plain['passed']); self.assertEqual(plain, compact)

    def test_mixed_history_reconcile_and_retained_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); root = base/'project'
            native = base/'input.blend'; native.write_bytes(b'synthetic - not native validation')
            obs = repeated_observation()
            obs['coverage']['measured'] = ['geometry', 'materials']
            obs['scene']['world'] = {'nodes': [], 'links': []}
            resign(obs)
            obs.update(native_dirty=False, checkpoint_sha256=file_hash(native))
            before = base/'before.json'; write_json(before, obs)
            handoff = base/'CONTINUE.md'; handoff.write_text('Preserve all measured content.')
            script = base/'edit.py'; script.write_text('# synthetic retained edit')
            rules = base/'contract.json'; write_json(rules, contract())
            initial = workflow.start(root, native, before, 'Storage qualification', {}, handoff)
            edit = workflow.begin_edit(root, initial['active']['id'], native, before, script, rules, 'storage')
            candidate = base/'candidate.blend'; candidate.write_bytes(b'synthetic saved result')
            obs['checkpoint_sha256'] = file_hash(candidate)
            after = base/'after.json'; write_json(after, obs, compact_observation=True)
            self.assertEqual(workflow.resume(root)['status'], 'RECONCILE')
            result = workflow.finish_edit(root, edit['edit'], candidate, after, handoff, {}, reconciled=True)
            self.assertTrue(result['passed'])
            packet = workflow.resume(root)
            self.assertEqual(packet['status'], 'READY_FOR_INSPECTION')
            self.assertEqual(packet['active']['sequence'], 2)
            retained = root/'checkpoints/000002/observation.json'
            self.assertEqual(file_hash(retained), file_hash(after))
            # Tampering anywhere in retained history must still fail every resume.
            for path in (root/'checkpoints/000001/observation.json', retained):
                data = path.read_bytes()
                path.write_bytes(data+b' ')
                with self.assertRaises(ValueError): workflow.resume(root)
                path.write_bytes(data)
                self.assertEqual(workflow.resume(root)['status'], 'READY_FOR_INSPECTION')


if __name__ == '__main__':
    unittest.main()
