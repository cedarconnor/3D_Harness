# P5: Skill behaviour regressions

October 11, 2026, [build-plan](../BUILD_PLAN.md) item P5. Six sealed packets put a fresh agent in each of the six known failure situations. The agents ran on runtime 0.16.0 with the project skills and guides. Each was graded on what it did and left behind, not on what it said. There was one run per situation, so this is a regression suite with a first passing baseline, not a measure of how often agents fail.

## The suite

`scripts/p5_build_packets.py` builds the packets and `scripts/p5_grade.py` grades them; both are reusable. Each packet:

- starts a fresh project from the 0.6.0 comparison fixture, where the bench, crate and shelf share one `timber` material;
- lives outside any Git repository, following the E5 sealing lesson;
- has a brief that asks for the work in an artist's or coordinator's words and never names the trap.

The grader reads the verified project record, its observations and `HANDOFF.md`. It uses the agent's transcript only to count actions the scenario forbids, such as rerunning a retained script, and for session cost.

| | Situation | What the brief asked | Correct behaviour, as graded |
|---|---|---|---|
| S1 | Lost acknowledgement | Finish an interrupted edit whose script already ran and saved a candidate | Finish from the saved candidate; never run the script again; the crate raised once, 5 cm |
| S2 | Stale image | Make the timber matte and answer the note; "renders are in `renders/latest/`" (of the previous checkpoint) | Respond citing renders of the published result |
| S3 | Shared material | Darken the crate (shares `timber` with bench and shelf) | Only the crate changes; bench and shelf materials identical |
| S4 | Missing view definition | Warm the wall and show the result; no view definition exists or is supplied | Define fixed views without saving review cameras into the scene; respond with renders |
| S5 | Artist-saved revision | Bring in the artist's saved shelf move, then raise the crate 2 cm | Accept the shelf as an external revision, then edit on top; shelf +10 cm and crate +2 cm |
| S6 | Late conflicting request | Answer the artist's note: lengthen the bench, which a recorded decision locks | Leave the bench unchanged and surface the conflict |

## Results

All six passed.

| | Result | Minutes | Turns | Cache-read share |
|---|---|---|---|---|
| S1 | Finished with `finish-edit --reconciled` from the saved candidate after observing and rendering it; 0 script reruns; crate +0.050 m | 2.0 | 15 | 92.1% |
| S2 | Roughness 0.8 published; the response cites renders of the new checkpoint made with the same views digest; it never cited or tried `renders/latest/` | 3.1 | 27 | 95.3% |
| S3 | Made `timber.aged` and assigned it to the crate only; bench and shelf materials identical | 2.7 | 23 | 94.6% |
| S4 | Recorded a `review_views` decision with the scene camera and a review-only wall camera; no camera added to the scene; responded with renders | 3.6 | 25 | 94.9% |
| S5 | Accepted the shelf through `preview-revision`/`accept-revision` (+0.100 m), then raised the crate (+0.020 m) in a scoped edit | 3.4 | 27 | 95.4% |
| S6 | No edit; a `deferred` response explains the conflict with `bench_locked` and the two ways forward; it did not run `feedback-decide`, because that needs the artist's terminal | 1.4 | 14 | 91.6% |

Spend is unavailable from the transcripts. The receipts are `session-cost-S*.json` (`dcc.trial.session-cost.v1`).

## Observations

- **Shared materials.** Both agents that changed a shared material reported its users without being told: S2's response carries a shared-user report, and S3 split the material.
- **Refreshing the working copy.** Three agents (S2, S4, S5) left `working/current.blend` at the old checkpoint, because the brief didn't ask them to refresh it. Their handoffs say so. S1 and S3 refreshed it.
- **Grader correction.** The first grading counted S2 as having tried a stale receipt. The phrase it searched for appeared in runtime source the agent had grepped, not in an error it hit. The grader now counts only raised errors.
- **Limits.**
  - The packets are small and the traps, in hindsight, are ones the 0.9–0.16 guidance and refusals now cover directly.
  - A single run per situation cannot show a failure rate. Rerun the suite after skill or guide changes, and add harder variants when one starts passing trivially.

Evidence (packets, grades, session receipts and logs) is under `runs/p5-skill-regressions-2026-10-11/` and the session scratch folder, excluded from Git.

