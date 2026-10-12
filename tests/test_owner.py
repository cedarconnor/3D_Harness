import json
import os
import re
import subprocess
import sys
import uuid

from coordination_helpers import Console, Fixture
from dcc_harness import coordination as c, owner


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in owner.AGENT_MARKERS}
    env.update(extra)
    return env


class OwnerTests(Fixture):
    def approve(self, kind, value):
        return owner.confirm(kind, value, Console())

    def artist_stage(self, **policies):
        manifest = self.manifest()
        manifest['stages'][0]['review'] = 'artist_required'
        self.bind(manifest=manifest, **policies)
        return self.submit()

    def completion(self, submitted, role='artist'):
        return {'submission_id': submitted['revision'],
                'review': {'reviewer': self.actor(role), 'verdict': 'pass', 'finding': 'Reviewed the stated direction'}}

    def test_artist_completion_needs_an_owner_approval(self):
        submitted = self.artist_stage()
        value = self.completion(submitted)
        with self.assertRaisesRegex(RuntimeError, 'Owner approval required'):
            self.apply('stage.complete', value)
        other = self.approve('stage.complete', {**value, 'review': {**value['review'], 'finding': 'Something else'}})
        with self.assertRaisesRegex(RuntimeError, 'Owner approval required'):
            self.apply('stage.complete', value, approval=other)
        done = self.apply('stage.complete', value, approval=self.approve('stage.complete', value))
        self.assertEqual(done['status'], 'COMMITTED')
        self.assertEqual(done['result']['artistic_acceptance'], 'artist_confirmed')
        provenance = done['result']['owner_approval']
        self.assertEqual(provenance['channel'], 'owner_terminal')
        self.assertTrue(provenance['user'] and provenance['confirmed_at'] and re.fullmatch('[A-Z0-9]{4}', provenance['code']))

    def test_agent_completion_needs_no_owner(self):
        self.bind(); submitted = self.submit()
        done = self.apply('stage.complete', self.completion(submitted, 'agent'))
        self.assertEqual(done['result']['artistic_acceptance'], 'not_evaluated')
        self.assertNotIn('owner_approval', done['result'])

    def test_replay_needs_no_new_approval(self):
        submitted = self.artist_stage()
        value = self.completion(submitted); request = str(uuid.uuid4())
        self.apply('stage.complete', value, request=request, approval=self.approve('stage.complete', value))
        again = self.apply('stage.complete', value, request=request, expected=submitted['revision'])
        self.assertEqual(again['status'], 'ALREADY_COMMITTED')

    def test_every_artist_authority_needs_the_owner(self):
        nid = self.add(review_policy='artist_required'); response = self.respond(nid)
        verification = {'schema': 'dcc.feedback.verification.v1', 'note_id': nid, 'response_id': response['revision'],
                        'reviewer': self.actor('artist'), 'finding': 'Measured the intended table', 'verdict': 'pass', 'views': []}
        decision = {'schema': 'dcc.feedback.decision.v1', 'note_id': nid, 'action': 'deferred', 'reason': 'Later',
                    'authority': self.actor('artist'), 'result': self.cp()}
        for kind, value in (('feedback.verify', verification), ('feedback.decide', decision)):
            with self.subTest(kind=kind), self.assertRaisesRegex(RuntimeError, 'Owner approval required'):
                self.apply(kind, value)
        self.assertEqual(self.apply('feedback.decide', decision, approval=self.approve('feedback.decide', decision))['status'], 'COMMITTED')
        with self.assertRaisesRegex(RuntimeError, 'Owner approval required'):
            self.bind(authority=self.actor('artist'))
        self.bind()
        reopen = {'schema': 'dcc.environment.reopen.v1', 'stage_id': 'direction', 'reason': 'Revisit', 'authority': self.actor('artist')}
        with self.assertRaisesRegex(RuntimeError, 'Owner approval required'):
            self.apply('stage.reopen', reopen)

    def test_relaxing_an_artist_stage_needs_the_artist(self):
        manifest = self.manifest()
        manifest['stages'][0]['review'] = 'artist_required'
        with self.assertRaisesRegex(ValueError, 'Relaxing an artist-required stage'):
            self.bind(manifest=manifest, review_policies={'direction': 'agent_within_brief'})
        done = self.bind(manifest=manifest, review_policies={'direction': 'agent_within_brief'}, authority=self.actor('artist'), owner=True)
        self.assertEqual(done['status'], 'COMMITTED')
        self.assertEqual(done['result']['owner_approval']['channel'], 'owner_terminal')

    def test_console_refuses_agent_sessions_pipes_and_wrong_codes(self):
        value = {'submission_id': 'x', 'review': {'reviewer': self.actor('artist'), 'verdict': 'pass', 'finding': 'Looks right', 'answers': {'finish': 'Raw'}}}
        with self.assertRaisesRegex(RuntimeError, 'agent session.*CLAUDECODE.*own terminal'):
            owner.confirm('stage.complete', value, Console(environ={'CLAUDECODE': '1'}))
        # A current Codex shell sets its thread and session IDs, not CODEX_SANDBOX.
        for marker in ('CODEX_THREAD_ID', 'CODEX_SESSION_ID'):
            with self.subTest(marker=marker), self.assertRaisesRegex(RuntimeError, 'agent session.*' + marker):
                owner.confirm('stage.complete', value, Console(environ={marker: '0199a3c0-thread'}))
        with self.assertRaisesRegex(RuntimeError, 'interactive terminal'):
            owner.confirm('stage.complete', value, Console(tty=False))
        for answer in ('', 'ZZZZ', None):
            with self.subTest(answer=answer), self.assertRaisesRegex(RuntimeError, 'not confirmed'):
                owner.confirm('stage.complete', value, Console(answer=answer))
        console = Console()
        approval = owner.confirm('stage.complete', value, console)
        self.assertIn('Looks right', console.shown[0])
        self.assertIn('answers: {"finish": "Raw"}', console.shown[0])
        self.assertIn('stage.complete', console.shown[0])
        self.assertEqual(approval.request_hash, owner.request_hash('stage.complete', value))

    def test_only_artist_authority_is_claimed(self):
        self.assertTrue(owner.claims_artist('feedback.decide', {'authority': {'role': 'artist'}}))
        self.assertTrue(owner.claims_artist('workflow.bind', {'binding': {'authority': {'role': 'artist'}}}))
        self.assertFalse(owner.claims_artist('feedback.add', {'source': {'role': 'artist'}}))
        self.assertFalse(owner.claims_artist('stage.complete', {'review': {'reviewer': {'role': 'agent'}}}))
        self.assertFalse(owner.claims_artist('stage.complete', {'review': 'malformed'}))

    def test_cli_refuses_inside_an_agent_session_and_from_a_pipe(self):
        submitted = self.artist_stage()
        path = self.base / 'review.json'
        path.write_text(json.dumps(self.completion(submitted)['review']), encoding='utf-8')
        command = [sys.executable, '-m', 'dcc_harness', 'stage-complete', str(self.root), '--submission-id', submitted['revision'],
                   '--review', str(path), '--expected-revision', submitted['revision'], '--request-id', str(uuid.uuid4())]
        before = len(c.read(self.root))
        inside = subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=clean_env(CLAUDECODE='1'))
        self.assertNotEqual(inside.returncode, 0)
        self.assertIn('agent session', inside.stderr)
        piped = subprocess.run(command, capture_output=True, text=True, input='ABCD\n', env=clean_env())
        self.assertNotEqual(piped.returncode, 0)
        self.assertIn('interactive terminal', piped.stderr)
        self.assertEqual(len(c.read(self.root)), before)
