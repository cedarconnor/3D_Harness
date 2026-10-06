"""Create new diagnostic copies; never save over the source or touch live Blender."""
import argparse
from pathlib import Path
import sys
import bpy

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
seat = next(o for o in bpy.context.scene.objects if o.get('dcc_instance_id') == 'hero.seat')
for vertex in seat.data.vertices:
    vertex.co.x *= 2.1 / 1.9
stone = next(m for m in seat.data.materials if m.get('dcc_material_id') == 'stone') if any(m.get('dcc_material_id') == 'stone' for m in seat.data.materials) else next(m for m in bpy.data.materials if m.get('dcc_material_id') == 'stone' and m.users)
stone.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.38, .43, .48, 1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'valid-post.blend'))
target = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('dcc_asset_id') != 'bench' and o.data.uv_layers and len(o.data.uv_layers[0].data))
uv = target.data.uv_layers[0].data[0].uv
previous = float(uv.x)
uv.x += 5.960464477539063e-8
if float(uv.x) == previous:
    raise RuntimeError('Probe did not change authored float32 UV')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'tiny-authored-uv.blend'))
print('UV_PROBE', target.name, previous, float(uv.x))
