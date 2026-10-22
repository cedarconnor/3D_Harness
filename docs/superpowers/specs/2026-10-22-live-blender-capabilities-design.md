# Live Blender control and reusable add-on capabilities

Status: implementation design supporting the owner's requested plan; no product changes implemented by this document.

## Intent and decisions

The owner approved the general capability-discovery and tested-adapter approach and selected **direct operation in the open Blender scene**. No specific commercial add-on is required. Edge wear is an example of an intent a future provider could fulfill. Both autonomous and approval-gated workflows remain supported. The earlier instruction to remove telemetry remains in force.

Deliver two increments: P21 live execution and richer observation, then P22 reusable add-on onboarding and policy. The companion implementation plans specify files, interfaces, regression cases and release gates. The builder may choose internal algorithms within these contracts; the defaults below are proposed engineering decisions, not additional owner statements.

### Approaches considered

| Approach | Advantage | Limitation | Decision |
| --- | --- | --- | --- |
| Generic live Python/operator endpoint | Maximum reach with little routing code | Repeated context discovery; cannot guarantee add-on selection or recovery | Keep existing managed background scripts; do not expose raw socket execution |
| One hard-coded MCP tool per add-on | Predictable recipes | Repeated tool plumbing and provider-specific server releases | Use adapters, not one public tool per product |
| Discover capabilities and execute qualified recipes through shared management | General discovery, explicit tool choice, reusable verification | Requires registry, environment pins and qualification | Selected direction; live execution is the first dependency |

## Current repository seams

- `execution.py` owns admission, immutable requests, budgets, replay refusal, independent observation and publication. Preserve this authority for both backends.
- `native.py:run_worker` starts offline, factory-state background Blender. An installed desktop add-on is not automatically enabled in that process.
- `data/bridge/__init__.py` supplies bounded main-thread dispatch and five read commands. `blender_bridge.py` enforces protocol 2 and that exact list.
- `blender.py` observations deliberately declare incomplete coverage, including arbitrary node/modifier properties, other scenes and animation. They cannot become a universal live-change detector by renaming `revision`.
- `distribution.py:export_addon` currently exports exactly three source/license files. A multi-module bridge requires an explicit export manifest and artifact tests.
- `owner.py` and `environment_workflow.py` preserve artist authority separately from agent completion. A Blender button must not silently become an agent-accessible approval bypass.

## Global constraints

- Python 3.11+, MCP SDK 1.26.0, Blender 5.1.1 on Windows are the initial qualification targets.
- One managed execution service owns admission, operation identity, budgets, verification and publication for background and live backends.
- Unknown mutation outcomes are never automatically replayed; live Blender is never killed to enforce a deadline.
- No telemetry, user-activity recording, tracking URLs or automatic external network calls are introduced.
- Artist approval remains in the existing owner terminal/review-import path; MCP cannot approve its own stage.
- Source and installed-wheel tests, source-archive parity and owned native positive/negative fixtures are required for each increment.
- Existing runtime-pinned projects retain their installed runtime; no silent project migration.

## P21: operate directly in the open scene

### Session attachment and preservation

The bridge generates a process session UUID and a document-generation UUID. Loading any file, including reopening the same path, invalidates the generation and outstanding preparation tokens. Use file-load lifecycle callbacks only; do not restore undo/operator/dependency-graph activity recording. Observe current state on explicit requests and managed job boundaries.

Attaching names an explicit project, scene and session; never choose the first running Blender instance or selected object implicitly. A local pairing descriptor holds a random 256-bit token, port, process/session identity and project binding outside the blend file. The write endpoint binds to loopback, authenticates every write/status request, and never returns the token through observation, MCP results, logs or packaged files. Same-user filesystem access remains a trusted-local boundary, not a sandbox.

