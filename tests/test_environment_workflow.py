import copy
from pathlib import Path
import tempfile
import unittest

from coordination_helpers import Fixture
from dcc_harness import environment_workflow as ew, workflow, coordination as c


class RuntimeStampTests(unittest.TestCase):
    def test_source_digest_ignores_checkout_line_endings_but_not_content(self):
        with tempfile.TemporaryDirectory() as temp:
            sources = {'lf': b'x = 1\ny = 2\n', 'crlf': b'x = 1\r\ny = 2\r\n', 'changed': b'x = 1\ny = 3\n'}
            for name, data in sources.items():
                (Path(temp) / name).mkdir()
                (Path(temp) / name / 'module.py').write_bytes(data)
            digests = {name: ew.runtime_stamp(Path(temp) / name)['source_digest'] for name in sources}
        self.assertEqual(digests['lf'], digests['crlf'])
        self.assertNotEqual(digests['lf'], digests['changed'])

    def test_experiment_tooling_is_outside_the_runtime_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'core.py').write_text('x = 1\n'); (root / 'blind.py').write_text('y = 1\n')
            first = ew.runtime_stamp(root)['source_digest']
            (root / 'blind.py').write_text('y = 2\n')
            self.assertEqual(ew.runtime_stamp(root)['source_digest'], first)
            (root / 'core.py').write_text('x = 2\n')
            self.assertNotEqual(ew.runtime_stamp(root)['source_digest'], first)

    def test_the_pinned_runtime_never_imports_experiment_tooling(self):
        import ast
        package = Path(ew.__file__).parent
        experiments = {name[:-3] for name in ew.EXPERIMENT_TOOLING}
        for path in sorted(package.glob('*.py')):
            if path.name in ew.EXPERIMENT_TOOLING:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.ImportFrom):
                    names = [node.module or ''] + [a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                else:
                    continue
                with self.subTest(module=path.name):
                    self.assertFalse({n.split('.')[-1] for n in names} & experiments, names)


class EnvironmentWorkflowTests(Fixture):
    def test_packaged_manifest_and_pin_is_independent_of_source(self):
        ew.validate_manifest(ew.default_manifest())
        binding = self.bind()
        path = self.base / 'skills/dcc-plan-environment/SKILL.md'
        path.write_text('changed source skill')
        packet = workflow.resume(self.root)['coordination']['workflow']
        pinned = c.read(self.root)[0]['result']['binding']['skill_files']['dcc-plan-environment'][0]
        self.assertNotEqual(path.read_text(), (c.relative(packet['pinned_files_root'], pinned['path'])).read_text())
        self.assertTrue(packet['runtime_compatible'])

    def test_unknown_evidence_cycle_and_disconnected_stage_reject(self):
        for mutation in ('cycle', 'evidence', 'disconnected'):
            m = self.manifest()
            if mutation == 'cycle': m['stages'][0]['after'] = ['delivery']
            if mutation == 'evidence': m['stages'][0]['evidence'] = ['magic_beauty_score']
            if mutation == 'disconnected': m['stages'][1]['after'] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.bind(manifest=m)

    def test_stage_completes_and_new_note_reopens_it(self):
        self.bind(); submitted = self.submit(); self.complete(submitted)
        self.assertEqual(ew.stages(c.read(self.root))['direction']['state'], 'complete')
        self.add()
        states = ew.stages(c.read(self.root))
        self.assertEqual(states['direction']['state'], 'needs_review')
        self.assertEqual(states['delivery']['state'], 'blocked')

    def test_reopening_a_global_note_reopens_delivery(self):
        self.bind(); nid = self.add(stage_id=None); self.verify(nid, self.respond(nid)); self.complete(self.submit())
        self.complete(self.submit(stage_id='delivery', deliverables={'native': 'Deliver'}, evidence=[
            {'kind': 'native_reopen', 'observation': self.ref(self.obs_path), 'producer': self.actor()},
            {'kind': 'native_contract', 'before': self.cp(), 'contract': self.ref(self.contract)},
            {'kind': 'feedback_reconciliation'}, {'kind': 'handoff', 'file': self.ref(self.handoff)}]))
        self.assertEqual(ew.stages(c.read(self.root))['delivery']['state'], 'complete')
        self.apply('feedback.decide', {'schema': 'dcc.feedback.decision.v1', 'note_id': nid, 'action': 'reopen',
                                       'reason': 'The issue returned', 'authority': self.actor(), 'result': self.cp()})
        states = ew.stages(c.read(self.root))
        self.assertEqual((states['direction']['state'], states['delivery']['state']), ('complete', 'needs_review'))

    def test_artifact_names_reaching_one_file_are_refused_before_writing(self):
        self.bind()
        ref = self.ref(self.handoff)
        alias = {**ref, 'path': ref['path'].swapcase()}
        with self.assertRaisesRegex(ValueError, 'same file differently'):
            self.submit(evidence=[{'kind': 'direction_record', 'file': ref}, {'kind': 'handoff', 'file': alias}])
        self.assertEqual(len(c.read(self.root)), 1)
        workflow.resume(self.root)

    def test_omitted_note_and_unverified_response_block_completion(self):
        self.bind(); nid = self.add()
        with self.assertRaisesRegex(ValueError, 'every applicable'):
            self.submit(feedback_ids=[])
        submitted = self.submit()
        with self.assertRaisesRegex(ValueError, 'unresolved feedback'):
            self.complete(submitted)
        self.verify(nid, self.respond(nid))
        self.complete(self.submit())

    def test_new_feedback_invalidates_pending_submission(self):
        self.bind(); submitted = self.submit()
        self.add(priority='advisory')
        with self.assertRaisesRegex(ValueError, 'Stale submission'):
            self.complete(submitted)

    def test_pending_native_prevents_stage_completion(self):
        self.bind(); submitted = self.submit(); self.begin()
        with self.assertRaisesRegex(RuntimeError, 'Unresolved native'):
            self.complete(submitted)

    def test_stage_policy_requires_artist_and_missing_evidence_blocks(self):
        self.bind(review_policies={'direction': 'artist_required'})
        submitted = self.submit()
        with self.assertRaisesRegex(ValueError, 'Artist review'):
            self.complete(submitted)
        self.complete(submitted, reviewer=self.actor('artist'), owner=True)

    def test_missing_stage_evidence_can_be_submitted_but_not_completed(self):
        self.bind(); submitted = self.submit(evidence=[])
        self.assertEqual(submitted['result']['missing_evidence'], ['direction_record'])
        with self.assertRaisesRegex(ValueError, 'missing evidence'):
            self.complete(submitted)

    def test_inheritance_has_explicit_gaps_and_no_fictional_completion(self):
        self.bind(inherited={'direction': {'reason': 'Existing project', 'gaps': ['No style reference'], 'evidence': [{'kind': 'direction_record', 'file': self.ref(self.handoff)}]}})
        states = ew.stages(c.read(self.root))
        self.assertEqual(states['direction']['state'], 'inherited')
        self.assertEqual(states['direction']['inherited_gaps'], ['No style reference'])
        self.assertEqual(states['delivery']['state'], 'ready')

    def test_inheritance_cannot_hide_missing_stage_evidence(self):
        self.bind(inherited={'direction': {'reason': 'Existing project', 'gaps': [], 'evidence': [{'kind': 'handoff', 'file': self.ref(self.handoff)}]}})
        self.assertEqual(ew.stages(c.read(self.root))['direction']['inherited_gaps'], ['Missing direction_record'])
