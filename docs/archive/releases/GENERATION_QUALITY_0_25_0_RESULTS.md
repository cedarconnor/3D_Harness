# Generation quality: 0.25.0 qualification

November 15, 2026. Implementation follows the [generation quality plan](../../plans/G_GENERATION_QUALITY.md), items G1 to G8, which followed the owner's [retirement of the investment gate](../../DESIGN_DECISIONS.md#investment-gate-retired--november-14-2026).

Version 0.25.0 adds tools that help an agent produce better 3D and find its own defects: a geometry audit, an all-sides review sheet, a blockout spec with a scene-against-spec check, and a bounded judge loop. It also shortens the entry skill, turns two whole-scene refusals into recorded coverage gaps, and moves the trial tooling out of the wheel.

## What changed

| Item | Change | Guide |
|---|---|---|
| G1 | Entry skill cut from 1,429 to 519 words, with reference files and a skill lint test. Fixed `allowed_material_inputs` rejecting a correct single-input change | [Skill regressions](../../studies/P5_SKILL_REGRESSIONS.md) |
| G2 | Undescribed Geometry Nodes modifiers and empty material slots observe `READY` as listed coverage gaps. Two Blender 5.2 observer fixes | [Coverage gaps](../../guides/EVERYDAY_WORKFLOW.md#coverage-gaps) |
| G3 | `audit`: 18 geometry defect codes under `render`, `game` and `print` profiles | [Audit](../../guides/AUDIT.md) |
| G4 | `review-sheet`: one contact sheet with silhouette, clay, wireframe and backface rows | [Review sheet](../../guides/REVIEW_SHEET.md) |
| G5 | Blockout spec with `spec-check`, `blockout-build` and `spec-compare` | [Blockout spec](../../guides/BLOCKOUT_SPEC.md) |
| G6 | Judge loop: `judge-start`, `judge-round`, `judge-verdict`, `judge-status` and the `dcc-judge-loop` skill | [Judge loop](../../guides/JUDGE_LOOP.md) |
| G7 | Two extension trials, documentation only: geometry-script dropped, StableGen kept as an optional tool | [geometry-script](../../studies/G7_GEOMETRY_SCRIPT_TRIAL.md), [StableGen](../../studies/G7_STABLEGEN_TRIAL.md) |
| G8 | Trial tooling moved to `dcc_harness_trials`, outside the wheel; add-on capabilities frozen at 0.24.0 behaviour; `autonomous` shown first | [Add-on recipes](../../guides/ADDON_RECIPES.md) |

## Observed results

The release check ran on Windows with Python 3.11, MCP SDK 1.26.0 and Blender 5.1.1, against the wheel built from the 0.25.0 tree.

| Check | Observed result | Retained evidence |
|---|---|---|
| Release check | All 22 stages passed | `runs/r025/VERIFICATION.json` |
| Source suite | 885 tests, successful; 2 skipped | `runs/r025/source-tests.log` |
| Installed-wheel suite | 885 tests, successful; 3 skipped; installed import path asserted | `runs/r025/installed-tests.log` |
| Wheel | `dcc_harness-0.25.0-py3-none-any.whl`, SHA-256 `e6e0eeb4734a4e4878a42efab7898cba069e27c0875f4cef0a71a303cb50a45d`; ships none of the trial modules | `runs/r025/wheels/` |
| G2 coverage gaps | `qualify_coverage_gaps.py` passed on Blender 5.1.1 and 5.2.1, from source | `runs/g2-coverage-gaps-2026-11-14/` |
| G3 audit | `qualify_audit.py` passed on 5.1.1 and 5.2.1, from source: 18 defect fixtures each report their own code alone | `runs/g3-audit-2026-11-15/` |
| G4 review sheet | `qualify_review_sheet.py` passed on 5.1.1 and 5.2.1, from source; byte-identical sheets on both | `runs/g4-review-sheet-2026-11-15/` |
| G5 blockout | `qualify_blockout.py` passed on 5.1.1 and 5.2.1, from source | `runs/g5-blockout-2026-11-15/` |
| G6 judge loop | `qualify_judge.py` passed on 5.1.1 and 5.2.1, from source | `runs/g6-judge-loop-2026-11-15/` |
| Skill regressions | All six P5 situations passed with the final entry skill | `runs/p5-rerun-2026-11-15/` |
| Skill verify blocks | `blender-python`, three blocks, passed on 5.1.1 and 5.2.1 | In the G5 run |

The 22 release stages are the source and installed suites, wheel and source-archive builds and parity, clean install, CLI and MCP entry points, bridge export parity, then native config, paths, recipe paths, units, adoption, execution, MCP, the 26-case live matrix, live preservation, live transport, review capabilities and capabilities.

## Agent runs

These are single runs and are directional.

- **Judge loop.** One held-out brief ran to a stop in four rounds, and a fresh agent resumed mid-loop from the record alone ([first run](../../studies/JUDGE_LOOP_FIRST_RUN.md)). It led the owner to narrow the stall rule: a repeated gap forces a change of approach only when less than one point was gained.
- **Plain against harness.** One held-out brief built both ways with the same cameras and budgets. Two blind judges each scored the harness scene 9 of 10 and the plain scene 7, at about twice the builder time; neither file had an `audit` error ([comparison](../../studies/PLAIN_VS_HARNESS_COMPARISON.md)).
- **Production garden.** `audit` found 519 of 1,285 meshes built inside out, and a review sheet of the potting bench shows it. The checkpoint was not repaired.

## Hosted CI

On the pull request that carried G1 to G8, seven of eight hosted jobs passed. The Windows, Python 3.11 job failed once in the installed suite, in `test_detached_job_runs_in_another_process_and_records_failure`: the test removed its temporary folder while the detached child still held `job.log` open. The same job passed on the parallel run of the same commit. The test now waits for the child to release the file.

## Limits and what was not done

- **The per-item native qualifications ran from source, before the version bump.** The release check exercises the older qualifications against the installed 0.25.0 wheel; the G2 to G6 scripts are not yet part of it. Their code did not change after they passed, apart from the judge loop's stall rule, which was requalified.
- **The release check ran on Blender 5.1.1 only.** The G2 to G6 qualifications also passed on 5.2.1.
- **Projects holding observations from before 0.24.0 still refuse `begin-edit`,** because the observer records more than it did. Only the P5 packet builder works around this.
- **Shader graphs past the reader's limits or with animation, vertex, face and particle instancing, and library overrides still refuse a scene.**
- **`review-sheet` was not used by any agent in the P5 rerun,** so its clause in the entry skill is untested where it applies.
- **Judge loop scores and side-by-side scores are not calibrated to each other.** The loop's judges scored a scene 7 that two blind judges scored 9.
- **Breaking change.** `python -m dcc_harness.blind`, `.blind_review`, `.continuity_trial`, `.continuity_review` and `.session_cost` are now `dcc_harness_trials.*` and run from a checkout. They were outside the runtime digest, so pinned projects are unaffected.
- **Existing projects keep their pinned runtime.** The version change gives new projects a new runtime digest.
- **None of this is artist acceptance.** A judge score is an agent's opinion, and an audit finds defects in geometry; neither says the work is good.

## Follow-ups

- Add the G2 to G6 qualifications to `verify_release.py`.
- Read `modifier.node_warnings` in the Geometry Nodes verify step.
- A craft-skill reference for texturing one object with StableGen.
- Re-baseline for projects holding pre-0.24 observations.