The attach operation saves an exclusive recovery copy of the current in-memory scene, including unsaved edits, before assigning any missing harness identities. The active artist filepath must remain unchanged and its disk bytes must not be overwritten. Reuse adoption planning/validation for stable IDs; include the assignment diff and a post-adoption baseline. Empty scenes receive the existing non-rendering harness root. Untitled files are supported only after save-copy semantics pass qualification.

For a new project, initialize continuity from this adopted live baseline and bind its rules. For an existing project, compare against its active checkpoint. Divergent user edits are retained as a named external-edit checkpoint with provenance and stage invalidation; never silently replace the active parent. Automatic recording of that checkpoint is allowed within an autonomous run's policy, but it does not satisfy a requested build or imply artist acceptance. Gated runs preserve the existing stage rules. Pin the selected backend in new `dcc.execution.run.v2`; store replaceable live-session bindings separately so reconnects do not rewrite policy.

### One execution path, two backends

Extract the current background dispatch behind a backend interface; keep its CLI behavior and verification unchanged. Live execution is:

1. Admit the stage and reserve the immutable operation UUID/request under the existing controller lock.
2. Prepare on Blender's main thread: resolve stable target IDs, check context and declared inspection coverage, save a pre-operation recovery copy, compute the relevant scene/provider fingerprint, and return a short-lived preparation token.
3. Persist the token and expected fingerprint before submitting. Recheck session, generation, stage authorization, cancellation and fingerprint immediately before mutation.
4. Journal a dispatched marker before invoking the operation. Run one job at a time in the paired scene. Network threads never call `bpy`.
5. Execute a registered recipe, restore temporary selection/mode/editor changes where valid, and save a separate candidate copy. Leave the result visible in the open scene.
6. Independently reopen that copy using the declared environment and run existing continuity checks plus operation-specific validators. Immediately before publication recheck the live session/generation and candidate fingerprint. A mismatch retains the verified candidate but blocks publication pending reconciliation. After publication check again before marking the live binding ready: a change in the narrow publication/acknowledgment interval leaves the saved checkpoint valid but marks the binding `LIVE_DIVERGED`, blocking further execution and live stage completion until refresh/reconciliation.

Every subsequent preparation compares live measured state against the active checkpoint, not merely against a new snapshot of itself. Artist edits or a file reload during verification therefore cannot become implicit inputs to the next generated edit. There is no claimed atomic transaction spanning the Blender UI and the host journal. The pre/post checks and the next-operation guard preserve that distinction; external changes are imported with their own provenance and stage invalidation before work resumes.

Technical publication does not imply approval. In gated mode edits are visible while the stage awaits owner review; no successor stage executes until approved. Autonomous mode continues within the configured requirements and budgets.

### Conflicts, cancellation and recovery

Fingerprint scope combines existing measured scene state with the recipe's explicit read/write/dependency fields, target identities, frame, relevant context and environment hashes. A missing required measurement means `UNSUPPORTED_COVERAGE`, not an assumed match. `bpy.data.is_dirty` alone is never a revision proof. Cross-scene, rig, simulation or arbitrary-property edits are not automatically qualified by the initial observer.

User changes between preparation and dispatch produce `STALE_SCENE` without mutation. During cooperative multi-step work, compare declared protected state between steps; stop with `CONFLICT` when it diverges. Do not claim to distinguish every user edit from arbitrary add-on internals. A job announces busy state in Blender; simultaneous artist edits to the job's declared scope are unsupported. Initial qualified operations must be bounded synchronous calls or cooperative steps. Modal tools that cannot report completion/cancellation stay discoverable but not live-executable until an adapter exists.

Live status states: `PREPARED`, `QUEUED`, `RUNNING`, `SAVED`, `VERIFIED`, `PUBLISHED`, `CANCEL_REQUESTED`, `CANCELLED`, `FAILED`, `NEEDS_RECONCILIATION`. A cancelled queued job never dispatches. A running non-cooperative operator may finish after cancellation; record that fact, block publication and retain the visible result/candidate for reconciliation. Never terminate the artist's process. Socket timeout triggers status inspection, never mutation retry.

