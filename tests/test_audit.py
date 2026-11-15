"""Portable checks for audit: profiles, evidence classes, selection and the CLI."""
import subprocess
import sys
import unittest

from dcc_harness import audit


def mesh(**changes):
    record = {'id': None, 'faces': 6, 'triangles': 12, 'islands': 1, 'closed_islands': 1, 'scale': [1.0, 1.0, 1.0], 'mirrored': False,
              'inconsistent_edges': 0, 'inward_closed_islands': 0, 'inward_closed_faces': 0, 'inward_open_islands': 0, 'inward_open_faces': 0,
              'boundary_edges': 0, 'nonmanifold_edges': 0, 'loose_edges': 0, 'loose_vertices': 0, 'zero_area_faces': 0, 'empty_slots': [],
              'empty_slot_faces': 0, 'uv_layers': 1, 'materials': [],
              'contact': {'parts': 1, 'floating': 0, 'unmeasured': 0, 'islands_as_one': False, 'examples': []}}
    return {**record, **changes}


def measured(objects, coincident=(), materials=None, complete=None):
    return {'schema': 'dcc.audit.measurement.v1', 'checkpoint_sha256': 'a' * 64, 'select': None, 'unit_scale': 1.0,
            'sizes': {'diagonal': 5.0, 'coincident': 0.00025, 'min_side': 0.0025, 'contact': 0.005, 'zero_area': 2.5e-11, 'volume': 1.25e-16},
            'objects': objects, 'materials': materials or {}, 'coincident': list(coincident),
            'complete': {'coincident': True, 'contact': True, 'contact_measured': True, **(complete or {})}, 'not_audited': {}}


def found(report):
    return {(f['code'], f['severity']) for f in report['findings']}


