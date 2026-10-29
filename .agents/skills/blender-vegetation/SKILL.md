---
name: blender-vegetation
description: Build trees, shrubs and grass for Blender scenes or realtime assets. Use for leaf cards and atlases, branching and canopy structure, root pivots, declared wind attributes, foliage LODs and impostors. Covers saved-data checks and target-view review; use Geometry Nodes for scattering and hair for strand grooming.
---

# Vegetation from close-up to distant canopy

Choose the representation from the closest intended view and delivery target. A
hero branch can need modeled leaf surfaces; a game tree can use branch geometry
and leaf cards; a distant forest can use simplified crowns or impostors. Record
species references, plant dimensions, viewing distances and budgets before making
variants. These are craft methods inside the [managed harness workflow](../dcc-harness/SKILL.md).

## Establish one plant before scattering

1. Block the trunk taper, primary branches and crown silhouette from species
   references. Check characteristic branching, leaf arrangement and growth direction.
   A collection of randomly placed leaves does not establish botanical structure.
2. Keep the origin at the root/ground anchor and author card vertices relative to
   their attachment point. Preserve an existing root pivot when applying transforms
   or making LODs. Record attachment points before changing leaf size.
3. Test a representative branch and whole crown under the intended lighting.
   Check leaf-to-twig contact, canopy gaps and trunk visibility at final image size.
4. Make seeded variants with coherent growth. Scatter through [Geometry Nodes](../blender-geometry-nodes/SKILL.md)
   and [environment assembly](../dcc-environment-assembly/SKILL.md), preserving
   root support, exclusion zones and shared asset definitions.

## Cards, atlas and opacity

Pack related leaf variants into an atlas with padding and alpha dilation suitable
for its mip levels. Give each card UVs inside its assigned atlas region. Avoid
large transparent rectangles: tighter cards can reduce wasted transparent pixels
but cost more triangles. Compare both geometry and overdraw in the target engine.

Connect the image's colour to Base Color and Alpha to shader alpha; retain the
image's colour interpretation while treating separate masks as data. Configure
opacity and sidedness for the actual Blender renderer and engine importer. Old
`blend_method='CLIP'` examples are not a portable Blender 5.x recipe. A material
that looks correct in Blender does not prove the same alpha, shadows or backfaces
after export. Check both sides of leaves, bright backgrounds and thin silhouettes.
For glTF cutouts, inspect the exported alpha mode/cutoff as well as the image.

## Wind is an explicit shader contract

Record attribute name, domain, type, channels, coordinate space and destination
shader. For example, a POINT/FLOAT_COLOR layer named `VC_Wind` could encode bend
weight in R, with 0 at anchored roots and 1 at tips, and reserved G/B channels.
That name and mapping are a project convention, not a built-in wind system.

Inspect the evaluated and saved values after topology changes. A root-to-tip
gradient across a whole tree may be insufficient for branch pivots, flutter and
phase variation; implement the destination shader's declared contract. Test a
small native deformation or engine import before multiplying assets. Attributes
surviving a file round trip do not prove runtime wind or correct normals in motion.

## Foliage LODs and impostors

Simplify foliage deliberately: reduce small twigs/cards, consolidate crown clusters,
then consider an impostor at the far viewing range. Keep root pivot, crown extent,
opacity response and shader attributes consistent. Blind decimation can erase a
canopy while meeting its triangle budget. An impostor is optional when the scene's
distances and performance do not need one.

Capture all LODs at the same camera and switch size. Compare occupied crown area,
large holes, shading, alpha shimmer and transition popping, including a moving
camera and wind if used. Record material-slot mappings and required UV/colour
layers with the [realtime asset checks](../blender-realtime-assets/SKILL.md).

## Native fixture: root pivot, atlas UVs and wind persistence

This tiny card proves data authoring and native/GLB persistence. It does not
qualify a complete oak, foliage shading, engine wind, overdraw or visual quality.

```python verify
import bpy

mesh = bpy.data.meshes.new('leaf_card')
mesh.from_pydata([(-0.1, 0, 0), (0.1, 0, 0), (0.08, 0, 0.4), (-0.08, 0, 0.4)], [], [(0, 1, 2, 3)])
plant = bpy.data.objects.new('SM_Leaf', mesh)
bpy.context.scene.collection.objects.link(plant)
uv = mesh.uv_layers.new(name='UVMap')
for loop, value in zip(uv.data, [(0.05, 0.05), (0.45, 0.05), (0.45, 0.95), (0.05, 0.95)]):
    loop.uv = value
wind = mesh.color_attributes.new(name='VC_Wind', type='FLOAT_COLOR', domain='POINT')
mesh.color_attributes.active_color = wind
for vertex, colour in zip(mesh.vertices, wind.data):
    colour.color = (vertex.co.z / 0.4, 0, 0, 1)

native = str(WORK / 'leaf.blend')
bpy.ops.wm.save_as_mainfile(filepath=native)
bpy.ops.wm.open_mainfile(filepath=native)
plant = bpy.data.objects['SM_Leaf']; mesh = plant.data
assert plant.matrix_world.translation.length < 1e-7
assert min((plant.matrix_world @ v.co).z for v in mesh.vertices) == 0
wind = mesh.color_attributes['VC_Wind']
assert (wind.domain, wind.data_type) == ('POINT', 'FLOAT_COLOR')
assert [round(c.color[0], 5) for c in wind.data] == [0, 0, 1, 1]
expected_uv = {(0.05, 0.05), (0.45, 0.05), (0.45, 0.95), (0.05, 0.95)}
assert {(round(item.uv.x, 5), round(item.uv.y, 5)) for item in mesh.uv_layers['UVMap'].data} == expected_uv

# Explicitly export active vertex colours; an attribute name alone is not an export contract.
bpy.ops.object.select_all(action='DESELECT')
plant.select_set(True); bpy.context.view_layer.objects.active = plant
glb = str(WORK / 'leaf.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True,
                          export_vertex_color='ACTIVE')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
leaves = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(leaves) == 1
leaf = leaves[0]; mesh = leaf.data
assert len(mesh.uv_layers) == 1
assert {(round(item.uv.x, 5), round(item.uv.y, 5)) for item in mesh.uv_layers[0].data} == expected_uv
assert leaf.matrix_world.translation.length < 1e-6
assert abs(leaf.dimensions.z - 0.4) < 1e-5
# glTF stores colours by semantic; do not require the Blender attribute name to survive.
colour = mesh.color_attributes.active_color
assert colour is not None
for polygon in mesh.polygons:
    for index in polygon.loop_indices:
        vertex_index = mesh.loops[index].vertex_index
        data_index = index if colour.domain == 'CORNER' else vertex_index
        expected = mesh.vertices[vertex_index].co.z / 0.4
        assert abs(colour.data[data_index].color[0] - expected) < 0.01
```
