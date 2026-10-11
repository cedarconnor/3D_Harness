---
name: blender-simulation
description: Set up, tune and bake physics simulations in Blender 5.x: rigid bodies, cloth, soft bodies, Mantaflow smoke and liquid, particles, and Geometry Nodes simulation zones. Covers real scale and applied transforms, collision shapes and margins, substeps and quality, pinning and modifier order, domain resolution, cache and bake management in background mode, and verifying results.
---

# Physics simulation

Simulations are deterministic only when everything about them is fixed: scale, transforms, settings, the start frame and the cache. Set them up at real scale with applied transforms, tune them at preview quality, bake them, then render the bake. Never render a simulation by playing it back live.

## Rules for every solver

- **Real scale.** Use real-world scale (1 unit = 1 m, mass in kg, gravity 9.81 m/s²). A 1 cm teacup simulated as a 1 m cube behaves like a building. Apply scale (`transform_apply(location=False, rotation=False, scale=True)`) on every simulated and collision object; rigid bodies and cloth read object scale wrongly otherwise.
- **Cache range.** Every cache has its own frame range (`point_cache.frame_start` and `frame_end`; the rigid body default end is 250). A simulation silently stops past the end. Set the range to the shot plus a pre-roll.
- **Pre-roll.** Start the simulation 20–60 frames before the shot so cloth and liquids settle.
- **Baking.** Bake before rendering or reviewing: `bpy.ops.ptcache.bake_all(bake=True)` bakes cloth, soft body, rigid body and particle caches, and blocks until done. Check `point_cache.is_baked`. Scrubbing an unbaked simulation is not the simulated result.
- **Cache files.** Use an absolute, project-relative directory for disk caches, and save the .blend first, because a relative path in an unsaved file resolves badly. 5.0 caches always use ZSTD compression; caches from older versions with other compression must be rebaked.

## Rigid bodies

- **World.** Use `bpy.ops.rigidbody.world_add()`. `substeps_per_frame` (default 10) and `solver_iterations` (default 10): raise both for stacks, fast objects and small objects. `use_split_impulse` reduces bouncing in stacks.
- **Collision shapes.** Use primitives (box, sphere, capsule) where they fit; they are fastest and most stable. Use `CONVEX_HULL` for dynamic objects, and `MESH` only for passive or concave colliders. A concave dynamic object needs a compound of convex children (`COMPOUND`).
- **Mass and friction.** Set mass from density × volume rather than leaving every object at 1 kg; mismatched masses look wrong in collisions. Use `friction` around 0.5 and `restitution` (bounciness) around 0–0.3 for most solids.
- **Small objects.** They need more substeps and, where contact is seen, a smaller `collision_margin`.
- **Start positions.** A body that starts overlapping another is pushed out explosively. Measured on 5.1: a box whose location had been applied into its mesh started inside the ground and was launched 7 m into the air. Check the first frames, not just the end state.
- **Hand animation.** Make animated objects `kinematic` (Animated), and turn off `kinematic` at the frame where the simulation should take over.
- **To keys.** `bpy.ops.rigidbody.bake_to_keyframes` converts the result to keys for export or hand edits.

## Cloth

- **Modifier order.** Rest-shape modifiers (Armature, shape keys) go above Cloth; Subdivision and Solidify go below it. Simulate the low-resolution mesh and subdivide afterwards.
- **Pinning.** Set `cloth.settings.vertex_group_mass` to a vertex group whose weight 1 means fixed, and adjust `pin_stiffness`. Pinned areas follow the rest-shape modifiers.
- **Tuning order.** Mass and air first, then tension, shear, bending, damping, and finally quality. `quality` (steps per frame, default 5) comes before collision quality for fast motion.
- **Collisions.** Collision distance (`collision_settings.distance_min`, default 0.015 m) must be smaller than real gaps. Self-collision (`use_self_collision`) is the most expensive option; turn it on only when folds touch.
- **Sewing.** Garment sewing uses loose edges as sewing springs (`use_sewing_springs`, `sewing_force_max`). Automated garment sewing often fails artistically; starting from a modeled or licensed garment is usually better.

## Fluids (Mantaflow)

