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

## Accept a LOD chain

Record a row per LOD: source revision/hash, evaluated triangles, expected UV and
colour layers (name/domain/type), ordered material mapping, pivot/bounds, intended
switch screen size or distance, and visual findings. Engine screen-size conventions
differ; calibrate in the actual engine rather than transferring a generic percentage.

- **Shader data:** preserve required UVs, wind masks, colour channels and their
  semantics through simplification and export. Check evaluated data and a saved,
  reopened file. Matching layer names is insufficient: check finite values,
  required ranges and root/tip or other semantic samples. Interpolated values can
  be valid where topology changes; define tolerances before accepting them.
- **Material mapping:** compare ordered slots and face assignments, not just slot
  count. A legitimate remap needs explicit correspondence and verification that
  leaves, glass or other regions still use the intended material. Check for empty
  slots and out-of-range indices. The fixture below checks used slots but does not
  prove spatial equivalence of every material region.
- **Visual transition:** render LOD0 and each lower LOD from the same camera at
  its switch size, then inspect silhouette, holes, shading and alpha coverage.
  Check multiple directions and a camera sweep for popping. Keep the accepted
  editable LOD0; regenerate dependent LODs after relevant source/shader changes.

A lower triangle count cannot compensate for a lost canopy, changed pivot or
missing shader attribute. Retain the failed candidate and repair the specific
defect. See [vegetation](../blender-vegetation/SKILL.md) for foliage-specific LODs.
Blender checks establish native preparation; claim engine transitions, physics,
wind and performance only after checking them in the destination runtime.

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

# Two material regions and a declared wind-mask schema must survive simplification.
for name in ('wood', 'trim'):
    crate.data.materials.append(bpy.data.materials.new(name))
for polygon in crate.data.polygons:
    polygon.material_index = polygon.index % 2
wind = crate.data.color_attributes.new(name='VC_Wind', type='FLOAT_COLOR', domain='POINT')
crate.data.color_attributes.active_color = wind
for vertex, colour in zip(crate.data.vertices, wind.data):
    colour.color = (vertex.co.z + 0.5, 0, 0, 1)

def shader_contract(obj):
    import math
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        assert [m.name if m else None for m in mesh.materials] == ['wood', 'trim'], 'material order'
        assert {p.material_index for p in mesh.polygons} == {0, 1}, 'material regions'
        assert 'UVMap' in mesh.uv_layers, 'UV layer'
        attribute = mesh.color_attributes.get('VC_Wind')
        assert attribute is not None, 'wind attribute'
        assert (attribute.domain, attribute.data_type) == ('POINT', 'FLOAT_COLOR'), 'wind schema'
        for vertex, colour in zip(mesh.vertices, attribute.data):
            weight = colour.color[0]
            assert math.isfinite(weight) and -1e-6 <= weight <= 1 + 1e-6, 'wind range'
            # The cube's linear Z mask permits interpolation as vertices change.
            assert abs(weight - (vertex.co.z + 0.5)) < 0.03, 'wind semantics'
    finally:
        evaluated.to_mesh_clear()

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

shader_contract(crate); shader_contract(lod1)
assert (crate.matrix_world.translation - lod1.matrix_world.translation).length < 1e-7
# A damaged LOD must be rejected even when its triangle reduction still passes.
bad = lod1.copy(); bad.data = lod1.data.copy(); scene.collection.objects.link(bad)
bad.data.color_attributes.remove(bad.data.color_attributes['VC_Wind'])
try:
    shader_contract(bad)
except AssertionError as error:
    assert str(error) == 'wind attribute', str(error)
else:
    raise AssertionError('lost shader data was accepted')
bad.data.materials.clear()
bad.data.materials.append(bpy.data.materials['trim']); bad.data.materials.append(bpy.data.materials['wood'])
try:
    shader_contract(bad)
except AssertionError as error:
    assert str(error) == 'material order', str(error)
else:
    raise AssertionError('reordered materials were accepted')
bpy.data.objects.remove(bad, do_unlink=True)
native = str(WORK / 'lod-chain.blend')
bpy.ops.wm.save_as_mainfile(filepath=native)
bpy.ops.wm.open_mainfile(filepath=native)
crate = bpy.data.objects['SM_Crate']; lod1 = bpy.data.objects['SM_Crate_LOD1']
shader_contract(crate); shader_contract(lod1)

# Export both LODs, with explicit colour export; check the lower LOD too.
glb = str(WORK / 'SM_Crate.glb')
bpy.ops.object.select_all(action='DESELECT'); crate.select_set(True); lod1.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True,
                          export_apply=True, export_vertex_color='ACTIVE')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert {o.name for o in meshes} == {'SM_Crate', 'SM_Crate_LOD1'}
for obj in meshes:
    imported = obj.data; imported.calc_loop_triangles()
    expected = lod0 if obj.name == 'SM_Crate' else lod1_tris
    assert len(imported.loop_triangles) == expected
    assert all(abs(d - 1.0) < 0.03 for d in obj.dimensions), tuple(obj.dimensions)
    assert [m.name for m in imported.materials] == ['wood', 'trim']
    assert {p.material_index for p in imported.polygons} == {0, 1}
    assert 'UVMap' in imported.uv_layers
    colour = imported.color_attributes.active_color
    assert colour is not None
    for index, loop in enumerate(imported.loops):
        data_index = index if colour.domain == 'CORNER' else loop.vertex_index
        expected_weight = imported.vertices[loop.vertex_index].co.z + 0.5
        assert abs(colour.data[data_index].color[0] - expected_weight) < 0.03
```
