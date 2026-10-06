"""Build disposable native fixtures and qualify the v2 extent observer.

Run with Blender --background --factory-startup --python-exit-code 1 --python
THIS_SCRIPT -- --repo REPOSITORY --out NEW_DIRECTORY. No live editor or existing
native file is modified. A failed attempt retains its files and receipt.
"""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Matrix


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def qualify(repo, out, receipt):
    require(bpy.app.background, 'Qualification requires a disposable background Blender process')
    require(not bpy.data.filepath, 'Start without a loaded native file; use --factory-startup')
    sys.path.insert(0, str(repo))
    import dcc_harness.continuity_blender as observer
    from dcc_harness.continuity_checks import evaluate_stage
    require(Path(observer.__file__).resolve().is_relative_to(repo), 'Observer imported outside --repo')
    names = ('continuity_blender.py', 'continuity_checks.py', 'blender.py', 'evidence.py', 'uv_guard.py')
    receipt['runtime_sha256'] = {name: sha256(repo / 'dcc_harness' / name) for name in names}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    fixtures = out / 'fixtures'
    fixtures.mkdir()
    observations = out / 'observations'
    observations.mkdir()
    material = bpy.data.materials.new('Qualification surface')
    material.use_nodes = True
    material['dcc_material_id'] = 'surface'
    vertices = [(-.04, -.045, -.22), (.04, -.045, -.22), (.04, .045, -.22), (-.04, .045, -.22),
                (-.04, -.045, .22), (.04, -.045, .22), (.04, .045, .22), (-.04, .045, .22)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for iid, points, polygons in (('subject', vertices, faces), ('empty', [], []),
                                 ('degenerate', [(0, 0, 0)] * 3, [(0, 1, 2)])):
        mesh = bpy.data.meshes.new(iid + '-mesh')
        mesh.from_pydata(points, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new(iid, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj['dcc_instance_id'] = iid
        obj['dcc_asset_id'] = iid
        obj.data.materials.append(material)
    subject = bpy.data.objects['subject']
    subject.rotation_euler = (0, 0, math.radians(17))
    subject.scale = (1.3, .7, 1.1)
    subject.location = (6, -5, .3)
    bpy.context.view_layer.update()

    def save(name):
        path = fixtures / (name + '.blend')
        require(not path.exists() and path.resolve().is_relative_to(out), 'Fixture must be a new owned path')
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        return path

    baseline_path = save('baseline')
    baseline_sha = sha256(baseline_path)
    baseline = observer.observe()
    write_json(observations / 'baseline.json', baseline)
    require(baseline['coverage'].get('continuity_observation') == 2, 'Expected v2 observer')
    require(baseline['coverage'].get('dimensions_measurement') == 'world_linear_extents_v2', 'Missing v2 extent declaration')
    require(not baseline['issues'], 'Baseline has observation issues')
    for iid in ('empty', 'degenerate'):
        require(baseline['objects'][iid]['dimensions'] == [0.0, 0.0, 0.0], iid + ' extents must be zero')
    receipt['edge_cases'] = {iid: {'dimensions': baseline['objects'][iid]['dimensions'],
                                 'vertices': baseline['objects'][iid]['vertices']} for iid in ('empty', 'degenerate')}
    contract = {'schema': 'dcc.continuity.contract.v1',
        'spec': {'schema': 'dcc.spec.v1', 'required': {'subject': {'type': 'MESH', 'min_triangles': 12}}},
        'allowed_object_prefixes': {'subject': ['matrix_world', 'bounds']}, 'allowed_new_prefixes': []}
    write_json(out / 'translation-contract.json', contract)
    receipt['cases'] = []
    for case in ('translation', 'far-translation', 'geometry', 'scale', 'rotation'):
        bpy.ops.wm.open_mainfile(filepath=str(baseline_path))
        obj = bpy.data.objects['subject']
        if case == 'translation':
            obj.location.y -= .35
        elif case == 'far-translation':
            obj.location = (1e6, -1e6, 1e6)
        elif case == 'geometry':
            obj.data.vertices[1].co.x += .05
            obj.data.update()
        elif case == 'scale':
            obj.scale.x *= 1.05
        else:
            obj.rotation_euler.z += math.radians(4)
        bpy.context.view_layer.update()
        path = save(case)
        observed = observer.observe()
        write_json(observations / (case + '.json'), observed)
        result = evaluate_stage(baseline, observed, contract)
        write_json(out / (case + '-check.json'), result)
        expected = case in ('translation', 'far-translation')
        require(result['passed'] == expected, case + ' gave the wrong preservation verdict')
        old, new = baseline['objects']['subject'], observed['objects']['subject']
        if expected:
            require(new['dimensions'] == old['dimensions'], case + ' changed translation-free extents')
            require(new['bounds'] != old['bounds'], case + ' did not change world bounds')
        else:
            require(new['dimensions'] != old['dimensions'], case + ' did not change extents')
        if case == 'geometry':
            require(new['source_mesh_hash'] != old['source_mesh_hash'], 'Authored geometry edit was not measured')
        receipt['cases'].append({'case': case, 'expected_pass': expected, 'passed': result['passed'],
            'native_sha256': sha256(path), 'dimensions': new['dimensions'],
            'check_sha256': sha256(out / (case + '-check.json'))})
        require(sha256(baseline_path) == baseline_sha, 'Baseline fixture changed')

    # Bulk mesh writes preserve IEEE NaN. RNA coordinate setters can clamp Inf;
    # always verify the actual injected native value before asserting rejection.
    bpy.ops.wm.open_mainfile(filepath=str(baseline_path))
    mesh = bpy.data.objects['subject'].data
    coordinates = array.array('f', [0] * (len(mesh.vertices) * 3))
    mesh.vertices.foreach_get('co', coordinates)
    coordinates[-3] = float('nan')
    mesh.vertices.foreach_set('co', coordinates)
    mesh.update()
    bpy.context.view_layer.update()
    require(math.isnan(float(mesh.vertices[-1].co.x)), 'Later-vertex NaN injection did not persist')
    invalid_path = save('later-vertex-nan')
    require(math.isnan(float(mesh.vertices[-1].co.x)), 'Saving altered the NaN injection')
    try:
        observer.observe()
    except (ValueError, OverflowError) as error:
        receipt['nonfinite_case'] = {'actual_injection_verified': True, 'rejected': True,
            'exception': type(error).__name__, 'message': str(error), 'native_sha256': sha256(invalid_path)}
    else:
        raise AssertionError('Later-vertex NaN was accepted')
    require(sha256(baseline_path) == baseline_sha, 'Baseline fixture changed during negative test')
    require(all(sha256(repo / 'dcc_harness' / name) == sha for name, sha in receipt['runtime_sha256'].items()),
            'Runtime source changed during qualification')
    receipt.update(passed=True, baseline_sha256=baseline_sha, baseline_unchanged=True,
                   runtime_sources_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'dcc.continuity.extent_qualification.v1', 'passed': False,
        'blender': bpy.app.version_string, 'script_sha256': sha256(Path(__file__).resolve()),
        'command': sys.argv, 'background': bpy.app.background,
        'limits': 'Disposable structural fixtures only. No live editor, existing native file, beauty render, artist score, or silent v1 history migration.'}
    try:
        qualify(repo, out, receipt)
    except Exception as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        receipt['traceback'] = traceback.format_exc()
        write_json(out / 'qualification.json', receipt)
        raise
    write_json(out / 'qualification.json', receipt)
    print('CONTINUITY_EXTENT_QUALIFICATION_PASS', str(out / 'qualification.json'))


if __name__ == '__main__':
    main()
