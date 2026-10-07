# Artist review session

Prepared October 6, 2026, for build-plan items E1–E3. The investment gate needs artist judgments that do not exist yet: scores, repair time and preferences. This session collects them from finished work, without running new trials. Budget about two hours.

A coordinator, either an agent or the user, prepares anonymous copies and keeps the method mapping private. The artist does not read method labels, build logs or this repository's results before scoring. Frozen galleries, score forms and native evidence stay unchanged; every output goes into a new folder.

## Materials

All of these are local and excluded from Git.

| Item | Location |
|---|---|
| Short comparison gallery and blank score form | `runs/blind-round-2026-10-03/review/index.html` and `scores.json` |
| Continuity gallery and blank score form | `runs/continuity-round-2026-10-04/review/index.html` and `scores.json`; see the [review guide](../archive/studies/CONTINUITY_REVIEW.md) |
| Continuity final scenes | `runs/continuity-round-2026-10-04/private/accepted/<run>/s04/scene.blend`; one workflow ends at `s02`. This folder reveals run IDs, so only the coordinator opens it. |
| Production checkpoint 9 | `runs/shed-production-2026-10-05/project/checkpoints/000009/checkpoint.blend` and the [README render](../images/potting-shed.png) |

## E1: scores, about 45 minutes

Score every anonymous entry in both galleries before seeing any method label. Use five points: 1 unusable, 2 needs major rework, 3 a useful foundation needing substantial refinement, 4 usable with minor cleanup, 5 accepted without cleanup. Consider composition, proportion, material coherence, lighting and, for the continuity gallery, whether later stages still belong to the original environment.

Save filled copies of the score forms under new names, keeping the blank originals. Score checkpoint 9 separately against its realistic brief, in `runs/shed-production-2026-10-05/BRIEF.md`.

## E2: timed repair, about 45 minutes

The coordinator copies one complete plain-MCP final and one complete continuity final to anonymous names, such as `repair-A.blend` and `repair-B.blend`, in random order. The artist opens each in Blender and repairs it until they would accept it for the workflow's final request. Stop at 20 minutes per scene.

For each scene, record the minutes spent, the defects fixed, the defects left and whether it reached acceptance. This is a repair-effort baseline on a brief the harness has already seen, not the held-out gate comparison.

## E3: ranked pairs, about 20 minutes

The coordinator prepares about twenty pairs of same-view images from existing renders: gallery entries plus accepted and rejected production candidates. Left/right order is randomized and the key is kept private. The artist picks the better image for the stated brief and marks confidence: sure, lean or tie.

These choices become a held-out calibration set. Agent critics are later scored against them, so never show the choices to a critic.

## Recording

Save everything to a new folder, `runs/artist-review-YYYY-MM-DD/`: filled score files, repair timings, ranked-pair choices and the coordinator's private key. Summarize the results in a new `docs/studies/ARTIST_REVIEW_RESULTS.md`, then mark E1–E3 in the [build plan](../BUILD_PLAN.md).
