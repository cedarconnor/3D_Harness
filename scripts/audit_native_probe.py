"""Build the audit fixtures for build-plan item G3. Run inside background Blender.

control.blend is a closed ground slab and a closed, textured crate standing on it, with nothing to
report under any profile. Every other file is the control with one defect, named after it.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

out = Path(sys.argv[sys.argv.index('--out') + 1])
out.mkdir(parents=True, exist_ok=True)
# Outward-facing box: bottom, top, front, right, back, left.
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
CRATE = ((-0.5, -0.5, 0), (0.5, 0.5, 1))
SHEET = [(1, 1, 0), (1.8, 1, 0), (1.8, 1.8, 0), (1, 1.8, 0)]


def corners(lo, hi):
    (a, b, c), (d, e, f) = lo, hi
    return [(a, b, c), (d, b, c), (d, e, c), (a, e, c), (a, b, f), (d, b, f), (d, e, f), (a, e, f)]


def mesh_object(name, iid, vertices, faces, material=None, edges=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, list(edges), faces)
    mesh.uv_layers.new(name='UVMap')
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if iid:
        obj['dcc_instance_id'] = iid
    if material is not None:
        mesh.materials.append(material)
    return obj


def control():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    stone = bpy.data.materials.new('Stone'); stone.use_nodes = True
    paint = bpy.data.materials.new('Paint'); paint.use_nodes = True
    nodes, links = paint.node_tree.nodes, paint.node_tree.links
    shader = nodes['Principled BSDF']
    albedo = nodes.new('ShaderNodeTexImage'); albedo.name = 'Albedo'; albedo.image = bpy.data.images.new('albedo', 8, 8)
    relief = nodes.new('ShaderNodeTexImage'); relief.name = 'Relief'; relief.image = bpy.data.images.new('relief', 8, 8)
    relief.image.colorspace_settings.name = 'Non-Color'
    bump = nodes.new('ShaderNodeNormalMap')
    links.new(albedo.outputs['Color'], shader.inputs['Base Color'])
    links.new(relief.outputs['Color'], bump.inputs['Color'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    mesh_object('Ground', 'ground', corners((-2, -2, -0.2), (2, 2, 0)), FACES, stone)
    mesh_object('Crate', 'crate', corners(*CRATE), FACES, paint)


def crate():
    return bpy.data.objects['Crate']


def rebuild(faces, extra=(), edges=()):
    old = crate()
    material = old.data.materials[0]
    bpy.data.objects.remove(old)
    return mesh_object('Crate', 'crate', corners(*CRATE) + list(extra), faces, material, edges)


def flip(face):
    return tuple(reversed(face))


def rescale(factors):
    obj = crate()
    obj.data.transform(Matrix.Diagonal([1 / f for f in factors]).to_4x4())
    if factors[0] * factors[1] * factors[2] < 0:
        obj.data.flip_normals()   # keep the faces outward as drawn, so the mirror is the only defect
    obj.scale = factors


def empty_slot():
    crate().data.materials.append(None)
    crate().data.polygons[1].material_index = 1


VARIANTS = {
    'flipped-face': lambda: rebuild([flip(FACES[1])] + FACES[:1] + FACES[2:]),
    'inward': lambda: rebuild([flip(f) for f in FACES]),
    'inward-open': lambda: rebuild([flip(f) for f in FACES[1:]]),
    # Without its bottom, so the rim still stands on the ground and no face lies in the ground's plane.
    'open': lambda: rebuild(FACES[1:]),
    'doubled-face': lambda: rebuild(FACES + [FACES[1]]),
    'loose': lambda: rebuild(FACES, [(0, 0, 1), (0, 0, 1.2)], [(8, 9)]),
    # A vertex on the front top edge, with a triangle of no area between the top and the front face.
    'zero-area': lambda: rebuild([f for f in FACES if f != (0, 1, 5, 4)] + [(0, 1, 5, 8, 4), (4, 8, 5)], [(0, -0.5, 1)]),
    'coincident': lambda: mesh_object('Plate', None, corners((0.2, 0.2, 0), (1.2, 1.2, 1)), FACES),
    'coincident-matched': lambda: mesh_object('Plate', None, corners((0.2, 0.2, 0), (1.2, 1.2, 1)), FACES, bpy.data.materials['Paint']),
    'sheet-down': lambda: mesh_object('Sheet', 'sheet', SHEET, [(3, 2, 1, 0)]),
    'sheet-up': lambda: mesh_object('Sheet', 'sheet', SHEET, [(0, 1, 2, 3)]),
    'floating': lambda: setattr(crate(), 'location', (0, 0, 0.3)),
    'scale-uniform': lambda: rescale((2, 2, 2)),
    'scale-nonuniform': lambda: rescale((2, 1, 1)),
    'scale-negative': lambda: rescale((-1, 1, 1)),
    'empty-slot': empty_slot,
    'data-srgb': lambda: setattr(bpy.data.images['relief'].colorspace_settings, 'name', 'sRGB'),
    'no-uv': lambda: crate().data.uv_layers.remove(crate().data.uv_layers[0]),
}

control()
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'control.blend'))
for name, change in VARIANTS.items():
    bpy.ops.wm.open_mainfile(filepath=str(out / 'control.blend'))
    change()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f'{name}.blend'))
print('fixtures written', out)
