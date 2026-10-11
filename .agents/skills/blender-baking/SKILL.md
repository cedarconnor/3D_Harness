---
name: blender-baking
description: Bake textures in Blender 5.x reliably from Python and background mode. Covers procedural-to-image bakes, high-to-low normal and AO bakes with cages and ray distance, the active-image-node rule and silent CANCELLED results, margins, colour spaces and bit depth, channel packing, saving baked images without the view transform, and checking a bake by reloading its pixels.
---

# Baking textures

Baking turns shading or high-resolution detail into images. You bake for realtime export, for speed, and to freeze procedural looks. Baking runs in Cycles only.

## The rules that make bakes work

1. **Engine.** Set `scene.render.engine = 'CYCLES'`. Bake samples can be low for colour and data bakes; 1–16 is often enough, and AO needs more.
2. **Target image.** Each material on the target object needs an **Image Texture node holding the target image, and that node must be selected**. Measured on 5.1.1: a selected node bakes even when it is not active, while an active but unselected node returns `{'CANCELLED'}` **without raising**. Select it and make it active (`node.select = True`, `nodes.active = node`), deselect other image nodes, and always check the return value.
3. **Selection.** For selected-to-active, select the high-poly sources and make the low-poly object active.
4. **Unique UVs.** The target needs non-overlapping UVs inside 0–1 with padding (see the [UV skill](../blender-uv/SKILL.md)). Overlapping islands, including mirrored halves, fight over the same pixels.
5. **Margin.** `bake.margin` is in pixels, from the island edge outward. Use 16 px at 2K and 32 at 4K, and `margin_type='EXTEND'` or `'ADJACENT_FACES'`. Too little margin shows seams in the mip levels.

## Bake types

- **Colour (albedo).** `type='DIFFUSE'`, `pass_filter={'COLOR'}`. Leaving out `DIRECT` and `INDIRECT` keeps lighting out of it. The image is sRGB.
- **Roughness.** `type='ROUGHNESS'` gives a Non-Color image.
- **Normal.** `type='NORMAL'`, `normal_space='TANGENT'`. Blender bakes OpenGL (+Y). For DirectX targets such as Unreal, set `normal_g='NEG_Y'`. Non-Color, preferably 16-bit.
- **AO.** `type='AO'` gives a Non-Color image. Add samples, or it will be noisy.
- **Emission.** `type='EMIT'` bakes arbitrary data. Route any scalar or mask (curvature, a procedural mask, an ID colour) into an Emission shader temporarily, bake EMIT, then restore the material.
- **Combined.** `'COMBINED'` and the lit diffuse passes bake lighting in. Use them only for lightmaps and unlit targets, never for assets that will be relit.

## High-to-low (selected to active)

- **Cage.** `use_selected_to_active=True`. Rays start on the low poly's surface pushed outward by `cage_extrusion`, typically 1–5% of the object size, or come from an explicit `cage_object`: a copy of the low poly inflated to enclose the high poly, passed by name. `max_ray_distance` limits how far rays search; 0 means unlimited, which picks up wrong surfaces in concave areas.
- **Common faults.**
  - Wavy or skewed details mean the cage is too small or the ray distance too short.
  - Detail from a neighbouring part means the cage is too large, or parts were not exploded. Bake interpenetrating parts separately or exploded apart.
  - Seams on hard edges mean the UVs are not split at the sharp edges, or the triangulation differs between bake and export. Triangulate the low poly before baking.
- **Memory.** Join high-poly parts into one object, and decimate invisible areas.

## Images: depth, colour space and saving

