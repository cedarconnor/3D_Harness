"""Portable checks for review views, the render command and its queue; native runs are qualified separately."""
import copy
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings
import weakref
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import render, workflow
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.payloads import fill_hashes

VIEWS = {'schema': 'dcc.review.views.v1',
         'render': {'engine': 'CYCLES', 'resolution': [64, 36], 'samples': 4, 'seed': 0},
         'views': [{'id': 'REVIEW_WHOLE', 'purpose': 'whole', 'camera': {'object_id': 'review.camera'}},
                   {'id': 'REVIEW_DETAIL', 'purpose': 'detail', 'camera': {'object_id': 'review.camera'},
                    'border': [0.2, 0.8, 0.1, 0.7]},
                   {'id': 'GARDEN', 'purpose': 'whole', 'camera': {'lens': 48, 'location': [1, -2, 3], 'target': [0, 0, 1]}}]}


def fake_worker(change_source=False, bad_digest=False):
    """Stand in for Blender: write images, settings and a receipt where the real worker would."""
    def run(blender, folder, worker, action, request):
        out = Path(request['out'])
        images = {}
        for view in request['definition']['views']:
            (out / (view['id'] + '.png')).write_bytes(b'synthetic image ' + view['id'].encode())
            images[view['id']] = {'path': view['id'] + '.png', 'sha256': file_hash(out / (view['id'] + '.png'))}
        settings = {'schema': 'dcc.review.render-settings.v1', 'definition': request['definition'], 'resolved': {'frame': 1}}
        write_json(out / 'views.json', settings)
        write_json(out / 'receipt.json', {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': request['source']['sha256'],
                                          'views_digest': 'f' * 64 if bad_digest else digest(settings), 'images': images})
        write_json(out / 'report.json', {'blender': 'synthetic', 'seconds': {}})
        if change_source:
            Path(request['source']['path']).write_bytes(b'changed during render')
    return run