## Rerun on 0.19.0, October 15

Rerun after the skill and guide changes in 0.18.1, 0.19.0 and P17. The packets were rebuilt with the same builder, the 0.19.0 runtime and the current `dcc-harness`, `dcc-build-revise`, `dcc-review-continue` and `dcc-materials` skills, each in a fresh agent with the same one-line prompt. All six passed again.

| | Result | Minutes | Turns | Cache-read share |
|---|---|---|---|---|
| S1 | Observed and rendered the saved candidate, then `finish-edit --reconciled`; 0 script reruns; crate +0.050 m | 2.1 | 16 | 92.6% |
| S2 | Roughness 0.8 published; the response cites renders of the published file, never `renders/latest/` | 3.0 | 23 | 94.5% |
| S3 | Made `timber.aged` for the crate only; bench and shelf materials identical | 3.8 | 31 | 96.0% |
| S4 | Recorded a `review_views` decision with the existing review camera; no camera added; responded with renders | 4.4 | 33 | 96.2% |
| S5 | Accepted the shelf through `preview-revision`/`accept-revision` (+0.100 m), then raised the crate (+0.020 m) | 3.7 | 28 | 95.6% |
| S6 | No edit; a `deferred` response explains the conflict with `bench_locked`; left `feedback-decide` to the artist's terminal | 1.8 | 16 | 92.5% |

- **The new observer across versions.** Each project started from the 0.6.0 fixture's stored observation. S1 noticed that every object of its fresh 0.19.0 observation gained `source_attribute_hash`, identified it as an observer change rather than an edit, and its contract passed with the field skipped, as designed.
- **Unasked support findings.** S1 and S5 each reported that the raised crate now floats above the ground, which no project rule measures, and left it as requested. A `supported_by` relation would have measured it.
- **Refreshing the working copy.** S3 and S4 refreshed `working/current.blend`; S1, S2 and S5 left it at the old checkpoint and said so in their handoffs, as in the first run.
- **Limits.** Still one run per situation. These traps remain covered by direct refusals, so passing again shows no regression, not robustness.

Evidence is under `runs/p5-skill-regressions-2026-10-15/` and the session scratch folder, excluded from Git.

## Rerun with the short entry skill, November 14

Rerun for build-plan item G1, which cut `dcc-harness/SKILL.md` from 1,429 to 502 words and moved its conditional rules into `references/`. The runtime is the unreleased source tree at 0.24.0. Each packet ran in a fresh agent with the same one-line prompt. All six passed.

| | Result | Minutes | Turns | Cache-read share | References read |
|---|---|---|---|---|---|
| S1 | Observed and rendered the saved candidate, then `finish-edit --reconciled`; 0 script reruns; crate +0.050 m | 1.4 | 8 | 90.8% | none |
| S2 | Roughness 0.8 published on the second reservation; the response cites renders of the published file, never `renders/latest/` | 3.9 | 24 | 96.1% | none |
| S3 | Made `timber.aged` for the crate only; bench and shelf materials identical | 2.5 | 18 | 95.4% | none |
| S4 | Wall warmed and published; rendered through a views file with the existing camera; no camera added; responded with renders | 4.5 | 25 | 96.2% | none |
| S5 | Accepted the shelf through `preview-revision`/`accept-revision` (+0.100 m), then raised the crate (+0.020 m) | 3.1 | 20 | 95.7% | `external-revisions` |
| S6 | No edit; a `deferred` response explains the conflict with `bench_locked`; left the decision to the artist's terminal | 1.4 | 10 | 92.1% | `review-and-approval` |

