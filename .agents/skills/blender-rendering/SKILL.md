---
name: blender-rendering
description: Configure and run Blender 5.x renders that are correct, comparable and efficient. Covers choosing Cycles or EEVEE, colour management (AgX, Khronos PBR Neutral, ACES, Standard, exposure, looks), Cycles sampling, denoising and light paths, EEVEE ray tracing and probes, passes and view layers, image and video output, and long renders through MCP or background Blender.
---

# Render deliberately

A render is evidence only if its settings are known. For every image you keep, record:

- the engine, samples and denoiser;
- the view transform, look and exposure;
- the camera, frame and resolution;
- the file it came from.

In a harness project, render with `dcc-harness render` against the project's `review_views`, which records all of these. See the [everyday workflow](../../../docs/guides/EVERYDAY_WORKFLOW.md).

## Choose the engine

- **Cycles** (`'CYCLES'`) is the path tracer. Use it for physically correct glass, caustics, subsurface scattering, product and final lookdev, and anything compared against photographs.
- **EEVEE** (`'BLENDER_EEVEE'` in 5.x; `'BLENDER_EEVEE_NEXT'` only in 4.2–4.5) is the rasterizer, with optional screen and probe ray tracing. Use it for fast previews, motion graphics, stylized work and long animations where speed matters. It needs baked volume probes for bounce light and has limits with refraction depth and light linking.
- **Workbench** (`'BLENDER_WORKBENCH'`) is for clay and silhouette reviews. Use flat or studio lighting, a mid-gray (about 0.6) material, and the Standard view transform. It is good for checking form without materials getting in the way.

Gate the engine string on the version (`bpy.app.version >= (5, 0, 0)`) in code that may meet 4.x files.

## Colour management decides what the numbers mean

- **View transforms (5.1).** `AgX` is the default since 4.0. The others are `Khronos PBR Neutral`, `Standard`, `Filmic`, `ACES 1.3`, `ACES 2.0`, `False Color` and `Raw`.
  - **AgX** handles bright highlights gracefully and desaturates them. Its looks carry a prefix: `'AgX - Punchy'`, `'AgX - Medium High Contrast'` and so on.
  - **Khronos PBR Neutral** keeps the base colour close to what was authored. Use it for product and e-commerce colour accuracy.
  - **Standard** is a plain sRGB transfer. Use it for diagnostics, for UI and graphics that must match their hex values, and for compositing plates that are already display-referred.
  - **False Color** shows exposure zones; use it to check that the key sits in mid-range and nothing important clips.
- **Exposure.** `view_settings.exposure` is in stops and applies after rendering. Prefer fixing the light levels; use exposure for a global trim, and keep it constant across a comparison.
- **What gets baked in.** PNG, JPEG and video are written through the view transform. OpenEXR stores scene-linear data without it. Never load an already display-encoded PNG into a compositor or texture and run it through AgX again, because it gets tone-mapped twice.
- **Changing the transform.** Changing the view transform between two renders makes them incomparable. Change it once, on purpose, and re-render the references.

## Cycles

- **Sampling.** Use adaptive sampling (`use_adaptive_sampling`, `adaptive_threshold` 0.01 for finals and 0.05 for drafts) with a sample cap: 128–256 for drafts, 512–4096 for finals depending on noise. Set `seed` explicitly; use `use_animated_seed` only for animations. Note that the 5.1 default is 4096.
- **Denoising.** OpenImageDenoise with albedo and normal passes is the default, and it runs on GPU too. The denoiser erases faint detail such as fine print, embossing, thin wires and texture grain. Judge those at full resolution, with more samples and denoising off or at a higher quality. A denoised preview once made a failed fix look successful.
- **Light paths.** The defaults are 12 maximum bounces, 4 diffuse, 4 glossy, 12 transmission and 8 transparent. For stacked glass and liquids, raise transmission to 12–16. For many alpha-mapped leaves, raise transparent bounces to 16–32, or leaves turn black.
  - **Clamping.** `sample_clamp_indirect` (default 10) removes fireflies at the cost of energy. Lower it only after finding the source of the fireflies, such as a small bright light seen through glossy paths.
  - **Filter Glossy.** `blur_glossy` (0.5–1) also reduces caustic noise.
- **Persistent data.** Use `render.use_persistent_data = True` for animations with static geometry.
- **Device.** Compute devices are a user preference (`preferences.addons['cycles'].preferences`). Report the device that was used, not the one you requested.

## EEVEE (5.x)

