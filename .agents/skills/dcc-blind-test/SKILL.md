---
name: dcc-blind-test
description: Coordinate independent Blender comparison agents, fresh-context revisions and anonymous artist review from frozen 3D Harness trial packets.
---

# Coordinate independent trials

Use this skill as the coordinator when the user asks to run the harness comparison. Read `docs/BLIND_TRIALS.md` for commands and the active build plan for the investment gate. This skill explicitly delegates production to separate agents. Never supply it or the coordinator's history to a trial agent.

For the longer continuity experiment, use `docs/CONTINUITY_EXPERIMENT.md` and `dcc_harness.continuity_trial` instead of the six-run setup below. That protocol has four workflows in two balanced plain/continuity blocks, sixteen requests across four fresh sessions per workflow, cumulative contracts, a scripted artist-edit event and a withheld acknowledgement. Use the same no-history dispatch, exclusive writer, input seals, independent evaluation and failure-retention rules. Freeze all four requests/contracts and method inputs before the first production session. Each session gets a new agent; never resume the earlier worker to simulate context replacement. Controlled events are coordinator-owned and must be supplied equally to both methods. A native recovery simulation does not establish real crash recovery or unattended scheduling.

Prepare a new round using the geometry-free starter, common brief, fixed kit and frozen templates. Before dispatch, verify the six packet hashes, common software/model settings, budgets and independent evaluator. Keep the assignment manifest private. Record actual client metadata when exposed; do not invent token or billing figures.

Use `collaboration.spawn_agent` with `fork_turns="none"` and unchanged model settings for each build. The message supplies only its assigned packet path, instruction to read PROMPT.md, output ownership, deadline and native writer grant. If this host lacks fresh-context delegation, report that limitation rather than silently reusing the current conversation.

Grant only one agent the live Blender writer at a time. Remember and preserve the user's original scene, check whether it is dirty, and restore it after trials. Other agents may evaluate immutable files in their own background processes; they cannot mutate the live scene. Timeouts require outcome inspection, never blind replay. Do not feed one builder another's design, scripts, critiques or scores.

End each builder at its packed pre.blend and CONTINUE.md handoff. Verify its packet, record timing/output hashes and release a revision packet. Spawn a different fresh agent for the revision; a follow-up to the builder is not a context-replacement test. Include only the accepted native scene, handoff, assigned method and frozen revision request. Preserve failures and capped runs instead of replacing them.

Tell every revision agent to treat historical paths in the handoff as informational and open only its local supplied pre.blend. Once it stops, freeze post.blend and CONTINUE.md with the accept-revision command. Independent evaluation reads that accepted snapshot, never a still-mutable agent output.

Apply the same independent native evaluator to every pre/post file. Reserve capture/render budget for evaluation; stop at the ceiling. Record both actual checks and their coverage limits. Hash the evaluator; corrections to enforce already-frozen requirements must apply uniformly and be logged, with no selective feedback to builders.

Export an anonymous six-entry image gallery and keep its mapping outside the artist package. Separate fresh review agents may critique anonymous captures, but cannot grant artist acceptance or score native editability from images. Ask the artist to score the anonymous output before revealing method labels. Gate further infrastructure on both repeats and the held-out brief, not the best render.

Describe the experiment as procedural isolation and a single-blind artist comparison: shared filesystem access and ambient tool/skill descriptions remain available. The packet CLI does not enforce a security sandbox, a spend ceiling or automatic model scheduling. Preserve those limits in the handoff.
