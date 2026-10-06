# DCC Harness Architecture and Skill Review

Supporting review. Current implementation order is defined by the [build plan](./DCC_HARNESS_BUILD_PLAN.md) and [design decisions](./DESIGN_DECISIONS.md). Recovery requirements below are staged: basic checkpoints during supervised experiments, managed execution before unattended work.

Reviewed October 3, 2026. The architecture note and all six files under `dcc-skills/` were read as design material. Their embedded execution instructions were not treated as authorization to build assets, install tools, dispatch agents, or modify the supplied files.

The strongest ideas are explicit specifications, compact scene observation, recorded operations, staged workflows, fixed review views and independent verification. Keep these. The main changes are to make recovery enforceable, represent project-wide dependencies, and give artistic judgment its own evidence and workflow.

The supplied folder contains process documents and example API calls. It does not yet contain an executable harness or implementations of the proposed assertion and history APIs. The review below evaluates the proposed design; it does not certify the linked projects' runtime behavior.

## Findings that affect the architecture

| Priority | Finding and evidence | Required correction |
|---|---|---|
| P1 | **The cited Mixar envelope does not establish the stated execution guarantees.** The note at lines 204–220 says every request enforces epochs, fences and duplicate rejection. In the inspected source, the envelope is optional and its module documentation says it is parsed and carried through without task admission through it. [Local claim](./llm-dcc-agent-architecture.md), [pinned source](https://github.com/Mixar-AI/mixar-app/blob/3696b05bbcfc477ffb820f5f10375f35c263e0cb/src/scripts/mixar/modules/common/agent_execution/request.py#L4-L10) | Treat the envelope as a useful schema pattern. Implement admission, stale-write rejection and persistent receipts, then test them. Do not infer enforcement from field names. |
| P1 | **A separate scene or level is insufficient isolation.** The note at lines 224–230 and the execution skill at lines 26–30 use scene-per-job as the analogue of an isolated checkout. Blender scenes can share object data, materials and other datablocks; Unreal levels still share project assets. | Use separate native files and owned processes for independent builders, immutable published assets and explicit integration. Logical scene scopes remain useful for organization. |
| P1 | **Undo alone does not establish recovery.** Architecture lines 325–334 defer execution envelopes until multiple agents; skill checkpoints make native file snapshots optional. A single agent can lose a response, retry a mutation or resume against stale state. | Start supervised trials with saved task checkpoints, a call log and readback after ambiguity. Add managed operation identity and restart reconciliation before unattended execution. Full recovery infrastructure is not a prerequisite for testing creative quality. |
| P1 | **The proposed sandbox overstates its boundary.** Architecture lines 261–282 propose porting Python restrictions by changing a namespace allowlist. Native DCC APIs can touch files, extensions, embedded scripts and external resources through many paths. | Use typed operations, scoped workers and OS-level boundaries for generated code. Treat AST restrictions as additional checks, not a general security guarantee. Blender's vendor documentation itself warns that its MCP executes unguarded code. [Vendor documentation](https://www.blender.org/lab/mcp-server/) |
| P1 | **Completion has no durable link to the exact scene and dependencies.** The execution skill at line 30 trusts a text completion marker, while line 64 deletes review packages. The verification skill anchors freshness to the current message. | Bind evidence to native checkpoint, dependency hashes and validator configuration. Invalidate it on relevant changes. Use transactional task state, and retain review history under an explicit storage policy. |
| P1 | **Project consistency needs more than task-local contracts.** Current asset/material/scene specifications omit a shared style record, revision dependencies, approved asset versions and change propagation across lighting and shots. | Add environment, style, lighting and sequence contracts; stable asset and instance IDs; dependency-aware invalidation; and explicit artist locks. A late shared-material change must identify every consumer. |
| P2 | **The scene-diff proposal misses important changes.** Architecture line 149 suggests hashes of transform, vertex count and material slots. Mesh coordinates can change without changing vertex count; node values, texture contents, UVs, animation and instances can change without those fields moving. | Use domain-specific fingerprints, stable IDs and evaluated observations. Document coverage. Capture hooks are hints; compare complete relevant state at checkpoints. |
| P2 | **Tool visibility is confused with enforcement.** Architecture lines 50–54 imply that a texturing mode prevents remodeling. An exposed arbitrary Python tool can bypass this restriction; clients may also cache tool catalogs. | Filter tools for relevance, but enforce allowed targets and operation categories at dispatch. Scope or disable script escape hatches. Use capability discovery with versioned schemas. |
| P2 | **Technical validity is too universal.** The examples impose manifold meshes, zero ngons, no UV overlap and zero warnings across unlike tasks. Foliage cards, open architectural surfaces and intentional mirrored UVs may be correct. Export formats can legitimately change vertex counts. | Define requirement profiles by asset purpose. Distinguish base and evaluated meshes, intentional exceptions and format conversions. Validate appearance and semantics with tolerances rather than identical serialization. |
| P2 | **The source landscape contains material inaccuracies.** The note says UE has no first-party MCP, calls DCC-MCP host dispatch only, and treats a local-modification mirror as the official Blender source. | Use current vendor sources and the upstream DCC-MCP organization. Pin exact commits and versions. Epic now documents an experimental MCP and Toolset Registry. [Epic documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor) |
| P2 | **Research conclusions are stronger than their evidence.** The LL3M section attributes a measured reduction in regression to separation of critic and verifier and an explanation based on proposal bias. The inspected paper describes verification, qualitative comparisons and ablations, but does not establish that specific causal claim or production recovery. | Present independent verification as a design hypothesis to evaluate here. Preserve context and prior source recipes during revisions; LL3M explicitly demonstrates the importance of retaining prior code. [LL3M](https://arxiv.org/html/2508.08228v1) |
| P2 | **Portability and effort are understated.** Statements such as “lift as-is,” “~150 lines,” “~300 lines” and “a few hundred tokens” omit host differences, scope, licenses, robust geometry checks and failure handling. | Replace line-count estimates with bounded prototypes and acceptance tests. Record file licensing and dependencies before reuse. Mixar's public desktop source does not include its hosted AI backend. [Mixar repository](https://github.com/Mixar-AI/mixar-app) |

P1 means the design could lose work, corrupt continuity or claim unproven completion. P2 means the design could cause substantial rework, misleading evaluation or maintenance problems. These are review priorities, not claims of confirmed exploitable defects in deployed software.

## Review of the supplied skill library

### Writing asset plans

Keep the task-sized deliverables, consumes/produces interfaces, explicit review views and global constraints. Extend the plan format with input versions, authorized change scope, stable IDs, dependencies, native checkpoint requirements, visual criteria and recovery behavior.

Do not require a predetermined modeling approach when exploration is part of the task. Create a bounded exploration stage with named candidates and a selection gate. Fixed diagnostic cameras are useful, while production cameras must remain animatable and revisable under version control.

Evidence: [writing-asset-plans/SKILL.md](./dcc-skills/writing-asset-plans/SKILL.md), especially lines 24–42, 61–71 and 79–117.

### Assert first modeling

Use **expected RED for new deliverables, and a baseline for edits**. A genuinely new deliverable's existence/identity check must fail for the expected reason before construction, accompanied by substantive acceptance criteria. Existing constraints may already pass and should continue to pass. Forcing them to fail would add work or encourage artificial tests.

Validate the validators using known failing fixtures. Do not require the artist's actual scene to be deliberately broken just to produce RED evidence. For visual exploration, use comparison rubrics and preserved candidates; geometry counts cannot specify beauty or expressive timing.

Evidence: [assert-first-modeling/SKILL.md](./dcc-skills/assert-first-modeling/SKILL.md), lines 13–18, 64–80 and 84. The rule that every measurement warning must be fixed also needs a task-specific applicability policy.

### Asset driven development

Keep the concise worker reports, explicit ownership, bounded repair loops and whole-environment review. Make fresh context and independent review available at meaningful boundaries rather than mandatory for every small edit. Share the exact relevant source recipe and artifact versions so a new worker refines the existing result.

Replace the text ledger as scheduler authority, make native checkpoints mandatory at durable boundaries, and retain evidence. Scope parallel work to separate owned processes or immutable inputs. Convert blanket stopping rules into recorded project permissions and budgets so authorized unattended work can continue.

The skill references `re-review-prompt.md` at line 52, but that file is absent from the supplied folder. The assertion, history and mode APIs also have no implementation here. Resolve these dependencies before calling the skill package executable.

Evidence: [asset-driven-development/SKILL.md](./dcc-skills/asset-driven-development/SKILL.md), lines 20–30, 43–64 and 66–72; [implementer prompt](./dcc-skills/asset-driven-development/implementer-prompt.md), lines 23–34 and 75–79.

### Task reviewer

A concise review packet is a good default. It should be produced by the execution and evidence services, not solely by the builder's prose. Give reviewers read-only access to the pinned native checkpoint and allow targeted independent checks when a report is incomplete or a risk crosses the task boundary.

Technical review checks contract compliance. Art-direction review should also evaluate composition, cohesion and material relationships against a style specification. The supplied “do not critique aesthetics the spec doesn't constrain” rule is reasonable only if the system actually has that style specification and a separate creative review stage.

Evidence: [task-reviewer-prompt.md](./dcc-skills/asset-driven-development/task-reviewer-prompt.md), lines 20–38 and 41–61.

### Verification before completion

Keep the claims-to-evidence discipline. Replace “run in this message” with **valid for the current artifact and dependency versions**. An unchanged expensive render remains valid across a chat boundary; a fresh check against the wrong scene is still invalid.

Separate technical completion, visual acceptance and production qualification. Rerun affected checks after scoped changes and perform full checks at release boundaries. Export verification must include the actual destination application when cross-DCC compatibility is claimed.

Evidence: [verification-before-completion-dcc/SKILL.md](./dcc-skills/verification-before-completion-dcc/SKILL.md), lines 13–27 and 33–45.

## Recommended disposition

Preserve the supplied documents as research inputs. Adapt three practical trial skills immediately around existing tools and the minimum native helper. Do not wait for a generalized API or registry. Their first comparison should test artistic quality, controlled revision and whether executable measurement adds value beyond instructions.

Use saved checkpoints and context replacement in the first creative comparison. Fault-injected unattended recovery follows only after the workflow demonstrates useful output. The active plan defines those gates.
