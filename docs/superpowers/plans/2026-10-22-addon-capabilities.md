# Reusable Blender Add-on Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Discover future add-ons, qualify reusable recipes, select appropriate providers and enforce preferred/required use throughout managed builds and revisions.

**Architecture:** Keep a local capability registry and immutable environment profiles above P21's shared execution service. The calling agent drafts semantic recipes; deterministic validation, isolated qualification, provider resolution and checkpoint-bound receipts make those recipes usable and enforceable. Live and background execution use the same policy and evidence contracts.

**Tech Stack:** Python 3.11+, standard library, existing JSON Schema dependency through MCP 1.26.0, Blender 5.1.1, unittest. Declare JSON Schema directly if production code imports it; pin a version compatible with the qualified SDK environment rather than relying on an undeclared transitive dependency.

**Spec:** [Live Blender capabilities design](../specs/2026-10-22-live-blender-capabilities-design.md), P22. Dependency: [P21 live execution](2026-10-22-live-blender-execution.md) must pass release qualification before implementation is enabled for live scenes.

## Global Constraints

- Python 3.11+, MCP SDK 1.26.0, Blender 5.1.1 on Windows are the initial qualification targets.
- One managed execution service owns admission, operation identity, budgets, verification and publication for background and live backends.
- Unknown mutation outcomes are never automatically replayed; live Blender is never killed to enforce a deadline.
- No telemetry, user-activity recording, tracking URLs or automatic external network calls are introduced.
- Artist approval remains in the existing owner terminal/review-import path; MCP cannot approve its own stage.
- Source and installed-wheel tests, source-archive parity and owned native positive/negative fixtures are required for each increment.
- Existing runtime-pinned projects retain their installed runtime; no silent project migration.

## Review Focus

1. An add-on can be installed but disabled, shadowed, incompatible or changed without a version bump (Tasks 1–2).
2. An operator may return `FINISHED` without the intended effect, mutate before raising, or require a real viewport (Task 3).
3. A required provider can be bypassed by a direct script, a stale receipt or a text claim unless completion checks actual outputs (Tasks 4–5).
4. Repeated revisions can stack duplicate effects or alter every user of a shared material (Tasks 3–5).
5. The live result can depend on a provider absent from the verifier, or on secrets/network access unavailable offline (Tasks 1–3, 6).

## File Structure and Contract

| Files | Responsibility |
| --- | --- |
| new `dcc_harness/environments.py`, bridge `addons.py` | Inventory and pinned live/worker/observer environments |
| new `dcc_harness/recipes.py`, bridge `recipes.py` | Schema validation, retained adapters, isolated qualification and invocation |
| new `dcc_harness/capabilities.py` | Registry, deterministic resolution, requirement/freshness receipts |
| new `dcc_harness/data/capabilities/{recipe,profile,policy,receipt}.schema.json` | Explicit serialized schemas with versioned validators |
| `execution.py`, `execution_backends.py`, `live.py`, `native.py`, `_execution_blender.py`, `_observe_blender.py` | Apply profiles and record verified capability use through shared execution |
| `environment_workflow.py`, `guidance.py`, `mcp_server.py`, `__main__.py` | Stage enforcement and public discovery/onboarding/use commands |
| new `tests/test_environments.py`, `test_recipes.py`, `test_capabilities.py`, `tests/fixtures/addons/` | Portable contracts and synthetic providers |
| new `scripts/qualify_capabilities.py`; existing release tooling | Owned native onboarding/routing/revision proof |

Schemas reject unknown keys and require the fields in the design. Use registry state under `PROJECT/capabilities/`, with immutable recipe/profile/policy versions and qualification artifacts. No editing qualified files in place. `Profile` holds `schema=dcc.environment.profile.v1`, Blender compatibility, provider IDs/module paths/source digests, asset digests and whitelisted non-secret preferences; local secret references remain out of exported evidence. `Recipe` uses `dcc.capability.recipe.v1` and includes a parameter JSON Schema plus explicit input/output coverage.

`Requirement`: capability ID, target IDs, effect slot, policy version/hash, lifecycle stage, compatible provider constraints and dependency fingerprint. `Resolution`: `RESOLVED`, `UNAVAILABLE`, `UNQUALIFIED`, `UNSUPPORTED_CONTEXT` or `NO_COMPARABLE_EVIDENCE`, selected provider/recipe hashes when available and a reason. `CapabilityReceipt` uses `dcc.capability.receipt.v1` and binds requirement, operation UUID, provider/recipe/profile/policy hashes, actual output fingerprint, validation artifact hashes and published checkpoint. A pending live job cannot produce a completion-valid receipt.

