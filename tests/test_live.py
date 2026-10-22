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
