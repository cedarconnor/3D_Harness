---
name: dcc-build-revise
description: Build or revise owned Blender assets using 3D Harness native observations, scoped edit reservations and saved checkpoints through an existing MCP connection or owned background Blender.
---

# Build, measure and revise

Read the project's brief, `CONTINUE.md` and latest observation. Use [the everyday workflow](../../../docs/guides/EVERYDAY_WORKFLOW.md) for exact commands. Discover the actual connected tools; the current Blender Lab execute tool returns a JSON-compatible `result` variable. Other integrations may have different conventions.

For everyday projects, start with `dcc-harness` and [managed execution](../../../docs/guides/MANAGED_EXECUTION.md). Background runs use `run-execute`; [paired open scenes](../../../docs/guides/LIVE_BLENDER.md) use `blender_execute`/`live-execute`. Both share reservation, verification and publication. Discover the live session and inspect stable target IDs before an open-scene edit. Use `run-submit` for stages; use the backend's `run-reconcile` or `live-reconcile` for interrupted outcomes. The manual `begin-edit`/`finish-edit` instructions below apply only to advisory projects. Load the relevant architecture, materials, assembly or lighting skill for actual craft decisions. Frozen trials continue using their supplied method/runtime, not newer local instructions.

When coordination is enabled, retain the note IDs that this revision addresses. Native publication does not resolve those notes. Record a [feedback response](../../../docs/guides/STRUCTURED_FEEDBACK.md) with the resulting checkpoint and evidence; mark partial work honestly. A separate verification/disposition records closure. On a lost response receipt, reuse its request ID and exact payload; never redispatch Blender to recover metadata.

If the live connection is unavailable, an authorized owned checkpoint may be processed in background Blender. Record that execution mode and preserve the user's editor. Background execution does not qualify the live MCP integration.

For a new deliverable, check its intended identity and meaningful requirements first; record an expected missing-target failure. For an edit, record the passing baseline and allowed delta. Never break an existing asset merely to create a failing check.

Begin with silhouette, proportions and construction. Check modular joins and sightlines before detail. Keep material texture scale coherent across related objects; preserve the project's world and lighting during asset work. Use material and lighting recipes as adjustable methods, not global resets. In appearance review, prioritize the focal hierarchy and readable form over added noise.

Use `dcc_instance_id` per placement, `dcc_asset_id` per definition and `dcc_material_id` per shared material. Detect duplicate IDs after copying; do not identify an ambiguous duplicate by guesswork. Linked mesh edits affect all users: decide explicitly between editing the shared definition and making a local variant.

Reserve the planned script with `begin-edit` before dispatch. Do not retry an unresolved write. Observe native state, then complete the edit with `finish-edit`, or with `finish-edit --reconciled` after inspecting an uncertain outcome. Legacy journal-only projects use the pilot `begin`/`finish` journal instead. This is a single-writer advisory system; direct MCP writes are not intercepted.

Keep each dispatched script immutable, including failed attempts; save a corrected script under a new name so its journal hash remains meaningful. For continuity stages use the pinned `continuity_blender.observe` and `continuity_checks.evaluate_stage` runtime described in `docs/guides/CONTINUITY_USAGE.md`. Keep independently corrected evaluations separate from a frozen worker's evidence.

Save accepted task boundaries to new checkpoint filenames. Observe saved files with the `observe` command, which reopens them in a fresh background Blender and never saves; `start` and `begin-edit` require its clean saved-state fields. In a background Blender script, `dcc_harness.continuity_blender.observe()` is equivalent straight after opening or saving the file; an interactive session observes `native_dirty: true`, because Blender does not mark edits made from Python as modified. The pilot observer `dcc_harness.blender.observe()` and `dcc_harness.evidence.evaluate/compare` remain for legacy journal projects and frozen trials only. Reject missing coverage and unsupported rules. Do not claim topology cleanliness or animation correctness from fields this observer does not inspect.

For an A/B/C experiment, B uses written procedures with native inspection; added deterministic measurement scripts belong to C. Evaluate all conditions with the same independent evaluator.

