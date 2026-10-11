---
name: blender-craft
description: Index of the Blender craft skill library. Use it to pick the right skills for any Blender task (modeling, sculpting, CAD and design engineering, UVs, materials, baking, Geometry Nodes, lighting, cameras, rendering, compositing, animation, rigging, skinning, mocap, matchmove, simulation, hair, Grease Pencil, motion design, realtime export and pipeline), plus the rules that apply to all of them.
---

# Blender craft library

These skills hold general Blender 5.x craft knowledge. Each code example in them, a `python verify` block, runs and passes in Blender 5.1.1 through `scripts/qualify_blender_skills.py`. Load only the skills a task needs.

In a 3D Harness project, the harness skills still govern the work:

- [`dcc-harness`](../dcc-harness/SKILL.md) for sessions and checkpoints;
- [`dcc-build-revise`](../dcc-build-revise/SKILL.md) for scoped edits;
- [`dcc-review-continue`](../dcc-review-continue/SKILL.md) for review.

These skills say *how* to do the craft inside that workflow. The [library guide](../../../docs/guides/BLENDER_SKILL_LIBRARY.md) records sources, verification and limits.

## Rules for every Blender task

1. **Inspect before changing.** Check the version, units, selection, mode, and the shared users of anything you touch. Never assume names.
2. **Real scale.** Work at real scale (1 unit = 1 m) with applied transforms, and write out all three `transform_apply` arguments.
3. **Measure the evaluated result.** Modifiers, nodes, constraints and simulations change what renders; read it from the depsgraph, not the base data.
4. **Check what the operator returned.** Several fail silently: bakes `CANCELLED`, the Manifold boolean on non-manifold input, unbound deform cages, empty bone-heat groups.
5. **Render to judge appearance.** A numeric pass is not a visual pass; look at the images, and record the settings that made them.
6. **Change one variable at a time.** Compare with locked camera, light, exposure and samples.
7. **Keep sources editable.** Do destructive steps (apply, decimate, triangulate, bake) on copies or export files.
8. **Report honestly.** Separate what was measured, what was looked at, and what still needs the artist's judgment.

## Skills by area

| Area | Skill | Use when |
|---|---|---|
| Foundations | [blender-python](../blender-python/SKILL.md) | Writing any bpy script; API changes 4.0–5.1; background and MCP execution |
| | [blender-visual-design](../blender-visual-design/SKILL.md) | Hierarchy, silhouette, value, colour, composition and storytelling decisions |
| | [blender-pipeline](../blender-pipeline/SKILL.md) | Files, paths, packing, linking and overrides, asset libraries, USD, Alembic, FBX, OBJ, STL |
| Modeling | [blender-reference-modeling](../blender-reference-modeling/SKILL.md) | Building from photos, drawings or orthographic views; camera matching |
| | [blender-hard-surface](../blender-hard-surface/SKILL.md) | Products, machines, props: booleans, bevels, subdivision, weighted normals |
| | [blender-sculpt-retopo](../blender-sculpt-retopo/SKILL.md) | Organic sculpting, remeshing, retopology and deformation topology |
| | [blender-precision-cad](../blender-precision-cad/SKILL.md) | Exact dimensions, tolerances, CAD/STEP/STL interchange, 3D printing |
| | [blender-geometry-nodes](../blender-geometry-nodes/SKILL.md) | Procedural modeling, scattering, instancing, node-based motion, simulation zones |
| Surfaces | [blender-uv](../blender-uv/SKILL.md) | Seams, unwrapping, packing, texel density, UDIMs, lightmap UVs |
| | [blender-shading](../blender-shading/SKILL.md) | Principled BSDF, PBR values, procedural textures, glass, wear |
| | [blender-baking](../blender-baking/SKILL.md) | Procedural-to-image, high-to-low normal and AO bakes, channel packing |
| Look | [blender-lighting](../blender-lighting/SKILL.md) | Light rigs, HDRI and sky, product lighting, light linking, EEVEE probes |
| | [blender-camera](../blender-camera/SKILL.md) | Lenses, framing, depth of field, camera moves, turntables and loops |
| | [blender-rendering](../blender-rendering/SKILL.md) | Cycles and EEVEE settings, colour management, passes, output, long renders |
| | [blender-compositing](../blender-compositing/SKILL.md) | The 5.x compositor node group, glare, mattes, plates, EXR |
| Motion | [blender-animation](../blender-animation/SKILL.md) | Keyframing, timing, Graph Editor, NLA, slotted actions from Python |
| | [blender-motion-design](../blender-motion-design/SKILL.md) | Titles, motion graphics, product and social video, the Video Sequencer |
| | [blender-grease-pencil](../blender-grease-pencil/SKILL.md) | 2D animation, storyboards, Line Art, Grease Pencil v3 scripting |
| Characters | [blender-rigging](../blender-rigging/SKILL.md) | Armatures, bone collections, IK/FK, drivers, Rigify, mechanical rigs |
| | [blender-skinning](../blender-skinning/SKILL.md) | Weights, bone-heat failures, preserve volume, correctives, deform cages |
| | [blender-mocap](../blender-mocap/SKILL.md) | BVH/FBX import, curve cleanup, retargeting, root motion |
| | [blender-hair](../blender-hair/SKILL.md) | Curves hair and fur, grooming node groups, hair shading |
| Effects | [blender-simulation](../blender-simulation/SKILL.md) | Rigid body, cloth, fluids, particles, caches and baking |
| | [blender-matchmove](../blender-matchmove/SKILL.md) | Camera tracking, solving, scene orientation, CG over footage |
| Delivery | [blender-realtime-assets](../blender-realtime-assets/SKILL.md) | Game and web assets: budgets, LODs, collision, glTF and FBX export |

## Common combinations

- **Product shot:** reference-modeling → hard-surface → uv → shading → lighting → camera → rendering, with visual-design for the frame.
- **Game prop:** hard-surface → uv → baking → realtime-assets, using `uv-report` for texel density.
- **3D-printed part:** precision-cad, with pipeline for STL and STEP exchange.
- **Animated character:** sculpt-retopo → uv → shading → rigging → skinning → animation (or mocap), with hair where needed.
- **Environment:** the harness `dcc-plan-environment` and `dcc-environment-assembly`, with geometry-nodes for scattering, shading and lighting.
- **CG in live footage:** matchmove → lighting (match the plate) → rendering (shadow catcher, holdouts) → compositing.
- **Motion graphics:** motion-design with animation, camera, geometry-nodes and rendering.
- **Effects shot:** simulation, with geometry-nodes for simulation zones and rendering for motion blur and volumes.