class ViewDefinitionTests(unittest.TestCase):
    def test_valid_definition_passes(self):
        self.assertEqual(render.validate_views(copy.deepcopy(VIEWS)), VIEWS)

    def test_invalid_definitions_are_rejected(self):
        cases = {
            'schema': {**VIEWS, 'schema': 'dcc.review.views.v2'},
            'duplicate id': {**VIEWS, 'views': [VIEWS['views'][0], VIEWS['views'][0]]},
            'unsafe id': {**VIEWS, 'views': [{**VIEWS['views'][0], 'id': '../whole'}]},
            'purpose': {**VIEWS, 'views': [{**VIEWS['views'][0], 'purpose': 'hero'}]},
            'mixed camera': {**VIEWS, 'views': [{**VIEWS['views'][0], 'camera': {'object_id': 'a', 'lens': 50}}]},
            'missing target': {**VIEWS, 'views': [{**VIEWS['views'][2], 'camera': {'lens': 48, 'location': [1, 2, 3]}}]},
            'border order': {**VIEWS, 'views': [{**VIEWS['views'][1], 'border': [0.8, 0.2, 0.1, 0.7]}]},
            'border range': {**VIEWS, 'views': [{**VIEWS['views'][1], 'border': [0, 1.2, 0, 1]}]},
            'resolution': {**VIEWS, 'render': {**VIEWS['render'], 'resolution': [0, 36]}},
            'unknown render key': {**VIEWS, 'render': {**VIEWS['render'], 'denoise': True}},
            'no views': {**VIEWS, 'views': []},
            'engine name Blender 5.1 rejects': {**VIEWS, 'render': {**VIEWS['render'], 'engine': 'BLENDER_EEVEE_NEXT'}},
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                render.validate_views(copy.deepcopy(value))


class RenderCommandTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.source = self.base / 'scene.blend'
        self.source.write_bytes(b'synthetic saved native - not Blender qualification')
        self.views = self.base / 'views.json'
        write_json(self.views, VIEWS)
        patcher = mock.patch.dict(os.environ, {'DCC_HARNESS_RENDER_LOCK': str(self.base / 'render.lock')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_render(self, worker, **kwargs):
        with mock.patch.object(render, 'run_worker', side_effect=worker):
            return render.render_file(self.source, self.base / 'work' / 'after-views', 'blender.exe', views=kwargs.get('views', self.views),
                                      project=kwargs.get('project'))

    def test_render_returns_bound_receipt_and_evidence_entries(self):
        result = self.run_render(fake_worker())
        self.assertEqual(result['status'], 'RENDERED')
        self.assertTrue(result['source_unchanged'])
        receipt = read_json(result['receipt'])
        self.assertEqual(receipt['checkpoint_sha256'], file_hash(self.source))
        self.assertEqual(sorted(result['images']), ['GARDEN', 'REVIEW_DETAIL', 'REVIEW_WHOLE'])
        kinds = {e['render']['view_id']: e['kind'] for e in result['evidence']}
        self.assertEqual(kinds, {'REVIEW_WHOLE': 'whole_scene_render', 'REVIEW_DETAIL': 'detail_render', 'GARDEN': 'whole_scene_render'})
        self.assertEqual(result['evidence'][0]['render']['receipt'], {'path': 'after-views/receipt.json'})
        self.assertEqual(result['evidence_root'], str((self.base / 'work').resolve()))
        status = read_json(self.base / 'work/after-views/status.json')
        self.assertEqual(status['state'], 'done')
        self.assertLessEqual(status['started_at'], status['finished_at'])

    def test_source_change_fails_and_is_recorded(self):
        with self.assertRaisesRegex(RuntimeError, 'Source changed'):
            self.run_render(fake_worker(change_source=True))
        status = read_json(self.base / 'work/after-views/status.json')
        self.assertEqual(status['state'], 'failed')
        self.assertIn('Source changed', status['error'])

    def test_settings_digest_must_match_the_receipt(self):
        with self.assertRaisesRegex(RuntimeError, 'digest'):
            self.run_render(fake_worker(bad_digest=True))

    def test_existing_output_folder_is_refused_before_blender(self):
        (self.base / 'work/after-views').mkdir(parents=True)
        worker = mock.Mock()
        with self.assertRaises(FileExistsError):
            self.run_render(worker)
        worker.assert_not_called()

    def test_views_source_is_exactly_one_of_project_or_file(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_render(mock.Mock(), views=None)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_render(mock.Mock(), project=self.base / 'state')

    def test_non_blend_source_is_refused(self):
        other = self.base / 'scene.txt'
        other.write_text('not blender', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'saved .blend'):
            render.render_file(other, self.base / 'out', 'blender.exe', views=self.views)


class ProjectViewTests(Fixture):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(os.environ, {'DCC_HARNESS_RENDER_LOCK': str(self.base / 'render.lock')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_project_without_review_views_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'review_views'):
            render.render_file(self.native, self.base / 'out', 'blender.exe', project=self.root)

    def publish_views(self):
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {'review_views': VIEWS})
        return native

    def test_project_decision_supplies_the_definition(self):
        native = self.publish_views()
        seen = {}
        def worker(blender, folder, script, action, request):
            seen.update(request)
            fake_worker()(blender, folder, script, action, request)
        with mock.patch.object(render, 'run_worker', side_effect=worker):
            render.render_file(native, self.base / 'views-out', 'blender.exe', project=self.root)
        self.assertEqual(seen['definition'], VIEWS)

    def test_evidence_entries_commit_in_a_feedback_response(self):
        native = self.publish_views()
        note = self.add()
        with mock.patch.object(render, 'run_worker', side_effect=fake_worker()):
            result = render.render_file(native, self.base / 'after-views', 'blender.exe', project=self.root)
        draft = self.base / 'response.draft.json'
        write_json(draft, {'schema': 'dcc.feedback.response.v1', 'note_id': note, 'author': 'test-builder',
                           'disposition': 'implemented', 'change': 'Rendered the published views', 'result': self.cp(),
                           'evidence': [{'kind': 'native_contract', 'before': self.cp(), 'contract': {'path': 'contract.json'}},
                                        *result['evidence']]})
        fill_hashes(draft, self.base / 'response.json')
        committed = self.apply('feedback.respond', read_json(self.base / 'response.json'))
        self.assertEqual(committed['status'], 'COMMITTED')
        self.assertTrue(all(r['passed'] for r in committed['result']['reports']))


def chunk(kind, data):
    import struct
    import zlib
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


class PngTextTests(unittest.TestCase):
    def test_text_chunks_are_removed_and_image_chunks_kept_byte_for_byte(self):
        import struct
        import zlib
        header = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 0, 0, 0, 0))
        pixels = chunk(b'IDAT', zlib.compress(b'\x00\x7f'))
        texts = [chunk(b'tEXt', b'cycles.ViewLayer.render_time\x0000:00.22'), chunk(b'zTXt', b'Date\x00\x00' + zlib.compress(b'now')),
                 chunk(b'iTXt', b'File\x00\x00\x00\x00\x00C:/local/path')]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\n' + header + texts[0] + pixels + texts[1] + texts[2] + chunk(b'IEND', b''))
            render.strip_png_text(path)
            self.assertEqual(path.read_bytes(), b'\x89PNG\r\n\x1a\n' + header + pixels + chunk(b'IEND', b''))

    def test_non_png_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.png'
            path.write_bytes(b'not a png')
            with self.assertRaisesRegex(ValueError, 'PNG'):
                render.strip_png_text(path)


class QueueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        patcher = mock.patch.dict(os.environ, {'DCC_HARNESS_RENDER_LOCK': str(self.base / 'render.lock')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_lock_admits_one_job_at_a_time(self):
        events = []
        def job(name):
            with render.render_lock():
                events.append(('start', name))
                time.sleep(0.3)
                events.append(('end', name))
        threads = [threading.Thread(target=job, args=(n,)) for n in 'ab']
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual([e[0] for e in events], ['start', 'end', 'start', 'end'])

    def test_wait_returns_current_state_after_timeout(self):
        folder = self.base / 'job'
        folder.mkdir()
        write_json(folder / 'status.json', {'schema': 'dcc.render.status.v1', 'state': 'running'})
        started = time.monotonic()
        self.assertEqual(render.wait(folder, timeout=0.3)['state'], 'running')
        self.assertGreaterEqual(time.monotonic() - started, 0.25)

    def test_wait_on_an_unknown_folder_fails_plainly(self):
        with self.assertRaisesRegex(ValueError, 'No render job'):
            render.wait(self.base / 'missing', timeout=0)

    def test_detached_job_runs_in_another_process_and_records_failure(self):
        source = self.base / 'scene.blend'
        source.write_bytes(b'synthetic saved native')
        views = self.base / 'views.json'
        write_json(views, VIEWS)
        queued = render.start_detached(source, self.base / 'job', str(self.base / 'no-blender-here.exe'), views=views)
        self.assertEqual(queued['status'], 'QUEUED')
        self.assertEqual(queued['job'], str((self.base / 'job').resolve()))
        final = render.wait(self.base / 'job', timeout=60)
        self.assertEqual(final['state'], 'failed', final)
        self.assertTrue(final['error'])

    def test_detached_child_handle_is_retained_until_exit_and_reaped(self):
        """Dropping a running Popen emits a warning and abandons explicit reaping."""
        source = self.base / 'scene.blend'
        source.write_bytes(b'synthetic saved native')
        views = self.base / 'views.json'
        write_json(views, VIEWS)
        release = self.base / 'release'
        real_popen = subprocess.Popen
        children = []

        def launch(*args, **kwargs):
            # Keep an actual owned child alive past start_detached's return.
            code = ('import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); '
                    'deadline=time.monotonic()+10\n'
                    'while not p.exists() and time.monotonic()<deadline: time.sleep(.02)')
            child = real_popen([sys.executable, '-c', code, str(release)], **kwargs)
            children.append(weakref.ref(child))
            return child

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', ResourceWarning)
                with mock.patch.object(render.subprocess, 'Popen', side_effect=launch):
                    queued = render.start_detached(source, self.base / 'job', 'unused', views=views)
                gc.collect()
                self.assertEqual(queued['status'], 'QUEUED')
                self.assertFalse(release.exists())
                self.assertFalse([w for w in caught if issubclass(w.category, ResourceWarning)])
                child = children[0]()
                self.assertIsNotNone(child, 'Running child handle was discarded')
                self.assertIsNone(child.returncode, 'Detached start waited for the child')
                release.touch()
                deadline = time.monotonic() + 10
                # Do not call poll/wait here: the owner must reap automatically.
                while child.returncode is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertEqual(child.returncode, 0)
        finally:
            release.touch(exist_ok=True)
            for reference in children:
                child = reference()
                if child is not None:
                    child.wait(timeout=15)


class RenderCliTests(unittest.TestCase):
    def test_project_and_views_are_mutually_exclusive(self):
        result = subprocess.run([sys.executable, '-m', 'dcc_harness', 'render', 'a.blend', '--blender', 'b', '--output-dir', 'o',
                                 '--project', 'p', '--views', 'v'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('not allowed with', result.stderr)

    def test_render_wait_reports_a_finished_job(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            write_json(folder / 'status.json', {'schema': 'dcc.render.status.v1', 'state': 'done', 'result': {'status': 'RENDERED'}})
            result = subprocess.run([sys.executable, '-m', 'dcc_harness', 'render-wait', str(folder), '--timeout', '1'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['state'], 'done')


if __name__ == '__main__':
    unittest.main()
