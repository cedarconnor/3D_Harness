# Live Blender Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Edit the explicitly attached open Blender scene through the existing managed service, with richer observation, visual feedback and recoverable operations in both workflow modes.

**Architecture:** Extract background dispatch behind a backend interface while preserving shared admission and publication. Add a paired live bridge with main-thread jobs, immutable save copies, scoped change detection and independent verification. The live scene retains successful edits; failed or ambiguous edits require reconciliation.

**Tech Stack:** Python 3.11+, standard library, MCP SDK 1.26.0, Blender 5.1.1, unittest.

**Spec:** [Live Blender capabilities design](../specs/2026-10-22-live-blender-capabilities-design.md), P21. Follow with [P22 add-on capabilities](2026-10-22-addon-capabilities.md).

## Global Constraints

- Python 3.11+, MCP SDK 1.26.0, Blender 5.1.1 on Windows are the initial qualification targets.
- One managed execution service owns admission, operation identity, budgets, verification and publication for background and live backends.
- Unknown mutation outcomes are never automatically replayed; live Blender is never killed to enforce a deadline.
- No telemetry, user-activity recording, tracking URLs or automatic external network calls are introduced.
- Artist approval remains in the existing owner terminal/review-import path; MCP cannot approve its own stage.
- Source and installed-wheel tests, source-archive parity and owned native positive/negative fixtures are required for each increment.
- Existing runtime-pinned projects retain their installed runtime; no silent project migration.

## Review Focus

1. Unsaved/untitled work and relative dependencies survive attach and save-copy; the artist file is not overwritten (Task 3).
2. Same-path reload, rename/duplicate names and edits during preparation cannot target an unintended object/session (Tasks 2â€“4).
3. Lost replies or restart after mutation never execute twice; failure is distinguishable from proven cancellation (Tasks 1, 4).
4. A rejecting verifier or a non-cooperative operator leaves the artist's process and later edits intact (Tasks 4, 6).
5. Live routing, preview jobs or direct bridge access cannot fabricate owner approval or silently bypass managed admission (Tasks 2, 5â€“6).

## File Structure and Contract

| Files | Responsibility |
| --- | --- |
| `dcc_harness/execution.py`, new `execution_backends.py` | Existing service plus backend protocol/background implementation |
| new `live.py`, `live_contracts.py` | Host orchestration, binding, serialized request/receipt validation |
| `blender_bridge.py`; new `data/bridge/session.py`, `jobs.py`, `inspection.py`, `operations.py` | Transport client; isolated Blender-side session/job/inspection/recipe modules |
| `data/bridge/__init__.py`, `data/upstream.json`, `distribution.py` | Protocol 3 dispatch, lifecycle, file-manifest export |
| `mcp_server.py`, `__main__.py`, `bootstrap.py`, `guidance.py`, `environment_workflow.py` | Public routes, live adoption, actionable state and gate invalidation |
| new `tests/test_execution_backends.py`, `test_live.py`, `test_live_protocol.py`; existing MCP/distribution tests | Portable contracts and real transport checks |
| new `scripts/qualify_live.py`; existing `verify_release.py`, `qualify_mcp.py` | Owned GUI and installed-artifact qualification |

Define validated dict schemas in `live_contracts.py` and type them with TypedDict. `OperationRequest` contains `schema=dcc.execution.operation.v2`, UUID, project/run/stage/expected-parent, backend, binding ID, operation kind, targets, parameters, retained script/contract/handoff hashes, runtime hash and deadline. Background script requests retain their original fields. Live operations initially reference built-in recipe IDs, not arbitrary operator strings.

`PreparedOperation`: operation UUID, session/document generation, preparation token, pre-copy path/hash, scoped fingerprint, coverage descriptor and expiry. Tokens last 30 seconds; expiry before dispatch returns `STALE_PREPARATION` with no mutation. `JobReceipt`: operation/request hash, ordered state, candidate path/hash when available, error/uncertainty and local artifact references. Polling has a 2-second response deadline and never submits work. Jobs may exceed it within the run budget. Transport JSON remains bounded (64 KiB request, 8 MiB response); large files use retained workspace paths.

### Task 1: Preserve one execution service while introducing backends

**Files:** Modify `execution.py`; create `execution_backends.py`, `live_contracts.py`, `tests/test_execution_backends.py`; extend `tests/test_execution.py`.

