# Plain against harness: one comparison, November 15

The generation quality plan's own check: one held-out brief built twice, once with plain Blender scripting and once with the harness, with the same cameras and budgets. The plan says to keep both results whatever they show. This is one brief, one build per arm and one model, so it is a single data point. Evidence is retained in `runs/g-comparison-2026-11-15/`.

## Setup

- **Brief.** A galvanised metal watering can on a weathered wooden crate, with a coiled green garden hose beside it, on a gravel path, in overcast daylight. Six stated targets (can, crate, hose, ground, light, framing). Not used in any earlier run.
- **Common to both arms.** Blender 5.2.1 in the background, Python only, no downloaded assets, the same two fixed cameras in `views.json`, a 30-minute budget and at most five build-and-look rounds. Each arm was a fresh agent given the same one-line prompt pointing at its folder.
- **Plain arm.** The brief, the views file and a small render helper. No harness runtime, skills or guides. In place of a live Blender MCP session it ran scripts in background Blender, which is the same access the harness arm had.
- **Harness arm.** The same, plus the runtime, skills and guides at commit `3545e26`, and an instruction to use the judge loop. Each time it reached a judging step it stopped; a separate fresh agent judged the packet, and the verdict was sent back.
- **Scoring.** Both final files were audited with `audit` and rendered through the same views by the same command. Two fresh judges each scored both scenes on the loop's rubric from the renders alone, with neutral labels and without being told which builder made which; the second judge was shown them in the opposite order.

## Results

| | Plain | Harness |
|---|---|---|
| Blind judge one (composition, lighting, materials, detail) | 7 (2, 2, 2, 1) | 9 (3, 3, 2, 1) |
| Blind judge two | 7 (2, 2, 2, 1) | 9 (3, 2, 3, 1) |
| Preferred by | neither judge | both judges |
| `audit` errors at finish | 0 | 0 |
| `audit` warnings at finish | 1 | 2 |
| Build-and-look rounds used | 2 of 5 | 3 of 5 |
| Builder working time | 10.8 min | 19.9 min |
| Builder tokens, as reported | 137,886 | 193,820 |
| Judge tokens during the build | none | 254,929 across three judges |
| How it ended | The builder judged itself done | The loop stopped itself: `stop_ask` |

The harness arm's loop judges scored its three rounds 7, 7 and 7. Round 2 repeated gaps with no gain, so the loop required a change of approach; round 3 changed approach and also gained nothing, so the loop stopped and asked.

## What the judges said

Both judges gave the same reasons, independently.

- **For the harness scene:** clearer contact shadows, a more convincing weathered crate with visible grain and slat gaps, a looser hose coil, and the whole arrangement in frame.
- **Against the plain scene:** the hose runs out of frame at the left edge, the crate boards are blurred with little grain, the can's galvanised pattern is oversized and chalky, and contact shadows are faint.
- **For the plain scene:** both judges said its rose is better, brass with visible perforations. The harness scene's rose is a plain cone, which its own loop judges had also named and the builder did not fix.

## What it shows, and what it does not

- **On this brief the harness arm produced the better picture by two points of ten, at roughly twice the builder time and with three extra judge runs.** Counting the loop judges, it used about three times the tokens.
- **Neither arm had a geometry error at finish.** `audit` found nothing to prevent in the plain arm's file, so this run gives no evidence that the code checks improved the result. The harness arm ran them every round and they passed every round.
- **The loop's judges and the blind judges disagree on the same scene.** The loop judges, asked to list gaps against the targets, scored the harness arm's final round 7. The blind judges, scoring two scenes side by side, gave it 9. The rubric is not calibrated between those two uses, so a loop score should not be read as the score a comparison would give. With a pass score of 9, the loop would have stopped as met if its own judges had scored as the blind ones did.
- **The stall rule ended the loop while the result was already good.** Three rounds at 7 triggered `stop_ask`. The builder's notes say rounds 2 and 3 fixed named gaps while the judge raised new ones, which kept the total flat.
- **The likeliest reason for the difference is the extra rounds with outside criticism,** not any single tool. The plain builder stopped after two rounds, satisfied with its own renders; the faults the blind judges then named (cropped hose, faint shadows, oversized pattern) are ones an outside judge would have raised.
- **It does not show that the harness wins in general.** One brief, one run per arm. A second run could reverse it.

## Other things that happened

- The plain builder's first render wrote two images outside its folder, to `C:\r1`, by passing a relative output path that Blender resolved against the drive root. Its attempt to delete them was blocked. The harness `render` command takes a new output folder and would not have done this.
- The native release check was running on the same machine throughout, so both arms' times are slower than they would be alone.
