"""Native qualification of deliver-glb: export, fresh reimport, comparison and checkpoint binding.

Builds the relations probe's bench scenes and delivers the flat bench. It delivers the 0.6.0
comparison project's active checkpoint with --project, and checks that the GLB of a copy with
the bench top moved 5 cm fails against the original manifest with BOUNDS. It also checks that a
truncated GLB fails to import and that a project delivery of a file that is not one of its
checkpoints is refused.
"""
import shutil

from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
from dcc_harness import delivery
from dcc_harness.evidence import file_hash, read_json
from dcc_harness.native import run_worker

FIXTURE = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project'
q.blender('scenes.log', '--python', REPO / 'scripts/relations_native_probe.py', '--', '--out', out / 'scenes')
flat = out / 'scenes/flat.blend'
summary = {}

# The flat bench: every mesh delivered, camera and light listed as not delivered.
plain = q.cli('deliver-glb', flat, '--blender', a.blender, '--output-dir', out / 'deliver-flat')
assert plain['passed'] and plain['comparison']['matched'] == 6, plain['comparison']
skipped = {(x['id'], x['type']) for x in plain['comparison']['not_exported']}
assert skipped == {('review.camera', 'CAMERA'), ('light.sun', 'LIGHT')}, skipped
summary['flat'] = {'matched': 6, 'not_exported': sorted(skipped), 'glb_bytes': plain['glb']['bytes'], 'exporter': plain['exporter']}

# The comparison project's active checkpoint, bound to the project.
project = out / 'project'
shutil.copytree(FIXTURE, project)
active = q.cli('next', project)['active']
bound = q.cli('deliver-glb', active['checkpoint'], '--blender', a.blender, '--output-dir', out / 'deliver-project', '--project', project)
assert bound['passed'] and bound['checkpoint']['checkpoint_id'] == active['id'] and bound['checkpoint']['active'], bound['comparison']
summary['project'] = {'checkpoint': active['id'], 'matched': bound['comparison']['matched'],
                      'not_exported': [x['id'] for x in bound['comparison']['not_exported']]}
summary['refused_non_checkpoint'] = q.refused(('deliver-glb', flat, '--blender', a.blender, '--output-dir', out / 'deliver-refused',
                                               '--project', project), 'not a checkpoint of this project')

# A copy with the bench top moved 5 cm: its GLB must not match the original export record.
mover = out / 'move_top.py'
mover.write_text("import bpy\n"
                 "obj = next(o for o in bpy.data.objects if o.get('dcc_instance_id') == 'bench.top')\n"
                 "obj.location.z += 0.05\n"
                 f"bpy.ops.wm.save_as_mainfile(filepath={str(out / 'moved.blend')!r})\n", encoding='utf-8')
q.blender('move.log', flat, '--python', mover)
moved = q.cli('deliver-glb', out / 'moved.blend', '--blender', a.blender, '--output-dir', out / 'deliver-moved')
assert moved['passed'], 'the moved copy is itself a faithful delivery'
against = delivery.compare(read_json(out / 'deliver-flat/export.json'), read_json(out / 'deliver-moved/reimport/import.json'))
codes = [(f['id'], f['code']) for f in against['findings']]
assert codes == [('bench.top', 'BOUNDS')], codes
summary['moved_against_original'] = codes

# A truncated GLB fails to import.
broken = out / 'truncated'
broken.mkdir()
data = (out / 'deliver-flat/delivery.glb').read_bytes()
(broken / 'delivery.glb').write_bytes(data[:len(data) // 2])
try:
    run_worker(a.blender, broken, delivery.WORKER, 'reimport', {'glb': str(broken / 'delivery.glb'),
               'glb_sha256': file_hash(broken / 'delivery.glb'), 'out': str(broken)})
except RuntimeError as exc:
    summary['truncated'] = str(exc).split(';')[0]
else:
    raise AssertionError('A truncated GLB imported')
assert not (broken / 'import.json').exists()
q.finish(summary)
