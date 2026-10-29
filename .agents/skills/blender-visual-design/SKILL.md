---
name: blender-visual-design
description: Apply visual design judgment to Blender scenes through hierarchy, silhouette, proportion, value, palette, composition and storytelling. Use for visual critique or art direction, including cel/NPR, retro/PSX, isometric, voxel and horror looks through selectively loaded references, with render comparisons and explicit artistic acceptance.
---

# Visual design for 3D

Technical correctness does not make an image good. Before building, decide what the viewer should see first, second and third, and what the image should feel like. Then check those decisions on renders. The artist or client decides on taste; measurable proxies only make the discussion concrete. In a harness project, record approved directions as project decisions; see [planning](../dcc-plan-environment/SKILL.md).

## Hierarchy and focus

- **One focal point per image or beat.** Make it win on several of these at once: highest value contrast, the most saturated colour, the sharpest focus, the most detail, the eye-line and leading lines converging on it, and an isolated position.
- **Reduce competition.** Lower the contrast, detail and saturation of everything else rather than raising the focal point further. Busy backgrounds kill hierarchy.
- **Detail is a budget.** Spend it where the eye goes and let the rest rest: roughly 60% quiet areas, 30% medium detail, 10% dense detail. Every detail should explain something: use, age, function, story.

## Silhouette and shape language

- **Silhouette.** It must be readable at thumbnail size. Test it with a flat black render against white: if the object cannot be identified, change the form, not the materials.
- **Shape language.** Circles read as friendly, soft and safe; squares as stable, solid and dependable; triangles and diagonals as dynamic, aggressive or dangerous. Make one shape type dominant and use the others as accents.
- **Size rhythm.** Vary large, medium and small forms; similar-sized repeated forms are monotonous. Group details into clusters with clear spacing.

## Proportion and scale

- **Scale cues.** People read scale from known objects: doors (about 2.0–2.1 m), stairs (about 17 cm rise), chairs (about 45 cm seat), handrails (about 0.9–1.0 m), and texture size such as bricks, tiles and planks. Wrong texture scale makes a correct model look like a miniature.
- **Depth of field.** Shallow depth of field and a high camera read as small; a low camera with a long depth of field reads as large. Use this deliberately (see [camera](../blender-camera/SKILL.md)).
- **Reference.** Take proportions from reference and measurement, not from memory. Stylization exaggerates real proportions consistently; it does not replace them.

## Value and colour

- **Values first.** Group the image into about three value masses (light, middle, dark) and check them with a grayscale version. Colour cannot rescue a muddled value structure. The focal point holds the strongest local value contrast.
- **Palette.** Choose a limited palette: a dominant hue, a secondary, and a small accent (60/30/10). Complementary accents draw the eye, so use them on the focal point. Saturate the focal point and desaturate distance and shadow, which is natural atmospheric perspective.
- **Colour temperature.** Warm and cool contrast between light and shadow, such as warm key and cool fill or sky, gives depth. Set it on the lights, not the materials (see [lighting](../blender-lighting/SKILL.md)).
- **Material colour.** Real materials are less saturated and darker than they seem. Keep albedos plausible (see [shading](../blender-shading/SKILL.md)) and let the lighting create the mood.

## Composition

- **Guides.** Thirds, golden ratio, diagonals, centred symmetry, and frame within a frame. Blender shows them on the camera: `show_composition_thirds`, `show_composition_golden`, `show_composition_center`, `show_composition_diagonal` and the harmony triangles.
- **Leading lines.** Roads, edges, light shafts and gaze direct the eye to the focal point. Avoid lines that lead out of frame or tangents, where edges just touch and flatten depth.
- **Depth layers.** Foreground, midground and background, with overlap and atmosphere separating them. A foreground element frames the scene and gives scale.
- **Negative space.** Empty space is part of the composition; crowded frames have no hierarchy.
- **Reframing.** Treat each aspect ratio as its own composition.

## Storytelling

Ask what happened here before, what is happening and what will happen next. Wear, clutter, placement and lighting should answer it consistently: a workshop has tools where hands reach, wear where people walk, light where people work. Purposeful detail beats uniform greebles and random damage.

## Measurable proxies

These do not replace looking at the images. They make critiques specific and comparable between versions:

- **Silhouette.** A flat black-on-white render (Workbench, flat lighting, single colour). Report the subject's coverage of the frame and compare masks between versions.
- **Focal position.** `world_to_camera_view` of the focal point. Report its normalized frame position and its distance to the nearest thirds intersection or chosen guide.
- **Value.** A small grayscale render: a luminance histogram, the share of the frame in each value band, and the local contrast around the focal point versus the frame average.
- **Review.** Look at the actual renders, list at most three to five ranked issues per pass (camera and silhouette before materials and detail), change one thing, and re-render with the same settings. Stop after a few passes and ask for direction rather than polishing indefinitely.

## Choose style references when the brief needs them

Record reference images, shape/edge treatment, palette, detail density, projection,
shader/renderer, output size and permitted variation as project direction. Keep
examples of both desired and rejected results with reasons. Style labels guide
choices; they do not override approved dimensions, accessibility or delivery rules.

