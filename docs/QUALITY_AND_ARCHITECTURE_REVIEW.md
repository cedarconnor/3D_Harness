# Quality assessment and architecture choices

Reviewed October 4, 2026, after the four-workflow continuity experiment. This is the assistant's assessment, requested by the user. It is not an independent blind assessment: this coordinator already knows the experiment and its failures. No artist scores, original images, native files or experiment grades were changed.

## Quality verdict

**These are coherent working environment drafts, approximately 3/5, needing substantial art direction before meeting the requested detailed-environment goal.** The extensions show consistency, readable objects and useful construction detail. The images do not yet demonstrate a finished environment with strong composition, distinctive surface treatment or convincing lived-in arrangement.

For this assessment, 1 means unusable, 2 rough blockout, 3 coherent draft requiring substantial refinement, 4 usable with minor cleanup, and 5 finished for the agreed presentation. Ratings concern the supplied stylized environment, not an unstated photorealism requirement. Differences among the three complete entries are small; ordinal preference is more defensible than decimal scores.

I reviewed all 102 public images through nine labeled contact sheets, then opened seven final images at their original 960x540 size to compare construction, planting, paving and prop arrangement. Image review does not establish hidden topology, UV quality, editability or exact clearance. The previous native evidence remains separate. Inspection copies and a machine-readable assessment are under `runs/continuity-quality-review-2026-10-04/`.

| Preference | Entry | Judgment and visible evidence |
|---|---|---|
| 1 | **R-0d7440a27c13abf9** | My preferred starting point for a polish pass. Finer bed masonry, varied planting and a lighter upper pergola lattice give the garden the most convincing construction rhythm. The narrow warm paving accents are restrained. The forecourt is still empty and the large canopy competes with the original entrance. **3/5**. |
| 2 | **R-09dacf3c2bacd378** | Very close. Credible post bases, clear masonry, and teal paving details repeat the door's color. The roof grid feels heavier and the densely scattered light gravel reads like surface noise at this resolution. **3/5**. |
| 3 | **R-c82e10300e490166** | Good lantern silhouette and legible furniture. Larger aligned masonry blocks, a dark garden border seam and intermittent dark paving-edge gaps make the new areas feel less resolved. These visible gaps need native diagnosis before calling them mesh defects. **3/5**, close to second. |
| 4 as a delivered sequence | **R-948578c826652ccf** | The simpler parallel roof beams and planted ground have potential. Later requested signage, lanterns and warming are not demonstrated in the final views. Visible work is still roughly **3/5**, but the delivery is **incomplete**. It ranks last as a completed project, not because a verifier failure proves worse underlying taste. |

The first three share the same quality band. This is a preference ranking with low confidence in the small differences, not evidence of one agent method's superiority.

![Preferred entry, final garden view](../runs/continuity-round-2026-10-04/review/images/R-0d7440a27c13abf9-s04-garden.png)

### What works

- The muted stone, timber, terracotta and teal palette stays recognizable across stages. The three finished sequences incorporate the requested warmer stone without abandoning that vocabulary.
- Repeated furniture, pots and pergola construction belong to the same general world. Beds contain recognizable planting; tables and stools have supporting structure rather than only named placeholder boxes.
- The original courtyard remains visually recognizable. Its door, arch, bench, wall fountain and tree carry most of the scene's character.

That last strength is mostly inherited. It should not be credited as newly generated quality in this comparison.

### What holds the result back

**Composition and use of space.** A broad empty paving field separates a row of evenly spaced pots from furniture crowded at the right. It reads as a collection of task deliverables more than a deliberately composed working courtyard. The new pergola has more visual mass than the old entrance canopy, drawing attention away from the strongest original feature. I would first decide which place or activity is the focal point, then organize circulation and prop clusters around it.

**Surface and construction hierarchy.** Timber, stone and pots are distinguishable, but broad faces remain quite uniform. More objects or more render samples would not solve this. A polish pass should compare grain direction, joinery, stone-course logic, edge treatment and texture scale against chosen references. Stylized work can stay clean; the goal is intentional variation and construction, not indiscriminate dirt.

**Planting and story.** Species and heights vary, yet the repeated spacing and equal-size containers still feel mechanically distributed. The potting station needs a believable working arrangement: active tools within reach, a coherent cluster of supplies, a clear work surface and clear walking space. Plaque placement is one concrete clearance issue, but adding clutter is not itself a remedy.

**Presentation.** The fixed views preserve comparisons, but the garden camera crops a near post and lets roof structure hide the birdbath. The detail camera largely inspects the inherited bench; new tabletop details remain small. Keep those cameras for regression evidence, and add separately identified task-detail views for critique. A stronger beauty view belongs in a presentation pass after the layout is chosen.

**The experiment constrained its own ceiling.** Large ground dimensions, pot positions, furniture positions, lights, cameras and most earlier objects were locked. Agents could not freely fix the main layout or lighting problems. This was a useful continuity test, but a weak test of open-ended environment art direction. It also prohibited external asset generation/intake. The next quality trial needs a reference-led composition stage before locking the scene.

