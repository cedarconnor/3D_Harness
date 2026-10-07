import concurrent.futures
import copy
from pathlib import Path
import uuid
from unittest.mock import patch

from coordination_helpers import Fixture
from dcc_harness import coordination as c, workflow
from dcc_harness.evidence import file_hash


class CoordinationTests(Fixture):
    def test_absent_extension_keeps_legacy_packet(self):
        self.assertNotIn('coordination', workflow.resume(self.root))

    def test_acknowledgement_recovery_is_idempotent_even_after_later_events(self):
        request = str(uuid.uuid4()); note = self.note()
        one = self.apply('feedback.add', note, request=request)
        self.add(text='Another note')
        hashes = {str(p): file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        replay = self.apply('feedback.add', note, request=request, expected='none')
        self.assertEqual(replay['status'], 'ALREADY_COMMITTED')
        self.assertEqual(replay['result'], one['result'])
        self.assertEqual(hashes, {str(p): file_hash(p) for p in self.root.rglob('*') if p.is_file()})
        with self.assertRaisesRegex(ValueError, 'different content'):
            self.apply('feedback.add', {**note, 'text': 'changed'}, request=request)

    def test_partial_commit_prevents_replay(self):
        original = c._write
        def broken(path, value):
            if path.name == 'manifest.json':
                raise OSError('injected disk failure')
            original(path, value)
        with patch.object(c, '_write', broken), self.assertRaises(OSError):
            self.add()
        with self.assertRaisesRegex(RuntimeError, 'Partial'):
            self.add()
        with self.assertRaisesRegex(RuntimeError, 'Partial'):
            workflow.resume(self.root)

    def test_corrupt_inventory_blocks_resume(self):
        self.add()
        path = self.root / 'coordination/events/000001/event.json'
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed'):
            workflow.resume(self.root)

    def test_stale_revision_and_concurrent_writer(self):
        value = self.note()
        def attempt(_):
            try:
                return self.apply('feedback.add', value, expected='none')
            except (ValueError, RuntimeError):
                return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(x is not None for x in results), 1)

    def test_invalid_paths_reject_without_store_creation(self):
        for name in ('../escape', 'x/../escape', '/absolute', 'C:/absolute', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                c.relative(self.base, name)
        self.assertFalse((self.root / 'coordination').exists())

    def test_note_can_be_recorded_while_native_pending(self):
        self.begin()
        self.add()
        packet = workflow.resume(self.root)
        self.assertEqual(packet['status'], 'RECONCILE')
        self.assertEqual(len(packet['pending']), 1)
        self.assertEqual(packet['coordination']['total_notes'], 1)
