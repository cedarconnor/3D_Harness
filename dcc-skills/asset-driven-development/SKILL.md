---
name: asset-driven-development
description: Use when executing an asset build plan with mostly independent tasks — dispatches a fresh implementer per task, a scene-delta review after each, and a whole-asset review at the end
---

# Asset-Driven Development

Adapted from superpowers `subagent-driven-development`. Diffs become scene deltas + fixed-camera renders; commits become checkpoints.

**Core principle:** Fresh implementer per task + task review (spec + build quality) + whole-asset final review.

**Narration:** at most one short line between tool calls. The ledger carries the record.

**Continuous execution:** Do not pause between tasks. Execute the whole plan.

**Rulings, not stalls.** Conflicts, ambiguities, plan defects — decide them. The spec is binding, the plan is its argument, your judgment settles the rest. Record every decision in the ledger as
`Ruling: <what you decided> — <why> — <what it costs if wrong>`
and keep going.

Four things stop you, and only these:
1. An irreversible operation — deleting user-authored data, overwriting the master scene/level, purging orphan datablocks, applying modifiers on objects the spec marks `preserve_stack`.
2. Anything that leaves the machine — uploading to a generation service with the user's credits, publishing to a library, pushing to source control.
3. A side effect outside this job's scene — editing the hero scene directly, modifying a linked library.
4. A plan so broken every path forward is a guess.

## Setup

1. **Isolate.** Work in the job's own scene (Blender: `bpy.data.scenes.new("JOB_<slug>")`; UE: a dedicated level under `/Game/Jobs/<slug>`). Never build in the master scene without explicit consent.
2. **Workspace.** `job/<slug>/` holds `spec.json`, `plan.md`, `progress.md` (ledger), `briefs/`, `reports/`, `reviews/`, `renders/`, `checkpoints/`. Another job's directory is never yours.
3. **Ledger.** First line: `# ADD ledger — plan: job/<slug>/plan.md`. If the ledger exists and names your plan, tasks with a `Task <N>: complete` line are DONE — do not redo. Resume at the first task without one. After compaction, trust the ledger and `op_history` over your recollection. A ledger naming a different plan is not yours.
4. **Read** plan, spec, workflow file, `notes/lessons.md`. Create a todo per task.
5. **Review cameras.** Verify `REVIEW_*` cameras exist as the plan specifies; create them if Task 1 hasn't. They never move.
6. **Pre-flight.** Scan the plan for objects named in `Consumes` that no earlier task `Produces` and that don't exist in the scene. Rule on each and ledger it.

## Per Task

### Dispatch implementer
Write `briefs/task-N.md` (full task text from plan + Global Constraints + the `Consumes` state). Dispatch with `implementer-prompt.md`. Model per **Model Selection**.

### Collect
Implementer returns the short status contract. Record `op_history` range (`seq_start`..`seq_end`) and the before/after render pair paths in the ledger.

### Review package
`reviews/task-N/` contains: brief, implementer report, `scene_delta.json` (from `op_history` diff over the seq range — created/modified/deleted objects with transform/topology/material changes), `measure.json` for every produced object, before/after renders from each `REVIEW_*` camera. **The reviewer sees this and nothing else.**

### Dispatch task reviewer
`task-reviewer-prompt.md`. Returns Spec Compliance ✅/❌/⚠️, Build Quality verdict, Issues (Critical / Important / Minor).

### Fix loop
- Approved → ledger `Task N: complete — <one line>`, mark todo.
- Finding conflicts with plan text → rule on it, ledger the ruling.
- Otherwise fix round R of 5: R ≤ 3 resume same implementer with findings; R ≥ 4 fresh implementer on a more capable model with "A prior implementer attempted this [N] times; read the report file for what was tried." Each round the implementer re-runs the asserts covering the amended objects and appends to its report. Scoped re-review (`re-review-prompt.md`) over the new seq range.
- R = 5 → adjudicate each open finding. Load-bearing (spec violation, non-manifold on a deform region, missing texture) → rule and continue only if a path exists; otherwise stop (#4). Non-load-bearing → park in ledger with ruling.

### Checkpoint
`op_history.checkpoint("task-N")`. If the workflow profile says so, `snapshot_file("checkpoints/task-N.blend")`.

## After All Tasks

1. **Whole-asset review** on the most capable model. Reviewer gets: spec, `check_asset_ready` output, `measure` for every object, final renders from all `REVIEW_*` cameras + a lookdev turntable if materials were in scope, the ledger's parked/deferred lines. Not the task-by-task history.
2. Findings → **one** fix dispatch with the complete list, one scoped re-review, adjudicate residuals.
3. Clean → `check_asset_ready` must pass. Then hand off to the finishing step: link into master scene / mark as library asset / export per spec / discard. Export runs `verify_export` (round-trip re-import and compare).
4. Append lessons: any assert that failed and was fixed becomes one conditional line in `notes/lessons.md` ("When X, Y happens → do Z"). Prune lessons that haven't fired in 10 jobs.
5. Delete `briefs/`, `reviews/`; keep `spec.json`, `plan.md`, `progress.md`, `renders/final/`, `checkpoints/final`.

## Model Selection

Least capable model that can do the role.
- **Mechanical build tasks** (one object, fully specified asserts, no judgment): fast/cheap model. Most tasks are mechanical when the plan is good.
- **Judgment tasks** (matching a reference silhouette, resolving a topology trade-off, material lookdev): standard model.
- **Final whole-asset review, and fix round ≥ 4:** most capable model.
- An omitted model silently inherits the session's most expensive one — always set it.

## Ledger Format

```
# ADD ledger — plan: job/chair-hero/plan.md
Task 1: complete — review cameras + collections; seq 0..14
Task 2: complete — Chair_Frame; seq 15..61; renders/task-2/{before,after}_3q.png
Task 3: fix round 1 — reviewer: seat bbox z max 0.49 > 0.47; resumed implementer
Ruling: spec silent on seat thickness — chose 0.04 m (matches reference photo) — cost if wrong: rebuild seat, ~2 min
Task 3: complete — Chair_Seat; seq 62..98
Parked: Minor — Chair_Frame has 2 ngons on hidden underside; ruled acceptable (not a deform region)
```

## Red Flags

| Thought | Reality |
|---|---|
| "The render looks right, skip `measure`" | Renders hide flipped normals, overlap, scale. Run it. |
| "I'll review this one myself" | Controller never reviews. Dispatch. |
| "Task 4 is basically done from task 3's leftovers" | Ledger says not complete → dispatch it. The implementer will find it trivial. |
| "I'll move the review camera for a better angle" | Then no render is comparable. Add a camera; never move one. |
| "I remember doing task 6" | Ledger doesn't. You compacted. Trust the ledger. |
