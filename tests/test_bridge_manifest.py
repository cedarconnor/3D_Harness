"""A protocol number alone cannot identify the implementation of a live writer."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import uuid
import zipfile

from dcc_harness import blender_bridge, distribution


class ManifestTests(unittest.TestCase):
    def test_handshake_errors_also_redact_private_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            descriptor = Path(tmp) / 'private.json'; token = 'a' * 64
            descriptor.write_text(json.dumps({'schema': 'dcc.blender.session.v1', 'port': 9878,
                'session_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4()), 'workspace': tmp, 'token': token}))
            with mock.patch.object(blender_bridge, '_request', side_effect=RuntimeError(token)):
                with self.assertRaises(RuntimeError) as error:
                    blender_bridge.call('inspect', {}, binding=descriptor)
            self.assertNotIn(token, str(error.exception))

    def test_missing_or_modified_export_is_refused(self):
        verify = getattr(distribution, 'verify_addon', None)
        self.assertTrue(callable(verify), 'Standalone export verifier missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = root / 'good.zip'
            distribution.export_addon(original)
            good = verify(original)
            self.assertEqual(good['identity'], distribution.bridge_manifest())
            with zipfile.ZipFile(original) as archive:
                contents = {name: archive.read(name) for name in archive.namelist()}
            for kind in ('missing', 'changed'):
                target = root / (kind + '.zip')
                with zipfile.ZipFile(target, 'w') as archive:
                    for name, data in contents.items():
                        if name.endswith('/jobs.py'):
                            if kind == 'missing': continue
                            data += b'\n# drift\n'
                        archive.writestr(name, data)
                with self.assertRaises(ValueError): verify(target)

    def test_different_bridge_code_is_refused_before_authenticated_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            descriptor = Path(tmp) / 'private.json'
            descriptor.write_text(json.dumps({'schema': 'dcc.blender.session.v1', 'port': 9878,
                'session_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4()), 'workspace': tmp, 'token': 'a' * 64}))
            meta = distribution.upstream()
            info = {'harness_protocol': 3, 'protocol_version': meta['protocol'], 'upstream_commit': meta['commit'],
                    'features': sorted(blender_bridge.FEATURES), 'paired_commands': sorted(blender_bridge.PAIRED_COMMANDS),
                    'bridge_manifest': '0' * 64}
            with mock.patch.object(blender_bridge, '_request', side_effect=[info, {'ok': True}]) as send:
                with self.assertRaisesRegex(ValueError, 'manifest'):
                    blender_bridge.call('inspect', {}, binding=descriptor)
            self.assertEqual(send.call_count, 1)
