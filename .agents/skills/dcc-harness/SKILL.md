---
name: dcc-harness
description: Use when starting, resuming, reviewing or revising a Blender project that 3D Harness tracks with checkpoints, recorded decisions and feedback notes.
---

# Work in a persistent Blender project

Run commands as `python -m dcc_harness ...`, or through the installed `dcc-harness` and `dcc-harness-mcp`. [The agent quick reference](../../../docs/guides/AGENT_QUICK_REFERENCE.md) has the exact command sequences and payload shapes.

## The loop

1. **Run `brief PROJECT`.** It prints where the project stands, open feedback, the recorded brief, the last handoff and the permitted next steps with their commands filled in. Follow those steps and run it again after any command that changes the project. `next PROJECT` gives the same steps as JSON.
2. **Load one craft skill.** `dcc-architecture`, `dcc-materials`, `dcc-environment-assembly` or `dcc-lighting-review`, or one from the [`blender-craft` index](../blender-craft/SKILL.md). `dcc-build-revise` and `dcc-review-continue` cover authoring and evidence.
3. **Reserve the edit.** `resume PROJECT --focus ID...` returns the measured fields and shared users of what you will touch. Save the script and its continuity contract, then run `begin-edit`.
4. **Build.** Run the retained script once on an owned working copy, save a new file and `observe` it.
5. **Look and measure.** Run `render` with the project's `review_views`, `relations` when the project records a `relations` decision, and `audit` on the saved file, repairing its errors. `review-sheet --targets ID...` shows one asset from all sides. Inspect images of this result, never earlier renders.
6. **Publish or reject.** `finish-edit` rechecks the contract and publishes the checkpoint, decisions and handoff. `finish-edit --reject-reason "visible defect"` retains a candidate that measures right but looks wrong.
7. **Write the handoff:** what changed, what you left undone and why, and anything unresolved.

## Always

- **No reply after a script ran:** inspect the saved result and finish with `finish-edit --reconciled`. Never run the script again. `RECONCILE` asks for inspection, not replay.
- **Accepted files and retained scripts are never edited in place.** Work on a copy.
- **A shared material changes every user.** Change only what the request names; give one object its own material when the others must stay.
- **A request that conflicts with a recorded decision** is answered with the conflict, not carried out.
- **Only the artist approves.** Hand over the exact command for their terminal; never claim their role.
- **Review views** live in the `review_views` decision or a views file, never as cameras saved into the scene.
- **Relation history:** never repeat a repair marked `OPPOSING` or `NO_PROGRESS`; a `bounds_only` estimate permits inspection, not repair.

## Read only when it applies

| When | Read first |
|---|---|
| `brief` says the project is managed, has capability policy, or has a pending job. Do not call `begin-edit` or `finish-edit` there. | [Managed execution](references/managed-execution.md) |
| The work is in an open Blender scene | [Live scene](references/live-scene.md) |
| There is no project yet, or the scene lacks stable IDs | [New project](references/new-project.md) |
| Someone saved an edit outside a reservation | [External revisions](references/external-revisions.md) |
| An artist review, a stage approval, pinned skills or a learned check | [Review and approval](references/review-and-approval.md) |
| An add-on recipe or asynchronous provider | [Add-on effects](references/addon-effects.md) |
