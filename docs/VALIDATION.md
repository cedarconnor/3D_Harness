# Pilot qualification — October 3, 2026

Current engineering increment, October 5: [version 0.4.8 native observation optimization](OBSERVER_0_4_8_RESULTS.md), with 171 source/installed tests, eight native differential edit cases, a saved continuation/reconciliation exercise, full production-history comparison and three paired timings. Strict production equality fails on evaluated UV noise also reproduced by the old runtime; the existing policy admits only those differences. [Version 0.4.7](TERRAIN_0_4_7_RESULTS.md) adds protected-core terrain helpers and retains three visually rejected background studies. The accepted garden remains checkpoint 9 from [the 0.4.5 roof repair](ROOF_0_4_5_RESULTS.md). [Lossless storage](OBSERVATION_0_4_6_RESULTS.md), [resume optimization](RESUME_0_4_2_RESULTS.md) and the [production exercise](PRODUCTION_0_4_1_RESULTS.md) remain earlier evidence. The qualification below is historical; its tool availability and counts are not current status.

Earlier increment, October 4: [version 0.3.1 overnight evaluation](OVERNIGHT_EVALUATION.md). Both source and installed-wheel suites ran 125 tests (123 passed, two Windows symlink-permission skips). Eighteen native visibility fixtures and seven scope/UV fixtures passed, including corrections for render/viewport modifier divergence and tiled evaluated-UV float32 noise. Failed creative variants and original validator failures remain recorded; three fresh file-only worker continuations were evaluated independently. An additional saved-mesh probe verifies the six revised tool meshes and actual steel face assignments. Live MCP was unavailable during that evaluation. The [version 0.2.0 quality-loop results](QUALITY_LOOP_RESULTS.md) and earlier qualification below remain historical evidence.

The advisory prototype passed the technical checks below on this workstation. The engineering scene is a compact procedural courtyard with eight mesh asset families and 257 scene objects, including cameras/lights. It is not a production environment or an independent comparison of agent methods.

## Implemented

- Three focused project skills in `.agents/skills/`.
- Python CLI for project setup, intent journaling, status, observed completion/reconciliation, assertions and change reports.
- Blender-side evaluated geometry, identity, material/dependency, camera, light and selected render-state observations with explicit coverage limits.
- New-file checkpoints and immutable JSON evidence; unresolved journal operations block that journal's next dispatch.
- A staged fixture, fixed asset intake, native render/reopen scripts, fault probes, continuation regression and local review-page generator.

## Executed evidence

| Check | Result and scope |
|---|---|
| Live MCP | Connected to Blender 5.1.1 on Windows; original unsaved camera/light scene preserved in a separate recovery .blend before authoring |
| Assert-before-build | Six required geometry targets absent in the initial observation; explicit failing report saved; final target checks passed |
| Courtyard build | Eight asset families, shared materials and three fixed cameras; selected geometry/identity/material requirements passed |
| Late revision | Bench wooden spans changed from 1.9 to 2.1 meters and shared stone tint changed. 31 changed observed fields were allowed; measured placements, cameras and lights were preserved |
| Bounded appearance repair | Visual review found masonry texture lines competing with paver joints. One material-contrast refinement changed only the stone graph; prior candidate retained |
| Native fault injection | Five reversible cases: duplicate instance ID, unexpected placement, lighting drift, missing target ID and missing texture. All detected; original observed revision restored |
| Missing acknowledgement | Simulated native write with withheld journal acknowledgement. A separate Python process refused another dispatch. Native inspection found exactly one object; explicit reconciliation/cleanup restored the scene without replay |
| Reopen | Five checkpoints reopened in separate Blender processes with identical observed revisions; original .blend hashes unchanged by render workers |
| Renders | 15 native stills, 960x540, 32 Cycles samples, OptiX GPU. Sum of timed render calls 39.41 seconds; this excludes process startup, observation, coding and review time |
| Packed dependencies | Three used images packed; final checkpoint rendered after external image paths were redirected to absent files in a disposable process |
| Pixel comparison | Packed/unpacked images were not bitwise identical. Maximum channel difference was 1 in 8-bit output; mean differences were below 0.0001 per channel in all three views. Exact-equality failure and diagnostic measurements are retained; bit-exact rendering is not claimed |
| Starter persistence | Initial checkpoint failed a fresh-process palette assertion. Fix: retain deliberately unused palette materials with fake users. New setup process followed by a different continuation process built the scene and passed checks |
| Core tests | Nine unit tests passed, covering missing/placeholder targets, unknown rules, desired material values, corrupt/nonfinite evidence, forbidden changes, changed coverage, immutable evidence and interrupted/torn journals |
| Skill structure | All three skills passed the skill-creator validator; this checks structure, not independent behavioral effectiveness |
| Built artifact | Wheel built without dependencies; installed into an isolated virtual environment. Its `dcc-harness` console executable checked the final observation from outside the repository successfully |

