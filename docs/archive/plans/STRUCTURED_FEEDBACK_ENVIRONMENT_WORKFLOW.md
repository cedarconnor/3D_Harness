# Structured feedback and environment workflow implementation plan

Date: October 6, 2026. Status at authoring: **planned; not implemented**.

Implementation update: the user subsequently approved this plan. Version 0.5.0 implements the bounded runtime in [usage](../../guides/STRUCTURED_FEEDBACK.md); see [qualification and deviations](../releases/FEEDBACK_0_5_0_RESULTS.md). The original proposal and draft examples below remain the design record, not current CLI payload documentation.

Requested outcome: make review feedback survive long sessions and give the existing environment skills a small, repeatable workflow. Keep the normal Claude, Codex or Cursor chat as the entry point. This document and its draft JSON examples are the deliverable for the planning request; they do not add runtime commands or change a native scene.

Baseline inspected: version 0.4.10, commit `7d80939a7beabc4895c53355c5929f499fcc69bd`, branch `codex/manual-revision`. Follow the [active build plan](../../BUILD_PLAN.md) and [design decisions](../../DESIGN_DECISIONS.md). Existing artistic-quality and repair-effort qualification gaps remain open.

## Outcome and scope

An artist or agent records a specific issue against a saved checkpoint and, where useful, a stable object/material ID and rendered view. A fresh session sees that issue without reading the previous conversation. A revision records what changed, what remains unresolved and evidence of the result. A small environment workflow selects the relevant skills and deliverables for the current stage.

First release includes:

- Structured feedback with persistent IDs, immutable history and explicit response/verification records.
- One versioned environment workflow, pinned to the project with its relevant skill files.
- File/CLI entry points and compact additions to `resume` and `review`.
- Explicit technical completion, agent visual review and artist acceptance as separate facts.
- An owned Blender exercise proving continuation, preservation and unresolved-note handling.

Defer the annotation web UI, background scheduler, new MCP server, render queue, client installers, global taste learning, motion execution and Unreal adapters. The metadata can reserve optional frame anchors, but this release makes no animation-quality claim. Implement the patterns independently; no Mortiflix code or skill text is to be copied into this increment.

## Existing components to reuse

| Existing component | Integration |
|---|---|
| `Continuity.status()` and immutable checkpoint manifests | Verify the native history and use `active.id` as checkpoint identity; retain the separate `.blend` SHA. Never add files inside an existing checkpoint bundle. |
| `workflow.writer_guard()` | Serialize short metadata writes by cooperating callers. Do not hold it while rendering, running Blender or awaiting review. |
| `begin-edit` / `finish-edit` | Keep scoped native authoring and publication unchanged. Publishing a checkpoint does not complete a workflow stage or resolve feedback. |
| `preview-revision` / `accept-revision` | A saved external edit may supply the result checkpoint for a feedback response after acceptance. Do not create a fictional dispatch. |
| `quality.audit()` / `quality.select()` and render receipts | Bind review images to checkpoint bytes and view settings; retain native checks and attributed visual assessments. |
| Current project skills | Route to existing environment, architecture, materials, assembly, lighting and review methods. |

The new layer coordinates evidence above existing native operations. It does not intercept arbitrary MCP writes, authenticate authors, or make the advisory harness a sandbox.

## 1. Structured feedback contract

Draft examples: [note](examples/feedback-note.draft.json) and [response](examples/feedback-response.draft.json). Their IDs, hashes and evidence paths are synthetic placeholders, not real artist feedback or passing fixtures.

### Note

Use schema `dcc.feedback.note.v1` with these fields:

| Field | Meaning |
|---|---|
| `id` | Stable UUID allocated by the runtime; retained across all responses. |
| `source` | Claimed role (`artist` or `agent`), author and source reference. Attribution is caller-supplied; do not label agent critique as artist feedback. |
| `stage_id` | Stage responsible for addressing the note. Null is allowed before a workflow is bound. |
| `category` | `technical`, `visual` or `preference`. Preferences are local direction, not new universal validators. |
| `text`, `acceptance` | Concrete issue and what evidence would demonstrate a satisfactory response. Preserve the original wording. |
| `priority` | `blocking` or `advisory`, within the recorded brief/authority. Advisory notes remain visible even when they do not block progression. |
| `anchor` | Checkpoint manifest ID and native SHA; optional instance/material IDs and a frozen render receipt/image/view reference. |

