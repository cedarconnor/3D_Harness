---
name: blender-uv
description: Unwrap and lay out UVs in Blender 5.x for texturing, baking and lightmaps. Covers seam placement, choosing unwrap methods and their real parameters, Smart UV Project, island packing with exact pixel margins, texel density targets and measurement, mirrored and flipped islands, UDIMs, lightmap UVs, and checking UVs with the harness uv-report.
---

# UV unwrapping

UVs decide how a 2D texture lands on the surface. They need a consistent texel density, little stretching, seams where nobody looks, and padding large enough for the texture's mip levels and bakes.

## Seams

- **Where seams go:** on hard edges (over about 60°), where the object is occluded or faces the ground, along material boundaries, and where the real object has a seam (panels, cloth seams).
- **Where they don't:** never across a continuous visible surface such as a face, a hero panel or the top of a table.
- **Shading splits.** Hard-surface meshes with sharp-edge or harden-normal shading should also split their UVs at the sharp edges. A shading split inside one UV island makes baked normal maps show seams.
- **Grain direction.** Wood grain, fabric weave and brushed metal have a direction. Orient the islands so that the texture's grain runs along each member's long axis. Check one vertical and one horizontal member before mapping the whole kit; see [architecture](../dcc-architecture/SKILL.md).

## Unwrap methods (5.1)

- **`bpy.ops.uv.unwrap`.** `method` is `'ANGLE_BASED'`, `'CONFORMAL'` (the default) or `'MINIMUM_STRETCH'`. Pass it explicitly: angle-based is usually better for organic shapes. Use `margin` and `margin_method`. It works on the selected faces in Edit Mode.
- **`bpy.ops.uv.smart_project`.** For hard-surface and kitbash shapes.
  - `angle_limit` is in **radians** (the default 1.1519 is 66°). Passing `66` is a common bug.
  - Use 30–45° for hard surfaces and 60–66° for blobby shapes, and `area_weight` 0.5–1 when face sizes vary.
  - Its poll fails in Object Mode: enter Edit Mode and select all first.
- **Projections.** Use `uv.cube_project`, `cylinder_project` and `sphere_project` for primitives. A box-mapped material (Image Texture `projection='BOX'`) avoids UVs entirely for tiling surfaces.
- **Physical scale.** Keep materials that must stay at a physical scale (bricks, tiles, planks) on UVs or coordinates measured in metres. Resizing an object must not resize its bricks; see [shading](../blender-shading/SKILL.md).

## Packing

- **`bpy.ops.uv.pack_islands`.**
  - `shape_method`: `'CONCAVE'` (tightest), `'CONVEX'` or `'AABB'` (fastest).
  - `rotate_method`: `'ANY'`, `'CARDINAL'` or `'AXIS_ALIGNED'`. Use `'AXIS_ALIGNED'` or none for directional textures.
  - `margin_method` and `margin`. For exact pixel padding use `margin_method='FRACTION'` with `margin = pad_px / texture_px` (8 px at 2048 is 0.0039). It is slower, but exact.
- **Padding.** Use at least 4 px at 1K, 8 px at 2K and 16 px at 4K, more for assets seen at a distance (mip levels). Bakes need dilation, the bake margin, past the islands.
- **Mirrored halves.** A Mirror modifier's copy reuses the original's UV space, which halves texture memory.
  - Without `use_mirror_u`, the copy's islands are **flipped**: the same UVs with reversed winding, so a negative signed area.
  - With `use_mirror_u`, they are mirrored in U instead, and keep a positive area.
  - Either way they overlap the original. That is fine for tiling and colour textures, and wrong for AO, lightmaps and unique baked normals unless you move the copy out of the 0–1 square with the modifier's `offset_u` (+1) before baking.
- **Flipped islands.** Detect them by the sign of the UV face area in loop order. A flipped island on non-mirrored geometry is a mistake; fix it before baking normal maps.

## Texel density

- **Definition.** Density in px/m = √(UV area ÷ world area) × texture size, with the world area taken after applying scale.
- **Targets** depend on viewing distance and are set per project. Rough guides:
  - first-person and hero assets: 512–1024 px/m (5.12–10.24 px/cm);
  - third-person and standard props: 256–512 px/m;
  - background and top-down: 128–256 px/m or less.
