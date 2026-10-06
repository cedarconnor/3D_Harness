# Everyday Blender workflow

Version 0.4.0 adds one project entry skill, `dcc-harness`, and five CLI entry points over the existing continuity store. Use the normal chat to ask for a start, continuation, review or bounded revision. This repository's `.agents/skills/` is the current project-scoped delivery; a standalone client installer is still future work.

The host agent supplies reasoning and calls the existing Blender MCP or owned background Blender. These commands do not launch an agent, buy credits, run a daemon or implement another MCP server. The workflow serializes its own edit reservations. Direct MCP writes and older Python/CLI entry points remain outside that protection.

## Start and resume

Before `start`, save an owned `.blend`, then capture `dcc_harness.continuity_blender.observe()` inside Blender to a new JSON file. The observation must match the native hash, have no observation issues, and report `native_dirty: false`. For a saved scene missing stable identities, version 0.4.9 adds [preview/apply adoption commands](SCENE_ADOPTION.md). They write a new native file and independently observe it; setup does not silently rewrite the input.

```powershell
python -m dcc_harness start C:/project/state --checkpoint C:/project/baseline.blend --observation C:/project/baseline.json --brief-file C:/project/BRIEF.md --decisions C:/project/decisions.json --handoff C:/project/CONTINUE.md
python -m dcc_harness resume C:/project/state --focus ext.bench.top --out C:/project/resume-01.json
python -m dcc_harness review C:/project/state --focus ext.bench.top
```

`decisions.json` is a JSON object recording project choices. The initial checkpoint establishes a baseline and does not certify visual quality. `start` refuses an existing initialized store.

`resume` verifies the committed chain and provides the active paths, brief, current decisions, handoff, last five steps, counts, observation coverage and pending operations. Optional focus IDs include dimensions/bounds, mesh-sharing users and material users. It avoids dumping per-vertex/UV arrays. Shared-user lists can be large; request only relevant objects and use the referenced observation for deeper queries.

Version 0.4.2 removes redundant observation serialization and registry derivation while retaining full chain verification on every read. The six-checkpoint production measurement improved from 36.8 to 13.2 seconds; see [measurements and validation](RESUME_0_4_2_RESULTS.md). No store migration or command change is required. Large histories still take time to verify; do not bypass the checks or replay a pending edit to work around latency.

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

`PARENT_ID` is `active.id` from resume; `EDIT_ID` is `edit` from begin-edit. These are placeholders in this example, not literal commands to paste unchanged. `updates` may be `{}`. Every `--out` is an exclusively created optional report file; choose a new name and inspect outcomes before retrying if report export itself fails.

Begin checks parent identity, exact current saved-file bytes, a matching clean observation and observed preservation against the accepted baseline. It then retains script/contract bytes and starts a durable pending journal operation. Another cooperating begin cannot reserve concurrently or while that edit is pending. Execute the returned retained script, not an earlier source path that may have changed.

Finish recomputes the retained contract. A passing result publishes a new checkpoint with the handoff and decision updates. A failed contract is recorded as `REJECTED_RETAINED`, leaves the prior checkpoint active, and returns exit code 1. Candidate files stay where the caller saved them; failed candidates are not copied into accepted history. This outcome is known and does not require replay. Corrections need new scripts/reservations from an explicitly selected baseline.

Version 0.4.1 adds `finish-edit --reject-reason "specific visual defect"`. Review required images before finishing. With this flag a native-passing candidate records `REJECTED_VISUAL`, `native_check_passed: true`, and `passed: false`; it leaves the parent and decisions unchanged and returns exit code 1. This is an intentional selection outcome, not an error to retry. The current API equivalent is `finish_edit(..., reject_reason="...")`. Rejections remain visible in `resume` and repairs use a new reservation. A caller's review is attributed as a review, not automatically as artist acceptance.

## Interruptions and limitations

After lost acknowledgement, quota exhaustion or an agent handoff, inspect the native result first. If it exists, freshly observe it and use `finish-edit --reconciled` to record the outcome without dispatching the write again. This is explicit observed reconciliation, not automatic crash recovery or exactly-once execution.

A short `workflow.lock` serializes workflow metadata mutations. A crash can leave it behind; it never expires automatically. Inspect its PID, the original process, journal, edit folder and native outcome before manually releasing a stale lock. A partial reservation/publication remains an inspection stop. Do not delete pending evidence to make a command pass. The module cannot detect every external editor mutation between inspection and execution, and the caller still owns the native writer discipline.

If the current saved file differs from the accepted native file, begin rejects it even if a supplied observation looks similar. Version 0.4.10 adds [external revision preview and acceptance](EXTERNAL_REVISIONS.md): freeze a deliberately saved edit with its observation, contract, handoff and decision updates, review that copy, then publish it as a new measured parent. The identity helper addresses new projects only. Unsaved manual edits require a saved copy and observation; unresolved reserved edits still require their own reconciliation.

Observations and render receipts remain trusted producer claims; hashes detect changes, not dishonest producers. Native checks do not grant artistic acceptance. The existing observer's topology, UV, modifier and animation coverage limits remain in force.

## Craft routing and qualification

Read [CRAFT_SKILLS.md](CRAFT_SKILLS.md) for the four task-specific skills and tested recipe boundaries. `scripts/qualify_workflow.py` exercises the entry points on a separate saved shed file, including fresh-process unresolved-state detection, independent native reopen, narrow material revision and two architectural aperture configurations. It is an engineering exercise, separate from the frozen blind comparison.

Version 0.4.3 adds the [seeded broadleaf study](VEGETATION_RECIPE.md), used through the same reservation workflow. Its consumer creates new native geometry but does not save, place roots or manage project state. Review both representative close-ups and destination views before publishing. The [garden results](VEGETATION_0_4_3_RESULTS.md) retain a numerically passing visual rejection and a bounded repair.
