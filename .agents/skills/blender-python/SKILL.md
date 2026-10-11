---
name: blender-python
description: Write reliable bpy scripts for Blender 5.x through an MCP connection or background Blender. Covers inspecting before writing, choosing the data API or operators, context overrides, bmesh, numpy bulk access, evaluated depsgraph data, deterministic and idempotent scripts, and the 4.0–5.1 API changes agents most often get wrong.
---

# Script Blender deliberately

Every other `blender-*` skill assumes this one. The facts in the [API changes table](#api-changes-that-break-older-scripts) were checked on Blender 5.1.1. Treat code you remember from older Blender versions as unverified until it runs.

## Inspect before writing

- Read what is there before changing anything: the Blender version (`bpy.app.version_string`), the scene's unit system and scale, the render engine, the active object and selection, the mode, and the objects, collections and materials the task touches. Through MCP, use the summary tools first; run code only for what they do not report.
- Never assume a name. `Cube.001` exists because something was copied; materials, meshes and node groups are shared datablocks with their own users (`datablock.users`). Find an object through a stable identity where the project has one, such as `dcc_instance_id` in a harness project.
- Return JSON-serializable values from MCP code: names, numbers and lists, not `bpy` objects.
- In a [3D Harness](../dcc-harness/SKILL.md) project, a scripted change to an accepted scene goes through `begin-edit`/`finish-edit`. Run the script once against an owned working copy, save to a new file, and let the harness observe it. Do not edit the artist's open file in place.

## Data API first, operators when they earn it

- **Data API.** `bpy.data`, object, mesh and modifier properties, `bmesh`. It is fast, needs no context and has no side effects on selection. Create objects with `bpy.data.objects.new(name, data)` and link them with `collection.objects.link(obj)`.
- **Operators.** `bpy.ops` acts on the context: the active object, the selection, the mode and the editor. Each call may push undo, update the depsgraph and change the selection. Use operators for what the data API lacks, such as applying modifiers, unwrapping, baking, importing and exporting, and remeshing.
- **Context.** Supply operator context with `with bpy.context.temp_override(...)`. The old dictionary-override argument was removed in 4.0. Check `bpy.ops.x.y.poll()` when unsure; a poll failure means missing context, not a broken operator.
- **Loops.** Never call operators per element inside a loop over thousands of items. Use bmesh, `foreach_get`/`foreach_set`, or a Geometry Nodes modifier.
- **Operator defaults.** Check them. `bpy.ops.object.transform_apply()` defaults to `location=True, rotation=True, scale=True`, so `transform_apply(scale=True)` also bakes the location into the mesh and moves the origin to the world origin. In a 5.1 test this put a rigid body inside the ground. Write all three arguments, for example `transform_apply(location=False, rotation=False, scale=True)`.
- **Mode.** Leave objects in Object Mode before reading mesh data: edit-mode changes reach `mesh.vertices` only after leaving Edit Mode or calling `bmesh.update_edit_mesh`.

## Background Blender

`blender --background --factory-startup --python script.py -- args` has no window. Operators that need a 3D Viewport, such as view-dependent selection, `view3d.*` and some UV projections, fail their poll. Use bmesh or data alternatives. Pass `--python-exit-code 1` so an exception fails the process. Factory startup skips the user's add-ons; enable what you need with `addon_utils.enable('rigify', default_set=True)`, or check that it is present.

## Measure the evaluated result

What renders is the evaluated object: modifiers, Geometry Nodes, constraints, drivers and animation applied.

- Get it with `depsgraph = bpy.context.evaluated_depsgraph_get()`, then `obj.evaluated_get(depsgraph)`.
- For a temporary mesh, call `to_mesh()` and release it with `to_mesh_clear()`.
- After changing transforms through Python, call `bpy.context.view_layer.update()` before reading `matrix_world`.
- World-space bounds are `obj.matrix_world @ Vector(corner)` over `obj.bound_box`. `obj.dimensions` includes scale but not parent or constraint effects on orientation.

## Bulk data with numpy

`foreach_get` and `foreach_set` move whole arrays at C speed: positions, normals, UVs and attributes. Allocate the array to the exact flat size first. This is how the harness's own UV measurement reads millions of triangles in seconds.

## bmesh

Use bmesh for topology work. Build it with `bm = bmesh.new()`, then `bm.from_mesh(me)`. Call `ensure_lookup_table()` before indexing. Write back with `bm.to_mesh(me)`, then `me.update()`, then `bm.free()`. Check structure with `bmesh.ops` and element flags: `e.is_manifold`, `e.is_boundary`, `v.is_wire`, `f.calc_area()`.

## Deterministic and idempotent scripts

- **Seeds.** Seed every random choice from a recorded seed with `random.Random(seed)`, and use a seed input on Geometry Nodes Random Value nodes.
- **Ordering.** Iterate in sorted order. Set and `bpy.data` ordering are not a contract.
- **Get or create.** Look up an existing object, material or node group by name before creating it, so that running a script twice does not leave `.001` duplicates.
- **Saving.** Save to a new path with `bpy.ops.wm.save_as_mainfile(filepath=..., copy=True)` when the open document must stay unchanged. Store paths relative with a `//` prefix, and resolve them with `bpy.path.abspath`.
- **Cleanup.** `bpy.data.orphans_purge(do_recursive=True)` removes datablocks with no users. Do it only in files you own: it deletes unused materials an artist may have kept on purpose.

## API changes that break older scripts

| Since | Change |
|---|---|
| 4.0 | Principled BSDF v2 renamed sockets, for example `Specular IOR Level`, `Transmission Weight`, `Coat Weight`, `Sheen Weight`, `Emission Color` and `Subsurface Weight`. Armature layers and bone groups became bone collections (`armature.collections`). The `bgl` module was removed; use `gpu`. Context dictionaries passed to operators were removed; use `temp_override`. The node group interface moved to `tree.interface.new_socket(...)` |
| 4.1 | Mesh auto smooth was removed. Use `bpy.ops.object.shade_auto_smooth()` or a Smooth by Angle modifier; there is no `mesh.use_auto_smooth` |
| 4.2 | EEVEE Next replaced EEVEE Legacy: no `use_bloom`, `use_ssr` or `use_gtao`. Use the Glare compositor node and ray tracing (`scene.eevee.use_raytracing`), and `material.surface_render_method`. Add-ons became extensions |
| 4.3 | Grease Pencil v3 replaced the legacy data. In 5.x it is `bpy.data.grease_pencils`, with layers, frames and drawings |
| 4.4 | Slotted actions: an Action holds slots, layers, strips and channelbags. Reach F-curves with `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot).fcurves` |
| 5.0 | `action.fcurves` is gone. The compositor is a node group (`scene.compositing_node_group`), and the Composite node is replaced by the group output. `sequence_editor.strips` replaces `sequences`. The render engine identifier is `BLENDER_EEVEE`, not `BLENDER_EEVEE_NEXT`. `Material.use_nodes` is deprecated, to be removed in 6.0 |
| 4.5–5.0 | The Boolean modifier solvers are `FLOAT`, `EXACT` and `MANIFOLD`. Datablock names may exceed 63 characters; 100 characters is accepted |

When an attribute error names a property from this table, port the code; do not search for a compatibility shim.

```python verify
import bpy, bmesh
import numpy as np

scene = bpy.context.scene
# Data-API creation, no operators.
mesh = bpy.data.meshes.new('probe')
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.to_mesh(mesh); bm.free()
obj = bpy.data.objects.new('probe', mesh)
scene.collection.objects.link(obj)
obj.modifiers.new('subd', 'SUBSURF').levels = 1

# Evaluated data differs from the base mesh until the modifier is applied.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = obj.evaluated_get(depsgraph)
temp = evaluated.to_mesh()
assert len(mesh.vertices) == 8 and len(temp.vertices) == 26
evaluated.to_mesh_clear()

# numpy bulk read of the base mesh.
co = np.empty(len(mesh.vertices) * 3); mesh.vertices.foreach_get('co', co)
assert np.allclose(np.abs(co), 1.0)

# An operator with an explicit context override works in background mode.
with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
    assert bpy.ops.object.modifier_apply(modifier='subd') == {'FINISHED'}
assert len(obj.data.vertices) == 26

# Transforms set through Python need a view-layer update before matrix_world is read.
obj.location.x = 5
bpy.context.view_layer.update()
assert abs(obj.matrix_world.translation.x - 5) < 1e-6

# transform_apply applies location too unless told otherwise.
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2)); moved = bpy.context.object
bpy.ops.object.transform_apply(scale=True)
assert moved.location.z == 0.0                    # the origin moved: the default trap
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2)); kept = bpy.context.object
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
assert kept.location.z == 2.0

# API facts from the table, so a Blender upgrade that changes them fails this block.
action = bpy.data.actions.new('probe')
assert not hasattr(action, 'fcurves') and hasattr(action, 'slots')
assert hasattr(scene, 'compositing_node_group') and not hasattr(scene, 'node_tree')
assert hasattr(scene.sequence_editor_create(), 'strips')
solvers = {i.identifier for i in bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items}
assert solvers == {'FLOAT', 'EXACT', 'MANIFOLD'}
assert not hasattr(mesh, 'use_auto_smooth') and not hasattr(scene.eevee, 'use_bloom')
assert len(bpy.data.objects.new('n' * 100, None).name) == 100
```
