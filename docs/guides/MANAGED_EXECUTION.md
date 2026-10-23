# Managed execution

The `dcc_harness.execution` service owns the complete edit lifecycle: admission, retained inputs, one background Blender invocation, independent saved-file observation, contract checking and checkpoint publication. CLI commands and the shipped `dcc-harness-mcp` endpoint use this service.

The calling agent still interprets the brief, writes the construction script, inspects images and supplies stage evidence. This package does not embed an LLM or start an unattended reasoning agent itself. An autonomous client can loop over the service without routine human gates; a gated client uses the same loop and waits for owner review between stages.

## Select a mode

Start or adopt a scene and bind an environment workflow using the existing `start` and `workflow-bind` commands. Select the run mode before completing stages:

```powershell
python -m dcc_harness run-create PROJECT --mode autonomous --max-operations 20 --seconds 3600
# Alternatively, for stage-by-stage owner review:
python -m dcc_harness run-create PROJECT --mode approval_gated --max-operations 20 --seconds 86400
python -m dcc_harness run-status PROJECT
```

Run policy is immutable. The deadline is wall-clock time, including approval waits, and the operation budget counts attempts, including rejected attempts. A cancelled or exhausted run stops; there is no automatic budget extension or mode downgrade. Start a new project from its accepted checkpoint to begin a separately authorized run. Existing advisory projects remain advisory until `run-create` is called. Old runtime bindings stay pinned; use their matching installed runtime rather than silently changing their approval semantics.

In managed projects, `begin-edit`, `finish-edit`, direct continuity publication, and legacy journal mutation cannot bypass service admission. Python scripts and local files remain trusted: this is a cooperating-client boundary, not an OS sandbox or authenticated multi-user security service.

## Execute a stage

Use the current checkpoint ID returned by `run-status`. Generate one UUID for the intended operation and retain it across retries:

```powershell
python -m dcc_harness run-execute PROJECT --stage direction --operation-id OPERATION_UUID --parent CHECKPOINT_ID --script edit.py --contract contract.json --handoff CONTINUE.md --blender "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --timeout 300
```

The script runs with an owned copy open. The service saves `candidate.blend` after it returns, then a separate Blender process reopens that candidate. The script may read `DCC_OUTPUT_PATH`; it does not need to save manually. Do not depend on an interactive editor, network access or a persistent Python session. Preserve stable identities and declare intended changes in the contract.

The service checks predecessors before reserving work and again before publication. Revisions within a stage awaiting review are allowed. Reopen a completed stage before changing it. A changed blocking target or stale evidence invalidates current readiness and downstream admission; historical approval receipts are retained.

An identical operation ID and request recover the retained receipt; they never execute the script a second time. Changing script, contract, handoff, timeout, executable, stage or parent under that ID is rejected. A failed or interrupted dispatch returns `NEEDS_RECONCILIATION`, even if it left a candidate on disk.

## Submit evidence and advance

`requirements PROJECT STAGE` describes the submission payload and required evidence. Supply real checkpoint-bound observations and renders; a script finishing is not visual acceptance.

```powershell
python -m dcc_harness run-submit PROJECT --submission submission.json --evidence-root EVIDENCE_FOLDER
```

In autonomous mode, `run-submit` attempts agent completion only when the effective manifest and binding policy permit it, after validating evidence, feedback and pinned checks. An `artist_required` stage returns `AWAITING_APPROVAL` in either mode. Optional `--review review.json` supplies the agent's finding and answers to questions without defaults. Invalid or incomplete evidence leaves the submission unapproved. Agent completion always records `artistic_acceptance: not_evaluated`. Fresh submissions and resumed agent completion enforce cancellation, deadline and runtime pins; completed identical submissions remain readable.

In approval-gated mode, submission returns `AWAITING_APPROVAL`. The owner reviews the checkpoint using `review-page`/`review-import` or the existing `stage-complete` command from their terminal. Every stage requires artist review even if its original manifest allowed agent review. Approval refers to a specific submission, checkpoint and pinned workflow; intervening coordination activity or a changed checkpoint makes it stale. Existing terminal attribution is a guard, not a cryptographic identity system.

## Stop and recover

```powershell
python -m dcc_harness run-cancel PROJECT
python -m dcc_harness run-status PROJECT
python -m dcc_harness run-reconcile PROJECT --operation-id OPERATION_UUID --reason "Inspected attempt; reject its candidate"
# Accept only after inspecting the retained candidate and its independent observation:
python -m dcc_harness run-reconcile PROJECT --operation-id OPERATION_UUID --accept --reason "Candidate and preserved scene verified"
```

Timeout/cancellation terminate and reap the owned worker. They do not mean that nothing ran. MCP tool teardown records operation-specific cancellation; it does not terminally cancel the run. After reconciling that operation, a fresh operation can proceed within the remaining budget. Explicit `run-cancel` is irreversible for that run. Unresolved work takes precedence as `NEEDS_RECONCILIATION` in status, even on a terminally cancelled run.

The accepted checkpoint stays unchanged until a passing candidate is published. Explicit reconciliation never reruns the script. It can finish an interrupted independent native check or recover a committed publication and its frozen capability receipt. An already verified candidate may publish after deadline through explicit reconciliation, while runtime, stage policy and terminal run cancellation still apply. Rejecting an attempt closes its journal record without changing the accepted checkpoint. Failed pre-dispatch staging is retained and listed by status; inspect it before deliberate cleanup.

Saved external revisions in background managed projects use `accept-revision --stage STAGE`, consume ordinary admission/budget and reopen affected stages. The caller's review note is recorded without authenticating artist approval. Paired live projects refuse this import route; use measured live refresh/recovery. See [external revisions](EXTERNAL_REVISIONS.md).

If the controller itself dies, its kernel lock releases, but its unresolved operation blocks new work. A surviving Blender process may still be working on that attempt's owned files; inspect and stop it before reconciling. Corrupted files, incomplete checkpoint bundles, and a crash-retained `workflow.lock` remain explicit inspection stops. Automatic recovery does not erase partial evidence or guess which files to delete.

## Qualification

`scripts/verify_release.py` is the maintained release entry point. It runs source and installed suites, builds wheel/sdist, compares rebuilt package members, and checks the installed CLI/MCP and bridge exports. The [portable CI workflow](../../.github/workflows/portable.yml) runs it without Blender. Supplying `--blender` adds local native units, adoption, managed/MCP, live preservation/transport and capability qualifications. Native GUI/background fixtures require owned fresh configuration directories and exact native CONFIG path guards before preference writes. The gated fixture's synthetic owner console tests authority routing; it does not establish a person's approval or artistic quality. The [external-review ledger](../archive/releases/EXTERNAL_REVIEW_0_23_RESULTS.md) records current evidence, historical failures and the unresolved preference incident.

The wheel ships the execution service/workers, bundled rules and bridge, and registers the `dcc-harness` and `dcc-harness-mcp` executable entry points in its Python environment. `mcp==1.26.0` is the declared direct dependency; its transitive dependencies are not fully locked. Client registration is a separate explicit setup step: installation does not edit Codex or another client's configuration. See [combined setup](COMBINED_MCP.md).

The [v0.20.0 verification report](../reference/MANAGED_EXECUTION_VERIFICATION_2026-10-22.md) records the passing source/installed suites, native checks, independent-review fixes and exact wheel hash.