Validate target IDs against the anchored observation, not the newest object names. Names may be included for display but cannot silently rebind a note after a rename, deletion or duplication. Screen coordinates use normalized `[0,1]` values and require the exact referenced image. A screen pin is not automatically a 3D point. Optional frame anchors contain an integer frame and positive rational FPS; preserve exact frame semantics rather than rounding seconds.

A note can reference any verified checkpoint in the project history. Default capture targets the active checkpoint. Initial scope excludes unpublished candidate files; retain candidate critiques through the existing quality loop. A deleted target remains an unresolved note with an explicit missing-target condition until it is reassigned or closed through a recorded decision.

### Response and verification

Use schema `dcc.feedback.response.v1`. A response references the original note ID, result checkpoint and concrete change description. Disposition is `implemented`, `partial`, `deferred` or `not_applicable`; each requires a reason, and implemented/partial responses require relevant evidence references.

**An implementation claim does not close a note.** Store a separate verification record referencing the exact response and result checkpoint:

- Technical verification recomputes the applicable supported native contract and checks the evidence binding. Retain the contract plus its required before/after observations and native checkpoint references, not just a check report. An imported `passed: true` value is insufficient.
- Visual verification records an actual inspection of the specified images, with reviewer attribution and a narrow finding. It is not an automated beauty score.
- A visual note requiring artist judgment stays awaiting artist review unless prior user direction explicitly delegates that decision. Agent review is usable within the accepted direction, with `artistic_acceptance` still unassessed.
- Mixed technical/visual requirements retain both evidence types. Passing one does not satisfy the other.

Derived statuses: `open`, `in_progress`, `awaiting_verification`, `resolved`, `deferred`, `not_applicable`, `reopened`. A partial response stays unresolved. Deferral and non-applicability need a separate attributed disposition decision; the builder cannot remove a blocker merely by selecting a status. Routine interpretation may use existing delegation, while a change to explicit artist requirements needs the artist's direction.

Carry every unresolved note across versions and sessions, not just notes from the last review round. Never auto-resolve after a retry cap. Corrections, reassignment, reopening and supersession append events; they do not rewrite the original note.

Resolution is valid at its reviewed checkpoint. On a later checkpoint, show that historical resolution and mark current validity `needs_recheck` until applicable checks/inspection are repeated. For the first release, use this conservative rule rather than guessing field dependencies. Rechecking may reuse unchanged image bytes only when their checkpoint/view binding is still valid; copied old evidence cannot claim to show a changed native file.

## 2. Small environment workflow manifest

Use schema `dcc.environment.workflow.v1`. The complete [draft manifest](examples/environment-workflow.draft.json) defines a linear sequence with explicit dependencies, applicable skills and required evidence types. Seven stages are enough; no arbitrary workflow scripting or parallel native writers.

| Stage | Deliverable | Evidence and review |
|---|---|---|
| `direction` | Brief, references, style record, protected features, review views and project permissions | Attributed references and recorded direction; agent proceeds within the existing brief. Ask only for unresolved direction that materially changes the result. |
| `blockout` | Connected spatial layout, scale and major silhouettes | Scoped native contract, whole-scene views, layout review. |
| `assets` | Editable architectural/prop construction and shared identities | Supported native checks, shared-user inspection, construction details. |
| `materials` | Coherent material families, texture scale and controlled variation | Supported material/dependency checks and representative detail views. |
| `assembly` | Grounded placement, circulation and purposeful dressing | Support/clearance checks where qualified; whole-scene and detail inspection. |
| `lighting` | Motivated lighting and readable composition through fixed views | Relevant preservation contract, bound renders and visual assessment. |
| `delivery` | Latest editable native checkpoint, review evidence and continuation handoff | Fresh native reopen, current feedback reconciliation and delivery review. |

