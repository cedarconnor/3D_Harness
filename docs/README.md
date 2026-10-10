# Documentation index

Updated October 10, 2026, for version 0.7.0. Start with the repository [README](../README.md), then the [everyday workflow](guides/EVERYDAY_WORKFLOW.md). Agents continuing a project start with `brief` and the [agent quick reference](guides/AGENT_QUICK_REFERENCE.md). The [build plan](BUILD_PLAN.md) tracks current status and next work; the [changelog](../CHANGELOG.md) lists what each version delivered.

Documents are split by whether they are still in use:

| Folder | Holds |
|---|---|
| `docs/` | The tracked [build plan](BUILD_PLAN.md), the [decision log](DESIGN_DECISIONS.md) and this index |
| [`guides/`](guides/) | How to use current features |
| [`recipes/`](recipes/) | Bounded construction helpers used by the craft skills |
| [`studies/`](studies/) | Open evaluation work: the interrupted realistic comparison and the artist review session |
| [`reference/`](reference/) | Research and designs behind upcoming stages |
| `plans/` | Implementation plans for active tracked items, created when work starts and archived when it finishes; currently [P9](plans/P9_AGENT_GUIDANCE.md) |
| [`archive/`](archive/) | Work already addressed: release reports, completed studies, implemented plans and superseded inputs |

Archived documents stay as written. They remain the evidence for the claims in the plan, README and changelog; only their links were updated when files moved.

## Guides

| Document | Covers | Since |
|---|---|---|
| [Agent quick reference](guides/AGENT_QUICK_REFERENCE.md) | `brief`, `next`, `requirements` and the exact sequences for an edit, a feedback response and a stage submission | 0.7.0 |
| [Everyday workflow](guides/EVERYDAY_WORKFLOW.md) | `start`, `resume`, `review`, `begin-edit`, `finish-edit`, reconciliation and locks | 0.4.0 |
| [Scene adoption](guides/SCENE_ADOPTION.md) | `adopt-preview` and `adopt-apply` for saved scenes without stable IDs | 0.4.9 |
| [External revisions](guides/EXTERNAL_REVISIONS.md) | `preview-revision` and `accept-revision` for deliberate saved edits | 0.4.10 |
| [Structured feedback and environment stages](guides/STRUCTURED_FEEDBACK.md) | Feedback notes, verification, workflow binding and stage commands | 0.5.0 |
| [Continuity APIs](guides/CONTINUITY_USAGE.md) | The continuity store's Python API and comparison usage | 0.1.0 |
| [Quality loop](guides/QUALITY_LOOP_USAGE.md) | Reference-led rounds, reserved-space preflight and visibility probes | 0.2.0 |
| [Observation storage](guides/OBSERVATION_STORAGE.md) | Compact, lossless observation files | 0.4.6 |
| [Observation performance](guides/OBSERVATION_PERFORMANCE.md) | Within-call reuse and its limits | 0.4.8 |
| [Craft skills](guides/CRAFT_SKILLS.md) | What the architecture, materials, assembly and lighting skills support, and what they do not | 0.4.0 |

## Recipes

Each was qualified on one production scene: [ground](recipes/GROUND_RECIPE.md), [roof laps](recipes/ROOF_RECIPE.md), [terrain](recipes/TERRAIN_RECIPE.md) and [broadleaf vegetation](recipes/VEGETATION_RECIPE.md).

## Open studies

| Document | Status |
|---|---|
| [Artist review session](studies/ARTIST_REVIEW_SESSION.md) | Protocol for build-plan items E1–E3: scores, timed repair and ranked pairs from finished work |
| [Realistic comparison](studies/REALISM_COMPARISON.md) and [progress](studies/REALISM_PROGRESS.md) | Interrupted after one partial build. Resuming or retiring it is item E4. |

## Reference

| Document | Use |
|---|---|
| [Repository ideas](reference/REPOSITORY_IDEAS_2026-10-06.md) | Source comparison with seven external projects; the basis for P2 and P4–P8 |
| [Motion harness review](reference/MOTION_HARNESS_REVIEW_2026-10-10.md) | Gated motion-design harness compared with this one; the basis for P9–P12 and M5 |
| [Research](reference/DCC_HARNESS_RESEARCH.md) | External evidence behind the decisions, dated October 3 |
| [Skill system](reference/DCC_HARNESS_SKILL_SYSTEM.md) | Skill catalog and motion-design expansion for stage E |
| [Packaging and entry points](reference/DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md) | Client packages, connectors and hooks for stage E |
| [UE-MCP review](reference/DCC_HARNESS_UE_MCP_REVIEW.md) | Unreal integration study for stage E |

## Archive: release reports