- **Domain.** The domain is a box at real size around the action; its `resolution_max` sets the voxel size. 32 is for previews only, finals are typically 128–256 or more, and the cost grows with the cube of the resolution.
- **Cache.** Set `cache_type='ALL'` for scripted bakes (`REPLAY` bakes only during playback). Use an absolute `cache_directory`, and bake with `bpy.ops.fluid.bake_all()` with the domain active.
- **Liquids.** Mesh generation (`use_mesh`) and a particle radius tuned to the resolution matter. Thin sheets need more resolution, not more particles.
- **Smoke and fire.** Use adaptive domains, noise upres for detail, and render with Principled Volume (density, temperature-driven emission).

## Particles and Geometry Nodes simulation

- **New work.** Use the Geometry Nodes simulation zone, which is flexible, bakeable and readable. State lives in the zone's state items; bake with `bpy.ops.object.simulation_nodes_cache_bake(selected=False)`, and choose `bake_target` `'PACKED'` or `'DISK'`. See [Geometry Nodes](../blender-geometry-nodes/SKILL.md).
- **Legacy particles.** These remain for particle hair dynamics and simple emitters. Seed them, and bake their point cache.

## Check the result

1. **Final state.** Read it from the evaluated objects at specific frames after baking: resting heights, contact, no interpenetration (a BVH overlap test between objects), cloth not passing through colliders.
2. **Stability.** Look for objects that should be still but jitter at rest. Measure their velocity in the last frames.
3. **Playback.** Watch the baked result at full speed. Simulations fail visibly in ways numbers miss: popping, explosive first frames, tunnelling.
4. **Record.** Write down the settings and the cache location with the shot.

```python verify
import bpy, bmesh

scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 60
bpy.ops.rigidbody.world_add()
world = scene.rigidbody_world
world.substeps_per_frame, world.solver_iterations = 10, 10
world.point_cache.frame_start, world.point_cache.frame_end = 1, 60

# Passive ground and a dynamic 0.5 m box dropped from 2 m, with real mass and applied scale.
bpy.ops.mesh.primitive_plane_add(size=10); ground = bpy.context.object
bpy.ops.rigidbody.object_add(); ground.rigid_body.type = 'PASSIVE'; ground.rigid_body.collision_shape = 'BOX'
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2)); box = bpy.context.object
box.scale = (0.5, 0.5, 0.5)
assert any(abs(s - 1) > 1e-6 for s in box.scale)              # unapplied scale: apply it before simulating
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.rigidbody.object_add()
box.rigid_body.collision_shape, box.rigid_body.mass = 'BOX', 0.5 ** 3 * 700   # 700 kg/m^3 wood
box.rigid_body.restitution, box.rigid_body.friction = 0.1, 0.6

# Cloth: a subdivided sheet pinned along one edge, subdivision below the cloth modifier.
bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=1, location=(3, 0, 2)); sheet = bpy.context.object
pin = sheet.vertex_groups.new(name='pin')
pin.add([v.index for v in sheet.data.vertices if v.co.y > 0.49], 1.0, 'REPLACE')
cloth = sheet.modifiers.new('cloth', 'CLOTH'); cloth.settings.vertex_group_mass = 'pin'
cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, 60
sheet.modifiers.new('subdivide', 'SUBSURF')
assert [m.type for m in sheet.modifiers] == ['CLOTH', 'SUBSURF']

# Bake every point cache in background, then read the baked state.
assert bpy.ops.ptcache.bake_all(bake=True) == {'FINISHED'}
assert world.point_cache.is_baked and cloth.point_cache.is_baked
scene.frame_set(2)
assert box.matrix_world.translation.z < 2.0                  # falling from its start, not launched
scene.frame_set(60)
assert abs(box.matrix_world.translation.z - 0.25) < 0.02, box.matrix_world.translation.z     # resting on the ground
scene.frame_set(59); z59 = box.matrix_world.translation.z
scene.frame_set(60); assert abs(box.matrix_world.translation.z - z59) < 1e-3                  # at rest, not jittering

depsgraph = bpy.context.evaluated_depsgraph_get()
cloth_mesh = sheet.evaluated_get(depsgraph).to_mesh()
bm = bmesh.new(); bm.from_mesh(cloth_mesh)
heights = [(sheet.matrix_world @ v.co).z for v in bm.verts]
bm.free(); sheet.evaluated_get(depsgraph).to_mesh_clear()
assert max(heights) > 1.95 and min(heights) < 1.6           # pinned edge holds, the free edge has fallen
```