- **Consistency.** Keep density consistent across a kit or scene; neighbouring objects with different densities read as wrong immediately. Flag islands more than about 20% off the target.
- **Measuring in a harness project.** `dcc-harness uv-report SAVED.blend --blender PATH --output-dir NEW --project P` measures per-mesh density, self-overlap and the share of UVs outside 0–1 against the project's `uv_targets` (see [UV report](../../../docs/guides/UV_REPORT.md)). Its density is a whole-mesh average, so check local stretching visually with a checker texture.

## UDIMs and lightmaps

- **UDIMs.** Use them for hero assets that need more resolution than one map: tile 1001 is 0–1, 1002 is 1–2 in U, and so on.
  - Create a tiled image with `bpy.data.images.new(name, w, h, tiled=True)`.
  - `image.tiles.new(1002)` creates a tile with no pixel buffer, so `save()` then fails for it. Fill tiles with `bpy.ops.image.tile_add(number=..., fill=True)` under an Image Editor context override. Then save with `filepath_raw = '.../name.<UDIM>.png'`.
- **Lightmap UVs.** Use a second UV map, made with `bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_NEW_UVLAYER=True)` or a dedicated pack. It must have no overlap, everything inside 0–1, and padding sized for the *lightmap* resolution, which is much lower than the colour map. Name the maps for their purpose (`UVMap`, `Lightmap`) and set `active_render` on the one materials use. A mesh may have at most 8 UV maps.

```python verify
import bpy, bmesh, math
import numpy as np

bpy.ops.mesh.primitive_cube_add(size=2); cube = bpy.context.object
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
assert bpy.ops.uv.smart_project(angle_limit=math.radians(45), island_margin=0.0) == {'FINISHED'}
# Exact pixel padding: 8 px at 2048 as a fraction of the texture.
assert bpy.ops.uv.pack_islands(margin_method='FRACTION', margin=8 / 2048, rotate_method='AXIS_ALIGNED', shape_method='AABB') == {'FINISHED'}
bpy.ops.object.mode_set(mode='OBJECT')

def uv_stats(obj, texture_px):
    mesh = obj.data; mesh.calc_loop_triangles(); n = len(mesh.loop_triangles)
    loops = np.empty(n * 3, dtype=np.int64); mesh.loop_triangles.foreach_get('loops', loops)
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32); mesh.uv_layers.active.data.foreach_get('uv', uv)
    tri = uv.reshape(-1, 2)[loops].reshape(n, 3, 2)
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    signed = 0.5 * (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    world = sum(t.area for t in mesh.loop_triangles) * abs(obj.matrix_world.determinant()) ** (2 / 3)
    return {'density': math.sqrt(abs(signed).sum() / world) * texture_px,
            'flipped': int((signed < 0).sum()), 'inside': bool(((tri >= 0) & (tri <= 1)).all())}

stats = uv_stats(cube, 2048)
assert stats['inside'] and stats['flipped'] == 0, stats
assert 100 < stats['density'] < 1024, stats

# A Mirror copy without mirror_u has flipped islands; with mirror_u it does not; offset_u moves it out of 0-1.
bpy.ops.mesh.primitive_plane_add(size=1, location=(0.5, 0, 0)); half = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
mirror = half.modifiers.new('mirror', 'MIRROR')

def mirrored_stats():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    copy = bpy.data.objects.new('mirrored', bpy.data.meshes.new_from_object(half.evaluated_get(depsgraph)))
    bpy.context.scene.collection.objects.link(copy)
    return uv_stats(copy, 1024)

assert mirrored_stats()['flipped'] == 2             # both triangles of the copy
mirror.use_mirror_u = True
assert mirrored_stats()['flipped'] == 0 and mirrored_stats()['inside']
mirror.offset_u = 1.0
assert not mirrored_stats()['inside']

# A lightmap layer as a second UV map; the render UV stays the first.
bpy.context.view_layer.objects.active = cube; cube.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_NEW_UVLAYER=True)
bpy.ops.object.mode_set(mode='OBJECT')
assert len(cube.data.uv_layers) == 2 and cube.data.uv_layers[0].active_render
```