class ClassifyTests(unittest.TestCase):
    def test_clean_objects_pass_every_profile(self):
        for profile in audit.PROFILES:
            report = audit.classify(measured({'Crate': mesh(id='crate')}), profile)
            self.assertEqual((report['passed'], report['findings'], report['objects_audited']), (True, [], 1))

    def test_every_check_has_three_settings_a_cause_and_a_fix(self):
        for code, (severities, cause, fix) in audit.CHECKS.items():
            self.assertEqual(len(severities), len(audit.PROFILES), code)
            self.assertTrue(set(severities) <= {'error', 'warning', None} and cause and fix, code)

    def test_profiles_set_the_same_measurement_to_error_warning_or_skip(self):
        scene = measured({'Card': mesh(boundary_edges=4, contact={'parts': 1, 'floating': 1, 'unmeasured': 0, 'islands_as_one': False,
                                                                 'examples': [{'faces': 1, 'centre': [0, 0, 1], 'size': [1, 1, 0]}]})})
        self.assertEqual(found(audit.classify(scene, 'render')), {('FLOATING_PART', 'warning')})
        self.assertTrue(audit.classify(scene, 'render')['passed'])
        self.assertEqual(found(audit.classify(scene, 'game')), {('FLOATING_PART', 'warning'), ('OPEN_EDGES', 'warning')})
        report = audit.classify(scene, 'print')
        self.assertEqual(found(report), {('FLOATING_PART', 'error'), ('OPEN_EDGES', 'error')})
        self.assertFalse(report['passed'])
        self.assertEqual(report['counts'], {'error': 2, 'warning': 0})

    def test_each_object_measurement_maps_to_its_code(self):
        cases = {'NORMALS_INCONSISTENT': {'inconsistent_edges': 4}, 'NORMALS_INWARD': {'inward_closed_islands': 1, 'inward_closed_faces': 6},
                 'NON_MANIFOLD_EDGES': {'nonmanifold_edges': 4}, 'LOOSE_GEOMETRY': {'loose_vertices': 1}, 'ZERO_AREA_FACES': {'zero_area_faces': 1},
                 'SCALE_NEGATIVE': {'mirrored': True}, 'SCALE_UNAPPLIED': {'scale': [2.0, 2.0, 2.0]}, 'SCALE_NONUNIFORM': {'scale': [2.0, 1.0, 1.0]},
                 'EMPTY_SLOT_FACES': {'empty_slot_faces': 1, 'empty_slots': [1]}}
        for code, change in cases.items():
            with self.subTest(code):
                report = audit.classify(measured({'Crate': mesh(id='crate', **change)}), 'game')
                self.assertEqual([f['code'] for f in report['findings']], [code])
                finding = report['findings'][0]
                self.assertEqual((finding['object'], finding['name'], finding['evidence'], finding['permitted']),
                                 ('crate', 'Crate', 'native_measurement', 'repair'))

    def test_an_estimate_permits_inspection_and_is_never_an_error(self):
        for profile in audit.PROFILES:
            report = audit.classify(measured({'Room': mesh(inward_open_islands=1, inward_open_faces=5)}), profile)
            finding = next(f for f in report['findings'] if f['code'] == 'NORMALS_INWARD_ESTIMATE')
            self.assertEqual((finding['severity'], finding['evidence'], finding['permitted']), ('warning', 'bounds_only', 'inspect'))

    def test_coplanar_overlaps_name_both_objects_by_facing(self):
        pair = {'objects': ['Crate', 'Plate'], 'area': 0.18, 'planes': 2, 'point': [0.3, 0.3, 1.0], 'same_material': False}
        scene = measured({'Crate': mesh(id='crate'), 'Plate': mesh()}, [{**pair, 'facing': 'same'}, {**pair, 'facing': 'opposed'}])
        report = audit.classify(scene, 'render')
        self.assertEqual(found(report), {('COINCIDENT_FACES', 'error'), ('BACK_TO_BACK_FACES', 'warning')})
        self.assertEqual({(f['object'], f['other']) for f in report['findings']}, {('crate', 'Plate')})
        self.assertEqual(report['findings'][0]['code'], 'COINCIDENT_FACES')   # errors first
        matched = audit.classify(measured({'Crate': mesh(), 'Plate': mesh()}, [{**pair, 'facing': 'same', 'same_material': True}]), 'render')
        self.assertEqual(found(matched), {('COINCIDENT_FACES_MATCHED', 'warning')})

    def test_material_findings_need_a_user_and_no_uv(self):
        materials = {'Paint': {'uses_uv': True, 'data_srgb': [{'node': 'Relief', 'image': 'relief', 'colorspace': 'sRGB', 'feeds': ['Normal Map.Color']}]}}
        report = audit.classify(measured({'Crate': mesh(id='crate', materials=['Paint'], uv_layers=0)}, materials=materials), 'render')
        self.assertEqual(found(report), {('DATA_MAP_SRGB', 'error'), ('TEXTURE_WITHOUT_UV', 'error')})
        srgb = next(f for f in report['findings'] if f['code'] == 'DATA_MAP_SRGB')
        self.assertEqual((srgb['material'], srgb['objects'], srgb['object']), ('Paint', ['crate'], None))
        self.assertEqual(audit.classify(measured({'Crate': mesh(materials=['Paint'])}, materials=materials), 'print')['findings'], [])
        self.assertEqual(audit.classify(measured({'Crate': mesh()}, materials=materials), 'render')['findings'], [])

    def test_selection_reports_only_matching_objects(self):
        scene = measured({'Crate': mesh(id='ext.crate', inconsistent_edges=4), 'Ground': mesh(id='ground', zero_area_faces=1),
                          'Loose': mesh(nonmanifold_edges=2)},
                         [{'objects': ['Crate', 'Ground'], 'facing': 'same', 'area': 0.1, 'planes': 1, 'point': [0, 0, 0], 'same_material': False}])
        report = audit.classify(scene, 'render', 'ext.*')
        self.assertEqual({(f['code'], f['name']) for f in report['findings']}, {('NORMALS_INCONSISTENT', 'Crate'), ('COINCIDENT_FACES', 'Crate')})
        self.assertEqual(report['objects_audited'], 1)
        self.assertEqual([f['name'] for f in audit.classify(scene, 'render', 'Loose')['findings']], ['Loose'])   # no ID: matched by name
        self.assertEqual({f['code'] for f in audit.classify(scene, 'render', 'ground')['findings']}, {'ZERO_AREA_FACES', 'COINCIDENT_FACES'})

    def test_work_past_the_budget_is_reported_and_fails_only_the_print_profile(self):
        scene = measured({'Field': mesh(contact={'parts': 9, 'floating': 0, 'unmeasured': 3, 'islands_as_one': False, 'examples': []})},
                         complete={'coincident': False})
        self.assertEqual({(f['code'], f['check'], f['severity']) for f in audit.classify(scene, 'render')['findings']},
                         {('UNMEASURED', 'FLOATING_PART', 'warning'), ('UNMEASURED', 'COINCIDENT_FACES', 'warning')})
        self.assertFalse(audit.classify(scene, 'print')['passed'])

    def test_notes_say_what_was_not_checked(self):
        scene = measured({'Crate': mesh(contact=None)}, complete={'contact_measured': False})
        scene['not_audited'] = {'CURVE': 2}
        notes = audit.classify(scene)['notes']
        self.assertTrue(any('single connected part' in n for n in notes) and any('2 CURVE' in n for n in notes))

    def test_unknown_profiles_and_other_measurements_are_refused(self):
        with self.assertRaises(ValueError):
            audit.classify(measured({}), 'film')
        with self.assertRaises(ValueError):
            audit.classify({'schema': 'dcc.uv.measurement.v1'})


class CommandTests(unittest.TestCase):
    def test_cli_lists_the_command_and_its_profiles(self):
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'audit', '--help'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn('--profile', proc.stdout)
        self.assertIn('{render,game,print}', proc.stdout)

    def test_a_missing_source_is_refused_before_blender_starts(self):
        with self.assertRaises(ValueError):
            audit.audit_file('absent.blend', 'never-created', 'blender')
        with self.assertRaises(ValueError):
            audit.audit_file(__file__, 'never-created', 'blender', profile='film')


if __name__ == '__main__':
    unittest.main()
