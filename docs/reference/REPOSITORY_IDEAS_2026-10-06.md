# Repository ideas for 3D Harness

Reviewed October 6, 2026. This is a source-based comparison and proposal, not an implementation or runtime qualification. All seven repositories were inspected beyond their READMEs; relevant source, tests and documentation were read. Upstream code was not installed or executed. The local comparison includes the working tree's uncommitted v0.5 feedback and environment-workflow changes, above Git HEAD `7d80939a7beabc4895c53355c5929f499fcc69bd`.

The most useful additions are better spatial evidence, recognition of ineffective repairs, clearer visual inspection, and qualification of exported deliverables. The existing checkpoint and feedback architecture is already a suitable foundation for these additions.

**What is already present locally**

- Stable asset/instance/material identities, saved observations, retained scripts, preservation contracts, checkpoint history and explicit unresolved native outcomes.
- Reference roles and visual targets, common whole/detail views, an unchanged comparison candidate, and separate critique/verification in [quality.py](../../dcc_harness/quality.py).
- Feedback anchored to checkpoints, objects, materials and image pins; implementation and verification are separate in [feedback.py](../../dcc_harness/feedback.py).
- Pinned skills, seven environment stages, stale-evidence handling and inherited evidence gaps in [environment_workflow.py](../../dcc_harness/environment_workflow.py).
- Shared mesh/material users and observed parent/image dependencies. These are different from a named design-input dependency graph.
- Native negative fixtures and fresh-context trials. The v0.5 qualification document still labels qualification in progress; this review does not change that status.

Consequently, generic advice to add stages, memory, reviewers, screenshots or checkpoints would mostly duplicate existing work. The following recommendations target specific gaps.

**Repository comparison**

