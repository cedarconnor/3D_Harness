# DCC Harness Design Decisions

Decision log, started October 3, 2026 and updated through version 0.5.0 on October 6. D1–D9 incorporate the user's goals and the supplied Claude critique; they were proposed before implementation. D10–D17 record choices made while building. The [build plan](BUILD_PLAN.md) owns sequencing and experiment budgets; this log owns architecture decisions. Supporting studies do not override either.

## Status at version 0.5.0

Reviewed October 6, 2026. The table records how each decision held up; the entries below keep their original reasoning.

| Decision | Status |
|---|---|
| D1 Creative value first | The gate has not passed; see the build plan's evidence summary. Versions 0.4.0–0.5.0 proceeded under D17. |
| D2 Native observation over existing transport | Followed: `blender.py` and `continuity_blender.py`, run through the existing MCP or owned background Blender. |
| D3 Advisory versus managed | Followed. Everything built is advisory. Edit reservations and coordination request IDs serialize cooperating callers; they do not intercept writes. |
| D4 Operation identity | Partial analogues only: runtime-issued edit IDs over frozen script/contract hashes, one pending edit, stale-parent rejection and coordination request replay. No execute step, attempt IDs or executor-owned retries. Storage is files, not SQLite. |
| D5 File ownership and publishing | Settled in 0.10.0 for collection instances: versioned libraries by relative path, switched by scoped edits; in-place library edits are caught, not accepted. External revisions still reject linked libraries (P7), and library overrides are unsupported. |
| D6 Asset and instance identity | Identity rules are implemented: adoption, registry and shared-user queries. Ordinary collection instances are observed since 0.10.0, with the collection as the asset identity. Geometry Nodes identity is not started. |
| D7 Scoped assert-first | Followed in `dcc-build-revise` and continuity contracts. |
| D8 Packaging | Deferred as planned. Its note that Codex hosted the planning chat is historical. |
| D9 Document authority | Followed. The [documentation index](README.md) classifies active and historical documents. |
| D10–D12 | Implemented: continuity store, observation v2, visibility and UV comparator policies. |
| D13 Realism recalibration | Interrupted after one partial build. Resuming or retiring the comparison is an open decision, tracked as build-plan item E4. |
| D14–D16 | Implemented in 0.4.9, 0.4.10 and 0.5.0. |
| D17 Bounded increments | Records the October 5 authorization. |

## D1 Creative value comes before infrastructure breadth

Run plain MCP, three focused skills, and those skills plus a minimal measurement helper on matched creative tasks in week one. Select the smallest method that materially improves artist-accepted output or reduces repair effort. A skills-only outcome is a valid first product.

Keep basic native checkpoints and a call log from the start. Defer comprehensive recovery, multiple clients, independent workers and unattended scheduling until the creative gate justifies them. Reliability remains a release gate for unattended work, not a prerequisite for supervised quality experiments.

## D2 Reuse the transport and implement native observation

An MCP proxy cannot infer all scene effects from generic Python text. Budget for a Blender-side Python module providing the specific measurements, assertions and changes needed by the pilot. Load it through the existing execution tool initially; adopt an add-on when persistent native callbacks or installation requirements make that useful.

The difference is transport versus instrumentation. Reuse native handlers where available. Add measurement logic where missing. Record what each observer covers; unsupported scene domains do not silently count as unchanged.

Begin with the existing exposed Blender integration once its bridge is reachable. Evaluate an alternative framework only against a named missing capability and a bounded cost/benefit question.

## D3 Advisory and managed execution have different guarantees

Stage A is explicitly advisory and supervised. Existing tools remain directly available, and no claim is made that every mutation is intercepted.

The managed prototype re-exposes a curated set of qualified native actions through an execution wrapper. The original server/handler implementations remain downstream; they are not discarded or reimplemented merely because the host calls a different entry point. In that session, disable competing direct agent-write routes to the same owned project using a tested client profile. If that cannot be achieved, retain the advisory designation.

