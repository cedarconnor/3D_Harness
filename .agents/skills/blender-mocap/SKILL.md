---
name: blender-mocap
description: Import, clean and retarget motion capture in Blender 5.x. Covers BVH and FBX import settings (scale, axes, frame rate, rotation mode), diagnosing curve problems before smoothing (Euler wrap, quaternion flips, spikes, foot slide), cleanup tools, constraint-based retargeting with bone maps and rest-pose alignment, baking to the target rig, root motion, and checking contacts on the evaluated result.
---

# Motion capture and retargeting

Mocap is dense, noisy and recorded on someone else's skeleton. The job has four parts:

1. Import it at the right scale and rate.
2. Diagnose problems before smoothing anything.
3. Move it onto the production rig without losing contacts.
4. Bake it into clean keys.

Keep the raw take untouched, and work on copies.

## Import

- **BVH.** `bpy.ops.import_anim.bvh(filepath, global_scale=..., frame_start=1, update_scene_fps=True, update_scene_duration=True, rotate_mode='NATIVE', axis_forward='-Z', axis_up='Y')`.
  - BVH files are usually in centimetres, so `global_scale=0.01`. Confirm by measuring the hip height (about 0.9–1.0 m for an adult) rather than trusting the header.
  - Match the frame rate: `update_scene_fps=True`, or `use_fps_scale=True` to resample into the scene's rate.
  - Use `rotate_mode='QUATERNION'` when the data flips: quaternions do not gimbal-lock.
- **FBX.** In 5.x the default importer is the C++ `bpy.ops.wm.fbx_import`; `import_scene.fbx` is legacy. Its `automatic_bone_orientation` and `ignore_leaf_bones` options help with skeletons from other packages.
- **After import.** Check the scale, the facing direction, the frame range, the rest pose (T-pose, A-pose or a first-frame pose), and whether the root carries the translation.

## Diagnose before smoothing

Classify every problem first, because each has a different fix:

- **Euler 360° wraps.** A channel jumps by about 2π between frames. Run the Euler filter (`graph.euler_filter`, which needs a Graph Editor context) on whole XYZ groups, or unwrap the values in numpy.
- **Quaternion sign flips.** q and −q are the same rotation, so a sign flip is not a pose change. Make consecutive keys continuous (if dot(q₀, q₁) < 0, negate q₁), and never smooth the four components separately.
- **Real IK or pole flips.** The joint really pops. Fix the pole, not the curve.
- **Spikes and jitter.** Single-frame outliers or high-frequency noise from marker swaps. Remove the spike, then smooth lightly.
- **Foot slide and floor penetration.** Fix them with contact locking (below), not by smoothing.
- **Timing problems.** Retime with one monotonic time map applied to every related channel; see [animation](../blender-animation/SKILL.md).

Measure angular speed per bone: angle = 2·acos(|q₀·q₁|) divided by the frame time. Spikes stand out at once.

## Cleanup tools

- **Smoothing.** The Smooth (Gaussian) F-curve modifier (5.1+) is non-destructive and restricted to a frame range, and must be first in the stack. Butterworth and Gaussian smoothing operators need an editor context.
- **Reducing keys.** Decimate or Clean only after the motion is approved, and check world-space hand and foot error afterwards.
- **Contact locking.** Find the frames where a foot is near the floor and slow. Key an IK foot control at the planted position for that interval, then blend back. Or drive a Child Of or Limit Distance constraint to a floor marker, then bake.
- **Low-frequency offsets.** To change a pose over a stretch of frames, add an offset that rises and falls smoothly (smoothstep 3u² − 2u³), rather than re-posing every frame.

## Retarget

1. **Bone map.** Map source bones to target bones for at least hips, spine, chest, neck, head, upper arms, forearms, hands, thighs, shins and feet. Score how much of the map matched automatically. A low score needs a person to review it, not a guess.
2. **Rest poses.** Align the rest poses: pose the target to match the source's rest pose, or the reverse. Different arm angles (T versus A) otherwise become permanent offsets.
3. **Constraints.**
   - On each mapped target bone, add a **Copy Rotation** constraint to its source bone. Use the `WORLD` space in both spaces when the bone orientations differ, and `LOCAL` when the rigs share bone axes.
   - Only the hips get **Copy Location**, scaled by the leg-length ratio of target to source, so feet do not slide.
4. **Bake.** Bake the target to keys: `bpy.ops.nla.bake(frame_start=..., frame_end=..., only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=False, bake_types={'POSE'})` in Pose Mode on the target. Headless, use `bpy_extras.anim_utils.bake_action_objects`.
5. **Slot.** After assigning the baked Action, set `animation_data.action_slot` (4.4+), or the rig will not play it.
6. **Store the take.** Push it to an NLA strip, and give the Action a fake user.

