---
name: animatica-marionette
description: Use when posing characters or repairing keyed Blender animation with Animatica Marionette, including Autopose, motion trails, contact locks, smoothing, rig maps and edits to Choreographer takes.
---

# Animatica Marionette

Pose a character and refine its keyed motion using Marionette's local tools. Use [animatica-choreographer](../animatica-choreographer/SKILL.md) for text-driven generation and MMCP servers.

## Execution in 3D Harness

Follow [dcc-harness](../dcc-harness/SKILL.md) and [dcc-build-revise](../dcc-build-revise/SKILL.md). Inspect the character, action users, rig type, IK/FK state, FPS, frame range and installed add-on version. Save an owned baseline before editing keys; scope the affected character, prop and frames.

This is documentation-based workflow guidance, not a qualified provider or a documented Python API. Discover actual installed tools/operators before scripting; never fabricate an operator from a UI label. Use the project's managed route for native edits. If Animatica is unqualified there, report that boundary and provide artist-operated steps instead of bypassing the managed executor. Rig-map tests temporarily pose the rig, so treat them as native edits too.

## Start and pose

The [getting-started guide](https://animatica.ai/marionette/docs/getting-started) specifies Blender 5.0+ and a platform-specific licensed add-on ZIP. The bundled pose model runs offline on CPU, without a Blender account sign-in or GPU requirement. Installation and licensing are separate from adding this skill.

Select the rig, enable Autopose on the floating viewport bar, move a handle and key the result with Key Pose or `I`. Auto Keying can record successive edits. Marionette has no separate sidebar tab; with Choreographer installed, its tools share Choreographer's bar.

For [posing](https://animatica.ai/marionette/docs/posing), distinguish pinned handles, which retain their locations, from carried handles, which follow the body. Use the Handle Picker for per-handle position/turn constraints and slack. Reduce Body Follows or hold Alt during a drag for a more isolated limb change. Check contacts after altering floor or slack settings. Finger tools require finger bones.

## Respect the rig

The [rig guide](https://animatica.ai/marionette/docs/your-rig) documents Rigify, Auto-Rig Pro and CloudRig control rigs, plus Mixamo skeletons. Control-rig edits key controls; Mixamo edits pose bones directly. Do not infer arbitrary-rig compatibility from automatic skeleton recognition.

Marionette poses control rigs through FK. It can match and switch a limb initially in IK; an already animated IK limb is preserved. Inspect keyed switches and the Keep IK and FK Matched setting before diagnosing a mismatch. For Auto-Rig Pro or CloudRig, Connect Its IK and Test Rig Map can establish the rig mapping on an owned fixture. Correct joint identification in Settings → Skeleton; refreshing detection replaces manual joint choices. Preserve/export a corrected rig map before rebuilding it.

For Rigify, select the generated animation rig, not its metarig, before entering Pose Mode and Autopose. Turn on Rig Controls when comparing Marionette handles with the underlying controls and keyed channels. The [beginner video notes](../animatica-choreographer/references/video-workflows.md) locate this demonstration and other useful cues.

## Choose the edit

From [editing motion](https://animatica.ai/marionette/docs/editing-motion):

| Need | Tool and boundary |
|---|---|
| Local pose correction | Reach controls the surrounding frame interval; Falloff and Intensity shape it. Reach 0 edits one frame. |
| Neighboring-frame edit | Handle drags propagate with Auto Keying on, except on control rigs: use the motion trail there. |
| Reshape or retime an arc | Drag a trail point; Alt retimes it. Inspect the resulting timing. |
| Remove jitter | Smooth Brush edits keys per stroke; inspect its orange preview. |
| Stop a contact sliding | Lock in Place on a hand/foot over the contact interval; inspect entry and exit. |
| Carry a prop | Pick Up sets grips and the carrying interval. A later hand drag does not automatically carry the prop; rerun Pick Up. |
| Diagnose motion | Review Motion Check findings; use selective fixes to preserve intentional accents. |

These tools write keys. Compare the changed interval and its boundaries against the baseline, not only the edited pose.

Choose the visualization for the diagnosis: onion skin shows surrounding poses in place; motion trails expose joint arcs and timing; zoetrope separates overlapping poses spatially. Use them before brushing or locking to identify the actual problem. Recheck full-speed playback after the edit; a readable static trail alone does not establish good motion.

## Work with Choreographer

The [integration guide](https://animatica.ai/marionette/docs/choreographer) distinguishes Choreographer key-pose ghosts from Marionette's edit-range onion skin. Key Pose becomes a constraint for the next generated take; clicking a ghost jumps to that pose for editing.

Edit Root Trajectory requires Choreographer. It redirects a take while retaining timing; it does not re-solve feet, so sharp bends can introduce sliding. Use gentle bends and inspect contacts. Existing locks can be applied again over a newly generated take, but this is not a guarantee that arbitrary path edits preserve contacts. Marionette's supported control rigs do not establish Choreographer's generation/baking support for those same rigs.

Example: to adjust a Rigify character's reaching hand over several frames, preserve the action, drag its motion trail with a bounded Reach, inspect the approach/contact/release and neighboring keys, and verify IK/FK playback. If redirecting its generated walk, check the feet again after changing the root path.

## Troubleshoot and verify

Use the [troubleshooting guide](https://animatica.ai/marionette/docs/troubleshooting):

- Missing bar: check View → Marionette Bar, Show Gizmo, and the combined Choreographer bar.
- Pose disappears after a frame change: key it or enable Auto Keying.
- Missing edit tools: the character needs keyed animation.
- One-frame-only edit: inspect Reach/Intensity and use the trail for control rigs.
- Wrong joint: inspect Skeleton mapping; contact locking also needs an appropriate two-bone parent chain.

Use [blender-animation](../blender-animation/SKILL.md) and [blender-mocap](../blender-mocap/SKILL.md) for evaluated playback and contact checks. Measure planted-foot world-space drift and floor penetration over the intended contact interval; visually review body balance and hand/prop attachment. Verify unedited motion and shared actions were preserved, then save a new checkpoint and reopen it for readback.

Sources checked 2026-10-27. No Marionette native execution or artist-scene compatibility has been qualified by this skill addition. Report observed results separately from these documented capabilities.