**Interfaces:** `ExecutionBackend.prepare(request: dict) -> dict`, `submit(request: dict, prepared: dict) -> str`, `status(operation_id: str) -> dict`, `cancel(operation_id: str) -> dict`. `BackgroundBackend` preserves current behavior. `execution.create(..., backend='background')` writes v2 for new runs; readers retain v1 background interpretation. Existing `execution.execute(...)` signature remains a compatibility wrapper. New `execution.execute_operation(root, request: dict) -> dict` performs shared admission/reservation/verification/publication.

- [x] Write fake-backend regressions `test_background_api_preserved`, `test_duplicate_uuid_dispatches_once`, `test_changed_request_refused`, `test_restart_after_dispatch_needs_reconciliation`, `test_v1_read_does_not_rewrite`. Assert repeated request has `dispatch_count == 1`, changed hash raises, and an absent terminal receipt yields `NEEDS_RECONCILIATION` rather than redispatch. Add tests that live cancellation never calls the background process-kill path.
- [x] Run `python -m unittest discover -s tests -p 'test_execution*.py' -v`; verify new tests fail before refactoring.
- [x] Extract only dispatch-specific logic into `BackgroundBackend`; leave locks, `_admit`, `_authorized`, budgets, input hashes, `workflow.begin_edit/finish_edit` and owner rules in the shared service. Define explicit backend recovery hooks instead of treating a live failure as an unchanged background input. Reject v1 runtime-pin mismatches as before.
- [x] Run the same focused suite and existing `scripts/qualify_execution.py` in a fresh output directory; require no behavior regression in either mode.
- [x] Commit only these files with `refactor: share managed execution across backends` after reviewing the diff against the pre-existing uncommitted overhaul.

### Task 2: Paired sessions, protocol 3 and explicit inspection coverage

**Files:** Create bridge `session.py`, `inspection.py`; modify bridge `__init__.py`, `blender_bridge.py`, `data/upstream.json`, `distribution.py`, `tests/test_distribution.py`; create `tests/test_live_protocol.py`.

**Interfaces:** Blender-side `session.describe() -> dict`, `session.bind(project: str, workspace: str) -> dict`, `session.invalidate(reason: str) -> None`; `inspection.inspect(query: dict) -> dict`, `inspection.fingerprint(scope: dict) -> dict`. Host `blender_bridge.call(command, payload, *, binding, timeout=2) -> dict` authenticates writes and never retries them. `binding` is resolved from a private local descriptor, not an MCP-returned token.

- [x] Add transport tests for missing/wrong token, two simultaneous clients, replayed preparation token, oversize request, secret redaction and v2 write rejection. Native fixture assertions must establish `generation_after_reload != generation_before_reload` even for the same filepath; object name collisions resolve only by stable ID. An unmeasured requested field must return `UNSUPPORTED_COVERAGE`, not a partial success.
- [x] Run `python -m unittest discover -s tests -p 'test_live_protocol.py' -v`; retain initial failures.
- [x] Implement session pairing with 256-bit random tokens, one paired project and one active job. Add only load lifecycle invalidation callbacks; all bpy inspection runs in the existing timer queue. Introduce versioned feature negotiation with required feature checks. Inspect paginated objects/materials/modifiers/nodes/assets/operator metadata and annotate measured coverage. Do not load discovered third-party modules just to inspect metadata.
- [x] Replace the hard-coded add-on export tuple with an explicit hash manifest, including every required support module and license. Keep reduced `upstream.py` untouched. Extend export tests to inspect all Python members for removed activity/telemetry code; qualify authorized local lifecycle callbacks separately. Run `test_live_protocol.py`, `test_distribution.py` and `test_mcp*.py`; require old observation paths to remain functional.
- [x] Commit `feat: pair live Blender sessions and inspect capabilities`.

### Task 3: Attach the actual live scene with recoverable baselines

**Files:** Create `live.py`, `tests/test_live.py`, `scripts/qualify_live.py`; modify `bootstrap.py`, `data/bridge/session.py`, `guidance.py`; reuse `adoption.py` and existing identity helpers.