### Task 1: Inventory actual environments and freeze profiles

**Files:** Create `environments.py`, bridge `addons.py`, `profile.schema.json`, `tests/test_environments.py`, synthetic fixtures in `tests/fixtures/addons/`; modify `native.py`, `_execution_blender.py`, `_observe_blender.py`, P21 bridge/export manifest and `execution_backends.py`.

**Interfaces:** `environments.inventory(binding: dict | None, *, blender: str) -> dict`; `create_profile(root, inventory: dict, selected: list[str], preferences: dict) -> dict`; `validate_profile(profile: dict, inventory: dict) -> dict`. Bridge `addons.inventory() -> dict`, `addons.enable_profile(profile: dict) -> dict` checks sources before activation. Background workers receive an explicit profile path/hash; existing requests with no profile remain unchanged.

- [x] Add tests asserting distinct installed/enabled/compatible states; exact source-hash invalidation despite unchanged version; ambiguous provider ownership remains unknown; disabled add-ons are not imported during inventory; secrets are redacted. Synthetic fixtures must include a legacy module, an extension manifest, a conflicting module name and a provider requiring unavailable network/license configuration. Assert `validate_profile` fails on changed bytes or missing required dependencies.
- [x] Run `python -m unittest discover -s tests -p 'test_environments.py' -v` and retain red results.
- [x] Read filesystem/extension metadata and registered operator metadata separately. Profile only explicitly selected local providers; do not auto-install/download/update. Activate matching profile modules in isolated workers and independent observers before loading/evaluating the candidate. Live activation records the enabled-state delta without persisting global preferences. A missing GUI-only verifier environment yields an explicit verification failure, not a pass from the factory worker.
- [x] Run portable tests and a native profile fixture proving the desktop-enabled provider is absent in factory mode, becomes available under the profile, and is also present in the independent verifier. Inspect reports for secret leakage and record any declared unsupported dependencies.
- [x] Commit `feat: inventory and pin Blender add-on environments`.

### Task 2: Recipe contracts, local registry and draft onboarding

**Files:** Create `recipes.py`, bridge `recipes.py`, `recipe.schema.json`, `tests/test_recipes.py`; extend `distribution.py`/package-data declarations; create `docs/guides/ADDON_RECIPES.md`.

**Interfaces:** `recipes.validate(value: dict) -> dict`; `draft(root, value: dict, adapter_path: str, assets: list[str]) -> dict`; `load(root, recipe_id: str, digest: str) -> dict`. Invocation kinds are `python_function`, `operator`, `node_asset`. Adapter protocol: `preflight(context, parameters) -> dict`, `apply(context, parameters, effect_id) -> dict`, `inspect_output(context, effect_id) -> dict`, `verify_saved(observation, output) -> dict`. Qualification status is separate from draft content.

- [x] Write schema/registry tests for path traversal, arbitrary import during discovery, wrong parameter type, non-finite values, missing validators, altered assets and duplicate recipe IDs with different content. Assert a valid draft is `DRAFT`, cannot execute as qualified, and inspecting it never calls adapter code. Use explicitly versioned immutable storage; loading a tampered adapter fails on its digest.
- [x] Run `python -m unittest discover -s tests -p 'test_recipes.py' -v`; require the expected failures before adding the API.
- [x] Implement validation and exclusive local retention with source/asset hashes. Provide a generated recipe scaffold and inventory/operator documentation to the calling agent, not a hidden model in the server. Resolve adapter paths only from retained qualified bundles. Package the schema and built-in support runtime into both wheel and exported bridge; user provider binaries/licenses remain external.
- [x] Run recipe and distribution tests, including a source-archive rebuild. Confirm the guide covers semantic intent, parameter bounds, poll/context, effect identity, dependency scope, output validation, offline behavior and version-change requalification.
- [x] Commit `feat: define versioned add-on recipes and onboarding drafts`.

### Task 3: Qualify invocation, context and actual results

**Files:** Extend `recipes.py`, bridge `recipes.py`/`operations.py`, `tests/test_recipes.py`; create `scripts/qualify_capabilities.py` and fixtures for a function provider, a viewport-only operator, a node asset and two providers for one capability.