The packed checkpoint SHA-256 is `0d65615b77575f35a8911b76d5e86fc31d2a318b9981754754568a6df6a79778`.

## Inspect the artifacts

Local run: `runs/engineering-2026-10-03/`. Open `REVIEW.html` for images, matched-view comparison and an optional local review form. The native handoff is `checkpoints/05-portable.blend`; original work is in `checkpoints/user-session-before-harness.blend`. Read `CONTINUE.md` before continuing.

Detailed evidence includes `reports/summary.json`, `reports/native-fault-probes.json`, `reports/03-delta.json`, `reports/04-delta.json`, `reports/unknown-*.json`, `evidence/*-render/report.json`, `evidence/05-packed-render/report.json`, and `operations.jsonl`. The corrected restart fixture is `runs/resume-validation/`; its `reports/resume-check.json` passed. The original `00-start.blend` remains a known failing starter and must not be used as the future comparison input.

Inputs came from the pinned Poly Haven kit in `assets/manifest.json`. The three active images are HDRI, stone base color and stone roughness. The downloaded tangent normal is intentionally unused in the box-projection fixture. No paid generation service was used. Model token/cost metering is unavailable in this run, so no dollar or cost-advantage claim is made.

## Next gate and known limits

There is no unresolved native operation or current connection blocker. This rehearsal itself was not independent: its author saw the architecture, all methods and prior outputs. A subsequent separate-agent comparison is now complete; see [current results](./BLIND_RESULTS.md). Counting repeated executions of the engineering fixture as independent trials would be invalid.

The user should inspect composition, proportions, materials, lighting and editability in all views. Foliage remains simplified and the scene has no production-scale environmental detail. Select or revise the style brief before freezing trial inputs and instructions. Follow the build plan's blinded comparisons and artist scoring; do not expand into the full managed runtime solely because these technical tests passed.

The current journal is single-writer and advisory, not an enforced security boundary or the D4 managed protocol. Its evidence writes are exclusive but not a transactional native save/JSON commit. A partial save or interrupted receipt still needs reconciliation. It does not arbitrate concurrent agents, automatically recover a crashed editor, intercept arbitrary MCP writes or run creative decisions after the chat ends.

The observer is scoped to the active scene and declares unmeasured native fields. Tests establish neither general topology/UV quality nor animation, simulation, cross-DCC transfer, multi-hour autonomy or universal Blender-version compatibility.
## Independent-agent test infrastructure

October 3–4 follow-up: added six balanced, randomized trial packets, frozen input hashes, method-specific skill/helper inclusion, fresh revision packets that exclude builder scripts/transcripts, and an anonymous six-entry artist gallery. Six builders and six different revision agents completed the comparison. All twelve checkpoints and six preservation comparisons passed the uniformly corrected evaluator. See [protocol and commands](./BLIND_TRIALS.md) and [results](./BLIND_RESULTS.md). This comparison is separate from the authored courtyard rehearsal above.

Validation: 36 unit tests ran, 35 passed and one filesystem-symlink test was skipped because Windows denied symlink creation. A separate evaluator auditor ran eleven fresh-process native checks against the final code: four baseline/valid scenes passed; six fault scenes failed, including linked stone input, an unused stone decoy, extra camera, fake mesh sharing, changed lighting and a tiny authored UV edit; a corrupted prior observation aborted before grading. The authored UV change of `5.96e-8` was rejected despite being smaller than the evaluated-noise tolerance. See `runs/blind-fixtures/probe-validation-v4.json`; all source files and native inputs remained unchanged. Corrections enforce the existing frozen brief uniformly and are recorded privately. The earlier anonymous export smoke test used repeated engineering-fixture renders and is not counted as independent creative work. The coordinator/review modules also installed and ran from a wheel in a new virtual environment outside the checkout; templates and skills still require the repository.

The MCP's background endpoint currently cannot resolve the Blender executable. The live MCP connection remains usable; production agents have sequential exclusive writer ownership, separate files and fresh contexts. The known native executable runs read-only evaluations separately. Ambient skill/tool descriptions, the host-provided general memory summary and filesystem access remain shared. No clean-room isolation, double-blinding, unmetered cost advantage or autonomous quality winner is claimed.


The independent audit exposed evaluated bevel UV float noise on unchanged files. The original `1e-7` guard detected a later difference of `1.1920928955078125e-7` on three door components; reopening the unchanged input reproduced it. The final guard permits at most `2e-7`, with exact source mesh/UV, evaluated geometry and modifier state required. All twelve immutable scenes were reobserved uniformly; the original failure and diagnostic command's incorrect-spec-path error remain recorded. No production scene or frozen helper was changed. The final wheel was reinstalled and its updated guard and packet verification exercised outside the checkout. The installed CLI had also frozen an actual completed revision outside the checkout.

