"""Build the coverage-gap fixtures for build-plan item G2. Run inside background Blender.

  base.blend             a ground, a bench whose material uses a shader group nested in another group,
                         a ground copy carrying a scatter Geometry Nodes tree, and a crate with an
                         empty material slot
  group-changed.blend    base with one value changed inside the inner shader group
  scatter-changed.blend  base with the scatter density changed inside the Geometry Nodes tree
  scatter-input.blend    base with the scatter modifier's exposed Seed input changed
  slot-filled.blend      base with the crate's empty slot bound to the stone material
  missing-texture.blend  base with an image texture whose file does not exist
"""
import sys
from pathlib import Path

import bpy

out = Path(sys.argv[sys.argv.index('--') + 2]) if '--out' in sys.argv else Path(sys.argv[-1])
out.mkdir(parents=True, exist_ok=True)


def material(name, mid, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat['dcc_material_id'] = mid
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = color
    return mat


def cube(name, iid, aid, location, scale, mat=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj['dcc_instance_id'] = iid
    obj['dcc_asset_id'] = aid
    obj.data.name = aid
    if mat is not None:
        obj.data.materials.append(mat)
    return obj


def shader_groups():
    inner = bpy.data.node_groups.new('Wear.Inner', 'ShaderNodeTree')
    inner.interface.new_socket('Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    rgb = inner.nodes.new('ShaderNodeRGB'); rgb.name = 'Tint'
    rgb.outputs[0].default_value = (0.30, 0.18, 0.10, 1.0)
    end = inner.nodes.new('NodeGroupOutput')
    inner.links.new(rgb.outputs[0], end.inputs[0])
    outer = bpy.data.node_groups.new('Wear.Outer', 'ShaderNodeTree')
    outer.interface.new_socket('Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    nested = outer.nodes.new('ShaderNodeGroup'); nested.name = 'Inner'; nested.node_tree = inner
    end = outer.nodes.new('NodeGroupOutput')
    outer.links.new(nested.outputs[0], end.inputs[0])
    return outer


def scatter_tree():
    tree = bpy.data.node_groups.new('Scatter', 'GeometryNodeTree')
    tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    seed = tree.interface.new_socket('Seed', in_out='INPUT', socket_type='NodeSocketInt')
    seed.default_value = 3
    tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    start, end = tree.nodes.new('NodeGroupInput'), tree.nodes.new('NodeGroupOutput')
    points = tree.nodes.new('GeometryNodeDistributePointsOnFaces'); points.name = 'Points'
    points.inputs['Density'].default_value = 4.0
    shape = tree.nodes.new('GeometryNodeMeshCube'); shape.name = 'Pebble'
    shape.inputs['Size'].default_value = (0.05, 0.05, 0.05)
    place = tree.nodes.new('GeometryNodeInstanceOnPoints'); place.name = 'Place'
    join = tree.nodes.new('GeometryNodeJoinGeometry'); join.name = 'Join'
    tree.links.new(start.outputs['Geometry'], points.inputs['Mesh'])
    tree.links.new(start.outputs['Seed'], points.inputs['Seed'])
    tree.links.new(points.outputs['Points'], place.inputs['Points'])
    tree.links.new(shape.outputs['Mesh'], place.inputs['Instance'])
    tree.links.new(start.outputs['Geometry'], join.inputs['Geometry'])
    tree.links.new(place.outputs['Instances'], join.inputs['Geometry'])
    tree.links.new(join.outputs['Geometry'], end.inputs['Geometry'])
    return tree, seed.identifier


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.world = bpy.data.worlds.new('World'); scene.world.use_nodes = True
stone = material('Stone', 'stone', (0.4, 0.4, 0.38, 1.0))
worn = material('Worn', 'worn', (0.5, 0.3, 0.2, 1.0))
group = worn.node_tree.nodes.new('ShaderNodeGroup'); group.name = 'Wear'; group.node_tree = shader_groups()
worn.node_tree.links.new(group.outputs[0], worn.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
cube('Ground', 'ground', 'ground.mesh', (0, 0, -0.05), (2, 2, 0.05), stone)
cube('Bench', 'bench', 'bench.mesh', (0, 0, 0.25), (0.6, 0.2, 0.25), worn)
bed = cube('Bed', 'bed', 'bed.mesh', (1.2, 1.2, 0.01), (0.5, 0.5, 0.01), stone)
tree, seed_id = scatter_tree()
modifier = bed.modifiers.new('Scatter', 'NODES'); modifier.node_group = tree
crate = cube('Crate', 'crate', 'crate.mesh', (-1.0, 0.8, 0.2), (0.2, 0.2, 0.2))
crate.data.materials.append(None)
bpy.data.cameras.new('Camera')
camera = bpy.data.objects.new('Camera', bpy.data.cameras['Camera']); scene.collection.objects.link(camera)
camera['dcc_instance_id'] = 'review.camera'; camera.location = (4, -4, 3); scene.camera = camera
base = out / 'base.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(base))


def variant(name, change):
    bpy.ops.wm.open_mainfile(filepath=str(base))
    change()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / name))


def change_group():
    bpy.data.node_groups['Wear.Inner'].nodes['Tint'].outputs[0].default_value = (0.10, 0.30, 0.18, 1.0)


def change_scatter():
    bpy.data.node_groups['Scatter'].nodes['Points'].inputs['Density'].default_value = 9.0


def change_input():
    modifier = bpy.data.objects['Bed'].modifiers['Scatter']
    if hasattr(modifier, 'properties'):  # Blender 5.2 moved modifier inputs off ID properties
        getattr(modifier.properties.inputs, seed_id).value = 11
    else:
        modifier[seed_id] = 11


def fill_slot():
    bpy.data.objects['Crate'].material_slots[0].material = bpy.data.materials['Stone']


def missing_texture():
    nodes = bpy.data.materials['Stone'].node_tree
    image = bpy.data.images.new('Lost', 4, 4)
    image.source = 'FILE'; image.filepath = '//textures/lost.png'
    texture = nodes.nodes.new('ShaderNodeTexImage'); texture.name = 'Lost'; texture.image = image
    nodes.links.new(texture.outputs['Color'], nodes.nodes['Principled BSDF'].inputs['Base Color'])


variant('group-changed.blend', change_group)
variant('scatter-changed.blend', change_scatter)
variant('scatter-input.blend', change_input)
variant('slot-filled.blend', fill_slot)
variant('missing-texture.blend', missing_texture)
print('fixtures written', out)
