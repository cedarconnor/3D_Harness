# External branch review remediation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Verify every supplied review finding, fix confirmed defects, and qualify the corrected combined harness without weakening preservation or owner authority.

**Architecture:** Retain one managed execution service and explicit live state transitions. Fix lifecycle and evidence contracts at their shared boundaries; do not solve availability problems by replaying uncertain writes or ignoring unmeasured changes. Each review ID receives a confirmed/fixed, narrowed, unsupported, or intentional-boundary disposition with evidence.

**Tech Stack:** Python 3.11+, pinned MCP 1.26.0, Blender 5.1.1 on Windows, unittest, wheel/sdist.

**Spec:** User-authorized verification and fixes for [the supplied external review](../../reference/BRANCH_REVIEW_2026-10-22.md), interpreted against the [approved design](../specs/2026-10-22-live-blender-capabilities-design.md).

## Global Constraints

- Work on `codex/managed-execution-overhaul`, preserving existing edits and evidence. Base: `188e7d55ffc26445240b480aa790e4541f9d09a4`. The owner subsequently authorized commit/push/merge after completion on October 23; the controller handles independent review and delivery. No global registration. The owner confirmed no known Blender 5.1 preference backup and instructed leaving real preferences untouched.
- No telemetry or activity recording. No third-party purchases, installs or network calls during provider execution.
- Native tests use only owned disposable Blender scenes and configurations; never modify the artist's open scene.
- Never retry an ambiguous native mutation. Durable proof may resolve a lost response without redispatch.
- Neither run mode nor agent authority may weaken an artist-bound stage or capability policy.
- Source/runtime pins remain enforced. Freeze runtime before final native qualification; changed runtime invalidates previous proof.
- Every behavior fix has a failing-before/passing-after regression. Do not broaden accepted scene coverage without measured preservation evidence.
- Python environment: `runs/overhaul/mcp-dev/Scripts/python.exe`; Blender: `C:/Program Files/Blender Foundation/Blender 5.1/blender.exe`.

## Review Focus

1. Explicit artist stage policies in autonomous runs must still wait for the owner (Task 1).
2. Cancellation, expired budgets and partial publication must be recoverable without duplicate edits or lost capability receipts (Task 1).
3. Slow saves, refusals and crashed sessions must retain a truthful, recoverable live state (Task 2).
4. Rotated targets, unrelated scene data and non-harness-shaped providers must have truthful measurement and invocation contracts (Task 3).
5. Installed package behavior, rule pins and documentation must agree; synthetic qualification is not general product proof (Tasks 4-5).

### Task 1: Execution authority and durable outcomes

**Files:** `dcc_harness/environment_workflow.py`, `execution.py`, `mcp_server.py`, `workflow.py`, `revisions.py`, `bootstrap.py`, `__main__.py`; capability receipt construction in `capabilities.py`; new `tests/test_review_execution.py` and related existing tests. Native script changes only when required by corrected semantics.
**Review IDs:** A1-A3; B1-B8, B10, B12. Assess each claim before fixing.
**Interfaces:** Preserve existing public execution shapes. Add operation-level cancellation used by MCP transport teardown, distinct from `run-cancel`. Build and validate capability publication evidence before commit and complete receipt persistence during reconciliation. Explicit reconciliation may finish an already verified candidate after time expiry; no new native dispatch. Managed external revisions must use the same authority/publication boundary.

- [x] Reproduce artist-required override, cancel/expired submission, transport cancellation stranding a run, runtime-mismatched reconcile, and interrupted capability receipt publication in focused tests.
- [x] Preserve stricter stage policy; return `AWAITING_APPROVAL` for artist-required stages in either mode. Reject new submissions after cancel/deadline while permitting idempotent reads of completed submissions.
- [x] Separate operation cancellation from terminal run cancellation. Surface unresolved operations ahead of terminal cancellation; make configuration/unknown-operation errors explicit and creation atomic. Remove only owned failed staging data or make retained staging diagnosable if safe cleanup is unavailable.
- [x] Validate capability evidence and current policy under publication lock before committing; recover receipts after interrupted publication. Reconciliation checks runtime and never executes a script.
- [x] Return structured CLI failure outcomes over MCP. Route deliberate managed external revision acceptance through explicit managed admission. Make rules binding retries recover the same complete export and validate capability payloads before dereference.
- [x] Run focused tests RED then GREEN, the full portable suite once, self-review and commit. Record exact evidence/dispositions in the task report.

### Task 2: Live transport and recovery

**Files:** `dcc_harness/blender_bridge.py`, `live.py`, `live_recovery.py`, `live_surface.py`, `execution_backends.py`; `dcc_harness/data/bridge/{__init__,attachment,session,jobs,recovery,inspection}.py`; new `tests/test_review_live.py`; owned native qualification cases/scripts.
**Review IDs:** C1-C9. C9 is a trust-boundary claim requiring precise documentation, not a hostile-same-user sandbox.
**Interfaces:** Explicit transport errors distinguish durable pre-mutation refusal from unknown outcome. Use command-appropriate bounded deadlines. Host recovery consumes durable matching refusal/result evidence after lost responses without retrying mutation. Preserve Task 1 operation cancellation and receipt guards.

