# Judge loop: first run, November 15

One held-out brief run through the [judge loop](../guides/JUDGE_LOOP.md) to a stop condition, and one sealed resume test. One run each, so the results are directional. The builder was the agent that implemented the loop; each judge was a separate agent that saw only the round's packet. Evidence is retained in `runs/g6-judge-loop-2026-11-15/stool/`.

## The brief

A handmade three-legged wooden milking stool with a small terracotta pot of soil on it, standing on worn stone paving, in low warm late-afternoon sun. Five visual targets (timber, terracotta, paving, light, framing), a four-part [blockout spec](../guides/BLOCKOUT_SPEC.md), and the default pass score of 9. No reference images.

## What happened

| Round | Approach | Code checks | Score | Then |
|---|---|---|---|---|
| 1 | Plain primitives, one flat colour per material | Passed | 4 (2, 1, 1, 0) | Continue |
| 2 | Procedural materials, separate slabs, lathe-turned parts, warmer sun | `spec-compare`: `SIZE parts/legs/size` | Not judged | Fix the checks |
| 3 | Round 2 with the legs splayed to the planned footprint | Passed | 7 (2, 2, 2, 1) | Change approach |
| 4 | Wear painted per vertex, unequal chipped slabs set into the ground, hero view reframed | Passed | 7 (2, 2, 2, 1) | Stop and ask |

Scores are composition, lighting, materials, detail. The loop stopped at round 4 with `stop_ask`: the changed approach gained no points. This was under the original stall rule; see the outcome below.

## What the run showed

- **The code gate caught a real error.** Round 2 randomised the leg splay and came out 0.31 m deep against a planned 0.42 m. The round was recorded as gated and no judge saw it. It cost one of the five rounds.
- **The judge found a defect no code check did.** In round 4 the ground plane was raised to set the paving into it, and it cut through the tilted slabs. `audit` passed, because intersecting surfaces are not a defect it measures. The judge reported it as the paving and ground "passing through each other", which is the symptom; the cause (the ground plane's height against the slabs' tilt) had to be read from the build script.
- **The stall rule fired on a round that gained three points.** Round 3 went from 4 to 7, and the judge still named five of round 1's twelve gaps again, so the record required a change of approach. A judge that lists eight to twelve gaps will almost always repeat one. As specified, "the same gap named twice" makes a change of approach nearly certain after the second judged round, whatever the progress.
- **The forced change then ended the loop.** Round 4's new approach introduced the defect above and scored the same, so the loop stopped with one round unused. Without the forced change, round 4 would have continued refining round 3.
- **Judges kept gap IDs.** Both later judges reused earlier IDs for gaps that remained and coined new ones for new gaps, as the packet asks.

## Sealed resume

A fresh agent was given the loop folder, the `dcc-judge-loop` skill and `judge-status`, while round 4 waited for its verdict. It was told to read nothing else and change nothing, and was asked seven questions.

| Question | Answer |
|---|---|
| What is being made and the targets | Correct, all five targets |
| Rounds used and what happened in each | Correct, including the gated round and its cause |
| The exact next step | Correct: hand packet 4 to a fresh judge, then `judge-verdict`; no building |
| Anything unusual required of the next round | Correct, with one inference: it worked out that round 4's changed approach had been required, and noted the status did not say so |
| Open gaps | Correct, all eight IDs |
| Two things not to do | Correct |
| What a stop means for acceptance | Correct: never acceptance |

Its one inference led to a change: `judge-status` now shows, for each round, what the record required after it.

## Outcome

The owner decided on November 15 that a repeated gap forces a change of approach only when the score also gained less than one point. The rule was changed and requalified. The run above was made under the original rule and its record is kept as it was. Under the new rule the same record replays differently: round 3 continues, and round 4, which repeated gaps and gained nothing, requires a change of approach with one round left, so the loop would not have stopped there.
