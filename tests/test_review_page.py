"""Portable checks for the before/after review page and importing what the reviewer exports."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import coordination as c, review_page, workflow
from dcc_harness.continuity import Continuity
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from test_continuity_checks import observation, resign
from test_questions import QUESTIONS


def views(root, checkpoint_sha, settings=None, missing_image=False):
    """A render folder as `render` writes it, bound to one checkpoint."""
    root.mkdir(parents=True)
    settings = settings or {'schema': 'dcc.review.render-settings.v1', 'definition': {'views': ['WHOLE', 'DETAIL']}}
    images = {}
    for view in ('WHOLE', 'DETAIL'):
        (root / f'{view}.png').write_bytes(b'synthetic ' + view.encode() + checkpoint_sha.encode())
        images[view] = {'path': f'{view}.png', 'sha256': file_hash(root / f'{view}.png')}
    if missing_image:
        (root / 'DETAIL.png').write_bytes(b'changed after the receipt')
    write_json(root / 'views.json', settings)
    write_json(root / 'receipt.json', {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': checkpoint_sha,
                                       'views_digest': digest(settings), 'images': images})
    return root


class ChangeTests(Fixture):
    def test_objects_are_classified_by_stable_id(self):
        before = observation()
        before['objects']['ext.chair'] = copy.deepcopy(before['objects']['ext.table.top'])
        before['objects']['ext.lamp'] = copy.deepcopy(before['objects']['ext.table.top'])
        after = copy.deepcopy(before)
        del after['objects']['ext.lamp']
        after['objects']['ext.rug'] = copy.deepcopy(before['objects']['ext.table.top'])
        after['objects']['ext.chair']['matrix_world'] = [[1, 0], [0, 2]]
        after['objects']['ext.chair']['bounds'] = [[2, -.5, 0], [4, .5, 1]]
        after['objects']['ext.table.top']['dimensions'] = [2.5, 1, 1]
        after['materials']['stone']['graph']['nodes'][0]['inputs']['Roughness'] = .8
        result = review_page.changes(resign(before), resign(after))
        self.assertEqual([o['id'] for o in result['added']], ['ext.rug'])
        self.assertEqual([o['id'] for o in result['removed']], ['ext.lamp'])
        self.assertEqual([(o['id'], o['distance']) for o in result['moved']], [('ext.chair', 3.0)])
        self.assertEqual([(o['id'], o['fields']) for o in result['changed']], [('ext.table.top', ['dimensions'])])
        self.assertEqual([(m['id'], m['change']) for m in result['materials']], [('stone', 'changed')])


class PageFixture(Fixture):
    def publish(self):
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {})
        history = Continuity(self.root).status()['task_history']
        return history[0], history[1]


class PageTests(PageFixture):
    def build(self, **kwargs):
        before, after = self.publish()
        kwargs.setdefault('before_views', views(self.base / 'before-views', before['checkpoint_sha256']))
        kwargs.setdefault('after_views', views(self.base / 'after-views', after['checkpoint_sha256']))
        return review_page.build(self.root, self.base / 'page', **kwargs), before, after

    def test_page_shows_changes_views_and_verification(self):
        result, before, after = self.build()
        page = (self.base / 'page/index.html').read_text(encoding='utf-8')
        data = read_json(self.base / 'page/page.json')
        self.assertEqual((data['from']['id'], data['to']['id']), (before['id'], after['id']))
        self.assertEqual([v['id'] for v in data['views']], ['DETAIL', 'WHOLE'])
        self.assertTrue(data['verification']['chain_verified'] and data['verification']['receipts_bound'])
        self.assertTrue(data['views_match'])
        self.assertEqual(data['verification']['reopened'], 'not run')
        self.assertTrue((self.base / 'page/renders/after/WHOLE.png').is_file())
        self.assertIn(result['page_digest'], page)
        self.assertEqual(result['page_digest'], digest(data))

    def test_receipt_for_another_checkpoint_is_refused(self):
        before, after = self.publish()
        with self.assertRaisesRegex(ValueError, 'not bound'):
            review_page.build(self.root, self.base / 'page', before_views=views(self.base / 'b', after['checkpoint_sha256']),
                              after_views=views(self.base / 'a', after['checkpoint_sha256']))

    def test_changed_image_is_refused(self):
        before, after = self.publish()
        with self.assertRaisesRegex(ValueError, 'changed'):
            review_page.build(self.root, self.base / 'page', before_views=views(self.base / 'b', before['checkpoint_sha256']),
                              after_views=views(self.base / 'a', after['checkpoint_sha256'], missing_image=True))

    def test_different_view_settings_are_flagged(self):
        before, after = self.publish()
        review_page.build(self.root, self.base / 'page', before_views=views(self.base / 'b', before['checkpoint_sha256']),
                          after_views=views(self.base / 'a', after['checkpoint_sha256'], settings={'camera': 'moved'}))
        self.assertFalse(read_json(self.base / 'page/page.json')['views_match'])

    def test_notes_and_a_pending_submission_with_questions_appear(self):
        self.bind()
        before, after = self.publish()
        note = self.add(anchor={**c.checkpoint_ref(after), 'instance_ids': ['ext.table.top']})
        submitted = self.submit(questions=QUESTIONS)
        review_page.build(self.root, self.base / 'page', before_views=views(self.base / 'b', before['checkpoint_sha256']),
                          after_views=views(self.base / 'a', after['checkpoint_sha256']))
        data = read_json(self.base / 'page/page.json')
        self.assertEqual([n['id'] for n in data['notes']], [note])
        self.assertEqual(data['notes'][0]['targets'], ['ext.table.top'])
        self.assertEqual(data['submission']['id'], submitted['revision'])
        self.assertEqual(data['submission']['questions'], QUESTIONS)

    def test_build_without_views_still_lists_changes(self):
        self.publish()
        result = review_page.build(self.root, self.base / 'page')
        self.assertEqual(read_json(self.base / 'page/page.json')['views'], [])
        self.assertTrue(result['page'].endswith('index.html'))

    def reopen(self, change=None):
        before, after = self.publish()
        stored = read_json(after['observation'])
        def fake(source, out, blender, expanded=False):
            fresh = copy.deepcopy(stored)
            if change:
                change(fresh)
            Path(out).mkdir(parents=True)
            write_json(Path(out) / 'observation.json', resign(fresh))
            return {'revision': fresh['revision'], 'issues': fresh['issues'], 'observation': str(Path(out) / 'observation.json')}
        with mock.patch('dcc_harness.observe.observe_file', side_effect=fake):
            review_page.build(self.root, self.base / 'page', blender='blender.exe', views=None, reopen=True,
                              before_views=views(self.base / 'b', before['checkpoint_sha256']),
                              after_views=views(self.base / 'a', after['checkpoint_sha256']))
        return read_json(self.base / 'page/page.json')['verification']['reopened']

    def test_reopen_reports_an_exact_match(self):
        self.assertEqual(self.reopen(), 'matches the stored observation exactly')

    def test_reopen_reports_a_measured_difference(self):
        def grow(obs):
            obs['objects']['ext.table.top']['dimensions'] = [9, 9, 9]
        self.assertTrue(self.reopen(grow).startswith('differs from the stored observation'))

    def test_one_checkpoint_needs_an_explicit_pair(self):
        with self.assertRaisesRegex(ValueError, 'two checkpoints'):
            review_page.build(self.root, self.base / 'page')


class ImportTests(PageFixture):
    def page_with_submission(self):
        self.bind()
        before, after = self.publish()
        submitted = self.submit(questions=QUESTIONS)
        result = review_page.build(self.root, self.base / 'page', before_views=views(self.base / 'b', before['checkpoint_sha256']),
                                   after_views=views(self.base / 'a', after['checkpoint_sha256']))
        return result, after, submitted

    def bundle(self, result, after, review=None, notes=()):
        value = {'schema': 'dcc.review.export.v1', 'page': result['page_digest'], 'review': review, 'notes': list(notes)}
        path = self.base / 'review-export.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def note(self, after, text='The bench reads too glossy'):
        return {'schema': 'dcc.feedback.note.v1', 'source': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'},
                'stage_id': None, 'category': 'visual', 'priority': 'advisory', 'text': text, 'acceptance': 'Matte timber',
                'anchor': {**c.checkpoint_ref(after), 'instance_ids': ['ext.table.top'],
                           'render': {'receipt': {'path': 'renders/after/receipt.json', 'sha256': file_hash(self.base / 'page/renders/after/receipt.json')},
                                      'settings': {'path': 'renders/after/views.json', 'sha256': file_hash(self.base / 'page/renders/after/views.json')},
                                      'view_id': 'WHOLE', 'pin': {'x': 0.4, 'y': 0.6}}}}

    def test_import_completes_the_stage_then_adds_notes_and_replays_safely(self):
        result, after, submitted = self.page_with_submission()
        review = {'reviewer': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'}, 'verdict': 'pass',
                  'finding': 'Direction reads well', 'answers': {'path': 'Gravel'}}
        bundle = self.bundle(result, after, review, [self.note(after)])
        first = review_page.import_review(self.root, bundle, self.base / 'page')
        self.assertEqual([r['status'] for r in first['results']], ['COMMITTED', 'COMMITTED'])
        self.assertEqual(first['results'][0]['kind'], 'stage.complete')
        events = c.read(self.root)
        self.assertEqual(events[-2]['result']['answers'][1], {'id': 'path', 'text': QUESTIONS[1]['text'], 'answer': 'Gravel', 'used_default': False})
        again = review_page.import_review(self.root, bundle, self.base / 'page')
        self.assertEqual([r['status'] for r in again['results']], ['ALREADY_COMMITTED', 'ALREADY_COMMITTED'])
        self.assertEqual(len(c.read(self.root)), len(events))

    def test_export_from_another_page_is_refused(self):
        result, after, submitted = self.page_with_submission()
        bundle = self.bundle({'page_digest': 'f' * 64}, after, None, [self.note(after)])
        with self.assertRaisesRegex(ValueError, 'another review page'):
            review_page.import_review(self.root, bundle, self.base / 'page')

    def test_cli_builds_and_imports(self):
        self.bind()
        before, after = self.publish()
        build = subprocess.run([sys.executable, '-m', 'dcc_harness', 'review-page', str(self.root), '--output-dir', str(self.base / 'page'),
                                '--before-views', str(views(self.base / 'b', before['checkpoint_sha256'])),
                                '--after-views', str(views(self.base / 'a', after['checkpoint_sha256']))], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        digest_ = json.loads(build.stdout)['page_digest']
        bundle = self.bundle({'page_digest': digest_}, after, None, [self.note(after)])
        imported = subprocess.run([sys.executable, '-m', 'dcc_harness', 'review-import', str(self.root), str(bundle), '--page', str(self.base / 'page')],
                                  capture_output=True, text=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(json.loads(imported.stdout)['results'][0]['kind'], 'feedback.add')
