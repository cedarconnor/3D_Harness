# 3D Harness Build Plan

Updated October 6, 2026, at version 0.5.0. **This is the active plan.** It owns sequencing, gates and trial budgets. [Design decisions](DESIGN_DECISIONS.md) own architecture, qualification reports own evidence, and the [changelog](../CHANGELOG.md) records what each version delivered. The [documentation index](README.md) lists every report.

This revision replaces the October 3 week-one plan, whose status notes had accumulated through version 0.5.0. That text is archived verbatim in [research/archive](../research/archive/DCC_HARNESS_BUILD_PLAN_v3_2026-10-06.txt); its experiment design remains the protocol record for the completed short comparison.

## Objective

Help an agent build and revise detailed environments while preserving assets, materials, lighting and project intent across long work sessions. The artist works in their normal Claude Code, Codex or Cursor chat. The harness runs above an existing Blender MCP or an owned background Blender process: it supplies project state, contracts and evidence, while the host agent supplies reasoning and tool calls.

The governing question is unchanged: do explicit skills and measured feedback produce better artist-accepted work, or less repair effort, than plain MCP? Broader infrastructure follows a demonstrated yes.

## Current state

Version 0.5.0 is an advisory, supervised prototype: one cooperating native writer, Blender 5.1.1 on Windows, no interception of direct MCP writes, no executor and no scheduler.

| Capability | Entry points | Since | Qualification |
|---|---|---|---|
| Continuity store: immutable checkpoints, observations, decisions and handoffs | `start`, `resume`, `review` | 0.1.0; CLI 0.4.0 | [Continuity results](CONTINUITY_RESULTS.md), [0.4.0](WORKFLOW_0_4_RESULTS.md), [0.4.2](RESUME_0_4_2_RESULTS.md) |
| Scoped edit reservations, preservation contracts, visual rejection, observed reconciliation | `begin-edit`, `finish-edit` | 0.4.0–0.4.1 | [0.4.0](WORKFLOW_0_4_RESULTS.md), [0.4.1](PRODUCTION_0_4_1_RESULTS.md) |
| Native observation with explicit coverage, compact storage and within-call reuse | `continuity_blender.observe()` in Blender, `pack-observation` | 0.1.0–0.4.8 | [0.4.6](OBSERVATION_0_4_6_RESULTS.md), [0.4.8](OBSERVER_0_4_8_RESULTS.md) |
| Reference-led quality loop, reserved-space preflight, native visibility | `python -m dcc_harness.quality` | 0.2.0–0.3.1 | [Quality loop](QUALITY_LOOP_RESULTS.md), [overnight study](OVERNIGHT_EVALUATION.md) |
| Initial scene adoption | `adopt-preview`, `adopt-apply` | 0.4.9 | [0.4.9](ADOPTION_0_4_9_RESULTS.md) |
| External revision acceptance | `preview-revision`, `accept-revision` | 0.4.10 | [0.4.10](REVISIONS_0_4_10_RESULTS.md) |
| Structured feedback and a pinned seven-stage environment workflow | `feedback-*`, `workflow-*`, `stage-*` | 0.5.0 | [0.5.0](FEEDBACK_0_5_0_RESULTS.md) |
| Nine project skills and bounded recipes: walls, roof laps, ground, terrain, broadleaf | `.agents/skills/`, `dcc_harness.craft` and recipe modules | 0.4.0–0.4.7 | [Craft skills](CRAFT_SKILLS.md) and recipe reports |
| Comparison tooling: frozen packets, fresh-context revisions, anonymous galleries | `python -m dcc_harness.blind`, `python -m dcc_harness.continuity_trial` | Pilot–0.1.1 | [Short comparison](BLIND_TRIALS.md), [continuity protocol](CONTINUITY_EXPERIMENT.md) |

The portable suite runs 233 tests: 231 pass and two Windows symlink-permission cases skip (rerun on the 0.5.0 source on October 6).

### Evidence on the governing question

