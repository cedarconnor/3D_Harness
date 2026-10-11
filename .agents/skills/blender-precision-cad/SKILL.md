---
name: blender-precision-cad
description: Model and check dimensionally exact parts in Blender for design engineering, product design and 3D printing. Covers units and the single mm-to-m conversion, datums and stated tolerances, CAD and CadQuery interchange (STEP/STL), boolean solver choice, hole and clearance arithmetic, printability (manifold, wall thickness, overhangs, orientation) and measuring the exported file rather than the scene.
---

# Precision modeling and design engineering

Blender is a mesh modeler. Where exact solids matter, a parametric CAD source should be the truth: CadQuery, Onshape, FreeCAD or SolidWorks, exported as STEP. Blender then previews, renders and checks; it does not decide dimensions. When the part must be built in Blender, treat every dimension as data and measure the result.

## Define before modeling

- **Units.** One Blender unit is one metre (`unit_settings.scale_length = 1`, system `METRIC`).
  - Show millimetres with `length_unit = 'MILLIMETERS'`. This changes the display only, not the geometry.
  - Convert millimetres to metres exactly once, at import (`global_scale=0.001`). Never also scale the scene and the object.
  - Some projects use `scale_length = 0.001` instead, so that one unit reads as one millimetre. Keep whatever an inherited project uses, write it down, and never mix the two.
- **Datums.** Fix the origin, the mounting plane and the hole datum, and which side faces the operator.
  - State angles as a relation between named faces ("bottom edge 80° from the mounting face toward the operator"), never as a bare number.
- **Provenance.** Tag every dimension as *drawing*, *measured*, *design allowance* or *unknown*. Two parts with the same model name or diagonal do not have the same hole pattern.
- **Poses.** Keep the assembly pose separate from the print or fabrication pose. Choose the print orientation before the design is locked, because it decides overhangs, layer strength and support.

## Build exact geometry in Blender

