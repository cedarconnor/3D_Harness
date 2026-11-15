"""Geometry defect audit of a saved file: stable issue codes, each with a cause and a suggested fix.

A fresh background Blender measures the render-visible meshes and never saves. Portable code turns
the numbers into findings under a profile, which sets each check to an error, a warning or skip.
Evidence follows the relations vocabulary: a native measurement permits repair, and an estimate
from an island's shape alone (`bounds_only`) permits inspection and is never an error. Like
uv-report it sits beside the observation and binds to the file's hash.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

from .continuity import _plain
from .evidence import file_hash, read_json, write_json
from .native import run_worker

WORKER = Path(__file__).with_name('_audit_blender.py')
SHOWN = 40  # findings printed; the report file holds them all
LIMITS = ('Evaluated, render-visible mesh objects only: not curves, text, volumes, or geometry that modifiers instance. '
          'Coplanar overlap and contact are measured between connected islands, to tolerances scaled by the bounding diagonal. '
          'It finds defects in the geometry; it does not say the model looks right.')

# code: (render, game, print), cause, fix
CHECKS = {
    'NORMALS_INCONSISTENT': (('error', 'error', 'error'),
                             'Neighbouring faces disagree about which side is out, so some faces are flipped.',
                             'Recalculate normals outside on the object, then check the reported count is zero.'),
    'NORMALS_INWARD': (('error', 'error', 'error'),
                       'A closed part has all its faces pointing inward.',
                       'Flip the normals of that part, or recalculate normals outside.'),
    'NORMALS_INWARD_ESTIMATE': (('warning', 'warning', 'warning'),
                                'An open part\'s faces mostly point toward its own centre. This is an estimate from its shape; '
                                'a room interior or a sky dome is meant to face inward.',
                                'Look at it with face orientation shown before changing anything.'),
    'OPEN_EDGES': ((None, 'warning', 'error'),
                   'The mesh has boundary edges, so it is not a closed surface.',
                   'Fill or bridge the holes, or give the part thickness.'),
    'NON_MANIFOLD_EDGES': (('warning', 'error', 'error'),
                           'An edge is shared by more than two faces, usually an interior face or duplicated geometry.',
                           'Delete the interior or duplicate faces, then merge by distance.'),
    'LOOSE_GEOMETRY': (('warning', 'error', 'error'),
                       'Vertices or edges belong to no face.',
                       'Delete loose geometry.'),
    'ZERO_AREA_FACES': (('warning', 'error', 'error'),
                        'Faces have no area.',
                        'Dissolve degenerate geometry or merge by distance.'),
    'COINCIDENT_FACES': (('error', 'error', 'error'),
                         'Faces of two parts lie in the same plane, face the same way and overlap, so they will flicker (z-fighting).',
                         'Move one part off the plane, delete the hidden face, or join the parts and remove the doubled surface.'),
    'COINCIDENT_FACES_MATCHED': (('warning', 'warning', 'warning'),
                                 'Faces of two parts overlap in one plane, facing the same way, and both parts use the same materials, '
                                 'so the flicker does not show until a material, a bevel or the lighting differs.',
                                 'Join the parts or trim the overlap if either will be textured or exported separately.'),
    'BACK_TO_BACK_FACES': (('warning', 'warning', 'error'),
                           'Faces of two parts lie in the same plane facing opposite ways, and at least one part is an open sheet.',
                           'Give the sheet thickness or offset it; if it is a duplicate, delete it.'),
    'FLOATING_PART': (('warning', 'warning', 'error'),
                      'A connected part has no other surface within the contact distance.',
                      'Move it into contact, join it to what should carry it, or delete it if it is stray geometry.'),
    'SCALE_UNAPPLIED': ((None, 'warning', None),
                        'The object carries a uniform scale that is not 1.',
                        'Apply the scale.'),
    'SCALE_NONUNIFORM': (('warning', 'error', None),
                         'The object carries a non-uniform scale, which distorts bevels, procedural textures and exports.',
                         'Apply the scale.'),
    'SCALE_NEGATIVE': (('warning', 'error', 'error'),
                       'The object is mirrored by a negative scale; its normals flip when the scale is applied or exported.',
                       'Apply the scale, then recalculate normals outside.'),
    'EMPTY_SLOT_FACES': (('error', 'error', None),
                         'Faces are assigned to a material slot that holds no material.',
                         'Assign a material to the slot or move the faces to a filled slot.'),
    'DATA_MAP_SRGB': (('error', 'error', None),
                      'An image used only as data (normal, roughness, metallic, height) is tagged sRGB, so its values are altered.',
                      'Set the image\'s colour space to Non-Color.'),
    'TEXTURE_WITHOUT_UV': (('error', 'error', None),
                           'A material maps an image by UV, but the mesh has no UV layer.',
                           'Unwrap the mesh, or map the image by generated or object coordinates.'),
    'UNMEASURED': (('warning', 'warning', 'error'),
                   'A check stopped at its work budget, so part of the file was not measured.',
                   'Audit a smaller selection with --select.'),
}
PROFILES = ('render', 'game', 'print')
ESTIMATES = {'NORMALS_INWARD_ESTIMATE'}


def _matches(name, record, select):
    return select is None or fnmatch.fnmatchcase(record.get('id') or name, select)


def classify(measurement, profile='render', select=None):
    """Findings for one profile. Passed means no error; warnings are listed and do not fail."""
    if profile not in PROFILES:
        raise ValueError('Profile must be one of: ' + ', '.join(PROFILES))
    if measurement.get('schema') != 'dcc.audit.measurement.v1':
        raise ValueError('Not an audit measurement')
    column = PROFILES.index(profile)
    objects = measurement['objects']
    findings = []

    def add(code, name=None, **values):
        severities, cause, fix = CHECKS[code]
        if severities[column] is None:
            return
        estimate = code in ESTIMATES
        findings.append({'code': code, 'severity': severities[column], 'object': objects[name]['id'] if name else None, 'name': name,
                         'evidence': 'bounds_only' if estimate else 'native_measurement', 'permitted': 'inspect' if estimate else 'repair',
                         **values, 'cause': cause, 'fix': fix})

    for name, r in sorted(objects.items()):
        if not _matches(name, r, select):
            continue
        if r['inconsistent_edges']:
            add('NORMALS_INCONSISTENT', name, edges=r['inconsistent_edges'])
        if r['inward_closed_islands']:
            add('NORMALS_INWARD', name, parts=r['inward_closed_islands'], faces=r['inward_closed_faces'])
        if r['inward_open_islands']:
            add('NORMALS_INWARD_ESTIMATE', name, parts=r['inward_open_islands'], faces=r['inward_open_faces'])
        if r['boundary_edges']:
            add('OPEN_EDGES', name, edges=r['boundary_edges'])
        if r['nonmanifold_edges']:
            add('NON_MANIFOLD_EDGES', name, edges=r['nonmanifold_edges'])
        if r['loose_edges'] or r['loose_vertices']:
            add('LOOSE_GEOMETRY', name, edges=r['loose_edges'], vertices=r['loose_vertices'])
        if r['zero_area_faces']:
            add('ZERO_AREA_FACES', name, faces=r['zero_area_faces'])
        if r['mirrored']:
            add('SCALE_NEGATIVE', name, scale=r['scale'])
        if max(abs(s - 1) for s in r['scale']) > 1e-4:
            uniform = max(r['scale']) - min(r['scale']) <= 1e-4 * max(r['scale'])
            add('SCALE_UNAPPLIED' if uniform else 'SCALE_NONUNIFORM', name, scale=r['scale'])
        if r['empty_slot_faces']:
            add('EMPTY_SLOT_FACES', name, faces=r['empty_slot_faces'], slots=r['empty_slots'])
        if not r['uv_layers']:
            mapped = [m for m in r['materials'] if measurement['materials'][m]['uses_uv']]
            if mapped:
                add('TEXTURE_WITHOUT_UV', name, materials=mapped)
        contact = r.get('contact')
        if contact and contact['floating']:
            add('FLOATING_PART', name, parts=contact['floating'], of=contact['parts'], examples=contact['examples'])
        if contact and contact['unmeasured']:
            add('UNMEASURED', name, check='FLOATING_PART', parts=contact['unmeasured'])
    for entry in measurement['coincident']:
        first, second = entry['objects']
        if not (_matches(first, objects[first], select) or _matches(second, objects[second], select)):
            continue
        code = 'BACK_TO_BACK_FACES' if entry['facing'] != 'same' else 'COINCIDENT_FACES_MATCHED' if entry['same_material'] else 'COINCIDENT_FACES'
        add(code, first, other=objects[second]['id'] or second,
            area=entry['area'], planes=entry['planes'], point=entry['point'])
    if not measurement['complete']['coincident']:
        add('UNMEASURED', check='COINCIDENT_FACES')
    for material, facts in sorted(measurement['materials'].items()):
        users = sorted(objects[n]['id'] or n for n, r in objects.items() if material in r['materials'] and _matches(n, r, select))
        for image in facts['data_srgb'] if users else []:
            add('DATA_MAP_SRGB', material=material, objects=users, image=image['image'], node=image['node'], feeds=image['feeds'])
    findings.sort(key=lambda f: (f['severity'] != 'error', f['code'], f['name'] or '', f.get('material', '')))
    counts = {level: sum(f['severity'] == level for f in findings) for level in ('error', 'warning')}
    by_code = {}
    for f in findings:
        by_code[f['code']] = by_code.get(f['code'], 0) + 1
    audited = sum(_matches(n, r, select) for n, r in objects.items())
    notes = []
    if not measurement['complete']['contact_measured']:
        notes.append('Contact was not checked: the file has a single connected part.')
    if measurement['not_audited']:
        notes.append('Not audited: ' + ', '.join(f'{count} {kind}' for kind, count in sorted(measurement['not_audited'].items())))
    return {'schema': 'dcc.audit.report.v1', 'profile': profile, 'passed': counts['error'] == 0, 'counts': counts, 'by_code': by_code,
            'objects_audited': audited, 'tolerances': {k: measurement['sizes'][k] for k in ('diagonal', 'coincident', 'contact')},
            'findings': findings, 'notes': notes, 'limits': LIMITS}


def audit_file(source, out, blender, *, profile='render', select=None):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    if profile not in PROFILES:
        raise ValueError('Profile must be one of: ' + ', '.join(PROFILES))
    if select is not None and (not isinstance(select, str) or not select):
        raise ValueError('Select must be a nonempty ID glob')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    run_worker(blender, folder, WORKER, 'measure', {'source': descriptor, 'out': str(folder.resolve()), 'select': select})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during the audit; inspect retained outputs')
    measurement = read_json(folder / 'measurement.json')
    if measurement.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Measurement is not bound to the source bytes')
    report = {**classify(measurement, profile, select), 'source': descriptor}
    write_json(folder / 'report.json', report)
    shown = report['findings'][:SHOWN]
    return {**report, 'findings': shown, 'omitted': len(report['findings']) - len(shown), 'report': str(folder / 'report.json'),
            'artistic_acceptance': 'not_assessed'}