Add-ons such as Rokoko (free), Auto-Rig Pro Remap (paid) and the Retarget extension automate the bone map and rest alignment. The checks below still apply to their output.

## Root motion

Engines that use root motion need the travel on a root bone at the floor, not on the hips. Bake the hips' horizontal translation and yaw onto the root, and leave the hips' height and the remaining rotation on the hips. Export with all bones baked (`bake_anim_use_all_bones=True` for FBX).

## Check the result

Compare the target against the source at several frames, especially extremes and contacts, using world-space positions of hands and feet scaled by the limb ratio. Measure foot slide: the distance a planted foot moves while within a few centimetres of the floor. Measure floor penetration and hand-to-prop distances. Watch the retarget at full speed next to the source. A pass on numbers alone does not mean the motion keeps its weight and intent.

```python verify
import bpy, math
import numpy as np
from mathutils import Quaternion

scene = bpy.context.scene
scene.render.fps = 30

def make_rig(name, upper, lower):
    arm = bpy.data.armatures.new(name); rig = bpy.data.objects.new(name, arm); scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
    a = arm.edit_bones.new(upper); a.head, a.tail = (0, 0, 1), (0, 0, 1.5)
    b = arm.edit_bones.new(lower); b.head, b.tail, b.parent, b.use_connect = (0, 0, 1.5), (0, 0, 2), a, True
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig

# Source take: the lower bone swings 0 -> 90 degrees over 30 frames.
source = make_rig('mocap', 'Hips', 'Spine')
spine = source.pose.bones['Spine']; spine.rotation_mode = 'XYZ'
for frame, angle in ((1, 0), (30, 90)):
    spine.rotation_euler.x = math.radians(angle); spine.keyframe_insert('rotation_euler', frame=frame)

# BVH round trip in centimetres: export at 100x, import at 0.01 and measure the bone length.
path = str(WORK / 'take.bvh')
scene.frame_start, scene.frame_end = 1, 30
bpy.context.view_layer.objects.active = source; source.select_set(True)
bpy.ops.export_anim.bvh(filepath=path, global_scale=100.0, frame_start=1, frame_end=30)
bpy.ops.import_anim.bvh(filepath=path, global_scale=0.01, update_scene_fps=True, rotate_mode='QUATERNION')
imported = bpy.context.object
assert abs(imported.data.bones['Spine'].length - 0.5) < 1e-3 and scene.render.fps == 30

# Quaternion sign continuity: q and -q are the same rotation; make neighbours agree before any smoothing.
keys = [Quaternion((1, 0, 0), math.radians(a)) for a in range(0, 360, 30)]
keys[5] = -keys[5]                                          # an imported sign flip
for i in range(1, len(keys)):
    if keys[i - 1].dot(keys[i]) < 0:
        keys[i] = -keys[i]
speed = [2 * math.acos(min(1, abs(keys[i - 1].dot(keys[i])))) for i in range(1, len(keys))]
assert all(keys[i - 1].dot(keys[i]) > 0 for i in range(1, len(keys))) and max(speed) - min(speed) < 1e-6

# Euler wrap unwrapping in numpy: a 350 -> 10 degree jump becomes 350 -> 370.
wrapped = np.radians([340, 350, 10, 20])
assert np.allclose(np.degrees(np.unwrap(wrapped)), [340, 350, 370, 380])

# Retarget onto a rig with different bone names through a bone map and Copy Rotation, then bake visual keys.
target = make_rig('character', 'DEF-pelvis', 'DEF-spine')
bone_map = {'DEF-pelvis': 'Hips', 'DEF-spine': 'Spine'}
for target_bone, source_bone in bone_map.items():
    c = target.pose.bones[target_bone].constraints.new('COPY_ROTATION')
    c.target, c.subtarget = source, source_bone
bpy.ops.object.select_all(action='DESELECT'); target.select_set(True); bpy.context.view_layer.objects.active = target
bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(frame_start=1, frame_end=30, only_selected=True, visual_keying=True, clear_constraints=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
assert not any(pb.constraints for pb in target.pose.bones)
assert target.animation_data.action_slot is not None
for frame in (1, 15, 30):
    scene.frame_set(frame)
    a = (source.matrix_world @ source.pose.bones['Spine'].matrix).to_quaternion()
    b = (target.matrix_world @ target.pose.bones['DEF-spine'].matrix).to_quaternion()
    assert abs(abs(a.dot(b)) - 1) < 1e-4, frame
target.animation_data.action.use_fake_user = True
```
