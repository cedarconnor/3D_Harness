# Everyday Blender workflow

Version 0.4.0 adds one project entry skill, `dcc-harness`, and five CLI entry points over the existing continuity store. Use the normal chat to ask for a start, continuation, review or bounded revision. This repository's `.agents/skills/` is the current project-scoped delivery; a standalone client installer is still future work.

Later additions use the same store. These are [scene adoption](SCENE_ADOPTION.md) in 0.4.9, [external revisions](EXTERNAL_REVISIONS.md) in 0.4.10, and optional [structured feedback and environment stages](STRUCTURED_FEEDBACK.md) in 0.5.0. When feedback coordination is enabled, `resume` and `review` add a `coordination` section listing open notes and stage states. A published checkpoint never resolves a note by itself.

The host agent supplies reasoning and calls the existing Blender MCP or owned background Blender. These commands do not launch an agent, buy credits, run a daemon or implement another MCP server. The workflow serializes its own edit reservations. Direct MCP writes and older Python/CLI entry points remain outside that protection.

## Orient first

Since 0.7.0, `brief PROJECT` prints where a project stands and the permitted next steps, with each command filled in from the verified record: project path, parent ID, checkpoint path, edit ID, coordination revision and a fresh request ID. `next PROJECT` returns the same steps as JSON, and `requirements PROJECT STAGE` returns what a stage submission needs with a skeleton for `fill-hashes`. All three only read. The [agent quick reference](AGENT_QUICK_REFERENCE.md) has the exact sequences and payload shapes.

## Start and resume

Before `start`, save an owned `.blend` and observe it. Since 0.6.0 one command does this in a fresh background Blender without saving the file:

```powershell
python -m dcc_harness observe C:/project/baseline.blend --blender "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --output-dir C:/project/observe-baseline
```

It writes `observation.json` in the new folder and reports `READY`, or `HAS_ISSUES` with exit status 1. The report lists the issues, such as missing IDs or an unsupported collection instancer. Use the same command for every saved file that `begin-edit`, `finish-edit` or `preview-revision` needs observed. Calling `dcc_harness.continuity_blender.observe()` inside Blender remains equivalent. The observation must match the native hash, have no observation issues, and report `native_dirty: false`. For a saved scene missing stable identities, version 0.4.9 adds [preview/apply adoption commands](SCENE_ADOPTION.md). They write a new native file and independently observe it; setup does not silently rewrite the input.

```powershell
python -m dcc_harness start C:/project/state --checkpoint C:/project/baseline.blend --observation C:/project/baseline.json --brief-file C:/project/BRIEF.md --decisions C:/project/decisions.json --handoff C:/project/CONTINUE.md
python -m dcc_harness resume C:/project/state --focus ext.bench.top --out C:/project/resume-01.json
python -m dcc_harness review C:/project/state --focus ext.bench.top
```

`decisions.json` is a JSON object recording project choices. The initial checkpoint establishes a baseline and does not certify visual quality. `start` refuses an existing initialized store.

`resume` verifies the committed chain and provides the active paths, brief, current decisions, handoff, last five steps, counts, observation coverage and pending operations. Optional focus IDs include dimensions/bounds, mesh-sharing users and material users. It avoids dumping per-vertex/UV arrays. Shared-user lists can be large; request only relevant objects and use the referenced observation for deeper queries.

Version 0.4.2 removes redundant observation serialization and registry derivation while retaining full chain verification on every read. The six-checkpoint production measurement improved from 36.8 to 13.2 seconds; see [measurements and validation](../archive/releases/RESUME_0_4_2_RESULTS.md). No store migration or command change is required. Large histories still take time to verify; do not bypass the checks or replay a pending edit to work around latency.

`READY_FOR_INSPECTION` means the saved project can be inspected, not that a live editor is synchronized or that a new mutation is approved. `RECONCILE` identifies pending operations/reservations or a metadata lock. `review` additionally points to the retained latest check report and explicitly leaves artistic acceptance unassessed. Review the actual images separately.

Version 0.4.6 adds optional [compact observation storage](OBSERVATION_STORAGE.md) for new files. It pools repeated UV arrays without changing expanded values or revision hashes. All readers must use 0.4.6 or later. Retained history remains immutable; this does not migrate older checkpoints or skip full chain verification.

## Reserve and complete an edit

Create an immutable author script and a `dcc.continuity.contract.v1` contract. Use the actual allowed targets/fields and cumulative required objects; do not grant a whole scene because a single material changes. The script must open the intended input, write a new native file and produce a saved-state observation. It must not overwrite the accepted checkpoint.

```powershell
python -m dcc_harness begin-edit C:/project/state --parent PARENT_ID --current C:/project/baseline.blend --observation C:/project/fresh-baseline.json --script C:/project/change.py --contract C:/project/contract.json --label metal-revision-01
# Execute the retained script returned above, once, using the existing DCC connection.
# Reopen the result and generate its observation in a separate process where practical.
python -m dcc_harness finish-edit C:/project/state EDIT_ID --checkpoint C:/project/revised.blend --observation C:/project/revised.json --handoff C:/project/CONTINUE-revised.md --updates C:/project/decision-updates.json
```

`PARENT_ID` is `active.id` from resume; `EDIT_ID` is `edit` from begin-edit. These are placeholders in this example, not literal commands to paste unchanged. `updates` may be `{}`. Every `--out` is an exclusively created optional report file. Since 0.5.1 the result is printed before the file is written. If the path already exists, nothing is overwritten and the command exits with status 2, but the printed result and any committed change stand. Never rerun a committed command just to obtain a receipt.

