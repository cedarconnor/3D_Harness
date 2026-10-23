# Combined harness MCP

One installation provides the harness CLI, stdio MCP endpoint, build rules and a pinned Blender bridge. Construction uses the [managed execution service](MANAGED_EXECUTION.md) in autonomous or approval-gated mode, with background scripts or [bounded operations in the open scene](LIVE_BLENDER.md). The calling agent provides plans, parameters, scripts and visual judgment.

Live inspection is advisory; saved checkpoint observations remain authoritative. Paired live writes use retained pre-copies, explicit recipes, independent verification and the same stage rules as background execution. Unpaired access remains read-only. Qualified local add-ons use the same managed service. The public protocol exposes no raw live Python command. Qualified project-resident adapters still execute Python under the same trusted local user; their hashes are integrity checks, not a sandbox. Provider downloads and telemetry are not part of this endpoint.

## Install and connect

Use Python 3.11 or newer in a dedicated environment. Install the built wheel with
`python -m pip install PATH_TO/dcc_harness-0.23.0-py3-none-any.whl`, or install this
checkout with `python -m pip install .`. Dependencies include the pinned MCP SDK.
The existing `dcc-harness` CLI remains available. Installation registers both executables in this environment; adding the MCP to a client is separate. Only the direct MCP SDK version is pinned; transitive dependencies are not fully locked.

Configure one stdio server in your MCP client with the environment's absolute
`dcc-harness-mcp` executable and these arguments (replace paths):

```json
{
  "command": "C:/my-environment/Scripts/dcc-harness-mcp.exe",
  "args": ["--workspace", "C:/my-projects", "--blender", "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"]
}
```

This document gives a server entry, not a client-specific configuration file.
Installation does not edit client settings or register a second upstream server.
The package does not include Blender itself. This release is qualified on Blender
5.1.1 on Windows; other hosts/versions need qualification.

## Starting and continuing a build

1. Call `harness_info`, then `harness_rules` with
   `.agents/skills/dcc-harness/SKILL.md`. `harness_command_help` gives exact arguments
   for each supported CLI command.
2. Write the user's brief with `harness_write_input`. For a new scene, call
   `harness_command` with `new-project NEW_DIRECTORY --brief-file PATH --blender PATH
   --mode autonomous` (or `approval_gated`). It creates an owned baseline containing
   one non-rendering `HarnessRoot` Empty, independently observes it, initializes the
   project, pins the bundled rules and enables the mode. Use its returned `project`
   path for subsequent commands. The destination must be new; after an uncertain
   reply inspect `created.json` and state instead of repeating initialization.
3. For an existing saved file, use `adopt-preview`/`adopt-apply` if identities are
   absent, then `start`, `harness_bind` and `run-create`. Keep the artist's original.
4. Follow `brief` and `next`. Write scripts, contracts and handoffs with
   `harness_write_input`, then use `run-execute`. New IDs are scoped beneath `ext.`;
   contracts explicitly allow the intended new prefixes and changes. Each edit
   requires a stable operation UUID and the current parent. Reusing that UUID with
   identical inputs reads its retained outcome; an unresolved dispatch is never
   automatically replayed.
5. Gather native and visual evidence with `observe`, `render`, `relations`,
   `uv-report`, `harness_read` and the relevant craft rules. `requirements` supplies
   stage evidence requirements. Call `run-submit` once the evidence is ready.
6. Autonomous mode advances valid agent-reviewed stages within the brief, preserving any manifest/binding `artist_required` policy. Gated
   mode returns `AWAITING_APPROVAL`; create a `review-page` and give its file and
   export/import instructions to the owner. The artist runs `review-import` or
   `stage-complete` in their own interactive terminal. There is no MCP approval
   tool, and MCP child commands always carry the agent marker. Explicit feedback
   requiring artist authority can also pause autonomous work.

The model still supplies the reasoning, code and visual judgment. The server is
not a separate LLM, scheduler or unattended agent. A technically published
checkpoint is not automatically an artist-accepted stage. Budget exhaustion,
unknown outcomes and missing evidence remain visible stops. Consult
[managed execution](MANAGED_EXECUTION.md) for immutable mode/budget and restart
semantics. A new package source digest cannot silently replace a project's pinned
runtime; keep the qualified runtime for existing projects. Rules include their recursive local references, including executable examples, schemas and tests. Installed wheels freeze that closure in `rules.zip`; editing the checkout changes its development catalog and intentionally invalidates a mismatched rules binding. Do not edit an exported rules bundle or rebind it to bypass a runtime mismatch.

## Reusable local add-ons

