"""Portable checks for the judge loop: code gates, the stall rule, the round cap, attribution and the CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coordination_helpers import Fixture
from dcc_harness import judge, workflow
from dcc_harness.evidence import digest, file_hash, read_json, write_json

SPEC = {'schema': 'dcc.blockout.v1', 'name': 'stool', 'units': 'metres', 'up': 'Z', 'parts': [
    {'name': 'seat', 'category': 'furniture', 'primitive': 'cylinder', 'position': [0, 0, 0.4], 'size': [0.35, 0.35, 0.04]}]}


class Loop:
    """A loop in a temporary folder, with synthetic evidence shaped like the real commands' output."""

    def __init__(self, folder, spec=False, pass_score=None, checkpoint=None):
        self.base, self.count, self.checkpoint = Path(folder), 0, checkpoint
        target = {'schema': 'dcc.judge.target.v1', 'brief': 'A three-legged stool on a paved patch, late afternoon.',
                  'targets': [{'id': 'worn-seat', 'intent': 'The seat reads as worn timber, not plastic.'}]}
        (self.base / 'mood.png').write_bytes(b'reference pixels')
        target['references'] = [{'id': 'mood', 'role': 'mood', 'intent': 'Warm low sun', 'file': {'path': 'mood.png'}}]
        if spec:
            write_json(self.base / 'spec.json', SPEC)
            target['spec'] = {'path': 'spec.json'}
        if pass_score is not None:
            target['pass_score'] = pass_score
        write_json(self.base / 'target.json', target)
        self.root = self.base / 'loop'
        self.started = judge.start(self.root, self.base / 'target.json')

    def evidence(self, approach='first build', audit_passed=True, spec_passed=True, **extra):
        self.count += 1
        folder = self.base / f'round{self.count}'
        (folder / 'views').mkdir(parents=True)
        (folder / 'sheet').mkdir()
        blend = self.checkpoint or folder / 'candidate.blend'
        if self.checkpoint is None:
            blend.write_bytes(f'blend {self.count}'.encode())
        sha = file_hash(blend)
        (folder / 'views' / 'hero.png').write_bytes(f'hero {self.count}'.encode())
        (folder / 'sheet' / 'sheet.png').write_bytes(f'sheet {self.count}'.encode())
        write_json(folder / 'views' / 'receipt.json', {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': sha, 'views_digest': 'd' * 64,
                                                       'images': {'hero': {'path': 'hero.png', 'sha256': file_hash(folder / 'views' / 'hero.png')}}})
        write_json(folder / 'sheet' / 'receipt.json', {'schema': 'dcc.review.sheet.v1', 'checkpoint_sha256': sha,
                                                       'image': {'path': 'sheet.png', 'sha256': file_hash(folder / 'sheet' / 'sheet.png')}})
        findings = [] if audit_passed else [{'code': 'NORMALS_INWARD', 'severity': 'error'}]
        write_json(folder / 'audit.json', {'schema': 'dcc.audit.report.v1', 'passed': audit_passed, 'findings': findings, 'source': {'sha256': sha}})
        document = {'schema': 'dcc.judge.evidence.v1', 'approach': approach, 'checkpoint': {'path': str(blend)}, 'audit': {'path': 'audit.json'},
                    'views': {'path': 'views/receipt.json'}, 'sheet': {'path': 'sheet/receipt.json'}, **extra}
        if (self.base / 'spec.json').exists():
            write_json(folder / 'compare.json', {'schema': 'dcc.blockout.report.v1', 'passed': spec_passed, 'spec_digest': digest(SPEC),
                                                 'findings': [] if spec_passed else [{'code': 'SIZE', 'path': 'parts/seat/size'}], 'source': {'sha256': sha}})
            document['spec_compare'] = {'path': 'compare.json'}
        write_json(folder / 'evidence.json', document)
        return folder / 'evidence.json'

    def round(self, **options):
        return judge.add_round(self.root, self.evidence(**options))

    def verdict(self, total, gaps=('seat-too-clean',), context='fresh'):
        scores, left = {}, total
        for key, most in judge.RUBRIC.items():
            scores[key] = min(most, left)
            left -= scores[key]
        self.verdicts = getattr(self, 'verdicts', 0) + 1
        path = self.base / f'verdict{self.verdicts}.json'
        write_json(path, {'schema': 'dcc.judge.verdict.v1', 'judge': {'author': 'judge-agent', 'context': context}, 'scores': scores,
                          'gaps': [{'id': g, 'where': 'hero view, seat', 'problem': 'no wear on the edges'} for g in gaps], 'summary': 'Synthetic verdict.'})
        return judge.add_verdict(self.root, path)

    def judged(self, total, gaps=('seat-too-clean',), **options):
        self.round(**options)
        return self.verdict(total, gaps)


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def loop(self, **options):
        return Loop(self.folder.name, **options)

    def test_a_new_loop_fixes_its_target_and_waits_for_a_build(self):
        loop = self.loop()
        self.assertEqual((loop.started['next'], loop.started['rounds_used'], loop.started['cap'], loop.started['pass_score']), ('build', 0, 5, 9))
        record = read_json(loop.root / 'loop.json')
        self.assertEqual(record['references'][0]['file']['sha256'], file_hash(loop.base / 'mood.png'))
        self.assertIn('not owner acceptance', record['attribution'])
        with self.assertRaises(FileExistsError):
            judge.start(loop.root, loop.base / 'target.json')

    def test_invalid_targets_are_refused(self):
        base = Path(self.folder.name)
        good = {'schema': 'dcc.judge.target.v1', 'brief': 'x', 'targets': [{'id': 'a', 'intent': 'b'}]}
        cases = {'schema': {**good, 'schema': 'v0'}, 'no targets': {**good, 'targets': []}, 'brief': {**good, 'brief': ' '},
                 'slug': {**good, 'targets': [{'id': 'A b', 'intent': 'x'}]}, 'pass': {**good, 'pass_score': 11}, 'extra': {**good, 'mode': 'fast'},
                 'missing reference': {**good, 'references': [{'id': 'r', 'role': 'mood', 'intent': 'x', 'file': {'path': 'absent.png'}}]}}
        for name, target in cases.items():
            write_json(base / f'{name}.json', target)
            with self.subTest(name), self.assertRaises(ValueError):
                judge.start(base / f'loop-{name}', base / f'{name}.json')

    def test_a_round_with_an_audit_error_is_gated_and_never_judged(self):
        loop = self.loop()
        result = loop.round(audit_passed=False)
        self.assertEqual((result['status'], result['passed'], result['next']), ('gated', False, 'fix_gates'))
        self.assertIn('NORMALS_INWARD', result['gate_failures'][0])
        self.assertNotIn('packet', result)
        self.assertEqual(list((loop.root / 'packets').iterdir()), [])
        with self.assertRaisesRegex(ValueError, 'No round is waiting'):
            loop.verdict(5)
        self.assertEqual(loop.round()['status'], 'awaiting_verdict')

    def test_a_failed_spec_compare_gates_the_round_when_the_target_has_a_spec(self):
        loop = self.loop(spec=True)
        result = loop.round(spec_passed=False)
        self.assertEqual(result['status'], 'gated')
        self.assertIn('SIZE parts/seat/size', result['gate_failures'][0])
        document = read_json(loop.evidence())
        document.pop('spec_compare')
        write_json(loop.base / 'no-compare.json', document)
        with self.assertRaises(ValueError):
            judge.add_round(loop.root, loop.base / 'no-compare.json')

    def test_evidence_must_belong_to_the_candidate_and_be_unchanged(self):
        loop = self.loop()
        path = loop.evidence()
        report = path.parent / 'audit.json'
        report.write_text(json.dumps({**read_json(report), 'source': {'sha256': 'f' * 64}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'another file'):
            judge.add_round(loop.root, path)
        path = loop.evidence()
        (path.parent / 'views' / 'hero.png').write_bytes(b'edited after the receipt')
        with self.assertRaisesRegex(ValueError, 'changed after its receipt'):
            judge.add_round(loop.root, path)
        self.assertEqual(judge.status(loop.root)['rounds_used'], 0)

    def test_the_packet_carries_the_target_images_rubric_and_previous_verdict(self):
        loop = self.loop()
        first = loop.round()
        packet = read_json(first['packet'])
        self.assertEqual((packet['previous'], set(packet['images']), packet['references'][0]['id']), (None, {'hero', 'sheet'}, 'mood'))
        self.assertEqual(set(packet['rubric']), set(judge.RUBRIC))
        loop.verdict(4)
        with self.assertRaisesRegex(ValueError, 'No round is waiting'):
            loop.verdict(4)
        second = read_json(loop.round()['packet'])
        self.assertEqual((second['previous']['total'], second['previous']['gaps'][0]['id']), (4, 'seat-too-clean'))
        with self.assertRaisesRegex(ValueError, 'still needs its verdict'):
            loop.round()

    def test_steady_gains_with_new_gaps_continue(self):
        loop = self.loop()
        self.assertEqual(loop.judged(3, ['flat-light'])['next'], 'continue')
        self.assertEqual(loop.judged(5, ['seat-too-clean'])['next'], 'continue')
        self.assertEqual(loop.judged(7, ['no-ground-contact'])['next'], 'continue')

    def test_a_repeated_gap_while_the_score_rises_is_not_a_stall(self):
        loop = self.loop()
        loop.judged(4)
        self.assertEqual(loop.judged(7)['next'], 'continue')                  # same gap, three points gained
        self.assertEqual(loop.judged(8)['next'], 'continue')

    def test_the_same_gap_named_twice_without_a_point_gained_forces_a_change_of_approach(self):
        loop = self.loop()
        loop.judged(3)
        stalled = loop.judged(3)
        self.assertEqual((stalled['next'], stalled['stopped']), ('change_approach', False))
        self.assertIn('seat-too-clean', stalled['reason'])
        with self.assertRaisesRegex(ValueError, 'different approach'):
            loop.round(approach='first build')
        with self.assertRaisesRegex(ValueError, 'different approach'):
            loop.round(approach='procedural wear mask')                       # no changed_approach statement
        self.assertEqual(judge.status(loop.root)['rounds_used'], 2)
        loop.round(approach='procedural wear mask', changed_approach='Replaced the hand-set roughness with an edge-wear mask.')
        self.assertEqual(loop.verdict(7, ['seat-too-clean'])['next'], 'continue')   # it gained two points, so the loop goes on

    def test_less_than_one_point_across_two_rounds_forces_a_change_of_approach(self):
        loop = self.loop()
        loop.judged(4, ['a'])
        self.assertEqual(loop.judged(4, ['b'])['next'], 'continue')
        flat = loop.judged(4, ['c'])
        self.assertEqual(flat['next'], 'change_approach')
        self.assertIn('0 points gained across rounds 1 to 3', flat['reason'])

    def test_a_changed_approach_that_gains_nothing_stops_and_asks(self):
        loop = self.loop()
        loop.judged(4)
        loop.judged(4)
        loop.round(approach='rebuilt from a blockout', changed_approach='Started again from the blockout.')
        stopped = loop.verdict(4, ['other'])
        self.assertEqual((stopped['next'], stopped['stopped']), ('stop_ask', True))
        with self.assertRaisesRegex(ValueError, 'stopped'):
            loop.round()

    def test_a_second_stall_after_a_successful_change_stops_and_asks(self):
        loop = self.loop()
        loop.judged(2)
        loop.judged(2)                                                         # same gap twice, nothing gained
        loop.round(approach='new materials', changed_approach='New material graph.')
        self.assertEqual(loop.verdict(5, ['x'])['next'], 'continue')
        self.assertEqual(loop.judged(5, ['x'])['next'], 'stop_ask')

    def test_a_gated_round_does_not_clear_a_required_change_of_approach(self):
        loop = self.loop()
        loop.judged(3)
        loop.judged(3)
        gated = loop.round(approach='new approach', changed_approach='Rebuilt the seat.', audit_passed=False)
        self.assertEqual((gated['status'], gated['next']), ('gated', 'change_approach'))
        with self.assertRaisesRegex(ValueError, 'different approach'):
            loop.round(approach='new approach')

    def test_the_loop_stops_at_five_rounds(self):
        loop = self.loop()
        for total, gap in ((1, 'a'), (3, 'b'), (5, 'c'), (7, 'd')):
            self.assertEqual(loop.judged(total, [gap])['next'], 'continue')
        last = loop.judged(8, ['e'])
        self.assertEqual((last['next'], last['stopped']), ('stop_cap', True))
        with self.assertRaisesRegex(ValueError, 'stopped'):
            loop.round()

    def test_gated_rounds_count_toward_the_cap(self):
        loop = self.loop()
        for _ in range(4):
            self.assertEqual(loop.round(audit_passed=False)['next'], 'fix_gates')
        self.assertEqual(loop.round(audit_passed=False)['next'], 'stop_cap')

    def test_reaching_the_pass_score_stops_without_claiming_acceptance(self):
        loop = self.loop(pass_score=7)
        loop.judged(5, ['a'])
        met = loop.judged(7, ['b'])
        self.assertEqual((met['next'], met['stopped']), ('stop_target_met', True))
        self.assertIn('not owner acceptance', met['attribution'])
        self.assertIn('not acceptance', met['instruction'])

    def test_verdicts_are_validated_and_record_who_judged(self):
        loop = self.loop()
        loop.round()
        good = {'schema': 'dcc.judge.verdict.v1', 'judge': {'author': 'j', 'context': 'fresh'},
                'scores': {'composition': 2, 'lighting': 2, 'materials': 1, 'detail': 0}, 'gaps': [{'id': 'g', 'where': 'w', 'problem': 'p'}], 'summary': 's'}
        cases = {'range': {**good, 'scores': {**good['scores'], 'detail': 2}}, 'fraction': {**good, 'scores': {**good['scores'], 'lighting': 1.5}},
                 'missing line': {**good, 'scores': {'composition': 2}}, 'no gaps below full': {**good, 'gaps': []},
                 'duplicate gap': {**good, 'gaps': good['gaps'] * 2}, 'context': {**good, 'judge': {'author': 'j', 'context': 'owner'}},
                 'gap id': {**good, 'gaps': [{'id': 'Too Clean', 'where': 'w', 'problem': 'p'}]}}
        for name, verdict in cases.items():
            write_json(loop.base / f'bad-{name}.json', verdict)
            with self.subTest(name), self.assertRaises(ValueError):
                judge.add_verdict(loop.root, loop.base / f'bad-{name}.json')
        write_json(loop.base / 'same.json', {**good, 'judge': {'author': 'builder', 'context': 'same'}})
        self.assertEqual(judge.add_verdict(loop.root, loop.base / 'same.json')['judge_context'], 'same')

    def test_status_alone_is_enough_to_resume(self):
        loop = self.loop()
        loop.judged(3, ['flat-light', 'seat-too-clean'])
        loop.round(approach='warmer key light')
        state = judge.status(loop.root)
        self.assertEqual((state['next'], state['rounds_used'], state['rounds'][0]['score'], state['rounds'][1]['status']), ('judge', 2, 3, 'awaiting_verdict'))
        self.assertEqual([g['id'] for g in state['open_gaps']], ['flat-light', 'seat-too-clean'])
        self.assertTrue(state['brief'] and state['targets'] and state['instruction'])
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'judge-status', str(loop.root)], capture_output=True, text=True)
        self.assertEqual(json.loads(proc.stdout)['next'], 'judge')

    def test_a_gated_round_exits_nonzero_from_the_cli(self):
        loop = self.loop()
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'judge-round', str(loop.root), '--evidence', str(loop.evidence(audit_passed=False))],
                              capture_output=True, text=True)
        self.assertEqual((proc.returncode, json.loads(proc.stdout)['status']), (1, 'gated'))


class FeedbackNoteTests(Fixture):
    def test_gaps_become_feedback_note_drafts_the_project_accepts(self):
        active = workflow.resume(self.root)['active']
        (self.base / 'judge-work').mkdir()
        loop = Loop(self.base / 'judge-work', checkpoint=Path(active['checkpoint']))
        loop.round(project_checkpoint=self.cp())
        result = loop.verdict(4, ['flat-light', 'seat-too-clean'])
        self.assertEqual(len(result['feedback_notes']), 2)
        draft = read_json(result['feedback_notes'][0])
        self.assertEqual((draft['category'], draft['priority'], draft['source']['role']), ('visual', 'advisory', 'agent'))
        self.assertIn('not owner acceptance', draft['source']['reference'])
        note = self.apply('feedback.add', draft)['result']['note']
        self.assertEqual(note['text'], 'hero view, seat: no wear on the edges')

    def test_without_a_project_checkpoint_no_drafts_are_written(self):
        (self.base / 'plain').mkdir()
        loop = Loop(self.base / 'plain')
        self.assertEqual(loop.judged(4)['feedback_notes'], [])


if __name__ == '__main__':
    unittest.main()
