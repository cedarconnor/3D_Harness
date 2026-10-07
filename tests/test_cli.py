"""Command-line result handling: printing, receipts and exit status."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from coordination_helpers import Fixture
from dcc_harness.evidence import write_json


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], capture_output=True, text=True)


class CliOutputTests(unittest.TestCase):
    def test_existing_out_path_still_prints_the_result_and_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'manifest.json'
            out.write_text('keep', encoding='utf-8')
            result = cli('workflow-template', '--out', out)
            self.assertEqual(json.loads(result.stdout)['schema'], 'dcc.environment.workflow.v1')
            self.assertEqual(result.returncode, 2)
            self.assertIn('not written', result.stderr)
            self.assertEqual(out.read_text(encoding='utf-8'), 'keep')

    def test_legacy_pilot_commands_are_labeled_in_help(self):
        result = cli('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ('init', 'status', 'begin', 'finish'):
            self.assertRegex(result.stdout, rf'\n\s+{command}\s+Legacy pilot journal')


class CoordinationExitStatusTests(Fixture):
    def test_failed_verification_is_committed_and_exits_nonzero(self):
        note = self.add()
        response = self.respond(note)
        verification = self.base / 'verification.json'
        write_json(verification, {'schema': 'dcc.feedback.verification.v1', 'note_id': note,
                                  'response_id': response['revision'], 'reviewer': self.actor(),
                                  'finding': 'The table is still the wrong length', 'verdict': 'fail', 'views': []})
        result = cli('feedback-verify', self.root, '--verification', verification, '--expected-revision',
                     self.revision(), '--request-id', uuid.uuid4(), '--evidence-root', self.base)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['status'], 'COMMITTED')
        self.assertIs(payload['result']['passed'], False)
        self.assertEqual(result.returncode, 1)


if __name__ == '__main__':
    unittest.main()
