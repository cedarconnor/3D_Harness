"""Native regression gate for physical delivery/support units; all outputs are disposable."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--blender', required=True)
p.add_argument('--runtime', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
sys.path.insert(0, a.runtime)
from dcc_harness import delivery, relations
from dcc_harness.evidence import file_hash, read_json, write_json

out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
script = out / 'fixtures.py'
script.write_text('''import bpy
from pathlib import Path
import sys
out = Path(sys.argv[-1])
for scale in (1., .01, .1):
    for gap in (.00005, -.002):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = scale
        bpy.ops.mesh.primitive_plane_add(size=10/scale)
        bpy.context.object['dcc_instance_id'] = 'support'
        bpy.ops.mesh.primitive_cube_add(size=1/scale, location=(1/scale, 2/scale, (.5+gap)/scale))
        cube = bpy.context.object
        cube['dcc_instance_id'] = 'subject'
        parent = bpy.data.objects.new('Parent', None)
        scene.collection.objects.link(parent)
        parent['dcc_instance_id'] = 'parent'
        parent.location.x = .25/scale
        cube.parent = parent
        bpy.ops.wm.save_as_mainfile(filepath=str(out / (str(scale)+'_'+str(gap)+'.blend')))
''', encoding='utf-8')
with (out / 'fixtures.log').open('x') as log:
    subprocess.run([a.blender, '--background', '--offline-mode', '--factory-startup', '--disable-autoexec',
                    '--python-exit-code', '1', '--python', str(script), '--', str(out)], stdout=log, stderr=subprocess.STDOUT, check=True)
spec = {'schema': 'dcc.relations.v1', 'relations': [{'id': 'support', 'kind': 'supported_by', 'subjects': ['subject'],
        'support': ['support'], 'max_gap': .001, 'max_penetration': .001, 'footprint': .001}]}
write_json(out / 'relations.json', spec)
results = []
for scale in (1., .01, .1):
    for gap in (.00005, -.002):
        source = out / f'{scale}_{gap}.blend'
        sha = file_hash(source)
        folder = out / f'measure-{scale}-{gap}'
        relations.measure_file(source, folder, a.blender, spec=out / 'relations.json')
        measured = read_json(folder / 'measurement.json')['relations']['support']['subjects']['subject']
        assert abs(measured['min_distance'] - gap) < 2e-6, (scale, gap, measured)
        classified = relations.classify(spec, read_json(folder / 'measurement.json'))
        assert classified['passed'] == (gap > 0), classified
        destination = out / f'export-{scale}-{gap}'
        if scale != 1:
            try:
                delivery.deliver(source, destination, a.blender)
            except RuntimeError:
                assert 'unit scale' in (destination / 'export.log').read_text()
                assert not (destination / 'delivery.glb').exists()
            else:
                raise AssertionError('Non-unit scale must not be certified without conversion')
        else:
            result = delivery.deliver(source, destination, a.blender)
            assert result['passed'], result
            data = (destination / 'delivery.glb').read_bytes()
            length = struct.unpack_from('<I', data, 12)[0]
            gltf = json.loads(data[20:20+length])
            # Independent exported accessor extent: a one metre cube.
            accessors = [gltf['accessors'][m['primitives'][0]['attributes']['POSITION']] for m in gltf['meshes']]
            assert any(abs(max(x['max'][i]-x['min'][i] for i in range(3)) - 1) < 1e-6 for x in accessors)
        assert file_hash(source) == sha
        results.append({'scale': scale, 'gap_m': gap, 'passed': True})
write_json(out / 'VERIFICATION.json', {'passed': True, 'cases': results})
print(json.dumps(results))