| Repository and inspected commit | Most useful idea | Fit for this harness |
|---|---|---|
| [Superpowers](https://github.com/obra/superpowers/tree/8ca22dba9a94f28898bbce59f2537ff4d87c747d) — `8ca22db` | Test actual agent behavior under realistic pressure, separately from runtime unit tests. | High: turn known continuation failures into small repeatable skill evaluations. |
| [remesher](https://github.com/remesher/remesher/tree/30f1a95ca62935d0a6cb9d3b01c7b51b0a65f8aa) — `30f1a95` | Export a candidate, reimport it in isolation, validate, then publish. | High when delivering GLB or other interchange formats. Its generation/rigging stack is much more specialized. |
| [HarnessCAD](https://github.com/ReverseZoom2151/harnesscad/tree/c62b4e621438bc2b664930c1668bf808844aae30) — `c62b4e6` | Separate finding severity from evidence reliability; test exact feature locations and detector failure cases. | High: prevent speculative diagnostics from driving destructive scene repairs. |
| [dsh-cad](https://github.com/LAU-MARS/dsh-cad/tree/fa38ec56a58d97c3ecaa609f4d04118c87be2ba9) — `fa38ec5` | Named design inputs with explicit dependents and an inspectable edit impact. | Medium: useful for building footprints, paths, roof recipes and material families. |
| [CheshireJCat/blender](https://github.com/CheshireJCat/blender/tree/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02) — `19dec3c` | Registered reference views, contradiction reports and export validation profiles. | Medium: valuable for reconstruction and delivery, with substantial corrections needed in the inspected helpers. |
| [Manifest3D](https://github.com/scottstts/Manifest3D/tree/bca059c4ec06b7915b42efe761ba64784c0c2012) — `bca059c` | Group failures by stable object relationships and recognize repeated or opposing repairs. | High: adds persistent repair history beyond the current written retry ceiling. |
| [Astra Blender Harness](https://github.com/AleBrito124356/astra-blender-harness/tree/8363efaaa7330589ed4758d0f33e30ebc6f75098) — `8363efa` | Budgeted evaluated-geometry preview with incremental updates; sampled motion diagnostics. | Preview is useful for review usability; motion inspection belongs with a future animation workflow. |

**1. Explain the reliability of a finding before choosing a repair**

HarnessCAD implements evidence tiers and filters model-facing diagnostics through a common boundary. Its [soundness implementation](https://github.com/ReverseZoom2151/harnesscad/blob/c62b4e621438bc2b664930c1668bf808844aae30/src/harnesscad/eval/verifiers/soundness.py#L493-L610) distinguishes stronger observations from heuristic findings, while [agent feedback](https://github.com/ReverseZoom2151/harnesscad/blob/c62b4e621438bc2b664930c1668bf808844aae30/src/harnesscad/agents/agent/feedback.py#L1-L55) applies the distinction centrally.

For this harness, retain both the seriousness of a problem and how it was established. A useful finding record would include the requirement, stable target IDs, checkpoint, measurement method, scope, observed value, tolerance, evidence class and permitted next action. An AABB overlap can request closer inspection; it does not establish that two meshes intersect. An artist's composition instruction remains actionable as an attributed artistic decision.

This extends the existing feedback categories and observer coverage statements. It must not turn uncertain evidence into a pass, hide advisory findings, or downgrade a protected-object change.

First exercise: a valid architectural arch with overlapping component bounds. The broad-phase warning should survive in the report without causing the agent to move correctly placed geometry. A genuinely obstructed opening should still fail its qualified clearance check. Scope: small to medium.

**2. Check the relationship at the place where it matters**

HarnessCAD's [hard-corpus oracle](https://github.com/ReverseZoom2151/harnesscad/blob/c62b4e621438bc2b664930c1668bf808844aae30/src/harnesscad/eval/hardcorpus/oracle.py#L129-L197) probes material/void state at specified positions. Manifest3D's [contact check](https://github.com/scottstts/Manifest3D/blob/bca059c4ec06b7915b42efe761ba64784c0c2012/src/engine/validation/runPromptChecks.ts#L272-L355) separately bounds gap and penetration.

The useful DCC adaptation is a small set of explicit spatial witnesses: doorway clearance along the intended route, four bench feet supported by the declared ground, a downpipe meeting its gutter, or a required subject visible from the review camera. Each needs stable IDs, coordinate space, measurement method, tolerance and coverage limits. A whole-object dimension check cannot establish these relationships.

Start with one relation family. For example, two shed walls can have identical dimensions and opening counts while only one doorway aligns with the path. Check that location directly. Existing visibility and ground helpers supply starting points; generic watertightness is inappropriate for foliage cards and intentional open surfaces. Scope: medium for a narrow qualified collector, much larger for general collision/contact semantics.

**3. Remember failed strategies and recognize progress**

Manifest3D implements [failure clustering](https://github.com/scottstts/Manifest3D/blob/bca059c4ec06b7915b42efe761ba64784c0c2012/src/engine/agent/feedback/failureClusters.ts#L20), [candidate failure history](https://github.com/scottstts/Manifest3D/blob/bca059c4ec06b7915b42efe761ba64784c0c2012/src/engine/agent/session/candidateHistory.ts#L105) and [close/far repair hints](https://github.com/scottstts/Manifest3D/blob/bca059c4ec06b7915b42efe761ba64784c0c2012/src/engine/agent/loop/relationLoopHints.ts#L3).

The local review skill already limits repairs. The incremental value is preserving a normalized failure code, exact target pair, attempted strategy, measured error and parent checkpoint across contexts. A later agent could see that raising the bench solved penetration but caused a gap, and lowering the entire bench simply reversed the defect. It should choose a different bounded strategy or report the conflict.

Track numerical improvement separately from failure identity. Upstream cluster signatures omit magnitude, so an improving error can retain the same signature. Its close/far detector recognizes opposing failures in recent revisions, not necessarily strict alternation; its main loop also permits an unlimited default repair budget. These are patterns to refine, not evidence that convergence is solved.

First exercise: replay saved floating/penetrating bench failures, a steadily improving gap, and an unrelated second bench. Only ineffective repetition should trigger the warning. Scope: small to medium, with no new executor required.

**4. Make the changed scene easier to inspect**

Astra's [scene probe](https://github.com/AleBrito124356/astra-blender-harness/blob/8363efaaa7330589ed4758d0f33e30ebc6f75098/src/astra_blender/blender_scripts/scene_probe.py#L103-L221) extracts evaluated geometry, applies budgets and substitutes visible bounding-box proxies for overly dense objects. Its [live refresh](https://github.com/AleBrito124356/astra-blender-harness/blob/8363efaaa7330589ed4758d0f33e30ebc6f75098/src/astra_blender/live.py#L88-L108) sends geometry updates selectively.

Adapt this as an optional reviewer over immutable saved checkpoints. Show added, removed, moved and geometrically changed objects, with a selectable stable ID and a link to the corresponding feedback. Start with a static before/after viewer; incremental refresh is a later optimization. Existing image-pin feedback can remain the authoritative note format.

Reuse the local topology-aware SHA-256 observations. Astra's cache signature omits topology connectivity and material indices, so it can miss a same-count topology edit. Its simplified browser materials also cannot qualify Blender shading. Label proxy objects and unsupported domains explicitly.

First exercise: a scene with one moved object, one same-count topology change, one deletion and one dense proxy. Compare the preview against the reopened native checkpoints. Scope: medium to large; keep the UI and geometry producer outside the dependency-free core.

**5. Qualify the actual exported deliverable**

remesher's [_export_validate_and_promote](https://github.com/remesher/remesher/blob/30f1a95ca62935d0a6cb9d3b01c7b51b0a65f8aa/src/comfy_prompt_cli/workers/blender_auto_skin_worker.py#L277-L381) exports a unique GLB candidate, resets its isolated scene, reimports, and checks relevant rig/material/UV properties before promotion. Cheshire exposes [export validation](https://github.com/CheshireJCat/blender/blob/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02/index.js#L1059-L1103) with deliverable profiles.

Add a separate delivery receipt tying the accepted native checkpoint to exporter settings/version, output hash, importer version and round-trip observations. Begin with static GLB: scope checks to imported IDs, then verify nonempty geometry, units/world bounds, expected materials/textures, UVs and declared instance semantics. A successful native reopen already exists locally; this checks a different artifact.

The validation process must begin with an explicitly empty scene. Cheshire launches factory startup and imports without clearing its default objects; its default scene validation only requires some mesh. Source inspection therefore indicates that the factory cube could conceal an empty import. This was not reproduced at runtime. See [process launch](https://github.com/CheshireJCat/blender/blob/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02/index.js#L485-L508) and [import/validation code](https://github.com/CheshireJCat/blender/blob/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02/scripts/dsh_blender_driver.py#L387-L464).

First exercise: a textured prop passes; separate missing-texture, incorrect-scale and empty-geometry fixtures fail. The original native checkpoint stays byte-identical. Scope: medium for one static format. Blender-to-Blender round-trip success does not establish compatibility with Unreal or another destination; that destination needs its own import check.

**6. Preview the impact of changing a design input**

dsh-cad has [named sketch definitions](https://github.com/LAU-MARS/dsh-cad/blob/fa38ec56a58d97c3ecaa609f4d04118c87be2ba9/src/modeling/document.ts#L84-L97), [dependent lookup on edit](https://github.com/LAU-MARS/dsh-cad/blob/fa38ec56a58d97c3ecaa609f4d04118c87be2ba9/src/tools/cad-model.ts#L658-L667), and a [referenced-sketch deletion guard](https://github.com/LAU-MARS/dsh-cad/blob/fa38ec56a58d97c3ecaa609f4d04118c87be2ba9/src/tools/cad-model.ts#L755-L764). Its [test](https://github.com/LAU-MARS/dsh-cad/blob/fa38ec56a58d97c3ecaa609f4d04118c87be2ba9/test/sketch.test.ts#L160-L189) covers rebuilding an extrusion after a sketch edit while preserving body identity.

An advisory design-input manifest could express that the shed footprint drives walls, roof and gutter; a path curve drives paving and planting exclusions; a material recipe serves particular asset families. Before authoring, show affected stable IDs, shared users and required reviews.

The local registry already records several native dependencies. The new value is intentional recipe dependency and impact explanation. Do not automatically treat the graph as complete, carry old verification forward, or replay whole builders over artist edits. Keep native observations and current evidence requirements.

First exercise: widen a shed footprint, predict the affected parts, and verify the result while unrelated planting stays unchanged. Scope: medium for advisory records; safe parametric regeneration is a separate larger task.

**7. Test whether the skills change agent behavior**

Superpowers explicitly separates [runtime/plugin tests from live skill evaluations](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/docs/testing.md). Its [skill-testing method](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/writing-skills/testing-skills-with-subagents.md) compares behavior with and without a skill under realistic pressure.

Build a small regression packet collection around this harness's actual failures: lost acknowledgement, stale image, changed shared material, missing view definition, an artist's saved revision, and a late request conflicting with protected geometry. Grade observable actions and artifacts, such as whether the agent resumed, preserved the baseline, inspected the appropriate view and reconciled instead of redispatching. Merely restating the skill is not success.

The existing blind/fresh-context machinery is the right base; a new evaluation platform is unnecessary. Pair these behavior tests with native defect fixtures. HarnessCAD's [mutation algorithm](https://github.com/ReverseZoom2151/harnesscad/blob/c62b4e621438bc2b664930c1668bf808844aae30/src/harnesscad/eval/gates/mutation_score.py#L193-L250) offers a useful rule: a detector only gets credit for rejecting a genuinely activated defect when it accepts the correct baseline. Track false positives and surviving defects separately.

HarnessCAD's inspected mutation CLI falls back to a synthetic self-check when its real oracle loader is unavailable; this checkout lacks the imported oracle-fleet module. Its [fallback](https://github.com/ReverseZoom2151/harnesscad/blob/c62b4e621438bc2b664930c1668bf808844aae30/src/harnesscad/eval/gates/mutation_score.py#L299-L335) does not establish native qualification. Scope: small initial behavior suite plus bounded native fixture expansion.

**Useful later: registered references and temporal sampling**

For reconstruction, Cheshire's [shared-axis reference checks](https://github.com/CheshireJCat/blender/blob/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02/skills/create-3d-model/references/modules/multiview-constraint-solver/scripts/view_constraint_report.py#L6-L58) suggest a reference contract with projection, world scale, crop/registration, landmarks and uncertainty. The current scripts compare raw pixel dimensions and have schema mismatches; their [repair helper](https://github.com/CheshireJCat/blender/blob/19dec3cdd48368dd0d9865ac2072ea6f5f65cc02/skills/create-3d-model/references/modules/fit-repair-optimizer/scripts/fit_repair_queue.py#L28-L30) also compares different dimensional ratios as though they should match. Reimplement the narrow concept with calibrated views. Mood photographs should remain visual guidance.

For animation, Astra's [sampled motion collection](https://github.com/AleBrito124356/astra-blender-harness/blob/8363efaaa7330589ed4758d0f33e30ebc6f75098/src/astra_blender/blender_scripts/animation.py#L85-L183) and [summary](https://github.com/AleBrito124356/astra-blender-harness/blob/8363efaaa7330589ed4758d0f33e30ebc6f75098/src/astra_blender/motion.py#L116-L184) provide a bounded pattern for finding worst-frame gaps, overlaps and ground breaches. Explicit support/attachment IDs would improve its name-based heuristics. Sampling and bounding boxes do not prove continuous collision freedom, correct deformation or good motion.

**Recommended next increment**

For the current environment work, combine one qualified relationship check with persistent repair history and explicit evidence reliability. Use a supported bench-on-ground or doorway/path task, preserve an unchanged control, and run a fresh-context continuation. Measure correct problem identification, ineffective repair count, unintended changes, artist repair effort and elapsed work.

Add the behavior regression packets alongside that increment. Build the visual change viewer when review effort warrants a UI, and prioritize GLB round-trip validation when exported artist delivery becomes an actual requirement. Named recipe dependencies and calibrated multi-view reconstruction can follow demonstrated demand.

This recommendation preserves the project's creative investment gate: success means better accepted work or less repair effort. More orchestration, a larger skill library or additional checks alone would not demonstrate improvement. No runtime, skill, build-plan or scene changes were made by this review.
