---
name: blender-animation
description: Animate in Blender 5.x with sound timing and spacing, and script animation correctly against slotted actions. Covers blocking, breakdowns and splining, ease and physics-based timing, arcs and overlap, contacts, loops, the Graph Editor and F-curve modifiers, NLA, the layered Action / slot / channelbag API, fast keyframe insertion, baking, and checking motion at full speed.
---

# Animation

Animation is timing (when) and spacing (how far between frames). Plan the beats before keying. Judge the result at full speed, never by scrubbing stills alone.

## Plan the shot

- **Shot specification.** Before keying, write down the fps and `fps_base` (the frame rate is fps ÷ fps_base), the inclusive frame range, the beats in seconds, the contacts, the part that leads each move, and the camera.
- **Units.** Work in real units: 1 m, 9.81 m/s². Physics only looks right at the right scale.
- **Reference.** Film yourself or find real footage. Count frames in the reference rather than inventing them.

## Workflow: block, break down, spline, polish

1. **Blocking.** Key the key poses on every main control at once, with `CONSTANT` interpolation, so timing is read without in-betweens.
2. **Breakdowns.** Add the poses that define arcs, overlap and weight shifts: the pelvis leads, feet clear the ground, hands travel in arcs, and the head lags.
3. **Splining.** Switch to `BEZIER` with `AUTO_CLAMPED` handles only when the timing reads. Then fix the spacing in the Graph Editor; do not add more keys.
4. **Polish.** Work in layers: root and pelvis, then the legs and feet with locked contacts, then torso, arms and head, then secondary motion such as hair, tails, cloth and fingers. Offset overlap by 2–4 frames, and measure delays in seconds rather than uniform frame offsets.

## Timing that reads physically

- **Falls and jumps.** Flight time is T = 2·v₀ / g, and the apex height is h = g·T² / 8. A 0.5 m hop takes about 0.64 s, 15 frames at 24 fps. Only the centre of mass follows the parabola.
- **Accelerate into impacts.** Do not ease into an impact. Keep first contact, maximum compression and settle as separate keys. Impacts are asymmetric: a fast hit, a slower recovery.
- **Walk cycles.** At 24 fps, about 12 frames per step (two steps a second) reads natural, 14–16 relaxed. Weight transfers onto the support foot before the other lifts. Plan footsteps from the root path.
- **Contacts.** Never fix feet sliding through the floor by moving the whole body. Lock planted contacts in world space with IK targets or Child Of.
- **Eyes.** Saccades take 2–4 frames and lead head turns. A blink closes in about 2 frames and opens in 3–4, tied to changes of thought, not a timer.
- **Mechanical motion.** Turntables and machines move at constant speed with linear keys. Everything organic eases.

## Loops

Make the last key equal to the first, at frame N+1, and render frames 1..N. Matching values is not enough: the velocity must also match across the seam. Check the tangents at both ends, or use the Cycles F-curve modifier with `cycles_before` and `cycles_after`, and preview several repetitions.

## Graph Editor and F-curve modifiers

- **Interpolation.** `CONSTANT`, `LINEAR` and `BEZIER`, plus the Penner easings (`BACK`, `ELASTIC`, `BOUNCE`, with `easing`, `back`, `amplitude` and `period`). The built-in easings replace easing libraries for motion graphics.
- **Rotation repair.** Use the Euler filter on a whole XYZ group in a single rotation mode. For quaternions, normalize and keep the sign continuous (dot ≥ 0 with the previous key), and never smooth the four components separately.
- **Modifiers.**
  - **Noise** (`scale` in frames, `strength`, `phase` as the seed) for handheld drift and idle jitter. Put it on a separate offset control, windowed with its restricted range and blend in/out.
  - **Cycles** for repeats.
  - **Stepped** for animation on twos or threes.
  - **Smooth (Gaussian)** (5.1+) for dense data. It must be first in the stack and does not combine with Cycles.
- **Clean and Decimate.** Use them only after the animation is approved, and check the world-space contact or tip error afterwards. A curve-error threshold is not a hand-position error.

## The 5.x Action API

Since 4.4 an Action holds **slots**, one per animated datablock, with layers, strips and channelbags inside. Since 5.0, `action.fcurves`, `action.groups` and `action.id_root` are gone.

