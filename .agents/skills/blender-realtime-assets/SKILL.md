---
name: blender-realtime-assets
description: Prepare Blender assets for game engines, the web and other realtime targets. Covers budgets measured after modifiers, LODs, collision proxies, texel density and atlases, naming, pivots and axes, the glTF and FBX export settings that matter, and checking the exported file by re-importing it. Use for Unity, Unreal, Godot, three.js, WebXR or modding targets.
---

# Build assets for realtime engines

A realtime asset is judged in its engine at its viewing distance. Budgets, LODs and textures follow from how large the asset appears on screen, not from a universal polygon count. Keep the editable source with its modifiers live, and make every destructive step (applying modifiers, decimation, triangulation, baking) on an export copy.

## Inventory and budget

- **Inventory first:** units and scale, applied transforms, origins, the modifier stack, material slots, UV maps and any custom normals.
- **Measure the right things together:** triangles after modifiers and triangulation, draw calls (roughly one per material per mesh), texture memory, and file size. Polycount alone hides the material and texture cost. Read triangles from the evaluated mesh: `len(eval_mesh.loop_triangles)`.
- **Set the budget from screen size.** A prop that covers 5% of a 1080p screen does not need hero density. Estimate the tri cost of the repeated features first (openings, bolts, rails), then simplify all of them the same way.

## Geometry for engines

- **Scale and pivots.** Use real-world scale, with 1 unit = 1 m. Put the pivot where the engine will place the asset: at ground level at the footprint centre for buildings and props, and at the hinge for doors. Apply rotation and scale before export.
- **Shading.** Use hard edges where UV seams are; a split normal without a UV seam wastes nothing, but one across a continuous UV shell causes bake seams. Smooth by Angle (a modifier since 4.1) or explicit sharp edges define the split normals. A Weighted Normal modifier gives flat-shaded hard-surface assets clean shading at low tri counts.
- **Topology.** Remove internal faces, hidden caps and loose geometry. Triangulate in Blender before baking (Triangulate modifier, `quad_method='BEAUTY'`) so the baker, the exporter and the engine all use the same triangles. Different triangulations make baked normal maps shade wrongly.
- **LODs.** Make them on purpose. As a starting point, LOD1 has 50–60% of LOD0's triangles and LOD2 25–30%. Keep the silhouette and the rhythm of repeated features, and bake the small detail into the normal map. Test at the switch distance. Rebuild the LODs whenever LOD0 changes; a stale LOD is a common shipped bug.
- **Collision.** Build simple convex proxies with low counts. Unreal imports `UCX_<MeshName>_00` convex pieces from FBX. Other engines take a primitive or a simplified mesh. Never use the render mesh as collision for dynamic objects.

## Textures and materials

- **Texel density.** Keep it consistent across a kit; measure it with the harness [`uv-report`](../../../docs/guides/UV_REPORT.md) or the [UV skill](../blender-uv/SKILL.md). Use power-of-two sizes. Pad islands about 8 px at 2K, and dilate the baked maps past the island edges.
- **Channel packing.** Pack data maps where the engine expects it. ORM means R = ambient occlusion, G = roughness, B = metallic, which is the glTF convention for G and B. Mark every data map Non-Color and the colour map sRGB. Never let a view transform touch data maps; check saved pixel values numerically when an engine reads exact codes.
- **What exports.** glTF carries Principled BSDF factors and image textures only; procedural nodes must be [baked](../blender-baking/SKILL.md) first. Normal maps for glTF and Unity use OpenGL (+Y); Unreal uses DirectX (−Y green).
- **No baked lighting** in the colour map of an asset that will be relit.

## Naming and export

- **Name stems.** Use stable stems that pair meshes, materials and textures: `SM_Crate`, `M_Crate`, `T_Crate_D`, `T_Crate_N`, `T_Crate_ORM`, `SM_Crate_LOD1`. Remove `.001` suffixes before export; engines treat them as different assets.
- **glTF** (`bpy.ops.export_scene.gltf`). Use the `GLB` format for a single file. Set `use_selection=True` so only the intended objects export. `export_apply=True` applies modifiers, and `export_yup=True` (the default) converts Blender's Z-up. Draco compression shrinks web files, but the client must support it.
- **FBX** (`bpy.ops.export_scene.fbx`). Set `apply_scale_options='FBX_SCALE_UNITS'` and `axis_forward='-Z', axis_up='Y'` for Unity-style targets. Use `use_selection=True` and `mesh_smooth_type='FACE'` or `'EDGE'` so smoothing exports. For Unreal, turn off `bake_anim` for static meshes.
- **Animation.** Animated exports also need the [rigging](../blender-rigging/SKILL.md) skill's export rules: deform bones only, at most four influences per vertex, and baked actions.
- **Check the file.** Re-import the exported file into an empty scene and check:
  - its dimensions and facing;
  - the triangle count;
  - the material count;
  - the UV maps;
  - that each texture reference resolves.

  "The export command returned FINISHED" is not evidence. In a harness project, `deliver-glb` performs this round trip for a checkpoint (see [GLB delivery](../../../docs/guides/GLB_DELIVERY.md)).

```python verify
import bpy

scene = bpy.context.scene
# Source with live modifiers: a bevelled crate.
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5)); crate = bpy.context.object
crate.name = 'SM_Crate'
bevel = crate.modifiers.new('bevel', 'BEVEL'); bevel.width, bevel.segments = 0.02, 2
crate.modifiers.new('tri', 'TRIANGULATE')

# Budget from the evaluated mesh, after modifiers and triangulation.
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_mesh = crate.evaluated_get(depsgraph).to_mesh(); eval_mesh.calc_loop_triangles()
lod0 = len(eval_mesh.loop_triangles); crate.evaluated_get(depsgraph).to_mesh_clear()
assert lod0 > 12

# LOD1 on a copy: decimate to about 55%, measured after evaluation.
lod1 = crate.copy(); lod1.data = crate.data.copy(); lod1.name = 'SM_Crate_LOD1'
scene.collection.objects.link(lod1)
lod1.modifiers.new('decimate', 'DECIMATE').ratio = 0.55
depsgraph = bpy.context.evaluated_depsgraph_get()
m1 = lod1.evaluated_get(depsgraph).to_mesh(); m1.calc_loop_triangles(); lod1_tris = len(m1.loop_triangles)
lod1.evaluated_get(depsgraph).to_mesh_clear()
assert 0.4 * lod0 <= lod1_tris <= 0.7 * lod0, (lod0, lod1_tris)

# Export only the LOD0 crate as GLB with modifiers applied, then re-import into an empty scene and measure.
glb = str(WORK / 'SM_Crate.glb')
bpy.ops.object.select_all(action='DESELECT'); crate.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert [o.name for o in meshes] == ['SM_Crate'], [o.name for o in meshes]
imported = meshes[0].data; imported.calc_loop_triangles()
assert len(imported.loop_triangles) == lod0, (len(imported.loop_triangles), lod0)
assert all(abs(d - 1.0) < 1e-4 for d in meshes[0].dimensions), tuple(meshes[0].dimensions)
```