**Interfaces:** `recipes.qualify(root, recipe_id, recipe_digest, profile_digest, *, blender, out) -> dict`; `register_qualified(root, report_path: str) -> dict`. Qualification binds recipe/provider/profile/Blender hashes and includes independent saved-output validation. Registry states are `DRAFT`, `QUALIFIED`, `FAILED`, `STALE`; content changes cannot inherit `QUALIFIED`.

- [x] Add positive function/operator/node-asset cases and negative `FINISHED`-without-effect, poll failure, missing viewport, modal-without-completion, mutation-before-error, shared-material and missing-dependency-on-reopen cases. Assert wrong context fails preflight before mutation, unchanged output fails qualification, and source changes set `STALE`. A repeated effect application must update the original effect ID with `effect_count == 1`.
- [x] Run portable recipe tests and `python scripts/qualify_capabilities.py --case onboarding --runtime . --blender BLENDER_PATH --out FRESH_DIRECTORY`; retain failures.
- [x] Execute only in owned disposable scenes during qualification. Use P21 context handling and cooperative job semantics; explicitly reject unsupported modal completion. Compare provider outputs after independent reopen under the pinned environment. Capture fixed-view previews, elapsed time, settings and failures locally. Audit outbound connections in offline fixtures; quarantine network-requiring/unreviewed providers under the default offline policy. Do not infer artistic superiority from technical pass status.
- [x] Require all expected positives and negatives to pass, including restoration of temporary context and persistence of effect IDs after reopen. Test live GUI and headless invocation separately; qualification for one does not imply qualification for the other.
- [x] Commit `feat: qualify add-on recipes against native Blender results`.

### Task 4: Resolve semantic requirements and enforce provider policy

**Files:** Create `capabilities.py`, `policy.schema.json`, `receipt.schema.json`, `tests/test_capabilities.py`; modify `execution.py`, `environment_workflow.py`, `guidance.py`, `tests/test_environment_workflow.py`.

**Interfaces:** `capabilities.resolve(root, requirement: dict, inventory: dict) -> dict`; `execute(root, requirement: dict, resolution: dict, parameters: dict, operation_id: str) -> dict`; `verify_receipts(root, stage_id: str, checkpoint: dict) -> dict`. Capability execution routes through `execution.execute_operation`; no second journal, budget or publication path. Freeze requirement/policy/profile hashes into the operation request.

- [x] Add tests for `prefer` with permitted versus forbidden fallback; `require` unavailable/unqualified/incompatible; `best_qualified` with comparable measurements, deterministic tie and no comparable evidence. Assert a stage with a required provider cannot complete using a manual script, a textual usage claim, another target's receipt, a stale checkpoint or an edited provider source. Both modes must enforce this before any completion receipt is written.
- [x] Run `python -m unittest discover -s tests -p 'test_capabilities.py' -v` and `test_environment_workflow.py`; retain initial failures.
- [x] Implement deterministic selection, rejecting providers without applicable qualification. Store receipts only after actual execution, saved-output validation and publication. Revalidate live binding alignment before submitting a live stage. Validate receipt references against service-owned operation evidence and current output/dependency fingerprints; inherited output may satisfy a requirement only while the same declared dependencies and effect remain valid. Rebinding policy is a versioned event that invalidates affected requirements, never an in-place edit to an approved stage.
- [x] Run the focused tests plus native two-provider selection. Demonstrate a different compatible winner when the chosen engine/target changes, and no false best-quality claim when evidence is absent. Existing projects without capability policy must preserve current behavior.
- [x] Commit `feat: enforce preferred and required Blender capabilities`.

### Task 5: Trigger capability checks at lifecycle boundaries without duplication

**Files:** Extend `capabilities.py`, `live.py`, `guidance.py`, `environment_workflow.py`, bridge `recipes.py`, tests for capabilities/environment/live; update `.agents/skills/dcc-harness/SKILL.md`, `dcc-build-revise/SKILL.md`, `dcc-materials/SKILL.md`.

**Interfaces:** `capabilities.requirements(root, stage_id: str, observation: dict) -> list[dict]`; `changes(root, before: dict, after: dict) -> list[dict]`; `effect_key(capability: str, target_id: str, slot: str) -> str`. A stable effect key identifies the owned modifier/node group/material binding; dependency fingerprints determine whether to reuse or update it.

