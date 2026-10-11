"""Agent guidance: next steps, stage requirements and the generated brief."""
import json
from pathlib import Path
import subprocess
import sys
import uuid

from coordination_helpers import Fixture
from dcc_harness import coordination as c, guidance
from dcc_harness.payloads import fill_hashes


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], capture_output=True, text=True)


def ids(result):
    return [step['id'] for step in result['steps']]


def step(result, sid):
    return next(s for s in result['steps'] if s['id'] == sid)


class NextStepTests(Fixture):
    def test_ready_project_offers_observe_then_begin_edit_with_recorded_values(self):
        result = guidance.next_steps(self.root)
        self.assertEqual(result['schema'], 'dcc.next.v1')
        self.assertEqual(result['status'], 'READY_FOR_INSPECTION')
        self.assertEqual(ids(result), ['observe', 'begin-edit'])
        active = self.packet['active']
        command = step(result, 'begin-edit')['command']
        self.assertIn('--parent ' + active['id'], command)
        self.assertIn('--current "' + active['checkpoint'] + '"', command)
        self.assertIn('"' + active['checkpoint'] + '"', step(result, 'observe')['command'])
        self.assertEqual(result['used_labels'], ['initial'])

    def test_reserved_edit_offers_only_its_finish(self):
        edit = self.begin()['edit']
        result = guidance.next_steps(self.root)
        self.assertEqual(result['status'], 'RECONCILE')
        self.assertEqual(ids(result), ['finish-edit'])
        finish = step(result, 'finish-edit')
        self.assertIn(' ' + edit + ' ', finish['command'])
        self.assertIn('never', finish['why'].lower())

    def test_metadata_lock_offers_only_inspection(self):
        (self.root / 'workflow.lock').write_text('{}', encoding='utf-8')
        result = guidance.next_steps(self.root)
        self.assertEqual(ids(result), ['inspect-lock'])
        self.assertIsNone(result['steps'][0]['command'])

    def test_open_note_offers_a_response_with_revision_and_fresh_request_id(self):
        self.bind()
        note = self.add()
        result = guidance.next_steps(self.root)
        self.assertEqual(result['revision'], self.revision())
        respond = next(s for s in result['steps'] if s['id'] == 'feedback-respond' and s['note_id'] == note)
        self.assertIn('--expected-revision ' + self.revision(), respond['command'])
        request = respond['command'].split('--request-id ')[1].split()[0]
        self.assertEqual(str(uuid.UUID(request)), request)
        self.assertLess(ids(result).index('begin-edit'), ids(result).index('feedback-respond'))

    def test_implemented_response_offers_verification_by_another_reviewer(self):
        self.bind()
        note = self.add()
        response = self.respond(note)
        verify = step(guidance.next_steps(self.root), 'feedback-verify')
        self.assertEqual(verify['note_id'], note)
        self.assertEqual(verify['response_id'], response['revision'])
        self.assertIn('separate reviewer', verify['why'])

    def test_ready_stage_points_to_requirements_and_pending_submission_to_completion(self):
        self.bind()
        submit = step(guidance.next_steps(self.root), 'stage-submit')
        self.assertEqual(submit['stage_id'], 'direction')
        self.assertIn('requirements "' + str(self.root) + '" direction', submit['command'])
        submitted = self.submit()
        complete = step(guidance.next_steps(self.root), 'stage-complete')
        self.assertIn('--submission-id ' + submitted['revision'], complete['command'])
        self.assertIn('--expected-revision ' + submitted['revision'], complete['command'])
        self.assertNotIn('stage-submit', ids(guidance.next_steps(self.root)))

    def test_artist_required_stage_is_flagged(self):
        self.bind(review_policies={'direction': 'artist_required'})
        self.submit()
        complete = step(guidance.next_steps(self.root), 'stage-complete')
        self.assertTrue(complete['artist_required'])
        self.assertIn('review-page', complete['why'])
        self.assertIn('own terminal', complete['why'])

    def publish_review_views(self):
        from dcc_harness import workflow
        from test_render import VIEWS
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {'review_views': VIEWS})

    def test_review_views_add_a_render_step_for_the_active_checkpoint(self):
        self.publish_review_views()
        result = guidance.next_steps(self.root)
        self.assertEqual(ids(result), ['observe', 'begin-edit', 'render'])
        command = step(result, 'render')['command']
        active = guidance.next_steps(self.root)['active']
        self.assertIn('render "' + active['checkpoint'] + '" --blender "<BLENDER>"', command)
        self.assertIn('--project "' + str(self.root) + '"', command)

    def test_review_views_add_a_candidate_render_before_finishing_a_reserved_edit(self):
        self.publish_review_views()
        self.begin(label='second-review', current=guidance.next_steps(self.root)['active']['checkpoint'],
                   observation=self.base / 'candidate.json', expected_parent=guidance.next_steps(self.root)['active']['id'])
        result = guidance.next_steps(self.root)
        self.assertEqual(ids(result), ['render', 'finish-edit'])
        self.assertIn('render "<saved result .blend>"', step(result, 'render')['command'])

    def test_cli_prints_next_steps(self):
        result = cli('next', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['schema'], 'dcc.next.v1')