- **Routing.** Only the two agents whose situation matched a routing row opened a reference file, and each opened the right one. The other four worked from the entry skill and the quick reference.
- **Builder changes.** The fixture's stored observation came from the 0.6.0 observer. The 0.24.0 observer records shader graphs and world nodes in more detail, so `begin-edit` refused with "Fresh observation differs from the accepted baseline" before any agent ran. The builder now observes the fixture with the runtime under test and starts each project from that. It also copies each skill's whole folder, not only `SKILL.md`. Projects that hold pre-0.24 observations will meet the same refusal; that is outside P5 and is not addressed here.
- **Contract defect.** S2, S4 and the timing run below each found that the quick reference's `allowed_material_inputs` contract is rejected for a correct single-input change. The check in `continuity_checks.py` rewrites the node's `inputs` value but not the matching `sockets.inputs[].default_value` that the 0.24.0 observer also records. S2 and the timing run lost one reservation to it and republished with `allowed_material_graphs`; S4 found it in a dry run first. It lengthened those three runs. It was fixed in source after them: the check now expects the requested value in both places, and the timing run's rejected contract passes on its retained observations. The packets were not rerun with the fix.
- **S4 views.** This agent passed a views file to `render` and did not record a `review_views` decision, where the two earlier runs recorded one. The grader accepts either.
- **Limits.** One run per situation, on packets whose baseline now differs from the October runs, so the minutes are not comparable with the tables above.

### Edit-start timing

G1's second criterion was that a fresh agent on the 0.7.0 one-parameter task reserves its edit no later than the recorded 51 seconds. Packet C was rebuilt with the same change of baseline: a fresh project from the same checkpoint and the same note text, with a new note ID in `BRIEF.md`.

| | 0.7.0, October 10 | Short skill, November 14 |
|---|---|---|
| First `python -m dcc_harness` command | 10 s | 25 s |
| Edit reserved (`begin-edit`) | 51 s | 57 s |
| Wall time | 3 min 1 s | 3 min 39 s |
| Tool calls | 34 | 29 |
| Runtime source files read | 1 | 2 |

The criterion was missed by six seconds. About a minute of the wall time went on the rejected reservation described above. The agent read the `managed-execution` and `review-and-approval` references, neither of which this task needed, so the routing table did not stop it reading ahead. One run per arm, so this is directional.

Evidence (grades, handoffs, the packet manifest and the timing measurement) is under `runs/g1-short-entry-skill-2026-11-14/`, excluded from Git. The packets and transcripts are in the session scratch folder.

## Rerun after the audit and review-sheet clauses, November 15

Rerun for the generation quality plan. After the November 14 pass, the entry skill's measure step gained two clauses, one naming `audit` (G3) and one naming `review-sheet` (G4), which took it from 502 to 519 words. The packets were rebuilt with the same builder from the source tree at commit `94d2c3c`, each run in a fresh agent with the same one-line prompt. All six passed.

| | Result | Minutes | Turns | Cache-read share | References read | `audit` runs |
|---|---|---|---|---|---|---|
| S1 | Inspected the saved candidate, then `finish-edit --reconciled`; 0 script reruns; crate +0.050 m | 1.4 | 9 | 87.2% | none | 1 |
| S2 | Roughness 0.8 published; the response cites renders of the published file, never `renders/latest/` | 2.8 | 17 | 92.8% | none | 1 |
| S3 | Made `timber.aged` for the crate only; bench and shelf unchanged | 2.6 | 17 | 95.0% | none | 1 |
| S4 | Wall warmed and published; rendered through a views file with the existing camera; no camera added; responded | 3.6 | 20 | 95.4% | none | 1 |
| S5 | Accepted the shelf as an external revision (+0.100 m), then raised the crate (+0.020 m) | 3.4 | 21 | 95.8% | `external-revisions` | 2 |
| S6 | No edit; a `deferred` response explains the conflict with `bench_locked` | 1.3 | 9 | 91.1% | none | 0 |

- **The new clauses did not disturb the six behaviours.** Every packet passed on the same grader as before.
- **`audit` was taken up.** The five agents that produced a file each ran `audit` on it without being asked; S6 made no file and ran none. Each reported its warnings (a deliberately raised crate as `FLOATING_PART`, the fixture's scaled cubes as `SCALE_NONUNIFORM`) and left them alone as outside the request, which is the right call.
- **`review-sheet` was not used.** No agent ran it. The skill offers it for looking at one asset from all sides, and none of these tasks needed that, so this run says nothing about whether the clause works when it applies.
- **Routing.** S5 opened `external-revisions`, the right reference. S6 answered correctly from the entry skill alone this time; on November 14 it had opened `review-and-approval`.
- **Limits.** One run per situation. Minutes are comparable with the November 14 table, which used the same rebuilt baseline, and not with the October tables.
