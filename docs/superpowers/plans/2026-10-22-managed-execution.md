# Managed execution and adversarial fixes implementation plan

> Execute inline with regression tests and a fresh final code review. The user has authorized implementation of the reviewed design; no additional plan approval is needed.

**Goal:** Fix F1–F6 and provide one durable execution service for autonomous and approval-gated development before integrating MCP.

**Architecture:** Preserve immutable native checkpoints and coordination receipts. Derive current readiness from current evidence. Add a managed controller above these primitives, owning admission, bounded native processes, operation identity and recovery. Existing advisory projects remain readable.

**Tech stack:** Python 3.11+, standard library, Blender background workers, unittest.

**Spec:** `docs/reference/ADVERSARIAL_PACKAGE_REVIEW_2026-10-22.md` and the user's implementation instruction.

## Constraints and decisions

- Preserve existing diagnostics and source scenes; operate on fresh owned outputs.
- Human approval remains attributable and bound to a specific submitted checkpoint. Autonomous mode may use agent review but cannot label it artist acceptance.
- A dispatched operation with an unknown outcome is never automatically dispatched again.
- Ruling: explicitly reject non-unit-scale GLB export until conversion is qualified; this is the review's allowed conservative fix and prevents false certification.
- Ruling: work on `codex/managed-execution-overhaul` in the current checkout; preserve the user's review artifact. No push or installation into user configuration.

## Tasks

### 1. Validation and units (F1, F4, F5)
- [x] Add red regressions for malformed measured/spec vectors, scale rejection, and native metric support distances.
- [x] Centralize finite numeric/vector validation in `evidence.py`; reject unsupported export scale in `_delivery_blender.py`; convert relation footprint/reach/distances using scene scale.
- [x] Run focused portable and native checks; verify source hashes unchanged.

### 2. Current readiness and recoverable review import (F2, F3)
- [x] Add regressions for relevant/irrelevant checkpoint changes and downstream invalidation; invalid import first/last note, corrected retry and interruption after approval.
- [x] Make `environment_workflow.stages(events, native=None)` derive current validity and use it in admission/summary. Preflight review imports and retain stable per-page/per-item request identities for retry.
- [x] Run environment, feedback and review tests.

### 3. Native adoption qualification (F6)
- [x] Replace stale unsupported fixture with a genuinely unsupported construct; add positive collection-instance adoption.
- [x] Run maintained adoption qualification in a fresh directory.

### 4. Shared managed execution
- [x] Add `execution.py` service with create/status/execute/cancel/reconcile APIs and CLI routes. Explicit run mode, stage identity, operation UUID, pinned request, operation/time budgets, owned background processes, durable state and cancellation.
- [x] Enforce predecessor approval in both modes; require owner stage completion in gated mode. Prevent legacy mutation paths from bypassing managed admission. Reuse observation, contract validation, checkpoint publication and coordination functions.
- [x] Test end-to-end portable admission, idempotency, stale candidates, timeout, cancellation, process failure and restart ambiguity; qualify both modes with real Blender.

### 5. Release verification
- [x] Update current docs and version; provide a maintained verification entry point.
- [x] Run full source suite, wheel build, installed-runtime suite, native adoption/units/managed workflow qualification.
- [x] Fresh review, address material findings, record evidence and remaining limits. Only then assess MCP integration readiness.

## Review focus

Concurrent clients, edited scripts after reservation, interruption between native save and publication, stale human approvals, and replay with altered request content must fail closed without erasing evidence or repeating mutations.

## Progress

Implementation starting from 0b8c30c; baseline 437 tests run, two symlink skips. Review evidence retained under `runs/adversarial-review-2026-10-22`.

- Tasks 1–3 implemented. Malformed vectors, partial imports and stage invalidation were reproduced with red regressions; focused tests pass. Native units: six scale/gap cases pass. Native adoption passes both supported collection instancing and unsupported vertex instancing.
- Task 4 implemented. Owned execution, policies, direct-writer guards, budgets, cancellation, explicit reconciliation and automatic agent stage submission share the service. Portable controller-death and concurrency tests pass. Two basic native modes passed; expanded timeout/cancel qualification is queued for the installed artifact.
- Fresh independent reviewer found five issues: own-stage admission race, missing bound-material dependencies, inherited evidence freshness, stale submission replay after reopen, and a missing journal-operation pointer after interrupted reservation. All have failing regression reproductions and fixes; focused execution/environment suites pass.
- Ruling: preserve immutable file stores and explicit inspection stops for corrupted/partial checkpoint bundles and crash-retained metadata locks; do not invent automatic deletion/replay recovery. Cost: those exceptional cases need inspection rather than automatic continuation.
- Ruling: the agent remains the reasoning backend. The service executes scripts and enforces workflow policy; bundling an LLM client is outside this increment. Cost: autonomous operation needs a cooperating agent client.
- Release verification is in progress. Earlier full runs caught malformed old synthetic observations (fixed) and one exact-runtime-stamp race caused by editing source while its tests were running. Final runtime verification must use a stable tree.

Final verification: all release gates passed. Source and installed suites each ran 467 tests with two symlink skips; installed native units, adoption, both modes, timeout/cancel passed. Runtime source and wheel files are byte-identical. See docs/reference/MANAGED_EXECUTION_VERIFICATION_2026-10-22.md. MCP integration has not started.
