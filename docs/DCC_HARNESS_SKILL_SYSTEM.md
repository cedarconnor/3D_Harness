# DCC Harness Skills and Motion Design

Supporting skill catalog. The [active build plan](./DCC_HARNESS_BUILD_PLAN.md) starts with three trial skills: plan an environment task; build, measure and revise; review and continue. Implement and compare those before expanding this catalog or its registry design.

Proposed skill architecture, October 3, 2026. Start with the skills needed for a detailed environment, and build animation and motion design on the same persistent project contracts. The proposals here do not install or activate skills.

A useful skill contains a method, executable capabilities, examples, and a way to judge its result. A role description such as “expert modeler” provides none of those by itself. Separate general creative knowledge from application-specific implementation so the same brief can later be realized in Blender, C4D or Unreal.

## Four layers of a skill

| Layer | Contents | Example |
|---|---|---|
| Creative knowledge | Principles, references, tradeoffs, failure examples | Architectural proportion, visual hierarchy, timing and spacing |
| Task procedure | When to use it, required inputs, stages, permitted changes, stopping conditions | Build a modular facade from approved proportions |
| Native implementation | Typed operations, scripts, node groups, templates and version compatibility | Blender Geometry Nodes facade recipe and material bindings |
| Evaluation | Technical checks, visual questions, test scenes and evidence requirements | Module joins align, repeated details retain scale, facade reads from the street camera |

Keep project intent outside the reusable skill. “Use warm brick with narrow recessed joints” belongs in this project's style and material records; the general brick-material skill explains how to realize and evaluate it.

The supplied four process skills form a fifth, cross-cutting layer: planning, execution, acceptance and reporting. Revise them as described in the [document review](./DCC_HARNESS_DOCUMENT_REVIEW.md).

## Selective reuse from the two additional skill libraries