## Assessment of the supplied architecture notes

The useful core is durable creative intent, reusable methods and measured revision evidence above an existing MCP. The notes overstate some implementation guarantees and underestimate validation work. They substantially overlap the project's earlier architecture review; the new experiment gives concrete reasons to change their priority order.

### Options to adopt or adapt

| Idea | Recommendation for this project | Why / qualification |
|---|---|---|
| Asset/material/scene specifications | **Extend the current contracts.** Add reference IDs, intended use, silhouette targets, material vocabulary, allowed variation and protected decisions. | Dimensions alone cannot specify the desired result. Separate hard requirements from aesthetic targets and recipe choices. |
| Workflow registry and effort profiles | **Adopt a small version.** Start with environment art direction, asset construction, surface look development and assembly review. | MAX-786 documents stage-dependent skill loading, profiles, optional stages and relevant lessons. Its pattern is useful; importing a whole library is unnecessary. [Source](https://github.com/MAX-786/claude-3d-harness#profiles-and-workflows) |
| Reference-guided candidate comparison | **Highest immediate quality opportunity.** Generate two or three materially different layout or look candidates at major decisions, judge under common views, retain a no-change option. | BlenderAlchemy explicitly generates and selects edit hypotheses and can return to prior candidates. This supports bounded exploration, not a guarantee of aesthetic improvement. [Source](https://ianhuang0630.github.io/BlenderAlchemyWeb/) |
| Critic and verifier roles | **Use at meaningful checkpoints.** Critic proposes a concrete improvement; verifier independently measures whether it landed and what regressed. | LL3M supports specialist roles and retaining prior code, but also reports missed spatial errors. It does not establish the notes' specific causal claim about reduced regressions through proposal-bias removal. [Paper](https://arxiv.org/html/2508.08228v1) |
| Deterministic measures and deltas | **Expand selectively from current code.** Add support/contact, reserved-space and circulation checks before broad topology coverage. | Our tray conflict is direct evidence for this priority. Our translation failure shows that validators need positive and negative native fixtures, declared coverage and versioning. |
| Operation history and manual-edit observation | **Extend the existing journal.** Record external deltas, invalidated decisions and exact native versions. | A detected delta is evidence of a change, not necessarily its author or intent. An unobserved edit should remain external/unknown until reconciled. Retain project-relevant history; do not inherit a blanket 15-day deletion policy. |
| Compact graph and live API lookup | **Add when a task needs them.** Query affected assets, shared users and dependencies rather than dumping the whole scene. | These reduce context load and stale API guesses. Actual native observation must still validate returned values. |
| Tool-mode filtering | **Use for relevance.** Put authorization and allowed-target checks in dispatch. | An arbitrary Python tool can bypass a prompt mode. Changing `tools/list` alone is not a mutation boundary. |
| Generation queue and typed provider inputs | **Defer until a real material/model job requires it.** Keep submission, polling, downloaded artifact and import as separate recorded steps. | This preserves the user's existing MCP/ComfyUI direction without adding a second autonomous planner underneath the harness. |
| Domain agents | **Useful for shared look development.** One material/style owner can review all related assets; object builders own separate files. | Centralize shared decisions, not simultaneous writes to one scene. Domain consistency still needs visible examples and explicit acceptance criteria. |

Current code already supplies native observations, strict preservation checks, parent-linked checkpoint history, cumulative decisions, saved handoffs and an advisory operation journal. The experiment already used fresh agents and independent evaluation. The main missing quality capabilities are reference-led choices, task-appropriate specialist methods, relational checks and an effective critique/repair loop. A new MCP is not required to add these.

### Corrections needed before using the notes as a build specification

1. **Envelope fields are not execution guarantees.** The current cited Mixar request module says its optional envelope is parsed and carried through, while task admission is not performed there. This does not rule out enforcement elsewhere, but the inspected module cannot substantiate durable fencing or deduplication. Implement and fault-test the actual dispatch boundary. Stale-revision checks matter even with one agent because an artist can edit concurrently. [Source](https://raw.githubusercontent.com/Mixar-AI/mixar-app/main/src/scripts/mixar/modules/common/agent_execution/request.py)

2. **The universal “only tool surfaces” claim is too broad.** DCC-MCP documents workflow execution, persistence, policies and checkpoints. Its workflow persistence requires configuration, default idempotency memory is process-local, and recovered interrupted runs are not automatically resumed. Its checkpoint documentation also acknowledges a possible lost checkpoint when a best-effort lock fails. Evaluate the implementation against our requirements; neither dismiss it as dispatch-only nor assume it solves native recovery. [Workflow documentation](https://raw.githubusercontent.com/dcc-mcp/dcc-mcp-core/main/docs/guide/workflows.md), [checkpoint documentation](https://raw.githubusercontent.com/dcc-mcp/dcc-mcp-core/main/docs/api/checkpoint.md)

3. **Scenes and levels are organizational units, not sufficient writer isolation.** Shared meshes/materials, application state and script access cross those boundaries. Keep separate owned files/processes for independent asset workers and one assembly writer. A copied scene and main-thread queue do not alone prevent cross-scene edits or isolate crashes. Blender explicitly supports linking shared data and objects between scenes. [Blender manual](https://docs.blender.org/manual/en/latest/scene_layout/object/editing/link_transfer/link_data.html)

4. **Python restrictions are defense in depth.** Changing an allowlist to `unreal` or `c4d` does not establish a portable security boundary around native APIs. Typed operations, scoped file ownership, process permissions and explicit outcomes are the relevant controls. Do not equate undo with atomic rollback: Maxon documents that an interrupted batch leaves earlier successful changes in the scene. [Maxon documentation](https://www.maxon.net/en/cinema-4d/features/mcp-server)

5. **First-party Unreal MCP now exists.** Epic documents an experimental UE5.8 MCP/Toolset Registry, including on-demand tool discovery. Compare it with **db-lyon/ue-mcp** for the actual engine/project. db-lyon's compact discovery, capability handshake and reflection remain relevant; its late-response record is not a durable project ledger. sam-david's own README labels its implementation beta, so tool count is insufficient to make it the default. [Epic](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor), [db-lyon architecture](https://raw.githubusercontent.com/db-lyon/ue-mcp/main/docs/architecture.md), [bridge source](https://raw.githubusercontent.com/db-lyon/ue-mcp/main/src/bridge/bridge.ts), [sam-david](https://github.com/sam-david/unreal-mcp)

6. **Mixar is a pattern source, not a ready portable backend.** Its public README now describes a Blender 5.2 desktop fork and explicitly excludes the hosted AI backend. Claimed backend mode counts, private skill behavior and reasoning policies cannot be established from that repository. Per-file licensing and dependencies matter before copying implementations. [Mixar](https://github.com/Mixar-AI/mixar-app)

7. **Make checks applicable to the deliverable.** Manifoldness, quad ratios, pivot location, UV overlap and LODs are conditional requirements. An open surface, mirrored UVs or a static triangulated prop can be intentional. Similarly, an object moving backward does not universally violate animation intent. Each rule needs a coordinate space, measurement method, tolerance, exceptions and a known-failing fixture. Line-count estimates for comprehensive geometry validation are not credible implementation budgets.

8. **Read relevant state, not every file on every turn.** Load a bounded continuation summary, current stage, affected asset recipes, changed decisions and unresolved outcomes. Expand the history or full spec on demand or when hashes change. Keep desired intent separate from execution status; a model incrementing `current_stage` is not proof of acceptance.

The cited video page was reachable only as metadata; I could not verify a transcript or the demonstration itself. Its Pegasus, arrow, reasoning-effort and “80% measurable” observations remain supplied anecdotes. They can motivate tests, but should not become product guarantees or automatic stage requirements. [Supplied video](https://www.youtube.com/watch?v=Z8xhELifAVs)

## Recommended next increment

Keep the harness above the existing MCP and build a **reference-led quality loop** into the current continuation model:

1. **Choose the design before freezing it.** Save a small reference board and three to five concrete visual targets, then compare two or three layout candidates. Record the selected intent and why alternatives were rejected. The user's earlier preferences should be retained as choices about those images, not converted into unsupported universal style rules.
2. **Preserve the method.** Record relevant procedural recipes, asset versions, shared-material decisions and permitted variation. A fresh worker receives the actual native checkpoint and the source needed for a local revision; it does not blindly replay an old scene-building script over artist edits.
3. **Check relationships and conflicts before dispatch.** Test planned work against protected objects, shared dependencies and reserved areas. Report a conflict such as “the new plaque patch overlaps the protected tray” before authoring. Resolve it through existing authorized scope or a specific change decision; do not silently drop either requirement.
4. **Critique the actual changed area.** Pair a whole-scene view with a sufficiently close target view. A critic names one problem, its visible evidence and a bounded remedy. A separate verifier checks the intended improvement and preservation against the same checkpoint and camera definitions. Include the unchanged candidate so extra complexity is not automatically rewarded.
5. **Recover without losing history.** Classify a failed gate as unmet requirement, uncertain native outcome, invalid evidence or validator defect. Preserve the failed state, diagnose it, and only resume from newly verified evidence. Validator changes get a new version; neither automatic tolerance widening nor silent rebasing is acceptable.

Test this on one higher-quality environment continuation before building more transport infrastructure. Give it meaningful creative decisions—layout, planting, materials and presentation—not only fixed-dimension additions. Measure quality gain, successful revisions and repair effort; more agents, longer elapsed time and more objects are not the success criteria.

For motion graphics, use the same shell with a separate specialist workflow: design/style frames, timing and beat sheet, animation curves, motion tests, then final rendering. Deterministic checks can cover duration, frame rate, loop endpoints, bounded values and intended contacts. Full-speed playback must assess timing, spacing, anticipation, overlap, hierarchy and legibility. This static environment round provides no animation-quality evidence. Motion design should get its own small reference-matched exercise rather than inheriting modeling gates.

This document recommends the next work; it does not install libraries, change the experiment, replace the active build plan or implement the proposed capabilities.