| Study | Design | Result |
|---|---|---|
| [Short comparison](BLIND_RESULTS.md), Oct 3–4 | Plain MCP, skills, and skills plus a measured loop; six builds and six fresh revisions | All twelve checkpoints passed common checks. The artist preferred two plain-MCP entries, called the differences subtle and gave no scores. |
| [Continuity comparison](CONTINUITY_RESULTS.md), Oct 4 | Two plain and two continuity workflows, four fresh sessions each | Plain MCP passed 8/8 stages; continuity passed 6/8. One continuity workflow was blocked by the harness's own float32 extent artifact, fixed in 0.1.1. No artist scores. |
| [Quality loop](QUALITY_LOOP_RESULTS.md) and [overnight study](OVERNIGHT_EVALUATION.md), Oct 4 | Reference-led candidates, native visibility gates, anonymous critics | Measurement caught what images and critics missed: the birdbath was 21.7% and 34.0% visible against a predeclared 55% minimum, and both canopy alternatives failed, including the critics' favorite. A scoped relocation reached 88.7% and 97.4%. |
| [Realistic comparison](REALISM_COMPARISON.md), Oct 5 | Two plain and two harness runs, fixed scanned kit, fresh revisions | Interrupted by an account usage limit: one partial build, zero complete builds, zero revisions. |
| Guided production, Oct 5 ([0.4.1](PRODUCTION_0_4_1_RESULTS.md)–[0.4.7](TERRAIN_0_4_7_RESULTS.md)) | Same-agent everyday workflow on the potting shed | Nine accepted checkpoints; all 934 original objects preserved; six native-passing visual rejections retained. The terrain study did not improve realism. |