`blender_capabilities` discovers installed providers, creates pinned profiles, binds
selection policy, reports requirements, resolves candidates and prepares operations.
`blender_recipe` scaffolds, retains, inspects, qualifies and registers adapters.
`blender_execute` dispatches prepared operations through either managed backend.
See [payload fields and a complete executable example](ADDON_RECIPES.md#mcp-and-cli-onboarding).

Choose `require` when a stage must use a named qualified provider. Choose `prefer`
with an explicit fallback when substitution is allowed. `best_qualified` returns
`TIMING_SELECTION_UNAVAILABLE`; only explicitly configured fallbacks may proceed.
Missing, changed or unverifiable required effects block both autonomous completion
and gated approval. Source changes require requalification; unrelated scene changes
can preserve receipts. No add-on is purchased, installed or enabled globally by this
onboarding flow. There is still no MCP owner-approval action.

## Optional live bridge

The managed build path works without an interactive Blender window. To inspect a
live scene or execute bounded recipes in it, export the bundled add-on:

```powershell
dcc-harness-mcp --workspace C:/my-projects --export-addon C:/my-projects/dcc_harness_bridge.zip
```

Install that zip in Blender's add-on preferences and enable **3D Harness observation
bridge**. In the 3D View sidebar's **3D Harness** tab, click **Start bridge**.
Set its Workspace to enable paired access. It binds only to `127.0.0.1`, defaults to port `9878`, and does not auto-start.
Use `--bridge-port` on the MCP server if you choose a different port in Blender.
An incompatible or original upstream listener is refused with an explicit error.
Do not use another raw-write MCP endpoint to bypass managed workflow policy.

`blender_observe` supports `ping`, `get_addon_info`, `get_scene_info`,
`get_object_info` and `list_scene_items`. Both the MCP adapter and the socket
dispatcher restrict that list. Replies are advisory and are labeled accordingly;
scene summaries are capped upstream and are not full saved-state observations.
Those legacy reads remain unauthenticated on loopback. Paired inspection and writes
require the private session token and current document generation. They use the
[live execution service](LIVE_BLENDER.md); same-user local access remains a trusted boundary.

The bundled add-on is an observation-only derivative of commit
`5a3618fccb2d982d0dd61e7a1879912c3100073b` (2.2.2, upstream protocol 14), with its MIT
license retained. Activity recording, telemetry consent/UI, trajectory capture,
tracking links and unused provider/account/update code are removed from the source.
Original and modified source hashes are recorded in `upstream.json`. The adjacent
adapter registers its own UI and managed dispatcher. Harness bridge protocol 3 adds
paired sessions and scoped live execution; protocol 2 remains read-only compatibility.
Replace earlier exports with the current package's add-on before using live writes.
Restart Blender after replacing an export. The bridge pins its identity when
imported and refuses a changed installation until a clean restart.
Paid generation, downloads and arbitrary live Python are outside this integration's
surface; this is not full upstream tool parity.

## Bundles, errors and limits

`harness_rules` and `harness://rules/index` expose the same hash-indexed bundle.
`--export-rules NEW_DIRECTORY` writes an inspectable local copy. Workflow bindings
retain skill and reference copies, so later package changes do not silently change
active rules. Historical `runs/`, `dist/` and `build/` links are listed in
`EXTERNAL_EVIDENCE.json`; those previous outputs are intentionally not shipped.

MCP command logs live under `WORKSPACE/.harness-mcp/requests/UUID`. Cancellation
marks the request, asks native workers to stop, and for a managed edit cancels the
run. Inspect `run-status` and retained results before `run-reconcile`. Closing or
killing the entire MCP process abruptly may leave a native child alive; inspect
owned background processes before reconciliation. Live cancellation never kills the
artist's Blender; inspect `live-status` and choose explicit `live-reconcile` recovery.
Known pre-mutation recovery refusals can be retried explicitly after resolving the
reported condition. A missing or ambiguous response is never a retry permission.
Do not assume a transport error means that
nothing changed. There is no automatic mutation retry.

Input helpers write exclusively beneath `WORKSPACE/inputs`; evidence reads are
restricted to the workspace. CLI artifact paths and trusted Python scripts have
ordinary local filesystem authority, so the server is not a filesystem or Python
sandbox. Render images above 4 MiB need local inspection or a smaller review view.
Private bridge descriptors cannot be read through the public evidence reader.

Save unsaved image edits explicitly before live attachment, editing or recovery:
a `.blend` copy alone is not proof that texture-paint buffers were preserved.
The initial live copy boundary also refuses audio/video/sequence data, volumes,
cache datablocks and unpacked external fonts pending separate qualification.

Run `scripts/verify_release.py --out NEW_DIRECTORY --blender BLENDER_PATH` from a
development environment with the declared dependencies. It checks source tests,
wheel and sdist resource equality, a clean Python environment, real stdio calls,
owned native Blender workflows and the optional live bridge. User registration
and actual artist production acceptance are separate from these fixtures.