| Request | Load | Check on the resulting images |
|---|---|---|
| Cel, anime or graphic NPR | [Cel and NPR](references/cel-npr.md) | Shadow bands, contour stability and face readability |
| Retro, PSX or deliberately low-poly | [Retro](references/retro.md) | Silhouette, texel scale and motion at target resolution |
| Isometric kit or diorama | [Isometric](references/isometric.md) | Shared projection, tile joins and readability at game scale |
| Voxel or block-grid assets | [Voxel](references/voxel.md) | Grid occupancy, palette and seams between modules |
| Horror, liminal or unsettling environments | [Horror](references/horror.md) | Intended reveal, usable navigation and focal contrast |

These choices can combine: isometric is a projection/layout choice, voxel changes
geometry language, cel changes shading, and horror sets mood. Name their roles
instead of treating them as mutually exclusive presets. Approve a small style
frame before producing a large family. The [library guide](../../../docs/guides/BLENDER_SKILL_LIBRARY.md)
records provenance and qualification limits.

```python verify
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 192, 108, 100
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0)); hero = bpy.context.object
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.show_composition_thirds = True
cam.location = (0, -6, 0)
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

# Place the focal point on the lower-left thirds intersection by shifting the lens, then measure it.
cam.data.shift_x, cam.data.shift_y = 1 / 6 * (192 / 192), 1 / 6 * (108 / 192)
bpy.context.view_layer.update()
focal = world_to_camera_view(scene, cam, hero.matrix_world.translation)
thirds = [(x, y) for x in (1 / 3, 2 / 3) for y in (1 / 3, 2 / 3)]
nearest = min(((focal.x - x) ** 2 + (focal.y - y) ** 2) ** 0.5 for x, y in thirds)
assert nearest < 0.02, (focal.x, focal.y)

# Silhouette test: flat black on white in Workbench, then the subject's frame coverage from the pixels.
scene.render.engine = 'BLENDER_WORKBENCH'
shading = scene.display.shading
shading.light, shading.color_type, shading.single_color = 'FLAT', 'SINGLE', (0, 0, 0)
scene.world = bpy.data.worlds.new('white'); scene.world.color = (1, 1, 1)
scene.view_settings.view_transform = 'Standard'
scene.render.filepath = str(WORK / 'silhouette.png')
bpy.ops.render.render(write_still=True)
image = bpy.data.images.load(str(WORK / 'silhouette.png'))
pixels = np.empty(192 * 108 * 4, dtype=np.float32); image.pixels.foreach_get(pixels)
luminance = pixels.reshape(-1, 4)[:, :3].mean(axis=1)
coverage = float((luminance < 0.5).mean())
assert 0.02 < coverage < 0.4, coverage          # the subject reads as a distinct shape, neither lost nor cramped
```

The following fixture renders both renderer-specific toon routes. It checks
render execution and non-flat pixels, not successful anime art direction.

```python verify
import bpy
import numpy as np
from mathutils import Vector

scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16)
obj = bpy.context.object
for polygon in obj.data.polygons:
    polygon.use_smooth = True
mat = bpy.data.materials.new('cel'); mat.use_nodes = True
obj.data.materials.append(mat)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -5, 1)
cam.rotation_euler = (-cam.location).to_track_quat('-Z', 'Y').to_euler()
sun = bpy.data.objects.new('key', bpy.data.lights.new('key', 'SUN'))
scene.collection.objects.link(sun)
sun.rotation_euler = Vector((3, 4, -5)).to_track_quat('-Z', 'Y').to_euler()
sun.data.energy = 3
scene.render.film_transparent = True

for engine in ('CYCLES', 'BLENDER_EEVEE'):
    scene.render.engine = engine
    if engine == 'CYCLES':
        scene.cycles.samples = 8
    nodes = mat.node_tree.nodes; nodes.clear(); links = mat.node_tree.links
    output = nodes.new('ShaderNodeOutputMaterial')
    if engine == 'CYCLES':
        toon = nodes.new('ShaderNodeBsdfToon')
        toon.inputs['Color'].default_value = (0.3, 0.6, 0.15, 1)
        toon.inputs['Size'].default_value = 0.5
        toon.inputs['Smooth'].default_value = 0
        links.new(toon.outputs[0], output.inputs['Surface'])
    else:
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        convert = nodes.new('ShaderNodeShaderToRGB')
        ramp = nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'
        ramp.color_ramp.elements[0].color = (0.03, 0.06, 0.02, 1)
        ramp.color_ramp.elements[1].position = 0.45
        ramp.color_ramp.elements[1].color = (0.3, 0.6, 0.15, 1)
        emission = nodes.new('ShaderNodeEmission')
        links.new(diffuse.outputs[0], convert.inputs[0])
        links.new(convert.outputs['Color'], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], emission.inputs['Color'])
        links.new(emission.outputs[0], output.inputs['Surface'])
    scene.render.filepath = str(WORK / (engine + '.png'))
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath)
    pixels = np.array(image.pixels[:]).reshape(-1, 4)
    assert tuple(image.size) == (64, 64)
    assert np.isfinite(pixels).all() and pixels[:, :3].max() > 0.1
    solid = pixels[pixels[:, 3] > 0.99, :3].mean(axis=1)
    assert len(solid) > 100
    assert np.quantile(solid, 0.9) - np.quantile(solid, 0.1) > 0.05
```
