import concurrent.futures
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dcc_harness import revisions, workflow
from dcc_harness.continuity import Continuity
from dcc_harness.evidence import file_hash, read_json, write_json
from test_continuity_checks import observation, contract, resign


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'state'
        self.native = self.base / 'original.blend'
        self.native.write_bytes(b'synthetic original; not native qualification')
        self.obs = observation()
        self.obs['scene']['world'] = {'nodes': [{'name': 'Background', 'inputs': {'Strength': .5}}], 'links': []}
        self.obs['native_dirty'] = False
        self.obs['coverage']['measured'] = ['geometry', 'materials']
        self.obs['checkpoint_sha256'] = file_hash(self.native)
        resign(self.obs)
        self.obs_path = self.base / 'original.json'
        write_json(self.obs_path, self.obs)
        self.started = workflow.start(self.root, self.native, self.obs_path, 'Revision test', {'palette': 'warm'})
        self.parent = self.started['active']['id']
        self.candidate = self.base / 'artist.blend'
        self.candidate.write_bytes(b'synthetic external revision; not native qualification')
        after = copy.deepcopy(self.obs)
        after['checkpoint_sha256'] = file_hash(self.candidate)
        after['materials']['stone']['graph']['nodes'][0]['inputs']['Roughness'] = .65
        self.after = self.base / 'artist.json'
        write_json(self.after, resign(after))
        self.rules = contract()
        self.rules['allowed_new_prefixes'] = []
        self.rules['allowed_material_inputs'] = {'stone': {'Principled BSDF': {'Roughness': .65}}}
        self.contract = self.base / 'contract.json'
        write_json(self.contract, self.rules)
        self.handoff = self.base / 'CONTINUE.md'
        self.handoff.write_text('Keep the changed stone roughness and existing layout.', encoding='utf-8')

    def preview(self, **kwargs):
        args = dict(root=self.root, expected_parent=self.parent, checkpoint=self.candidate, observation=self.after,
                    contract=self.contract, handoff=self.handoff, updates={'stone_roughness': .65},
                    label='artist-material', note='Saved external material adjustment', out=self.base / 'preview')
        args.update(kwargs)
        return revisions.preview_revision(**args)

    def accept(self, preview, **kwargs):
        args = dict(root=self.root, preview=preview['preview'], expected_preview_sha=preview['preview_sha256'],
                    review_note='Engineering fixture reviewed; no artistic acceptance claim')
        args.update(kwargs)
        return revisions.accept_revision(**args)

    def tree(self):
        return {str(p.relative_to(self.root)): file_hash(p) for p in self.root.rglob('*') if p.is_file()}

    def test_preview_is_read_only_to_store_and_lists_shared_users(self):
        original = self.tree()
        preview = self.preview()
        self.assertEqual(preview['status'], 'READY_FOR_REVIEW')
        self.assertEqual(preview['changed_material_users']['stone']['after'], ['ext.table.top'])
        self.assertEqual(self.tree(), original)
        self.assertEqual(workflow.resume(self.root)['active']['id'], self.parent)

    def test_accept_retains_contract_provenance_decisions_and_old_bytes(self):
        original = self.tree()
        preview = self.preview()
        result = self.accept(preview)
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(result['active']['sequence'], 2)
        for name, sha in original.items():
            self.assertEqual(file_hash(self.root / name), sha)
        packet = workflow.resume(self.root)
        self.assertEqual(packet['decisions'], {'palette': 'warm', 'stone_roughness': .65})
        self.assertEqual(packet['pending'], [])
        self.assertFalse((self.root / 'operations.jsonl').exists())
        check = read_json(Path(result['active']['checkpoint']).parent / 'check.json')
        self.assertEqual(check['external_revision']['contract'], self.rules)
        self.assertEqual(check['external_revision']['preview_sha256'], preview['preview_sha256'])
        self.assertEqual(check['external_revision']['preview_manifest']['source_kind'], 'external_saved_edit')
        reviewed = workflow.review(self.root)
        self.assertEqual(reviewed['external_revision']['preview_sha256'], preview['preview_sha256'])
        self.assertEqual(reviewed['external_revision']['review_attribution'], 'caller_supplied')

    def test_original_candidate_changes_do_not_change_frozen_review(self):
        preview = self.preview()
        frozen = file_hash(Path(preview['preview']) / 'checkpoint.blend')
        self.candidate.write_bytes(b'later artist work')
        self.handoff.write_text('different later handoff')
        result = self.accept(preview)
        self.assertEqual(result['active']['checkpoint_sha256'], frozen)

    def test_changed_preview_file_or_wrong_hash_cannot_publish(self):
        preview = self.preview()
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.accept(preview, expected_preview_sha='a' * 64)
        (Path(preview['preview']) / 'handoff.md').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Frozen revision input changed'):
            self.accept(preview)
        self.assertEqual(workflow.resume(self.root)['active']['id'], self.parent)

    def test_unallowed_change_is_retained_as_rejected_preview(self):
        after = read_json(self.after)
        after['scene']['world']['nodes'][0]['inputs']['Strength'] = 2
        path = self.base / 'bad.json'
        write_json(path, resign(after))
        preview = self.preview(observation=path)
        self.assertEqual(preview['status'], 'REJECTED_CONTRACT')
        self.assertEqual(self.accept(preview)['status'], 'REJECTED_CONTRACT')
        self.assertEqual(workflow.resume(self.root)['active']['id'], self.parent)

    def test_stale_parent_cannot_preview_or_accept(self):
        with self.assertRaisesRegex(ValueError, 'Stale revision parent'):
            self.preview(expected_parent='old')
        one = self.preview()
        two = self.preview(out=self.base / 'other-preview', label='other-material')
        self.accept(two)
        with self.assertRaisesRegex(ValueError, 'Stale revision parent'):
            self.accept(one)

    def test_pending_native_operation_blocks_preview_and_accept(self):
        preview = self.preview()
        script = self.base / 'edit.py'
        script.write_text('# pending real workflow reservation')
        workflow.begin_edit(self.root, self.parent, self.native, self.obs_path, script, self.contract, 'pending-edit')
        with self.assertRaisesRegex(RuntimeError, 'Unresolved workflow'):
            self.preview(out=self.base / 'pending-preview')
        with self.assertRaisesRegex(RuntimeError, 'Unresolved workflow'):
            self.accept(preview)
        self.assertEqual(workflow.resume(self.root)['status'], 'RECONCILE')

    def test_incomplete_reservation_and_metadata_lock_are_not_bypassed(self):
        preview = self.preview()
        (self.root / 'workflow.lock').write_text('{}')
        with self.assertRaises(RuntimeError):
            self.accept(preview)
        (self.root / 'workflow.lock').unlink()
        (self.root / 'edits' / 'partial').mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, 'Partial edit'):
            self.accept(preview)

    def test_lost_ack_returns_existing_publication_without_redispatch(self):
        preview = self.preview()
        publish = Continuity.publish

        def published_then_lost(*args, **kwargs):
            publish(*args, **kwargs)
            raise RuntimeError('Injected lost acknowledgement after commit')

        with patch.object(Continuity, 'publish', published_then_lost):
            with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
                self.accept(preview)
        committed = self.tree()
        with patch.object(Continuity, 'publish', side_effect=AssertionError('must not republish')):
            recovered = self.accept(preview)
        self.assertEqual(recovered['status'], 'ALREADY_PUBLISHED')
        self.assertEqual(recovered['accepted']['sequence'], 2)
        self.assertEqual(self.tree(), committed)

    def test_partial_publication_stops_without_cleanup(self):
        preview = self.preview()

        def partial(*args, **kwargs):
            (self.root / 'checkpoints' / '000002').mkdir()
            raise RuntimeError('Injected partial publication')

        with patch.object(Continuity, 'publish', partial):
            with self.assertRaisesRegex(RuntimeError, 'partial publication'):
                self.accept(preview)
        with self.assertRaisesRegex(RuntimeError, 'Incomplete/unexpected'):
            self.accept(preview)
        self.assertTrue((self.root / 'checkpoints' / '000002').is_dir())

    def test_concurrent_accepts_publish_at_most_one_checkpoint(self):
        preview = self.preview()

        def attempt(_):
            try:
                return self.accept(preview)['status']
            except RuntimeError:
                return 'LOCKED'

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(results.count('PUBLISHED'), 1)
        self.assertEqual(workflow.resume(self.root)['active']['sequence'], 2)

    def test_another_project_and_inside_store_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside the project store'):
            self.preview(out=self.root / 'checkpoints' / 'bad-preview')
        preview = self.preview()
        other = self.base / 'other-state'
        workflow.start(other, self.native, self.obs_path, 'Different project', {})
        with self.assertRaisesRegex(ValueError, 'another project'):
            self.accept(preview, root=other)

    def test_relative_parent_segments_cannot_hide_an_inside_store_output(self):
        alias = self.base / 'other' / '..' / 'state' / 'checkpoints' / 'preview'
        with self.assertRaisesRegex(ValueError, 'outside the project store'):
            self.preview(out=alias)
        self.assertFalse((self.root / 'checkpoints' / 'preview').exists())

    def test_accept_recomputes_checks_even_when_modified_report_is_rehashed(self):
        preview = self.preview()
        folder = Path(preview['preview'])
        report = read_json(folder / 'check.json')
        report['checked_targets'] = ['invented-target']
        (folder / 'check.json').write_text(json.dumps(report))
        manifest = read_json(folder / 'manifest.json')
        manifest['files']['check.json'] = file_hash(folder / 'check.json')
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'checks differ from preview'):
            self.accept(preview, expected_preview_sha=file_hash(folder / 'manifest.json'))
        self.assertEqual(workflow.resume(self.root)['active']['id'], self.parent)

    def test_older_publication_can_be_found_after_another_accepted_step(self):
        first = self.preview()
        accepted = self.accept(first)
        second = self.preview(expected_parent=accepted['active']['id'], label='second-step', out=self.base / 'second-preview')
        later = self.accept(second)
        recovered = self.accept(first)
        self.assertEqual(recovered['accepted']['id'], accepted['active']['id'])
        self.assertEqual(recovered['active']['id'], later['active']['id'])

    def test_dirty_candidate_and_empty_review_note_rejected(self):
        after = read_json(self.after)
        after['native_dirty'] = True
        path = self.base / 'dirty.json'
        write_json(path, after)
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.preview(observation=path)
        preview = self.preview()
        with self.assertRaisesRegex(ValueError, 'Review note'):
            self.accept(preview, review_note=' ')

    def test_observed_external_dependencies_reject_before_relocating_candidate(self):
        for kind in ('image', 'library'):
            after = read_json(self.after)
            if kind == 'image':
                after['materials']['stone']['graph']['nodes'].append({'name': 'ExternalTexture', 'inputs': {},
                    'image': {'exists': True, 'sha256': 'b' * 64, 'packed': False, 'path': '//texture.png'}})
            else:
                after['objects']['ext.table.top']['mesh_datablock']['library'] = '//asset.blend'
            path = self.base / (kind + '.json')
            write_json(path, resign(after))
            with self.assertRaisesRegex(ValueError, 'relocation'):
                self.preview(observation=path, out=self.base / (kind + '-preview'))
            self.assertFalse((self.base / (kind + '-preview')).exists())

    def test_cli_accept_and_fresh_resume(self):
        preview = self.preview()
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'accept-revision', str(self.root),
            preview['preview'], '--preview-sha', preview['preview_sha256'], '--review-note', 'CLI fixture review'],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(proc.stdout)['status'], 'PUBLISHED')
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'resume', str(self.root)],
                              capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(proc.stdout)['active']['sequence'], 2)
