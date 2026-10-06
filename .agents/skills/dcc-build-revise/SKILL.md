---
name: dcc-build-revise
description: Build or revise owned Blender assets using the 3D Harness pilot's native observations, scoped changes and saved checkpoints through an existing MCP connection.
---

# Build, measure and revise

Read the project's brief, `CONTINUE.md`, latest observation and `docs/PILOT_USAGE.md`. Discover the actual connected tools; the current Blender Lab execute tool returns a JSON-compatible `result` variable. Other integrations may have different conventions.

For everyday projects, start with `dcc-harness` and `docs/EVERYDAY_WORKFLOW.md`. Use its `begin-edit`/`finish-edit` reservations instead of manually issuing competing journal calls. Load the relevant architecture, materials, assembly or lighting skill for actual craft decisions. Frozen trials continue using their supplied method/runtime, not newer local instructions.

If the live connection is unavailable, an authorized owned checkpoint may be processed in background Blender. Record that execution mode and preserve the user's editor. Background execution does not qualify the live MCP integration.

For a new deliverable, check its intended identity and meaningful requirements first; record an expected missing-target failure. For an edit, record the passing baseline and allowed delta. Never break an existing asset merely to create a failing check.

Begin with silhouette, proportions and construction. Check modular joins and sightlines before detail. Keep material texture scale coherent across related objects; preserve the project's world and lighting during asset work. Use material and lighting recipes as adjustable methods, not global resets. In appearance review, prioritize the focal hierarchy and readable form over added noise.

Use `dcc_instance_id` per placement, `dcc_asset_id` per definition and `dcc_material_id` per shared material. Detect duplicate IDs after copying; do not identify an ambiguous duplicate by guesswork. Linked mesh edits affect all users: decide explicitly between editing the shared definition and making a local variant.

Log the planned script before dispatch with the journal. Do not retry an unresolved write. Observe native state, then complete the journal with evidence or reconcile it explicitly. This is a single-writer advisory system; direct MCP writes are not intercepted.

Keep each dispatched script immutable, including failed attempts; save a corrected script under a new name so its journal hash remains meaningful. For continuity stages use the pinned `continuity_blender.observe` and `continuity_checks.evaluate_stage` runtime described in `docs/CONTINUITY_USAGE.md`. Keep independently corrected evaluations separate from a frozen worker's evidence.

Save accepted task boundaries to new checkpoint filenames. Use `dcc_harness.blender.observe()` for actual measured fields and `dcc_harness.evidence.evaluate/compare` for rules and declared-change checks when the condition includes helpers. Reject missing coverage and unsupported rules. Do not claim topology cleanliness or animation correctness from fields this observer does not inspect.

For an A/B/C experiment, B uses written procedures with native inspection; added deterministic measurement scripts belong to C. Evaluate all conditions with the same independent evaluator.