Evidence-kind names in the manifest are proposed registry keys, not new native measurement capabilities. A `native_contract` record must point to a supported existing contract; unimplemented topology/UV/animation checks must not be advertised as available. Define each evidence kind's validator before enabling the template.

### Binding and versioning

`workflow-bind` copies the manifest and the explicitly selected skill files/references into project coordination storage, records their hashes and the minimum compatible runtime, and links the binding to the current checkpoint. Store project-specific review policy and permission evidence with the binding. Subsequent repository skill edits do not silently change an ongoing project.

Keep the snapshot bounded: selected skill text and its required documentation/recipe version references, not all repository files or native binaries. If a recipe executes runtime code rather than a copied script, record its package version and source digest; a mismatch requires a recorded upgrade or the qualified prior runtime.

Default review policy is `agent_within_brief`, with separate `artist_acceptance: not_evaluated`. A project may explicitly require `artist_required` for selected stages. Neither policy waives failing native checks. Existing user permission carries forward; the template must not create unnecessary approval stops or pretend that an agent has human approval.

For an existing environment, bind the workflow at the current accepted checkpoint and record earlier stages as `inherited` with evidence references and known gaps. Do not fabricate historic stage approvals or demand rebuilding the scene. Inherited stages satisfy ordering only; their missing evidence must be addressed before claiming delivery. Preserve the accepted production environment while exercising this on an owned copy.

### Stage state and progression

Derived/stored states: `blocked`, `ready`, `working`, `awaiting_review`, `complete`, `inherited`, `needs_review`. Check dependency IDs, unique stage IDs and absence of cycles when binding.

`stage-submit` freezes an evidence inventory, the current checkpoint, required feedback IDs and their responses, predecessor stage receipt IDs, review policy, and coordination revision. Missing required evidence or an unanswered blocking note prevents completion. A submission may explicitly remain incomplete while recording partial work.

`stage-complete` revalidates the submitted hashes, expected checkpoint and coordination revision; runs applicable validators; requires the configured review record; and verifies that all applicable blocking notes are resolved or explicitly waived under recorded authority. Advisory notes remain listed. New feedback or a changed checkpoint invalidates a pending completion and requires a refreshed submission.

Stage receipts are immutable historical facts. Normal work in the next stage does not erase completed planning/construction history. Reopening or changing an upstream stage revision marks its dependent stages `needs_review`; revalidate them, with a documented no-change finding where appropriate. Delivery always checks current native evidence and current validity of blocking feedback, even when earlier stages were completed at older checkpoints.

A new blocking note assigned to an already completed stage marks that stage and its dependent stages `needs_review`. An advisory note remains visible without automatically reopening the whole sequence. Feedback cannot quietly disappear because its responsible stage finished earlier.

## 3. Storage, interruption and compatibility

Add a separate optional `coordination/` directory under an existing project root. Preserve checkpoint bundle inventories and the native operation journal exactly as they are. Use one ordered stream of immutable metadata event bundles for feedback, workflow binding and stage transitions:

```text
PROJECT/
  checkpoints/                  existing, unchanged
  operations.jsonl              existing native operation journal
  coordination/
    events/000001/
      event.json                event type, payload, request ID, previous event hash
      artifacts/                copied evidence / pinned workflow inputs, when needed
      manifest.json             complete inventory and hashes, written last
```

Bind each event to the immutable project metadata hash. Keep references to committed native checkpoints by ID; copy external review evidence into the event bundle with relative, contained paths. Reject traversal, links/reparse points, nonfinite numbers, unknown schemas and changed inventories using existing repository conventions. Hashes establish integrity, not producer authenticity.

Mutations use `writer_guard`, an expected coordination revision and a caller-retained request UUID. Return the new revision and event identity. A repeated request with identical payload returns the committed result; the same UUID with different content is rejected. Check committed-request replay before rejecting the old expected revision. A partial bundle remains visible as a reconciliation stop; never silently skip it, discard it or replay native work.

Native publication and coordination events are deliberately separate commits. If `finish-edit` publishes but the feedback response write is interrupted, recovery finds the existing checkpoint and records the response; it must not rerun the Blender edit. If acknowledgement of the metadata commit is lost, replay returns its retained receipt.

