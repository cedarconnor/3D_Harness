"""Portable checks for the blockout spec: strict validation, self-consistency, classification and the CLI."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dcc_harness import blockout
from dcc_harness.evidence import digest
from dcc_harness.relations import validate_relations

SPEC = {'schema': 'dcc.blockout.v1', 'name': 'yard', 'units': 'metres', 'up': 'Z', 'parts': [
    {'name': 'ground', 'category': 'ground', 'primitive': 'plane', 'position': [0, 0, 0], 'size': [8, 8, 0]},
    {'name': 'shed', 'category': 'structure', 'primitive': 'box', 'position': [0, 1.5, 0], 'size': [3, 2, 2.2], 'group': 'building', 'rests_on': 'ground'},
    {'name': 'roof', 'category': 'roof', 'primitive': 'wedge', 'position': [0, 1.5, 2.2], 'size': [2.8, 1.8, 0.6], 'group': 'building'},
    {'name': 'bench', 'category': 'furniture', 'primitive': 'box', 'position': [-2, -1, 0], 'size': [1.6, 0.6, 0.9], 'yaw': 90, 'rests_on': 'ground'},
    {'name': 'pot', 'category': 'prop', 'primitive': 'cylinder', 'position': [-2, -1, 0.9], 'size': [0.3, 0.3, 0.25], 'rests_on': 'bench'}],
    'proportions': [
        {'id': 'bench-to-shed', 'ratio': [{'part': 'bench', 'measure': 'height'}, {'part': 'shed', 'measure': 'height'}], 'target': 0.4, 'tolerance': 0.05},
        {'id': 'building-height', 'value': {'part': 'building', 'measure': 'height'}, 'max': 3.0}],
    'never': [{'id': 'bench-clear', 'rule': 'no_overlap', 'parts': ['bench', 'building']},
              {'id': 'pot-up', 'rule': 'not_below', 'part': 'pot', 'z': 0},
              {'id': 'pot-on-bench', 'rule': 'within', 'part': 'pot', 'footprint': 'bench'}],
    'avoid': ['The shed must not read as a house.']}


def changed(change):
    spec = copy.deepcopy(SPEC)
    change(spec)
    return spec


def measured(spec=SPEC, **overrides):
    parts = {name: {**record, 'objects': 1, 'ids': [name]} for name, record in blockout.planned(spec).items()}
    for name, record in overrides.items():
        parts[name] = {'objects': 0} if record is None else {**parts[name], **record}
    return {'schema': 'dcc.blockout.measurement.v1', 'checkpoint_sha256': 'a' * 64, 'spec_digest': digest(spec), 'unit_scale': 1.0, 'parts': parts}


def found(report):
    return {(f['code'], f['path']) for f in report['findings']}


class ValidationTests(unittest.TestCase):
    def test_a_valid_spec_passes_and_is_returned_unchanged(self):
        self.assertEqual(blockout.validate_spec(copy.deepcopy(SPEC)), SPEC)

    def test_unknown_fields_and_out_of_range_numbers_are_errors_not_clamped(self):
        cases = {
            'top field': lambda s: s.update(colour='red'), 'part field': lambda s: s['parts'][1].update(scale=2),
            'huge size': lambda s: s['parts'][1].update(size=[3, 2, 5000]), 'tiny size': lambda s: s['parts'][1].update(size=[3, 2, 0.0001]),
            'far position': lambda s: s['parts'][1].update(position=[0, 20000, 0]), 'nan': lambda s: s['parts'][1].update(position=[0, float('nan'), 0]),
            'boolean number': lambda s: s['parts'][1].update(size=[True, 2, 2]), 'yaw': lambda s: s['parts'][3].update(yaw=720),
            'plane height': lambda s: s['parts'][0].update(size=[8, 8, 0.2]), 'box without height': lambda s: s['parts'][1].update(size=[3, 2, 0]),
            'primitive': lambda s: s['parts'][1].update(primitive='torus'), 'category': lambda s: s['parts'][1].update(category='building'),
            'duplicate name': lambda s: s['parts'][2].update(name='shed'), 'uppercase name': lambda s: s['parts'][2].update(name='Roof'),
            'group equals part': lambda s: s['parts'][2].update(group='bench'), 'support': lambda s: s['parts'][4].update(rests_on='table'),
            'self support': lambda s: s['parts'][4].update(rests_on='pot'), 'ids': lambda s: s['parts'][4].update(ids=[]),
            'units': lambda s: s.update(units='feet'), 'up': lambda s: s.update(up='Y'), 'no parts': lambda s: s.update(parts=[]),
            'too many parts': lambda s: s.update(parts=[{**s['parts'][0], 'name': f'p{i}'} for i in range(501)]),
            'tolerance key': lambda s: s.update(tolerance={'angle': 1}), 'avoid': lambda s: s.update(avoid=['']),
            'measure': lambda s: s['proportions'][1]['value'].update(measure='volume'),
            'unknown reference': lambda s: s['proportions'][1]['value'].update(part='tower'),
            'value and ratio': lambda s: s['proportions'][1].update(ratio=s['proportions'][0]['ratio']),
            'target without tolerance': lambda s: s['proportions'][0].pop('tolerance'),
            'target and range': lambda s: s['proportions'][0].update(min=0.1), 'no limit': lambda s: s['proportions'][1].pop('max'),
            'min above max': lambda s: s['proportions'][1].update(min=5.0),
            'duplicate id': lambda s: s['never'][0].update(id='building-height'), 'rule': lambda s: s['never'][0].update(rule='near'),
            'rule fields': lambda s: s['never'][1].update(parts=['pot']), 'overlap with itself': lambda s: s['never'][0].update(parts=['bench', 'bench']),
            'level': lambda s: s['never'][1].update(z='ground')}
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                blockout.validate_spec(changed(change))

    def test_a_spec_must_satisfy_its_own_proportions_and_never_rules(self):
        for name, change in {'proportion': lambda s: s['parts'][3].update(size=[1.6, 0.6, 1.6]),
                             'overlap': lambda s: s['parts'][3].update(position=[0, 1.5, 0]),
                             'below': lambda s: s['parts'][4].update(position=[-2, -1, -1]),
                             'outside': lambda s: s['parts'][4].update(position=[2, -3, 0.9])}.items():
            with self.subTest(name), self.assertRaisesRegex(ValueError, 'breaks its own rules'):
                blockout.validate_spec(changed(change))

    def test_yaw_turns_the_world_box_but_not_the_part_size(self):
        bench = blockout.planned(SPEC)['bench']
        self.assertEqual(bench['size'], [1.6, 0.6, 0.9])
        self.assertEqual((bench['world']['min'], bench['world']['max']), ([-2.3, -1.8, 0], [-1.7, -0.2, 0.9]))

    def test_review_views_are_validated_by_the_render_rules(self):
        views = {'schema': 'dcc.review.views.v1', 'render': {'engine': 'BLENDER_WORKBENCH', 'resolution': [800, 600], 'samples': 8, 'seed': 0},
                 'views': [{'id': 'front', 'purpose': 'whole', 'camera': {'lens': 35, 'location': [0, -8, 2], 'target': [0, 0, 1]}}]}
        blockout.validate_spec(changed(lambda s: s.update(review_views=views)))
        with self.assertRaises(ValueError):
            blockout.validate_spec(changed(lambda s: s.update(review_views={**views, 'views': []})))


class ClassifyTests(unittest.TestCase):
    def test_a_scene_built_as_planned_passes(self):
        report = blockout.classify(SPEC, measured())
        self.assertEqual((report['passed'], report['findings'], report['parts_measured'], report['not_measured']), (True, [], 5, SPEC['avoid']))

    def test_size_and_position_use_the_tolerances(self):
        inside = blockout.classify(SPEC, measured(bench={'size': [1.7, 0.6, 0.9], 'base': [-2.05, -1, 0]}))
        self.assertTrue(inside['passed'])
        report = blockout.classify(SPEC, measured(bench={'size': [2.0, 0.6, 0.9]}, pot={'base': [-2, -1, 1.2]}))
        self.assertEqual(found(report), {('SIZE', 'parts/bench/size'), ('POSITION', 'parts/pot/position')})
        tight = changed(lambda s: s.update(tolerance={'size': 0.01, 'position': 0.01}))
        self.assertEqual(found(blockout.classify(tight, measured(tight, bench={'size': [1.7, 0.6, 0.9], 'base': [-2.05, -1, 0]}))),
                         {('SIZE', 'parts/bench/size'), ('POSITION', 'parts/bench/position')})

    def test_a_missing_part_fails_and_so_does_every_rule_that_needs_it(self):
        report = blockout.classify(SPEC, measured(pot=None))
        self.assertEqual(found(report), {('PART_MISSING', 'parts/pot'), ('UNMEASURED', 'never/pot-up'), ('UNMEASURED', 'never/pot-on-bench')})
        self.assertFalse(report['passed'])
        group = blockout.classify(SPEC, measured(roof=None))
        self.assertEqual(found(group), {('PART_MISSING', 'parts/roof'), ('UNMEASURED', 'proportions/building-height'), ('UNMEASURED', 'never/bench-clear')})

    def test_proportions_and_never_rules_are_judged_on_measured_boxes(self):
        tall = {'size': [1.6, 0.6, 1.4], 'world': {'min': [-2.3, -1.8, 0], 'max': [-1.7, -0.2, 1.4]}}
        self.assertEqual(found(blockout.classify(SPEC, measured(bench=tall))), {('SIZE', 'parts/bench/size'), ('PROPORTION', 'proportions/bench-to-shed')})
        sunk = {'base': [-2, -1, -0.5], 'world': {'min': [-2.15, -1.15, -0.5], 'max': [-1.85, -0.85, -0.25]}}
        self.assertEqual(found(blockout.classify(SPEC, measured(pot=sunk))), {('POSITION', 'parts/pot/position'), ('NEVER_BELOW', 'never/pot-up')})
        away = {'base': [1, -3, 0.9], 'world': {'min': [0.85, -3.15, 0.9], 'max': [1.15, -2.85, 1.15]}}
        self.assertEqual(found(blockout.classify(SPEC, measured(pot=away))), {('POSITION', 'parts/pot/position'), ('NEVER_OUTSIDE', 'never/pot-on-bench')})
        indoors = {'base': [0, 1.5, 0], 'world': {'min': [-0.3, 0.7, 0], 'max': [0.3, 2.3, 0.9]}}
        self.assertIn(('NEVER_OVERLAP', 'never/bench-clear'), found(blockout.classify(SPEC, measured(bench=indoors))))

    def test_every_finding_has_a_message_and_a_remediation(self):
        report = blockout.classify(SPEC, measured(pot=None, bench={'size': [2.0, 0.6, 1.4]}))
        self.assertTrue(report['findings'] and all(f['message'] and f['remediation'] and f['path'] for f in report['findings']))
        self.assertEqual(sum(report['by_code'].values()), len(report['findings']))

    def test_a_measurement_of_another_spec_is_refused(self):
        other = changed(lambda s: s.update(name='other'))
        with self.assertRaises(ValueError):
            blockout.classify(SPEC, measured(other))


class CommandTests(unittest.TestCase):
    def test_relations_come_from_rests_on_and_are_a_valid_definition(self):
        definition = blockout.relations(SPEC)
        validate_relations(definition)
        self.assertEqual([(r['subjects'], r['support']) for r in definition['relations']],
                         [(['shed'], ['ground']), (['bench'], ['ground']), (['pot'], ['bench'])])
        self.assertIsNone(blockout.relations(changed(lambda s: [p.pop('rests_on', None) for p in s['parts']])))

    def test_spec_check_reports_a_summary_and_exits_nonzero_on_a_broken_spec(self):
        with tempfile.TemporaryDirectory() as folder:
            good, bad = Path(folder) / 'good.json', Path(folder) / 'bad.json'
            good.write_text(json.dumps(SPEC), encoding='utf-8')
            bad.write_text(json.dumps(changed(lambda s: s['parts'][1].update(colour='red'))), encoding='utf-8')
            summary = blockout.check_file(good)
            self.assertEqual((summary['passed'], summary['parts'], summary['supported_parts'], summary['spec_digest']), (True, 5, 3, digest(SPEC)))
            proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'spec-check', str(bad)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('unknown field', proc.stderr)

    def test_the_potting_shed_study_spec_is_valid(self):
        path = Path(__file__).resolve().parents[1] / 'docs/studies/potting-shed.blockout.json'
        self.assertEqual(blockout.check_file(path)['parts'], 10)

    def test_build_and_compare_refuse_bad_paths_before_blender_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = Path(folder) / 'spec.json'
            spec.write_text(json.dumps(SPEC), encoding='utf-8')
            with self.assertRaises(ValueError):
                blockout.build_file(spec, spec, Path(folder) / 'out', 'blender')              # output exists and is no .blend
            with self.assertRaises(ValueError):
                blockout.build_file(spec, Path(folder) / 'new.blend', Path(folder) / 'out', 'blender', source=Path(folder) / 'absent.blend')
            with self.assertRaises(ValueError):
                blockout.compare_file(spec, Path(folder) / 'absent.blend', Path(folder) / 'out', 'blender')
            self.assertFalse((Path(folder) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