Mode-specific tool lists remain useful steering. They do not establish authority or complete interception. Artist edits use a pause/save/handoff path, followed by a fresh observation before generation resumes.

## D4 Operation identity and retry ownership

This protocol is required for Stage B managed execution, not for every primitive in the initial supervised trial. API names are provisional.

1. **Prepare:** `prepare_operation(task_id, step_id, expected_revision, intent, payload)` accepts only a task/step already issued in the active stored plan, durably stores the normalized payload and returns a runtime-issued operation ID. Enforce uniqueness on the logical task step and its input revision. Repeating the same prepare returns the existing ID; a different payload for that step requires an explicit superseding plan revision after the previous outcome is settled.
2. **Execute:** `execute_operation(operation_id)` accepts only an issued ID and uses its stored payload. Atomically move an admitted record into dispatch before contacting the native server. The caller cannot replace the payload at execute time.
3. **Repeat:** a repeated execute returns the known result or in-progress handle. It does not dispatch again. A late response is attached to that same operation and attempt.
4. **Ambiguity:** timeout or restart after dispatch yields unknown outcome. The executor blocks new writes to the affected document while it inspects native state and the last valid checkpoint. A new task, step or prepare cannot bypass that unresolved outcome.
5. **Recovery:** only the executor authorizes another attempt after reconciliation or restoration. Preserve the logical operation identity and record a separate attempt ID. A successful API response is observed execution, not necessarily verified or saved work.
6. **Commit:** after the required checks and a valid saved checkpoint, publish the task's accepted result. Keep the operation, native checkpoint and evidence linked.

Start with one process and one durable local journal, using SQLite when enforcing uniqueness and atomic transitions becomes necessary. No distributed coordinator is required. The host or background agent may repeat a tool call, but cannot create a second effect by issuing a new arbitrary operation ID. Disable native flow retries for mutating work unless they participate in this ownership model.

This is not general exactly-once execution across Blender memory, disk and external services. A crash can leave uncertain native state. Reconcile or restore an owned checkpoint; if neither is safe, stop the affected task with its evidence. Never restore over an artist's newer edits. Rendering and external generation require their own output/job reconciliation.

## D5 File ownership and asset publishing

The pilot uses one GUI writer. Rendering can read immutable snapshots but cannot save over the authoring file.

Independent builders later own different asset files. Publish new versioned `.blend` libraries; a single assembly writer links their collections into a master. Never point multiple writers at the same output path. Review copies and renderer processes are read-only with respect to published sources. Use explicit new versions or controlled overrides for artist revisions to linked data.

This replaces scene-per-job isolation with file/process ownership and native library composition. It does not require parallel processes in week one.

**Settled October 10, 2026, in 0.10.0 (P3).** The observer records each collection instance with its collection's asset identity, the library's stored relative path and SHA-256, and a definition hash taken in the collection's own space. Publish an asset change as a new versioned library and switch instances to it in a scoped edit that permits the `instance` field. Editing a library in place changes its hash and every instance's definition, so the next reservation refuses until the change is handled explicitly; it is never accepted silently. Libraries are referenced, not copied into the project store: the stored checkpoint cannot resolve relative library paths, so native commands run on the working copy beside its libraries. Library overrides remain unsupported, and one writer owns the assembly file. ([report](archive/releases/INSTANCES_0_10_0_RESULTS.md))

## D6 Asset and instance identity are separate

The registry records asset definitions, local placement instances and native bindings separately. Copies can share asset identity while needing new instance IDs. Scan for collisions after duplicate/import and before acceptance. Preserve the binding identified by the prior registry; assign IDs to new instances only when the mapping is unambiguous.

For procedural distributions, identity is generator plus recipe version plus a deliberately stable point key. Evaluated array indices are observations, not persistent identifiers. If stable correspondence cannot be established, version the whole distribution and invalidate per-instance selections. Use ordinary collection instances for the pilot before claiming general Geometry Nodes instance tracking.