**Interfaces:** `live.attach(root, binding, *, expected_parent: str | None, brief_file: str | None, mode: str | None) -> dict`; `live.refresh(root, binding, *, expected_parent: str) -> dict`; `session.save_copy(path: str) -> dict` returns content hash and original filepath. New-project attachment uses a fresh destination; existing-project attachment requires an explicit current parent. Metadata adoption and external-edit checkpoints have distinct provenance from generated edits.

- [x] Write tests/native fixtures for an untitled cube, a dirty saved scene, relative textures, missing/duplicate IDs, an empty scene, a linked read-only object, changed user data since the accepted checkpoint, and a crash between pre-copy and ID assignment. Assert original file hash and active filepath are unchanged, unsaved geometry exists in the reopened copy, retries never repeat ID assignment, and divergence produces an external-edit checkpoint or actionable refusal under policy.
- [x] Run `python -m unittest discover -s tests -p 'test_live.py' -v` and `python scripts/qualify_live.py --case attach --runtime . --blender BLENDER_PATH --out FRESH_DIRECTORY`; establish the failing behavior before implementation.
- [x] Save exclusive pre-adoption and baseline copies; reuse identity planning rather than inventing another ID scheme. Record source filepath, selected scene, session/generation and dependency resolution. Validate external edits against current scope and invalidate stage evidence. Do not use `is_dirty` as the equality check. Preserve incompatible linked content and explain unsupported coverage instead of making it local automatically.
- [x] Repeat focused and native attach checks. If Blender save-copy changes a required scene/filepath property, fix preservation before enabling live mutation; do not quietly switch the user into an owned worker.
- [x] Commit `feat: attach live scenes without overwriting artist files`.

### Task 4: Main-thread live jobs, verification and honest recovery

**Files:** Create bridge `jobs.py`, `operations.py`; extend `execution_backends.py`, `live.py`, `tests/test_live.py`, `tests/test_live_protocol.py`, `scripts/qualify_live.py`; modify `execution.py` reconciliation routing.

**Interfaces:** `LiveBackend` implements Task 1. Bridge `jobs.prepare(request) -> dict`, `submit(request, prepared) -> str`, `status(operation_id) -> dict`, `cancel(operation_id) -> dict`; `operations.resolve(recipe_id: str) -> Recipe` exposes `prepare`, `execute_step`, `verify_live`, `capture_scope`. `live.reconcile(root, operation_id, decision, expected_fingerprint) -> dict`, where decision is `keep-current` or `restore-precopy`.

- [x] Add `test_stale_preparation_mutates_nothing`, `test_lost_reply_is_status_only`, `test_mutation_then_exception_blocks_next_job`, `test_cancel_running_operator_does_not_claim_reverted`, `test_restore_archives_intervening_edits`, and `test_rejected_candidate_leaves_live_state_visible`. Inject edits/reload at a verification barrier: before-publication divergence must retain the candidate without publication; a change between publication and acknowledgment must set binding state `LIVE_DIVERGED` and refuse both the next operation and live stage completion. A subsequent prepare must compare against the accepted checkpoint. Native assertions cover transforms, material values, modifier settings and node-asset updates, plus duplicates and shared datablocks.
- [x] Run `test_live*.py` and the new `qualify_live.py --case jobs` against disposable GUI Blender; retain red results.
- [x] Implement the spec state machine and durable dispatch-before-invoke marker. Persist per-operation status under the bound project using exclusive writes and atomic replacement for status revisions. The main thread revalidates generation/token/fingerprint immediately before mutation. Restore temporary context; save a candidate; independently reopen/check/publish through Task 1. Implement the spec's pre-publication, post-publication and next-preparation alignment checks; binding divergence is distinct from a saved candidate's verification result. Reject unsupported modal recipes and busy contexts. Cancellation is cooperative; unknown outcomes block new edits. Recovery archives current state before any restore and never runs implicitly on a transport error.
- [x] Require portable replay/race tests and native failure/cancel/recovery fixtures to pass. Repeat a cancelled non-cooperative fixture until its eventual outcome is recorded without killing Blender; prove later user edits survive recovery refusal.
- [x] Commit `feat: execute and reconcile managed live Blender jobs`.

### Task 5: MCP/CLI access, previews and unchanged approval authority

