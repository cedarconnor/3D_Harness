---
name: animatica-choreographer
description: Use when generating or revising Blender character motion with Animatica Choreographer, directing prompt blocks, key poses, waypoints and pins, reviewing takes, or connecting a self-hosted MMCP motion server.
---

# Animatica Choreographer

Direct generated character motion, then inspect the take before keeping it. For manual posing and motion repair, use [animatica-marionette](../animatica-marionette/SKILL.md).

## Execution in 3D Harness

Start with [dcc-harness](../dcc-harness/SKILL.md) and use [dcc-build-revise](../dcc-build-revise/SKILL.md) for scene changes. Record the character, action/NLA state, frame range, FPS, installed add-on version, backend and model before generation. Preserve a saved baseline and inspect shared action users.

This skill supplies documentation-based guidance, not a qualified Animatica provider or a Python operator API. Discover installed tools and inspect the installed add-on before scripting it; do not invent `bpy.ops` names. Managed projects require their qualified execution route. If that route cannot drive this add-on, report the missing qualification and provide an artist-operated procedure rather than bypassing it with direct writes. Product Accept is distinct from a harness artist approval gate.

## Setup

The [overview](https://animatica.ai/blender/docs/overview) specifies Blender 5.0+. Open the 3D View sidebar's Animatica tab after installing the add-on. Check the selected model and armature explicitly.

For [connection setup](https://animatica.ai/blender/docs/sign-in), use Cloud with the user's account, or enable Self-hosted and supply the existing MMCP URL. Localhost can work with Blender online access disabled; remote hosts, including LAN servers, require it enabled. Never forward a Cloud session to a self-hosted endpoint. Some setup prose still calls the posing companion Autoposer Pro; consult Marionette's own docs and the installed version for its current UI.

Generation transmits prompts, constraints, skeleton information and settings to the selected service; see [privacy](https://animatica.ai/blender/docs/privacy). Skill installation alone does not authorize generation or account changes. Read [MMCP integration](references/mmcp.md) when diagnosing a server or implementing an adapter.

## Direct a take

1. Establish the intended action, duration, root travel, contact points and review frames. Start with a short take on the intended rig; use the ready-made character to isolate rig-specific failures.
2. Use [prompt blocks](https://animatica.ai/blender/docs/prompt-blocks) for successive actions. Resize blocks to set timing. An empty prompt lets the model fill that interval; a disabled block is skipped. During review, the block menu supports regenerating a range.
3. Add key poses inside the generated interval. Check the panel's range summary: poses outside it are excluded. Use [waypoints](https://animatica.ai/blender/docs/constraints-panel) for timed root locations and facing, and pins for hand/foot targets. They belong to their originating character; verify ownership after changing selection.
4. Set quality, cleanup and a reproducible seed via [Settings](https://animatica.ai/blender/docs/settings-panel). Seed 0 requests fresh randomness; retain the actual seed used. Blend Between Blocks controls transitions, including boundaries against existing keys. Change one setting at a time when diagnosing motion.

## Review and keep

The [panel reference](https://animatica.ai/blender/docs/animatica-panel) documents these behaviors:

- Resolve the pending take with Accept or Reject before switching characters. Leave NLA tweak mode before Generate, Accept or Reject.
- Compare existing variations before generating again. In place can be toggled during review without another generation.
- Accepted blocks normally become NLA clips; generation into a gap between existing keys instead fills the action. Inspect the actual result and stashed previous action.
- Reject restores the preceding action, pose and range while retaining keys edited during review. Verify this against the saved baseline rather than assuming a complete rollback.
- For multiple characters, Each Their Own uses individual direction. Shared uses the active character's prompts and omits waypoints/pins. Check the displayed generation count before dispatch.

Inspect playback, boundary poses, foot contacts, root travel and NLA mixing. Save a new checkpoint and record model, settings, actual seed, sample choice, prompts, constraints and review evidence. After a lost response, inspect the pending take/job before considering another generation.

## Limits that change the plan

The [limits reference](https://animatica.ai/blender/docs/tips-and-limits) says Loop requires one prompt block and model support. Do not promise a multi-block seamless loop. Generation produces dense body keys; face animation and detailed finger motion need separate work. Choreographer's documented control-rig baking supports Rigify and Mixamo Control Rig; other control rigs receive deform-bone motion. Marionette's broader rig support does not extend that Choreographer guarantee. Linked actions and library overrides cannot be edited in place by the listed take-editing features; establish an owned local action before those edits.

Example: for a looping walk, use one supported loop block, review contact continuity across the seam, then save the accepted take. For a walk-then-wave shot, use separate blocks and review their transition instead of enabling Loop.

## Lessons from the video workflows

Read the [timestamped video notes](references/video-workflows.md) for Mixamo preparation, gap-jump direction and differences between the demonstrated interfaces.

- **Imported Mixamo character:** start from an FBX in T-pose when following that tutorial. Inspect its imported action and keys before adding direction. Preserve the source, then remove only unwanted import keys from the owned working action so they do not compete with intentional poses.
- **Spatial action such as a gap jump:** establish takeoff/landing poses and timing, fit the prompt interval, and review the first take. Add a short hold pose or a follow-on block only when the intended performance needs it; verify the boundary does not create a freeze or velocity discontinuity. These are directing techniques, not evidence that the model sees scene geometry or solves collisions.
- **Iteration:** keep the recorded seed when comparing timing or pose changes to reduce random variation. Changed constraints still change the request; a fixed seed does not guarantee identical motion after editing the shot.
- **Older tutorials:** Proscenium labels, connection buttons, text-to-pose dialogs and standalone retarget/export controls are version-specific. Locate their current documented equivalents and check model capabilities before using them.

## Evidence boundary

Sources above checked 2026-10-27. These workflows have not been executed with Animatica in this repository. Report documentation support, installed capability, observed motion and saved-file verification separately. Existing Blender craft verification does not qualify these add-ons.
