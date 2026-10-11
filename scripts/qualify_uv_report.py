"""Native qualification of uv-report: texel density, UV overlap and UVs outside the unit square.

Builds 2 m x 2 m planes whose UVs are known exactly, all using a 1024-pixel image:
  ext.good     full unit square: 0.5 UV/m, 512 px/m, no overlap, nothing outside
  ext.small    unit square scaled to 0.1: 51.2 px/m, too low
  ext.stacked  4 x 4 grid with every face mapped to the whole square: overlapping
  ext.outside  unit square shifted by +1 in U: entirely outside
  ext.bare     no UV layer
  ext.fine     a 64 x 64 grid unwrapped to the unit square: small UV triangles, no overlap
  ext.folded   the same grid with both halves folded onto the top half of the square: overlapping
and checks each finding and the production garden's timing.
"""
from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
from dcc_harness.evidence import read_json, write_json

builder = out / 'build.py'
builder.write_text(
    "import bpy, sys\n"
    "target = sys.argv[sys.argv.index('--') + 1]\n"
    "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
    "image = bpy.data.images.new('checker', 1024, 1024); image.pack()\n"
    "mat = bpy.data.materials.new('paint'); mat.use_nodes = True\n"
    "tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = image\n"
    "def plane(iid, cuts=0):\n"
    "    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cuts + 1, y_subdivisions=cuts + 1, size=2)\n"
    "    obj = bpy.context.object; obj.name = iid; obj['dcc_instance_id'] = iid; obj.data.materials.append(mat)\n"
    "    return obj\n"
    "def set_uv(obj, fn):\n"
    "    layer = obj.data.uv_layers.active\n"
    "    for poly in obj.data.polygons:\n"
    "        corners = [(0, 0), (1, 0), (1, 1), (0, 1)]\n"
    "        for k, li in enumerate(poly.loop_indices):\n"
    "            layer.data[li].uv = fn(obj.data.vertices[obj.data.loops[li].vertex_index].co, corners[k % 4])\n"
    "good = plane('ext.good'); set_uv(good, lambda co, c: ((co.x + 1) / 2, (co.y + 1) / 2))\n"
    "small = plane('ext.small'); set_uv(small, lambda co, c: ((co.x + 1) / 20, (co.y + 1) / 20))\n"
    "stacked = plane('ext.stacked', cuts=3); set_uv(stacked, lambda co, c: c)\n"
    "outside = plane('ext.outside'); set_uv(outside, lambda co, c: ((co.x + 1) / 2 + 1, (co.y + 1) / 2))\n"
    "bare = plane('ext.bare'); bare.data.uv_layers.remove(bare.data.uv_layers[0])\n"
    "fine = plane('ext.fine', cuts=63); set_uv(fine, lambda co, c: ((co.x + 1) / 2, (co.y + 1) / 2))\n"
    "folded = plane('ext.folded', cuts=63); set_uv(folded, lambda co, c: ((co.x + 1) / 2, abs(co.y) / 2 + 0.5))\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target)\n", encoding='utf-8')
q.blender('build.log', '--python', builder, '--', out / 'uv.blend')
write_json(out / 'targets.json', {'schema': 'dcc.uv.targets.v1', 'targets': [
    {'id': 'props', 'select': 'ext.*', 'min_density': 256, 'max_overlap': 0.02, 'max_outside': 0.0}]})
report = q.cli('uv-report', out / 'uv.blend', '--blender', a.blender, '--output-dir', out / 'report', '--targets', out / 'targets.json', expect=1)
measured = read_json(out / 'report/measurement.json')['objects']
findings = report['targets']['props']['findings']
codes = {i: f['codes'] for i, f in findings.items()}
assert codes == {'ext.good': ['OK'], 'ext.small': ['DENSITY_LOW'], 'ext.stacked': ['OVERLAP'], 'ext.outside': ['OUTSIDE'], 'ext.bare': ['NO_UV'],
                 'ext.fine': ['OK'], 'ext.folded': ['OVERLAP']}, codes
assert findings['ext.fine']['overlap'] == 0.0 and 0.9 < findings['ext.folded']['overlap'] <= 1.0, findings
assert abs(findings['ext.good']['density'] - 512) < 0.01 and abs(findings['ext.small']['density'] - 51.2) < 0.01, findings
assert findings['ext.good']['overlap'] == 0.0 and findings['ext.stacked']['overlap'] > 0.9, findings
assert measured['ext.outside']['outside'] == 1.0 and measured['ext.good']['texture_px'] == 1024, measured
summary = {'codes': codes, 'good': {k: findings['ext.good'][k] for k in ('density', 'overlap', 'outside')},
           'stacked_overlap': findings['ext.stacked']['overlap'], 'small_density': findings['ext.small']['density'],
           'fine_overlap': findings['ext.fine']['overlap'], 'folded_overlap': findings['ext.folded']['overlap']}

# Timing and plausibility on the production garden (1,285 meshes), with permissive limits.
production = REPO / 'runs/shed-production-2026-10-05/project/checkpoints/000009/checkpoint.blend'
if production.is_file():
    write_json(out / 'garden.json', {'schema': 'dcc.uv.targets.v1', 'targets': [{'id': 'all', 'select': '*', 'max_outside': 1.0}]})
    import time
    started = time.time()
    garden = q.cli('uv-report', production, '--blender', a.blender, '--output-dir', out / 'garden', '--targets', out / 'garden.json', expect=None)
    objects = read_json(out / 'garden/measurement.json')['objects']
    summary['production'] = {'seconds': round(time.time() - started), 'meshes': len(objects),
                             'overlap_measured': sum(o['overlap'] is not None for o in objects.values()),
                             'no_uv': sum(o['uv_layer'] is None for o in objects.values())}
q.finish(summary)
