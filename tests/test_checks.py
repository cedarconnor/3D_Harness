"""Portable checks for learned checks: rules, proposals, the owner-approved library, occurrences and pinning."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

from coordination_helpers import Console, Fixture
from dcc_harness import checks, coordination as c, guidance, workflow
from dcc_harness.continuity import Continuity
from dcc_harness.evidence import digest, file_hash, read_json, write_json

FIELD_RULE = {'schema': 'dcc.check.rule.v1', 'kind': 'object_field', 'select': {'id': 'ext.*'},
              'field': 'bounds.min.z', 'min': -0.005}
RELATION_RULE = {'schema': 'dcc.check.rule.v1', 'kind': 'supported_by', 'subjects': {'id': 'ext.*'}, 'support': {'id': 'ground'},
                 'max_gap': 0.005, 'max_penetration': 0.01, 'footprint': 0.002}

TABLE_RULE = {**FIELD_RULE, 'select': {'id': 'ext.table.*'}}
TABLE_RELATION = {**RELATION_RULE, 'subjects': {'id': 'ext.table.*'}, 'support': {'id': 'ext.ground'}}


def obj(kind='MESH', low=0.0, matrix=None, materials=('stone',), render=True):
    return {'type': kind, 'bounds': [[-1, -1, low], [1, 1, low + 1]], 'dimensions': [2, 2, 1], 'material_ids': list(materials),
            'triangles': 12, 'vertices': 8, 'visibility': {'hidden': False, 'render': render, 'viewport': True},
            'matrix_world': matrix or [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}


def scene(**objects):
    return {'checkpoint_sha256': 'a' * 64, 'objects': objects}


def measured(spec, sha, distance):
    relation = spec['relations'][0]
    return {'schema': 'dcc.relations.measurement.v1', 'checkpoint_sha256': sha, 'spec_digest': digest(spec),
            'relations': {relation['id']: {'missing': [], 'subjects': {
                s: {'footprint_points': 4, 'hits': 4, 'min_distance': distance, 'max_distance': distance, 'bounds_gap': None}
                for s in relation['subjects']}}}}


class RuleTests(unittest.TestCase):
    def test_object_field_reports_each_selected_object(self):
        observed = scene(**{'ext.a': obj(), 'ext.b': obj(low=-0.1), 'cam': obj('CAMERA', low=-5)})
        result = checks.evaluate('nothing-below', FIELD_RULE, observed)
        self.assertEqual((result['status'], result['passed']), ('FAIL', False))
        self.assertEqual([(f['id'], f['code']) for f in result['findings']], [('ext.a', 'OK'), ('ext.b', 'BELOW')])
        narrow = {**FIELD_RULE, 'select': {'id': 'ext.a'}}
        self.assertEqual(checks.evaluate('nothing-below', narrow, observed)['status'], 'PASS')

    def test_measured_fields(self):
        mirrored = [[-2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        observed = scene(**{'ext.a': obj(matrix=mirrored, materials=(), render=False)})
        values = {field: checks.evaluate('x', {**FIELD_RULE, 'field': field, 'min': -100}, observed)['findings'][0]['value']
                  for field in ('dimensions.z', 'bounds.max.z', 'scale.min', 'scale.max', 'determinant', 'materials', 'visible.render', 'triangles')}
        self.assertEqual(values, {'dimensions.z': 1, 'bounds.max.z': 1, 'scale.min': 1, 'scale.max': 2, 'determinant': -2,
                                  'materials': 0, 'visible.render': 0, 'triangles': 12})
        flat = scene(**{'ext.a': {**obj(), 'matrix_world': [[1, 0], [0, 1]]}})
        self.assertEqual(checks.evaluate('x', {**FIELD_RULE, 'field': 'scale.min'}, flat)['findings'][0]['code'], 'UNMEASURED')

    def test_matching_nothing(self):
        observed = scene(ground=obj())
        self.assertEqual(checks.evaluate('x', FIELD_RULE, observed)['status'], 'FAIL')
        self.assertEqual(checks.evaluate('x', {**FIELD_RULE, 'require_match': False}, observed)['status'], 'PASS')

    def test_invalid_rules_are_refused(self):
        cases = {'skill note': {**FIELD_RULE, 'kind': 'looks_good'}, 'field': {**FIELD_RULE, 'field': 'colour'},
                 'bound': {k: v for k, v in FIELD_RULE.items() if k != 'min'}, 'order': {**FIELD_RULE, 'min': 2, 'max': 1},
                 'selector': {**FIELD_RULE, 'select': {}}, 'glob': {**FIELD_RULE, 'select': {'id': 3}},
                 'key': {**FIELD_RULE, 'note': 'x'}, 'schema': {**FIELD_RULE, 'schema': 'v0'},
                 'tolerance': {**RELATION_RULE, 'footprint': 0}}
        for name, rule in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                checks.validate_rule(rule)
        with self.assertRaisesRegex(ValueError, 'skill note'):
            checks.validate_rule(cases['skill note'])

    def test_relation_rule_resolves_and_needs_a_matching_measurement(self):
        observed = scene(**{'ext.b': obj(), 'ext.a': obj(), 'ground': obj()})
        spec = checks.resolve('legs-on-ground', RELATION_RULE, observed)
        self.assertEqual(spec['relations'][0]['subjects'], ['ext.a', 'ext.b'])
        self.assertEqual(spec['relations'][0]['id'], 'legs-on-ground')
        self.assertEqual(checks.evaluate('legs-on-ground', RELATION_RULE, observed)['status'], 'NOT_MEASURED')
        self.assertEqual(checks.evaluate('legs-on-ground', RELATION_RULE, observed, measured(spec, 'a' * 64, 0.03))['status'], 'FAIL')
        self.assertEqual(checks.evaluate('legs-on-ground', RELATION_RULE, observed, measured(spec, 'a' * 64, 0.0))['status'], 'PASS')
        with self.assertRaisesRegex(ValueError, 'another checkpoint'):
            checks.evaluate('legs-on-ground', RELATION_RULE, observed, measured(spec, 'b' * 64, 0.0))


class LibraryFixture(Fixture):
    def setUp(self):
        super().setUp()
        self.library = self.base / 'library'
        self.allow = self.base / 'contract-move.json'
        write_json(self.allow, {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': ['ext.ground'],
                                'allowed_object_prefixes': {'ext.table.': ['bounds', 'dimensions'], 'ext.ground': ['bounds']},
                                'spec': {'schema': 'dcc.spec.v1', 'required': {'ext.table.top': {'type': 'MESH'}}}})
        self.count = 0

    def publish(self, low):
        """Publish a checkpoint whose table rests at height `low`, beside a ground object."""
        self.count += 1
        active = workflow.resume(self.root)['active']
        edit = workflow.begin_edit(self.root, active['id'], active['checkpoint'], active['observation'], self.script,
                                   self.allow, f'move-{self.count}')['edit']
        native = self.base / f'candidate-{self.count}.blend'
        native.write_bytes(f'synthetic native {self.count}'.encode())
        obs = copy.deepcopy(self.obs)
        obs['checkpoint_sha256'] = file_hash(native)
        table = obs['objects']['ext.table.top']
        table['bounds'] = [[-1, -.5, low], [1, .5, low + 1]]
        obs['objects']['ext.ground'] = {**copy.deepcopy(table), 'name': 'Ground', 'asset_id': 'ground', 'bounds': [[-5, -5, -.1], [5, 5, 0]]}
        path = self.base / f'candidate-{self.count}.json'
        self.save_observation(path, obs)
        outcome = workflow.finish_edit(self.root, edit, native, path, self.handoff, {})
        self.assertEqual(outcome['status'], 'PUBLISHED', outcome)
        return c.checkpoint_ref(Continuity(self.root).status()['active'])

    def artist_note(self, at, text='The table sinks into the ground'):
        return self.add(source=self.actor('artist'), stage_id=None, priority='advisory', category='technical', text=text,
                        anchor={**at, 'instance_ids': ['ext.table.top']})

    def proposal(self, note, failing, passing, **updates):
        value = {'schema': 'dcc.check.proposal.v1', 'id': 'nothing-below-ground', 'note_id': note, 'classification': 'error',
                 'rule': TABLE_RULE, 'stages': ['direction', 'assembly'], 'rationale': 'Objects must not sink below the ground plane',
                 'proposer': self.actor(), 'fails': {'checkpoint': failing}, 'passes': {'checkpoint': passing}}
        value.update(updates)
        return value

    def proposed(self, **updates):
        sunk = self.publish(-0.2)
        note = self.artist_note(sunk)
        fixed = self.publish(0.0)
        result = self.apply('check.propose', self.proposal(note, sunk, fixed, **updates))
        return result, sunk, fixed, note

    def approve(self, revision, console=None, expected=None):
        version = checks.read_library(self.library)['version'] if expected is None else expected
        return checks.approve(self.library, self.root, revision, version, console or Console())


class ProposalTests(LibraryFixture):
    def test_proposal_proves_the_rule_on_both_fixtures(self):
        result, sunk, fixed, note = self.proposed()
        self.assertEqual(result['status'], 'COMMITTED')
        self.assertEqual(result['result']['results']['fails']['status'], 'FAIL')
        self.assertEqual(result['result']['results']['passes']['status'], 'PASS')
        self.assertEqual(result['result']['note']['text'], 'The table sinks into the ground')

    def test_proposals_that_prove_nothing_are_refused(self):
        sunk = self.publish(-0.2)
        note = self.artist_note(sunk)
        fixed = self.publish(0.0)
        cases = {'Taste stays project direction': {'classification': 'taste'},
                 'does not fail on the note': {'rule': {**TABLE_RULE, 'min': -0.5}},
                 "note's own checkpoint": {'fails': {'checkpoint': fixed}, 'passes': {'checkpoint': sunk}},
                 'skill note': {'rule': {**TABLE_RULE, 'kind': 'looks_right'}},
                 'Unknown feedback note': {'note_id': 'f' * 64},
                 'Unknown stage': {'stages': ['polish']}}
        for message, updates in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                self.apply('check.propose', self.proposal(note, sunk, fixed, **updates))
        later = self.publish(-0.3)
        with self.assertRaisesRegex(ValueError, 'does not pass on the fixed'):
            self.apply('check.propose', self.proposal(note, sunk, later))
        self.apply('check.propose', self.proposal(note, sunk, fixed))
        with self.assertRaisesRegex(ValueError, 'already proposed'):
            self.apply('check.propose', self.proposal(note, sunk, fixed))


class ApprovalTests(LibraryFixture):
    def test_approval_needs_the_owner_and_writes_a_chained_version(self):
        result, sunk, fixed, note = self.proposed()
        with self.assertRaisesRegex(RuntimeError, 'agent session'):
            self.approve(result['revision'], Console(environ={'CLAUDECODE': '1'}))
        self.assertEqual(checks.read_library(self.library)['version'], 0)
        console = Console()
        first = self.approve(result['revision'], console)
        self.assertEqual((first['status'], first['version']), ('APPROVED', 1))
        self.assertIn('Approve check.approve as the owner', console.shown[0])
        for shown in ('nothing-below-ground', 'bounds.min.z', 'The table sinks into the ground', 'Objects must not sink'):
            self.assertIn(shown, console.shown[0])
        library = checks.read_library(self.library)
        check = library['document']['checks'][0]
        self.assertEqual(check['id'], 'nothing-below-ground')
        self.assertEqual(check['approval']['channel'], 'owner_terminal')
        self.assertEqual(check['origin']['note']['text'], 'The table sinks into the ground')
        with self.assertRaisesRegex(ValueError, 'already in the library'):
            self.approve(result['revision'])
        other = self.apply('check.propose', self.proposal(note, sunk, fixed, id='table-not-sunk'))
        with self.assertRaisesRegex(ValueError, 'Stale library version'):
            self.approve(other['revision'], expected=0)
        second = self.approve(other['revision'])
        self.assertEqual(second['version'], 2)
        latest = checks.read_library(self.library)
        self.assertEqual(latest['document']['previous'], file_hash(self.library / 'versions/000001/library.json'))
        self.assertEqual([c_['id'] for c_ in latest['document']['checks']], ['nothing-below-ground', 'table-not-sunk'])
        self.assertEqual(len(checks.read_library(self.library, version=1)['document']['checks']), 1)

    def test_a_damaged_library_is_refused(self):
        result, *_ = self.proposed()
        self.approve(result['revision'])
        fixture = next((self.library / 'fixtures/nothing-below-ground').glob('fails.*'))
        original = fixture.read_bytes()
        fixture.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'changed'):
            checks.read_library(self.library)
        fixture.write_bytes(original)
        document = self.library / 'versions/000001/library.json'
        data = read_json(document); data['checks'][0]['rule']['min'] = -5
        document.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            checks.read_library(self.library)

    def test_occurrences_are_verified_and_ranked(self):
        result, sunk, fixed, note = self.proposed()
        self.approve(result['revision'])
        again = self.artist_note(sunk, text='Still sinking in the other corner')
        recorded = checks.occurrence(self.library, self.root, again, 'nothing-below-ground')
        self.assertEqual(recorded['sequence'], 1)
        with self.assertRaisesRegex(ValueError, 'already counted'):
            checks.occurrence(self.library, self.root, again, 'nothing-below-ground')
        passing = self.artist_note(fixed, text='Looks fine now')
        with self.assertRaisesRegex(ValueError, 'passes on the note'):
            checks.occurrence(self.library, self.root, passing, 'nothing-below-ground')
        listing = checks.listing(self.library)
        self.assertEqual([(x['id'], x['count']) for x in listing['checks']], [('nothing-below-ground', 2)])


class PinningTests(LibraryFixture):
    def pinned(self, version=None):
        path = self.base / 'pinned' / f'library-{version}.json'
        checks.export(self.library, path, version)
        return self.ref(path)

    def library_with_both(self):
        result, sunk, fixed, note = self.proposed()
        self.approve(result['revision'])
        spec = checks.resolve('table-on-ground', TABLE_RELATION, read_json(Continuity(self.root).status()['active']['observation']))
        fails, passes = (self.base / 'fails-measurement.json'), (self.base / 'passes-measurement.json')
        write_json(fails, measured({**spec}, sunk['checkpoint_sha256'], -0.2))
        write_json(passes, measured(spec, fixed['checkpoint_sha256'], 0.0))
        relation = self.apply('check.propose', self.proposal(note, sunk, fixed, id='table-on-ground', rule=TABLE_RELATION,
                                                             fails={'checkpoint': sunk, 'measurement': self.ref(fails)},
                                                             passes={'checkpoint': fixed, 'measurement': self.ref(passes)}))
        self.approve(relation['revision'])
        return spec

    def test_pinned_checks_run_at_submission_and_block_completion(self):
        spec = self.library_with_both()
        self.bind(checks=self.pinned())
        self.publish(-0.2)
        submitted = self.submit()
        result = submitted['result']
        self.assertEqual({r['id']: r['status'] for r in result['checks']},
                         {'nothing-below-ground': 'FAIL', 'table-on-ground': 'NOT_MEASURED'})
        self.assertEqual(result['failed_checks'], ['nothing-below-ground', 'table-on-ground'])
        with self.assertRaisesRegex(ValueError, 'Pinned library checks'):
            self.complete(submitted)
        fixed = self.publish(0.0)
        measurement = self.base / 'measurement-now.json'
        write_json(measurement, measured(spec, fixed['checkpoint_sha256'], 0.0))
        submitted = self.submit(check_measurements={'table-on-ground': self.ref(measurement)})
        self.assertEqual(submitted['result']['failed_checks'], [])
        self.assertEqual(self.complete(submitted)['status'], 'COMMITTED')

    def test_bindings_pin_a_version_and_earlier_bindings_are_unaffected(self):
        self.library_with_both()
        self.bind(checks=self.pinned(1))
        self.publish(-0.2)
        result = self.submit()['result']
        self.assertEqual([r['id'] for r in result['checks']], ['nothing-below-ground'])

    def test_a_project_bound_without_checks_runs_none(self):
        self.library_with_both()
        self.bind()
        self.publish(-0.2)
        self.assertNotIn('checks', self.submit()['result'])

    def test_requirements_list_the_pinned_checks(self):
        spec = self.library_with_both()
        self.bind(checks=self.pinned())
        needed = guidance.requirements(self.root, 'direction')
        relation = next(x for x in needed['checks'] if x['id'] == 'table-on-ground')
        self.assertEqual(relation['spec'], spec)
        self.assertIn('relations', relation['command'])
        self.assertIn('--spec', relation['command'])
        self.assertIn('table-on-ground', needed['skeleton']['check_measurements'])

    def test_a_pinned_file_needs_owner_approved_checks(self):
        self.library_with_both()
        path = self.base / 'forged.json'
        data = read_json(self.library / 'versions/000002/library.json')
        del data['checks'][0]['approval']
        write_json(path, data)
        with self.assertRaisesRegex(ValueError, 'owner'):
            self.bind(checks=self.ref(path))


class CommandTests(LibraryFixture):
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, env=env or os.environ)

    def test_propose_approve_and_list_from_the_command_line(self):
        sunk = self.publish(-0.2)
        note = self.artist_note(sunk)
        fixed = self.publish(0.0)
        path = self.base / 'proposal.json'
        write_json(path, self.proposal(note, sunk, fixed))
        proposed = self.run_cli('check-propose', self.root, '--proposal', path, '--expected-revision', self.revision(),
                                '--request-id', uuid.uuid4())
        self.assertEqual(proposed.returncode, 0, proposed.stderr)
        revision = json.loads(proposed.stdout)['revision']
        refused = self.run_cli('check-approve', self.library, '--project', self.root, '--proposal', revision, '--expected-version', 0,
                               env={**os.environ, 'CLAUDECODE': '1'})
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('agent session', refused.stderr)
        self.assertFalse((self.library / 'versions').exists())
        self.approve(revision)
        listed = self.run_cli('checks', self.library, '--export', self.base / 'exported.json')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout)['checks'][0]['id'], 'nothing-below-ground')
        self.assertEqual(file_hash(self.base / 'exported.json'), file_hash(self.library / 'versions/000001/library.json'))
        origin = self.run_cli('check-occurrence', self.library, '--project', self.root, '--note', note, '--check', 'nothing-below-ground')
        self.assertIn('already counted', origin.stderr)
        repeat = self.artist_note(sunk, text='The table is below the ground again')
        counted = self.run_cli('check-occurrence', self.library, '--project', self.root, '--note', repeat, '--check', 'nothing-below-ground')
        self.assertEqual(counted.returncode, 0, counted.stderr)
        self.assertEqual(json.loads(counted.stdout)['evaluation']['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
