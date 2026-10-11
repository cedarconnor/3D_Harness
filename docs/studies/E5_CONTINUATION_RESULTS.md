# E5: Fresh-agent continuation on the production garden

October 11, 2026, [build-plan](../BUILD_PLAN.md) item E5. One sealed fresh-agent session continued the production potting-shed garden from its files alone. The agent worked on runtime 0.13.0, against three open feedback notes the task did not list. This is one run of one agent. It measures continuation behavior, not a quality advantage over plain MCP.

## Setup

**The project.** The packet held an owned copy of the production project: nine accepted checkpoints, 1,289 objects and 2.36 million triangles, at checkpoint 9 (`roof-course-clearance`).

**The packet.**

- the 0.13.0 runtime;
- five project skills and seven guides;
- the fixed hero, context and detail views at the original 1280 × 720, 48-sample Cycles settings;
- a brief asking the agent to "address all of their open feedback" without listing it.

The builder is `runs/e5-continuation-2026-10-11/build_packet.py`.

**The notes.** Three controlled notes were recorded in the copy before sealing. They are written in the artist's voice, but their source says they are not an actual artist review.

| Note | Priority | Anchor | Request |
|---|---|---|---|
| Puddle | blocking | checkpoint 8, HERO render, `ext.rain.puddle0` | The dark front-path puddle reads as a hole or stain; make it read as water, or take it out |
| Watering can | blocking | checkpoint 9, HERO render, the four can parts | Move the can off the walk to the paving at the left end of the bench, upright, leaving everything else |
| Door paint | advisory | checkpoint 9, material `sage_paint` | Mute the door paint. The note does not say that 13 other objects share the material |

## Results

| Measure | Result |
|---|---|
| Elapsed | 32.0 minutes of the 90-minute budget |
| Turns and tool calls | 64 model turns, 77 tool calls |
| Tokens | 128 input, 235,076 cache creation, 10,452,086 cache read, 3,961 output; cache-read share 97.8% |
| Metered spend | Unavailable: the transcript reports tokens, not billed cost |
| First harness command (`brief`) | 9 s |
| First render | 113 s, of the unchanged checkpoint, to see the notes' views |
| Inspection before the first edit reservation | 7 min 0 s |
| Runtime source reads | 15 |
| Notes found | 3 of 3; none forgotten. Each has a committed response |
| Edits | 3 reservations, 2 retained as visual rejections and 1 published (checkpoint 10). Each script ran exactly once |
| Native checks | All three candidates passed; the two rejections were visual judgments about the puddle |

The cost figures come from `session-cost.json` (`dcc.trial.session-cost.v1`, written by 0.13.1's `session_cost`). The timings come from the transcript's tool-call times. The output-token count excludes reasoning, which the transcript does not report.

**What it did with each note:**

- **Watering can.** The four parts were moved together with no rotation, to the paving in front of the bench's front-left leg, about 0.17 m from the nearest pot. A contact measurement put the can 0.2 mm above the slabs.
- **Door paint.** The agent found that `sage_paint` is shared by the window frames, fascia and barge boards. It gave the door its own copy, `sage_paint_weathered_door`, which is greyer and less glossy, and left the shared material unchanged. Its response carries a material-user report.
- **Puddle.** It made two materially different attempts to make the puddle read as water: a water material on the original mesh, then a smooth outline with a damp edge. Both still read as a dark oval from the low hero camera, and both were retained as visual rejections. It then hid the object from render rather than deleting it, because the note is anchored to that ID.

**Separate review.** I, the coordinator, verified all three responses as an agent reviewer. The runtime recomputed each response's contract and confirmed the inspected views share the notes' settings digest. Each verification passed:

- **Watering can:** the can stands upright at the bench's left end, clear of the pots, and the walk is clear. The DETAIL view now shows the can's handle and spout at its bottom edge.
- **Puddle:** the front path reads as clean paving.
- **Door:** it reads as an older sage, and nothing else changes colour.

This is not artist acceptance.

## Still for the artist

The agent's handoff and my review agree on these:

- **Second puddle.** `ext.rain.puddle2`, in front of the bench, still reads as a dark stain. It was not in any note.
- **Detail view.** It now catches the top of the can at its lower edge.
- **Door and trim.** The door is now deliberately duller than the window frames and trim; the artist may want both changed.
- **Hidden puddle.** `ext.rain.puddle0` is hidden from render, not deleted.
- **Review views.** They are not recorded as a project decision, so `render --project` cannot find them.

**Remaining artist repair time is not measured.** It needs the artist, so E5's exit criterion is not fully met.

## Findings about the harness

- **Sealing leak.** The packet sat inside this Git repository. Near the end, the agent ran `git status` from the packet and saw uncommitted changes in the parent repository, which were my concurrent work. It wrote nothing outside the packet and reported the leak itself. Future packets should be built outside any repository.
- **Contention.** My own qualification runs overlapped the session on the same machine, so render and observe times inside it are pessimistic.
- **Recording views.** The agent had to pass `--views` because the production project predates `review_views`. A project adopted before 0.8.0 should record the decision.
- **Missing note targets.** The agent hid the puddle rather than deleting it, so the note's verification would not fail on a missing target. The harness rule is sound, but it pushed the agent to leave a hidden object behind. A note's response could allow the target to be removed explicitly; this is worth a P6 follow-up.

Evidence (the packet, transcript metrics, cost receipt and verifications) is under `runs/e5-continuation-2026-10-11/`, excluded from Git.
