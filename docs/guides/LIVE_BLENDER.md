# Managed edits in the open Blender scene

The bundled bridge pairs one explicit scene with a managed project. Both `autonomous` and `approval_gated` runs reserve edits, retain a pre-operation copy, apply a bounded recipe in Blender's main thread, save a candidate, independently reopen it, and validate it before publication. The artist's original file is never overwritten. Autonomous stage advancement still requires evidence; gated advancement requires the existing owner terminal or review-page import.

## Pair and adopt

Export/install the bundled add-on as described in [COMBINED_MCP.md](COMBINED_MCP.md). In Blender's **3D Harness** sidebar, select the workspace and port and start the bridge. Pairing secrets stay in private local descriptors; do not paste their contents into prompts or project documents.

1. Call `blender_session(action="discover", payload={})` to list sessions in the MCP workspace.
2. Call `blender_session(action="describe", payload={"binding": "<descriptor path>"})` and choose the scene explicitly.
3. Create a brief with `harness_write_input`.
4. Call `blender_session(action="attach", payload={"destination":"<new folder inside workspace>","binding":"<descriptor path>","scene":"Scene","brief_file":"<brief path>","mode":"autonomous"})`.
5. Inspect stable target IDs with `blender_inspect(query={"binding":"<descriptor path>","scene":"Scene","kind":"objects"})`.

Attachment preserves unsaved edits, assigns missing managed IDs under a retained identity plan, and creates independently checked baseline copies. Duplicate IDs, linked IDs requiring ownership repair, or unresolved dependencies cause an explicit stop. Attachment currently creates a new live project; it does not silently migrate a background project or its pinned runtime.

The matching CLI entry is:

```powershell
python -m dcc_harness live-attach WORKSPACE/new-project --binding DESCRIPTOR --scene Scene --brief-file BRIEF --mode autonomous --blender BLENDER
```

## Execute and review

`blender_execute` takes `{project, operation}`. `operation` is `dcc.execution.operation.v2`, with `backend="live"`, a stable UUID, stage, expected parent checkpoint, verifier executable, time budget, retained contract/handoff files, and a `live` recipe. The required script file is a declarative provenance note for this backend; it is never executed in the open scene. Keep its content and all other inputs identical when querying an existing operation UUID.

Available built-ins:

| Recipe | Explicit parameters |
| --- | --- |
| `object.transform` | Stable object ID; finite location, rotation_euler and/or scale vectors |
| `material.input` | Stable object/material IDs, Principled node/socket, value, and every shared material user ID |
| `modifier.settings` | Stable object ID, modifier name/type, qualified BEVEL/SUBSURF/SOLIDIFY settings |
| `node.asset` | Stable object ID; workspace asset path/hash, group, managed modifier name and input values |

Node assets are first qualified in an owned process. The initial subset supports group input/output and Geometry Node Transform, with bounded scalar/vector inputs. Revisions update the existing managed modifier. This is not arbitrary Geometry Nodes or third-party add-on execution. Generic provider qualification and routing are a separate increment.

The initial live coverage excludes animation, rigs, shape keys, constraints, linked/overridden/cross-scene objects, unsupported modifiers, and Edit mode. Unsupported fields and contexts produce explicit errors. Use `blender_inspect` for coverage and operator schema discovery; discovery does not grant execution permission.

Use `harness_command` with `run-submit` for stage evidence. `approval_gated` returns `AWAITING_APPROVAL`; the MCP cannot approve its own work. A changed live scene invalidates stage submission and owner completion until explicitly reconciled or refreshed.

CLI equivalents: `live-execute PROJECT --request OPERATION_JSON`, `live-status PROJECT [--operation-id UUID]`, and the existing `requirements`/`run-submit` commands.

## Interrupted jobs and external edits

`blender_job(action="status", operation_id=UUID, payload={"project":PROJECT})` reads the durable operation and live binding state. An empty operation ID requests run status. `cancel` writes a cooperative cancellation request. It never kills Blender or claims an edit was undone. A non-cooperative operation may finish later; inspect its eventual outcome.

A lost response, stale preparation, reload, or mutation error does not authorize another dispatch. An identical UUID is status-only. Before the next operation, the service checks alignment against the accepted checkpoint.

For external manual edits or a restarted bridge, call `blender_session(action="refresh", payload={"project":PROJECT,"binding":DESCRIPTOR,"expected_parent":CHECKPOINT_ID})`. Equivalent state reconnects without a new checkpoint. Measured external changes are imported through managed execution and invalidate prior stage decisions. Unknown IDs/dependencies need explicit repair first.

For an unresolved operation, inspect the current scene fingerprint through session refresh/status, then call `blender_job(action="reconcile", operation_id=UUID, payload={"project":PROJECT,"decision":"keep-current","expected_fingerprint":FINGERPRINT})`. `restore-precopy` is the other explicit choice. Recovery archives current state first and refuses if the fingerprint is stale. Restore opens a separate working copy, preserving the original artist file and immutable recovery source. An interrupted recovery is retained for inspection and is never automatically repeated.

CLI equivalents are `live-refresh PROJECT --binding DESCRIPTOR --parent CHECKPOINT_ID`, `live-cancel PROJECT --operation-id UUID`, and `live-reconcile PROJECT --operation-id UUID --decision keep-current --fingerprint FINGERPRINT`.

## Bounded previews

`blender_preview` takes `{project, preview}`. The preview requires `session_id`, `generation`, `frame`, `width`, `height`, `samples`, a fixed `camera={lens,location,target}`, and `compare_checkpoint`. Dimensions are 32–1024; samples are 1–32. Paths are generated inside the project; caller output paths are rejected.

These are **saved-copy geometry renders**, not a beauty-render or viewport-quality claim. Workbench antialiasing rounds the requested sample count up to its next supported level (5, 8, 11, 16 or 32), recorded in the receipt. The current copy and optional accepted checkpoint use identical frame, camera, studio lighting and color settings. Receipts identify source bytes and settings. Images remain with project evidence; the disposable current-scene copy is deleted only after successful rendering. Failed previews retain diagnostic files. Delete/archive the whole project through ordinary project retention when its evidence is no longer needed.

Preview never changes stage approval or the artist's render settings. `live-preview PROJECT --request PREVIEW_JSON --blender BLENDER` provides the same behavior from the CLI.

No external services, telemetry or background user-activity recording are introduced. Logs and artifacts are local records of explicit managed commands.
