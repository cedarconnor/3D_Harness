# G: Generation quality plan

Drafted November 14, 2026, for [build-plan](../BUILD_PLAN.md) items G1–G8. Status: draft, not started. It follows the owner's [retirement of the investment gate](../DESIGN_DECISIONS.md#investment-gate-retired--november-14-2026) and a review of this repository and eight external ones.

## Goal

Make a harness-assisted session produce better 3D than plain Blender MCP, while keeping continuity across context sessions as the default.

Today about 770 of the package's 13,900 lines help build geometry or materials. The rest records, verifies and governs. The runtime has no general geometry defect check, no cheap whole-asset review image, no build-against-spec check and no scored revision loop. This plan adds those four things and shortens what the agent must read before it starts.

## What stays, what freezes

| Area | Disposition |
|---|---|
| Continuity store, `brief`, `resume`, feedback notes, checkpoints | Stays in the default path. The owner's experience is that tracking across sessions helps. |
| `relations`, `uv-report`, `render`, `deliver-glb`, visibility | Stays. G3 and G4 sit beside them. |
| `blender-*` craft skills and their verify blocks | Stays. G1 routes to them sooner. |
| Managed execution and the live bridge | Stays, with no new features in this plan. Its rules leave the default entry skill (G1). |
| Add-on capabilities, v1/v2 and asynchronous recipes | Frozen (G8): fixes only until a real add-on is qualified through them. |
| Approval-gated mode and the owner channel | Stays as an option. `autonomous` is the documented default for a single-user setup. |
| Blind-trial and continuity-trial tooling | Moves out of the package (G8). |

## Order

G1 and G2 remove friction and come first. G3 and G4 are independent of each other and can run in parallel. G5 and G6 depend on G3 and G4. G7 is a trial, not a commitment. G8 can happen at any point.

```text
G1 ─┐
G2 ─┼─> G3 ─┐
    └─> G4 ─┼─> G5 ─> G6 ─> G7
G8 (any time)
```

Each item ships as its own version under the build plan's standing rules: source and installed suites, native positive and negative fixtures on Blender 5.1.1 and 5.2.1, a guide, a release report and a changelog entry.

## Items

### G1: Short default entry skill

`dcc-harness/SKILL.md` is about 1,500 words, most of it reservation, reconciliation, approval and add-on rules. Every session pays for that before any craft guidance.

- Cut the entry skill to roughly 400 words: run `brief`, follow its next steps, load one craft skill, build, run `audit` and the review sheet (once G3 and G4 exist), save a checkpoint, write the handoff.
- Move managed execution, live pairing, external revisions, adoption, learned checks and add-on effects into `references/` files that the skill names with one line each and a condition for reading them.
- Give each skill a word budget and add a source-suite test for it, for link resolution, and for every referenced command existing. This follows EL4CTEO/blender-skills' `validate_skills.py`.

**Done when:** the six P5 sealed failure situations still pass with the short skill, and a fresh agent on the 0.7.0 one-parameter revision task starts its edit no later than the recorded 51 seconds. One run each, reported as directional.