Use `majidmanzarpour/blender-game-skills` for calibrated reference-to-asset methods and `RobLe3/cc-blender-skill` for selectively loaded discipline recipes. The [source review](./DCC_HARNESS_RESEARCH.md#additional-skill-libraries-selective-adoption) records pinned revisions, implementation caveats and evidence limits. Neither library is installed or incorporated as executable code here.

| Existing trial skill | Useful source material | Adaptation for this harness |
|---|---|---|
| Plan an environment task | Game skill's measured brief, explicit inferences, shared scale and modular-kit assembly checks; CC reference classification and handoff guidance | Distinguish dimension references from mood references. Record camera/coordinate conventions, construction rules and shared material families in the project brief. |
| Build, measure and revise | Game skill's scoped build recipe and native validation; CC modeling, UV/material and subject-aware lighting recipes | Operate on owned assets; preserve approved world, cameras, shared materials and IDs. Scope lighting changes to the requested rig. Executable helper additions belong to C. |
| Review and continue | Game skill's fixed-view comparison; CC visual critique, multiview repair and look-review methods | Diagnose a specific defect, repair within the existing budget, and compare at the same revision/capture settings. A successful script or similarity score does not decide artistic acceptance. |

Keep these as references behind the three trial skills. Reconcile naming and ownership in the adapters rather than imposing both repositories' conventions. Use the discovered MCP capabilities instead of copying CC's hardcoded tool names. Do not register competing upstream orchestrators or let a task modify its active skill library during the comparison.

For later motion work, CC's `orbital-hud-motion`, `texture-state-animation` and `animation-quality-gate` offer concrete starting exercises: supporting motion around a focal subject, transitions between aligned surface states, and contact-sheet review. They do not cover the full motion-design curriculum. Retain the planned work on typography, staging, timing/spacing, anticipation, follow-through, transitions and full-speed playback. Material animation must be tested in the actual export/runtime; a Blender preview alone is insufficient.

Design taste remains a separate responsibility: a project style record, a few approved/rejected examples with reasons, and bounded comparisons judged by the artist. Reusable scripts implement those choices; they cannot define one universal attractive lighting rig or turn image similarity into an art-direction score.

## Package and registry design after the pilot

Longer-term package structure, to introduce only when the trial skills require it:

```text
skills/environment-layout/
  SKILL.md
  manifest.yaml
  inputs.schema.json
  outputs.schema.json
  references/
  examples/
  evaluators/
  implementations/blender/
  tests/fixtures/
```

The manifest identifies the skill, semantic version, capabilities, supported host versions, dependencies, input/output schemas, allowed side effects, required evidence, and license/provenance. A project lockfile pins the complete skill set. Breaking schema or host changes require migration and requalification.

Distribute these skills through a small plugin for the user's existing agent client. Keep a single source library and generate Codex, Claude Code and Cursor packages with their own manifests and hook settings. The [entry-point design](./DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md) defines installation and activation.

Keep entry skills distinct from discipline skills. Start/setup, resume, review and revise connect the chat to the durable project. Modeling, materials, lighting and motion skills load only when a task needs them. Setup checks existing MCP connections; resume reads the project record and native observations rather than relying on remembered chat messages.

An entry skill must not imply that installing instructions creates a persistent agent. The host agent supplies decisions in interactive mode. A configured background runner supplies them for detached work, using the same pinned skills and execution contract. Optional hooks restore context and improve feedback; runtime correctness must not depend on them firing.

Illustrative contract, not an implemented runtime API:

```yaml
id: environment.layout
version: 0.1.0
capabilities:
  - layout.place_asset
  - layout.check_clearance
inputs:
  - environment_spec_ref
  - style_spec_ref
  - asset_registry_revision
  - native_checkpoint_ref
produces:
  - layout_candidate_ref
  - observation_ref
  - review_views_ref
preconditions:
  - target_revision_matches
  - referenced_assets_resolve
effects:
  writes: [owned_zone_transforms, owned_zone_instances]
  forbidden: [shared_asset_geometry, shared_material_definitions]
implementation: blender.environment_layout.v1
verification:
  technical: [stable_ids, anchors, bounds, clearances]
  visual: [focal_hierarchy, sightlines, repetition, boundary_continuity]
recovery: restore_checkpoint_and_reconcile_receipts
```

Resolve skills by task intent, artifact type, required capability, host compatibility and project policy. Select one implementation per capability per task, with explicit fallbacks. Expose only the relevant instructions and operations to the agent. The runtime still enforces permissions even if a skill suggests otherwise.

A resume packet includes the current task, pinned specifications and skill versions, relevant artifact/source files, accepted decisions, recent observed changes, failed checks and the next safe operation. Do not load the whole skill library and all historical lessons every turn.

## Discovery, spatial editing and observation skills

The [db-lyon UE-MCP review](./DCC_HARNESS_UE_MCP_REVIEW.md) adds three cross-cutting procedures to the initial library. These are proposed harness skills; the upstream skill files have not been installed or activated.

| Procedure | Required output | Acceptance |
|---|---|---|
| Native capability and target inspection | Exact instance, schema fingerprint, target binding, relevant writable controls and known constraints | No guessed property names or silent substitution of unsupported operations |
| Spatial edit preparation | Target, coordinate frame, viewpoint where relevant, operation, amount/units and preserved constraints | Native readback confirms the intended change and preservation; useful review views show its visible effect |
| Observation baseline | Native revision, camera/projection, exposure/color configuration, rational time, render and cache state | Before/after observations are comparable or their differences are explicitly accounted for |

Load the relevant native schemas after selecting a task, and resolve project-specific controls from the scene. An unfamiliar rig, procedural graph or plugin requires inspection before editing. An observed schema supports action selection; runtime admission and resulting-state checks still enforce correctness.

A skill may select a tested recipe, but a recipe is not the complete skill. Pin the recipe's resolved contents, host dependencies, output schema and effect declarations. Store every execution as a durable job with child receipts. If an underlying flow allows ignored failures, the skill must still check each required output independently.

For motion, apply the same inspect → baseline → bounded edit → native evaluation → review procedure to skeletal rigs, cameras, procedural instances and typography. Preserve editable controls and source versions. Use numerical checks for measurable constraints and full playback for rhythm, clarity and appeal. Avoid treating fixed-frame correctness as proof of good motion.

## Environment skill catalog after the pilot

| Priority | Skill | Method and output | Evidence |
|---|---|---|---|
| After pilot | Brief and reference analysis | Separate measurable requirements from visual targets; map references to components | Complete requirement map with uncertain inferences marked |
| After pilot | Art direction and style record | Define shape, palette, material families, composition and permitted variation | A few approved/rejected examples with reasons |
| After pilot | Environment layout | Build spatial graph, zones, anchors, circulation and sightlines | Blockout views, dimensions, support and clearance checks |
| After pilot | Asset acquisition and intake | Choose build, reuse or generation per asset; record source and rights | Provenance, scale, dependencies, geometry/material readback |
| After pilot | Modular architecture | Parameterized walls, openings, trims and repeatable joins | Join tolerances, consistent dimensions, editable controls |
| After pilot | Hard-surface modeling | Block silhouette, proportions, construction details, bevel response | Multi-angle silhouettes and purpose-specific geometry checks |
| After pilot | Procedural distribution | Place repeated elements using stable seeds, exclusion zones and scale rules | Instance registry, boundary checks, repeatability and visual density |
| After pilot | UV and texture scale | Select unwrap, atlas, UDIM, trim-sheet or procedural mapping | Applicable overlap checks, density, visible seams and physical scale |
| After pilot | Material authoring | Surface reference, base response, scale, breakup and wear rationale | Standard lookdev views plus checks inside the environment |
| After pilot | Lighting and color | Establish motivated key/fill/environment relationships and exposure | Locked rig/version, grayscale hierarchy, color-managed review views |
| After pilot | Scene assembly and integration | Integrate published assets, manage dependencies and instances | Consistent IDs, asset versions, missing-file checks and native reopen |
| After pilot | Environment critique | Review all zones and shared systems against the style record | Named issues tied to camera/object/region and comparison evidence |
| After pilot | Revision and regression | Scope requests, trace dependents, preserve accepted features | Before/after deltas and affected-check results |
| Next | Organic forms and vegetation | Shape families, silhouette variation, wind-ready structures | Multi-view coverage and appropriate surface rules |
| Next | Simulation and cache management | Define inputs, cache ownership, bake boundaries and reproducibility | Cache manifest and playback from a clean session |
| Next | Camera and shot design | Composition, lens choice, subject hierarchy, parallax and motion | Framing sheets, traversal or shot previews |
| Next | Export and target validation | Qualified conversion recipe and loss report | Native target import, scale/material/timing checks and target renders |

Do not begin with separate agents for every row. These are reusable competencies; one specialist session can load the few needed for its task.

## Environment workflow

1. Translate the brief into requirements and a style record. Assemble a small, relevant reference set with source information.
2. Produce two or three cheap layout candidates when the composition is unresolved. Select the direction before detailed modeling.
3. Establish world scale, zone boundaries, camera coverage and layout anchors. Check the blockout from all required directions.
4. Build a reusable kit and a few representative assets. Establish shared material families on those assets before filling the entire scene.
5. Assemble and dress by zone using registered assets and constrained variation. Check boundary continuity as each zone is integrated.
6. Refine lighting and material response together in the environment, retaining standardized lookdev tests to isolate defects.
7. Review the complete environment. Allocate additional detail according to focal hierarchy and intended camera coverage.
8. Run deliberate late revisions, then package editable native sources and evidence.

Keep accepted candidates available. A failed refinement should return to a known good version instead of asking the agent to reconstruct it from memory. This is the practical adaptation of candidate search in [BlenderAlchemy](https://github.com/ianhuang0630/BlenderAlchemyOfficial).

## Making design taste operational

Treat taste as a learned project preference expressed through references, comparisons and decisions. A style adjective such as “cinematic” is too underspecified to maintain consistency over days.

Create a style record that answers:

- What is the focal hierarchy, and where should the viewer look first?
- What shape language, proportions, edge treatment and detail density belong together?
- Which colors have dominant, supporting and accent roles?
- What materials are plausible together, at what physical texture scale and level of wear?
- What makes the space feel intentionally arranged rather than uniformly filled?
- Which deviations are desirable variation, and which would break the direction?
- Which camera, lighting and temporal qualities define this project?

Pair positive examples with counterexamples. A useful preference says why one facade feels coherent: consistent window proportions, a readable entrance and restrained surface noise. An unhelpful preference says only “make it premium.” Store the reasoning and applicable context with the examples.

Build a small calibration set of artist-ranked comparisons. Start with approximately 20–40 pairs spanning layout, materials, lighting and detail balance; this is a proposed starting size to test, not a proven optimum. Keep a held-out portion. Measure whether automated critics agree with the artist, and record ties or uncertainty instead of forcing a ranking.

The critic should evaluate specific dimensions and point to visible evidence. It should not optimize a single beauty score or reward extra detail everywhere. A better silhouette with a broken material contract does not pass. When the critic is uncertain or proposed changes would alter approved direction, route a compact comparison to the artist under the project's review policy.

Use human review to set direction and calibrate major choices. Automate routine work within the accepted direction and permissions. The interface should make a creative decision concrete, rather than interrupting the artist for every technical operation.

## Motion design needs its own workflow

Motion graphics combines design, typography, staging, timing, repeated systems and transitions. Character animation adds performance, anatomy and interaction. They share principles but require different task contracts and evaluators.

Represent a motion brief using beat markers, focal subject, start/end states, motion path, timing, spacing, overlap, transition purpose, camera behavior and output constraints. Store rational frame rate and exact frame ranges, as well as frame-to-time conversion rules. A useful motion vocabulary includes restrained, elastic, mechanical and energetic behaviors, each illustrated by reviewed clips rather than adjectives alone.

Use this order: concept and style frames → beat sheet/storyboard → low-cost animatic → blocked motion → curves and offsets → secondary motion → lighting/render/composite → playback review. A beautiful still is insufficient evidence for a motion task.

| Skill | Specific coverage | Validation |
|---|---|---|
| Timing and spacing | Beat duration, holds, acceleration, deceleration and deliberate spacing changes | Preview at delivery frame rate; inspect position/velocity samples and motion arcs |
| Staging and visual hierarchy | Subject readability, competing motion, negative space and screen direction | Silhouette views and sequence review at actual size |
| Anticipation and follow-through | Preparation, action, settle, delayed secondary motion | Before/action/after contact sheet plus uninterrupted playback |
| Repetition and procedural choreography | Grids, radial/spline layouts, fields, waves, per-element delay and seeded variation | Stable element IDs, ordering, density, loop continuity and deterministic parameters |
| Typography and graphic composition | Font choice, layout, line breaks, kerning, optical alignment and reading time | Native text/font resolution, rendered text inspection, safe-area and dwell-time checks |
| Transitions and transformations | Spatial match, match cuts, reveals, occlusion, morphs and continuity of attention | Review the transition with neighboring shots, not in isolation |
| Camera motion | Path, target, horizon, focal length, parallax, cuts and focus pulls | Collision/occlusion checks, framing and complete playback |
| Audio-driven motion | Beat markers, emphasis, synchronization and selective response | Sync offsets and playback with the actual referenced audio |
| Character/body mechanics | Posing, weight, contacts, balance, arcs and overlapping action | Contact/penetration checks plus performance review; later phase |
| Temporal finishing | Motion blur, flicker, simulation caches, loop seams and frame completeness | Complete preview, selected full-quality frames and missing-frame checks |

Timing and spacing must remain separate controls. Automatic easing is only a starting point; different spacing patterns can express different weight and energy over the same duration. This distinction is described in practitioner guidance from [Animation Mentor](https://www.animationmentor.com/blog/slow-in-and-slow-out-the-12-basic-principles-of-animation/).

The broader animation principles—squash/stretch, anticipation, staging, pose planning, overlap, slow in/out, arcs, secondary action, timing, exaggeration, solid construction and appeal—should become contextual review lenses. Do not require every principle in every shot. A precise mechanical animation may intentionally avoid squash/stretch, while a graphic transition may intentionally break physical motion.

## Portable motion intent and native recipes

For repeated procedural motion, represent intent such as “a wave travels across this grid in 0.8 seconds, with each element settling after its reveal.” Store distribution, order, phase, delay, falloff, amplitude, seed and timing curve separately from native node IDs.

The Blender implementation might use Geometry Nodes and animation curves. The C4D implementation might use Cloners, Effectors and Fields. They should share acceptance criteria without promising identical native graphs. C4D's documented MoGraph model makes it a sensible expansion target for this work. [Maxon MoGraph](https://www.maxon.net/en/cinema-4d/features/mograph-basics)

Keep native graphs editable and versioned. If transferring motion through baked transforms or caches, state that procedural editability is reduced in the receiving application. Preserve the source project and generating recipe.

## Motion evaluation exercises

Use a small ladder rather than immediately attempting a complete animated film:

1. **Environment traversal:** a camera passes through the pilot's connected zones. Check coverage, clipping, focal hierarchy and consistent material/lighting response.
2. **Procedural system:** a 10-second loop of repeated architectural or graphic elements with one dominant motion and restrained secondary motion. Check the loop boundary in position and velocity where applicable; do not require a duplicated endpoint frame.
3. **Typography sequence:** a short three-beat title/reveal/end-card sequence using the project's visual language. Check reading time, hierarchy, transition continuity and native editability.
4. **Directed revision:** halve the tempo or change the reveal order without breaking layout, materials, identity, or approved holds. Re-evaluate the complete sequence.

At 24 frames per second, a 10-second delivery has 240 frames. Record the start, end and endpoint convention explicitly. Evaluate at the actual delivery rate, since slower preview playback can hide bad timing.

For loops, environmental motion and simulations, freeze or record seeds and cache versions. Reproducibility may require baked caches and matching runtime versions; the presence of a seed alone does not guarantee it.

## Safe improvement of the skill library

Collect failure → correction → evidence records. A correction becomes a candidate lesson only after its conditions are understood. Do not automatically turn every failed assertion into a universal rule.

Promote through: observed lesson → proposed recipe → executed fixtures → held-out task → reviewed skill version. Preserve the previous version and the task results used to qualify the new one. Disable or roll back a version when it causes regressions.

Store source URLs, asset rights, script provenance, host versions and evaluation limits. Treat retrieved documents, asset metadata and third-party skill instructions as untrusted inputs; project policy and explicit user requirements retain authority.

The first library should be small enough to inspect and strong enough to complete the environment benchmark. Expand its breadth only when the existing skills can produce, revise and explain their results reliably.