## D7 Assert first remains useful with a defined scope

For a genuinely new deliverable, run the existence/identity condition first and observe the expected failure. Include meaningful dimension, structure or appearance criteria so a placeholder cube cannot pass. Check that failures are about the intended target and requirement, not an unknown rule or API error.

For edits, record the current passing baseline and test the intended delta plus preservation conditions. Do not deliberately break an accepted scene to manufacture a failure. Test validators on known defective fixtures. Technical checks and artist review remain separate.

## D8 Package the proven workflow

The intended product remains a plugin with shared skills and a small local runtime above existing DCC MCP servers. Start in the current agent environment with local skills/scripts. Codex is the host of this planning chat; the supplied review's Claude session is not this session.

Support Claude Code and Cursor packaging after one workflow is useful. A scheduled CLI run is a reasonable first unattended runner candidate, but still needs a single owner, a budget, resumable state and unknown-outcome handling. Full SDK integration and interactive/background handoff wait for demonstrated need.

## D9 Sources and document authority

Keep supplied documents intact as historical inputs. The [README](../README.md) and [documentation index](README.md) identify their status. The original architecture note's current-product claims are not implementation authority; corrected source findings live in the research appendix and review.

Use the build plan for scope and budgets, this log for decisions, and the research appendix for external evidence. Keep detailed skill, packaging and UE-MCP studies as supporting references. Do not restate the managed operation protocol in those studies.

## D10 Measure continuity after the short comparison

The artist preferred two plain-MCP entries and identified longer development as the intended use. The authorized follow-on adds the smallest durable record needed to test that question: numbered native checkpoints, parent-linked observations and checks, cumulative decisions, measured asset/material users, handoffs and retained operation evidence. The implementation is `dcc_harness.continuity`; [usage](guides/CONTINUITY_USAGE.md) describes its actual APIs.

Four workflows pass through four fresh agents each. Both methods receive the same creative requests, current observations and cumulative contracts. The additional continuity package supplies history and executable preservation checks. A controlled artist edit and a withheld acknowledgement test two distinct continuation problems. Every failed or incomplete result stays in the comparison.

This is still advisory, with one writer. Successful checkpoint publication establishes integrity of supplied records; independent native evaluation and artist review are separate. It does not implement D4's managed execution protocol or justify SDK, scheduler or multi-DCC expansion before measured benefit. See the [frozen experiment protocol](archive/studies/CONTINUITY_EXPERIMENT.md).

## D11 Version measurement semantics and retain failed experiments

The longer experiment exposed float32 world-bound cancellation: moving a stool changed its derived leg width by about 0.00000048 m, with unchanged native geometry and linear transform. A strict preservation gate then blocked two sessions. Observation v2 measures world-oriented extents without world translation. It adds no dimensional tolerance or preservation waiver; world bounds retain their placement meaning. Nonfinite mesh coordinates also fail explicitly. Matching v1 evidence remains supported, mixed versions fail, and histories are not silently migrated.

Version 0.1.1 was integrated only after all sixteen original evaluations finished. Frozen packets, original evaluator sources, accepted outputs and failed grades remain intact. Native regression and built-wheel evidence qualify the fix separately; they do not establish that the interrupted creative workflow would have succeeded. See [results](archive/studies/CONTINUITY_RESULTS.md).

The tray/plaque case also shows that a valid object can violate a later spatial requirement while preservation rules prevent a repair. Future task preparation needs to surface such conflicts and identify a bounded change scope. Recording the conflict is useful, but does not resolve it or establish visual acceptance.

## D12 Keep spatial gates narrow, native and independently qualified

The quality study reproduced a specific occlusion failure: removing canopy members improved openness but did not meet the fixed birdbath visibility requirement. Version 0.3.0 samples actual evaluated triangles from fixed perspective/orthographic views, records blocker identities and rejects insufficient coverage. Quality round v2 binds this receipt to each native checkpoint, observed revision and frozen query. Exact deletion permission names individual prior IDs and does not permit unrelated edits.