The continuity mechanisms work under native and fresh-context qualification. No study shows a creative-quality or repair-effort advantage over plain MCP: there are no artist scores, no repair-time measurements and no completed held-out comparison. Under the October 3 rule ("if A is equally usable, keep the simpler workflow"), the short comparison promoted no method. The continuity work followed the artist's stated interest in longer development ([D10](DESIGN_DECISIONS.md#d10-measure-continuity-after-the-short-comparison)). Versions 0.4.0–0.5.0 are usability and craft increments made under the user's October 5 authorization while the gate stays open ([D17](DESIGN_DECISIONS.md#d17-bounded-increments-proceed-while-the-creative-gate-stays-open)).

## Investment gate

This is the single definition, restated from the October 3 rules. The archived text paraphrased it three different ways.

Run a held-out realistic brief with a fixed asset kit, matched cameras and budgets, two independent trials per method and fresh-context late revisions. Compare harness-assisted work with plain MCP. The October 3 rule compared the measured loop with skills alone; plain MCP is now the standing alternative.

1. **Practical quality.** A method qualifies only if both trials reopen with their dependencies, preserve the specified locks, have no critical missing requirement, and the artist rates the result at least 4 on the five-point rubric (usable with minor cleanup).
2. **Advantage.** Promote the harness beyond a supervised prototype only if it qualifies and, relative to plain MCP, the artist prefers both paired outputs or artist repair time falls by at least 25% without worse quality.
3. **Otherwise.** If plain MCP is equally usable, keep the simpler workflow and retain only the parts that measurably reduce repair effort. If results are mixed, run a limited additional comparison; never infer success from the best image. If nothing is acceptable after one bounded method revision, stop expanding infrastructure and revisit scope, assets or modeling methods.

These thresholds are investment rules, not statistical proof. Correctness and usability increments may continue under explicit user authorization; they do not count as passing the gate, and they do not authorize stages C–E.

## Stages

| Stage | Scope | Gate | Status, October 6 |
|---|---|---|---|
| A Creative experiment | Three skills, small native helper, six trials | Choose the minimum method that produces acceptable results | **Done.** The artist preferred plain MCP; no method was promoted on quality. |
| B Continuity prototype | Durable record, save/reopen, fresh-context resume, one entry point | Held-out brief succeeds; fresh context resumes; duplicate dispatch and lost responses cause no blind replay | **Built in advisory form (0.1–0.5).** Fresh-context resume and no-replay reconciliation are qualified on fixtures. The held-out brief is incomplete, and the [D4](DESIGN_DECISIONS.md#d4-operation-identity-and-retry-ownership) executor is not built. |
| C Detailed environment | Three zones, 12–20 assets, 4–6 material families, six views, linked asset publishing | Artist accepts the output and a late shared-material, hero-size and layout revision; unrelated work is preserved | **Partially exercised** by same-agent production. No artist acceptance. Instancers fail observation, and external revisions reject linked libraries. |
| D Unattended operation | One runner, owned workers, recovery, resource limits | Repeated two-hour, then eight-hour runs with injected faults | **Not started**, by design. |
| E Broader access and disciplines | Client packages, motion, a second DCC | The same project survives client changes; temporal and transfer work pass their own gates | **Not started**, by design. |

## Next work

### 1. Close the evidence gap

These need artist time and model capacity rather than new code. Every later stage depends on them.

1. **Artist review of existing outputs.** Score the anonymous continuity gallery and production checkpoint 9 on the frozen rubric before revealing labels. Time the artist's repair of one concrete late revision to establish a repair-effort baseline. In the same session, collect about twenty artist-ranked image pairs as a held-out calibration set for agent critics; the 0.5.0 reviewer and coordinator already disagreed on a visual verdict.
2. **Resume or retire the realistic comparison ([D13](DESIGN_DECISIONS.md#d13-recalibrate-quality-before-expanding-the-runtime)).** Frozen packets, the evaluator and its controls are intact; three builds and four fresh revisions remain. Resuming needs model capacity (the service quoted a reset on October 10) and a recorded protocol deviation for the interruption. If capacity or artist time is unavailable, record a decision retiring it and design a smaller held-out comparison. It is currently neither running nor cancelled.
3. **Fresh-agent continuation on the real scene.** The 0.5.0 fresh-agent trial used a micro fixture. Run one sealed continuation on an owned copy of the production garden with the craft skills and feedback workflow. Record elapsed and inspection time, forgotten notes and remaining artist repair.

### 2. Version 0.5.1: correctness maintenance

These defects were confirmed during the October 6 review. Each fix needs a regression test, and the version bump changes the pinned runtime digest.

- **Path guard.** `continuity._plain` follows Windows junctions because it calls `stat()`; `blind._reject_link` already uses `lstat()`. Every product path check relies on `_plain`. The symlink tests skip on this host, while junctions need no privilege to create.
- **Trial packets.** `HELPER_FILES` in `blind.py` and `continuity_trial.py` omit `observation_storage.py`, which `evidence.read_json` imports. Newly prepared packets therefore cannot read JSON.
- **Runtime pin.** `environment_workflow.runtime_stamp` hashes raw source bytes, so a CRLF checkout pins a different runtime than an LF one. The new `.gitattributes` forces LF checkouts; also consider normalizing line endings inside the digest.
- **CLI results.** `--out` is created exclusively after a transaction commits, so an existing path fails after the commit and suppresses the printed result. Coordination results nest `passed`, so a failed verification exits 0, unlike `finish-edit`.
- **Legacy commands.** The pilot's `init`, `status`, `begin` and `finish` appear beside the current workflow without labels, and `status` lists no checkpoints for a continuity store. Label them as legacy in the help text.
- **Latency.** `begin-edit` and `finish-edit` run full chain verification two or three times per command; verify once. A nine-checkpoint resume already took 34.77 seconds.

### 3. Product increments, ranked

These are ranked by expected effect on the gate. Each ships as its own version under the standing rules below.

1. **Lower the cost of each step.** Add an `observe` command that runs `continuity_blender.observe()` on a saved file in owned background Blender, reusing the adoption launcher. Add a helper that hashes referenced artifacts and writes feedback and stage payload skeletons. Today every step needs hand-written JSON, SHA-256 values and a separately scripted Blender observation. The 0.5.0 fresh agent spent 6 min 12.6 s on a one-parameter revision of a micro fixture. To compete with plain MCP, the harness must keep that overhead small.
2. **Relationship checks with reliability and repair history.** Qualify one relation family, such as an object supported by ground or a doorway clear along its path, with stable IDs, measurement method, tolerance and coverage. Classify each finding by evidence strength. Retain normalized failures, attempted strategies and measured error across contexts, so a fresh agent does not repeat an ineffective repair. Exercise it with an unchanged control and a fresh continuation. The basis is [repository ideas](../research/REPOSITORY_IDEAS_2026-10-06.md) 1–3; the visibility gate is the clearest case of measurement catching what images missed. Medium scope.
3. **Collection instances and linked libraries.** The observer records any instancer as an issue, so `start`, adoption and revisions reject common artist scenes. The production study used shared mesh datablocks instead. Observe collection instances with instance identity and library provenance, then settle the publishing model in [D5](DESIGN_DECISIONS.md#d5-file-ownership-and-asset-publishing). This is a prerequisite for stage C and dense vegetation. Medium to large, with native positive and negative fixtures.
4. **Before/after review page.** A static page over two immutable checkpoints shows added, removed, moved and changed objects by stable ID, with bound renders and linked feedback notes. Artist review time is the scarce input to track 1. Keep the page generator outside the dependency-free core. Medium scope.
5. **Skill behavior regressions.** Build sealed packets for known failure situations: lost acknowledgement, stale image, changed shared material, missing view definition, an artist-saved revision, and a late request that conflicts with protected geometry. Grade actions and artifacts, not restated instructions. This reuses the fresh-context tooling. Small scope.
6. **Evidence and coverage depth.** Add dependency-aware invalidation, so only feedback and stages whose targets or views changed need rechecking. Extend contracts to new lights and world edits, modifier and node fields, UV overlap and texel density. Each needs native negative fixtures.
7. **Revision dependency relocation.** Rebase relative texture and library paths when accepting an external revision into an owned copy, instead of rejecting it. Small to medium scope.
8. **GLB delivery receipt,** only when exported delivery becomes a requirement. Export, reimport into an explicitly empty scene, verify, and bind the receipt to the accepted checkpoint.

### Deferred until the gate passes

- The D4 executor and managed mode.
- An unattended runner, worker fencing and fault soak tests.
- Client plugins, installers and an MCP connector ([packaging study](DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md)).
- Unreal and other DCC adapters ([UE-MCP review](DCC_HARNESS_UE_MCP_REVIEW.md)).
- Motion workflows ([skill system](DCC_HARNESS_SKILL_SYSTEM.md)).
- Geometry Nodes distribution identity.
- Generated textures, bakes and UDIMs.
- SDK runners and a DCC-MCP core evaluation.

Revisit each against a named, measured gap.

## Standing rules

### Each version

- Ship one bounded increment on its own branch. Bump `pyproject.toml` and `dcc_harness/__init__.py` together, and add a changelog entry.
- Write usage documentation for new entry points and a qualification report. Update the README and decision log when behavior or authority changes.
- Run the source and installed-wheel suites, plus native positive and negative fixtures in a fresh `runs/` directory with `--python-exit-code 1`. Record the wheel hash.
- Retain failed trials, rejected candidates and superseded evaluators. Correct measurement policies by version, never in place.
- Any package source change alters the pinned workflow runtime digest. Projects bound to an earlier runtime need that runtime for workflow mutations.

### Creative trials

Freeze settings before comparing methods; a changed budget starts a new comparison round. A study's frozen protocol overrides these October 3 defaults, which should be recalibrated with a timing probe:

| Resource | Ceiling |
|---|---|
| Agent and native work per trial | 90 minutes, including a reserved 15-minute late revision |
| Metered model and generation spend | USD 25 per trial and USD 150 across six trials; a held-out round adds at most USD 100 and six hours |
| Rendering within a trial | 30 minutes in total |
| Native still captures | At most 24 per trial, normally 960 × 540 |
| Repair attempts | At most two materially different repairs of one failed requirement |
| External generation | None; use the fixed asset kit |
| Artist review | Recorded separately; target at most 30 minutes per method |

Capture fixed views at blockout, surface and lighting completion, pre-revision acceptance and after the revision; reuse valid baseline images. Record tokens, billed usage, wall time, rendering time, tool calls, repair count and artist repair time where the client exposes them. Where metering is unavailable, report it as unavailable. A subscription run is not zero cost, and a method with unmeasured spend cannot claim a cost advantage.

## Repository maintenance

State on October 6:

- `main` contains 0.4.9 through [pull request #1](https://github.com/cedarconnor/3D_Harness/pull/1). Version 0.4.10 is on `codex/manual-revision`, pushed without a pull request. Version 0.5.0 is on `codex/structured-feedback-workflow`, local only and stacked on 0.4.10. Merge them in that order. No release tags exist; tag each version when it merges.
- The planning documents moved from the repository root into `docs/`, and their links are updated.
- 44 links in qualification reports point into local, gitignored `runs/` and `dist/` folders and do not resolve in a clone. Keep them as provenance pointers; the [index](README.md) explains this.
- Code health is not urgent, but the package has duplicated helpers: file hashing, link rejection, JSON writers with different fsync behavior, and copy-then-verify. There are also private cross-module imports. The experiment modules `blind`, `blind_review`, `continuity_trial` and `continuity_review` are about a quarter of the package and sit inside the runtime and its pinned digest. Consolidate only within a qualified version; frozen packets keep their copied sources.
- `scripts/` mixes current qualification fixtures with tooling from finished studies, and the [scripts index](../scripts/README.md) classifies them. Moving study scripts would invalidate absolute paths recorded in local evidence, so they stay in place.
