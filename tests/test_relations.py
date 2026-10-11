"""Portable checks for supported_by relations: definitions, classification, repair history and guidance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import guidance, relations, workflow
from dcc_harness.evidence import digest, file_hash, read_json, write_json

SPEC = {'schema': 'dcc.relations.v1', 'relations': [
    {'id': 'bench-on-ground', 'kind': 'supported_by', 'subjects': ['leg.0', 'leg.1'], 'support': ['ground'],
     'max_gap': 0.005, 'max_penetration': 0.01, 'footprint': 0.002},
    {'id': 'crate-on-ground', 'kind': 'supported_by', 'subjects': ['crate'], 'support': ['ground'],
     'max_gap': 0.005, 'max_penetration': 0.01, 'footprint': 0.002}]}


def subject(minimum, maximum=None, points=4, hits=4, bounds_gap=None):
    return {'footprint_points': points, 'hits': hits, 'min_distance': minimum if hits else None,
            'max_distance': (minimum if maximum is None else maximum) if hits else None, 'bounds_gap': bounds_gap}


def measurement(legs=(0.0, 0.0), crate=0.0, missing=(), **extra):
    value = {'schema': 'dcc.relations.measurement.v1', 'checkpoint_sha256': 'a' * 64, 'spec_digest': digest(SPEC),
             'relations': {'bench-on-ground': {'missing': list(missing), 'subjects': {
                               f'leg.{i}': (v if isinstance(v, dict) else subject(v)) for i, v in enumerate(legs)}},
                           'crate-on-ground': {'missing': [], 'subjects': {'crate': crate if isinstance(crate, dict) else subject(crate)}}}}
    value.update(extra)
    return value


def finding(report, sid, rid='bench-on-ground'):
    return report['relations'][rid]['findings'][sid]


class DefinitionTests(unittest.TestCase):
    def test_valid_definition_passes(self):
        self.assertEqual(relations.validate_relations(copy.deepcopy(SPEC)), SPEC)

    def test_invalid_definitions_are_rejected(self):
        bench = SPEC['relations'][0]
        cases = {
            'schema': {**SPEC, 'schema': 'dcc.relations.v2'},
            'kind': {**SPEC, 'relations': [{**bench, 'kind': 'touching'}]},
            'duplicate id': {**SPEC, 'relations': [bench, bench]},
            'no subjects': {**SPEC, 'relations': [{**bench, 'subjects': []}]},
            'subject is support': {**SPEC, 'relations': [{**bench, 'support': ['leg.0']}]},
            'negative tolerance': {**SPEC, 'relations': [{**bench, 'max_gap': -0.1}]},
            'zero footprint': {**SPEC, 'relations': [{**bench, 'footprint': 0}]},
            'unknown key': {**SPEC, 'relations': [{**bench, 'method': 'aabb'}]},
            'no relations': {**SPEC, 'relations': []},
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                relations.validate_relations(copy.deepcopy(value))


class ClassificationTests(unittest.TestCase):
    def test_contact_within_tolerance_passes(self):
        report = relations.classify(SPEC, measurement(legs=(0.004, -0.009)))
        self.assertTrue(report['passed'])
        self.assertEqual(finding(report, 'leg.0')['code'], 'OK')
        self.assertEqual(finding(report, 'leg.0')['permitted'], 'none')
        self.assertEqual(finding(report, 'leg.0')['evidence'], 'native_raycast')

    def test_gap_and_penetration_beyond_tolerance_fail_with_signed_error(self):
        report = relations.classify(SPEC, measurement(legs=(0.03, -0.03)))
        self.assertFalse(report['passed'])
        self.assertEqual((finding(report, 'leg.0')['code'], finding(report, 'leg.0')['error']), ('GAP', 0.03))
        self.assertEqual((finding(report, 'leg.1')['code'], finding(report, 'leg.1')['error']), ('PENETRATION', -0.03))
        self.assertEqual(finding(report, 'leg.0')['permitted'], 'repair')

    def test_mixed_gap_and_penetration_is_a_conflict_no_rigid_move_fixes(self):
        report = relations.classify(SPEC, measurement(legs=(0.03, -0.03)))
        self.assertTrue(report['relations']['bench-on-ground']['conflict'])
        self.assertFalse(report['relations']['crate-on-ground']['conflict'])
        self.assertFalse(relations.classify(SPEC, measurement(legs=(0.03, 0.04)))['relations']['bench-on-ground']['conflict'])

    def test_the_point_closest_to_contact_decides(self):
        # A leg on a slope: one corner touches, another floats 4 cm. It stands.
        report = relations.classify(SPEC, measurement(legs=(subject(0.001, 0.04), 0.0)))
        self.assertEqual(finding(report, 'leg.0')['code'], 'OK')
        self.assertEqual(finding(report, 'leg.0')['spread'], 0.039)

    def test_no_hits_is_off_support_and_partial_hits_are_reported(self):
        report = relations.classify(SPEC, measurement(legs=(subject(0, hits=0), subject(0.0, hits=2))))
        self.assertEqual(finding(report, 'leg.0')['code'], 'OFF_SUPPORT')
        self.assertEqual(finding(report, 'leg.0')['permitted'], 'repair')
        self.assertEqual(finding(report, 'leg.1')['code'], 'OK')
        self.assertEqual(finding(report, 'leg.1')['coverage'], 'partial: 2 of 4 footprint points over the support')

    def test_missing_targets_ask_for_inspection(self):
        report = relations.classify(SPEC, measurement(missing=['ground']))
        self.assertEqual(finding(report, 'leg.0')['code'], 'MISSING_TARGET')
        self.assertEqual(finding(report, 'leg.0')['permitted'], 'inspect')
        self.assertFalse(report['passed'])

    def test_a_disagreeing_bounds_estimate_only_permits_inspection(self):
        report = relations.classify(SPEC, measurement(legs=(subject(0.0, bounds_gap=-0.4), 0.0)))
        leg = finding(report, 'leg.0')
        self.assertEqual(leg['code'], 'OK')
        self.assertEqual(leg['bounds_estimate'], {'code': 'PENETRATION', 'error': -0.4, 'evidence': 'bounds_only',
                                                  'permitted': 'inspect', 'agrees': False})
        self.assertTrue(report['passed'])

    def test_measurement_for_another_definition_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'definition'):
            relations.classify(SPEC, measurement(spec_digest='b' * 64))


class HistoryTests(Fixture):
    def entry(self, legs, crate=0.0, strategy=None):
        report = relations.classify(SPEC, measurement(legs=legs, crate=crate))
        report['source'] = {'path': 'candidate.blend', 'sha256': 'c' * 64}
        return relations.record(self.root, report, strategy)

    def warnings(self):
        return relations.history(self.root)['warnings']

    def test_record_is_append_only_and_bound_to_the_parent(self):
        first = self.entry((0.03, 0.03), strategy='Raised the bench 3 cm')
        second = self.entry((0.0, 0.0))
        self.assertEqual((first['sequence'], second['sequence']), (1, 2))
        self.assertEqual(first['parent'], workflow.resume(self.root)['active']['id'])
        self.assertEqual(read_json(self.root / 'relations/000001.json')['strategy'], 'Raised the bench 3 cm')
        with self.assertRaises(FileExistsError):
            write_json(self.root / 'relations/000001.json', {})

    def test_opposing_failures_warn_with_the_strategies_tried(self):
        self.entry((-0.03, -0.03), strategy='Lowered the whole bench 3 cm')
        self.entry((0.03, 0.03), strategy='Raised the whole bench 3 cm')
        codes = {(w['code'], w['subject']) for w in self.warnings()}
        self.assertEqual(codes, {('OPPOSING', 'leg.0'), ('OPPOSING', 'leg.1')})
        tried = [a['strategy'] for a in self.warnings()[0]['attempts']]
        self.assertEqual(tried, ['Lowered the whole bench 3 cm', 'Raised the whole bench 3 cm'])

    def test_repeated_failure_without_progress_warns(self):
        self.entry((0.03, 0.0), strategy='Moved leg 0 down 1 mm')
        self.entry((0.029, 0.0), strategy='Moved leg 0 down another 1 mm')
        self.assertEqual([(w['code'], w['subject']) for w in self.warnings()], [('NO_PROGRESS', 'leg.0')])

    def test_steady_improvement_does_not_warn(self):
        self.entry((0.03, 0.0))
        self.entry((0.01, 0.0))
        self.assertEqual(self.warnings(), [])
        self.assertEqual(relations.history(self.root)['subjects']['bench-on-ground/leg.0']['trend'], 'IMPROVING')

    def test_a_conflict_in_the_latest_measurement_warns_once_per_relation(self):
        self.entry((0.03, -0.03), strategy='Translated the bench down 2 cm')
        conflicts = [w for w in self.warnings() if w['code'] == 'CONFLICT']
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['relation'], 'bench-on-ground')
        self.assertIn('rigid move', conflicts[0]['advice'])

    def test_resolution_and_unrelated_subjects_clear_warnings(self):
        self.entry((-0.03, -0.03), crate=0.0)
        self.entry((0.03, 0.03), crate=0.0)
        self.entry((0.0, 0.0), crate=0.0)
        self.assertEqual(self.warnings(), [])


class RelationCommandTests(Fixture):
    def fake_worker(self, legs=(0.0, 0.0)):
        def run(blender, folder, worker, action, request):
            value = measurement(legs=legs, checkpoint_sha256=request['source']['sha256'], spec_digest=digest(request['definition']))
            write_json(Path(request['out']) / 'measurement.json', value)
        return run

    def run_relations(self, legs=(0.0, 0.0), **kwargs):
        spec = self.base / 'relations.json'
        if not spec.exists():
            write_json(spec, SPEC)
        with mock.patch.object(relations, 'run_worker', side_effect=self.fake_worker(legs)):
            return relations.measure_file(self.native, self.base / ('rel-' + str(len(list(self.base.glob('rel-*'))))), 'blender.exe',
                                          spec=kwargs.get('spec', spec), project=kwargs.get('project'), strategy=kwargs.get('strategy'))

    def test_measure_returns_a_bound_report_and_records_with_a_project(self):
        result = self.run_relations(legs=(0.03, 0.03))
        self.assertFalse(result['passed'])
        self.assertEqual(result['source']['sha256'], file_hash(self.native))
        self.assertNotIn('recorded', result)
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {'relations': SPEC})
        recorded = self.run_relations(legs=(0.0, 0.0), spec=None, project=self.root, strategy='Lowered the bench')
        self.assertEqual(recorded['recorded']['sequence'], 1)
        self.assertEqual(recorded['history']['warnings'], [])

    def test_strategy_needs_a_project(self):
        with self.assertRaisesRegex(ValueError, 'strategy'):
            self.run_relations(strategy='Lowered the bench')


class RelationGuidanceTests(Fixture):
    def publish_relations(self):
        edit = self.begin()['edit']
        native, obs = self.candidate()
        workflow.finish_edit(self.root, edit, native, obs, self.handoff, {'relations': SPEC})

    def test_relations_decision_adds_a_measurement_step(self):
        self.publish_relations()
        result = guidance.next_steps(self.root)
        self.assertIn('relations', [s['id'] for s in result['steps']])
        command = next(s for s in result['steps'] if s['id'] == 'relations')['command']
        self.assertIn('--project "' + str(self.root) + '" --strategy "<what you changed, or initial>"', command)

    def test_history_warnings_appear_in_next_and_brief(self):
        self.publish_relations()
        for legs, strategy in (((-0.03, -0.03), 'Lowered the whole bench 3 cm'), ((0.03, 0.03), 'Raised the whole bench 3 cm')):
            report = relations.classify(SPEC, measurement(legs=legs))
            report['source'] = {'path': 'candidate.blend', 'sha256': 'c' * 64}
            relations.record(self.root, report, strategy)
        self.assertEqual({w['code'] for w in guidance.next_steps(self.root)['relation_warnings']}, {'OPPOSING'})
        text = guidance.brief(self.root)
        self.assertIn('## Relation history', text)
        self.assertIn('Raised the whole bench 3 cm', text)
        self.assertIn('OPPOSING', text)


if __name__ == '__main__':
    unittest.main()