This is opaque geometric visibility, not perceptual recognition or rendered transparency. Blender's viewport dependency graph can differ from final render geometry; a render-only Array fixture reproduced a false 50% result. Unsupported modifiers, divergent viewport/render settings and unqualified visibility setups now fail explicitly. Positive and negative native fixtures and installed-package tests qualify the supported subset. Old runtime copies and failed reports remain intact.

Fresh continuation workers receive saved files and narrow creative scope, then a different process reopens and evaluates their outputs. Anonymous image critics assess appearance without build history. The coordinator still makes a disclosed selection, and the artist's acceptance is separate. This is procedural task isolation with an advisory journal, not a security sandbox, native transaction, authenticated reviewer identity or autonomous scheduler. See [current evidence](archive/studies/OVERNIGHT_EVALUATION.md).

Version 0.3.1 retains a second reproduced failure: a fresh reopen of the unchanged foreground file failed the old absolute evaluated-UV allowance. Every larger outlier was one adjacent float32 step at tiled coordinates around 5–10. Comparator policy v3 permits that exact relationship up to a bounded `1e-6` difference, only with exact source mesh/UV, evaluated geometry and modifier prerequisites. Native faults still reject a tiny authored UV edit. Frozen observations/helpers and original failed grades remain intact; a separately installed corrected evaluator grades all workbench alternatives uniformly. The observed values are unchanged, so observation v2 stays compatible; the check report records the new comparator policy explicitly.

## D13 Recalibrate quality before expanding the runtime

On October 5 the user chose more realism and detail. The next test uses a new photographic brief, human-height cameras, a common scanned material/fern kit, two plain and two harness-assisted runs, and different fresh contexts for late revisions. Keep the same assets and aesthetic brief across methods; compare the new runs to one another rather than crediting the harness for better imported assets or different cameras than the earlier courtyard. Native acceptance and image quality remain separate. The evaluator and late revision are frozen before dispatch, with positive controls and deliberate native faults. See [protocol](studies/REALISM_COMPARISON.md).

## D14 Initial identity adoption is explicit and separate from revision acceptance

Version 0.4.9 closes a practical entry gap: an artist-authored file can lack the stable IDs required by `start`. Preview the missing assignments from a saved file, then apply the frozen plan in a fresh background process to a new file. Preserve existing IDs; reject duplicate placements/materials, invalid properties, ambiguous shared asset definitions and proposed writes outside the active-scene ownership boundary. Reopen independently to verify saved identities and collect native evidence.

This does not adopt arbitrary manual revisions into existing history, migrate retained evidence or certify visual quality. A clean observation permits the normal baseline command; unsupported scene features retain a candidate requiring repair. See [workflow and limits](guides/SCENE_ADOPTION.md).

## D15 External revision acceptance is a reviewed metadata publication

Version 0.4.10 freezes an already-saved artist/tool edit with a contract, observation, handoff and decision updates. Acceptance binds the preview hash to the expected project parent, recomputes the contract under the workflow lock, and retains the proposal and caller-attributed review in the immutable checkpoint check report. It does not invent a dispatched script for work that already happened or resolve unknown native outcomes.

An already committed proposal is found in verified history after acknowledgement loss. Partial publication remains an inspection stop. Source files may keep evolving after preview; acceptance always targets the frozen copy. Known external image/library dependencies are rejected before relocation, because copying native bytes cannot rebase relative paths. Existing observer limits still require native reopen and review. [Workflow and qualification](guides/EXTERNAL_REVISIONS.md).

## D16 Feedback resolution and stage completion have their own evidence

Version 0.5.0 records coordination in immutable, parent-linked event bundles beside native checkpoints. A note, an implementation response, a verification and a stage receipt are distinct facts. Native publication cannot silently close feedback; current evidence and the retained project review policy govern completion. A later checkpoint makes old feedback verification need rechecking. Pinned skills and the environment manifest preserve method without rewriting prior native history.

