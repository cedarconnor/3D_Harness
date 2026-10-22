"""Portable checks for the before/after review page and importing what the reviewer exports."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid
from unittest import mock

from coordination_helpers import Console, Fixture
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

    def test_every_changed_scene_field_is_listed(self):
        before = observation()
        after = copy.deepcopy(before)
        after['scene']['camera'] = 'ext.camera.new'
        after['scene']['render']['samples'] = 128
        after['scene']['world'] = {'nodes': [], 'links': []}
        self.assertEqual(review_page.changes(resign(before), resign(after))['scene'], ['camera', 'render', 'world'])


class PageFixture(Fixture):
    def publish(self):
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {})
        history = Continuity(self.root).status()['task_history']
        return history[0], history[1]

    def publish_again(self, parent):
        """A third checkpoint after `parent`, with the same observed content."""
        edit = self.begin(expected_parent=parent['id'], current=parent['checkpoint'], observation=parent['observation'], label='third')['edit']
        native = self.base / 'third.blend'
        native.write_bytes(b'third synthetic native')
        obs = read_json(parent['observation'])
        obs['checkpoint_sha256'] = file_hash(native)
        path = self.base / 'third.json'
        write_json(path, obs)
        return workflow.finish_edit(self.root, edit, native, path, self.handoff, {})['active']


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

    def test_image_paths_outside_the_render_folder_are_refused_before_writing(self):
        before, after = self.publish()
        outside = self.base / 'victim.txt'
        outside.write_text('original', encoding='utf-8')
        source = views(self.base / 'nested/a/views', after['checkpoint_sha256'])
        (self.base / 'nested/victim.txt').write_text('replacement', encoding='utf-8')
        receipt = read_json(source / 'receipt.json')
        for path in ('../../victim.txt', 'C:/victim.txt', '/victim.txt', 'sub\\..\\..\\victim.txt', 'receipt.json'):
            receipt['images']['WHOLE'] = {'path': path, 'sha256': file_hash(self.base / 'nested/victim.txt')}
            (source / 'receipt.json').unlink()
            write_json(source / 'receipt.json', receipt)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'contained relative path|collides'):
                review_page.build(self.root, self.base / 'page', before_views=views(self.base / f'b-{len(path)}', before['checkpoint_sha256']),
                                  after_views=source)
            self.assertFalse((self.base / 'page').exists())
        self.assertEqual(outside.read_text(encoding='utf-8'), 'original')

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
    def test_invalid_last_note_commits_nothing_and_corrected_export_succeeds(self):
        result, after, submitted = self.page_with_submission()
        review = {'reviewer': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'},
                  'verdict': 'pass', 'finding': 'Direction reads well', 'answers': {'path': 'Gravel'}}
        good, bad = self.note(after), self.note(after, 'Second note')
        bad['anchor']['instance_ids'] = ['typo.unknown']
        before = len(c.read(self.root))
        for notes in ([bad], [good, bad]):
            with self.assertRaises(ValueError):
                review_page.import_review(self.root, self.bundle(result, after, review, notes), self.base / 'page', Console())
            self.assertEqual(len(c.read(self.root)), before)
        bad['anchor']['instance_ids'] = ['ext.table.top']
        outcome = review_page.import_review(self.root, self.bundle(result, after, review, [good, bad]), self.base / 'page', Console())
        self.assertEqual([r['status'] for r in outcome['results']], ['COMMITTED'] * 3)

    def test_interruption_after_approval_recovers_without_reapproving(self):
        result, after, submitted = self.page_with_submission()
        review = {'reviewer': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'},
                  'verdict': 'pass', 'finding': 'Direction reads well', 'answers': {'path': 'Gravel'}}
        bundle = self.bundle(result, after, review, [self.note(after)])
        with mock.patch('dcc_harness.feedback.apply', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                review_page.import_review(self.root, bundle, self.base / 'page', Console())
        # Correcting a not-yet-committed note must not change approval identity.
        bundle = self.bundle(result, after, review, [self.note(after, 'Corrected note')])
        outcome = review_page.import_review(self.root, bundle, self.base / 'page')
        self.assertEqual([r['status'] for r in outcome['results']], ['ALREADY_COMMITTED', 'COMMITTED'])

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
        first = review_page.import_review(self.root, bundle, self.base / 'page', Console())
        self.assertEqual([r['status'] for r in first['results']], ['COMMITTED', 'COMMITTED'])
        self.assertEqual(first['results'][0]['kind'], 'stage.complete')
        self.assertEqual(c.read(self.root)[-2]['result']['owner_approval']['channel'], 'owner_terminal')
        events = c.read(self.root)
        self.assertEqual(events[-2]['result']['answers'][1], {'id': 'path', 'text': QUESTIONS[1]['text'], 'answer': 'Gravel', 'used_default': False})
        again = review_page.import_review(self.root, bundle, self.base / 'page')
        self.assertEqual([r['status'] for r in again['results']], ['ALREADY_COMMITTED', 'ALREADY_COMMITTED'])
        self.assertEqual(len(c.read(self.root)), len(events))

    def test_an_approval_from_an_agent_session_imports_nothing(self):
        result, after, submitted = self.page_with_submission()
        review = {'reviewer': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'}, 'verdict': 'pass', 'finding': 'Fine', 'answers': {'path': 'Gravel'}}
        bundle = self.bundle(result, after, review, [self.note(after)])
        before = len(c.read(self.root))
        with self.assertRaisesRegex(RuntimeError, 'agent session'):
            review_page.import_review(self.root, bundle, self.base / 'page', Console(environ={'CLAUDECODE': '1'}))
        self.assertEqual(len(c.read(self.root)), before)
        imported = subprocess.run([sys.executable, '-m', 'dcc_harness', 'review-import', str(self.root), str(bundle), '--page', str(self.base / 'page')],
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL, env={**__import__('os').environ, 'CLAUDECODE': '1'})
        self.assertNotEqual(imported.returncode, 0)
        self.assertIn('agent session', imported.stderr)
        self.assertEqual(len(c.read(self.root)), before)
        notes_only = self.bundle(result, after, None, [self.note(after)])
        self.assertEqual([r['status'] for r in review_page.import_review(self.root, notes_only, self.base / 'page')['results']], ['COMMITTED'])

    def test_a_page_for_an_earlier_checkpoint_offers_no_approval(self):
        self.bind()
        first, second = self.publish()
        third = self.publish_again(second)
        submitted = self.submit()
        result = review_page.build(self.root, self.base / 'page', from_id=first['id'], to_id=second['id'],
                                   before_views=views(self.base / 'b', first['checkpoint_sha256']),
                                   after_views=views(self.base / 'a', second['checkpoint_sha256']))
        self.assertIsNone(read_json(self.base / 'page/page.json')['submission'])
        self.assertEqual(result['submissions_not_shown'], [{'stage_id': 'direction', 'checkpoint_id': third['id']}])
        review = {'reviewer': {'role': 'artist', 'author': 'Reviewer', 'reference': 'Review page'}, 'verdict': 'pass', 'finding': 'Looks right'}
        with self.assertRaisesRegex(ValueError, 'no stage submission'):
            review_page.import_review(self.root, self.bundle(result, second, review), self.base / 'page', Console())
        # A page edited to carry the newer submission is still refused at import.
        data = read_json(self.base / 'page/page.json')
        data['submission'] = {'id': submitted['revision'], 'stage_id': 'direction', 'checkpoint': c.checkpoint_ref(third)}
        (self.base / 'page/page.json').unlink()
        write_json(self.base / 'page/page.json', data)
        before = len(c.read(self.root))
        with self.assertRaisesRegex(ValueError, 'not for the checkpoint this page shows'):
            review_page.import_review(self.root, self.bundle({'page_digest': digest(data)}, second, review), self.base / 'page', Console())
        self.assertEqual(len(c.read(self.root)), before)

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
