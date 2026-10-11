---
name: blender-rigging
description: Build and inspect Blender 5.x armature rigs for characters, creatures, props and machines. Covers preparing the mesh, deform/control/mechanism bone separation, naming and roll, bone collections, constraints and their order, IK with pole targets, IK/FK switching, drivers that work without auto-run, custom shapes, Rigify generation from Python, mechanical rigs, and the checks that prove a rig works.
---

# Rigging

A rig is an interface for animators and a deformation system for the mesh. Keep those two roles in separate bones, so the controls can change without breaking the deformation. Skin weights and deformation quality are in the [skinning skill](../blender-skinning/SKILL.md).

## Prepare before adding bones

- **Rest pose.** The mesh is in a neutral rest pose at real scale (1 unit = 1 m), facing −Y, standing on Z = 0. A character's arms are in an A-pose (about 45°) or a T-pose, and the limbs are slightly bent at elbows and knees.
- **Transforms.** Apply rotation and scale on both the mesh and the armature (`transform_apply(location=False, rotation=True, scale=True)`; omitting `location=False` also moves the origin to the world origin). Unapplied scale breaks constraints, IK stretch, physics and FBX export.
- **Clean mesh.** Merge duplicate vertices, remove interior faces, and keep separate parts such as eyes and teeth as separate objects or clearly separate islands.

## Bone structure

- **Three kinds of bone.**
  - **DEF-** bones deform the mesh. They are the only bones with `use_deform=True`, and the only ones exported to engines.
  - **MCH-** mechanism bones do the internal work: IK chains, twist, helpers. They are hidden and never keyed.
  - **Control bones** (no prefix, or `CTRL-`) are what animators key. Set `use_deform=False`.
  - Rigify also creates **ORG-** bones, copies of the metarig bones.
- **Check.** `[b.name for b in arm.bones if b.use_deform and not b.name.startswith('DEF-')]` should be empty.
- **Naming.** Use `.L` and `.R` suffixes. Mirroring, Symmetrize and Paste Flipped depend on them.
- **Roll.** Recalculate it consistently per chain with `bpy.ops.armature.calculate_roll(type='GLOBAL_POS_X')` or another explicit axis. Mixed rolls break IK planes and mirrored poses. Check that the L/R pairs have mirrored `z_axis` vectors.
- **Bone collections (4.0+).** They replace layers and bone groups. Create them with `arm.collections.new(name, parent=...)` and assign with `collection.assign(bone)`; `arm.collections_all` includes nested ones. New edit bones are in no collection until assigned. Put DEF and MCH bones in hidden collections.
- **Selection and visibility (5.0).** These live on pose bones (`pose_bone.select`, `pose_bone.hide`). `Bone.select` was removed.

## Constraints and IK

- **Order.** Constraints evaluate top to bottom: Copy Transforms and IK first, Limit constraints last. Choose owner and target spaces deliberately (World, Local, Local With Parent). Avoid dependency cycles; the console reports them as "Dependency cycle detected".
- **IK.**
  - Pre-bend the chain in the rest pose so the IK plane is unambiguous.
  - Always set `chain_count`: the default 0 means "to the root", a classic bug.
  - Keep the IK target and the pole outside the chain's hierarchy.
  - Set `pole_angle` by measuring it. It is often ±90°, depending on the bone roll, and a wrong value swings the knee or elbow sideways, away from the pole. Try the candidates, keep the one where the joint points at the pole, and check that the posed bones at the rest frame match their rest matrices.
  - Keep `use_stretch` off unless you want stretch.
- **Hinges.** Single-axis joints get Limit Rotation on the other two axes.
- **IK/FK switching.** Drive the IK constraint's `influence` from a custom property on a settings bone. To switch without a jump, match the destination controls to the evaluated world matrices of the source chain at the switch frame, key them, then key the switch property with `CONSTANT` interpolation. Rigify's `IK_FK` property is **0 = IK, 1 = FK**.
- **Grab and release.** Use a Child Of constraint or a space switch; key the influence and compensate at the switch frame. Never let a prop and a hand depend on each other.

## Drivers

- **Simple expressions.** Prefer them: arithmetic, `min`, `max`, `sin`, and variables such as `var * 2` or `max(0, var / 1.57)`. They evaluate without Python, so they run when auto-run is disabled and are fast. Check with `fcurve.driver.is_simple_expression` and `fcurve.driver.is_valid`.
- **Python drivers.** Those that call functions in `bpy.app.driver_namespace` need auto-run (`--enable-autoexec` in background), and silently do nothing without it. The namespace resets on file load, so re-register it from a persistent `load_post` handler.
- **Rotation variables.** Use `TRANSFORMS` variables on a bone's local rotation for correctives and mechanisms, not raw `pose.bones[...]` property paths.

## Custom shapes

`pose_bone.custom_shape = widget_object`, with the widget objects in a hidden, excluded collection. Use `custom_shape_scale_xyz` and `custom_shape_transform` to place them. Controls should be easy to select in the viewport and colour-coded by side: left blue, right red, centre yellow.

## Rigify

Rigify ships with Blender (`addon_utils.enable('rigify')`).