- **Creating images.** Use `bpy.data.images.new(name, w, h, alpha=False, float_buffer=...)`. Use float or 16-bit for normal, height and displacement maps; 8-bit bands on smooth gradients. Set the colour space before baking: `'sRGB'` for colour, `'Non-Color'` for everything else.
- **Saving.** Set `image.filepath_raw = path` and `image.file_format = 'PNG'` (or `'OPEN_EXR'`), then call `image.save()`. Pack it (`image.pack()`) if the .blend must be self-contained.
  - `image.save(filepath=...)` on a generated float image leaves `filepath` empty, and can drop the pixel buffer.
  - `image.save_render(path)` **applies the scene's view transform** to float colour images: a linear 0.5 was written as 0.667 under AgX. Use it only for display images, or after setting the view transform to `Standard`.
- **Checking.** Reload the saved file (`bpy.data.images.load(path, check_existing=False)`) and read its pixels with `foreach_get`. Compare against the expected values with a tolerance from an 8-bit round trip (0.7 comes back as about 0.702). An 8-bit sRGB image's pixels hold sRGB-encoded values: a linear 0.2 reads back as about 0.48. Look at the island borders for margin bleed.

## Channel packing

Combine scalar bakes into one RGB(A) image in numpy (`ORM`: R = AO, G = roughness, B = metallic), write it with `foreach_set`, and save it Non-Color. Record the packing layout in the material or export notes; the engine has to know which channel is which.

## Big meshes and alternatives

Above a few hundred thousand faces, or for vertex-coloured assets, bake to a colour attribute instead of an image: `bake.target = 'VERTEX_COLORS'` with an active colour attribute. Geometry Nodes can also capture procedural values into attributes, with no bake at all, when the target reads attributes.

```python verify
import bpy
import numpy as np

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples, scene.cycles.device = 1, 'CPU'

bpy.ops.mesh.primitive_plane_add(size=1); plane = bpy.context.object
mat = bpy.data.materials.new('baked'); plane.data.materials.append(mat)
nodes = mat.node_tree.nodes
bsdf = nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.2, 0.4, 0.8, 1.0)   # linear colour to bake

target = bpy.data.images.new('T_plane_D', 32, 32, alpha=False)
target.colorspace_settings.name = 'sRGB'
image_node = nodes.new('ShaderNodeTexImage'); image_node.image = target

# An active but unselected image node: the bake is cancelled silently. Never assume success.
for node in nodes:
    node.select = False
nodes.active = image_node
try:
    result = bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=4)
except RuntimeError:
    result = {'CANCELLED'}
assert result == {'CANCELLED'}, result

# Selecting the image node makes it work.
image_node.select = True
assert bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=4) == {'FINISHED'}

# Save without the view transform, then reload and check the pixels.
path = str(WORK / 'T_plane_D.png')
target.filepath_raw, target.file_format = path, 'PNG'
target.save()
reloaded = bpy.data.images.load(path, check_existing=False)
pixels = np.empty(32 * 32 * 4, dtype=np.float32); reloaded.pixels.foreach_get(pixels)
centre = pixels.reshape(32, 32, 4)[16, 16, :3]
# Byte images hold sRGB-encoded values: compare against the encoded linear colour.
encode = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
assert np.allclose(centre, [encode(c) for c in (0.2, 0.4, 0.8)], atol=0.03), centre

# ORM channel packing in numpy, saved as Non-Color data.
ao, rough, metal = np.full(16, 1.0), np.full(16, 0.5), np.zeros(16)
orm = bpy.data.images.new('T_plane_ORM', 4, 4, alpha=True)
orm.colorspace_settings.name = 'Non-Color'
orm.pixels.foreach_set(np.stack([ao, rough, metal, np.ones(16)], axis=1).ravel().astype(np.float32))
orm.filepath_raw, orm.file_format = str(WORK / 'T_plane_ORM.png'), 'PNG'
orm.save()
check = bpy.data.images.load(str(WORK / 'T_plane_ORM.png'), check_existing=False)
check.colorspace_settings.name = 'Non-Color'
packed = np.empty(16 * 4, dtype=np.float32); check.pixels.foreach_get(packed)
assert np.allclose(packed.reshape(16, 4)[0, :3], (1.0, 0.5, 0.0), atol=0.005), packed[:4]
```
