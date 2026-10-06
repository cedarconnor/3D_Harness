---
name: dcc-materials
description: Build and revise physically scaled Blender materials, inspect shared users, and evaluate PBR channels, glass, roughness and motivated wear in a consistent lighting setup.
---

# Author surfaces as physical materials

Read the project's palette, surface references, physical tile sizes and shared material identities. Inspect native nodes and image connections, not just material names. Establish the base response first; add large-scale weathering only after the clean material reads correctly.

Record each texture's channel, color space, normal convention and real-world coverage. Albedo normally uses sRGB and scalar/normal data uses Non-Color; validate the actual connected image, not merely its filename. Keep UV/projection scale tied to meters when resizing geometry. A 1.4 m brick source tile is an input from this project's kit, not a universal masonry standard.

For blended ground, keep material masks separate from metric texture coordinates. A shader can read a named UV mask while the active render UV supplies texture tangents; verify both actual bindings after saving. Record source units before converting tile coverage to meters, and compare packed image hashes with the source receipt. The [ground example](../../../docs/GROUND_RECIPE.md) uses world-position texture scaling and a separate two-channel UV mask. These checks establish bindings and provenance; fixed-lighting review still decides whether scale, seams and repetition look convincing.

Inspect all users before editing a shared definition. `dcc_harness.craft_blender.set_material_scalar(material_id, node_name, socket_name, value, expected_users)` checks exact object identities across Blender datablocks, including hidden/other-scene users. It supports unlinked Principled roughness, metallic, IOR and transmission controls; driven inputs require an explicit upstream edit. The function does not journal or save: use a reserved project edit and independently inspect the result.

Worked revision: change the shared metal Roughness from 0.38 to 0.58 while preserving its other inputs and every object's geometry/binding. Enumerate the actual users rather than supplying only the visible tool. Compare both a standard lookdev view and the material inside the scene; roughness and lighting must not be changed together when diagnosing that parameter.

For glass, inspect real pane thickness, transmission, IOR, reflected surroundings and interior depth. A dark pane with no visible reflection/transmission may read as paint despite valid settings. For dampness, tie changes to drainage, porous absorption, sheltered areas and joints. Use coherent wear at contact/exposure zones; avoid uniform grunge across unrelated materials.

Require a whole-scene view and a material close-up at locked camera/light/color settings. Check visible seams, repetition, scale and the relative finish of adjacent materials. Pack dependencies and reopen the saved file. Numerical PBR validity is separate from realistic appearance. See [craft qualification](../../../docs/CRAFT_SKILLS.md).