Verification failure can leave the live scene changed. Keep the pre-copy, candidate, journal and error; block subsequent edits until reconciled. Default recovery is explicit `keep-current` or `restore-precopy`; restoration first archives the current state and checks the expected live fingerprint. No automatic full-file reload, undo or rollback that could erase later artist edits. Existing background reconcile behavior remains separate where its guarantees differ.

### Useful control surface

Provide paginated structured inspection of objects, transforms, modifiers, material slots, node graphs, Geometry Nodes interfaces, images, cameras, lights, collections and operator RNA/context requirements. Return coverage limits and stable IDs. Separate data reads from any evaluation/render action that can invoke extension code.

First built-in live recipes: set object transform, set a supported material input, configure a supported modifier and append/update a node-group asset. Recipes use explicit targets and validated parameters, poll operators, set context temporarily and verify effects. A general raw operator name is not sufficient qualification. Existing background Python remains available for broader trusted scripting.

Add bounded `preview` jobs: framed object/scene views and fixed camera/light/color before/after images. Report whether an image is a viewport preview or a render; no implicit artistic pass. Reuse evidence files and workspace image limits.

Public MCP additions: `blender_session(action, payload)`, `blender_inspect(query)`, `blender_execute(request)`, `blender_job(action, operation_id, payload)`, `blender_preview(request)`. These route through the service. Existing observation and background tools remain supported. Bridge protocol 3 negotiates named feature versions instead of assuming a frozen five-command list; protocol 2 is read-only compatibility, never accepted for live writes.

## P22: discover and reliably use future add-ons

### Inventory, profiles and recipes

Inventory both the open-session and isolated-worker environments. Distinguish installed, enabled, compatible, qualified and unavailable; report version/source digest, legacy module or extension ID, exposed operators, supplied assets, required context, offline capability and missing dependencies. Never activate every discovered add-on just to enumerate it. Operator introspection discovers syntax, not artistic purpose.

An immutable project environment profile pins Blender, add-on/module/source hashes, non-secret required preferences, asset hashes and recipe versions. Secrets remain references to local configuration and never enter receipts. Explicitly enable only this profile in workers and independent observers. Profiles that require GUI context can use an owned disposable GUI verifier; if reopening/evaluation cannot be verified, refuse publication. Source changes or missing licenses/dependencies invalidate qualification. No automatic purchases, downloads, global preference edits or upgrades.

Recipe schema `dcc.capability.recipe.v1` includes: ID/version; semantic capabilities; provider identity/source hash; parameter JSON schema; Blender/render-engine compatibility; supported target types; required context and environment; explicit read/write/dependency coverage; deterministic invocation entry point; completion/cancellation protocol; update identity; validators; qualification cases and artifact hashes. Invocation kinds are `python_function`, `operator` and `node_asset`. The registry accepts only locally retained recipes; imported metadata cannot execute code during discovery.

Onboarding sequence: discover -> inspect documentation/source and operator schema -> draft recipe -> qualify on disposable scenes -> register as qualified or retain failure. The calling agent can draft recipes; the MCP server validates, tests and stores them rather than pretending to contain an independent model. User-permitted onboarding can run autonomously. Tests establish technical support; visual superiority needs a relevant controlled comparison or an explicit user preference.

### Selection and mandatory use

Project capability policy uses `prefer`, `require` or `best_qualified`, plus capability, provider order, object selectors, lifecycle stages and permitted fallbacks. Resolve requirements from the brief/user policy and adapter applicability; do not infer that every object needs weathering. Freeze the resolved requirements before dispatch and include the policy digest in review evidence.

- `prefer`: choose the first compatible qualified preferred provider; an allowed fallback carries a reason. No implicit fallback unless configured.
- `require`: require a qualified matching provider and actual verified use. Missing provider, failed poll or missing receipt blocks the relevant stage without a fake success.
- `best_qualified`: use applicable retained benchmark evidence and deterministic tie-breaking by configured priority then provider ID. Without comparable evidence return `NO_COMPARABLE_EVIDENCE`; an explicitly configured fallback may proceed without claiming best quality.

