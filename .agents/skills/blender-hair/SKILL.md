---
name: blender-hair
description: Create hair, fur and grass with Blender's curves-based hair system (3.5+). Covers surface attachment and UVs, guide versus render density, the Geometry Nodes hair assets and modifier order, scripting Curves data, hair materials (Principled Hair BSDF and EEVEE), dynamics options, performance, and checking that strands stay attached.
---

# Hair, fur and strands

Blender's current hair is a **Curves** object: `bpy.data.hair_curves`, object type `'CURVES'`. It is attached to a surface mesh and shaped by sculpt brushes and Geometry Nodes. Legacy particle hair still exists, but new work should use Curves.

## Set up the surface

- **The surface mesh needs a UV map.** Strands store their root UV (`surface_uv_coordinate`) and stay attached through it. `curves.surface` is the mesh object and `curves.surface_uv_map` is the UV map name. Without both set, Deform Curves on Surface does nothing.
- **Adding hair.** With the surface active, `bpy.ops.object.curves_empty_hair_add()` creates an empty Curves object parented to it, with the surface already set.
- **UV changes.** Freeze the surface's UVs before grooming, because changing them later re-attaches strands in new places.
- **Separate objects.** Groom hair, brows, lashes and fur patches as separate Curves objects with their own density and materials.

## Groom in layers

1. **Guides.** Place a few hundred to a few thousand guide strands with the sculpt brushes (Add, Comb, Cut, Puff, Smooth). They define the shape and flow.
2. **Interpolation.** Use Geometry Nodes for render density. The bundled Essentials hair node groups (Interpolate Hair Curves, Clump, Curl, Frizz, Noise, Trim, Set Hair Curve Profile, Deform Curves on Surface) add in Add Modifier > Hair. Order matters: interpolate, then clump, curl and frizz, then trim, then Deform Curves on Surface **last**, so the hair follows an animated or deforming body.
3. **Variation.** Seed every random node, and vary length, clumping and frizz with masks such as painted attributes and position, never uniformly.
4. **Density.** A short-hair human head typically has tens of thousands of render strands, and a furry character can have millions. Preview at 5–10% with Is Viewport switches, or the simplify settings, and render full density.

## Script Curves data

Create strands directly when generating grass, fibres or cables. Use `curves = bpy.data.hair_curves.new(name)` and `curves.add_curves([points per curve, ...])`, then write `position` (and `radius`) through the attribute API with `foreach_set`. Set `curves.surface` and `surface_uv_map` for attached hair. `Curves.set_types()` (4.4+) changes curve types, for example to Catmull-Rom or Bézier.

## Materials

- **Cycles.** The Principled Hair BSDF (the Chiang or Huang model). Set `parametrization = 'MELANIN'` first, because the Melanin sockets do not exist until then. Then set colour by **melanin** (0 is blond or white, about 0.8+ is black) and `melanin_redness` for red tones, rather than RGB, for believable hair. Roughness is about 0.2–0.4; the radial roughness controls the softness of the highlight. Random Color/Roughness inputs add per-strand variation.
- **EEVEE.** Renders strands as strips or cylinders (Render settings > Curves). Hair shading there is an approximation, so judge final hair in the target engine.
- **Width.** Use a `radius` attribute that tapers to the tip, about 0.01–0.05 mm for real hair. Very thin strands alias; render with more samples rather than thickening the hair.

## Dynamics

Curves hair has no built-in solver. The options are:

- a Geometry Nodes simulation zone with spring or verlet logic, or a hair-dynamics node group asset (bake it);
- simulating a low-resolution guide mesh or curves with Cloth or Soft Body, then driving the hair with Deform Curves on Surface or a Surface Deform cage;
- the legacy particle-hair dynamics, if the project still uses particle hair.

Bake simulated hair before rendering (see [simulation](../blender-simulation/SKILL.md)).

## Checks

- Every strand has a root on the surface: the distance from each first point to the surface is about 0 (BVH `find_nearest`).
- The strand count and the per-strand point count are as intended. No strand goes through the body (sample points against the surface's BVH).
- Render a close-up and a full shot at the final sample count: hair problems such as clumping artefacts, flicker and noise appear only at render resolution and in motion.

```python verify
import bpy, random
import numpy as np
from mathutils.bvhtree import BVHTree

scene = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5); head = bpy.context.object
assert head.data.uv_layers, 'hair needs a UV map on the surface'

# An empty hair object attached to the surface, with the surface and UV map set.
bpy.ops.object.curves_empty_hair_add()
hair = bpy.context.object
assert hair.type == 'CURVES' and hair.data.surface == head and hair.data.surface_uv_map

# Script strands: roots on the surface, pointing along the normal, 6 points each, tapering radius.
rng = random.Random(1)
roots = [rng.choice(head.data.polygons) for _ in range(200)]
curves = hair.data
curves.add_curves([6] * len(roots))
positions = []
for poly in roots:
    root, normal = head.matrix_world @ poly.center, (head.matrix_world.to_3x3() @ poly.normal).normalized()
    positions += [tuple(root + normal * 0.02 * i) for i in range(6)]
curves.attributes['position'].data.foreach_set('vector', np.array(positions, dtype=np.float32).ravel())
radius = curves.attributes.get('radius') or curves.attributes.new('radius', 'FLOAT', 'POINT')
radius.data.foreach_set('value', np.tile(np.linspace(0.0005, 0.0001, 6), len(roots)).astype(np.float32))
assert len(curves.curves) == 200 and len(curves.points) == 1200

# Every root sits on the surface (hair's object space equals world here: both at the origin).
bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
first_points = [curves.points[c.first_point_index].position for c in curves.curves]
assert max(bvh.find_nearest(p)[3] for p in first_points) < 1e-4

# The Principled Hair BSDF uses melanin for colour.
mat = bpy.data.materials.new('MAT-hair'); nodes = mat.node_tree.nodes
hair_bsdf = nodes.new('ShaderNodeBsdfHairPrincipled')
assert 'Melanin' not in hair_bsdf.inputs             # hidden until the mode is set
hair_bsdf.parametrization = 'MELANIN'
hair_bsdf.inputs['Melanin'].default_value, hair_bsdf.inputs['Melanin Redness'].default_value = 0.8, 0.2
curves.materials.append(mat)
assert curves.materials[0] == mat
```
