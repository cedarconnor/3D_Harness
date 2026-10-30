# Shader and Async Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Qualify standalone shader/material effects and asynchronous providers through the existing managed executor.

**Architecture:** Keep v1 intact and add explicit v2 effect selectors and submit/poll/cancel/collect contracts. Native graph measurements establish shader output; a durable cooperative state machine establishes async completion. Existing publication and independent reopen remain mandatory.

**Tech Stack:** Python 3.11+, unittest, Blender 5.1.1, existing MCP and packaging tooling.

**Spec:** [Approved design](../specs/2026-10-30-shader-async-capabilities-design.md).

## Global Constraints

- No dummy modifier for shader qualification; no automatic replay of submit or collect.
- Preserve v1 recipes, pinned projects, artist preferences and existing evidence.
- Live work returns to Blender between polls; no artist Blender termination.
- Only independently verified saved output can publish or satisfy a required capability.
- User approved implementation and native qualification on October 30, 2026; execute continuously.

## Review Focus

1. Shared nested group edits affect other materials/worlds and must be measured or refused.
2. Changed shader internals must invalidate evidence after reopen.
3. Crash or cancellation after dispatch must not replay mutation or publish uncertainty.
4. Timer-driven providers must actually progress while the GUI remains responsive.
5. v1 schema/bridge/package behavior must remain compatible.

### Task 1: Shader graph observation

**Files:** `dcc_harness/blender.py`, new `dcc_harness/shader_graph.py`, `tests/test_shader_graph.py`.
**Interfaces:** `graph(tree)` produces deterministic recursive graph records and explicit unsupported markers; old flat graph keys remain compatible. Shared users are evaluated during recipe execution.

- [x] Write and run failing graph tests for nested values, interfaces, settings, images, recursion and unsupported types.
- [x] Implement bounded, deterministic recursive shader observation with explicit coverage refusal.
- [x] Run graph tests and existing observation tests; retain native graph/reopen proof in Task 5.

### Task 2: Versioned recipe and native effect contracts

**Files:** `recipe_schema.py`, `data/capabilities/recipe.schema.json`, bridge `recipes.py`, `capability_projection.py`, `recipe_store.py`, `recipes.py`, tests.
**Interfaces:** v2 `effect={kind,material_id,slot,nodes}` selects material/shader effects (modifier uses kind only); v2 async `invocation` adds lifecycle callables and timing fields. `native_effect(..., recipe=None)` defaults to v1 modifier evidence.

- [x] Write and run failing tests for v1 compatibility, closed v2 contracts and false output attribution.
- [x] Implement effect-specific native evidence, owned naming, material/node shared-user policy, and scope preservation.
- [x] Extend immutable drafts/scaffolds and serialized schemas consistently.
- [x] Run recipe, capability and projection regression tests.

### Task 3: Durable async lifecycle

**Files:** new `dcc_harness/async_recipe.py`, `tests/test_async_recipe.py`.
**Interfaces:** `AsyncOperation(folder, invocation, callbacks, *, clock, cancelled)` owns `step()` transitions; callbacks are submit(), poll(handle), cancel(handle), collect(handle). `step()` returns a terminal result or pending status, with interval supplied by invocation. `drive()` is for owned background workers only.

- [x] Write and observe failing tests for success, failure, cancellation, deadlines, grace expiry, duplicate dispatch, corrupt/restarted state and collect uncertainty.
- [x] Persist intent before mutation, bounded JSON handles/results and atomic state history; never resume mutation automatically after restart.
- [x] Run the complete portable async test module.

### Task 4: Cooperative native integration

**Files:** bridge `recipes.py`, `jobs.py`, `addons.py`, `_capability_blender.py`, `_recipe_blender.py`, `distribution.py`, qualification fixtures.
**Interfaces:** recipe execution exposes start/step/finalize for async jobs and synchronous apply remains unchanged. Live Jobs retains one reservation and schedules one step per timer callback; background worker drives only context-compatible providers.

- [x] Add failing integration tests for pending jobs, duplicate submit/collect, preserved scopes, preference restoration and publication refusal.
- [x] Integrate source-pinned lifecycle callbacks, native effect validation and terminal cleanup.
- [x] Extend bridge manifest exports; route async qualification through an owned GUI event loop where required.
- [x] Run portable integration and existing job/capability suites.

### Task 5: Native qualification, review and delivery proof

**Files:** new `scripts/qualify_shader_async.py`, fixture provider/adapter, results document, README, ADDON_RECIPES guide.
**Interfaces:** CLI `python scripts/qualify_shader_async.py --blender PATH --out FRESH_DIR` retains owned fixture artifacts and a machine-readable report.

- [x] Qualify standalone material and nested shader apply/repeat/update/save/reopen/render, shared-scope refusal and stale/deleted effect behavior.
- [x] Qualify async background/live completion, live timer responsiveness, cancel/fail/timeout/uncertain termination and no replay.
- [x] Run complete source suite and relevant existing native capability qualifiers.
- [x] Build wheel/sdist/rebuilt wheel; run installed suite and standalone bridge/package parity checks.
- [x] Dispatch independent whole-change review, fix actionable findings with regression tests, rerun affected native tests.
- [x] Document observed results and limitations, update active guides, and report exact verification results.

Execution ledger: `.superpowers/sdd/2026-10-30-shader-async-capabilities/progress.md`.