Begin checks parent identity, exact current saved-file bytes, a matching clean observation and observed preservation against the accepted baseline. It then retains script/contract bytes and starts a durable pending journal operation. Another cooperating begin cannot reserve concurrently or while that edit is pending. Execute the returned retained script, not an earlier source path that may have changed.

Finish recomputes the retained contract. A passing result publishes a new checkpoint with the handoff and decision updates. A failed contract is recorded as `REJECTED_RETAINED`, leaves the prior checkpoint active, and returns exit code 1. Candidate files stay where the caller saved them; failed candidates are not copied into accepted history. This outcome is known and does not require replay. Corrections need new scripts/reservations from an explicitly selected baseline.

Version 0.4.1 adds `finish-edit --reject-reason "specific visual defect"`. Review required images before finishing. With this flag a native-passing candidate records `REJECTED_VISUAL`, `native_check_passed: true`, and `passed: false`; it leaves the parent and decisions unchanged and returns exit code 1. This is an intentional selection outcome, not an error to retry. The current API equivalent is `finish_edit(..., reject_reason="...")`. Rejections remain visible in `resume` and repairs use a new reservation. A caller's review is attributed as a review, not automatically as artist acceptance.

## Review renders

Since 0.8.0, `render SAVED.blend --blender PATH --output-dir NEW_FOLDER --project PROJECT` renders the project's fixed review views of any saved file, such as a candidate before `finish-edit` or the active checkpoint, in a fresh background Blender. It never saves. The views come from the decision `review_views`, a `dcc.review.views.v1` definition recorded at `start` or in any edit's decision updates; `--views FILE` uses a file instead. Each view names a scene camera by stable ID or a review-only camera by lens, location and target, with an optional crop. The command writes the images, the resolved settings and a `dcc.quality.renders.v1` receipt bound to the file's hash, and returns evidence entries for feedback responses and stage submissions. Embedded PNG stamps are removed, so identical renders are byte-identical.

Renders run one at a time per machine. `--detach` queues a render in a separate process and returns `QUEUED`; `render-wait FOLDER` waits up to `--timeout` seconds (default 100) and returns `waiting`, `running`, `done` or `failed`. The [agent quick reference](AGENT_QUICK_REFERENCE.md#3-render-review-views) shows a definition.

## Relations and repair history

Since 0.9.0, `relations SAVED.blend --blender PATH --output-dir NEW_FOLDER --project PROJECT --strategy "what this file changes"` measures the project's `supported_by` relations in a fresh background Blender and never saves. The definition is the decision `relations` (`dcc.relations.v1`), or a file passed with `--spec`. For each subject, such as a bench leg, vertical rays through its lowest vertices meet the declared support surface. The finding gives `OK`, `GAP`, `PENETRATION`, `OFF_SUPPORT` or `MISSING_TARGET`, a signed error in metres from the point closest to contact, the footprint's spread and its coverage. A relation whose subjects both float and sink is a `CONFLICT`: no rigid move of the group fixes it. A bounding-box estimate is reported beside each finding as `bounds_only` evidence that permits inspection, not repair; on sloped ground it reports penetration that the rays show is not there.

With `--project`, every measurement is appended to the project's `relations/` record under the workflow lock, with the parent checkpoint, the file's hash and the strategy text. Entries are never rewritten. `brief` and `next` report the latest result per subject and warn when the last two attempts swung between gap and penetration (`OPPOSING`), changed the error by less than 20% (`NO_PROGRESS`), or the latest measurement is a `CONFLICT`. The [agent quick reference](AGENT_QUICK_REFERENCE.md#4-measure-what-rests-on-what) shows a definition.

## Interruptions and limitations

After lost acknowledgement, quota exhaustion or an agent handoff, inspect the native result first. If it exists, freshly observe it and use `finish-edit --reconciled` to record the outcome without dispatching the write again. This is explicit observed reconciliation, not automatic crash recovery or exactly-once execution.

A short `workflow.lock` serializes workflow metadata mutations. A crash can leave it behind; it never expires automatically. Inspect its PID, the original process, journal, edit folder and native outcome before manually releasing a stale lock. A partial reservation/publication remains an inspection stop. Do not delete pending evidence to make a command pass. The module cannot detect every external editor mutation between inspection and execution, and the caller still owns the native writer discipline.

If the current saved file differs from the accepted native file, begin rejects it even if a supplied observation looks similar. Version 0.4.10 adds [external revision preview and acceptance](EXTERNAL_REVISIONS.md): freeze a deliberately saved edit with its observation, contract, handoff and decision updates, review that copy, then publish it as a new measured parent. The identity helper addresses new projects only. Unsaved manual edits require a saved copy and observation; unresolved reserved edits still require their own reconciliation.

Observations and render receipts remain trusted producer claims; hashes detect changes, not dishonest producers. Native checks do not grant artistic acceptance. The existing observer's topology, UV, modifier and animation coverage limits remain in force.

## Craft routing and qualification

Read [CRAFT_SKILLS.md](CRAFT_SKILLS.md) for the four task-specific skills and tested recipe boundaries. `scripts/qualify_workflow.py` exercises the entry points on a separate saved shed file, including fresh-process unresolved-state detection, independent native reopen, narrow material revision and two architectural aperture configurations. It is an engineering exercise, separate from the frozen blind comparison.

Version 0.4.3 adds the [seeded broadleaf study](../recipes/VEGETATION_RECIPE.md), used through the same reservation workflow. Its consumer creates new native geometry but does not save, place roots or manage project state. Review both representative close-ups and destination views before publishing. The [garden results](../archive/releases/VEGETATION_0_4_3_RESULTS.md) retain a numerically passing visual rejection and a bounded repair.
