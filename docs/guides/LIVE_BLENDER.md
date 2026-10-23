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

The bridge allows up to 180 seconds for copy/capture commands and 10 seconds for its separate handshake and read/control commands. A timeout leaves the native outcome unknown. Exact command, payload, session and document-generation results are retained under the paired workspace's `.harness-mcp/outcomes/`; a lost response can be resolved from that record without redispatching. These explicit-command records are retained with the workspace and have no automatic expiry. Identical results share one immutable record, and identical divergence measurements share one diagnostic snapshot.

Attachment preflight refusals retain the destination and permit another explicit attachment attempt only when every prior attempt has exact durable proof of refusal before mutation. A confirmed job preparation refusal closes its reservation without publication; the live binding returns to READY only after an aligned scene check. A refusal caused by divergence requires refresh. Missing evidence remains unresolved.

For external manual edits or a restarted bridge, call `blender_session(action="refresh", payload={"project":PROJECT,"binding":DESCRIPTOR,"expected_parent":CHECKPOINT_ID})`. Equivalent state reconnects without a new checkpoint. Measured external changes are imported through managed execution and invalidate prior stage decisions. Unknown IDs/dependencies need explicit repair first.

A descriptor left by a crash may be replaced after its recorded process is definitively dead. A slow request, refused TCP connection, inaccessible process, or a reused process ID does not establish that the old session has stopped. Such uncertain sessions still require an explicit stop or further inspection; stale private descriptors are retained as evidence.

For an unresolved operation, inspect the current scene fingerprint through session refresh/status, then call `blender_job(action="reconcile", operation_id=UUID, payload={"project":PROJECT,"decision":"keep-current","expected_fingerprint":FINGERPRINT})`. `restore-precopy` is the other explicit choice. Recovery archives current state first and refuses if the fingerprint is stale. Restore opens a separate working copy, preserving the original artist file and immutable recovery source. An interrupted recovery is retained for inspection and is never automatically repeated.

Repeating the exact recovery intent can continue verification/publication from a matching durable capture result; it never captures/restores again. A matching durable pre-mutation refusal permits another explicit recovery decision. If the checkpoint was already published, reconciliation checks that saved/live state and completes alignment and frozen capability receipt persistence without entering capture/restore.

After an explicitly admitted replacement session, a published operation can realign from its saved snapshot and candidate bytes. The checkpoint must still be active, the snapshot fingerprint must be intact, and a fresh check must match the current session/document with no active native operation. The service retains an explicit refresh admission and alignment receipt, then finishes the frozen capability receipt. This neither invokes the old session's acknowledgement nor publishes another checkpoint or approves a stage. Same-session recovery continues to require its original job check and acknowledgement.

CLI equivalents are `live-refresh PROJECT --binding DESCRIPTOR --parent CHECKPOINT_ID`, `live-cancel PROJECT --operation-id UUID`, and `live-reconcile PROJECT --operation-id UUID --decision keep-current --fingerprint FINGERPRINT`.

## Bounded previews

`blender_preview` takes `{project, preview}`. The preview requires `session_id`, `generation`, `frame`, `width`, `height`, `samples`, a fixed `camera={lens,location,target}`, and `compare_checkpoint`. Dimensions are 32–1024; samples are 1–32. Paths are generated inside the project; caller output paths are rejected.

These are **saved-copy geometry renders**, not a beauty-render or viewport-quality claim. Workbench antialiasing rounds the requested sample count up to its next supported level (5, 8, 11, 16 or 32), recorded in the receipt. The current copy and optional accepted checkpoint use identical frame, camera, studio lighting and color settings. Receipts identify source bytes and settings. Images remain with project evidence; the disposable current-scene copy is deleted only after successful rendering. Failed previews retain diagnostic files. Delete/archive the whole project through ordinary project retention when its evidence is no longer needed.

Preview never changes stage approval or the artist's render settings. `live-preview PROJECT --request PREVIEW_JSON --blender BLENDER` provides the same behavior from the CLI.

No external services, telemetry or background user-activity recording are introduced. Logs and artifacts are local records of explicit managed commands.

Pairing and bridge identity checks assume a trusted local user and workspace. The bridge reports its own integrity hash; this is a compatibility pin, not remote attestation. Session discovery sends a descriptor's pairing token to its loopback port. The command whitelist excludes a raw Python endpoint, but qualified recipe adapters are project-resident Python executed inside Blender, with integrity records in that same project. These controls do not sandbox hostile code or another process running as the same user.

Save-copy path remapping uses `Image.filepath_raw` to avoid reloading live external image pixels. Owned tests cover unchanged live cached pixels, path strings and dirty flags. They do not establish preservation of arbitrary stale clean image caches when reopening saved copies; dirty image buffers and the existing unsupported dependency/scene classes remain refused.

## Windows evidence paths

Shared Python evidence I/O uses an internal extended-length filesystem spelling on Windows, including JSON reads, exclusive writes, hashes, verified copies, retained snapshots, and every component inspected for symlinks/reparse points. Requests, returned paths, containment comparisons and fingerprint content retain their ordinary logical spelling. Caller-supplied device/extended namespaces, reserved device components and ambiguous trailing-dot/space or alternate-stream names are refused at this boundary. Filesystem errors other than actual missing components remain errors during link inspection.

This fixes deep recovery-verifier evidence directories without shortening them or changing Windows/Blender configuration. It does **not** establish general long-path support for Blender `.blend` files or external assets. In owned Blender 5.1.1 Windows probes, ordinary 275-character `.blend` save/open paths failed; an extended save left a partial `@` file and failed its final rename; extended open succeeded but retained the extended namespace in `bpy.data.filepath`. Production code therefore does not pass the Python I/O spelling to `bpy` operations. Existing native save admission checks containment, suffix and absence, not a qualified maximum path length; a native save failure may leave partial evidence and must not be replayed automatically.

Reproduce the bounded proof with `python scripts/qualify_native_paths.py --blender BLENDER --runtime CHECKOUT --out NEW_FOLDER`. It creates four owned native user directories, checks exact effective CONFIG before every native action, retains real long-junction refusal evidence where Windows permits creation, and runs a fresh independent saved verifier at the deep recovery directory shape. Separate native save/open measurements retain their failures and partial files. The release runner includes this proof against the installed runtime; it is not a general asset-path qualification.

Recipe bundle loading also uses the I/O spelling when enumerating its admitted directory levels and reading adapter source or managed registration/report JSON. Enumeration errors propagate; they cannot produce a silently empty or incomplete inventory. Manifest membership, member hashes and reparse checks remain strict. Adapter module paths and compile filenames retain their ordinary logical spelling, and loading emits no bundle `.pyc` files. Draft retention remains a host-side operation.

`python scripts/qualify_recipe_paths.py --blender BLENDER --runtime CHECKOUT --out NEW_FOLDER` proves the 257-character bundle shape with a fresh pinned synthetic provider, negative member/reparse cases, real recipe application, and a separate saved verification process. It also tests deeper synthetic managed metadata records; those records are test inputs, not host qualification receipts. The release runner runs this against the installed runtime. Provider discovery/import paths and native scene/asset paths remain separate contracts: this proof uses short owned provider and `.blend` paths and does not establish arbitrary long-provider or native-asset support.
