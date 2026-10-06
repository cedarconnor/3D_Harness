import copy
import json
from pathlib import Path
import subprocess
import sys

from coordination_helpers import Fixture
from dcc_harness import workflow, coordination as c
from dcc_harness.evidence import write_json, digest


class FeedbackTests(Fixture):
    def test_response_does_not_resolve_until_recomputed_verification(self):
        nid = self.add(); response = self.respond(nid)
        packet = workflow.resume(self.root)['coordination']
        self.assertEqual(packet['notes'][0]['status'], 'awaiting_verification')
        self.assertEqual(packet['unresolved_blockers'], [nid])
        result = self.verify(nid, response)
        self.assertTrue(result['result']['passed'])
        self.assertEqual(result['result']['artistic_acceptance'], 'not_evaluated')
        self.assertEqual(workflow.resume(self.root)['coordination']['unresolved_blockers'], [])

    def test_partial_multiple_rounds_and_stale_response(self):
        nid = self.add(); first = self.respond(nid, disposition='partial')
        with self.assertRaisesRegex(ValueError, 'Partial'):
            self.verify(nid, first)
        second = self.respond(nid)
        with self.assertRaisesRegex(ValueError, 'Stale feedback'):
            self.verify(nid, first)
        self.verify(nid, second)
        self.assertEqual(len(c.read(self.root)), 4)

    def test_changed_checkpoint_requires_recheck(self):
        nid = self.add(); self.verify(nid, self.respond(nid))
        edit = self.begin(); native, obs = self.candidate()
        workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {})
        self.assertEqual(workflow.resume(self.root)['coordination']['notes'][0]['current_validity'], 'needs_recheck')

    def test_wrong_checkpoint_target_or_pin_rejected(self):
        for anchor in ({**self.cp(), 'instance_ids': ['missing']}, {**self.cp(), 'checkpoint_id': '0'*64},
                       {**self.cp(), 'render': {**self.render(), 'pin': {'x': 2, 'y': .5}}}):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                self.add(anchor=anchor)

    def test_visual_verification_requires_bound_original_view(self):
        render = self.render()
        nid = self.add(category='visual', anchor={**self.cp(), 'render': render})
        response = self.respond(nid, evidence=[{'kind': 'detail_render', 'render': render}])
        with self.assertRaisesRegex(ValueError, 'bound views'):
            self.verify(nid, response)
        result = self.verify(nid, response, views=['DETAIL'])
        self.assertTrue(result['result']['passed'])

    def test_old_render_on_new_checkpoint_rejected(self):
        render = self.render()
        nid = self.add(category='visual')
        edit = self.begin(); native, obs = self.candidate()
        workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {})
        with self.assertRaisesRegex(ValueError, 'Stale or invalid render'):
            self.respond(nid, evidence=[{'kind': 'detail_render', 'render': render}])

    def test_same_view_name_with_different_camera_digest_rejected(self):
        original = self.render()
        nid = self.add(category='visual', anchor={**self.cp(), 'render': original})
        changed = self.render()
        path = self.base / changed['receipt']['path']
        settings = self.base / changed['settings']['path']
        values = json.loads(settings.read_text()); values['frame'] = 2
        settings.write_text(json.dumps(values)); changed['settings'] = self.ref(settings)
        payload = json.loads(path.read_text()); payload['views_digest'] = digest(values)
        path.write_text(json.dumps(payload))
        changed['receipt'] = self.ref(path)
        response = self.respond(nid, evidence=[{'kind': 'detail_render', 'render': changed}])
        with self.assertRaisesRegex(ValueError, 'view settings changed'):
            self.verify(nid, response, views=['DETAIL'])

    def test_view_definitions_must_be_retained_and_match_the_digest(self):
        render = self.render()
        missing = {k: v for k, v in render.items() if k != 'settings'}
        with self.assertRaisesRegex(ValueError, 'Missing or unknown'):
            self.add(category='visual', anchor={**self.cp(), 'render': missing})
        path = self.base / render['settings']['path']
        path.write_text('{"camera":"changed"}')
        render['settings'] = self.ref(path)
        with self.assertRaisesRegex(ValueError, 'settings'):
            self.add(category='visual', anchor={**self.cp(), 'render': render})

    def test_mixed_note_cannot_resolve_without_native_contract(self):
        nid = self.add(category='visual', requires=['technical', 'visual'])
        response = self.respond(nid, evidence=[{'kind': 'detail_render', 'render': self.render()}])
        with self.assertRaisesRegex(ValueError, 'native contract'):
            self.verify(nid, response, views=['DETAIL'])

    def test_failing_contract_does_not_close_note(self):
        nid = self.add()
        rules = json.loads(self.contract.read_text())
        rules['spec']['required']['ext.table.top']['dimensions'] = [99, 99, 99]
        path = self.base / 'wrong.json'; write_json(path, rules)
        response = self.respond(nid, evidence=[{'kind': 'native_contract', 'before': self.cp(), 'contract': self.ref(path)}])
        self.assertFalse(self.verify(nid, response)['result']['passed'])
        self.assertEqual(workflow.resume(self.root)['coordination']['unresolved_blockers'], [nid])

    def test_artist_required_and_builder_waiver_rejected(self):
        nid = self.add(review_policy='artist_required'); response = self.respond(nid)
        with self.assertRaisesRegex(ValueError, 'Artist review'):
            self.verify(nid, response)
        decision = {'schema': 'dcc.feedback.decision.v1', 'note_id': nid, 'action': 'deferred',
                    'reason': 'Cannot finish', 'authority': self.actor(), 'result': self.cp()}
        with self.assertRaisesRegex(ValueError, 'artist decision'):
            self.apply('feedback.decide', decision)

    def test_all_notes_visible_to_fresh_process(self):
        ids = [self.add(text=f'Note {i}') for i in range(8)]
        result = subprocess.run([sys.executable, '-m', 'dcc_harness', 'resume', str(self.root)], capture_output=True, text=True, check=True)
        packet = json.loads(result.stdout)['coordination']
        self.assertEqual(packet['unresolved_blockers'], ids)
        self.assertEqual(packet['total_notes'], 8)