Feedback capture may record a historical issue while a native operation is pending, provided the verified metadata can be read and the short lock is available. Pending native work prevents stage completion and new native writes, not observation of an issue. An actual stale lock or partial metadata state remains an inspection stop.

Old projects without `coordination/` behave as before. New `resume`/`review` readers add an optional `coordination` section only when enabled. A malformed present coordination directory must not silently look disabled. Older runtimes may still read native checkpoints but cannot enforce this extension; document that downgrade limitation and require the new runtime for coordinated mutations. No claim of protection against older/direct writers.

## 4. Proposed CLI and skill changes

These command names are planned, not currently available:

| Command | Purpose |
|---|---|
| `feedback-add PROJECT --note FILE --expected-revision REV --request-id UUID` | Retain a new attributed note and its validated anchor. |
| `feedback-respond PROJECT --response FILE --expected-revision REV --request-id UUID` | Record implementation/partial/deferred intent and evidence without silently closing it. |
| `feedback-verify PROJECT --verification FILE --expected-revision REV --request-id UUID` | Record recomputed technical results and/or attributed visual review against the exact response. |
| `feedback-decide PROJECT --decision FILE --expected-revision REV --request-id UUID` | Reopen, reassign, supersede or explicitly accept a deferral/non-applicability decision. |
| `workflow-bind PROJECT --manifest FILE --binding FILE --expected-revision REV --request-id UUID` | Pin the workflow, relevant skills and project review policy. |
| `stage-submit PROJECT --submission FILE --expected-revision REV --request-id UUID` | Freeze one stage's proposed completion evidence and outstanding-note inventory. |
| `stage-complete PROJECT --submission-id ID --review FILE --expected-revision REV --request-id UUID` | Validate and retain completion, or return actionable missing/stale evidence. |
| `stage-reopen PROJECT --decision FILE --expected-revision REV --request-id UUID` | Record upstream revision and invalidate dependent readiness without erasing history. |

Use revision `none` only before the first coordination event. Payloads carry checkpoint identities wherever applicable. All commands support an optional exclusively-created `--out` receipt; failed receipt export does not undo a committed event.

Extend existing `resume`/`review` with manifest/skill digests, eligible stages, blocking and advisory counts, outstanding note IDs, review-policy status, current versus historical verification, and pointers to complete evidence. Summaries must not truncate blockers silently: report total counts and offer a complete machine-readable listing with stable ordering. Load only the active stage's relevant skills and notes into agent context.

Update `dcc-harness`, `dcc-plan-environment`, `dcc-build-revise` and `dcc-review-continue` after the commands work. Their sequence becomes: resume -> inspect stage and feedback -> scope native edit -> publish/reject through existing commands -> respond with evidence -> verify -> submit/complete when eligible. Keep artist attribution and authority explicit. No automatic global skill rewrites.

## 5. Implementation sequence

Create a `codex/structured-feedback-workflow` branch from the inspected feature baseline when implementation begins. Preserve any intervening user changes; reconcile with the latest base before editing. The file/module names below are proposed ownership boundaries, not permission to overwrite existing files.

| Slice | Files/responsibility | Completion evidence |
|---|---|---|
| 1. Contracts and metadata store | New `dcc_harness/coordination.py`, fixtures and `tests/test_coordination.py` | Verified immutable events, project binding, request replay, changed payload rejection and interrupted-write diagnostics. |
| 2. Feedback lifecycle | New `dcc_harness/feedback.py`, CLI commands and `tests/test_feedback.py` | Notes survive multiple revisions; response alone cannot resolve; stale/missing evidence and unauthorized disposition cannot close a blocker. |
| 3. Workflow and pinned skills | New `dcc_harness/environment_workflow.py`, package-owned JSON template and `tests/test_environment_workflow.py` | Template validation, explicit inheritance, pinned versions, dependency invalidation and policy-aware completion. |
| 4. Everyday integration | `workflow.py`, `__main__.py`, four skills, usage docs and package data configuration | Compact fresh-process resume includes every blocker; legacy projects remain compatible; installed wheel includes the template. |
| 5. Native qualification and report | New `scripts/qualify_feedback_workflow.py`, retained run artifacts and results doc | Owned Blender exercise, preservation checks, fresh-session continuation, source/installed verification and disclosed evidence limits. |

