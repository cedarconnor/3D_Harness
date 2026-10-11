---
name: blender-skinning
description: Bind meshes to armatures and get good deformation in Blender 5.x. Covers automatic weights and how bone-heat fails, weight normalization and influence limits, weight transfer from proxies, preserve volume (dual quaternion), Corrective Smooth, corrective shape keys driven by joint rotation, Surface and Mesh Deform cages, and stress-pose checks.
---

# Skinning and deformation

Good deformation comes from three things in order: topology that supports the bend (loops around joints, see [sculpt and retopology](../blender-sculpt-retopo/SKILL.md)), clean weights, and correctives for what weights cannot fix. Fix weights before adding correctives; a corrective that hides a weight error breaks in the next pose.

## Binding

- **Automatic weights.** With the mesh and the armature selected and the armature active, run `bpy.ops.object.parent_set(type='ARMATURE_AUTO')`. It uses bone heat: only deform bones (`use_deform=True`) get groups. Exclude control and mechanism bones first.
- **When bone heat fails.** It prints "Bone Heat Weighting: failed to find solution for one or more bones" and leaves some groups **empty or missing**, with no exception. After binding, check every deform bone for a vertex group containing weighted vertices. Causes and fixes:
  - **Duplicate or overlapping vertices.** Merge by distance.
  - **Non-manifold geometry, interior faces or flipped normals.** Clean up the mesh.
  - **Many disconnected or intersecting parts** (eyes, teeth, buttons, clothing layers). Weight them separately or by hand, or bind a clean watertight proxy and transfer its weights (see below).
  - **Very small meshes** with tiny faces. Scale the mesh and armature up 10–100×, apply, bind, then scale back down.
  - **Bones outside the mesh.** Move the bones inside the volume.
- **Rigid parts.** Machines, armour plates and props are not skinned with heat weights. Each rigid part gets one vertex group at weight 1.0, or bone parenting. See [rigging](../blender-rigging/SKILL.md).

## Weight hygiene

- **Normalize.** Every vertex's deform weights should sum to 1: `bpy.ops.object.vertex_group_normalize_all(lock_active=False)`.
- **Limit influences.** Game engines take at most 4 per vertex (some 8): `vertex_group_limit_total(limit=4)`. Then normalize again, and clean tiny weights with `vertex_group_clean(limit=0.01)`.
- **Check numerically.** Over `v.groups`, restricted to deform-bone groups: flag sums more than 0.02 from 1, more than the allowed influences, and unweighted vertices.
- **Mirror.** Use the `.L`/`.R` names and Mirror Vertex Group with topology mirror for asymmetric meshes.
- **Proxy transfer.** Bind a simple, clean, closed proxy, then on the real mesh add a Data Transfer modifier with vertex groups, `vert_mapping='POLYINTERP_NEAREST'` (nearest face, interpolated). Apply it, then normalize. This handles clothing and messy scans that bone heat cannot.

## Better joints

- **Preserve Volume.** `ArmatureModifier.use_deform_preserve_volume = True` switches to dual-quaternion skinning. It removes the "candy wrapper" collapse on twisting forearms, but bulges at shoulders and hips. Use it per mesh, or blend it with a vertex group (`vertex_group` plus `invert_vertex_group`).
- **Corrective Smooth.** Put it after the Armature modifier and limit it with a vertex group around the joints. `rest_source='BIND'` (after Bind) or `'ORCO'`, and 5–10 iterations. It smooths away pinching while keeping the rest shape.
- **Twist bones.** Split forearms and thighs into two or three twist segments that share the rotation, which keeps volume along the limb.

## Corrective shape keys

1. Pose the joint to its extreme, for example the elbow at 120° or the shoulder raised.
2. Sculpt or edit the fix as a shape key relative to the posed shape, using a corrective workflow or a sculpt in pose.
3. Drive the key's `value` from the joint rotation with a `TRANSFORMS` variable in local space and a simple expression such as `max(0, rot / 2.09)`, so it rises from 0 at rest to 1 at the extreme. Simple expressions run without Python auto-run.
4. Clamp `slider_min` and `slider_max` and check the in-between pose: a corrective that only looks right at the extreme pops along the way.

## Cages and surface binding

