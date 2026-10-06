"""Run in disposable background Blender; compare installed observer versions.

No artist file is saved. Fixture mode writes only beneath a new output folder.
Benchmark mode opens an immutable checkpoint and alternates runtime order.
"""
import argparse
import gc
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import bpy


def load(name, root):
    package = Path(root).resolve() / 'dcc_harness'
    spec = importlib.util.spec_from_file_location(name, package / '__init__.py',
                                                 submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return importlib.import_module(name + '.continuity_blender')


def comparable(obs):
    return {k: v for k, v in obs.items() if k != 'observed_at'}


def differences(a, b, path='', limit=12):
    found = []
    if type(a) is not type(b):
        return [path + ': type']
    if isinstance(a, dict):
        if set(a) != set(b):
            found.append(path + ': keys')
        for key in sorted(a.keys() & b.keys()):
            found += differences(a[key], b[key], path + '/' + str(key), limit)
            if len(found) >= limit:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            return [path + ': length']
        for index, (av, bv) in enumerate(zip(a, b)):
            if av != bv:
                found += differences(av, bv, path + '/' + str(index), limit)
                if len(found) >= limit:
                    break
    elif a != b:
        found.append(path + ': ' + repr(a)[:90] + ' != ' + repr(b)[:90])
    return found[:limit]


p = argparse.ArgumentParser()
p.add_argument('--baseline', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--out', required=True)
p.add_argument('--source')
p.add_argument('--pairs', type=int, default=3)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
old = load('baseline_harness', a.baseline)
new = load('candidate_harness', a.candidate)
evidence = importlib.import_module('candidate_harness.evidence')
write_json, file_hash = evidence.write_json, evidence.file_hash
runtime = {label: {'path': str(Path(module.__file__).parent),
                  'modules': {path.name: file_hash(path) for path in Path(module.__file__).parent.glob('*.py')}}
           for label, module in [('baseline', old), ('candidate', new)]}

if a.source:
    source = Path(a.source).resolve()
    sha = file_hash(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    pairs = []
    for index in range(a.pairs):
        results, seconds = {}, {}
        order = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        for label in order:
            gc.collect()
            started = time.perf_counter()
            results[label] = (old if label == 'baseline' else new).observe()
            seconds[label] = time.perf_counter() - started
        delta = differences(comparable(results['baseline']), comparable(results['candidate']))
        report = {'index': index, 'order': order, 'seconds': seconds,
                  'exact_equivalent_except_observed_at': not delta, 'differences': delta,
                  'revisions': {k: v['revision'] for k, v in results.items()},
                  'native_dirty': {k: v['native_dirty'] for k, v in results.items()}}
        write_json(out / f'pair-{index}.json', report)
        pairs.append(report)
        if delta:
            for label, obs in results.items():
                write_json(out / f'pair-{index}-{label}.json', obs, compact_observation=True)
        del results
    passed = all(pair['exact_equivalent_except_observed_at'] and
                 not any(pair['native_dirty'].values()) for pair in pairs)
    write_json(out / 'report.json', {'passed': passed, 'pairs': pairs, 'runtime': runtime,
               'source_sha256': sha, 'source_unchanged': file_hash(source) == sha, 'native_saves': 0,
               'blender': bpy.app.version_string, 'script_sha256': file_hash(__file__),
               'limits': 'One saved scene, alternating same-process observations. Timing excludes JSON writes and comparisons; not a general speed guarantee.'})
    assert file_hash(source) == sha and passed, 'Retain mismatch evidence; do not loosen comparison'
else:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new('Shared fixture mesh')
    mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),
                      (-1,-1,2),(1,-1,2),(1,1,2),(-1,1,2)], [],
                     [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    uv = mesh.uv_layers.new(name='Fixture UV')
    for index, entry in enumerate(uv.data):
        entry.uv = [(0,0),(1,0),(1,1),(0,1)][index % 4]
    mat = bpy.data.materials.new('Shared fixture shader')
    mat.use_nodes = True
    mat['dcc_material_id'] = 'material.shared'
    image_path = out / 'external.png'
    generated = bpy.data.images.new('Fixture generated', width=4, height=4)
    generated.filepath_raw = str(image_path)
    generated.file_format = 'PNG'
    generated.save()
    bpy.data.images.remove(generated)
    image = bpy.data.images.load(str(image_path))
    mat.node_tree.nodes.new('ShaderNodeTexImage').image = image
    mesh.materials.append(mat)
    objects = []
    for index, name in enumerate(('A', 'B', 'C', 'D')):
        obj = bpy.data.objects.new(name, mesh if index != 2 else mesh.copy())
        bpy.context.scene.collection.objects.link(obj)
        obj['dcc_instance_id'] = name
        obj['dcc_asset_id'] = 'shared.asset' if index != 2 else 'distinct.asset'
        obj.location.x = index * 3
        objects.append(obj)
    modifier = objects[1].modifiers.new('Per-object bevel', 'BEVEL')
    modifier.width = .17
    modifier.segments = 2
    distinct_mat = mat.copy()
    distinct_mat.name = 'Distinct fixture shader'
    distinct_mat['dcc_material_id'] = 'material.distinct'
    distinct_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .77
    objects[2].data.materials[0] = distinct_mat
    bpy.context.view_layer.update()
    source = out / 'fixture.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    sha = file_hash(source)
    checks = []

    def pair(name):
        before, after = old.observe(), new.observe()
        delta = differences(comparable(before), comparable(after))
        checks.append({'case': name, 'exact_equivalent_except_observed_at': not delta,
                       'differences': delta, 'revision': after['revision']})
        assert not delta, (name, delta)
        return after

    start = pair('shared data with per-object modifiers and transforms')
    assert start['objects']['A']['source_mesh_hash'] == start['objects']['B']['source_mesh_hash']
    assert start['objects']['A']['geometry_hash'] != start['objects']['B']['geometry_hash']
    assert start['objects']['A']['evaluated_uv_values'] != start['objects']['B']['evaluated_uv_values']
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .23
    shader = pair('shader edit between calls')
    assert shader['materials']['material.shared'] != start['materials']['material.shared']
    mesh.vertices[6].co.z += .11
    mesh.update()
    geometry = pair('shared source geometry edit between calls')
    for key in ('A', 'B', 'D'):
        assert geometry['objects'][key]['source_mesh_hash'] != shader['objects'][key]['source_mesh_hash']
    assert geometry['objects']['C']['source_mesh_hash'] == shader['objects']['C']['source_mesh_hash']
    mesh.uv_layers[0].data[0].uv.x += .125
    mesh.update()
    changed_uv = pair('authored UV edit between calls')
    for key in ('A', 'B', 'D'):
        assert changed_uv['objects'][key]['source_uv_hash'] != geometry['objects'][key]['source_uv_hash']
    with image_path.open('ab') as stream:
        stream.write(b'\nqualification texture file changed\n')
    external = pair('external texture bytes changed between calls')
    assert external['materials']['material.shared'] != changed_uv['materials']['material.shared']
    distinct_mat['dcc_material_id'] = 'material.shared'
    collision = pair('distinct material datablocks have a duplicate caller ID')
    assert 'Duplicate material ID: material.shared' in collision['issues']
    assert collision['materials']['material.shared']['name'] == mat.name
    distinct_mat['dcc_material_id'] = 'material.distinct'
    clean = pair('duplicate ID repaired')
    clean_digest = evidence.digest(comparable(clean))
    clean['objects']['A']['evaluated_uv_values']['Fixture UV'][0] = 12345
    clean['materials']['material.shared']['graph']['nodes'].clear()
    fresh = pair('caller changes old returned observation')
    assert evidence.digest(comparable(fresh)) == clean_digest
    assert file_hash(source) == sha
    write_json(out / 'report.json', {'passed': True, 'checks': checks, 'runtime': runtime,
               'fixture_source_sha256': sha, 'saved_fixture_unchanged': True, 'native_saves': 1,
               'blender': bpy.app.version_string, 'script_sha256': file_hash(__file__),
               'limits': 'Native differential checks in a disposable fixture. Unsaved edits are observed, never represented as publishable checkpoints.'})
print('OBSERVER_QUALIFIED', str(out))