- [x] Test object enrollment, relevant stage entry, geometry/material/profile/recipe change, deleted effect, irrelevant object change and repeated identical requests. Assert a fresh matching result schedules zero new jobs, a relevant change schedules one update using the same effect key, and unrelated changes do not force needless reapplication. An explicitly different slot may create a second effect. Shared materials must respect all-user scope or an explicit single-user-copy policy.
- [x] Run capability/environment/live tests and `qualify_capabilities.py --case revisions`; verify new cases fail before adding triggers.
- [x] Compute requirement freshness at managed boundaries and after refresh of external user edits. Expose missing/stale requirements through `next` and stage evidence; the agent schedules the resolved jobs within normal budgets. No background keystroke/operator watcher and no infinite auto-repair loop. Required failure blocks completion; allowed fallback records why. Preserve explicit artistic intent—do not add wear merely because a mesh or compatible add-on exists.
- [x] Require a native sequence of initial apply, same-input repeat, geometry revision, provider source change and effect deletion to produce the expected single effect/update or requalification stop. Include source-shared material users and reloaded scenes.
- [x] Commit `feat: keep add-on effects current across managed revisions`.

### Task 6: Public onboarding tools, documentation and release qualification

**Files:** Modify `mcp_server.py`, `__main__.py`, `distribution.py`, `pyproject.toml`, `dcc_harness/__init__.py`, `tests/test_mcp.py`, `tests/test_mcp_protocol.py`, `tests/test_distribution.py`, `scripts/verify_release.py`, `scripts/README.md`, `README.md`, `CHANGELOG.md`, `docs/BUILD_PLAN.md`, `docs/DESIGN_DECISIONS.md`, `docs/guides/COMBINED_MCP.md`; add `docs/archive/releases/ADDON_CAPABILITIES_RESULTS.md`.

**Interfaces:** MCP `blender_capabilities(action, payload)` supports `inventory`, `resolve`, `requirements`; `blender_recipe(action, payload)` supports `draft`, `inspect`, `qualify`, `register`. Execution/status/cancel use the existing P21 tools and stable operation UUIDs. Add CLI `capability-*` and `recipe-*` routes to the same service APIs. Draft/qualification results are explicitly labeled and never masquerade as executed project edits.

- [ ] Add real-stdio onboarding and policy tests. Discover a fixture provider, retain a draft, qualify/register it, resolve an explicit intent, execute directly in an owned open scene and complete only with valid evidence. Repeat for background mode. Assert required-provider failure blocks autonomous completion and gated approval cannot bless missing technical evidence; agent approval remains refused.
- [ ] Run MCP/distribution tests; retain the initial failures for these new routes. Build an incomplete export missing the recipe runtime to establish the packaging failure test.
- [ ] Implement the public surface, capability-aware skill routing and complete examples using synthetic providers. Add the fixture-only native qualifier to the release command. Package schemas and support modules using explicit recursive file manifests and hashes. Bump to 0.23.0 at release; update any bridge feature revisions required by the final protocol. Explain how user-installed paid or private add-ons are registered without bundling them.
- [ ] Run `python scripts/verify_release.py --out FRESH_DIRECTORY --blender BLENDER_PATH`; require full source/installed suites, wheel/source-archive parity, prior native gates and `qualify_capabilities.py --case all`. Recheck the no-telemetry code scan, offline fixture audit and absence of credentials. Run `git diff --check`, review cross-feature contracts and fix material findings.
- [ ] Commit `release: qualify reusable Blender add-on capabilities`; mark P22 done with exact evidence. State that fixture onboarding is proven and real third-party products require their own recipe qualification; do not claim universal compatibility or superior visual results.

## Handoff and Planning Checks

Use a fresh copy of the P21-qualified runtime and owned fixture scenes for native work. Preserve the existing uncommitted overhaul and all qualification evidence; do not overwrite source scenes or silently migrate earlier run pins. Commit commands must stage only the exact task files after checking the diff. A plan does not authorize publishing to GitHub or purchasing/installing third-party products.

Self-review mapping: discovery/environment Task 1; agent-assisted recipe creation Task 2; dependable invocation and quality evidence Task 3; mandatory use and mode compatibility Task 4; continuous applicability/revision Task 5; one-package delivery and end-to-end proof Task 6. The open-scene requirement is exercised throughout through P21's backend, not replaced by a separate production session. These tests are planned, not yet executed.