The actual comparison export includes 36 images. All exported decoded pixels match their source captures exactly, and the 38-file ZIP passed its integrity check. A fresh reviewer inspected all 36 images and both public text files, finding no method/path leakage or gross framing drift. Artistic scores and native editability remain unassessed. Browser interaction/download was not exercised because the browser tool blocked local file access; source and file/image checks do not establish browser behavior.

## Continuity prototype qualification

October 4: the longer comparison adds immutable checkpoint/decision history, fresh-session packets, cumulative preservation checks and a four-stage review exporter. The implementation and experiment are described in [usage](CONTINUITY_USAGE.md) and [protocol](CONTINUITY_EXPERIMENT.md). Creative comparison execution remains separate from these infrastructure checks.

The updated suite ran 90 tests: 88 passed and two Windows symlink-permission tests were skipped. Native fixture qualification includes 13 cases (three positive and ten expected fault rejections), followed by four cases confirming the narrower change scope and rejection of new light objects. Current-code store integration verified the artist placement event, the plaque at its exact tabletop contact, pending-operation blocking, explicit reconciliation without replay and relocation into a fresh process. No synthetic qualification geometry was copied into production packets.

Evidence: `runs/continuity-fixtures-2026-10-04/qa/qualification.json`, `qa/scope-correction/qualification.json`, and `store-integration-v2/qualification.json`. The earlier receipts remain preserved. The frozen-round 0.1.0 wheel has SHA-256 `52e5eaf3ab7c42f0b9ec37d19536cd823ff214aba9b2652b15ac05fec14c1108`; outside-checkout smoke checks verified all four initial packet seals and a synthetic 102-slot export with no images or assigned scores. See `runs/continuity-round-2026-10-04/private/package-smoke-v2.json`. That synthetic export is packaging evidence only.

An independent coordinator-script audit found and corrected unrecorded-image inclusion, acceptance-hash mismatches counted as passes and missing timing counted as zero. The reviewer reported 18 focused synthetic checks passing afterward. Final production gallery integrity, independent native results and artist preference must be assessed from the completed round, not inferred from these tests.

## Completed continuity round and post-round correction

All sixteen fresh production sessions and original native evaluations finished. Fourteen passed; two incomplete stages remain failures. Ninety-six independent stage renders and six baseline images were exported with identical decoded pixels; the 104-file review ZIP passed integrity and byte-identity checks. See [results and limits](CONTINUITY_RESULTS.md). Artist scores and native editability remain unassessed. The expected original saved scene was restored unchanged, with 257 active-scene objects. The restoration helper initially compared 259 total datablocks against that active-scene count; a separate live scope check resolved the discrepancy without editing the scene.

Version 0.1.1 fixes the reproduced translation-dependent extent error and rejects nonfinite coordinates that extrema could hide. The full suite ran 96 tests: 94 passed and two Windows symlink tests were skipped. The installed wheel has SHA-256 `4cc7066db23d83ef5148e4c80d2daa95b01a538f650bb1e801b2e08a3ea4d20c`. A new isolated environment, run outside the checkout, verified all sixteen packet seals, read both final legacy stores, retained the original v1 failure, accepted the v2 translation measurement and rejected mixed versions and tiny dimensional drift. No original helper, grade or checkpoint was replaced.

The reusable native test is `scripts/qualify_continuity_extents.py`; run it in a disposable factory-startup Blender process with `--repo` and a fresh `--out`. The installed package passed near/far translation preservation, geometry/scale/rotation rejection, empty/degenerate extents and an actual later-vertex NaN rejection. The broader installed native evaluator also matched all 15 expected cases (two passes, thirteen fault rejections), rejected four verified nonfinite injections and preserved native input hashes. Native reports and package provenance are under `runs/continuity-round-2026-10-04/private/`: `post-round-tests.txt`, `package-smoke-v3.json`, `extent-v2-integration.json`, `installed-native-qualification/qualification.json`, and `installed-extent-regression/qualification.json`. These are structural checks, not artistic or multi-DCC qualification.

Two fresh reviewers inspected the public gallery only: each checked 48 distinct stage images and the six baseline images, covering all 102 unique captures. Both found no broken references or explicit method/path leakage and retained blank artist scores. Small tabletop details, partial canopy occlusion and missing later additions in the incomplete sequence remain review findings. Their manifests and reports are in `private/anonymous-qa-1/` and `private/anonymous-qa-2/`. They did not inspect native editability or exercise browser interaction.
