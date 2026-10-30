import contextlib
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest import mock

from dcc_harness.evidence import file_hash, read_json, write_json


class OwnedGuiQualificationTests(unittest.TestCase):
    def run_worker(self, folder, *, background=False, fails=False):
        scheduled, quit_calls, overrides, events = [], [], [], []
        window = types.SimpleNamespace(screen=object())
        context = types.SimpleNamespace(scene=object(), window=window,
                                         window_manager=types.SimpleNamespace(windows=[window]))

        def open_file(**kwargs):
            events.append('open')
            context.window = None  # open_mainfile invalidates the old timer context.

        @contextlib.contextmanager
        def temp_override(**kwargs):
            overrides.append(kwargs)
            previous = context.window
            context.window = kwargs['window']
            try:
                yield
            finally:
                context.window = previous

        def quit_blender():
            quit_calls.append(context.window)
            events.append('quit')

        def verify(*args):
            if fails:
                raise ValueError('fixture verification failed')
            events.append('verify')
            return {'passed': True}

        context.temp_override = temp_override
        bpy = types.SimpleNamespace(context=context,
            app=types.SimpleNamespace(background=background,
                timers=types.SimpleNamespace(register=lambda fn, **kwargs: scheduled.append((fn, kwargs)))),
            ops=types.SimpleNamespace(wm=types.SimpleNamespace(open_mainfile=open_file,
                quit_blender=quit_blender, save_as_mainfile=lambda **kwargs: None)))
        addons = types.SimpleNamespace(assert_profile=lambda profile: None, build=lambda: {}, NETWORK_ATTEMPTS=[])
        recipes = types.SimpleNamespace(verify=verify)
        candidate = folder / 'candidate.blend'
        candidate.write_bytes(b'owned fixture')
        request = {'profile': {}, 'root': str(folder), 'id': 'recipe', 'digest': 'digest',
                   'case': {'parameters': {}}, 'effect_id': 'owned',
                   'applied': {'candidate': {'path': str(candidate), 'sha256': file_hash(candidate)},
                               'result': {}}}
        request_path = folder / 'recipe_verify-request.json'
        write_json(request_path, request)
        bridge = types.ModuleType('dcc_harness.data.bridge')
        bridge.recipes, bridge.addons = recipes, addons
        environments = types.ModuleType('dcc_harness.environments')
        environments.load_profile = lambda ref: {}
        worker = Path(__file__).parents[1] / 'dcc_harness/_recipe_blender.py'
        with mock.patch.dict(sys.modules, {'bpy': bpy, 'dcc_harness.data.bridge': bridge,
                                           'dcc_harness.environments': environments}), \
             mock.patch.object(sys, 'argv', [str(worker), '--', 'recipe_verify', str(request_path)]):
            namespace = runpy.run_path(str(worker), run_name='__main__')
        return namespace, scheduled, quit_calls, overrides, events, context, window

    def test_file_open_tick_defers_quit_to_fresh_timer_window_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, scheduled, quit_calls, overrides, events, context, window = self.run_worker(folder)
            advance, options = scheduled.pop(0)
            self.assertGreater(options['first_interval'], 0)
            self.assertTrue(options.get('persistent'), 'Qualification must resume after owned baseline file load')
            self.assertIsNone(advance())
            self.assertEqual(events, ['open', 'verify'])
            self.assertEqual(quit_calls, [])
            self.assertTrue(read_json(folder / 'recipe_verify-result.json')['passed'])
            self.assertEqual(len(scheduled), 1)
            quit_tick, options = scheduled.pop(0)
            self.assertIsNot(quit_tick, advance)
            self.assertGreater(options['first_interval'], 0)
            self.assertIsNone(quit_tick())
            self.assertEqual(quit_calls, [window])
            self.assertEqual(overrides, [{'window': window}])

    def test_shutdown_waits_for_recreated_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, scheduled, quit_calls, _, _, context, window = self.run_worker(Path(temporary))
            scheduled.pop(0)[0]()
            quit_tick = scheduled.pop(0)[0]
            context.window_manager.windows.clear()
            self.assertGreater(quit_tick(), 0)
            self.assertFalse(quit_calls)
            context.window_manager.windows.append(window)
            self.assertIsNone(quit_tick())
            self.assertEqual(quit_calls, [window])

    def test_failed_verification_also_defers_owned_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, scheduled, quit_calls, _, _, _, _ = self.run_worker(folder, fails=True)
            scheduled.pop(0)[0]()
            self.assertFalse(read_json(folder / 'recipe_verify-result.json')['passed'])
            self.assertFalse(quit_calls)
            self.assertEqual(len(scheduled), 1)

    def test_background_worker_never_schedules_gui_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, scheduled, quit_calls, _, _, _, _ = self.run_worker(folder, background=True)
            self.assertTrue(read_json(folder / 'recipe_verify-result.json')['passed'])
            self.assertFalse(scheduled)
            self.assertFalse(quit_calls)


if __name__ == '__main__':
    unittest.main()