class RequirementTests(Fixture):
    def test_unbound_project_fails_plainly(self):
        with self.assertRaisesRegex(ValueError, 'Bind an environment workflow first'):
            guidance.requirements(self.root, 'direction')

    def test_unknown_stage_fails_plainly(self):
        self.bind()
        with self.assertRaisesRegex(ValueError, 'Unknown workflow stage'):
            guidance.requirements(self.root, 'lighting')

    def test_ready_stage_lists_evidence_notes_and_a_skeleton_that_submits_once_filled(self):
        self.bind()
        note = self.add()
        result = guidance.requirements(self.root, 'direction')
        self.assertEqual(result['schema'], 'dcc.requirements.v1')
        self.assertEqual(result['state'], 'ready')
        self.assertEqual([e['kind'] for e in result['evidence']], ['direction_record'])
        self.assertEqual(result['feedback_ids'], [note])
        self.assertEqual(result['unresolved_blockers'], [note])
        self.assertEqual(result['expected_revision'], self.revision())
        skeleton = result['skeleton']
        self.assertEqual(skeleton['checkpoint'], self.cp())
        self.assertEqual(set(skeleton['deliverables']), {'brief'})
        self.assertEqual(skeleton['evidence'][0]['file'], {'path': '<direction record, relative to the evidence root>'})
        skeleton['evidence'][0]['file']['path'] = Path(self.handoff).relative_to(self.base).as_posix()
        skeleton['deliverables']['brief'] = 'Fixture description'
        skeleton['note'] = 'Direction ready for review'
        draft = self.base / 'stage.draft.json'
        draft.write_text(json.dumps(skeleton), encoding='utf-8')
        fill_hashes(draft, self.base / 'stage.json')
        submitted = self.apply('stage.submit', json.loads((self.base / 'stage.json').read_text(encoding='utf-8')))
        self.assertEqual(submitted['status'], 'COMMITTED')

    def test_blocked_stage_names_its_predecessors(self):
        self.bind()
        result = guidance.requirements(self.root, 'delivery')
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(result['blocked_by'], ['direction'])
        self.assertEqual(sorted(e['kind'] for e in result['evidence']),
                         ['feedback_reconciliation', 'handoff', 'native_contract', 'native_reopen'])

    def test_delivery_accounts_for_every_note(self):
        self.bind()
        first = self.add()
        second = self.add(stage_id=None)
        self.assertEqual(sorted(guidance.requirements(self.root, 'delivery')['feedback_ids']), sorted([first, second]))

    def test_cli_prints_requirements(self):
        self.bind()
        result = cli('requirements', self.root, 'direction')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['stage_id'], 'direction')


class BriefTests(Fixture):
    def test_brief_states_position_next_commands_and_fenced_records(self):
        text = guidance.brief(self.root)
        active = self.packet['active']
        self.assertIn(active['id'], text)
        self.assertIn('## What to do next', text)
        self.assertIn('begin-edit "' + str(self.root) + '" --parent ' + active['id'], text)
        self.assertIn('```text\nGarden\n```', text)
        self.assertIn('Keep the layout and inspect material response.', text)
        self.assertIn('"palette": "warm"', text)
        self.assertNotIn('## Feedback and stages', text)

    def test_brief_includes_open_notes_and_stages_when_coordinated(self):
        self.bind()
        self.add()
        text = guidance.brief(self.root)
        self.assertIn('## Feedback and stages', text)
        self.assertIn('Preserve the table dimensions', text)
        self.assertIn('| direction | ready |', text)

    def test_brief_details_each_open_note(self):
        self.bind()
        self.add(anchor={**self.cp(), 'instance_ids': ['ext.table.top'], 'render': {**self.render(), 'pin': {'x': .25, 'y': .5}}},
                 category='visual')
        text = guidance.brief(self.root)
        self.assertIn('Acceptance: Measured dimensions match the declared contract', text)
        self.assertIn('Targets: ext.table.top', text)
        self.assertIn('View: DETAIL, pin at x 0.25, y 0.5', text)
        self.assertIn('Needs: visual review', text)

    def test_brief_reports_rejected_edits_with_reasons(self):
        edit = self.begin()['edit']
        native, obs = self.candidate()
        from dcc_harness import workflow
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {}, reject_reason='Timber reads as plastic')
        self.assertIn('Timber reads as plastic', guidance.brief(self.root))

    def test_cli_prints_markdown_and_refuses_an_existing_out(self):
        out = self.base / 'BRIEF-out.md'
        result = cli('brief', self.root, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('# '))
        self.assertEqual(out.read_text(encoding='utf-8'), result.stdout.rstrip('\n') + '\n')
        again = cli('brief', self.root, '--out', out)
        self.assertEqual(again.returncode, 2)
        self.assertTrue(again.stdout.startswith('# '))
