# Documentation index

Updated October 6, 2026, for version 0.5.0. Start with the repository [README](../README.md), then the [everyday workflow](EVERYDAY_WORKFLOW.md). The [build plan](DCC_HARNESS_BUILD_PLAN.md) holds current status and next work; the [changelog](../CHANGELOG.md) lists what each version delivered.

Files stay where they are because skills link to them and `workflow-bind` pins references by relative path. This page supplies the grouping instead.

## Using the harness

| Document | Covers | Since |
|---|---|---|
| [Everyday workflow](EVERYDAY_WORKFLOW.md) | `start`, `resume`, `review`, `begin-edit`, `finish-edit`, reconciliation and locks | 0.4.0 |
| [Scene adoption](SCENE_ADOPTION.md) | `adopt-preview` and `adopt-apply` for saved scenes without stable IDs | 0.4.9 |
| [External revisions](EXTERNAL_REVISIONS.md) | `preview-revision` and `accept-revision` for deliberate saved edits | 0.4.10 |
| [Structured feedback and environment stages](STRUCTURED_FEEDBACK.md) | Feedback notes, verification, workflow binding and stage commands | 0.5.0 |
| [Continuity APIs](CONTINUITY_USAGE.md) | The continuity store's Python API and comparison usage | 0.1.0 |
| [Quality loop](QUALITY_LOOP_USAGE.md) | Reference-led rounds, reserved-space preflight and visibility probes | 0.2.0 |
| [Observation storage](OBSERVATION_STORAGE.md) | Compact, lossless observation files | 0.4.6 |
| [Observation performance](OBSERVATION_PERFORMANCE.md) | Within-call reuse and its limits | 0.4.8 |
| [Craft skills](CRAFT_SKILLS.md) | What the architecture, materials, assembly and lighting skills support and what they do not | 0.4.0 |

## Recipes

Bounded construction helpers, each qualified on one production scene: [ground](GROUND_RECIPE.md), [roof laps](ROOF_RECIPE.md), [terrain](TERRAIN_RECIPE.md) and [broadleaf vegetation](VEGETATION_RECIPE.md).

## Plans and design

| Document | Status |
|---|---|
| [Build plan](DCC_HARNESS_BUILD_PLAN.md) | Active. It owns sequencing, gates and budgets. |
| [Design decisions](DESIGN_DECISIONS.md) | Active decision log, D1–D17, with a status table. |
| [Structured feedback plan](plans/STRUCTURED_FEEDBACK_ENVIRONMENT_WORKFLOW.md) | Implemented in 0.5.0. It is kept as the design record; its draft JSON is not the current payload format. |
| [Repository ideas](../research/REPOSITORY_IDEAS_2026-10-06.md) | Source comparison with seven external projects. It is the basis for several ranked increments. |
| [Research](DCC_HARNESS_RESEARCH.md) | Reference: external evidence behind the decisions, dated October 3. |
| [Skill system](DCC_HARNESS_SKILL_SYSTEM.md) | Reference for stage E: the skill catalog and motion-design expansion. |
| [Packaging and entry points](DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md) | Reference for stage E: client packages, connectors and hooks. Deferred. |
| [UE-MCP review](DCC_HARNESS_UE_MCP_REVIEW.md) | Reference for stage E: the Unreal integration study. Deferred. |

## Qualification reports

One report per version. Counts and native evidence are summarized in the [changelog](../CHANGELOG.md).

| Version | Report |
|---|---|
| Pilot to 0.1.1 | [Validation](VALIDATION.md) and [continuity results](CONTINUITY_RESULTS.md) |
| 0.2.0 | [Quality loop results](QUALITY_LOOP_RESULTS.md) |
| 0.3.0–0.3.1 | [Overnight evaluation](OVERNIGHT_EVALUATION.md) |
| 0.4.0 | [Everyday workflow and craft](WORKFLOW_0_4_RESULTS.md) |
| 0.4.1 | [Guided production](PRODUCTION_0_4_1_RESULTS.md) |
| 0.4.2 | [Resume performance](RESUME_0_4_2_RESULTS.md) |
| 0.4.3 | [Vegetation](VEGETATION_0_4_3_RESULTS.md) |
| 0.4.4 | [Ground](GROUND_0_4_4_RESULTS.md) |
| 0.4.5 | [Roof](ROOF_0_4_5_RESULTS.md) |
| 0.4.6 | [Observation storage](OBSERVATION_0_4_6_RESULTS.md) |
| 0.4.7 | [Terrain](TERRAIN_0_4_7_RESULTS.md) |
| 0.4.8 | [Observer reuse](OBSERVER_0_4_8_RESULTS.md) |
| 0.4.9 | [Adoption](ADOPTION_0_4_9_RESULTS.md) |
| 0.4.10 | [External revisions](REVISIONS_0_4_10_RESULTS.md) |
| 0.5.0 | [Structured feedback](FEEDBACK_0_5_0_RESULTS.md) |

The [scripts index](../scripts/README.md) maps each version to its native qualification scripts.

## Comparisons and assessments

| Study | Protocol | Results and review |
|---|---|---|
| Short comparison, October 3–4 | [Trial protocol](BLIND_TRIALS.md) | [Results](BLIND_RESULTS.md) |
| Continuity comparison, October 4 | [Experiment protocol](CONTINUITY_EXPERIMENT.md) | [Results](CONTINUITY_RESULTS.md), [review guide](CONTINUITY_REVIEW.md), [coordinator assessment](QUALITY_AND_ARCHITECTURE_REVIEW.md) |
| Overnight courtyard, October 4 | [Evaluation](OVERNIGHT_EVALUATION.md) | [Quality assessment](OVERNIGHT_QUALITY_ASSESSMENT.md) |
| Realistic comparison, October 5 (interrupted) | [Protocol](REALISM_COMPARISON.md) | [Progress and image review](REALISM_PROGRESS.md) |

## Historical inputs

These documents are not implementation authority. Their example APIs and status claims may be unimplemented or superseded.

- [Original architecture note](llm-dcc-agent-architecture.md), the supplied starting proposal. [D9](DESIGN_DECISIONS.md#d9-sources-and-document-authority) records its status.
- [Document review](DCC_HARNESS_DOCUMENT_REVIEW.md), a one-time review of that note and the draft skills. Its findings were absorbed into D1–D9.
- [Pilot usage](PILOT_USAGE.md) covers the October 3 pilot and its legacy `init`, `status`, `begin` and `finish` journal commands.
- [`dcc-skills/`](../dcc-skills/) holds draft skills that call APIs that were never built.
- [`research/archive/`](../research/archive/) holds earlier build plans, and [`research/CLAUDE_PROPOSAL_FEEDBACK_2026-10-03.txt`](../research/CLAUDE_PROPOSAL_FEEDBACK_2026-10-03.txt) is the critique that D1–D9 answer.

## Local evidence links

Many reports link into `runs/` or `dist/`: native files, galleries, logs and wheels. Those folders are excluded from Git, so the links resolve only on the machine that produced them. The written reports, hashes and the [README render](images/README.md) are committed.
