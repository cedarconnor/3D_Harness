"""Portable async lifecycle contract; callbacks stand in for provider boundaries."""
import importlib
import json
from pathlib import Path
import tempfile
import unittest


class AsyncRecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'operation'
        self.now = 0.0
        self.stop = False
        self.calls = []
        self.polls = [{'state': 'SUCCEEDED'}]
        self.callbacks = {
            'submit': lambda: self.record('submit', {'job': 7}),
            'poll': lambda handle: self.record('poll', self.polls.pop(0)),
            'cancel': lambda handle: self.record('cancel', {'requested': True}),
            'collect': lambda handle: self.record('collect', {'output': 'Cube'}),
        }
        self.invocation = {'poll_interval': 1, 'timeout': 10, 'cancel_grace': 3}

    def record(self, name, result):
        self.calls.append(name)
        return result

    def operation(self, **kwargs):
        module = importlib.import_module('dcc_harness.async_recipe')
        return module.AsyncOperation(self.folder, self.invocation, self.callbacks,
                                     clock=lambda: self.now, cancelled=lambda: self.stop, **kwargs)

    def test_success_dispatches_and_collects_once(self):
        op = self.operation()
        self.assertEqual(op.step()['state'], 'PENDING')
        status = op.step()
        self.assertEqual(status['state'], 'SUCCEEDED')
        self.assertEqual(status['result'], {'output': 'Cube'})
        self.assertEqual(op.step(), status)
        self.assertEqual(self.calls, ['submit', 'poll', 'collect'])

    def test_pending_poll_is_rate_limited_and_persists_progress(self):
        self.polls = [{'state': 'PENDING', 'progress': {'percent': 30}}, {'state': 'SUCCEEDED'}]
        op = self.operation()
        op.step()
        status = op.step()
        self.assertEqual(status['progress'], {'percent': 30})
        self.assertEqual(op.step()['state'], 'PENDING')
        self.assertEqual(self.calls, ['submit', 'poll'])
        self.now = 1
        self.assertEqual(op.step()['state'], 'SUCCEEDED')

    def test_cancel_before_submit_does_not_invoke(self):
        op = self.operation()
        self.stop = True
        self.assertEqual(op.step()['state'], 'CANCELLED')
        self.assertEqual(self.calls, [])

    def test_cancel_once_waits_for_terminal_and_never_collects(self):
        op = self.operation()
        op.step()
        self.stop = True
        self.assertEqual(op.step()['state'], 'PENDING')
        self.polls = [{'state': 'PENDING'}, {'state': 'SUCCEEDED'}]
        self.assertEqual(op.step()['state'], 'PENDING')
        self.now = 1
        self.assertEqual(op.step()['state'], 'CANCELLED')
        self.assertEqual(self.calls.count('cancel'), 1)
        self.assertNotIn('collect', self.calls)

    def test_timeout_cancel_grace_expiry_requires_reconciliation(self):
        op = self.operation()
        op.step()
        self.now = 10
        self.assertEqual(op.step()['state'], 'PENDING')
        self.now = 13
        status = op.step()
        self.assertEqual(status['state'], 'NEEDS_RECONCILIATION')
        self.assertNotIn('result', status)
        self.assertEqual(self.calls, ['submit', 'cancel'])

    def test_provider_failure_and_cancelled_are_terminal_without_collect(self):
        for state in ('FAILED', 'CANCELLED'):
            with self.subTest(state=state):
                self.folder = Path(self.tmp.name) / state
                self.polls = [{'state': state, 'error': 'provider stopped'}]
                op = self.operation()
                op.step()
                self.assertEqual(op.step()['state'], state)
                self.assertNotIn('result', op.step())
        self.assertNotIn('collect', self.calls)

    def test_restored_pending_is_read_only_and_never_dispatches(self):
        op = self.operation()
        op.step()
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        restored = self.operation()
        self.assertEqual(restored.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
        self.assertEqual(self.calls, ['submit'])

    def test_restored_success_returns_retained_result_without_callbacks(self):
        op = self.operation()
        op.step()
        expected = op.step()
        self.assertEqual(self.operation().step(), expected)
        self.assertEqual(self.calls, ['submit', 'poll', 'collect'])

    def test_response_loss_never_replays_submit_or_collect(self):
        for boundary in ('submit', 'collect'):
            with self.subTest(boundary=boundary):
                self.folder = Path(self.tmp.name) / boundary
                self.polls = [{'state': 'SUCCEEDED'}]
                def lost(*args):
                    self.calls.append(boundary)
                    raise RuntimeError('response lost')
                original = self.callbacks[boundary]
                self.callbacks[boundary] = lost
                op = self.operation()
                if boundary == 'collect':
                    op.step()
                self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')
                calls = list(self.calls)
                self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')
                self.assertEqual(self.operation().step()['state'], 'NEEDS_RECONCILIATION')
                self.assertEqual(self.calls, calls)
                self.callbacks[boundary] = original

    def test_intents_are_durable_before_callback(self):
        for boundary in ('submit', 'collect', 'cancel'):
            with self.subTest(boundary=boundary):
                self.folder = Path(self.tmp.name) / boundary
                self.polls = [{'state': 'SUCCEEDED'}]
                def inspect(*args):
                    events = sorted(self.folder.glob('event-*.json'))
                    state = json.loads(events[-1].read_text())
                    self.assertEqual(state['phase'], boundary.upper() + '_INTENT')
                    self.assertTrue(state['operation_id'])
                    return {'id': 1}
                original = self.callbacks[boundary]
                self.callbacks[boundary] = inspect
                op = self.operation()
                op.step()
                if boundary == 'cancel':
                    self.stop = True
                if boundary != 'submit':
                    op.step()
                self.stop = False
                self.callbacks[boundary] = original

    def test_corrupt_state_requires_reconciliation(self):
        op = self.operation()
        op.step()
        sorted(self.folder.glob('event-*.json'))[-1].write_text('{broken')
        self.assertEqual(self.operation().step()['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.calls, ['submit'])

    def test_invalid_or_oversized_provider_json_requires_reconciliation(self):
        for value in (object(), {'bad': float('nan')}, 'x' * 70000):
            with self.subTest(value_type=type(value).__name__):
                self.folder = Path(self.tmp.name) / str(len(list(Path(self.tmp.name).iterdir())))
                self.callbacks['submit'] = lambda: value
                self.assertEqual(self.operation().step()['state'], 'NEEDS_RECONCILIATION')

    def test_cancel_failure_and_unknown_poll_never_publish(self):
        op = self.operation()
        op.step()
        self.stop = True
        op.callbacks['cancel'] = lambda handle: (_ for _ in ()).throw(RuntimeError('unknown termination'))
        self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertNotIn('collect', self.calls)
        self.folder = Path(self.tmp.name) / 'unknown'
        self.stop = False
        self.polls = [{'state': 'RUNNING_MODAL'}]
        op = self.operation()
        op.step()
        self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')

    def test_failed_cancellation_response_requires_reconciliation(self):
        self.callbacks['cancel'] = lambda handle: {'state': 'FAILED'}
        op = self.operation()
        op.step()
        self.stop = True
        self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')

    def test_deadline_during_poll_does_not_collect(self):
        def poll(handle):
            self.now = 11
            return {'state': 'SUCCEEDED'}
        self.callbacks['poll'] = poll
        op = self.operation()
        op.step()
        self.assertNotEqual(op.step()['state'], 'SUCCEEDED')
        self.assertNotIn('collect', self.calls)

    def test_interrupted_dispatch_cannot_advance_same_instance(self):
        def interrupted():
            raise KeyboardInterrupt('dispatch interrupted')
        self.callbacks['submit'] = interrupted
        op = self.operation()
        with self.assertRaises(KeyboardInterrupt):
            op.step()
        self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.calls, [])

    def test_large_bounded_result_can_be_read_as_status(self):
        self.callbacks['collect'] = lambda handle: 'x' * 65500
        op = self.operation()
        op.step()
        self.assertEqual(op.step()['state'], 'SUCCEEDED')
        self.assertEqual(self.operation().step()['state'], 'SUCCEEDED')

    def test_corrupt_success_without_result_requires_reconciliation(self):
        op = self.operation()
        op.step()
        op.step()
        latest = sorted(self.folder.glob('event-*.json'))[-1]
        data = json.loads(latest.read_text())
        del data['result']
        latest.write_text(json.dumps(data))
        self.assertEqual(self.operation().step()['state'], 'NEEDS_RECONCILIATION')

    def test_deadline_during_collect_prevents_success(self):
        def collect(handle):
            self.now = 11
            return {'output': 'Cube'}
        self.callbacks['collect'] = collect
        op = self.operation()
        op.step()
        self.assertEqual(op.step()['state'], 'CANCELLED')
        self.assertNotIn('result', op.step())

    def test_supplied_managed_operation_uuid_is_retained_and_checked(self):
        identity = '6d101f55-0d5a-4fa6-81fb-862945202a17'
        op = self.operation(operation_id=identity)
        self.assertEqual(op.step()['operation_id'], identity)
        op.step()
        self.assertEqual(self.operation(operation_id=identity).step()['state'], 'SUCCEEDED')
        mismatch = self.operation(operation_id='a41e18df-39fb-4b23-a175-3c41d26ae97b')
        self.assertEqual(mismatch.step()['state'], 'NEEDS_RECONCILIATION')

    def test_supplied_operation_uuid_must_be_canonical(self):
        for identity in ('invalid', '6D101F55-0D5A-4FA6-81FB-862945202A17', 5):
            with self.subTest(identity=identity):
                with self.assertRaises(ValueError):
                    self.operation(operation_id=identity)
        self.assertFalse(self.folder.exists())

    def test_cancel_callback_crossing_grace_requires_reconciliation(self):
        def cancel(handle):
            self.now = 4
            return {'requested': True}
        self.callbacks['cancel'] = cancel
        op = self.operation()
        op.step()
        self.stop = True
        self.assertEqual(op.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertNotIn('collect', self.calls)

    def test_driver_confirms_cancellation_when_poll_interval_exceeds_grace(self):
        self.invocation.update(poll_interval=5, cancel_grace=0.2)
        op = self.operation()
        self.polls = [{'state': 'CANCELLED'}]
        def sleep(seconds):
            self.now += seconds
            self.stop = True
        self.assertEqual(op.drive(sleep=sleep)['state'], 'CANCELLED')
        self.assertEqual(self.calls, ['submit', 'cancel', 'poll'])
        self.assertLessEqual(self.now, 1.05)
        self.assertEqual(op.invocation['poll_interval'], 5)

    def test_returned_interval_wakes_on_deadline_then_polls_before_grace(self):
        self.invocation.update(poll_interval=5, timeout=0.1, cancel_grace=0.1)
        op = self.operation()
        status = op.step()
        self.assertLessEqual(status['poll_interval'], 0.1)
        self.now += status['poll_interval']
        status = op.step()
        self.assertEqual(self.calls, ['submit', 'cancel'])
        self.assertLessEqual(status['poll_interval'], 0.025)
        self.assertGreater(status['poll_interval'], 0)
        self.now += status['poll_interval']
        self.polls = [{'state': 'CANCELLED'}]
        self.assertEqual(op.step()['state'], 'CANCELLED')
        self.assertEqual(self.calls, ['submit', 'cancel', 'poll'])

    def test_cancelling_pending_polls_continue_within_grace(self):
        self.invocation.update(poll_interval=5, cancel_grace=0.2)
        op = self.operation()
        op.step()
        self.stop = True
        status = op.step()
        self.polls = [{'state': 'PENDING'}, {'state': 'CANCELLED'}]
        for expected in ('PENDING', 'CANCELLED'):
            self.now += status['poll_interval']
            status = op.step()
            self.assertEqual(status['state'], expected)
        self.assertLess(self.now, 0.2)
        self.assertEqual(self.calls, ['submit', 'cancel', 'poll', 'poll'])

    def test_slow_cancel_response_still_polls_before_remaining_grace(self):
        self.invocation.update(poll_interval=5, cancel_grace=0.2)
        def cancel(handle):
            self.now += 0.19
            return {'requested': True}
        self.callbacks['cancel'] = cancel
        op = self.operation()
        op.step()
        self.stop = True
        status = op.step()
        self.assertLess(status['poll_interval'], 0.01)
        self.now += status['poll_interval']
        self.polls = [{'state': 'CANCELLED'}]
        self.assertEqual(op.step()['state'], 'CANCELLED')

    def test_drive_uses_bounded_sleep(self):
        op = self.operation()
        self.polls = [{'state': 'PENDING'}, {'state': 'SUCCEEDED'}]
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            self.now += seconds
        self.assertEqual(op.drive(sleep=sleep)['state'], 'SUCCEEDED')
        self.assertTrue(sleeps)
        self.assertTrue(all(0 < delay <= 1 for delay in sleeps))


if __name__ == '__main__':
    unittest.main()