One report per version. The [changelog](../CHANGELOG.md) summarizes counts and native evidence, and the [scripts index](../scripts/README.md) maps versions to their qualification scripts.

| Version | Report |
|---|---|
| Pilot to 0.1.1 | [Validation](archive/releases/VALIDATION.md); see also the [continuity results](archive/studies/CONTINUITY_RESULTS.md) |
| 0.2.0 | [Quality loop](archive/releases/QUALITY_LOOP_RESULTS.md) |
| 0.3.0–0.3.1 | [Overnight evaluation](archive/studies/OVERNIGHT_EVALUATION.md) |
| 0.4.0 | [Everyday workflow and craft](archive/releases/WORKFLOW_0_4_RESULTS.md) |
| 0.4.1 | [Guided production](archive/releases/PRODUCTION_0_4_1_RESULTS.md) |
| 0.4.2 | [Resume performance](archive/releases/RESUME_0_4_2_RESULTS.md) |
| 0.4.3 | [Vegetation](archive/releases/VEGETATION_0_4_3_RESULTS.md) |
| 0.4.4 | [Ground](archive/releases/GROUND_0_4_4_RESULTS.md) |
| 0.4.5 | [Roof](archive/releases/ROOF_0_4_5_RESULTS.md) |
| 0.4.6 | [Observation storage](archive/releases/OBSERVATION_0_4_6_RESULTS.md) |
| 0.4.7 | [Terrain](archive/releases/TERRAIN_0_4_7_RESULTS.md) |
| 0.4.8 | [Observer reuse](archive/releases/OBSERVER_0_4_8_RESULTS.md) |
| 0.4.9 | [Adoption](archive/releases/ADOPTION_0_4_9_RESULTS.md) |
| 0.4.10 | [External revisions](archive/releases/REVISIONS_0_4_10_RESULTS.md) |
| 0.5.0 | [Structured feedback](archive/releases/FEEDBACK_0_5_0_RESULTS.md) |
| 0.5.1 | [Correctness maintenance](archive/releases/MAINTENANCE_0_5_1_RESULTS.md) |
| 0.6.0 | [Lower step cost](archive/releases/STEP_COST_0_6_0_RESULTS.md) |

## Archive: completed studies

| Study | Protocol | Results and review |
|---|---|---|
| Short comparison, October 3–4 | [Trial protocol](archive/studies/BLIND_TRIALS.md) | [Results](archive/studies/BLIND_RESULTS.md) |
| Continuity comparison, October 4 | [Experiment protocol](archive/studies/CONTINUITY_EXPERIMENT.md) | [Results](archive/studies/CONTINUITY_RESULTS.md), [review guide](archive/studies/CONTINUITY_REVIEW.md), [coordinator assessment](archive/studies/QUALITY_AND_ARCHITECTURE_REVIEW.md) |
| Overnight courtyard, October 4 | [Evaluation](archive/studies/OVERNIGHT_EVALUATION.md) | [Quality assessment](archive/studies/OVERNIGHT_QUALITY_ASSESSMENT.md) |

Artist scoring for the first two studies is still open; it is item E1.

## Archive: plans and superseded inputs

These are not implementation authority. Their example APIs and status claims may be unimplemented or superseded.

- [P1 plan](archive/plans/P1_LOWER_STEP_COST.md), implemented in 0.6.0.
- [Structured feedback plan](archive/plans/STRUCTURED_FEEDBACK_ENVIRONMENT_WORKFLOW.md), implemented in 0.5.0. Its draft JSON is not the current payload format.
- The October 3 build plans: [version 2](archive/plans/DCC_HARNESS_BUILD_PLAN_v2_2026-10-03.txt) and [version 3](archive/plans/DCC_HARNESS_BUILD_PLAN_v3_2026-10-06.txt), the latter with status notes through 0.5.0.
- The [original architecture note](archive/historical/llm-dcc-agent-architecture.md), the supplied starting proposal. [D9](DESIGN_DECISIONS.md#d9-sources-and-document-authority) records its status.
- The [document review](archive/historical/DCC_HARNESS_DOCUMENT_REVIEW.md), a one-time review of that note and the draft skills. Its findings were absorbed into D1–D9.
- [Claude's proposal feedback](archive/historical/CLAUDE_PROPOSAL_FEEDBACK_2026-10-03.txt), the critique that D1–D9 answer.
- [Pilot usage](archive/historical/PILOT_USAGE.md), covering the October 3 pilot and its legacy `init`, `status`, `begin` and `finish` journal commands.
- [Draft skills](archive/historical/dcc-skills/), which call APIs that were never built.

## Local evidence links

Many reports link into `runs/` or `dist/`: native files, galleries, logs and wheels. Those folders are excluded from Git, so the links resolve only on the machine that produced them. The written reports, hashes and the [README render](images/README.md) are committed.
