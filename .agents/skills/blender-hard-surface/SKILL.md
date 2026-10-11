---
name: blender-hard-surface
description: Model clean hard-surface objects in Blender 5.x such as products, machines, vehicles, props and architecture details. Covers scale-order blockout, construction rules, boolean workflows and solver failures, bevels and bevel weights, subdivision with support loops or creases, weighted normals and Smooth by Angle, modifier order, and programmatic topology checks.
---

# Hard-surface modeling

## Build in scale order

1. **Primary:** the overall masses and silhouette.
2. **Structural:** the major subdivisions, panels and joints that explain how the thing is built.
3. **Transition:** chamfers, fillets, and the shapes that join masses.
4. **Functional:** handles, fasteners, vents and hinges, each with a reason to exist.
5. **Detail:** panel lines, small bevels, text and greebles.

Do not move on while an earlier stage reads wrong. If the middle-scale structure is missing, roll back and add it rather than covering the gap with detail. Check the silhouette at each stage from the project's camera.

## Construction rules

- **Shapes from their rules.**
  - An **opening** is one closed wall plus one named cutter that passes fully through. Never fake it with boxes around a gap.
  - **Stairs** are one step module with an Array modifier, constant offset (0, run, rise), after solving the count and the rise.
  - **Rails, pipes and cables** are curves with a bevel depth, or a profile object.
  - **Lasting fits to a surface** use Shrinkwrap or Surface Deform; **one-time placement** uses snapping.
- **Generated geometry.** Edit the source or the parameters and regenerate. Never hand-fix generated geometry.
- **Real scale.** Model at real scale and apply scale before using Bevel, Solidify, Boolean or physics. All of them measure in object space, so an unapplied scale of (2, 1, 1) bevels twice as wide along X. Check for unapplied scale with `any(abs(s - 1) > 1e-6 for s in obj.scale)`, and for mirroring with `obj.matrix_world.determinant() < 0`. A mesh with several users must be made single-user before its transforms can be applied.
- **Panels and details.**
  - Panel seams follow assembly and maintenance logic.
  - Use at most three panel sizes, and keep the smallest panel at least twice the bevel width.
  - Fasteners go at corners and joins at regular spacing.
  - Greebles need an implied function: roughly 60% of the surface is clean, 30% has medium detail and 10% is dense.

## Booleans

- **Cutters.** Keep them in a hidden `cutters` collection, displayed as wire or bounds, with `hide_render=True`. Union several cutters first, then do one Difference. Cutters must overshoot the surface: coplanar faces are the main cause of boolean artifacts.
- **Solvers (`BooleanModifier.solver`).**
  - `EXACT` is the default. It is robust with coplanar and overlapping input; enable `use_self` and `use_hole_tolerant` only when it fails.
  - `MANIFOLD` (4.5+) is fast, but needs closed manifold operands. **On a non-manifold cutter it silently returns the base mesh unchanged**, with no exception. Check the cutter first, or compare evaluated counts with the modifier on and off.
  - `FLOAT` is for speed only, with `double_threshold`.
- **After applying.** Merge by distance with a tolerance relative to the object's size (about the bounding-box diagonal × 1e-6), and check the result for non-manifold edges.

## Edges: bevel, subdivision or both

- **Bevel modifier.** The 5.1 defaults are `width=0.1`, which is 10 cm and far too large for products, with `segments=1` and `limit_method='ANGLE'` at 30°. Set the width deliberately.
  - **Typical widths:** 5–20 mm for primary edges, 1–3 mm for panel lines, 0.5–1 mm for micro edges.
  - **Selecting edges.** For explicit control, use `limit_method='WEIGHT'` and write the `bevel_weight_edge` float attribute on the edge domain. Bevel weights and creases are attributes in 4.0+, not edge properties.
  - **Profile.** `segments` 2–3 with `profile=0.5` reads as rounded; one segment is a chamfer. Keep `use_clamp_overlap` on unless you need exact widths.
  - **Normals.** `harden_normals=True` writes custom normals for flat faces with rounded edges.
- **Subdivision.** The Subdivision Surface modifier shrinks the cage: a cube becomes a blob. Hold the edges with one of these:
  - **Support loops.** Portable to any engine; the closer the loop, the tighter the edge.
  - **Creases.** Write the `crease_edge` attribute (0..1). It is cheap but usually lost on export.
  - **A bevel before subdivision.** It survives export once applied.
