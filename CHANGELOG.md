# Changelog

Each version is a bounded increment with its own qualification report. Test counts are portable-suite results on Windows; the two skips in each count are host symlink-permission cases. Native qualification uses Blender 5.1.1 on Windows. Studies are listed with the versions they exercised. The [build plan](docs/BUILD_PLAN.md) explains what remains open, and reports that link into `runs/` refer to local evidence excluded from Git.

## 0.13.0 — October 10, 2026

Learned check library, build-plan item P11 ([plan](docs/archive/plans/P11_LEARNED_CHECKS.md), decision [D19](docs/DESIGN_DECISIONS.md#d19-learned-checks-are-computed-rules-in-an-owner-approved-library)).

- **Added:** `dcc.check.rule.v1` rules the runtime computes. `object_field` bounds a measured field (bounds, dimensions, scale, determinant, counts, render visibility) of the objects a type/ID-glob selector matches. `supported_by` resolves selectors to a relations definition and is evaluated from a native `relations --spec` measurement of the exact checkpoint.
- **Added:** `check-propose`, a coordination command. It records a check proposed from a feedback note only if the rule fails on the note's checkpoint and passes on a later fixed one. Taste and unmeasurable lessons are refused.
- **Added:** `check-approve`, owner only through the 0.12.0 channel. It proves the proposal again and writes the next version of a library outside any project, with its fixtures and a chain to the previous version. `checks` re-proves and lists the library ranked by repeats, and exports a version; `check-occurrence` counts a verified repeat from another project.
- **Added:** a workflow binding may pin one exported library version (`checks`). Pinned checks run at stage submission, at their stages and at delivery; failed or unmeasured checks block completion. Submissions may carry `check_measurements`. `requirements` lists the stage's checks with the resolved relation definition and command.
- **Added:** the [learned checks guide](docs/guides/LEARNED_CHECKS.md).
- **Qualification:** 381 tests from source and from the installed wheel. Native proposals, refusals, owner approval, pinning, a blocked and then completed stage, and a counted repeat on the relations probe's bench scenes, from both runtimes. [Report](docs/archive/releases/CHECKS_0_13_0_RESULTS.md)

## 0.12.0 — October 10, 2026

Owner approval channel, build-plan item P12 ([plan](docs/archive/plans/P12_OWNER_APPROVAL.md), decision [D18](docs/DESIGN_DECISIONS.md#d18-artist-authority-comes-only-through-the-owners-terminal)).

- **Changed:** a payload that claims the artist as its reviewer or authority now needs the owner's confirmation for that exact request: a stage completion, feedback verification, feedback decision, stage reopening or workflow binding. The command shows what will be recorded and asks for a four-character code at an interactive terminal. It refuses inside an agent session (`CLAUDECODE`, `AI_AGENT`, `CODEX_SANDBOX`, `GEMINI_CLI`, `DCC_HARNESS_AGENT`) and with piped input. Replays of committed requests do not ask again.
- **Changed:** such receipts record `owner_approval` (channel, time, operating-system user, code) and `artistic_acceptance: artist_confirmed`. Earlier records keep `artist_declared`.
- **Changed:** `review-import` asks once before committing anything when the export approves a stage, and imports nothing if the owner does not confirm. Notes-only exports import as before.
- **Changed:** a binding that relaxes a stage the manifest marks `artist_required` needs the artist's authority. `brief` and `next` tell agents to hand artist-required stages to the artist.
- **Added:** the [owner approval guide](docs/guides/OWNER_APPROVAL.md). It states the limit: this is a guard against an agent approving its own work, not a wall against one with an unrestricted shell.
- **Qualification:** 365 tests from source and from the installed wheel. Native refusals and a scripted owner approval on the comparison project from both runtimes. [Report](docs/archive/releases/OWNER_APPROVAL_0_12_0_RESULTS.md)

## 0.11.0 — October 10, 2026

Before/after review page, build-plan item P4 ([plan](docs/archive/plans/P4_REVIEW_PAGE.md)).

- **Added:** `review-page PROJECT --output-dir NEW` writes a local page comparing two checkpoints: bound renders (rendered with `--blender` or supplied as render folders), a sheet of every view, before and after with hold-to-compare, changes by stable ID with linked notes, every feedback note, and a stage waiting for review with its questions. `--reopen` re-observes the after checkpoint with the qualified comparator.
- **Added:** the page writes new notes, optionally attached to an object or pinned on an after image, and a stage approval with answers, into one export. `review-import PROJECT EXPORT --page FOLDER` checks the export came from that page, completes the stage, then adds the notes; repeating it replays without duplicates.
- **Added:** stage submissions may carry up to 12 `questions` with optional choices and a default; completion reviews may carry `answers`, unanswered questions take their default, and the receipt records which answers were defaults.
- **Qualification:** 356 tests, 354 passed, from source; the installed wheel passed the same runtime tests. Native page from both runtimes on the comparison project; a pinned note and a stage approval with one changed answer round-tripped through the browser by hand and through the scripted import. [Report](docs/archive/releases/REVIEW_PAGE_0_11_0_RESULTS.md)

## 0.10.0 — October 10, 2026

Collection instances and linked libraries, build-plan item P3 ([plan](docs/archive/plans/P3_COLLECTION_INSTANCES.md)).

- **Added:** the observer supports collection instances, local or linked from a library, including nested sets. Each instancer records the collection, its asset identity, the library's stored path and SHA-256, a definition hash taken in the collection's own space, world bounds and orientation-only dimensions. Moving an instance changes only its transform and bounds.
- **Added:** `instance` is a contract field, `exact_asset_counts` counts instances, and adoption assigns asset IDs to local instanced collections.
- **Added:** `brief` lists linked libraries and `next` points native commands at the working copy beside them, since the stored checkpoint cannot resolve relative library paths.
- **Changed:** vertex, face and particle instancing, library overrides, missing libraries and unlabelled local instanced collections are reported as issues. Scenes without instances observe byte-for-byte as in 0.9.0, and the comparator ignores instance coverage present on only one side.
- **Decision:** [D5](docs/DESIGN_DECISIONS.md#d5-file-ownership-and-asset-publishing) settled: publish asset changes as versioned libraries switched by scoped edits; in-place library edits are caught at the next reservation.
- **Qualification:** 336 tests, 334 passed, from source; the installed wheel passed the same runtime tests. Native fixtures from both runtimes: instanced scenes observed `READY` with exact bounds and dimensions; the comparison fixture kept its 0.9.0 revision; permitted moves and library swaps published and protected ones were rejected for exactly the changed fields; an in-place library edit was refused; adoption produced `READY_FOR_START`. [Report](docs/archive/releases/INSTANCES_0_10_0_RESULTS.md)

## 0.9.0 — October 10, 2026

Relationship checks, build-plan item P2 ([plan](docs/archive/plans/P2_RELATIONSHIP_CHECKS.md)).

- **Added:** `relations SAVED.blend --blender PATH --output-dir NEW (--project PROJECT | --spec FILE) [--strategy TEXT]` measures `supported_by` relations in a fresh background Blender and never saves. Vertical rays through each subject's footprint meet the declared support. Findings are `OK`, `GAP`, `PENETRATION`, `OFF_SUPPORT` or `MISSING_TARGET`, with signed errors, spread and coverage; mixed gap and penetration is a `CONFLICT`.
- **Added:** evidence strength. The native ray measurement decides a finding; a bounding-box estimate is reported as `bounds_only` and permits inspection only.
- **Added:** a retained repair history. With `--project`, each measurement and its strategy text is appended to the project's `relations/` record, and `brief` and `next` warn on `OPPOSING` and `NO_PROGRESS` repairs and on `CONFLICT`.
- **Added:** the `dcc.relations.v1` definition, held as the decision `relations`. The quick reference, everyday-workflow guide, skill and README describe the command.
- **Qualification:** 324 tests, 322 passed, from source; the installed wheel passed the same runtime tests. Eight exact native scenes from both runtimes matched hand-computed values within 0.2 mm, including a sloped bench whose bounds estimate falsely reported penetration. Two fresh agents, with and without a history of failed whole-bench moves, each fixed the bench per leg on the first attempt; the history's own effect was not isolated. [Report](docs/archive/releases/RELATIONS_0_9_0_RESULTS.md)

## 0.8.0 — October 10, 2026

Fixed-view render command, build-plan item P10 ([plan](docs/archive/plans/P10_RENDER_COMMAND.md)).

- **Added:** `render SAVED.blend --blender PATH --output-dir NEW (--project PROJECT | --views FILE)` renders a project's review views in a fresh background Blender and never saves. It writes the images, the resolved view settings and a `dcc.quality.renders.v1` receipt bound to the file's hash, and returns ready evidence entries.
- **Added:** the `dcc.review.views.v1` definition, held by a project as the decision `review_views`. A view uses a scene camera by stable ID or a review-only camera by lens, location and target, with an optional crop.
- **Added:** one render at a time per machine under a file lock released on crash. `--detach` queues a render in a separate process; `render-wait FOLDER` returns its state.
- **Changed:** `next` and `brief` offer render steps when a project has `review_views`. The quick reference, guides, skill and README describe the command.
- **Fixed during qualification:** repeat renders differed only in embedded PNG stamps and Cycles timing chunks, which are now disabled and stripped. `BLENDER_EEVEE_NEXT`, which Blender 5.1 rejects, is not accepted.
- **Qualification:** 304 tests, 302 passed, from source; the installed wheel passed the same runtime tests. Native renders from both runtimes were byte-identical on repeat, changed digest with a moved camera, committed as feedback evidence, rendered from a project definition through the printed `next` command, and ran detached without overlapping. [Report](docs/archive/releases/RENDER_0_8_0_RESULTS.md)

## 0.7.0 — October 10, 2026

Agent guidance, build-plan item P9 ([plan](docs/archive/plans/P9_AGENT_GUIDANCE.md)).

- **Added:** `brief PROJECT` prints Markdown from the verified record: where the project stands, the permitted next steps with commands filled in (project path, parent ID, checkpoint path, edit ID, coordination revision and a fresh request ID), each open note's acceptance, targets and view, the stage table, and the recorded brief, handoff and decisions fenced as records. It only reads.
- **Added:** `next PROJECT` returns the same steps as JSON. While anything is unresolved it offers only inspection or `finish-edit`.
- **Added:** `requirements PROJECT STAGE` returns a stage's required evidence, deliverables, exact `feedback_ids`, blockers and a submission skeleton for `fill-hashes`.
- **Added:** the [agent quick reference](docs/guides/AGENT_QUICK_REFERENCE.md), whose commands, payload examples and quoted errors the suite checks against the runtime. The `dcc-harness` skill now starts with `brief`.
- **Not built:** the planned `demo` walk, because orientation fell below the plan's one-minute threshold.
- **Qualification:** 283 tests, 281 passed, from source; the installed wheel passed the same runtime tests. Native runs on copies of two retained projects, source and installed, executed the printed `observe` and `begin-edit` commands and left the copies otherwise unchanged. A fresh agent on the 0.6.0 comparison task finished in 3 min 1 s against 8 min 16 s and 9 min 41 s, reserving its edit after 51 s instead of 4 to 5 min (one run, directional). [Report](docs/archive/releases/GUIDANCE_0_7_0_RESULTS.md)

## 0.6.0 — October 6, 2026

Lower the cost of each step, build-plan item P1 ([plan](docs/archive/plans/P1_LOWER_STEP_COST.md)).

- **Added:** `observe SAVED.blend --blender PATH --output-dir NEW_FOLDER` observes a saved file in a fresh background Blender and never saves it. It reports `READY`, or `HAS_ISSUES` with exit status 1, listing problems such as missing IDs or an unsupported collection instancer. Its observation feeds `start`, `begin-edit`, `finish-edit` and `preview-revision` directly, so agents no longer write an observation script for every step.
- **Added:** `fill-hashes PAYLOAD DESTINATION` fills `{path}` references in coordination payloads with their SHA-256 and verifies hashes already present. A mismatch fails rather than being overwritten. It uses the coordination path rules and writes a new file.
- **Changed:** adoption and `observe` share one background-Blender launcher.
- **Fixed during qualification:** `fill-hashes` checks its destination for links and junctions before writing.
- **Qualification:** 260 tests, 258 passed, from both source and installed wheel. Native `observe` fixtures passed against both runtimes: clean, path with spaces, missing asset ID and collection instancer. The fresh-process observation matched an in-process observation exactly. A paired fresh-agent comparison found no elapsed-time reduction (8 min 16 s on 0.5.1, 9 min 41 s on 0.6.0, one run each, confounded by a shared tool); orientation dominated both runs. [Report](docs/archive/releases/STEP_COST_0_6_0_RESULTS.md)

## 0.5.1 — October 6, 2026

Correctness maintenance, build-plan item M1, plus the repository reorganization.

- **Fixed:** the path guard now rejects Windows directory junctions. It followed them with `stat()`, so a junction anywhere in a retained path passed the check.
- **Fixed:** trial packets from `dcc_harness.blind` and `dcc_harness.continuity_trial` now include `observation_storage.py`. Without it, their helper copies could not read JSON.
- **Fixed:** the pinned workflow runtime digest normalizes line endings, so CRLF and LF checkouts of the same sources pin the same runtime.
- **Changed:** results print before an `--out` receipt is written. An existing receipt path now exits 2 without hiding a committed result. Coordination commands whose result did not pass, such as a `fail` or `uncertain` verification, exit 1.
- **Changed:** `begin-edit` verifies the checkpoint chain once instead of twice, and `finish-edit` twice instead of three times. Publication refuses a stale pre-verified state.
- **Changed:** the legacy pilot commands are labeled in help. Legacy `status` lists continuity checkpoints and points to `resume`.
- **Compatibility:** the runtime digest changed, so projects bound under 0.5.0 need the 0.5.0 runtime for workflow mutations.
- **Qualification:** 244 tests, 242 passed, from both source and installed wheel. Native revisions, adoption and feedback-workflow exercises passed against both runtimes, which now pin the same digest. One full chain verification of the nine-checkpoint production store takes about 30 s under either version, so each edit command saves one such pass. [Report](docs/archive/releases/MAINTENANCE_0_5_1_RESULTS.md)
- **Documentation:** `docs/` is organized into active folders (`guides/`, `recipes/`, `studies/`, `reference/`) and `docs/archive/` for addressed work: release reports, completed studies, implemented plans and superseded inputs, including the former root `research/` and `dcc-skills/` folders. Links are rewritten and verified. The [build plan](docs/BUILD_PLAN.md) is now a tracker with IDs, owners, statuses, exit criteria and a log; the previous plans are archived. This changelog, a [documentation index](docs/README.md), a [scripts index](scripts/README.md) and an [artist review session guide](docs/studies/ARTIST_REVIEW_SESSION.md) are new.
- **Branches:** versions 0.4.10 and 0.5.0 were merged into `main`; development continues there.
- **Decision log:** a status table and D17, which records the October 5 authorization for bounded increments.
- **Skills:** `dcc-build-revise` and `dcc-plan-environment` route to the everyday workflow and continuity observer instead of pilot-only commands. `dcc-environment-assembly` no longer implies a packaged leaf-projection helper. `dcc-blind-test` describes fresh-context delegation without assuming one host.
- **Repository:** `.gitattributes` forces LF checkouts, so the pinned workflow runtime digest no longer depends on a clone's line-ending settings.

## 0.5.0 — October 6, 2026

Structured feedback and a pinned environment workflow.

- **Added:** immutable, parent-linked coordination events beside native checkpoints. Feedback notes are anchored to checkpoints, stable IDs and bound render views, with separate response, verification and disposition records: `feedback-add`, `feedback-respond`, `feedback-verify`, `feedback-decide`.
- **Added:** a packaged seven-stage environment manifest with `workflow-template`, `workflow-bind` (which pins skills, references and the runtime digest), `stage-submit`, `stage-complete` and `stage-reopen`. `resume` and `review` gain a coordination section.
- **Fixed during qualification:** render evidence must retain its view-settings JSON, not only the digest.
- **Qualification:** 233 tests, 231 passed, plus source and installed native exercises. One fresh-agent continuation failed and a second passed. The independent reviewer resolved three notes and left the visual note uncertain. [Report](docs/archive/releases/FEEDBACK_0_5_0_RESULTS.md) · [usage](docs/guides/STRUCTURED_FEEDBACK.md) · [design record](docs/archive/plans/STRUCTURED_FEEDBACK_ENVIRONMENT_WORKFLOW.md)

## 0.4.10 — October 6, 2026

External revision acceptance.

- **Added:** `preview-revision` freezes an already-saved artist or tool edit with its observation, contract, handoff and decision updates. `accept-revision` rechecks it under the workflow lock and publishes it with an attributed review. A lost acknowledgement returns `ALREADY_PUBLISHED`. Known external image and library dependencies are rejected before relocation.
- **Qualification:** 204 tests, 202 passed, plus native exercises and a 0.4.9 reader check. [Report](docs/archive/releases/REVISIONS_0_4_10_RESULTS.md) · [usage](docs/guides/EXTERNAL_REVISIONS.md)

## 0.4.9 — October 6, 2026

Initial scene adoption.

- **Added:** `adopt-preview` lists missing stable IDs from a saved file. `adopt-apply` applies the frozen plan to a new file in background Blender and observes it independently. Duplicate or ambiguous identities and outside-scene writes block adoption.
- **Qualification:** 186 tests, 184 passed; nine native sources were correctly blocked. [Report](docs/archive/releases/ADOPTION_0_4_9_RESULTS.md) · [usage](docs/guides/SCENE_ADOPTION.md)

## 0.4.8 — October 5, 2026

Within-call observation reuse. This was the first version published to GitHub, on October 6.

- **Changed:** each shared material graph and authored mesh/UV hash is measured once per observation call. Median observation of a 1,289-object scene fell from 41.52 to 22.53 seconds.
- **Qualification:** 171 tests, 169 passed, plus eight native differential edit cases and saved-file recovery. Strict evaluated-UV identity failed and was attributed through an old-runtime control. [Report](docs/archive/releases/OBSERVER_0_4_8_RESULTS.md) · [details](docs/guides/OBSERVATION_PERFORMANCE.md)

## 0.4.7 — October 5, 2026

Terrain helpers.

- **Added:** a protected-core terrain extension recipe and canopy-framing guidance.
- **Result:** all three terrain studies passed native checks and were rejected visually. Accepted art stayed at checkpoint 9.
- **Qualification:** 170 tests, 168 passed. [Report](docs/archive/releases/TERRAIN_0_4_7_RESULTS.md) · [recipe](docs/recipes/TERRAIN_RECIPE.md)

## 0.4.6 — October 5, 2026

Compact observation storage.

- **Added:** optional lossless compact observations (`pack-observation`, or `write_json(..., compact_observation=True)`) that pool repeated UV arrays. The production observation shrank from 214.37 MB to 21.85 MB. Readers must be 0.4.6 or later.
- **Qualification:** 165 tests, 163 passed. [Report](docs/archive/releases/OBSERVATION_0_4_6_RESULTS.md) · [usage](docs/guides/OBSERVATION_STORAGE.md)

## 0.4.5 — October 5, 2026

Roof recipe.

- **Added:** a lapped-course roof profile that derives tile pitch from roof pitch, gauge, thickness and clearance. It removed the production roof's banding, which intersecting tile courses caused, and was published as checkpoint 9.
- **Qualification:** 157 tests, 155 passed. [Report](docs/archive/releases/ROOF_0_4_5_RESULTS.md) · [recipe](docs/recipes/ROOF_RECIPE.md)

## 0.4.4 — October 5, 2026

Ground recipe.

- **Added:** metric corridor masks and evaluated-surface ray snapshots for ground transitions, published as checkpoint 8 after a retained visual rejection.
- **Qualification:** 153 tests, 151 passed. [Report](docs/archive/releases/GROUND_0_4_4_RESULTS.md) · [recipe](docs/recipes/GROUND_RECIPE.md)

## 0.4.3 — October 5, 2026

Broadleaf vegetation study.

- **Added:** a seeded broadleaf recipe with a Blender consumer, published as checkpoint 7. A native-passing candidate whose boundary planting looked too open is retained as a visual rejection.
- **Qualification:** 149 tests, 147 passed. [Report](docs/archive/releases/VEGETATION_0_4_3_RESULTS.md) · [recipe](docs/recipes/VEGETATION_RECIPE.md)

## 0.4.2 — October 5, 2026

Faster resume.

- **Changed:** redundant observation serialization and registry derivation were removed, while full chain verification is kept. A six-checkpoint resume fell from 36.83 to 13.22 seconds.
- **Qualification:** 144 tests, 142 passed. [Report](docs/archive/releases/RESUME_0_4_2_RESULTS.md)

## 0.4.1 — October 5, 2026

Visual rejection and guided production.

- **Added:** `finish-edit --reject-reason` retains a native-passing candidate as `REJECTED_VISUAL` without publishing it.
- **Production:** the interrupted realistic potting shed was adopted into a separate same-agent production project, with five published revisions and one visual rejection.
- **Qualification:** 140 tests, 138 passed. [Report](docs/archive/releases/PRODUCTION_0_4_1_RESULTS.md)

## 0.4.0 — October 5, 2026

Everyday workflow and craft skills.

- **Added:** the `dcc-harness` entry skill and `start`, `resume`, `review`, `begin-edit` and `finish-edit`, with scoped reservations and observed reconciliation. Also added the architecture, materials, environment-assembly and lighting-review skills.
- **Qualification:** 138 tests, 136 passed, from both source and installed wheel. [Report](docs/archive/releases/WORKFLOW_0_4_RESULTS.md) · [usage](docs/guides/EVERYDAY_WORKFLOW.md) · [craft skills](docs/guides/CRAFT_SKILLS.md)

## Realistic comparison — October 5, 2026 (interrupted)

A four-run potting-shed comparison with a fixed scanned kit. An account usage limit stopped it after one partial build, with zero complete builds and zero revisions. [Protocol](docs/studies/REALISM_COMPARISON.md) · [status](docs/studies/REALISM_PROGRESS.md)

## 0.3.0–0.3.1 — October 4, 2026

Native visibility and the UV comparator policy.

- **Added in 0.3.0:** opaque geometric visibility sampled from fixed perspective and orthographic views, recording blocker identities. Quality round v2 binds it to checkpoint, revision and frozen query.
- **Changed in 0.3.1:** comparator policy v3 accepts one adjacent float32 step in tiled evaluated UVs, up to 1e-6, only when the exact source prerequisites hold. Render/viewport modifier divergence is rejected.
- **Qualification:** 123, then 125 tests, plus 25 native cases. [Report](docs/archive/studies/OVERNIGHT_EVALUATION.md) · [assessment](docs/archive/studies/OVERNIGHT_QUALITY_ASSESSMENT.md)

## 0.2.0 — October 4, 2026

Reference-led quality loop.

- **Added:** bounded quality rounds that compare an unchanged candidate with up to three edits and retain critique and verification. The selection is published through the continuity store. Also added a reserved-space (AABB) preflight.
- **Qualification:** 113 tests, 111 passed. [Report](docs/archive/releases/QUALITY_LOOP_RESULTS.md) · [usage](docs/guides/QUALITY_LOOP_USAGE.md)

## 0.1.1 — October 4, 2026

Observation v2.

- **Fixed:** world-oriented extents are measured without world translation. This removes a float32 cancellation that falsely blocked a continuity workflow. Nonfinite coordinates now fail explicitly.
- **Qualification:** 96 tests, 94 passed, plus the native extent fixture `scripts/qualify_continuity_extents.py`. [Results](docs/archive/studies/CONTINUITY_RESULTS.md)

## Continuity comparison — October 4, 2026

Two plain and two continuity workflows, with four fresh sessions each. Fourteen of sixteen stages passed native checks: plain MCP 8/8, continuity 6/8. [Results](docs/archive/studies/CONTINUITY_RESULTS.md) · [protocol](docs/archive/studies/CONTINUITY_EXPERIMENT.md) · [review guide](docs/archive/studies/CONTINUITY_REVIEW.md) · [assessment](docs/archive/studies/QUALITY_AND_ARCHITECTURE_REVIEW.md)

## 0.1.0 — October 4, 2026

Continuity store.

- **Added:** `dcc_harness.continuity`, with numbered native checkpoints, parent-linked observations and checks, cumulative decisions, measured asset and material users, handoffs and retained operation evidence.
- **Qualification:** 90 tests, 88 passed, plus 13 native fixture cases and four scope cases. [Usage](docs/guides/CONTINUITY_USAGE.md) · [validation](docs/archive/releases/VALIDATION.md)

## Short comparison — October 3–4, 2026

Plain MCP, skills, and skills plus a measured loop, with six builds and six fresh revisions. All twelve checkpoints passed common checks. The artist preferred two plain-MCP entries and gave no scores. [Results](docs/archive/studies/BLIND_RESULTS.md) · [protocol](docs/archive/studies/BLIND_TRIALS.md)

## Pilot — October 3, 2026

Three trial skills, the advisory CLI and journal (`init`, `status`, `begin`, `finish`, `check`, `diff`), the native observer and a procedural courtyard fixture. [Usage](docs/archive/historical/PILOT_USAGE.md) · [validation](docs/archive/releases/VALIDATION.md)
