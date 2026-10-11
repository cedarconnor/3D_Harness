---
name: blender-grease-pencil
description: Draw, animate and script 2D and 2.5D work with Grease Pencil v3 in Blender 5.x: storyboards, 2D animation, annotations over 3D, line art and stylized outlines. Covers the v3 data model (layers, frames, drawings, attributes), the 4.3 and 5.0 API renames, materials, modifiers, Line Art, timing on twos, and rendering.
---

# Grease Pencil v3

Grease Pencil v3 (4.3+) rebuilt the 2D system on the same attribute and curves foundations as meshes and hair. Old scripts break. In 5.x the datablock is `bpy.types.GreasePencil` in `bpy.data.grease_pencils`, the object type is `'GREASEPENCIL'`, and modes are `PAINT_GREASE_PENCIL`, `SCULPT_GREASE_PENCIL` and so on, with Edit Mode just `'EDIT'`.

## The data model

- **Hierarchy.** A `GreasePencil` datablock has `layers` (with layer groups). Each layer has `frames`, keyed by frame number, and each frame has one `drawing`. A drawing holds the strokes as **curves** with point and curve attributes.
- **Creating strokes.** `layer = gp.layers.new('Ink')`, then `frame = layer.frames.new(frame_number)`, then `drawing = frame.drawing`, then `drawing.add_strokes([point_count, ...])`. Remove with `drawing.remove_strokes(indices=...)`.
- **Point attributes.** `position` (formerly `co`), `radius` (formerly pressure × thickness), `opacity` (formerly strength) and `vertex_color`. Curve attributes include `cyclic` and `material_index`. For bulk work, write `drawing.attributes['position'].data.foreach_set(...)`; the `drawing.strokes` Python layer is a slow compatibility shim whose references go stale after edits.
- **Renames since 4.3.** `layer.info` became `layer.name`; frames move with `layer.frames.move(from, to)`. The 5.0 rename moved `GreasePencilv3` to `GreasePencil`, and the old 2D annotation data became `Annotation*` types.

## Materials

Grease Pencil materials are separate from mesh materials. Create one with `mat = bpy.data.materials.new(name)` and `bpy.data.materials.create_gpencil_data(mat)`, then set `mat.grease_pencil.show_stroke`, `show_fill`, `color` and `fill_color`. Assign by `material_index` per stroke. Keep a small palette of named materials (`ink`, `shadow`, `fill_skin`) rather than one per stroke.

## Animation

- **Frames are drawings.** Hold a drawing by keeping one frame until the next key. Animate on twos (a new drawing every 2 frames at 24 fps) for a traditional look, and on ones for fast action.
- **Layers.** Use layers for line art, colour, shadows and effects. Lock and hide finished layers. Onion skinning shows neighbouring frames while drawing.
- **Object-level motion.** Layer transforms and object transforms move whole drawings without redrawing, for camera moves and parallax in 2.5D scenes.

## Modifiers and Line Art

- **Modifiers.** Grease Pencil modifiers are normal `object.modifiers` with `GREASE_PENCIL_*` types: Thickness, Smooth, Noise, Offset, Tint, Opacity, Dash, Envelope, Outline, Lattice, Armature, Time, Build, and more. `GREASE_PENCIL_BUILD` draws strokes on over time, for reveals and handwriting.
- **Line Art.** The `LINEART` modifier generates strokes from 3D geometry: contours, creases and intersections, filtered by collection, object or material. It gives 3D scenes an ink outline. It is expensive on dense meshes, so limit it with collections and bake it (`bpy.ops.object.lineart_bake_strokes`) for final renders.

## Storyboards and annotations

For storyboards, use one camera per panel with the timeline markers bound to cameras, draw on a layer per panel, and output an image sequence or a strip in the sequencer. Annotations (the 2D note tool) are separate `Annotation` data, used for review markup and not rendered.

## Rendering

Grease Pencil renders in EEVEE and Cycles (as a pass). Anti-aliasing is in the render settings. Stroke thickness can scale with the object or stay in screen space (the layer and material settings). Check it at the delivery resolution, because thin lines vanish when downscaled. 5.1 adds a Grease Pencil render pass (`view_layer.use_pass_grease_pencil`) for compositing.

```python verify
import bpy
import numpy as np

scene = bpy.context.scene
gp = bpy.data.grease_pencils.new('board')
assert type(gp).__name__ == 'GreasePencil'
obj = bpy.data.objects.new('board', gp); scene.collection.objects.link(obj)
assert obj.type == 'GREASEPENCIL'

ink = bpy.data.materials.new('ink'); bpy.data.materials.create_gpencil_data(ink)
ink.grease_pencil.color = (0.05, 0.05, 0.05, 1.0)
gp.materials.append(ink)

layer = gp.layers.new('Ink')
assert layer.name == 'Ink'
# A stroke on frame 1 and a held drawing changed on frame 3 (animating on twos).
for frame_number, height in ((1, 0.0), (3, 0.5)):
    drawing = layer.frames.new(frame_number).drawing
    drawing.add_strokes([5])
    points = np.array([(x * 0.25, 0.0, height) for x in range(5)], dtype=np.float32)
    drawing.attributes['position'].data.foreach_set('vector', points.ravel())
    radius = drawing.attributes.get('radius') or drawing.attributes.new('radius', 'FLOAT', 'POINT')
    radius.data.foreach_set('value', np.full(5, 0.01, dtype=np.float32))
assert [f.frame_number for f in layer.frames] == [1, 3]
second = layer.frames[1].drawing
positions = np.empty(5 * 3, dtype=np.float32); second.attributes['position'].data.foreach_get('vector', positions)
assert np.allclose(positions.reshape(5, 3)[:, 2], 0.5)
assert len(second.strokes) == 1 and len(second.strokes[0].points) == 5

# Grease Pencil modifiers live in object.modifiers with GREASE_PENCIL_* types.
build = obj.modifiers.new('reveal', 'GREASE_PENCIL_BUILD')
thickness = obj.modifiers.new('weight', 'GREASE_PENCIL_THICKNESS')
assert [m.type for m in obj.modifiers] == ['GREASE_PENCIL_BUILD', 'GREASE_PENCIL_THICKNESS']
```
