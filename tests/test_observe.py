"""Portable checks around the saved-file observe command; native runs are qualified separately."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from dcc_harness import observe
from dcc_harness.evidence import file_hash, write_json
from test_continuity_checks import observation, resign


class ObserveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.source = self.base / 'scene.blend'
        self.source.write_bytes(b'synthetic saved native - not Blender qualification')

    def fake_worker(self, **changes):
        """Stand in for Blender: write a synthetic observation where the real worker would."""
        def run(blender, folder, worker, action, request):
            obs = copy.deepcopy(observation())
            obs['checkpoint_sha256'] = request['source']['sha256']
            obs['native_dirty'] = False
            obs.update(changes)
            write_json(Path(request['out']) / 'observation.json', resign(obs))
        return run

    def run_observe(self, worker):
        with mock.patch.object(observe, 'run_worker', side_effect=worker):
            return observe.observe_file(self.source, self.base / 'out', 'blender.exe')

    def test_clean_saved_observation_is_ready_and_bound_to_the_source(self):
        result = self.run_observe(self.fake_worker())
        self.assertEqual(result['status'], 'READY')
        self.assertTrue(result['passed'])
        self.assertEqual(result['checkpoint_sha256'], file_hash(self.source))
        self.assertEqual(result['objects'], 1)
        self.assertTrue(Path(result['observation']).is_file())

    def test_observation_issues_are_reported_and_fail(self):
        result = self.run_observe(self.fake_worker(issues=['Unsupported instancer: Trees']))
        self.assertEqual(result['status'], 'HAS_ISSUES')
        self.assertFalse(result['passed'])
        self.assertEqual(result['issues'], ['Unsupported instancer: Trees'])

    def test_unsaved_native_state_is_not_ready(self):
        self.assertFalse(self.run_observe(self.fake_worker(native_dirty=True))['passed'])

    def test_observation_of_other_bytes_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'not bound'):
            self.run_observe(self.fake_worker(checkpoint_sha256='0' * 64))

    def test_source_changed_during_observation_is_rejected(self):
        inner = self.fake_worker()

        def changing(*args):
            inner(*args)
            self.source.write_bytes(b'changed while observing')
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            self.run_observe(changing)

    def test_invalid_inputs_are_rejected_before_launch(self):
        text = self.base / 'scene.txt'
        text.write_text('not a blend', encoding='utf-8')
        for source in (text, self.base / 'missing.blend'):
            with self.assertRaises(ValueError):
                observe.observe_file(source, self.base / 'never', 'no-blender-should-launch')
        self.assertFalse((self.base / 'never').exists())
        (self.base / 'taken').mkdir()
        with self.assertRaises(FileExistsError):
            observe.observe_file(self.source, self.base / 'taken', 'no-blender-should-launch')


if __name__ == '__main__':
    unittest.main()
