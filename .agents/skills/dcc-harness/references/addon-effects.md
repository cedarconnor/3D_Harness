# Managed add-on effects

Read this for add-on authoring, use, cancellation or continuation in a persistent
DCC project. The [recipe guide](../../../../docs/guides/ADDON_RECIPES.md) supplies
exact schemas, public tool payloads and CLI commands.

## Check the project's runtime

Use `brief`/`resume` and the project's pinned files and runtime identity. Runtime
0.24.0 introduces `dcc.capability.recipe.v2`: owned modifiers, standalone materials,
shader nodes and cooperative asynchronous Python lifecycle wrappers. V1 remains
modifier-based and synchronous. A project pinned to 0.23 cannot gain v2 support by
loading this newer skill. Keep its pin until an explicit compatible runtime change,
then requalify affected recipes; do not replace pinned instructions silently.

Inventory, enabled state, compatible metadata and an inert draft are separate from
qualification. Pin the installed provider/profile and source/assets; draft, qualify
on owned disposable inputs, register the report, then resolve against the project's
capability policy, target, engine and live/background context. Synthetic harness
qualification does not qualify an untested third-party provider or its artistic output.

## Own and measure the intended effect

Standalone shader effects require no placeholder modifier. Use the v2 material or
shader-node selector and stable capability/target/slot identity. Native ownership,
bindings, nested graph settings/links and image dependencies must establish the
effect; adapter JSON or a success flag alone is insufficient. Unknown relevant
native state remains a coverage refusal. A separate layer needs a new explicit slot.

Inspect direct shared users and transitive node-group users in other materials and
worlds. Choose explicit all-users scope or an isolated single-user copy; preserve
displaced originals through saving. Author exact `allowed_unbound_material_ids` or
`allowed_material_graphs` declarations when the intended binding/topology transition
needs them. These do not authorize unrelated material edits. Independently reopen
and verify both the effect and retained protected-state fingerprint. Use Cycles or
EEVEE evidence to review shader appearance; Workbench cannot show the shader result.

## Advance asynchronous work once

A qualified v2 Python wrapper declares submit, poll, cancel and collect plus bounded
poll interval, timeout and cancellation grace. Submit returns a retained JSON handle.
Provider handles and managed operation UUIDs are different: inspect the existing
operation through `run-status` or the live job API, using its managed UUID. Live
execution yields to Blender between steps so provider timers/modal wrappers can run.
Read [live Blender operation](../../../../docs/guides/LIVE_BLENDER.md) before using
the exact `blender_job` status/cancel/reconcile payloads or their CLI equivalents.

Do not publish a pending job or treat a handle as completion. The shared service
collects a successful terminal result, independently verifies its saved native output,
then publishes the checkpoint and receipt. Reuse a fresh receipt without another job.
After a lost reply, inspect retained status/outcome; never submit again with a new
UUID or replay submit/collect to discover whether it worked. A reconstructed
unfinished journal requires reconciliation. Keep the normal project budgets.

## Stop before recovery

Request cancellation through the backend's existing job API. An expired deadline or
grace period does not prove termination. Unconfirmed work retains its reservation,
temporary profile preferences and offline lease. The explicit stop path records
cancellation intent once and polls for confirmed termination without collecting.
Only after the lease is restored may the existing recovery route archive/restore
or release the reservation. Recovery itself must not run provider callbacks.
The explicit live stop path reports `termination: STOPPED` when cleanup is confirmed;
the operation can remain `NEEDS_RECONCILIATION` until its separate recovery decision.

If termination cannot be established, retain the evidence and unresolved state for
external reconciliation or a fresh Blender session. Do not kill an artist's Blender,
reset scripts, restore a precopy while callbacks may still mutate it, or infer safety
from a missing response. A raw `RUNNING_MODAL` status requires a qualified completion
and cancellation wrapper; it is not a completion receipt.

## Carry the state forward

In `CONTINUE.md`, retain the pinned runtime, recipe/profile identities, managed UUID,
handle/journal reference, last observed phase/status, verified checkpoint/candidate
and precopy references, termination/lease state, remaining budget and next action.
Distinguish native qualification, actual live execution, independent saved verification
and artist acceptance. The [0.24.0 results](../../../../docs/archive/releases/SHADER_ASYNC_0_24_0_RESULTS.md)
bound the harness's synthetic tests; qualify each real provider's own cases.
