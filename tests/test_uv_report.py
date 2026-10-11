"""Portable checks for uv-report: target validation, classification, project decisions and the CLI."""
import copy
import subprocess
import sys
import unittest

from coordination_helpers import Fixture
from dcc_harness import uv_report, workflow

TARGETS = {'schema': 'dcc.uv.targets.v1', 'targets': [
    {'id': 'props', 'select': 'ext.prop.*', 'min_density': 256, 'max_density': 2048, 'max_overlap': 0.02, 'max_outside': 0.0},
    {'id': 'ground', 'select': 'ground', 'min_density': 64, 'texture_px': 1024}]}


def measured(**objects):
    return {'schema': 'dcc.uv.measurement.v1', 'checkpoint_sha256': 'a' * 64, 'grid': 256, 'objects': objects}


def mesh(uv_per_m=0.5, texture_px=1024, overlap=0.0, outside=0.0, layer='UVMap', overlap_measured=True):
    return {'uv_layer': layer, 'triangles': 12, 'world_area': 2.0, 'uv_area': 0.5, 'uv_per_m': uv_per_m, 'texture_px': texture_px,
            'overlap': overlap if overlap_measured else None, 'outside': outside,
            'overlap_note': None if overlap_measured else 'over the triangle budget'}


class TargetTests(unittest.TestCase):
    def test_valid_targets_pass(self):
        self.assertEqual(uv_report.validate_targets(copy.deepcopy(TARGETS)), TARGETS)

    def test_invalid_targets_are_refused(self):
        rule = TARGETS['targets'][0]
        cases = {'schema': {**TARGETS, 'schema': 'x'}, 'empty': {**TARGETS, 'targets': []},
                 'no limit': {**TARGETS, 'targets': [{'id': 'a', 'select': 'x'}]},
                 'order': {**TARGETS, 'targets': [{**rule, 'min_density': 4096}]},
                 'fraction': {**TARGETS, 'targets': [{**rule, 'max_overlap': 1.5}]},
                 'duplicate': {**TARGETS, 'targets': [rule, rule]}, 'key': {**TARGETS, 'targets': [{**rule, 'colour': 1}]}}
        for name, spec in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                uv_report.validate_targets(copy.deepcopy(spec))


class ClassifyTests(unittest.TestCase):
    def test_density_overlap_and_outside_findings(self):
        report = uv_report.classify(TARGETS, measured(**{
            'ext.prop.pot': mesh(),                                   # 0.5 UV/m * 1024 px = 512 px/m
            'ext.prop.crate': mesh(uv_per_m=0.1),                     # 102 px/m, below 256
            'ext.prop.tray': mesh(uv_per_m=4.0),                      # 4096 px/m, above 2048
            'ext.prop.can': mesh(overlap=0.3, outside=0.2),
            'ground': mesh(uv_per_m=0.1, texture_px=None)}))          # falls back to the rule's 1024 px: 102 px/m
        codes = {(rid, oid): f['codes'] for rid, r in report['targets'].items() for oid, f in r['findings'].items()}
        self.assertEqual(codes[('props', 'ext.prop.pot')], ['OK'])
        self.assertEqual(codes[('props', 'ext.prop.crate')], ['DENSITY_LOW'])
        self.assertEqual(codes[('props', 'ext.prop.tray')], ['DENSITY_HIGH'])
        self.assertEqual(codes[('props', 'ext.prop.can')], ['OVERLAP', 'OUTSIDE'])
        self.assertEqual(codes[('ground', 'ground')], ['OK'])
        self.assertAlmostEqual(report['targets']['ground']['findings']['ground']['density'], 102.4)
        self.assertFalse(report['passed'])

    def test_unmeasurable_values_are_findings_not_passes(self):
        report = uv_report.classify(TARGETS, measured(**{
            'ext.prop.pot': mesh(texture_px=None), 'ext.prop.big': mesh(overlap_measured=False), 'ext.prop.bare': mesh(layer=None),
            'ground': mesh()}))
        findings = report['targets']['props']['findings']
        self.assertEqual(findings['ext.prop.pot']['codes'], ['UNMEASURED'])
        self.assertEqual(findings['ext.prop.big']['codes'], ['UNMEASURED'])
        self.assertEqual(findings['ext.prop.bare']['codes'], ['NO_UV'])
        self.assertFalse(report['passed'])

    def test_a_selector_matching_nothing_is_a_finding(self):
        report = uv_report.classify(TARGETS, measured(**{'ext.prop.pot': mesh()}))
        self.assertEqual(report['targets']['ground']['findings'], {})
        self.assertEqual(report['targets']['ground']['codes'], ['MISSING_TARGET'])
        self.assertFalse(report['targets']['ground']['passed'])

    def test_measurement_for_another_definition_is_still_classified_on_its_own_terms(self):
        report = uv_report.classify(TARGETS, measured(**{'ext.prop.pot': mesh(), 'ground': mesh()}))
        self.assertTrue(report['passed'])
        self.assertEqual(report['schema'], 'dcc.uv.report.v1')


class ProjectTests(Fixture):
    def test_the_project_decision_supplies_the_targets(self):
        with self.assertRaisesRegex(ValueError, 'no uv_targets decision'):
            uv_report._definition(self.root, None)
        edit = self.begin(); native, obs = self.candidate()
        workflow.finish_edit(self.root, edit['edit'], native, obs, self.handoff, {'uv_targets': TARGETS})
        self.assertEqual(uv_report._definition(self.root, None), TARGETS)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            uv_report._definition(self.root, self.base / 'targets.json')


class CommandTests(unittest.TestCase):
    def test_cli_parses(self):
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'uv-report', '--help'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('--targets', proc.stdout)


if __name__ == '__main__':
    unittest.main()
