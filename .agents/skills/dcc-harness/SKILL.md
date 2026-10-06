---
name: dcc-harness
description: Start, resume, review or revise a Blender project using 3D Harness checkpoints, project decisions and scoped edit reservations from the normal agent chat.
---

# Work in a persistent DCC project

Use the installed `dcc-harness` command or `python -m dcc_harness` from this repository. Read [the everyday workflow](../../../docs/EVERYDAY_WORKFLOW.md) for exact arguments. These skills currently depend on this runtime and repository; copying this folder alone is not a complete installation.

For an existing continuity project, run `resume PROJECT --focus ID...` before authoring. It verifies the checkpoint chain and returns the brief, retained decisions, handoff, pending edits and scoped shared users. `RECONCILE` means inspect the saved/native outcome; it does not authorize replay. An existing untracked .blend is input for a new project, not a reason to overwrite a previous store.

For a new project, inspect the intended Blender instance, record the brief/decisions, save an owned native checkpoint and observe it with `dcc_harness.continuity_blender.observe()`. `start` requires clean saved-state evidence. Preserve the artist's current document; use an owned background file when live editing is unnecessary. Initial adoption establishes a baseline, not artistic acceptance.

For large instance-heavy observations, use the optional [compact storage](../../../docs/OBSERVATION_STORAGE.md) when all consumers have runtime 0.4.6 or later. Write new files with `write_json(..., compact_observation=True)` and read them with `evidence.read_json`; full checks still apply. Never repack a retained checkpoint in place or discard UV evidence to shorten a resume.

Load the relevant craft skill only: `dcc-architecture` for construction, `dcc-materials` for surface work, `dcc-environment-assembly` for site/dressing, or `dcc-lighting-review` for camera/light decisions. The existing `dcc-plan-environment`, `dcc-build-revise` and `dcc-review-continue` govern planning, authoring and evidence. Ordinary work does not require a blind trial or subagents.

Before a scoped edit, save its actual script and continuity contract. `begin-edit` requires the expected parent, current saved file and matching native observation; it reserves the retained script/contract. Execute that retained script once against an owned working copy. A reservation does not execute code. Save a new result, freshly observe it, then use `finish-edit`: it recomputes the frozen contract, retains a rejection or publishes a passing checkpoint plus decisions/handoff. Never edit the accepted native or retained script in place.

Inspect required review images before publication. If a numerically valid candidate is visually unsuitable, use `finish-edit --reject-reason "specific visible defect"` to retain it without changing the accepted parent or decisions. The outcome separates `native_check_passed` from publication. A numeric pass must not silently override the reviewer's decision; rejected attempts appear in the next resume packet.

On lost acknowledgement or quota interruption, keep the edit unresolved. Inspect actual effects and supply the observed result to `finish-edit --reconciled`; do not redispatch merely because no reply arrived. Partial metadata or stale locks require manual diagnosis. Automatic crash recovery, external-write interception and background scheduling are not implemented.

For review, use `review PROJECT`, inspect the referenced whole-scene/detail images, and separate measured preservation from visible quality. Readiness to inspect is not permission to mutate an unknown live editor. A direct manual/MCP edit must be explicitly adopted as a new measured parent before reserving further work.
