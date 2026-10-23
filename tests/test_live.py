"""Host-side live attachment and managed lifecycle contracts."""
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_live_protocol import bridge_leaf


class AttachTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('dcc_harness.live'), 'Live attachment is not implemented')
        self.live = importlib.import_module('dcc_harness.live')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        self.session = bridge_leaf('session').Session(self.workspace, 9878)
        self.brief = self.workspace / 'brief.md'; self.brief.write_text('Build a product scene')

    def _attach_with_native_boundary(self, *, foreign_live=False):
        """Only native transport/measurement are doubled; host state is real."""
        from dcc_harness import live_snapshot
        from dcc_harness.evidence import file_hash, write_json
        from test_continuity_checks import observation, resign
        destination = self.workspace / 'project'
        native = destination / 'baseline.blend'
        saved = {}
        calls = []
        snapshot = {'objects': {}, 'materials': {}, 'scene': {}, 'coverage': {}, 'issues': []}

        def call(command, payload, **kwargs):
            calls.append(command)
            if command == 'session_describe':
                return {'scenes': ['Scene'], 'generation': self.session.generation}
            if command == 'attach_begin':
                return {'operation_id': payload['operation_id']}
            if command == 'attach_apply':
                native.write_bytes(b'owned synthetic native boundary')
                saved.update(operation_id=payload['operation_id'], session_id=self.session.session_id,
                             generation=self.session.generation, scene='Scene', inventory={},
                             baseline={'path': str(native), 'sha256': file_hash(native), 'original_filepath': ''},
                             fingerprint=live_snapshot.fingerprint(snapshot), snapshot=str(destination / 'snapshot.json'))
                write_json(destination / 'snapshot.json', snapshot)
                write_json(destination / 'attach-saved.json', saved)
                if foreign_live:
                    folder = destination / 'state/live'; folder.mkdir(parents=True)
                    (folder / 'foreign.txt').write_bytes(b'preserve foreign state')
                return dict(saved)
            if command == 'attach_check':
                # Real retention models the bridge check's new directory-creation side effect.
                identity = live_snapshot.retain(destination / 'state', snapshot)
                return {'session_id': self.session.session_id, 'generation': self.session.generation,
                        'scene': 'Scene', 'matches': identity == payload['fingerprint']}
            if command == 'attach_acknowledge':
                return {}
            raise AssertionError(command)

        def worker(blender, out, script, action, payload, **kwargs):
            value = observation()
            value['scene']['world'] = {'nodes': [], 'links': []}
            value['coverage']['measured'] = ['geometry', 'materials']
            resign(value)
            value.update(native_dirty=False, checkpoint_sha256=file_hash(native))
            write_json(Path(out) / 'observation.json', value)

        with mock.patch.object(self.live.blender_bridge, 'call', side_effect=call), \
                mock.patch.object(self.live, 'run_worker', side_effect=worker):
            if foreign_live:
                with self.assertRaises(FileExistsError):
                    self.live.attach(destination, self.session.descriptor_path, scene='Scene', mode='autonomous',
                                     brief_file=self.brief, blender='blender')
                self.assertEqual((destination / 'state/live/foreign.txt').read_bytes(), b'preserve foreign state')
                self.assertFalse((destination / 'created.json').exists())
                self.assertNotIn('attach_acknowledge', calls)
                return
            result = self.live.attach(destination, self.session.descriptor_path, scene='Scene', mode='autonomous',
                                      brief_file=self.brief, blender='blender')
            self.assertEqual(result['live_state'], 'READY')
            self.assertEqual(self.live.execution.configuration(result['project'])['backend'], 'live')
            retained = destination / 'state/live/observations' / (saved['fingerprint'] + '.json')
            self.assertEqual(json.loads(retained.read_text()), snapshot)
            replay = self.live.attach(destination, self.session.descriptor_path, scene='Scene', mode='autonomous',
                                      brief_file=self.brief, blender='blender')
            self.assertEqual(replay, result)
            self.assertEqual(calls.count('attach_apply'), 1)

    def test_attach_succeeds_when_alignment_retains_observation_before_binding(self):
        self._attach_with_native_boundary()

    def test_attach_refuses_foreign_live_directory_without_overwriting_it(self):
        self._attach_with_native_boundary(foreign_live=True)

    def test_new_attach_requires_brief_mode_and_explicit_scene(self):
        for kwargs in ({}, {'mode': 'autonomous'}, {'mode': 'autonomous', 'brief_file': self.brief}):
            with mock.patch.object(self.live.blender_bridge, 'call') as call:
                with self.assertRaises(ValueError):
                    self.live.attach(self.workspace / 'project', self.session.descriptor_path, blender='blender', **kwargs)
            call.assert_not_called()

    def test_attach_destination_cannot_escape_paired_workspace(self):
        with mock.patch.object(self.live.blender_bridge, 'call') as call:
            with self.assertRaisesRegex(ValueError, 'workspace'):
                self.live.attach(self.workspace.parent / 'outside', self.session.descriptor_path,
                                 scene='Scene', mode='autonomous', brief_file=self.brief, blender='blender')
        call.assert_not_called()

    def test_incomplete_attachment_never_replays_identity_assignment(self):
        destination = self.workspace / 'project'; destination.mkdir()
        (destination / 'attach-request.json').write_text('{}')
        with mock.patch.object(self.live.blender_bridge, 'call') as call:
            with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
                self.live.attach(destination, self.session.descriptor_path, scene='Scene', mode='autonomous',
                                 brief_file=self.brief, blender='blender')
        call.assert_not_called()

    def test_existing_project_requires_explicit_parent(self):
        destination = self.workspace / 'project'; destination.mkdir()
        (destination / 'state').mkdir()
        with mock.patch.object(self.live.blender_bridge, 'call') as call:
            with self.assertRaises(ValueError):
                self.live.attach(destination, self.session.descriptor_path, scene='Scene', mode='autonomous',
                                 brief_file=self.brief, blender='blender')
        call.assert_not_called()