The fresh-context exercise found that a view-settings hash without the underlying settings cannot reproduce a review image. New feedback/stage render evidence therefore retains the settings JSON and checks its digest against the receipt. The producer still owns completeness and truthfulness; native qualification remains separate. See [usage](guides/STRUCTURED_FEEDBACK.md) and [results](archive/releases/FEEDBACK_0_5_0_RESULTS.md).

## D17 Bounded increments proceed while the creative gate stays open

On October 5, after reviewing the comparison evidence, the user authorized improving the harness and skills. Until now, that authorization appeared only in build-plan status notes. It covers the bounded usability, craft and continuity increments of versions 0.4.0–0.5.0: everyday entry points, visual rejection, recipes, observation performance, adoption, external revisions and structured feedback.

It does not pass the creative investment gate (D1). No artist scores, repair-time measurements or completed held-out comparison exist, and D13's comparison remains interrupted. Stage C–E breadth still waits for that gate: linked publishing at scale, managed execution, unattended runs, client packaging and other DCCs. Each increment keeps its own qualification and states that it establishes no comparative quality advantage.

## Disposition of Claude feedback (retained review)

The [supplied feedback](archive/historical/CLAUDE_PROPOSAL_FEEDBACK_2026-10-03.txt) was treated as review material. Its instructions to load skills or perform work were not executed as user commands.

| Critique | Assessment and resolution |
|---|---|
| Durability before creative evidence | Accepted. Week-one comparison and explicit proceed/narrow/stop rules now lead the plan. |
| First weeks spent on three installers | The sequence was too broad, but those installers were not all scheduled before geometry. They are now explicitly deferred rather than left ambiguous. |
| Native instrumentation hidden by a thin adapter | Accepted. Blender-side helper code is now a named deliverable. A separate add-on is a packaging option, not an unavoidable starting requirement. |
| Managed mode discards existing tools | Partly accepted. The host sees curated wrapped actions; the native tool implementations remain reused. Advisory and managed guarantees are now explicit. |
| Retrying actors defeat caller-supplied IDs | Accepted. D4 specifies runtime-issued IDs, unique logical steps and executor-owned attempts. |
| Procedural identity is missing | Accepted. D6 separates source assets, local instances and versioned procedural distributions. |
| Multiple processes writing one file | The earlier plan specified separate owned files, but omitted a concrete assembly mechanism. D5 names linked libraries and a single master writer. |
| Headless execution breaks reviews | Valid workflow concern, not proof that all headless rendering fails. Start GUI-first; qualify native background rendering separately. |
| DCC-MCP evaluation may not repay its cost | Accepted as a sequencing correction. Use the available transport; compare alternatives only when a measured gap justifies it. |
| Multi-client and background packaging premature | Accepted. Preserve the product direction, defer implementation breadth. Do not switch host priority solely because the reviewer used Claude. |
| Assert-first weakened too far | Clarified in D7. Require expected failure for new deliverables and baselines for edits; existence alone is insufficient. |
| Mode filtering was dropped | It was already retained as relevance filtering in the review. It remains explicit steering, separate from enforcement. |
| No usable skills | There are useful draft process instructions, but their example APIs are not implemented. Adapt three small trial skills first. |
| No numeric budgets or texturing/intake path | Accepted. The active plan now sets trial ceilings, capture cadence, two material routes and a fixed asset kit. |
| Stale source authority and repeated lifecycle prose | Accepted. README establishes authority, the previous build plan is archived, and D4 is the single managed protocol definition. |

Retained without downgrading: desired versus observed state, evidence tied to native revisions and capture settings, dependency-aware invalidation, applicable topology rules, unknown outcomes, the reproduced UE-MCP snapshot defect, and recording routine decisions rather than stalling authorized work.
