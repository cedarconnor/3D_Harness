---
name: blender-compositing
description: Build Blender 5.x compositor node groups for finishing renders and integrating CG with plates. Covers the compositing node group API, menu input sockets, glare and bloom, denoising from passes, Cryptomatte and ID mattes, depth and mist, lens effects, colour management of plates and EXR inputs, and the canvas-size and double-tone-mapping traps.
---

# Composite in Blender 5.x

Since 5.0 the compositor is a node group. Create a `CompositorNodeTree` with `bpy.data.node_groups.new(name, 'CompositorNodeTree')` and assign it to `scene.compositing_node_group`.

- The result leaves through a **Group Output** node, with an interface socket made by `tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')`.
- There is no `scene.node_tree` and no Composite node.
- Many option enums are now **menu input sockets**: set `node.inputs['Type'].default_value = 'Bloom'`, not a node property.
- Several colour nodes were replaced by shared shader nodes. Mix is `ShaderNodeMix` with `data_type='RGBA'`.
- `scene.use_nodes` is deprecated, and compositing runs when the group is assigned.

## What belongs in the compositor

- **Finishing.** Glare and bloom, lens distortion and dispersion, vignette, light grading (Color Balance, curves), sharpening, and film grain at the very end.
- **Pass work.** Denoise from noisy, albedo and normal passes; relight with light groups; fix one object through a Cryptomatte matte; add depth fog from mist or depth.
- **Integration.** Put CG over a plate with Alpha Over. Use shadow catcher passes, the plate's lens distortion (Movie Distortion), and colour matching to the plate's blacks and whites. See [matchmove](../blender-matchmove/SKILL.md).

Do not fix in the compositor what should be fixed in the scene, such as geometry, UVs, wrong materials or missing lights. Never use glare or grading to hide a modeling error.

## Rules that prevent wrong results

- **Work in scene-linear.** Compositing happens before the view transform. Render passes and EXR inputs are linear; keep them that way.
  - **Image inputs.** For a PNG or JPEG input, set its colour space correctly: `sRGB` for display images and `Non-Color` for data.
  - **Display-referred plates.** When the comp's input is already a final display-referred image, and the output must look identical, render that scene with the `Standard` view transform. AgX on top would tone-map it a second time.
- **Bloom threshold.** Set the Glare threshold above 1.0 in linear values, so that only true highlights bloom. Bloom on everything makes a soft, low-contrast image.
- **Canvas size.** The output canvas is the first input's size. Inputs of different sizes are centred and cropped unless you add an explicit Scale or Transform node. Check the output resolution.
- **Alpha.** Check whether inputs are premultiplied, and convert explicitly. Check alpha in PNG or EXR, never in a JPEG contact sheet.
- **Missing passes.** A pass that does not exist does not appear as a socket on the Render Layers node. Enable it on the view layer first, then rebuild the links. Fail loudly when an expected pass is missing; do not substitute another.
- **Mattes.** Cryptomatte (`CompositorNodeCryptomatteV2`) gives anti-aliased object and material mattes. ID mask passes alias at edges and are a poor substitute.
- **Mist.** The mist pass needs `world.mist_settings.start` and `depth` set to the scene's scale; the defaults suit a 25 m scene.

## File output

- **File Output node.** Use it to write extra passes. In 5.x it has `directory`, `file_name` and `file_output_items` (formerly `base_path` and `file_slots`).
- **Multilayer EXR.** This is the format for passing data to another compositor.
- **Compare against the source.** Show the original render, the plate and the result side by side at the same view settings. Mean pixel statistics do not replace looking.

## Performance

- **Device.** `render.compositor_device = 'GPU'` is fast. Selecting the GPU does not prove it was used, so report what ran.
- **Previews.** Use the viewer node or a reduced render resolution for previews, and full resolution for decisions about fine grain and sharpening.

```python verify
import bpy

scene = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))
mat = bpy.data.materials.new('hot')
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Emission Color'].default_value = (1, 0.6, 0.2, 1); bsdf.inputs['Emission Strength'].default_value = 20
bpy.context.object.data.materials.append(mat)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (0, -6, 0), (1.5708, 0, 0); scene.camera = cam

# The 5.x compositor: a node group assigned to the scene, ending in a Group Output.
tree = bpy.data.node_groups.new('finish', 'CompositorNodeTree')
tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = tree
layers = tree.nodes.new('CompositorNodeRLayers')
glare = tree.nodes.new('CompositorNodeGlare')
glare.inputs['Type'].default_value = 'Bloom'            # a menu input socket, not a property
glare.inputs['Threshold'].default_value = 1.5           # only true highlights bloom
out = tree.nodes.new('NodeGroupOutput')
tree.links.new(layers.outputs['Image'], glare.inputs['Image'])
tree.links.new(glare.outputs['Image'], out.inputs[0])
assert not hasattr(scene, 'node_tree') and scene.compositing_node_group == tree
assert all(link.is_valid for link in tree.links)

# Passes appear as sockets only once enabled on the view layer.
assert 'Depth' not in layers.outputs or not layers.outputs['Depth'].enabled
bpy.context.view_layer.use_pass_z = True
assert layers.outputs['Depth'].enabled

# Render a tiny frame through the compositor and check the result exists at the expected size.
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 64, 64, 100
scene.render.filepath = str(WORK / 'comp.png')
bpy.ops.render.render(write_still=True)
result = bpy.data.images.load(str(WORK / 'comp.png'))
assert tuple(result.size) == (64, 64)
```