- **Inputs.** Type exact values into transforms and modifier fields: `obj.dimensions`, `location`, the Bevel `width`, the Solidify `thickness`. Snap with the increment or vertex modes, and never drag by eye. Apply scale (`transform_apply(location=False, rotation=False, scale=True)`; the operator's defaults also apply location and rotation) before using Bevel, Solidify, booleans or physics; they read object-space distances.
- **Boolean solver.**
  - `EXACT` handles coplanar and touching cases best and is slowest.
  - `MANIFOLD` (4.5+) is fast and robust, but only on closed manifold operands.
  - `FLOAT` is fastest and fails on coincident faces.
  - Avoid perfectly coplanar faces by extending cutters 0.1 mm beyond the surface, and inspect the result for non-manifold edges.
- **Round features.** Choose the segment count from the chord error you can accept. The deviation is about r·(1 − cos(π/n)): a 6.4 mm hole with 64 segments deviates by about 0.004 mm, and 128 segments by about 0.001 mm. A polygonal hole is smaller than its nominal circle at the flats; size cutters on the across-flats distance where fit matters.
- **Fillets and chamfers.** Use the Bevel modifier with `limit_method='ANGLE'` or bevel weights, with explicit `width` and `segments`. Use `profile=0.5` for a round fillet; one segment makes a chamfer.
- **Constraint sketching.** The CAD Sketcher extension adds parametric 2D sketches with real constraints. For anything beyond simple blocks, prefer it or an external CAD source over hand-placed vertices.

## Hardware arithmetic

- **Hex nuts.** The across-corners width D equals the across-flats width AF ÷ cos 30°. A 5.5 mm AF M3 nut is 6.35 mm across corners. Make the slot on the across-flats dimension plus clearance.
- **Holes.** A nominal M3 screw needs a clearance hole of about 3.2–3.4 mm, more for printed parts. Tapping and heat-set inserts have their own diameters from the supplier's sheet, not from the screw size.
- **Clearance.** Clearance depends on the process and the material; there is no universal printed value. Print a fit coupon cut from the real interface, in the same orientation as the part, before printing the whole thing.

## Printability and fabrication checks

- **Watertight solid.** Every edge has exactly two faces, the normals are consistent and point outward, and the volume is positive. Check with bmesh: `e.is_manifold`, `bm.calc_volume(signed=True) > 0`. The 3D Print Toolbox extension adds wall-thickness, overhang and intersection checks; it is not bundled with Blender 5.1.
- **Wall thickness.** Wall thickness must exceed the process minimum, typically 0.8–1.2 mm for FDM and less for resin. Measure it by ray-casting inward from surface samples with `mathutils.bvhtree.BVHTree.FromObject`.
- **Overhangs.** Faces past about 45° from vertical need support. Shape horizontal holes with a teardrop or pointed top, open nut slots toward +Z, or split the part. A long enclosed channel can pass every geometric check and still fail to print.
- **Bed fit.** Include brim and skirt. If the part does not fit, rotate or split it; never scale a functional part.
- **Molding and machining.** Use 1–2° of draft on molded faces and uniform wall thickness, and keep internal corners filleted at least the cutter radius for milling.

## Measure the delivered file

1. Export the actual deliverable, STL, 3MF or STEP from CAD, and re-import it into a fresh Blender. Check its bounds and volume against the specification within a stated tolerance, for example 0.05–0.1 mm and 1% volume.
2. Check its shell count. An internal void adds a shell; so does a stray part.
3. A part meant to sit on the bed must have its minimum Z at 0.
4. For a hole, check the axis, the radius and the span, and that an inscribed cylinder is empty. A boss can pass a bounds check where a hole was intended.
5. Report verification honestly, level by level: CAD or mesh geometry, slicer preview, test print, real fit, and load, creep or heat testing. A thicker wall is not a load rating.

Keep reference hardware such as screws, boards and mating parts in a separate `REFERENCE` collection. Use it for clearance checks, and keep it out of the print mesh.

```python verify
import bpy, bmesh, math
from mathutils import Vector

scene = bpy.context.scene
scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', 1.0
scene.unit_settings.length_unit = 'MILLIMETERS'          # display only

# A 40 x 20 x 5 mm plate with a 6.4 mm through hole, modelled in metres.
bpy.ops.mesh.primitive_cube_add(size=1); plate = bpy.context.object
plate.scale = (0.040, 0.020, 0.005)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
plate.location.z = 0.0025                                 # sits on the bed at z = 0
r, segments = 0.0032, 64
assert r * (1 - math.cos(math.pi / segments)) < 4e-6      # chord error under 0.004 mm
bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=r, depth=0.0052, location=(0.010, 0, 0.0025))
cutter = bpy.context.object
boolean = plate.modifiers.new('hole', 'BOOLEAN'); boolean.object, boolean.solver = cutter, 'EXACT'
with bpy.context.temp_override(object=plate, active_object=plate, selected_objects=[plate], selected_editable_objects=[plate]):
    bpy.ops.object.modifier_apply(modifier='hole')
bpy.data.objects.remove(cutter)

# Watertight, positive volume, expected volume within 1%.
bm = bmesh.new(); bm.from_mesh(plate.data)
assert all(e.is_manifold for e in bm.edges)
volume = bm.calc_volume(signed=True)
expected = 0.040 * 0.020 * 0.005 - math.pi * r * r * 0.005
assert volume > 0 and abs(volume - expected) / expected < 0.01, (volume, expected)
bm.free()

# Hex nut arithmetic: across corners = across flats / cos 30.
assert abs(5.5 / math.cos(math.radians(30)) - 6.351) < 0.001

# Export the deliverable in millimetres, re-import with the single conversion, and measure the file.
stl = str(WORK / 'plate.stl')
plate.select_set(True); bpy.context.view_layer.objects.active = plate
bpy.ops.wm.stl_export(filepath=stl, export_selected_objects=True, global_scale=1000.0)
bpy.ops.wm.stl_import(filepath=stl, global_scale=0.001)
imported = bpy.context.selected_objects[0]
corners = [imported.matrix_world @ Vector(c) for c in imported.bound_box]
size = [max(c[i] for c in corners) - min(c[i] for c in corners) for i in range(3)]
assert all(abs(a - b) < 1e-7 for a, b in zip(size, (0.040, 0.020, 0.005))), size
assert abs(min(c.z for c in corners)) < 1e-7               # still on the bed
```
