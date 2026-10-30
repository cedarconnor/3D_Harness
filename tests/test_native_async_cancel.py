from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from dcc_harness import native, recipe_store


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now


class Child:
    def __init__(self, clock, exits_at=None):
        self.clock = clock
        self.exits_at = exits_at
        self.returncode = None
        self.killed = False
        self.reaped = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if timeout is None:
            self.reaped = True
            return self.returncode
        self.clock.now += timeout
        if self.exits_at is not None and self.clock.now >= self.exits_at:
            self.returncode = 0
        if self.returncode is None:
            raise subprocess.TimeoutExpired('owned', timeout)
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class NativeAsyncCancelTests(unittest.TestCase):
    def run_owned(self, child, clock, **kwargs):
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(native.subprocess, 'Popen', return_value=child), \
             mock.patch.object(native.time, 'monotonic', side_effect=clock.monotonic), \
             mock.patch.dict(native.os.environ, {}, clear=True):
            native.run_process(['owned'], Path(folder) / 'log', **kwargs)

    def test_cooperative_cancel_waits_but_refuses_success(self):
        clock = Clock()
        child = Child(clock, exits_at=.35)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_owned(child, clock, cancelled=lambda: clock.now >= .1, cancel_grace=.5)
        self.assertFalse(child.killed)
        self.assertTrue(child.reaped)
        self.assertGreaterEqual(clock.now, .35)

    def test_timeout_waits_for_cooperative_cleanup_but_still_raises(self):
        clock = Clock()
        child = Child(clock, exits_at=.35)
        with self.assertRaises(TimeoutError):
            self.run_owned(child, clock, timeout=.2, cancel_grace=.5)
        self.assertFalse(child.killed)
        self.assertTrue(child.reaped)

    def test_grace_expiry_kills_only_owned_child(self):
        clock = Clock()
        child = Child(clock)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_owned(child, clock, cancelled=lambda: clock.now >= .1, cancel_grace=.3)
        self.assertTrue(child.killed)
        self.assertTrue(child.reaped)
        self.assertAlmostEqual(clock.now, .4)

    def test_default_cancellation_still_kills_immediately(self):
        clock = Clock()
        child = Child(clock)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_owned(child, clock, cancelled=lambda: clock.now >= .1)
        self.assertTrue(child.killed)
        self.assertAlmostEqual(clock.now, .1)

    def test_predispatch_cancel_never_starts_child(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(native.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'before dispatch'):
                native.run_process(['owned'], Path(folder) / 'log', cancelled=lambda: True, cancel_grace=1)
            start.assert_not_called()

    def test_worker_infers_grace_from_pinned_async_bundle_without_adapter_import(self):
        request = {'capability': {'root': 'project', 'resolution': {
            'selected': {'recipe_id': 'shader', 'recipe_digest': 'abc'}}}}
        bundle = {'recipe': {'invocation': {'completion': 'asynchronous',
                                          'cancel_grace': 2., 'poll_interval': .25}}}
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(recipe_store, 'load', return_value=bundle) as load, \
             mock.patch.object(native, 'run_process') as run:
            native.run_worker('blender', Path(folder), 'worker.py', 'execute', request)
            load.assert_called_once_with('project', 'shader', 'abc')
            self.assertEqual(run.call_args.kwargs['cancel_grace'], 3.5)

    def test_normal_worker_and_sync_recipe_have_zero_grace(self):
        request = {'capability': {'root': 'project', 'resolution': {
            'selected': {'recipe_id': 'shader', 'recipe_digest': 'abc'}}}}
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(recipe_store, 'load', return_value={'recipe': {
                 'invocation': {'completion': 'synchronous'}}}), \
             mock.patch.object(native, 'run_process') as run:
            native.run_worker('blender', Path(folder), 'worker.py', 'execute', request)
            self.assertEqual(run.call_args.kwargs.get('cancel_grace', 0), 0)
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(native, 'run_process') as run:
            native.run_worker('blender', Path(folder), 'worker.py', 'execute', {})
            self.assertEqual(run.call_args.kwargs.get('cancel_grace', 0), 0)

    def test_exit_racing_cancellation_cannot_report_success(self):
        clock = Clock()
        child = Child(clock, exits_at=.1)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_owned(child, clock, cancelled=lambda: clock.now >= .1, cancel_grace=.5)
        self.assertFalse(child.killed)
        self.assertTrue(child.reaped)

    def test_invalid_grace_refuses_dispatch(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(native.subprocess, 'Popen') as start:
            for invalid in (-1, float('inf'), float('nan'), True, 121):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    native.run_process(['owned'], Path(folder) / 'log', cancel_grace=invalid)
            start.assert_not_called()

    def test_explicit_worker_grace_is_forwarded_and_verification_does_not_infer(self):
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(recipe_store, 'load') as load, \
             mock.patch.object(native, 'run_process') as run:
            native.run_worker('blender', Path(folder), 'worker.py', 'capability-verify',
                              {'capability': {}}, profile={'owned': True}, cancel_grace=1.25)
            load.assert_not_called()
            self.assertEqual(run.call_args.kwargs['cancel_grace'], 1.25)
            self.assertIn('BLENDER_USER_CONFIG', run.call_args.kwargs['env'])


if __name__ == '__main__':
    unittest.main()
