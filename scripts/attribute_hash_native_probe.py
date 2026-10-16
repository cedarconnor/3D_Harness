"""Blender side of qualify_attribute_hash.py: a protected bench top and one saved variant per attribute change.

blender --background --factory-startup --python-exit-code 1 --python THIS -- --out NEW_FOLDER

Every variant changes only data that source_mesh_hash, source_uv_hash and geometry_hash leave out.
"""
from pathlib import Path
import sys

import bmesh
import bpy

out = Path(sys.argv[sys.argv.index('--') + 2])
out.mkdir(parents=True, exist_ok=False)


def scene():
    """A flat-shaded, UV-mapped bench top with stable IDs, a material and a camera."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    top = bpy.context.object
    top.name = 'BenchTop'
    top.data.name = 'BenchTopMesh'
    top.scale = (2.0, 0.5, 0.1)
    top['dcc_instance_id'] = 'probe.bench.top'
    top['dcc_asset_id'] = 'probe.bench.top-asset'
    material = bpy.data.materials.new('Timber')
    material['dcc_material_id'] = 'probe.timber'
    top.data.materials.append(material)
    camera = bpy.data.objects.new('ProbeCamera', bpy.data.cameras.new('ProbeCamera'))
    camera['dcc_instance_id'] = 'probe.camera'
    camera.location = (4, -4, 3)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return top.data


def edge_layer(mesh, name, kind, value):
    layer = mesh.attributes.new(name, kind, 'EDGE')
    layer.data[0].value = value


def loose_edge(mesh):
    """Join two existing vertices that share no edge; positions and faces stay as they were."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    a = bm.verts[0]
    neighbours = {v for edge in a.link_edges for v in edge.verts}
    bm.edges.new((a, next(v for v in bm.verts if v not in neighbours)))
    bm.to_mesh(mesh)
    bm.free()


def every_type(mesh):
    """One custom attribute of each type this Blender offers, so a type the observer cannot read shows up."""
    for kind in (item.identifier for item in bpy.types.Attribute.bl_rna.properties['data_type'].enum_items):
        mesh.attributes.new('every_' + kind.lower(), kind, 'POINT')


VARIANTS = {
    'base': lambda mesh: None,
    'base-again': lambda mesh: None,
    'smooth': lambda mesh: mesh.attributes.remove(mesh.attributes['sharp_face']),
    'sharp-edge': lambda mesh: edge_layer(mesh, 'sharp_edge', 'BOOLEAN', True),
    'crease': lambda mesh: edge_layer(mesh, 'crease_edge', 'FLOAT', 1.0),
    'seam': lambda mesh: edge_layer(mesh, 'uv_seam', 'BOOLEAN', True),
    'color': lambda mesh: mesh.color_attributes.new('Wear', 'BYTE_COLOR', 'CORNER'),
    'loose-edge': loose_edge,
    'every-type': every_type,
}

for name, change in VARIANTS.items():
    mesh = scene()
    assert 'sharp_face' in mesh.attributes, 'Primitive cubes are expected to be flat-shaded'
    change(mesh)
    mesh.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f'{name}.blend'))