- **Inserting keys.** `obj.keyframe_insert('location', frame=10)` still creates the action and its slot.
- **Reading F-curves.** Use `bpy_extras.anim_utils.animdata_get_channelbag_for_assigned_slot(obj.animation_data).fcurves`, or `action_get_channelbag_for_slot(action, slot)`. Use `action_ensure_channelbag_for_slot(action, slot)` only when you mean to create data, never during read-only analysis.
- **Assigning an Action.** Assigning `animation_data.action` is not enough: set `animation_data.action_slot`, chosen from `action_suitable_slots`, or the object does not animate. One Action can hold slots for several datablocks, such as the object and its armature data; check which slot each uses.
- **Many keys.** Use `fcurve.keyframe_points.add(n)`, then `foreach_set('co', ...)` with flat (frame, value) pairs, then `fcurve.update()`. `keyframe_points.insert(..., options={'FAST'})` also avoids recalculating per key.
- **Evaluating poses.** `fcurve.evaluate(f)` is one channel, not the final pose with constraints, drivers and NLA. Use `scene.frame_set(f, subframe=...)` and read the evaluated object, then restore the user's frame.
- **Tag after editing.** After editing keys or F-curve modifiers through Python, call `fcurve.update()` and `action.update_tag()` before `frame_set`. Measured on 5.1: without the tag, `fcurve.evaluate()` shows the new curve while the object still plays the old one.
- **Saving actions.** Give Actions you keep a fake user (`action.use_fake_user = True`). Reuse one Action per rig per take.

## NLA and baking

- **NLA.** Push finished actions to NLA strips to layer, blend and retime them. Strip `scale` 2 doubles the duration. Apply Scale writes into the shared Action, so copy the Action first.
- **Baking.** Bake constraints, IK and drivers to plain keys for export, with `bpy.ops.nla.bake(..., visual_keying=True, clear_constraints=True, bake_types={'POSE'})` on a **copy**, or headless with `anim_utils.bake_action_objects`. Compare poses at intermediate frames afterwards.
- **What to key.** Never key DEF-, MCH- or ORG- bones; key controls. Avoid keying bone scale unless the rig expects it.

## Check motion at full speed

Make a playblast or a low-sample EEVEE preview at the delivery frame rate, and watch it several times. Use a contact sheet to find pops and discontinuities, flagging large frame-to-frame jumps, but always confirm at speed. Check the first and last frames, the loop seam and every contact. Measure foot slide, the distance a planted foot moves while within a few centimetres of the floor, on the evaluated pose.

```python verify
import bpy
import numpy as np
from bpy_extras import anim_utils

scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = 24, 1.0
ball = bpy.data.objects.new('ball', None); scene.collection.objects.link(ball)

# Ballistic hop: 0.5 m apex. T = 2 v0 / g and h = g T^2 / 8, so T = sqrt(8 h / g).
g, h = 9.81, 0.5
T = (8 * h / g) ** 0.5
frames = round(T * scene.render.fps / scene.render.fps_base)
assert frames == 15, frames

# Keys through the normal API create the action and its slot; read F-curves through the channelbag.
ball.location.z = 0; ball.keyframe_insert('location', index=2, frame=1)
ball.location.z = h; ball.keyframe_insert('location', index=2, frame=1 + frames // 2)
ball.location.z = 0; ball.keyframe_insert('location', index=2, frame=1 + frames)
action, slot = ball.animation_data.action, ball.animation_data.action_slot
assert not hasattr(action, 'fcurves') and slot is not None and slot in action.slots[:]
bag = anim_utils.animdata_get_channelbag_for_assigned_slot(ball.animation_data)
z = bag.fcurves.find('location', index=2)
assert len(z.keyframe_points) == 3

# Blocking reads in CONSTANT; splining switches to BEZIER with AUTO_CLAMPED handles.
for key in z.keyframe_points:
    key.interpolation = 'CONSTANT'
assert z.evaluate(4) == 0.0
for key in z.keyframe_points:
    key.interpolation, key.handle_left_type, key.handle_right_type = 'BEZIER', 'AUTO_CLAMPED', 'AUTO_CLAMPED'
z.update()
assert 0 < z.evaluate(4) < h

# Thousands of keys at once: add, foreach_set flat (frame, value) pairs, then one update.
spin = bag.fcurves.new('rotation_euler', index=2)
keys = np.zeros((240, 2), dtype=np.float32); keys[:, 0] = np.arange(1, 241); keys[:, 1] = np.linspace(0, 6.283, 240)
spin.keyframe_points.add(len(keys)); spin.keyframe_points.foreach_set('co', keys.ravel()); spin.update()
assert len(spin.keyframe_points) == 240

# Assigning an action needs its slot too; a second object gets its own slot.
other = bpy.data.objects.new('other', None); scene.collection.objects.link(other)
other.animation_data_create().action = action
if other.animation_data.action_slot is None:
    other.animation_data.action_slot = other.animation_data.action_suitable_slots[0]
scene.frame_set(1 + frames // 2)
assert abs(other.location.z - h) < 1e-5

# Evaluated pose at a frame, then a Cycles modifier for a loop.
scene.frame_set(1)
assert abs(ball.location.z) < 1e-6
z.modifiers.new('CYCLES')
action.update_tag()          # F-curve edits made through Python reach the scene only after tagging the Action
scene.frame_set(1 + frames + frames // 2)
assert abs(ball.location.z - h) < 1e-4, ball.location.z
action.use_fake_user = True
```
