"""Disposable native files for external revision qualification; never use in a live editor."""
import argparse
from pathlib import Path
import sys

import bpy

p = argparse.ArgumentParser()
p.add_argument('action', choices=['fixtures', 'observe'])
p.add_argument('--runtime', required=True)
p.add_argument('--out', required=True)
p.add_argument('--source')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.runtime)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json

out = Path(a.out)
if a.action == 'observe':
    bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False)
    write_json(out, observe(), compact_observation=True)
else:
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, .7))
    table = bpy.context.object
    table.name = 'Table'
    table.dimensions = (2, 1, .1)
    table['dcc_instance_id'] = 'ext.table.top'
    table['dcc_asset_id'] = 'table'
    mat = bpy.data.materials.new('Stone')
    mat.use_nodes = True
    mat['dcc_material_id'] = 'stone'
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .4
    generated = bpy.data.images.new('TexturePixels', width=4, height=4)
    generated.generated_color = (.35, .2, .12, 1)
    generated.save_render(str(out / 'texture-source.png'))
    image = bpy.data.images.load(str(out / 'texture-source.png'))
    image.name = 'PackedTexture'
    image.pack()
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    mat.node_tree.links.new(texture.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    table.data.materials.append(mat)
    linked = bpy.data.objects.new('SecondTable', table.data)
    bpy.context.scene.collection.objects.link(linked)
    linked.location = (3, 0, .7)
    linked.scale = table.scale
    linked['dcc_instance_id'] = 'ext.table.second'
    linked['dcc_asset_id'] = 'table'
    bpy.ops.object.camera_add(location=(6, -6, 4))
    bpy.context.object['dcc_instance_id'] = 'ext.camera'
    bpy.context.scene.camera = bpy.context.object
    bpy.ops.object.light_add(type='AREA', location=(0, -2, 5))
    light = bpy.context.object
    light['dcc_instance_id'] = 'ext.light'
    light.data.energy = 300
    base = out / 'baseline.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(base))
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'artist-material.blend'))
    light.data.energy = 900
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'unrequested-light.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(base), load_ui=False)
    bpy.data.objects['SecondTable']['dcc_instance_id'] = 'ext.table.top'
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'duplicate-id.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(base), load_ui=False)
    bpy.data.images['PackedTexture'].save_render(str(out / 'relative.png'))
    external = bpy.data.images.load(str(out / 'relative.png'))
    external.filepath = '//relative.png'
    mat = bpy.data.materials['Stone']
    next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE').image = external
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'external-baseline.blend'))
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'external-candidate.blend'))
    print('REVISION_FIXTURES_SAVED')