- **Mid-poly (bevel + weighted normals).** One- or two-segment bevels on hard edges, a Weighted Normal modifier (`mode='FACE_AREA'`, `keep_sharp=True`) and no subdivision. Use it for game and realtime assets with clean shading at low counts. Triangulate before baking or exporting, because the triangulation changes the shading.
- **Smooth shading.** `bpy.ops.object.shade_auto_smooth(angle=math.radians(30))` adds a Smooth by Angle modifier pinned last (`use_pin_to_last`). Auto Smooth itself was removed in 4.1.

## Modifier order

Mirror (`use_clip`, `use_mirror_merge`) → booleans → bevel → subdivision, if any → Weighted Normal → Smooth by Angle (pinned last).

Keep the stack live in the source file; apply it only on export copies or at a planned freeze. Name the modifiers for their purpose (`panel_bevel`, `vent_cut`).

## Check topology programmatically

Count each of these with bmesh after evaluating the stack:

- non-manifold edges (`not e.is_manifold`);
- boundary edges (`e.is_boundary`) on objects that should be closed;
- loose wires (`e.is_wire`);
- n-gons (`len(f.verts) > 4`), which are fine on flat, non-deforming faces but not on curved subdivided ones;
- degenerate faces (`f.calc_area() < 1e-12`);
- an inverted shell (`bm.calc_volume(signed=True) < 0`);
- duplicate vertices (`bmesh.ops.find_doubles`).

Report the counts. Shading, Weighted Normal or bevel shaders never prove that geometry is fused or bevelled. Inspect a clay render (see [rendering](../blender-rendering/SKILL.md), Workbench) from the hero and opposite three-quarter views, and check the real contact with the floor, not the bounding box.

```python
# bevel only the edges you choose
attr = mesh.attributes.get('bevel_weight_edge') or mesh.attributes.new('bevel_weight_edge', 'FLOAT', 'EDGE')
```

```python verify
import bpy, bmesh, math

def counts(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = obj.evaluated_get(depsgraph).to_mesh()
    bm = bmesh.new(); bm.from_mesh(mesh)
    result = {'verts': len(bm.verts), 'non_manifold': sum(not e.is_manifold for e in bm.edges),
              'ngons': sum(len(f.verts) > 4 for f in bm.faces), 'volume': bm.calc_volume(signed=True)}
    bm.free(); obj.evaluated_get(depsgraph).to_mesh_clear()
    return result

# Unapplied scale is detected, then applied before bevelling.
bpy.ops.mesh.primitive_cube_add(size=1); body = bpy.context.object
body.scale = (0.3, 0.2, 0.1)
assert any(abs(s - 1) > 1e-6 for s in body.scale)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
assert all(abs(s - 1) < 1e-9 for s in body.scale) and abs(body.dimensions.x - 0.3) < 1e-6

# Bevel only weighted edges, with a deliberate 4 mm width.
weights = body.data.attributes.new('bevel_weight_edge', 'FLOAT', 'EDGE')
weights.data[0].value = 1.0
bevel = body.modifiers.new('edge_bevel', 'BEVEL')
bevel.limit_method, bevel.width, bevel.segments = 'WEIGHT', 0.004, 3
assert counts(body)['verts'] > 8 and counts(body)['non_manifold'] == 0

# MANIFOLD on a non-manifold cutter silently does nothing; compare counts with the modifier off.
bpy.ops.mesh.primitive_grid_add(size=0.1, location=(0, 0, 0.05)); sheet = bpy.context.object
sheet.hide_render = True
cut = body.modifiers.new('cut', 'BOOLEAN'); cut.object, cut.solver = sheet, 'MANIFOLD'
with_cut = counts(body)['verts']
cut.show_viewport = False
without_cut = counts(body)['verts']
assert with_cut == without_cut                      # the silent no-op, detected
cut.show_viewport = True

# A closed, overshooting cutter works with MANIFOLD and keeps the result closed.
bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.3, vertices=32); drill = bpy.context.object
drill.hide_render = True
cut.object = drill
after = counts(body)
assert after['verts'] > without_cut and after['non_manifold'] == 0 and after['volume'] > 0

# Smooth by Angle replaces Auto Smooth and stays last.
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body], selected_editable_objects=[body]):
    bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
body.modifiers.new('normals', 'WEIGHTED_NORMAL').keep_sharp = True
assert body.modifiers[-1].type == 'NODES' and body.modifiers[-1].use_pin_to_last
```