- [x] Reproduce slow requests, failed attach preflight, crashed descriptors, prepare refusal, nonfinite serialization, missing recovery inputs and repeated divergence checks using focused protocol/state tests.
- [x] Give saves/snapshots appropriate bounded deadlines independent of handshakes; keep late results inspectable. Serialize errors explicitly. Retain durable refusal/result evidence with exact request identity before allowing another intent.
- [x] Use non-reloading image path assignment, release only definitively unused session reservations, and allow safe retry after confirmed pre-mutation refusal. Detect stale/crashed descriptors without treating a slow live process as dead.
- [x] Deduplicate identical divergence evidence. Keep unknown outcomes unresolved and expose actionable status rather than replay.
- [x] Add owned native cases with deliberate delay, nontrivial populated/textured scenes, attach/prepare refusal and crash-style reconnect. Run focused RED/GREEN and full portable suite; commit. Final integrated native gate occurs after all runtime changes.

### Task 3: Add-on measurement, freshness and real API contracts

**Files:** `dcc_harness/capabilities.py`, `recipes.py`, `recipe_schema.py`, `provider_sources.py`, `environments.py`, `_recipe_blender.py`, related schemas; `data/bridge/{recipes,addons}.py`; new `tests/test_review_capabilities.py`, fixtures and qualification scripts.
**Review IDs:** D1-D11 and B11.
**Interfaces:** Keep publication/receipt interfaces established in Task 1. Use a shared canonical host/native measurement projection. Separate declared dependency/output freshness from benchmark selection metadata. Adapt an unchanged provider API with no harness effect-ID signature. Preserve explicit scope and ownership rather than accepting arbitrary unsupported state.

- [x] Reproduce out-of-dependency invalidation, rotation/material-user projection mismatch, stale-registration ordering, inventory cleanup/profile races and provider-call-with-no-effect receipts.
- [x] Fix freshness/projection defects while retaining output-change detection. Scope capability measurement to required targets/dependencies where preservation remains measured; explicitly refuse unsupported surrounding state when whole-scene publication cannot safely preserve it, and document that distinction.
- [x] Prove the declared provider invocation contributes the effect; no-op provider calls plus unrelated adapter work must not satisfy required use. Support explicit validated invocation argument mapping for ordinary provider APIs or truthfully restrict/remove unsupported API claims.
- [x] Verify preference persistence natively in isolated GUI configuration and restore session-only activation changes. Require explicit local review/allowlisting for unknown-network providers, keeping required-network/license refusal.
- [x] Establish a native positive timing selection on comparable inputs measuring provider execution, or remove unavailable ranking claims/action until supported. Avoid unsafe stale caches; eliminate redundant validation within one read operation if useful without weakening byte checks.
- [x] Add ordinary-provider, rotated/multiscene, no-op deception and preference-lifecycle fixtures. Run focused RED/GREEN and full portable suite; commit with per-ID dispositions.

### Task 4: Packaging, documentation and continuous checks

**Files:** `dcc_harness/distribution.py`, packaging tests; `README.md`, guides, `docs/BUILD_PLAN.md`, release review report; `.github/workflows/`.
**Review IDs:** A4, B9, B13, C9, E and F, plus documentation consequences of Tasks 1-3.
**Interfaces:** Rules closure must retain executable examples when referenced; do not remove useful source links merely to avoid source pinning. Distinguish immutable pinned runtime/rules from mutable checkout development.

- [x] Verify rule-closure behavior and choose an evidence-backed fix or explicit intentional pinning disposition. Clarify MCP dependency and executable registration versus user-client registration; document owner console injection/trusted-local boundary.
- [x] Correct stale tracker entries and damaged text; simplify touched logic where it helps review, without broad style-only rewriting.
- [x] Add CI that installs the pinned project dependency set and runs portable tests/package checks; native proof remains local Windows/Blender qualification. Add tests for material claimed gaps, not implementation-mirroring coverage.
- [x] Record every external finding and its evidence/status in `docs/archive/releases/EXTERNAL_REVIEW_0_23_RESULTS.md`. Validate links and relevant distribution tests, commit.

Completed task checkboxes record the implemented/evidence-backed dispositions, including removed unavailable timing selection. They do not resolve the historical real-preferences incident or qualify arbitrary providers/artist scenes.

### Task 5: Integrated qualification and delivery

**Files:** release scripts/evidence, review report and README counts as needed. No runtime changes while native qualification runs.
**Interfaces:** All corrected source, wheel, sdist and standalone bridge bytes must agree; final doc-only rebuild may differ only in the rules bundle.

- [x] Run the full source/clean-installed release gate, all maintained native checks and new focused fixtures against the installed runtime. Preserve each failed run before starting a fresh output directory.
- [ ] Run fresh whole-branch review under the development skill, adjudicate material findings and verify each fix. Do not claim approval for untested commercial products or artist scenes.
- [x] Refresh documentation counts/evidence, build final package and prove runtime/bridge equality. Commit, verify clean tree and report remaining explicit limitations. Preserve all evidence; do not retry previously blocked deletion of an unrelated workspace.