No new runtime dependency is required: follow the existing explicit Python validators and standard-library storage pattern. Do not create a general plugin framework, database migration system or workflow expression language for this increment.

## 6. Validation and completion criteria

Portable tests should target meaningful failures:

1. Wrong project/checkpoint/native hash, unknown target, stale render receipt and out-of-range pin/frame data reject before commitment.
2. Original note survives two response rounds; partial/deferred work remains visible; an omitted note blocks stage completion; claiming implementation without verification cannot close it.
3. Technical evidence is recomputed; visual review is attributed; same-agent review is disclosed; agent verification never becomes artist acceptance.
4. New feedback after submission, a changed native parent or a changed upstream stage receipt invalidates pending completion.
5. Duplicate request after lost acknowledgement returns the original receipt; different content under the same request ID rejects; interrupted metadata writes cannot be bypassed.
6. Manifest cycles, missing skills, unknown evidence types and missing inherited-stage evidence produce clear failures. Updating repository skills does not change a pinned project.
7. Pending native operations block completion; feedback metadata cannot clear an unresolved native operation or trigger a redispatch.
8. Projects without the extension retain current behavior; installed CLI/package data work outside the repository; old native history stays byte-identical.

The Blender exercise uses an owned, self-contained small environment fixture with a shared material, several instances and fixed cameras. Seed three **synthetic test notes**: a measurable dimension revision, a visual material issue and a protected lighting/layout requirement. Keep synthetic notes clearly distinct from the user's actual feedback. Include a forgotten-note attempt, stale-image attempt, protected-feature violation and passing correction.

Reopen each candidate in a separate Blender process, observe the saved state, render the relevant views, and verify that the final native file retains the declared protected features. Resume in a new Python process using only retained files. The native qualification script tests runtime continuity; it cannot by itself prove fresh-agent behavior or judge image quality.

After the portable/native gates, use a fresh agent session under the user's continuing evaluation authorization, with a sealed file packet and no builder transcript, to finish an outstanding revision. Give a separate reviewer only the brief, note, before/after evidence and contract. Record whether either needs missing context, whether notes were forgotten, actual inspection time and remaining artist repair work. This is a prospective qualification task, not a claim that it has run.

Run focused tests while building, then the full source suite and installed-wheel checks once integrated. Do not rerun prior art trials or edit production checkpoint 9 to qualify metadata changes. Save command logs, package hashes, input/output native hashes, review evidence and a concise results report in a new ignored run directory.

Release criteria: all applicable technical gates pass; fresh continuation can retrieve and account for every note; no stale or wrong-checkpoint evidence closes a blocker; stage completion reflects the configured review policy; a concrete Blender revision survives reopen without breaking its preservation contract. Report measured continuity separately from artist acceptance and comparative quality. If no artist review is available, ship the bounded engineering capability with that creative qualification still open.

## Research basis

Source reviewed: Mortiflix commit `e6beb12289a97b6d54cc1511375f6840af1a5375`.

- [Feedback and stage gates](https://github.com/GTKottman/mortiflix-oss/blob/e6beb12289a97b6d54cc1511375f6840af1a5375/src/gates.mjs): versioned notes and required response coverage. Our adaptation separates acknowledgement, implementation and evidence-backed resolution.
- [Pipeline packages](https://github.com/GTKottman/mortiflix-oss/blob/e6beb12289a97b6d54cc1511375f6840af1a5375/docs/PIPELINES.md): stages, skill selection, checks and review formats. Our initial scope is one Blender environment template.
- [Session context](https://github.com/GTKottman/mortiflix-oss/blob/e6beb12289a97b6d54cc1511375f6840af1a5375/src/torch.mjs): reconstruct working context from retained state. Our implementation extends the existing resume packet instead of introducing a Claude-specific runner.
- [Current quality loop](../../guides/QUALITY_LOOP_USAGE.md), [everyday workflow](../../guides/EVERYDAY_WORKFLOW.md) and [external revisions](../../guides/EXTERNAL_REVISIONS.md): local contracts and evidence boundaries to preserve.
