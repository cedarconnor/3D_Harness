# 3D Harness Build Plan

Tracked from October 6, 2026, at version 0.5.0. **This is the active plan.** It owns sequencing, gates and trial budgets. [Design decisions](DESIGN_DECISIONS.md) own architecture, qualification reports own evidence, and the [changelog](../CHANGELOG.md) records what each version delivered. The [documentation index](README.md) maps every document.

Earlier plans are archived verbatim in [archive/plans](archive/plans/). The October 3 plan's experiment design remains the protocol record for the completed short comparison.

## How to track work

- Every work item has an ID, an owner, a status and exit criteria. IDs are never reused or renumbered.
- Statuses are `todo`, `active`, `blocked`, `done` and `dropped`. Keep one or two items `active` at a time.
- When an item changes status, update its row and add a dated line to the [log](#log). Finished items keep their row and link their evidence, usually a qualification report and changelog entry.
- New work enters as a new row. Larger items get an implementation plan in `docs/plans/` before coding; smaller ones are specified under [item details](#item-details).
- Every version follows the [standing rules](#standing-rules).

## At a glance

| | |
|---|---|
| Version | 0.6.0 on `main` |
| Active | None; P1 finished with a neutral result |
| Next | P9 agent guidance commands and demo walk, then P10 queued render command; E5 can run at any time |
| Waiting on the user | E1–E3 artist review session; E4 decision on the realistic comparison; GitHub write access for R1 |
| Investment gate | Open |

## Tracker

### E: Evidence for the investment gate

These need artist time or a user decision rather than new code. Every stage after B depends on them.

| ID | Item | Owner | Status | Exit criteria |
|---|---|---|---|---|
| E1 | Score existing outputs: both anonymous galleries and production checkpoint 9 | Artist | todo | Five-point scores recorded before method labels are revealed ([session guide](studies/ARTIST_REVIEW_SESSION.md)) |
| E2 | Timed repair of one plain-MCP and one continuity final scene | Artist | todo | Minutes, fixed and remaining defects recorded per scene, with methods hidden |
| E3 | Critic calibration set | Artist | todo | About twenty ranked image pairs retained as a held-out set |
| E4 | Resume or retire the [realistic comparison](studies/REALISM_COMPARISON.md) | User | blocked: decision | Decision recorded in the decision log. A resumed run logs the interruption as a protocol deviation and keeps the frozen settings. |
| E5 | Fresh-agent continuation on the production garden | Agent | todo | Sealed continuation on an owned copy: elapsed and inspection time, forgotten notes and remaining artist repair recorded |

### M: Maintenance

| ID | Item | Owner | Status | Exit criteria |
|---|---|---|---|---|
| M1 | Version 0.5.1 correctness fixes ([details](#m1-version-051-correctness-maintenance)) | Agent | done | A regression test per defect, source and installed suites, native fixtures, and a [0.5.1 report](archive/releases/MAINTENANCE_0_5_1_RESULTS.md) |
| M2 | Consolidate duplicated helpers: file hashing, link rejection, JSON writers, copy-then-verify | Agent | todo | No behavior change; suites and native fixtures pass |
| M3 | Separate experiment tooling (`blind`, `blind_review`, `continuity_trial`, `continuity_review`) from the pinned runtime digest | Agent | todo | Experiment edits no longer invalidate workflow bindings; frozen packets are unaffected |
| M4 | Shared launcher helper for the qualification orchestrators | Agent | todo | `qualify_*` and `run_*` scripts share one helper; evaluators copied into packets stay self-contained |
| M5 | Record session cost in trial receipts ([details](#m5-session-cost)) | Agent | todo | Each trial session records turns, elapsed minutes, metered spend where known and cache-read share; reports compare spend with the trial ceilings |

### P: Product increments, ranked

Ranked by expected effect on the gate. Each ships as its own version.

| ID | Item | Owner | Status | Exit criteria |
|---|---|---|---|---|
| P1 | Lower the cost of each step: an `observe` command and a payload hash helper ([plan](archive/plans/P1_LOWER_STEP_COST.md)) | Agent | done | Shipped in 0.6.0. A paired fresh-agent run found no elapsed-time reduction: 8 min 16 s on 0.5.1, 9 min 41 s on 0.6.0, confounded by a shared tool. Orientation dominated both runs ([report](archive/releases/STEP_COST_0_6_0_RESULTS.md)) |
| P9 | Agent guidance: `next` and `requirements` commands, a `demo` walk on a fixture, and a one-page quick reference ([details](#p9p12-orientation-checks-and-authority)) | Agent | todo | Orientation time measured in a fresh-agent run against the 0.6.0 comparison's roughly 3 to 3.7 min; `demo` runs the full edit, feedback and stage loop without a model |
| P10 | Fixed-view render command that renders a project's review cameras for a saved file, with receipt and settings, through a one-at-a-time queue | Agent | todo | Replaces the fixture-specific render tool both comparison agents relied on; render IDs can be waited on; native fixtures |
| P11 | Learned check library: errors no check caught become owner-approved, versioned checks for later projects | Agent | todo | A caught error yields a proposed check; once approved it runs in a new project; positive and negative native fixtures; taste stays project-scoped |
| P12 | Owner-only approval channel the agent's tools cannot reach | Agent | todo | Artist acceptance and check approval enter only through an owner path; an agent-written artist authority is rejected; decision recorded in the decision log |
| P2 | Relationship checks with evidence reliability and repair history | Agent | todo | One relation family qualified natively; a fresh continuation avoids repeating an ineffective repair |
| P3 | Collection instances and linked libraries | Agent | todo | Instanced scenes can `start`; D5 publishing model decided; positive and negative native fixtures |
| P4 | Before/after review page over immutable checkpoints, with owner questions and a camera sheet | Agent | todo | Changed objects by stable ID with bound renders and linked notes, checked against reopened checkpoints; submission questions answered with defaults |
| P5 | Skill behavior regressions | Agent | todo | Sealed packets for six known failure situations, graded on actions and artifacts |
| P6 | Evidence and coverage depth | Agent | todo | Dependency-aware invalidation; contracts cover new lights, world edits, modifier and node fields, UV overlap and texel density |
| P7 | Revision dependency relocation | Agent | todo | External revisions with relative texture or library paths accepted into an owned copy |
| P8 | GLB delivery receipt | Agent | todo, when export is required | Export, reimport into an empty scene, verify, and bind the receipt to the accepted checkpoint |

### R: Repository

| ID | Item | Owner | Status | Exit criteria |
|---|---|---|---|---|
| R1 | Merge the feature branches into `main` | Agent | blocked: GitHub write access | Local `main` contains 0.4.9 through 0.5.0 and local branches are deleted. Pushing `main` and deleting the remote branches failed: the git credential's account, `Cedar-Sphere`, cannot write to `cedarconnor/3D_Harness`. |
| R2 | Organize documentation into active and archive folders; make this plan trackable | Agent | done | No broken relative links; index updated |
| R3 | Tag released versions | Agent | todo | Tags for 0.4.8 through the current version, pushed with user approval |

### X: Deferred until the gate passes

Revisit each against a named, measured gap.

| ID | Item | Reference |
|---|---|---|
| X1 | The D4 executor and managed mode | [D4](DESIGN_DECISIONS.md#d4-operation-identity-and-retry-ownership) |
| X2 | An unattended runner, worker fencing and fault soak tests, with runaway guards: pause after sessions that move nothing forward, and cap session length | Stage D below; [motion harness review](reference/MOTION_HARNESS_REVIEW_2026-10-10.md) |
| X3 | Client plugins, installers and an MCP connector | [Packaging study](reference/DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md) |
| X4 | Unreal and other DCC adapters | [UE-MCP review](reference/DCC_HARNESS_UE_MCP_REVIEW.md) |
| X5 | Motion workflows; evaluate adopting or connecting to Mortiflix before building | [Skill system](reference/DCC_HARNESS_SKILL_SYSTEM.md), [motion harness review](reference/MOTION_HARNESS_REVIEW_2026-10-10.md) |
| X6 | Geometry Nodes distribution identity | [D6](DESIGN_DECISIONS.md#d6-asset-and-instance-identity-are-separate) |
| X7 | Generated textures, bakes and UDIMs | [Archived October 3 plan](archive/plans/DCC_HARNESS_BUILD_PLAN_v3_2026-10-06.txt) |
| X8 | SDK runners and a DCC-MCP core evaluation | [D2](DESIGN_DECISIONS.md#d2-reuse-the-transport-and-implement-native-observation), [D8](DESIGN_DECISIONS.md#d8-package-the-proven-workflow) |

## Item details

### M1: Version 0.5.1 correctness maintenance

Done in 0.5.1; see the [report](archive/releases/MAINTENANCE_0_5_1_RESULTS.md). `finish-edit` still verifies twice, before and after publication; incremental verification is future work.

These defects were confirmed during the October 6 review. Each fix needs a regression test. The version bump changes the pinned runtime digest, so projects bound under 0.5.0 need that runtime for workflow mutations.

- **Path guard.** `continuity._plain` follows Windows junctions because it calls `stat()`; `blind._reject_link` already uses `lstat()`. Every product path check relies on `_plain`. The symlink tests skip on this host, while junctions need no privilege to create.
- **Trial packets.** `HELPER_FILES` in `blind.py` and `continuity_trial.py` omit `observation_storage.py`, which `evidence.read_json` imports. Newly prepared packets therefore cannot read JSON.
- **Runtime pin.** `environment_workflow.runtime_stamp` hashes raw source bytes, so a CRLF checkout pinned a different runtime than an LF one. `.gitattributes` now forces LF checkouts; also normalize line endings inside the digest.
- **CLI results.** `--out` is created exclusively after a transaction commits, so an existing path fails after the commit and suppresses the printed result. Coordination results nest `passed`, so a failed verification exits 0, unlike `finish-edit`.
- **Legacy commands.** The pilot's `init`, `status`, `begin` and `finish` appear beside the current workflow without labels, and `status` lists no checkpoints for a continuity store.
- **Latency.** `begin-edit` and `finish-edit` run full chain verification two or three times per command; verify once. A nine-checkpoint resume already took 34.77 seconds.

### P1: Lower the cost of each step

Done in 0.6.0; see the [report](archive/releases/STEP_COST_0_6_0_RESULTS.md). The motivation below is kept as written. The comparison showed that per-step commands remove scripts but not orientation time, which led to P9 and P10.

Before 0.6.0, every step needed hand-written JSON, SHA-256 values and a separately scripted Blender observation. The 0.5.0 fresh agent spent 6 min 12.6 s on a one-parameter revision of a micro fixture. To compete with plain MCP, the harness must keep that overhead small.

- An `observe` command runs `continuity_blender.observe()` on a saved file in an owned background Blender, reusing the adoption launcher. It never saves the source, verifies the source hash is unchanged, and writes the observation with exclusive creation.
- A payload helper fills `{path, sha256}` references in feedback, stage and evidence payloads from the actual files, so agents stop computing hashes by hand.
- Both need native positive and negative fixtures and a repeat of the 0.5.0 fresh-agent revision for comparison.

### P9–P12: orientation, checks and authority

P9 and P10 were added after the 0.6.0 comparison. Both fresh agents spent roughly three minutes reading skills, guides and runtime source before their first command, while native work took seconds. They wrote one script each, because a provided render tool covered rendering and observation; the 0.5.0 agent, without such a tool, wrote five. On October 10 the [motion harness review](reference/MOTION_HARNESS_REVIEW_2026-10-10.md) extended P9 and P10 and added P11 and P12; the same review adds questions and a camera sheet to P4 and the M5 cost record.

- **P9, agent guidance.** Answer "what next?" from the project's state instead of from documents. `next PROJECT` names the next permitted command for the current state, such as an open reservation, unanswered notes or a pending submission. `requirements PROJECT STAGE` prints the evidence a submission must carry and a payload skeleton with `{path}` references ready for `fill-hashes`. `demo` walks begin-edit, finish-edit, a feedback note, response and verification, and a stage submission on a bundled fixture, printing each command and payload; it needs Blender but no model, and doubles as a smoke test. Keep the one-page quick reference for the two most frequent tasks, generated from the same command list so it cannot drift. Measure orientation before building anything larger.
- **P10, render command.** Generalize the fixture-specific render tool: render the project's review cameras for a saved file without saving it, and write the receipt with its view settings in the format feedback evidence requires. Run renders one at a time through a queue; each request returns an ID that a later call waits on, so a slow render never blocks the session.
- **P11, learned checks.** When feedback verification finds an error that no existing check reported, the response may propose a check: a measurable rule, its applicable stages, tolerance and a negative fixture showing that it catches the error. An owner-approved check joins a versioned library outside any single project; new workflow bindings pin the library version as they pin skills, so earlier projects are unaffected. Classify each artist note as error or taste first: only errors become checks, and taste stays project direction. P2's first relation family is the natural first library entry. Needs P12 so that approval cannot come from the proposing agent.
- **P12, owner approval channel.** Roles are caller-attributed today, so an agent can write `authority: {role: "artist"}`. Accept artist completion, blocking deferrals and check approvals only through a path the agent's tools cannot reach, such as answers the artist saves in a review page, imported with their provenance, or an interactive owner command. Record the authority change as a design decision before coding. Pair it with P4.

### M5: session cost

Trial ceilings are set in dollars and minutes, but reports record only elapsed time. Capture turns, elapsed minutes, metered spend where the backend reports it, and the share of input read from cache for every trial session, retained with the trial's other receipts.

### P2–P8

- **P2, relationship checks.** Qualify one relation family, such as an object supported by ground or a doorway clear along its path, with stable IDs, method, tolerance and coverage. Classify findings by evidence strength. Retain normalized failures, attempted strategies and measured error across contexts. The basis is [repository ideas](reference/REPOSITORY_IDEAS_2026-10-06.md) 1–3; the visibility gate is the clearest case of measurement catching what images missed.
- **P3, instances.** The observer records any instancer as an issue, so `start`, adoption and revisions reject common artist scenes; the production study used shared mesh datablocks instead. Observe collection instances with instance identity and library provenance, then settle [D5](DESIGN_DECISIONS.md#d5-file-ownership-and-asset-publishing).
- **P4, review page.** Show added, removed, moved and changed objects by stable ID, with bound renders and linked feedback notes. Artist review time is the scarce input to track E. Keep the generator outside the dependency-free core. Let a stage submission carry owner questions with choices and a default, answered on the page with one click, and show every review camera on one sheet before the per-view comparisons. The October 6 [artist review page](studies/ARTIST_REVIEW_SESSION.md) is a working prototype of the layout.
- **P5, skill regressions.** Use sealed packets for a lost acknowledgement, a stale image, a changed shared material, a missing view definition, an artist-saved revision and a late request that conflicts with protected geometry. Grade actions and artifacts, not restated instructions.
- **P6, coverage.** Recheck only the feedback and stages whose targets or views changed, and extend contracts to the fields listed in the tracker. Each addition needs native negative fixtures.
- **P7, relocation.** Rebase relative texture and library paths when accepting an external revision into an owned copy, instead of rejecting it.
- **P8, delivery.** Start with static GLB. A Blender round trip does not establish compatibility with another destination.

## Investment gate

This is the single definition, restated from the October 3 rules, which the archived text paraphrased three different ways.

Run a held-out realistic brief with a fixed asset kit, matched cameras and budgets, two independent trials per method and fresh-context late revisions. Compare harness-assisted work with plain MCP; the October 3 rule compared the measured loop with skills alone, but plain MCP is now the standing alternative.

1. **Practical quality.** A method qualifies only if both trials reopen with their dependencies, preserve the specified locks, have no critical missing requirement, and the artist rates the result at least 4 on the five-point rubric (usable with minor cleanup).
2. **Advantage.** Promote the harness beyond a supervised prototype only if it qualifies and, relative to plain MCP, the artist prefers both paired outputs or artist repair time falls by at least 25% without worse quality.
3. **Otherwise.** If plain MCP is equally usable, keep the simpler workflow and retain only the parts that measurably reduce repair effort. If results are mixed, run a limited additional comparison; never infer success from the best image. If nothing is acceptable after one bounded method revision, stop expanding infrastructure and revisit scope, assets or modeling methods.

These thresholds are investment rules, not statistical proof. Correctness and usability increments may continue under explicit user authorization ([D17](DESIGN_DECISIONS.md#d17-bounded-increments-proceed-while-the-creative-gate-stays-open)); they do not count as passing the gate, and they do not authorize stages C–E.

## Evidence so far

| Study | Design | Result |
|---|---|---|
| [Short comparison](archive/studies/BLIND_RESULTS.md), Oct 3–4 | Plain MCP, skills, and skills plus a measured loop; six builds and six fresh revisions | All twelve checkpoints passed common checks. The artist preferred two plain-MCP entries, called the differences subtle and gave no scores. |
| [Continuity comparison](archive/studies/CONTINUITY_RESULTS.md), Oct 4 | Two plain and two continuity workflows, four fresh sessions each | Plain MCP passed 8/8 stages; continuity passed 6/8. One continuity workflow was blocked by the harness's own float32 extent artifact, fixed in 0.1.1. No artist scores. |
| [Quality loop](archive/releases/QUALITY_LOOP_RESULTS.md) and [overnight study](archive/studies/OVERNIGHT_EVALUATION.md), Oct 4 | Reference-led candidates, native visibility gates, anonymous critics | Measurement caught what images and critics missed: the birdbath was 21.7% and 34.0% visible against a predeclared 55% minimum, and both canopy alternatives failed, including the critics' favorite. A scoped relocation reached 88.7% and 97.4%. |
| [Realistic comparison](studies/REALISM_COMPARISON.md), Oct 5 | Two plain and two harness runs, fixed scanned kit, fresh revisions | Interrupted by an account usage limit: one partial build, zero complete builds, zero revisions. |
| Guided production, Oct 5 ([0.4.1](archive/releases/PRODUCTION_0_4_1_RESULTS.md)–[0.4.7](archive/releases/TERRAIN_0_4_7_RESULTS.md)) | Same-agent everyday workflow on the potting shed | Nine accepted checkpoints; all 934 original objects preserved; six native-passing visual rejections retained. The terrain study did not improve realism. |

The continuity mechanisms work under native and fresh-context qualification. No study shows a creative-quality or repair-effort advantage over plain MCP: there are no artist scores, no repair-time measurements and no completed held-out comparison. Under the October 3 rule ("if A is equally usable, keep the simpler workflow"), the short comparison promoted no method. The continuity work followed the artist's stated interest in longer development ([D10](DESIGN_DECISIONS.md#d10-measure-continuity-after-the-short-comparison)).

## Stages

| Stage | Scope | Gate | Status, October 6 |
|---|---|---|---|
| A Creative experiment | Three skills, small native helper, six trials | Choose the minimum method that produces acceptable results | **Done.** The artist preferred plain MCP; no method was promoted on quality. |
| B Continuity prototype | Durable record, save/reopen, fresh-context resume, one entry point | Held-out brief succeeds; fresh context resumes; duplicate dispatch and lost responses cause no blind replay | **Built in advisory form (0.1–0.5).** Fresh-context resume and no-replay reconciliation are qualified on fixtures. The held-out brief is incomplete (E4), and the D4 executor is deferred (X1). |
| C Detailed environment | Three zones, 12–20 assets, 4–6 material families, six views, linked asset publishing | Artist accepts the output and a late shared-material, hero-size and layout revision; unrelated work is preserved | **Partially exercised** by same-agent production. No artist acceptance. Instancers fail observation, and external revisions reject linked libraries (P3). |
| D Unattended operation | One runner, owned workers, recovery, resource limits | Repeated two-hour, then eight-hour runs with injected faults | **Not started**, by design (X1, X2). |
| E Broader access and disciplines | Client packages, motion, a second DCC | The same project survives client changes; temporal and transfer work pass their own gates | **Not started**, by design (X3–X5). |

## What exists at 0.5.0

An advisory, supervised prototype: one cooperating native writer, Blender 5.1.1 on Windows, no interception of direct MCP writes, no executor and no scheduler.

| Capability | Entry points | Since | Guide |
|---|---|---|---|
| Continuity store: immutable checkpoints, observations, decisions and handoffs | `start`, `resume`, `review` | 0.1.0; CLI 0.4.0 | [Everyday workflow](guides/EVERYDAY_WORKFLOW.md) |
| Scoped edit reservations, preservation contracts, visual rejection, observed reconciliation | `begin-edit`, `finish-edit` | 0.4.0–0.4.1 | [Everyday workflow](guides/EVERYDAY_WORKFLOW.md) |
| Native observation with explicit coverage, compact storage and within-call reuse | `continuity_blender.observe()` in Blender, `pack-observation` | 0.1.0–0.4.8 | [Observation storage](guides/OBSERVATION_STORAGE.md) |
| Reference-led quality loop, reserved-space preflight, native visibility | `python -m dcc_harness.quality` | 0.2.0–0.3.1 | [Quality loop](guides/QUALITY_LOOP_USAGE.md) |
| Initial scene adoption | `adopt-preview`, `adopt-apply` | 0.4.9 | [Scene adoption](guides/SCENE_ADOPTION.md) |
| External revision acceptance | `preview-revision`, `accept-revision` | 0.4.10 | [External revisions](guides/EXTERNAL_REVISIONS.md) |
| Structured feedback and a pinned seven-stage environment workflow | `feedback-*`, `workflow-*`, `stage-*` | 0.5.0 | [Structured feedback](guides/STRUCTURED_FEEDBACK.md) |
| Nine project skills and bounded recipes: walls, roof laps, ground, terrain, broadleaf | `.agents/skills/`, `dcc_harness.craft` and recipe modules | 0.4.0–0.4.7 | [Craft skills](guides/CRAFT_SKILLS.md) |
| Comparison tooling: frozen packets, fresh-context revisions, anonymous galleries | `python -m dcc_harness.blind`, `python -m dcc_harness.continuity_trial` | Pilot–0.1.1 | [Trial protocol](archive/studies/BLIND_TRIALS.md) |

## Standing rules

### Each version

- Ship one bounded increment on `main`. Bump `pyproject.toml` and `dcc_harness/__init__.py` together, and add a changelog entry.
- Write usage documentation in `docs/guides/` for new entry points and a qualification report in `docs/archive/releases/`. Update the README and decision log when behavior or authority changes.
- Run the source and installed-wheel suites, plus native positive and negative fixtures in a fresh `runs/` directory with `--python-exit-code 1`. Record the wheel hash. The [scripts index](../scripts/README.md) lists the fixtures for each version.
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

## Log

Newest first. One line per status change.

- **2026-10-10:** P11, P12 and M5 added and P4, P9, P10, X2 and X5 extended, from the [motion harness review](reference/MOTION_HARNESS_REVIEW_2026-10-10.md).
- **2026-10-06:** P9 and P10 added from the comparison's finding that orientation, not native steps, dominates agent time.
- **2026-10-06:** P1 done. Version 0.6.0 ships `observe` and `fill-hashes`. A paired fresh-agent comparison showed no elapsed-time reduction; the result is recorded as neutral.
- **2026-10-06:** P1 started; [implementation plan](archive/plans/P1_LOWER_STEP_COST.md) written.
- **2026-10-06:** M1 done. Version 0.5.1 fixes six defects, with eleven new tests; native exercises passed against source and installed runtimes.
- **2026-10-06:** R1 blocked. Pushing `main` was refused for the `Cedar-Sphere` credential; the merge exists locally.
- **2026-10-06:** M1 started.
- **2026-10-06:** R2 done. Documentation reorganized into active folders (`guides/`, `recipes/`, `studies/`, `reference/`) and `archive/`; this plan converted to a tracker.
- **2026-10-06:** R1 merged locally. `codex/manual-revision` (0.4.10) and `codex/structured-feedback-workflow` (0.5.0) merged into `main`; the local feature branches were deleted.
- **2026-10-06:** Plan rewritten from the October 3 week-one plan; previous text archived.
