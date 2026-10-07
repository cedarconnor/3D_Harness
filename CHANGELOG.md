# Changelog

Each version is a bounded increment with its own qualification report. Test counts are portable-suite results on Windows; the two skips in each count are host symlink-permission cases. Native qualification uses Blender 5.1.1 on Windows. Studies are listed with the versions they exercised. The [build plan](docs/BUILD_PLAN.md) explains what remains open, and reports that link into `runs/` refer to local evidence excluded from Git.

## Unreleased

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