The controller invokes recipes and writes receipts binding capability/provider/version, recipe/environment/policy hashes, target IDs, parameters, dependency fingerprint, operation UUID, accepted checkpoint and actual output verification. Stage submit/completion checks these receipts against the current saved checkpoint. Caller-supplied text saying an add-on was used is not evidence. Reject stale, unrelated, copied or manually fabricated receipts within the existing trusted-local authority model; arbitrary code with the same filesystem privileges is not a hostile-user security boundary.

### Triggering without duplication

Evaluate applicable requirements on object enrollment, entry to a relevant build stage and changes to declared geometry/material/environment/recipe dependencies. These are managed workflow boundaries, not perpetual monitoring of the artist. Represent each effect by `(capability, target ID, effect slot)`. A matching fingerprint reuses the verified result; changed inputs update the same owned effect. Multiple layers require distinct explicit slots. Deleted/edited effects invalidate the receipt. Shared materials require inspection of all users and either a scoped shared edit or an explicit single-user copy policy.

Direct edits outside capability tools can invalidate requirements and cannot bypass required receipts at completion. A capability repair job consumes the same operation/time budget as any other edit. An unavailable required add-on is an actionable stop in autonomous mode, not an extra permission prompt and not a reason to silently use manual construction.

### Qualification scope

Use distributable synthetic fixtures first: a legacy Python add-on, an extension package, an operator requiring a 3D View and a node asset. Include two providers for the same capability with deliberately different compatibility/results. They prove onboarding and selection without committing to a commercial product. Add product-specific adapters later with the user's supplied installation/license; do not advertise universal support or higher quality from synthetic fixtures alone.

Core telemetry remains absent. Imported third-party code is a separate dependency: record its reviewed network behavior and offline qualification. Do not claim Blender's offline flag sandboxes arbitrary Python networking. Network-requiring/unreviewed providers are unavailable under the default offline profile.

## Delivery and acceptance

P21 is independently shippable: live attach/edit/preview/checkpoint/recovery in both modes, with old background behavior intact. P22 follows: generic onboarding and policy enforcement for qualified recipes on both backends. The existing artist-quality evaluation remains separate; these upgrades do not automatically close it.

Each release exports a self-contained add-on with a hash-indexed file manifest; bundled bridge modules must not require the external harness package inside Blender. Include explicit runtime support files needed by qualified built-ins. Keep upstream attribution and its reduced source intact. Ship core, rules, schemas and test-qualified built-in recipes in one Python package; user-licensed add-ons remain external pinned dependencies.

Adversarial acceptance includes unsaved/untitled scenes, relative textures, same-path reload, duplicate object names, stale preparation, lost replies, controller restart, provider mutation before error, non-cooperative cancellation, missing dependencies on reopen, shared materials, required-provider bypass, repeated triggers and a changed add-on source without a version bump. All native tests use owned GUI processes and copied fixtures, never the artist's production scene.

## References and qualification boundaries

- [Current combined integration](../../guides/COMBINED_MCP.md) and [telemetry-removal evidence](../../reference/TELEMETRY_REMOVAL_VERIFICATION_2026-10-22.md).
- Blender documents `save_as_mainfile(copy=True)` as preserving which file is active; handling unsaved data and relative dependencies must still be tested on the supported runtime: [Blender 5.1 window-manager API](https://docs.blender.org/api/5.1/bpy.ops.wm.html).
- Operators have context requirements and polling: [Blender operator API](https://docs.blender.org/api/5.0/bpy.types.Operator.html). Context overrides are not a substitute for a real GUI when one is required.

No open product choice blocks planning. Direct open-scene operation and general future add-on support are owner decisions. Initial operation coverage, protocol, pairing, no automatic rollback, fixture providers and release split are explicit engineering defaults to validate during implementation.
