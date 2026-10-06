# Continuity prototype usage

The continuity layer stores accepted Blender checkpoints, observations, decisions and handoffs above the existing MCP connection. The agent client still drives Blender. The layer does not launch agents or intercept tool calls.

For the controlled comparison, activate the project skill `$dcc-blind-test` and specify the longer continuity experiment. Its coordinator supplies frozen packets and grants one Blender writer at a time. See [the experiment protocol](CONTINUITY_EXPERIMENT.md). Production agents must use the helper copied into their packet, not the current repository package.

For an ordinary project, the following APIs are available in `dcc_harness.continuity`. Use a new project directory and saved files. A store cannot reconstruct decisions or evidence from an unsaved editor session.

## Start and inspect a project

Capture the saved native state inside Blender using `dcc_harness.continuity_blender.observe()`. Its observation includes the actual saved checkpoint hash. Write the observation with `dcc_harness.evidence.write_json` to a new file.

Version 0.1.1 emits continuity observation version 2. Dimensions use evaluated, world-oriented geometry with translation excluded before computing extents; world bounds still measure placement. This avoids small float32 subtraction differences making a pure translation appear to resize an object. Nonfinite authored/evaluated coordinates are rejected.

Start new projects with v2 observations throughout. Matching legacy v1 observations remain readable and checkable, including their known translation failure. Mixed v1/v2, unknown versions and malformed measurement declarations fail. To continue a frozen v1 trial, use its frozen helper; do not silently replace its baseline or change its results. An ordinary older project needs a separately documented migration or a fresh v2 history before switching observers. Automatic migration is not implemented.

```python
from pathlib import Path
from dcc_harness.continuity import Continuity

work = Path("C:/path/to/project")
store = Continuity(work / "state")
state = store.initialize(
    work / "initial.blend",
    work / "initial-observation.json",
    "The project's creative brief and preservation requirements.",
    {"units": "meters", "table_width_m": 2.4},
)
```

Read or verify an existing store from a terminal:

```powershell
python -m dcc_harness.continuity status --root C:/path/to/project/state
python -m dcc_harness.continuity verify --root C:/path/to/project/state
```

Both commands verify the retained files and parent chain before returning the active checkpoint, cumulative decisions, task history, asset and material registry, and unresolved operations. The first checkpoint establishes a baseline; it does not grant artistic approval.

## Accept a revision

Keep the input observation fixed. After authoring, save a new native file and observe that saved file. Evaluate it with `evaluate_stage(before, after, contract)` from `dcc_harness.continuity_checks`, using a contract with schema `dcc.continuity.contract.v1`. Save the returned report. The repository's `experiments/continuity/contract-*.json` files are concrete examples for the experiment scene, not general contracts for arbitrary projects.

```python
state = store.status()
state = store.publish(
    step_id="widen-potting-table",
    expected_parent=state["active"]["id"],
    checkpoint=work / "revised.blend",
    observation=work / "revised-observation.json",
    handoff=work / "CONTINUE.md",
    decision_updates={"table_width_m": 2.8},
    check=work / "revision-check.json",
)
```

Publication requires a matching observation, passed check, factual handoff and current parent ID. Refresh the parent ID after each accepted step. Failed work remains in the working directory; do not weaken the contract to publish it. The store verifies supplied evidence and retains its bytes. Independent native inspection remains a separate source of confidence.

## Handle an uncertain operation

Use `Project(state_directory).begin(label, saved_script_path)` before dispatching a bounded write. Inspect the native result, save evidence, then call `finish(operation_id, evidence_path)`. If acknowledgement was lost, inspect before repeating the operation and use `finish(..., reconciled=True)` when the actual outcome is established. The store rejects a new publication while operations remain unresolved.

An external artist edit needs a newly observed checkpoint, an explicit decision update and a narrow preservation check before it becomes the next accepted parent. Neither an artist edit nor a missing acknowledgement justifies reinitializing the history.

## Continue in another context

Copy the whole state directory together with the working native scene, current request and handoff. Verify the copied store first. Use paths returned by the copied store's `status()`; historical absolute paths in journal records are provenance. Previously accepted script and evidence bytes are retained in the checkpoint bundles.

The present implementation assumes one cooperative writer. Partial publications are left visible and refused on retry, so they require inspection. Native saves and store publication are not one transaction, and direct MCP writes can bypass these APIs. Automatic scheduling, enforced tool routing and other DCC adapters are future work.
