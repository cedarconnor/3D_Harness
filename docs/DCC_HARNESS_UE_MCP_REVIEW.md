# What db-lyon UE-MCP changes in the harness plan

Supporting source review. Its implementation suggestions are future options governed by the [active build plan](./DCC_HARNESS_BUILD_PLAN.md); Unreal integration is deferred until the Blender creative experiment demonstrates value.

Reviewed October 3, 2026. Source snapshot: [`6975fc5cfbf513c19d2c8c8348f095c02401929e`](https://github.com/db-lyon/ue-mcp/tree/6975fc5cfbf513c19d2c8c8348f095c02401929e). This is a targeted architecture and source review, plus one isolated Git reproduction. Unreal was not launched or modified, and the upstream test suite was not run. Repository instructions and bundled skills were treated as reference material.

**Recommendation:** make this the leading third-party Unreal adapter candidate and an immediate design reference for the general adapter contract. Keep the durable project service independent. Blender remains the first production benchmark: a detailed environment that survives long runs, shared-material changes and later revisions.

## Why this is more relevant than a large tool list

The repository combines a Node/TypeScript MCP service with an Unreal C++ bridge, categorized operations and extensible workflows. Its architecture also addresses context size and mismatches between a client package and the editor binary actually running. Those concerns transfer directly to a multi-application harness. [Architecture](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/architecture.md)

| Pattern worth adopting | Consequence for our design |
|---|---|
| Discover capabilities before selecting actions | Resolve a skill against the active application instance and project, rather than a static product/version list |
| Inspect the target's writable properties | Ground edits in observed native types, constraints and current values |
| Reusable native workflows | Turn tested sequences into pinned recipes with declared effects and evidence |
| Guards around dispatch | Enforce operation policy in code, independently of the prompt |
| Explicit outcomes and compensating actions | Separate an unchanged result, an applied edit, a partial failure and an uncertain outcome |
| Spatial and animation verification | Preserve coordinate meaning and evaluate native results at known times and viewpoints |

The proposed abstraction should therefore expose discovery, inspection, execution, observation and recovery. It should also allow namespaced native operations. Reducing all hosts to create/move/delete would discard the procedural systems that make them useful.

## Capability discovery and native schemas

The documented `micro` surface starts with a compact gateway; richer discovery is available on demand. The native handshake exposes runtime identity, registered actions and handler parameter specifications. Some advertised schemas are generated from recorded native specifications, with live comparison for drift. This is a useful direction, not evidence that every handler already has an equally complete specification. [Architecture and parameter specifications](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/architecture.md)

More unusually, `reflection.reflect_instance` describes the selected object's current property values, editability, constraints and nested paths. That is more actionable than knowing a class exists. The inspected TypeScript declaration exposes this contract; individual native reflection behaviors still need live qualification. [Reflection action definitions](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/tools/reflection.ts)

For our harness, define a capability manifest with effect class, schemas, host/plugin versions, runtime identity, required project features, supported observation, retry classification and recovery limitations. Retrieve only the relevant subset for a task. Cache it by instance and schema fingerprint; invalidate after reconnect, rebuild or plugin changes. A listed action must still pass policy and precondition checks.

Blender can implement the same inspection contract using its native property metadata and adapter-specific checks. Other hosts may expose less. Record unknown constraints explicitly rather than inventing a uniform guarantee.

## Workflows are reusable procedures, with explicit ownership

UE-MCP flows provide configurable steps, references, retries, nested flows, hooks and best-effort inverse operations. Some operations have no inverse. A flow can also continue after a deliberately ignored failure, so its top-level success is insufficient evidence for our task acceptance. [Flow semantics](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/flows.md)

Adopt three distinct objects:

1. **Skill:** chooses and evaluates a method for a creative task.
2. **Recipe:** an executable, versioned sequence with defined inputs and outputs.
3. **Job:** the durable project instance of that recipe, with receipts and evidence.

The outer harness owns task dependencies, acceptance, restart and retry decisions. Start with direct native actions. Admit a multi-step adapter flow only when its resolved definition is hashed and its child outcomes can be reconciled. Do not retry an opaque mutating flow after a timeout. Either the harness owns step retries or a qualified recipe does; never both independently.

Package custom Unreal capabilities through the project's extension mechanism when practical, retaining its native bridge instead of copying a growing handler library into our core. Keep a pinned Node sidecar behind the Python adapter interface; language uniformity is not required for architectural consistency. Extension packaging is documented separately from the main application. [Plugin authoring](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/plugins-authoring.md)

## Recovery boundaries found in the source

The handler convention uses natural keys, conflict policies and explicit created/existed/updated outcomes. This is useful for repeatable desired-state operations. It does not establish durable deduplication for arbitrary effects. An existing asset also needs its contents checked before it satisfies a task. [Handler conventions](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/handler-conventions.md)

The bridge explicitly marks timeouts as an unknown outcome and retains late responses. The inspected implementation caps abandoned-call history at 32 records in an in-memory map. That helps a running client reconcile; it cannot serve as the harness's durable operation ledger after process loss. [Bridge implementation](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/bridge/bridge.ts)

The flow integration creates a runner per call and holds the active snapshot handle in a closure. Its event bus uses in-process listeners. I did not establish a persisted resume protocol through this inspected integration; this is a qualification gap, not a claim about every capability of the separate Flowkit package. [Flow runner integration](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/flow/flow-tool.ts), [event bus](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/flow/events.ts)

### Reproduced snapshot restore defect

`restoreSnapshot` constructs `git read-tree --reset -u <tree> -- <paths>`. This command does not accept those trailing paths as the intended pathspec. In a newly created temporary bare repository and disposable working directory, using the same argument structure with `Content`, Git 2.51.0.windows.1 returned:

```text
fatal: Not a valid object name Content
exitCode: 128
actualContent: after
```

The fixture began with `before`, was changed to `after`, and was not restored. This reproduces the Git command defect, not a full Unreal rollback. Snapshot creation failure is also logged without aborting the flow. Accordingly, do not rely on this optional recovery path until it is repaired and qualified. [Snapshot source](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/flow/git-snapshot.ts), [failure handling](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/flow/flow-tool.ts)

Our required checkpoint gate should fail before dependent writes if the checkpoint cannot be made. Restore must cover the declared file set, additions/deletions, saved and unsaved native state, reload results and artist edits. Keep this separate from optional best-effort compensation. The bridge can remain useful even when a particular recovery feature fails qualification.

## Guards and authority

Its guard model distinguishes all mutations from writes to existing files, and treats arbitrary execution/reflection invocation as an unknown effect. That distinction matters: creating an object can violate a task's scope even when no existing asset file is touched. [Guard scopes](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/plugins-guards.md)

The inspected wrapper gates calls; an empty registry passes them through. Guard code itself has a special bridge route to avoid recursively invoking the guard pipeline. Treat extensions and guard implementations as trusted executable dependencies, not sandboxed skill text. [Guard implementation](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/src/flow/guarded-bridge.ts)

Our enforcement tests must exercise direct operations, nested recipes, native reflection, shell/file operations and plugin actions. Use stable object IDs, resolved paths, write leases and expected revisions. Verify policy at the actual execution boundary and keep required audit records durable. A post-call logging hook cannot retroactively refuse an edit.

## Spatial edits, animation and motion graphics

The spatial contract separates target, coordinate frame, viewpoint, operation, amount and preserved constraints. Its capture guidance also distinguishes the camera used for an image from the editor viewport. Both prevent plausible-looking but incorrectly interpreted edits. [Spatial contract](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/spatial-instructions.md)

The animation documentation grounds work in a verified rig, measured constraints, versioned sessions, native bake and numerical comparison, followed by fixed-frame visual review. It explicitly limits the Control Rig edit loop to UE5.8. Treat this as a method and compatibility requirement to test. [Control Rig workflow](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/control-rig-animation.md)

Extend that method to our motion graphics skills: discover the actual controls, make a baseline, apply a bounded change, evaluate the resulting motion and retain editable native sources. Technical tests can check contacts, continuity and preservation; design taste still requires reference-led composition, pacing, hierarchy and artist-calibrated judgment. A mechanically valid sequence can be visually poor.

## Follow-on integration

After the Blender quality and continuity gates, use one small Unreal fixture to compare identity, capability discovery, property inspection and observation metadata. Explicitly label schema-only fixtures when no editor is available. This exercise should inform the second adapter without delaying the initial creative experiment.

When Unreal integration begins, compare db-lyon UE-MCP and Epic's direct interface on the exact engine/project. UE-MCP can already wrap Epic actions, so these are alternative integration surfaces with overlapping capabilities, not necessarily competing tool collections. Verify runtime availability and prevent ambiguous routing. [Native tool integration](https://github.com/db-lyon/ue-mcp/blob/6975fc5cfbf513c19d2c8c8348f095c02401929e/docs/native-tools.md)

Qualify only the actions needed for the environment transfer first: import, asset identity, material instances, placement, lighting, cameras, save/reopen and capture. Then add PCG, Niagara and Sequencer as production needs justify them. Required recovery probes remain duplicate dispatch, lost reply, coordinator restart, editor crash, partial write, manual edit, snapshot failure and stale binary/schema mismatch.

The revised outcome is a small durable project core with capable native integrations and disciplined skill packages. This repository sharpens the adapter design substantially; it does not remove the need for project continuity, change propagation or independently checked creative acceptance.
