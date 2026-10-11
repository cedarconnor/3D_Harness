"""The agent quick reference must stay runnable: its commands parse and its payloads validate."""
import json
from pathlib import Path
import re
import shlex
import unittest

import dcc_harness
from dcc_harness.__main__ import build_parser
from dcc_harness.continuity_checks import validate_contract
from dcc_harness.relations import validate_relations
from dcc_harness.render import validate_views

PAGE = Path(__file__).resolve().parents[1] / 'docs/guides/AGENT_QUICK_REFERENCE.md'
PREFIX = 'python -m dcc_harness '


def blocks(language):
    return re.findall(r'^```' + language + r'\n(.*?)^```', PAGE.read_text(encoding='utf-8'), re.M | re.S)


def commands():
    lines = []
    for block in blocks('powershell'):
        lines += [line.strip() for line in block.splitlines() if line.strip().startswith(PREFIX)]
    return lines


@unittest.skipUnless(PAGE.exists(), 'documentation is checked from the source tree, not an installed runtime')
class QuickReferenceTests(unittest.TestCase):
    def test_every_command_parses_with_the_real_parser(self):
        parser = build_parser()
        found = commands()
        self.assertGreater(len(found), 10)
        for line in found:
            with self.subTest(line=line):
                parser.parse_args(shlex.split(line[len(PREFIX):]))

    def test_the_common_loop_is_covered(self):
        used = {shlex.split(line[len(PREFIX):])[0] for line in commands()}
        self.assertLessEqual({'brief', 'next', 'observe', 'begin-edit', 'finish-edit', 'fill-hashes',
                              'feedback-respond', 'requirements', 'stage-submit', 'render', 'render-wait', 'relations'}, used)

    def test_every_quoted_stop_message_exists_in_the_runtime(self):
        source = ''.join(p.read_text(encoding='utf-8') for p in Path(dcc_harness.__file__).parent.glob('*.py'))
        stops = PAGE.read_text(encoding='utf-8').split('## Stops', 1)[1]
        messages = re.findall(r'^\| `([^`]+)`', stops, re.M)
        self.assertGreater(len(messages), 5)
        for message in messages:
            with self.subTest(message=message):
                self.assertIn(message, source)

    def test_payload_examples_have_the_required_shape(self):
        payloads = [json.loads(block) for block in blocks('json')]
        schemas = {p.get('schema') for p in payloads}
        self.assertLessEqual({'dcc.continuity.contract.v1', 'dcc.feedback.response.v1', 'dcc.review.views.v1', 'dcc.relations.v1'}, schemas)
        for payload in payloads:
            if payload['schema'] == 'dcc.continuity.contract.v1':
                validate_contract(payload)
            elif payload['schema'] == 'dcc.review.views.v1':
                validate_views(payload)
            elif payload['schema'] == 'dcc.relations.v1':
                validate_relations(payload)
            elif payload['schema'] == 'dcc.feedback.response.v1':
                self.assertEqual(set(payload), {'schema', 'note_id', 'author', 'disposition', 'change', 'result', 'evidence'})


if __name__ == '__main__':
    unittest.main()