**Status, November 14:** implemented, unreleased. The entry skill is 502 words; the lint budget is 550, since the routing table and the seven standing rules did not fit in 400. All six P5 situations passed. The fresh agent reserved its edit at 57 seconds, so the 51-second criterion was missed by six seconds on one run ([results](../studies/P5_SKILL_REGRESSIONS.md#rerun-with-the-short-entry-skill-november-14)).

**Risk:** the P5 situations depend on rules that move to references. If one fails, restore that rule to the entry skill as a single sentence rather than restoring the section.

### G2: Coverage gaps instead of refusals

Whole-scene validation refuses material node groups, unsupported Geometry Nodes setups, empty material slots and missing textures, so one unrelated object can block a checkpoint. The README already names this as the next priority.

- Find each refusal in the observer and classify it: a real integrity problem (missing texture) or content the observer cannot yet describe (node group, unsupported Geometry Nodes tree, empty slot).
- For the second class, record the object with an opaque content hash and an explicit `coverage_gap` entry. Preservation contracts can then still detect that it changed, without describing how.
- A stage can complete with coverage gaps listed in its evidence. Missing textures and non-finite coordinates keep refusing.

**Status, November 14:** implemented, unreleased. The fixture observes `READY` with two gaps, not three: 0.24.0 already measures nested shader groups in full, so that case needed no gap and changing the group fails a contract through the material's own record. Shader graphs past the reader's limits or with animation still refuse, because nothing below the limit is recorded to hash. The gap records are an optional `coverage.gaps` key, present only when a scene has such content, following the collection-instances precedent. Passed natively on Blender 5.1.1 and 5.2.1 ([guide](../guides/EVERYDAY_WORKFLOW.md#coverage-gaps)).

**Done when:** a fixture scene with a nested shader group, a scatter Geometry Nodes tree and an empty slot observes `READY` with three listed gaps; changing the node group fails a preservation contract; older observations still read. This changes the observation format, so it needs a new coverage version, never an in-place change.

### G3: `audit` command

A read-only geometry defect check on a saved file, in the style of `uv-report`.

- Checks: flipped or inward faces, non-manifold edges where the profile expects closed meshes, coincident and back-to-back faces (z-fighting), floating islands not touching anything, unapplied or negative scale, zero-area faces, faces on empty material slots, data maps tagged sRGB, image textures without UVs.
- Profiles `render`, `game` and `print` set each check to error, warning or skip. Foliage cards and intentionally open surfaces are why `render` does not require closed meshes.
- Tolerances scale with the asset's bounding diagonal. Output is one JSON report with stable issue codes, object IDs, a cause and a suggested fix per finding. The process exits non-zero on an error.
- Evidence classes reuse the existing `relations` vocabulary, so a bounds-only estimate permits inspection, not repair.

Sources for the idea: `bx_audit.deliverable` in scenario-labs/skills and `qa_check.py` in EL4CTEO/blender-skills. Both are MIT. Reimplement against this project's observer and identities rather than copying; record both in `THIRD_PARTY_NOTICES.md` if any code is adapted.

**Status, November 15:** implemented, unreleased. Eighteen native fixtures each report their own code alone and the control reports nothing, on Blender 5.1.1 and 5.2.1 ([guide](../guides/AUDIT.md)). Differences from the list above: unapplied scale is three codes (uniform, non-uniform, negative); a coplanar overlap between objects of the same materials is a warning, since it does not show; and tolerances are capped at 0.5 mm and 5 mm so a whole scene is not judged loosely. The garden does not pass under `render`: it has 522 errors, reviewed as real (519 parts built inside out, three coincident pairs), so there is no false error but also no clean run. No code was adapted from the two source repositories.

**Done when:** one native fixture per check fails on that check alone and a clean control passes; the production garden runs without a false error under `render`; the report binds to the file hash like `uv-report`.

### G4: Contact-sheet review renders

Fixed review cameras show the scene as composed. They do not show a single asset from all sides, or its topology.

- `review-sheet SAVED.blend --targets ID...` renders one image in a temporary scene, never saving the source: columns are four to six orbit views, rows are silhouette, clay with cavity, wireframe, and a backface pass that colours inward faces.
- A `random` colour mode gives each object its own colour so detached or duplicated parts stand out.
- Workbench only, about 1600 px wide, one image per call, with a receipt bound to the file hash. The size limit is there to protect the agent's context.

**Status, November 15:** implemented, unreleased. The qualification reads the sheet's pixels: the flipped face is red in the backface row, the detached block is a separate silhouette, repeat renders are byte-identical and the source hash is unchanged, on Blender 5.1.1 and 5.2.1 ([guide](../guides/REVIEW_SHEET.md)). Differences from the list above: the default is four views with `--views 6` adding top and bottom; `--color random` colours the clay row per object; and over 300,000 faces the wireframe row is left out.

**Done when:** a fixture with one flipped face and one detached part shows both in the sheet; repeat renders are byte-identical; the source file hash is unchanged.

### G5: Blockout spec and scene-against-spec check

This absorbs P16, which stays in the tracker under its own ID and points here.

- A versioned JSON schema for the planning stage: parts with a name, category, primitive, position, size, yaw and group, in metres with Z up; numeric proportions with tolerances; things that must never happen; review views.
- `spec-check` validates the spec alone, with clamped numbers and unknown fields as errors.
- `blockout-build` creates an owned, tagged collection with stable IDs, and refuses to rebuild a collection that has been edited.
- `spec-compare` measures a saved scene against the spec and fails closed on a missing measurement. Each finding carries a code, a path, a message and a remediation. `relations` runs on the built blockout.
- Add a short pitfalls section to `blender-python`: primitive `size` against `radius`, `scale=` at creation against `dimensions`, and primitives spawning at the 3D cursor. Each needs a verify block.

Sources for the idea: the blockout schema noted in the [Scenario review](../reference/SCENARIO_BLENDER_PLUGIN_REVIEW_2026-10-15.md), and dcc-mcp's `dcc-modeling-spec` and assembly-pitfalls skill (MIT).

**Status, November 15:** implemented, unreleased. Positive and negative native fixtures pass for all three commands on Blender 5.1.1 and 5.2.1 ([guide](../guides/BLOCKOUT_SPEC.md)). Differences from the list above: `position` is the centre of the base; parts carry `ids` so a detailed scene can be compared, and `rests_on` so the build writes a `relations` definition; never rules are three measurable kinds, with unmeasurable sentences kept under `avoid`; and a spec must satisfy its own rules. The potting-shed brief has no numbers, so its spec takes part sizes from checkpoint 9 and tests ten human-scale proportions and four never rules. Two door proportions failed at first; the owner judged the door right on November 15, the ranges were corrected, and checkpoint 9 passes.

**Done when:** positive and negative native fixtures pass for each command; the potting-shed brief is expressed as a spec and `spec-compare` passes on checkpoint 9 or reports defects a person agrees are real.

### G6: Target-led judge loop

A skill and a small record format, with no scheduler and no new agent runtime.

- **Target first.** Before building, fix what the result should look like: the reference images and visual targets `quality.py` already records, or a generated target image when the owner asks for one.
- **Rubric before generating.** Composition 0–3, lighting 0–3, materials 0–3, detail 0–1. Code checks come first: a round with an `audit` error or a failed `spec-compare` is not sent to the judge.
- **Fresh-context judge.** A separate agent sees the target, the current fixed views and review sheet, and the previous round's verdict. It returns a score and a list of specific gaps. Verdicts are stored as feedback notes, so they survive a context change.
- **Stall rule.** Less than one point gained across two rounds, or the same gap named twice, forces a change of approach. If that also fails, stop and ask. A hard cap of five rounds.
- **Attribution.** A judge score is an agent's opinion. It never substitutes for owner acceptance, and it is recorded that way.

Source for the idea: achimala/dream-loop (MIT), which is prompts only. The third-party report in its issue 6 found the judge names symptoms well and causes badly, which is why code checks gate each round here.

**Status, November 15:** implemented, unreleased. All three done-when parts are met on one run each ([guide](../guides/JUDGE_LOOP.md), [first run](../studies/JUDGE_LOOP_FIRST_RUN.md)). Differences from the list above: the loop record is its own append-only folder, and verdict gaps become feedback-note drafts only when the round names a published checkpoint, because a note must anchor to one; the round needs both fixed views and a review sheet; a default pass score of 9 adds a met-target stop; and gated rounds count toward the cap. The first run showed the repeated-gap rule forcing a change of approach after a three-point gain, which then ended the loop; the owner narrowed the rule on November 15 to a repeated gap with less than one point gained. The plain-MCP comparison under Measuring was not run.

**Done when:** on one held-out brief the loop runs to a stop condition with every round's score, gaps and evidence retained; a deliberately stalled fixture triggers the stall rule; a P5-style sealed packet shows a fresh agent resuming mid-loop from the notes alone.

### G7: Extension trials on Blender 5.2

Two bounded trials, each ending in a written keep-or-drop decision. Both tools are GPL-3.0, so they are used as installed extensions and driven through their public operators and API. No source is copied into this package.

- **geometry-script.** Requires Blender 5.2 or later, so it is unavailable on the qualified 5.1.1 runtime. Trial: five Geometry Nodes tasks from `blender-geometry-nodes`, each built once with raw `bpy` and once with the DSL by fresh agents. Compare first-attempt success, attempts to a valid tree, and tokens. Its `agent.run()` report (geometry counts, bounds, node warnings) is worth mirroring in our own verify step whichever way the trial goes.
- **StableGen.** Multi-view projection texturing through the local ComfyUI. Trial: texture the potting-shed pots and painted surfaces, the materials the realism review called too clean. Its generation operators are modal, so the agent must poll. Confirm its supported Blender versions first; the review found 5.0 listed as unsupported. Record VRAM and disk use.

**Status, November 15:** both trials run on Blender 5.2.1, each with a results document and a recommendation ([geometry-script](../studies/G7_GEOMETRY_SCRIPT_TRIAL.md), [StableGen](../studies/G7_STABLEGEN_TRIAL.md)). Differences from the list above: the geometry-script tasks turned out too easy to separate the arms, and its `agent.run()` report is described but not yet mirrored; the StableGen trial textured the pots only, not the painted surfaces. The owner decided on November 15: geometry-script is dropped as a dependency, and StableGen is kept as an optional, owner-run tool outside the default path.

**Done when:** each trial has a short results document under `docs/studies/` with the retained failures, and the build plan records the decision.

### G8: Freeze and trim

- State in the README and `ADDON_RECIPES.md` that add-on capabilities are frozen at 0.24.0 behaviour until a real third-party add-on is qualified through them.
- Move `blind.py`, `blind_review.py`, `continuity_trial.py`, `continuity_review.py` and `session_cost.py` from the package to `scripts/` or a separate `dcc_harness_trials` package. They are already excluded from the runtime digest, so pinned projects are unaffected. Update `dcc-blind-test` to match.
- Make `autonomous` the mode the quick reference shows first.

**Status, November 15:** implemented, unreleased. The trial modules are the `dcc_harness_trials` package and the source suite passes. The wheel, installed-suite and package-parity results were pending when this was committed.

**Done when:** the wheel no longer ships the trial modules, both suites pass, and the release gate's package-parity check passes.

## Not in this plan

- Unattended scheduling, a second DCC, client installers and motion workflows. The gate no longer blocks them, but none of them improves a single generated scene.
- Paid generation services. image-to-sculpt depends on fal.ai and is a week old; revisit if single-object image-to-mesh becomes a need.
- Adopting the dcc-mcp gateway or vork. The first is a heavy stack for one user; the second replaces Blender rather than driving it.

## Measuring whether it worked

The gate is retired, so this is a check on the plan, not a condition for continuing.

After G6, run one held-out brief twice: once with plain MCP and once with the harness, on Blender 5.2, with the same asset kit, cameras and budgets. Record `audit` errors at finish, judge score per round, rounds to stop, tokens and elapsed time. Keep both results whatever they show.

## Open questions for the owner

1. **Qualified Blender version.** G7 needs 5.2. Moving the primary qualification from 5.1.1 to 5.2 would simplify G3–G6 as well. The craft skills already pass on 5.2.1.
2. **Licence.** The package declares no licence of its own. That decides whether MIT code from the reviewed repositories can be adapted with attribution, and whether GPL code could ever be vendored.
3. **Generated target images in G6.** These would use ComfyUI locally or a hosted model. Local keeps the "no paid generation" rule from the creative-trial defaults.
