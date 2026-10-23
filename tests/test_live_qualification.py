"""Cancellation-fixture synchronization must not confuse queued and running work."""
import importlib.util
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from dcc_harness import execution
from dcc_harness.evidence import read_json, write_json


class CancellationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name); self.root = self.out / 'state'
        self.operation_id = str(uuid.uuid4())
        self.operation = self.root / 'execution/operations' / self.operation_id
        self.operation.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('live_qualifier', Path(__file__).resolve().parents[1] / 'scripts/qualify_live.py')
        self.qualifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.qualifier)
        self.process = SimpleNamespace(poll=lambda: None); self.stop = threading.Event()

    def evidence(self, state='RUNNING', started=True):
        write_json(self.out / 'mutation-barrier.json', {'operation_id': self.operation_id,
            'before': [0, 0, 0], 'after': [2, 1, 0], 'mutated_at': time.time()})
        write_json(self.operation / 'live-status.json', {'operation_id': self.operation_id,
            'state': state, 'mutation_started': started})

    def invoke(self, seconds=1):
        return self.qualifier.cancel_after_native_mutation(self.root, self.operation_id, self.out,
                                                          self.process, self.stop, seconds=seconds)

    def test_requests_public_operation_cancel_only_after_measured_running_mutation(self):
        self.evidence()
        with patch.object(execution, 'configuration', return_value={}):
            proof = self.invoke()
        durable = read_json(self.root / 'execution/cancellations' / (self.operation_id + '.json'))
        self.assertEqual(durable['operation_id'], self.operation_id)
        self.assertEqual(proof['durable_request'], durable)
        self.assertEqual(proof['api_result']['status'], 'CANCEL_REQUESTED')

    def test_queued_cancellation_is_not_interrupted_mutation_proof(self):
        self.evidence('CANCELLED', False)
        with patch.object(execution, 'cancel_operation') as cancel:
            with self.assertRaisesRegex(ValueError, 'RUNNING'):
                self.invoke()
        cancel.assert_not_called()

    def test_controller_exit_aborts_wait_without_requesting_cancellation(self):
        self.stop.set()
        with patch.object(execution, 'cancel_operation') as cancel:
            with self.assertRaisesRegex(RuntimeError, 'before native mutation'):
                self.invoke()
        cancel.assert_not_called()

    def test_absent_mutation_barrier_has_bounded_timeout(self):
        with patch.object(execution, 'cancel_operation') as cancel:
            with self.assertRaisesRegex(TimeoutError, 'native mutation'):
                self.invoke(seconds=.01)
        cancel.assert_not_called()


if __name__ == '__main__':
    unittest.main()
