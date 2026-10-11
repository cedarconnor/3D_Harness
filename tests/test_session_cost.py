"""Session cost receipts for trial transcripts (build-plan item M5)."""
import json
from pathlib import Path
import tempfile
import unittest

from dcc_harness import session_cost


def row(kind, at, **extra):
    return {'type': kind, 'timestamp': f'2026-10-11T{at}Z', **extra}


def reply(at, message_id, usage, tools=0):
    content = [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls'}} for _ in range(tools)]
    return row('assistant', at, message={'id': message_id, 'model': 'claude-opus-5-5', 'content': content, 'usage': usage})


USAGE = {'input_tokens': 10, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 0, 'output_tokens': 5}
LATER = {'input_tokens': 4, 'cache_creation_input_tokens': 20, 'cache_read_input_tokens': 300, 'output_tokens': 50}


class SessionCostTests(unittest.TestCase):
    def transcript(self, rows):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / 'agent-x.jsonl'
        path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
        return path

    def test_turns_tokens_and_cache_share(self):
        path = self.transcript([
            row('user', '10:00:00', message={'content': 'Read BRIEF.md'}),
            reply('10:00:05', 'm1', {**USAGE, 'output_tokens': 1}),  # a streamed partial row of the same request
            reply('10:00:06', 'm1', USAGE, tools=1),
            row('user', '10:00:30', message={'content': [{'type': 'tool_result'}]}),
            reply('10:31:00', 'm2', LATER, tools=2)])
        receipt = session_cost.receipt(path, ceiling_minutes=90, ceiling_usd=25)
        self.assertEqual(receipt['turns'], 2)
        self.assertEqual(receipt['tool_calls'], 3)
        self.assertEqual(receipt['elapsed_minutes'], 31.0)
        self.assertEqual(receipt['tokens'], {'input': 14, 'cache_creation': 120, 'cache_read': 300, 'output': 55})
        self.assertAlmostEqual(receipt['cache_read_share'], 300 / 434, places=4)
        self.assertEqual(receipt['models'], ['claude-opus-5-5'])
        self.assertTrue(receipt['within_minutes'])

    def test_spend_is_unavailable_unless_the_transcript_reports_it(self):
        path = self.transcript([row('user', '10:00:00', message={'content': 'go'}), reply('11:35:00', 'm1', USAGE)])
        receipt = session_cost.receipt(path, ceiling_minutes=90, ceiling_usd=25)
        self.assertIsNone(receipt['metered_spend_usd'])
        self.assertIsNone(receipt['within_usd'])
        self.assertIn('unavailable', receipt['spend_status'])
        self.assertFalse(receipt['within_minutes'])
        priced = self.transcript([row('user', '10:00:00', message={'content': 'go'}), {**reply('10:01:00', 'm1', USAGE), 'costUSD': 0.75},
                                  {**reply('10:02:00', 'm2', USAGE), 'costUSD': 0.5}])
        spent = session_cost.receipt(priced, ceiling_minutes=90, ceiling_usd=1)
        self.assertEqual((spent['metered_spend_usd'], spent['within_usd']), (1.25, False))

    def test_the_receipt_names_the_transcript_by_hash(self):
        path = self.transcript([row('user', '10:00:00', message={'content': 'go'}), reply('10:01:00', 'm1', USAGE)])
        receipt = session_cost.receipt(path)
        self.assertEqual(receipt['schema'], 'dcc.trial.session-cost.v1')
        self.assertEqual(len(receipt['transcript']['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
