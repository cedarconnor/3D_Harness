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