- **Ray tracing.** Enable `scene.eevee.use_raytracing` for reflections and refraction. `ray_tracing_method` `'SCREEN'` traces screen space and falls back to probes; `'PROBE'` uses probes only.
- **Other settings.** `use_fast_gi` adds approximate horizon-scan GI. `taa_render_samples` defaults to 64. Shadows improve with `shadow_ray_count` and `shadow_step_count`.
- **Removed settings.** These no longer exist: `use_bloom`, `use_ssr`, `use_gtao` and `use_soft_shadows`. Make bloom with the compositor's Glare node; see [compositing](../blender-compositing/SKILL.md).
- **Transparency.** It is per material: `material.surface_render_method = 'DITHERED'` (the default, sorted correctly) or `'BLENDED'` (true blending, with sorting problems).
- **Probes.** Bake the volume probes after the lights or geometry change.

## Passes, view layers and holdouts

- **Passes.** Enable only the passes you use: `view_layer.use_pass_z`, `use_pass_normal`, `use_pass_mist`, Cryptomatte (`use_pass_cryptomatte_object` and `use_pass_cryptomatte_material`), shader AOVs (`view_layer.aovs`) and light groups (`view_layer.lightgroups`, with `obj.lightgroup`). Store denoising data with `view_layer.cycles.denoising_store_passes` if you will denoise in the compositor.
- **View layers and holdouts.** Use them to split foreground and background, or to render a holdout with the collection's `holdout` flag or `obj.is_holdout`. `film_transparent` gives an alpha background.
- **Multilayer EXR.** `OPEN_EXR_MULTILAYER` keeps every pass in one file for compositing.

## Output and long renders

- **Stills.** PNG, 16-bit for grading, or EXR (half float, compressed with DWAA/ZIP) for linear data.
- **Animation.** Render an image sequence (`PNG` or `OPEN_EXR`), not straight to video: a crash then costs one frame. Set `render.use_overwrite = False` and `use_placeholder = True`, so that restarts and several machines continue rather than repeat frames.
- **Video.** In 5.x set `image_settings.media_type = 'VIDEO'` before `file_format = 'FFMPEG'`, then choose the codec (`H264`, `H265`, `AV1`, `PRORES`). Encode sequences with ffmpeg afterwards when you need control: `-crf 18 -pix_fmt yuv420p` for review, and ProRes 4444 with `yuva444p10le` for alpha.
- **Long jobs through MCP.** These exceed the call timeout. Start them in a background Blender, or with the harness's `render --detach`, then poll the output files. A timed-out call does not mean the render stopped.
- **Check the output.** Confirm that every expected file exists and is not empty, check the resolution, and look at the pixels. Render a hard frame at final settings before queueing a long sequence: motion blur, the most glass, the busiest view.

```python verify
import bpy
import numpy as np

scene = bpy.context.scene
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (0, -4, 0), (1.5708, 0, 0); scene.camera = cam
light = bpy.data.objects.new('key', bpy.data.lights.new('key', 'AREA')); light.data.energy = 300
light.location = (2, -3, 3); scene.collection.objects.link(light)

# Colour management names as they are in 5.1, including the prefixed AgX looks.
vs = scene.view_settings
assert vs.view_transform == 'AgX'
vs.look = 'AgX - Punchy'; assert vs.look == 'AgX - Punchy'
for transform in ('Khronos PBR Neutral', 'Standard', 'ACES 2.0', 'False Color'):
    vs.view_transform = transform; assert vs.view_transform == transform
vs.view_transform, vs.look, vs.exposure = 'Standard', 'None', 0.0

# A small, seeded, adaptive Cycles render with denoising off, written as PNG and read back.
scene.render.engine = 'CYCLES'
scene.cycles.samples, scene.cycles.use_adaptive_sampling, scene.cycles.adaptive_threshold = 16, True, 0.05
scene.cycles.seed, scene.cycles.use_denoising, scene.cycles.device = 7, False, 'CPU'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 96, 64, 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(WORK / 'still.png')
bpy.ops.render.render(write_still=True)
image = bpy.data.images.load(str(WORK / 'still.png'))
assert tuple(image.size) == (96, 64)
pixels = np.empty(96 * 64 * 4, dtype=np.float32); image.pixels.foreach_get(pixels)
assert pixels.reshape(-1, 4)[:, :3].max() > 0.2          # something lit is in frame

# EEVEE in 5.x: the engine id, ray tracing, and the removed legacy toggles.
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_raytracing = True
assert not any(hasattr(scene.eevee, k) for k in ('use_bloom', 'use_ssr', 'use_gtao'))

# Video output: media type first, then the container and codec.
scene.render.image_settings.media_type = 'VIDEO'
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format, scene.render.ffmpeg.codec = 'MPEG4', 'H264'
assert scene.render.image_settings.file_format == 'FFMPEG'
```