**Files:** Modify `mcp_server.py`, `__main__.py`, `environment_workflow.py`, `guidance.py`, bridge `inspection.py`, `tests/test_mcp.py`, `tests/test_mcp_protocol.py`, `tests/test_environment_workflow.py`, `scripts/qualify_live.py`; add `docs/guides/LIVE_BLENDER.md` and link it from `COMBINED_MCP.md`.

**Interfaces:** MCP tools from the spec route to `live`/`execution`, never directly to a write operator. CLI routes `live-attach`, `live-refresh`, `live-execute`, `live-status`, `live-cancel`, `live-reconcile`, `live-preview` expose the same payload schemas. `live.preview(root, request: dict) -> dict` returns scene/frame/camera/color provenance and bounded image artifacts.

- [x] Add real-stdio tests asserting live edit publication, `AWAITING_APPROVAL` on gated submission, successor refusal and owner-import advancement through the existing owner fixture. Assert an agent cannot use a panel/status/preview request to approve or mutate another stage. Preview inputs must reject traversal, wrong session and excessive dimensions; before/after images must carry the same comparison settings.
- [x] Run `python -m unittest discover -s tests -p 'test_mcp*.py' -v` and the relevant environment tests; see new cases fail.
- [x] Add typed operation payloads, bounded JSON results and actionable errors. Present busy state, latest operation and recovery paths in the bridge panel; no approval button in this increment. Implement owned preview image lifetime/cleanup and label viewport versus render evidence. Update skills to discover session and target IDs before writing. Both modes retain the same technical validation.
- [x] Run real MCP through `qualify_live.py --case modes`: autonomous advances; gated pauses after visible edits; owner completion unlocks the next stage; manual edits invalidate stale review. Verify original artist-file bytes remain unchanged throughout.
- [x] Commit `feat: expose live workflows and visual feedback through MCP`.

### Task 6: Release proof for source and installed artifacts

**Files:** Modify `scripts/verify_release.py`, `scripts/qualify_mcp.py`, `scripts/README.md`, `pyproject.toml`, `dcc_harness/__init__.py`, `README.md`, `CHANGELOG.md`, `docs/BUILD_PLAN.md`, `docs/DESIGN_DECISIONS.md`; add `docs/archive/releases/LIVE_EXECUTION_RESULTS.md`.

- [ ] Add release assertions that the exported add-on imports with no source checkout/harness package on Blender's Python path; every manifest file/hash matches in wheel and source-archive rebuild; the token is absent from all delivered artifacts/logs. Regression tests must fail if a bridge module is missing.
- [ ] Run the new artifact tests against a deliberately incomplete temporary export; require failure, then the complete export; require success.
- [ ] Wire `qualify_live.py --case all` into the maintained release verifier. Qualify attach, edits, context failure, same-file reload, external edits, lost replies, restart, cancellation, restore refusal and both modes on owned native fixtures. Retain all evidence. Bump version to 0.22.0 only at this release boundary, including bridge metadata.
- [ ] Run `python scripts/verify_release.py --out FRESH_DIRECTORY --blender BLENDER_PATH`; require source/installed suites, current qualifiers and live qualifiers to pass. Run `git diff --check`. Review all changed runtime/authority paths and resolve actionable findings before reporting completion. Document unsupported operators and observation coverage rather than overstating generic support.
- [ ] Commit `release: qualify live Blender execution` with explicit file paths; mark P21 done with evidence. Do not push or change global registration as part of this planning request. Start P22 only after this gate passes.

## Handoff and Planning Checks

Use the existing development environment at `runs/overhaul/mcp-dev/Scripts/python.exe` until a fresh one is prepared. Replace `python` in commands with that path where necessary. All native output directories must be fresh. Never test mutations against the user's working scene.

The checkout already contains the uncommitted v0.20â€“0.21.1 overhaul. Before implementation, record its exact baseline and separate new changes in commits without discarding or accidentally attributing previous work. A branch-only commit is not GitHub delivery. The repo's eventual main-release convention does not authorize a push from this plan-only turn.

Self-review mapping: session/inspection Task 2; unsaved adoption Task 3; shared authority Tasks 1/5; scoped concurrency/recovery Task 4; visual evidence Task 5; artifacts/telemetry/compatibility Task 6. Completed checkboxes reflect the implementation ledger and retained qualification reports; remaining unchecked work is not claimed as complete.