- **Mesh Deform.** A closed, manifold, low-resolution cage that fully encloses the mesh, deformed by the rig. It gives smooth, volume-preserving deformation for blobby characters. Bind with `bpy.ops.object.meshdeform_bind(modifier=name)`; `precision` sets the quality and the cost.
- **Surface Deform.** Sticks one mesh to another, such as clothing to a body or details to a deforming surface. Bind with `bpy.ops.object.surfacedeform_bind(modifier=name)`. It fails on target n-gons that are concave, and on edges with more than two faces.
- **Check the binds.** Both binds can fail without an exception. Check `modifier.is_bound` after binding, and rebind after any topology change.

## Stress test

Pose and render the deformation set: crouch, reach overhead, arms forward and crossed, a single-leg stand, a 90° spine twist, a full fist and spread fingers, head turns of about ±60°. Look for collapse, pinching, intersections, lost volume and weight "pops" between neighbouring vertices. Check the triangle count and weights on the evaluated mesh. Record which poses pass; deformation quality is a visual judgment that numbers alone do not decide.

```python verify
import bpy, bmesh, math

scene = bpy.context.scene
# A limb mesh with loops along its length.
mesh = bpy.data.meshes.new('limb'); bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, vec=(2.0, 0.2, 0.2), verts=bm.verts); bmesh.ops.translate(bm, vec=(1.0, 0, 0), verts=bm.verts)
long_edges = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 1e-6]
bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=9, use_grid_fill=True)
bm.to_mesh(mesh); bm.free()
limb = bpy.data.objects.new('limb', mesh); scene.collection.objects.link(limb)

arm = bpy.data.armatures.new('rig'); rig = bpy.data.objects.new('rig', arm); scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
a = arm.edit_bones.new('DEF-upper.L'); a.head, a.tail = (0, 0, 0), (1, 0, 0)
b = arm.edit_bones.new('DEF-lower.L'); b.head, b.tail, b.parent, b.use_connect = (1, 0, 0), (2, 0, 0), a, True
ctrl = arm.edit_bones.new('ctrl.L'); ctrl.head, ctrl.tail, ctrl.use_deform = (2, 0, 0), (2.3, 0, 0), False
bpy.ops.object.mode_set(mode='OBJECT')

limb.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[limb, rig], selected_editable_objects=[limb, rig]):
    assert bpy.ops.object.parent_set(type='ARMATURE_AUTO') == {'FINISHED'}

# Bone heat can fail silently: every deform bone must own a non-empty group; control bones get none.
deform = [bone.name for bone in arm.bones if bone.use_deform]
weighted = {limb.vertex_groups[g.group].name for v in mesh.vertices for g in v.groups if g.weight > 1e-4}
assert set(deform) <= weighted and 'ctrl.L' not in limb.vertex_groups, (deform, weighted)

# Hygiene for engines: at most 4 influences, sums normalized to 1.
bpy.context.view_layer.objects.active = limb
with bpy.context.temp_override(object=limb, active_object=limb):
    bpy.ops.object.vertex_group_limit_total(limit=4)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
for v in mesh.vertices:
    influences = [g.weight for g in v.groups if g.weight > 1e-4]
    assert 1 <= len(influences) <= 4 and abs(sum(influences) - 1) < 0.02

# Preserve volume and a Corrective Smooth after the Armature modifier.
armature_mod = next(m for m in limb.modifiers if m.type == 'ARMATURE')
armature_mod.use_deform_preserve_volume = True
smooth = limb.modifiers.new('joint_smooth', 'CORRECTIVE_SMOOTH'); smooth.iterations = 8
assert [m.type for m in limb.modifiers] == ['ARMATURE', 'CORRECTIVE_SMOOTH']

# A corrective shape key driven by the elbow's local rotation with a simple expression.
limb.shape_key_add(name='Basis'); fix = limb.shape_key_add(name='elbow_fix', from_mix=False)
curve = fix.driver_add('value')
var = curve.driver.variables.new(); var.name, var.type = 'rot', 'TRANSFORMS'
target = var.targets[0]
target.id, target.bone_target, target.transform_type, target.transform_space = rig, 'DEF-lower.L', 'ROT_Z', 'LOCAL_SPACE'
curve.driver.expression = 'max(0, rot / 2.09)'
assert curve.driver.is_simple_expression
rig.pose.bones['DEF-lower.L'].rotation_mode = 'XYZ'
rig.pose.bones['DEF-lower.L'].rotation_euler.z = math.radians(60)
bpy.context.view_layer.update()
assert abs(fix.value - math.radians(60) / 2.09) < 0.01, fix.value
```