1. Add a metarig with `bpy.ops.object.armature_human_metarig_add()`.
2. Fit its bones to the mesh in Edit Mode, from measured landmarks: joints at the mesh's pivot points, the knee slightly forward, the elbow slightly back.
3. With the metarig active, run `bpy.ops.pose.rigify_generate()`. It works in background mode.
4. Parent the mesh with automatic weights to the generated rig's DEF bones.

Generation is refused unless at least one bone collection has a UI row (`rigify_ui_row > 0`), which the stock metarigs have. Re-generation overwrites the rig named in `metarig.data.rigify_target_rig`. Put custom edits in a finalize script (`metarig.data.rigify_finalize_script`) rather than on the generated rig, or they are lost on regeneration. Set per-bone rig types with `pose_bone.rigify_type`.

## Props and machines

- **Rigid parts.** Use one bone per rigid part, with bone parenting (`parent_set(type='BONE')`) or a single vertex group at weight 1.0. Never use automatic weights on metal: it bends.
- **Pistons.** Two bones that Damped Track each other.
- **Wheels.** Rotation = distance travelled ÷ radius, as a driver.
- **Gears.** The driven rotation is −drive × teeth_drive ÷ teeth_driven.
- **Doors and lids.** A hinge bone at the real hinge axis, with Limit Rotation.

## Prove it works

Pose the stress cases before anyone animates: crouch, reach overhead, a single-leg stand, a 90° twist, and extreme fingers. Then check:

- IK reaches its targets;
- poles do not flip across the range;
- the rest pose at frame 0 equals the rest matrices;
- no dependency cycles;
- only DEF bones deform.

Render the stress poses for review. Animation lives in [animation](../blender-animation/SKILL.md); mocap goes to the rig through [mocap](../blender-mocap/SKILL.md).

```python verify
import bpy, math, addon_utils

scene = bpy.context.scene
arm = bpy.data.armatures.new('rig'); rig = bpy.data.objects.new('rig', arm); scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.edit_bones
upper = eb.new('DEF-upper_arm.L'); upper.head, upper.tail = (0, 0, 0), (1, 0, 0.05)       # pre-bent elbow
fore = eb.new('DEF-forearm.L'); fore.head, fore.tail = (1, 0, 0.05), (2, 0, 0)
fore.parent, fore.use_connect = upper, True
target = eb.new('hand_ik.L'); target.head, target.tail = (2, 0, 0), (2.3, 0, 0); target.use_deform = False
pole = eb.new('elbow_pole.L'); pole.head, pole.tail = (1, 0, 1), (1, 0, 1.2); pole.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')

# Bone collections: deform bones hidden, controls visible; only DEF- bones deform.
deform, controls = arm.collections.new('Deform'), arm.collections.new('Controls')
for bone in arm.bones:
    (deform if bone.use_deform else controls).assign(bone)
deform.is_visible = False
assert [b.name for b in arm.bones if b.use_deform and not b.name.startswith('DEF-')] == []

# IK with an explicit chain length and a pole outside the chain.
ik = rig.pose.bones['DEF-forearm.L'].constraints.new('IK')
ik.target, ik.subtarget, ik.chain_count = rig, 'hand_ik.L', 2
ik.pole_target, ik.pole_subtarget = rig, 'elbow_pole.L'
rig.pose.bones['hand_ik.L'].location = (0, -0.5, 0)       # pull the hand target in by 0.5 m

def elbow_for(angle):
    ik.pole_angle = math.radians(angle); bpy.context.view_layer.update()
    return rig.matrix_world @ rig.pose.bones['DEF-upper_arm.L'].tail

# Measure the pole angle, don't guess it: at 0 this chain's elbow swings sideways, 90 degrees off the pole.
assert abs(elbow_for(0).z) < 0.3
best = max((-90, 90), key=lambda a: elbow_for(a).z)
assert elbow_for(best).z > 0.3                           # now it bends toward the pole
tip = rig.matrix_world @ rig.pose.bones['DEF-forearm.L'].tail
goal = rig.matrix_world @ rig.pose.bones['hand_ik.L'].head
assert (tip - goal).length < 1e-3, (tip, goal)

# A simple-expression driver works without Python auto-run.
rig.pose.bones['hand_ik.L']['ik_fk'] = 0.0
fcurve = ik.driver_add('influence')
var = fcurve.driver.variables.new(); var.name = 'switch'
var.targets[0].id, var.targets[0].data_path = rig, 'pose.bones["hand_ik.L"]["ik_fk"]'
fcurve.driver.expression = '1 - switch'
assert fcurve.driver.is_simple_expression

# Rigify ships with Blender and generates in background mode.
addon_utils.enable('rigify', default_set=True)
bpy.ops.object.armature_human_metarig_add()
metarig = bpy.context.object
assert bpy.ops.pose.rigify_generate() == {'FINISHED'}
generated = metarig.data.rigify_target_rig
assert generated and any(b.name.startswith('DEF-') for b in generated.data.bones)
assert all(b.name.startswith('DEF-') for b in generated.data.bones if b.use_deform)
assert 'IK_FK' in generated.pose.bones['upper_arm_parent.L']
```
