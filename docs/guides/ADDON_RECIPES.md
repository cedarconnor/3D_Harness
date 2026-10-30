# Reusable add-on recipes

A retained draft is not qualified, and technical qualification
is not evidence that an add-on produces better art. Product-specific compatibility must
be established with the user's installed provider and its own recipe cases.

## Discovery and environment

Inventory reads static legacy `bl_info` or extension manifests and registered operator
metadata. Disabled providers are not imported. Installed, enabled, compatible, source
identity and qualification are separate facts. An operator's RNA explains its syntax;
the calling agent must inspect documentation/source and decide its semantic purpose.

Create an explicit profile from selected local providers. It pins the Blender build,
all provider source/assets within the supported source boundary, dependencies and
whitelisted non-secret scalar preferences. Workers activate it before opening the
candidate, including independent observers. Activation records its session delta and
restores temporary preferences and extension repositories after synchronous provider
work. Owned background workers keep that scope open through worker execution. A
pre-enabled provider without proven loaded-byte identity requires a clean Blender
session with that provider disabled before harness activation; merely hashing its
files cannot identify already loaded Python. The harness does not disable artist providers.
Extension wheels, unavailable licenses and required networking are initially refused.
No package installation, purchasing, downloading or updating is implicit.
Providers with unknown network behavior require an explicit `reviews` entry keyed
by provider ID: `{source_digest, reviewed_by, reason}`. The authorized agent may
review local source; this is a source-bound assertion, not a security sandbox or an
extra owner approval gate. Required-network/license refusal remains in force.
Implicit inventory directories are removed after success; failure retains native
evidence and reports its path. Explicit `out` directories always remain.

## Author an inert draft

Each recipe declares semantic capability IDs, a provider source digest, parameter
bounds, Blender/engine/target compatibility, supported live/background context,
read/write/dependency coverage, deterministic entry point, completion protocol,
effect identity, shared-material policy, validators and qualification cases.
Negative cases name a specific expected failure reason; an unrelated setup failure
does not satisfy them. The full effect ID stays in evidence even when Blender's
bounded native names use its shorter deterministic prefix.

`recipes.scaffold(recipe)` supplies a deliberately incomplete adapter. The calling
agent writes it; the server does not contain a hidden drafting model. Implement:

- `preflight(context, parameters)`: validate context, operator poll and dependencies
  before mutation. Report unsupported coverage rather than guessing.
- `apply(context, parameters, effect_id)`: invoke the declared function, operator or
  node asset and update the same owned effect. Never stack duplicates for the same ID.
- `inspect_output(context, effect_id)`: measure actual effects and their count. A
  `FINISHED` operator status or a custom success flag is not sufficient.
- `verify_saved(observation, output)`: validate independent reopened measurements and
  the intended effect. Missing dependencies or unverifiable output must fail.

Python function invocation can declare `arguments`, mapping native keyword names
to `target`, `effect_name`, `effect_id`, `parameters`, `context`, or `parameter:NAME`.
For example `{"object":"target","width":"parameter:amount","name":"effect_name"}`
calls an unchanged `bevel(object, width, name)` API. Without the mapping, the legacy
`function(context, parameters, effect_id)` protocol remains. A newly returned native
modifier can be named by the harness; unowned existing modifiers are not adopted.
Only one declared invocation is supported. The adapter and output inspector cannot
manufacture measured output outside that invocation. An unchanged call needs exact
prior successful invocation proof in the same native process; cross-process reuse
uses verified host receipts. Source, intent and measured state are checked each time.
If declared dependencies change, an idempotent refresh that leaves the claimed
modifier unchanged is unsupported without that exact native contribution proof.
The lifecycle qualifier uses a separate synthetic scale/finish provider: authored
mean vertex radius and material roughness determine bevel width. Its geometry and
material refreshes therefore produce measurable modifier changes. The fixed-width
provider remains a refusal case; these fixtures make no artistic quality claim.

Version-one claimed outputs require one native modifier on the target, named
`DCC::` plus the first 48 characters of the effect ID. `coverage.writes` must include
`modifiers`; standalone geometry, material and shader-node effects are refused at
draft/load admission. Node assets use their owned geometry-node modifier. Declared
geometry/material side effects alongside that modifier remain subject to the existing
coverage and shared-user checks.

The harness independently measures the modifier identity, stack position, native
settings and supported node-asset data before and after the provider call. Inspector
JSON is supplementary: changed transform metadata cannot establish modifier work.
Editor expansion/active flags do not count as effect changes. Saved verification
requires the same retained native effect evidence; legacy outputs without it must be
requalified. Whole-scene preservation and unsupported-surrounding-state refusal still
apply.

## Version-two shader and asynchronous recipes

Use `schema: "dcc.capability.recipe.v2"` for the extended contracts. Existing
immutable v1 bundles keep their meaning. A changed runtime requires new technical
qualification; projects keep their pinned runtime until explicitly moved.

Every v2 recipe adds one closed `effect` selector:

```json
{"kind":"modifier"}
{"kind":"material","material_id":"{effect_name}","slot":0}
{"kind":"shader_nodes","material_id":"stone","slot":0,"nodes":["{effect_name}"]}
```

These are three alternative effect objects, not one JSON document. Material effects
own their material ID and name. Shader-node effects own named nodes in the selected
material. Slot selectors range from zero to 1023. `{effect_name}` expands to `DCC::` plus the first 48 effect-key characters;
node selectors may append up to ten printable ASCII characters. The full key is
retained in `dcc_effect_id`; modifier ownership uses a reserved
`dcc_modifier_effects` mapping on the target object because Blender modifiers do
not support arbitrary custom properties. Pre-existing unowned effects are refused.

Shader writes require `materials` or `nodes` coverage and an explicit shared-user
policy. Native graph evidence includes nested groups, sockets, interfaces, settings,
links, image hashes and ownership. Unknown relevant graph state remains a coverage
failure. The preservation guard protects other nodes, materials, object slots and
worlds, including transitive shared groups. Effects cannot adopt unrelated artist
data. Geometry-only effects remain outside this v2 contract.

Synchronous invocation keeps the existing adapter protocol. An asynchronous v2
invocation uses a pinned Python submit wrapper and these additional fields:

```json
{
  "kind":"python_function",
  "entry":"provider.submit",
  "completion":"asynchronous",
  "cancellation":"cooperative",
  "poll":"provider.poll",
  "cancel":"provider.cancel",
  "collect":"provider.collect",
  "poll_interval":0.1,
  "timeout":120,
  "cancel_grace":5
}
```

`entry` has the usual `(context, parameters, effect_id)` signature or the optional
native keyword mapping. The adapter's `apply` calls `context['invoke']()` exactly
once and returns the submit handle. `poll(context, handle)` reports a JSON object
whose `state` is `PENDING`, `SUCCEEDED`, `FAILED` or `CANCELLED`, optionally with
`progress` and `error`. Poll must not mutate native scene data. The provider may
advance external work or use its qualified Blender callbacks between ticks.
`cancel(context, handle)` requests termination without native scene mutation;
subsequent polling must confirm termination. `collect(context, handle)` returns
`{"status":"FINISHED"}` after successful completion and may finalize the declared
native output. Handles and callback responses must be JSON values bounded to 64 KiB.
The independent native inspector still establishes the actual effect.

The bounds are 0.05–5 seconds between regular polls, 0.1–3600 seconds for timeout,
and 0.1–60 seconds for cancellation grace. Cancellation/deadline scheduling can
advance sooner than the regular poll interval. Submit, cancel and collect intent
are persisted before dispatch. A reconstructed unfinished operation requires
reconciliation and never repeats mutation. Live status exposes its target scope,
phase and progress through the existing job APIs. Pending work has no saved
candidate or completion-valid receipt.

Live execution returns control to Blender between steps, allowing provider timers
and modal wrappers to run. A modal operator requires an explicit source-pinned
completion/cancellation wrapper; `RUNNING_MODAL` alone is insufficient. Background
qualification is separate and requires progress independent of a GUI event loop.
GUI-only execution still needs independent background reopening of the saved result.

Temporary profile preferences and offline auditing remain active across provider
callbacks, with preference autosave disabled until cleanup. Confirmed terminal work
restores the prior settings. Uncertain termination retains the reservation and guard
for reconciliation; stopping polling does not prove a provider has stopped. Manual
artist edits inside the active write scope cannot always be distinguished from
provider progress. Avoid editing that scope while its operation is pending.

For uncertain live work, request cancellation through the existing job API. Its
cleanup timer records cancellation intent once and polls for confirmed termination
without collecting output. Recovery capture and acknowledgement refuse an active
lease, even if its original execution mapping is lost. Only confirmed cleanup can
restore the lease and allow a separate recovery decision; a failed stop still needs
external reconciliation or a fresh Blender session.

The portable tests and owned native fixtures cover synthetic providers. Run the
[shader/async matrix](../../scripts/qualify_shader_async.py) with a fresh output
directory and Blender 5.1.1; it records native renders, repeat/update, cancellation
and independent saved-file reopen. The [managed MCP qualifier](../../scripts/qualify_shader_async_managed.py)
adds public qualification/registration, required-provider enforcement, managed
publication, receipt reuse and both execution/approval modes. These do not qualify
an untested third-party product. Qualify the installed provider's own cases before
binding it into an artist project.

Reproducible sources are the [provider](../../tests/fixtures/addons/legacy/shader_async_fixture/__init__.py),
[adapter](../../tests/fixtures/addons/shader_async_adapter.py) and
[owned native worker](../../scripts/_shader_async_qualify.py).
See the [0.24.0 qualification results](../archive/releases/SHADER_ASYNC_0_24_0_RESULTS.md)
for the measured source, installed-package and native evidence and their limits.

Parameter schemas use a strict, portable JSON Schema subset shared with Blender:
closed objects (`properties`, `required`, `additionalProperties: false`), arrays with
`items` and length bounds, scalar types, `enum`, numeric bounds and string length bounds.
`description` is allowed. References, regexes, combinators, unknown keywords and non-finite
numbers are rejected; no schema can fetch network resources. This avoids a different
validator in Blender's Python runtime.

Draft retention copies the adapter and explicitly named assets into a content-addressed
bundle. Inspection parses JSON and hashes bytes; it does not import the adapter.
Different contents under one recipe ID create different immutable versions. Do not edit
retained files: changed or additional members invalidate the bundle. Provider binaries,
paid assets and licenses remain external unless explicitly supplied as recipe assets.

## Qualification and use

Qualification is a separate retained report bound to the recipe, profile, provider,
Blender and harness runtime identities. Run only on owned disposable scenes. Exercise successful effects,
wrong poll/context, no-op success, mutation before error, unsupported modal completion,
shared material scope, independent reopen and a repeated update with one effect ID.
Live GUI and background are separate qualifications; a background pass cannot imply
viewport support. Preserve temporary selection/context where still valid.

Declare all input dependencies that affect the result, including geometry, materials,
source assets and environment. Shared materials must name all users or explicitly copy
for a single user. Revisions with unchanged dependencies reuse evidence; relevant
changes update the original effect. A deleted effect is stale. A new slot is an explicit
request for another effect, not an automatic consequence of repeated prompts.

Core telemetry remains absent. Offline fixture audits are evidence for those runs,
not an operating-system sandbox for arbitrary third-party Python. Inspect provider
network behavior before activation; quarantined or unreviewed providers are unavailable
under the default policy. Source changes, even without a version bump, require a new
profile and requalification. Preserve older installed runtimes for older projects.

## Select and enforce providers

Bind a versioned capability policy to explicit instance IDs, ID prefixes or object
types and workflow stages. Each rule names a semantic capability, effect slot,
parameters, dependencies and retained recipe/profile candidates. `require` permits
only a qualified named provider. `prefer` permits another provider or manual work
only when that fallback is explicitly configured. A policy revision invalidates
the affected stage receipts; it never edits a previous policy event.
Once an artist confirms a policy, later revisions also require artist authority and
owner confirmation. This conservative guard covers all changes, including additions;
agent-authored policies remain revisable by the agent. The owner runs
`capability-bind --request binding.json` in their own interactive terminal with
`authority.role` set to `artist`. The CLI displays the policy and asks for confirmation;
identical committed request IDs do not prompt again. MCP cannot supply that approval.

`best_qualified` currently returns `TIMING_SELECTION_UNAVAILABLE`; only explicitly
configured provider/manual fallbacks may proceed. Worker elapsed time includes
saving and rendering, so it cannot select a provider winner. Benchmark metadata is
retained for parsing compatibility but does not invalidate dependency receipts.
Initial qualification proves the MESH fixture and first declared engine;
a longer compatibility list is not proof that every target/engine combination works.
Node-asset entry points are native group names, including spaces and Unicode (up to
255 characters, without control characters). Function entries use a dotted Python
callable path; operator entries use exactly `category.operator`.

Managed live use also requires an independent background reopen under the same
profile. GUI invocation alone cannot qualify the publication verifier. Activation
happens after the recovery copy and dispatch marker because provider registration
may itself mutate the scene. Session activation never saves global preferences.

The shared execution service retains the chosen requirement, recipe, profile and
policy with the operation UUID. A capability receipt is produced only after actual
invocation, independent output validation and publication. Stage submission and
completion recheck service-owned evidence; a prose claim or owner approval cannot
substitute for required technical evidence. Projects with no capability policy
retain their existing behavior.

## Revision freshness

At managed boundaries, requirements enroll matching targets and recheck declared
inputs, profile/recipe sources and the measured output scope. A matching receipt can
survive an unrelated checkpoint; a new request reuses it without a native job or budget
charge. Geometry/material changes and removed or edited effects require a new update
with the same effect key. New explicit slots permit additional layers. Broad recipes
may conservatively invalidate each other when they share measured output scope; no
automatic repair loop runs, and ordinary execution budgets still apply.

`changes(root, before, after)` reports scene enrollment/dependency changes. `status`
and stage checks additionally validate current provider/recipe qualification. Direct
artist edits require explicit live refresh first; no activity watcher is installed.
Initial managed support refuses recipes whose coverage includes custom properties,
which P21 does not measure, and refuses policies that omit declared recipe inputs.
The native qualifier also refuses unmeasured properties. Capability projections use
the target and measured active-scene material users consistently on host and native
paths. Whole-scene preservation remains a separate admission requirement: an unrelated
unlabeled object or unsupported Geometry Nodes graph can still refuse publication.
This does not claim support for arbitrary surrounding scenes. Existing projects keep
their pinned runtime and rules.

Provider-dependent preview and recovery beyond the retained synthetic fixtures are
not yet qualified. An add-on whose saved result needs active provider registration
during those paths needs additional native proof; do not infer that support from
successful execution and publication alone.

## MCP and CLI onboarding

The public MCP tools share the CLI service APIs. Each CLI action takes `--request`
pointing to a JSON payload; native actions also accept `--blender PATH`. MCP uses its
configured Blender executable. For example, `recipe-draft --request draft.json`
and `blender_recipe(action="draft", payload=...)` retain the same inert bundle.

| Tool/action | Required payload fields | Result |
|---|---|---|
| `blender_capabilities/inventory` | none; optional `binding`, `roots`, `out` | Discovered providers; roots are `{path, namespace}` entries |
| `blender_capabilities/profile` | `project`, `inventory`, `selected`, `preferences`; optional source-bound `reviews` | Immutable selected environment; `selected` is a provider-ID list |
| `blender_recipe/scaffold` | `recipe` | Incomplete adapter text; no native execution |
| `blender_recipe/draft` | `project`, `recipe`, `adapter`, `assets` | `DRAFT` bundle; adapter/assets are explicit local paths |
| `blender_recipe/inspect` | `project`, `recipe_id`, `recipe_digest` | Draft, failed, qualified or stale state |
| `blender_recipe/qualify` | previous three plus `profile_digest`, `out` | Owned native qualification report; fresh output directory |
| `blender_recipe/register` | `project`, `report` | Validated retained qualification registration |
| `blender_capabilities/bind` | `project`, `policy`, `expected_revision`, `request_id`, `authority` | Versioned policy event; same authority guards as workflow binding |
| `blender_capabilities/requirements` | `project`, `stage` | Current required effects, freshness and selection decisions |
| `blender_capabilities/resolve` | `project`, `requirement` | Applicable qualified candidate or explicit stop/fallback |
| `blender_capabilities/prepare` | `project`, `requirement`, `resolution`, `parameters`, `operation_id`, `contract`, `handoff`; optional `timeout` | Typed operation or verified `REUSED` result; no dispatch |

Execute a prepared operation with `blender_execute(request={"project": PROJECT,
"operation": PREPARED_OPERATION})`, or save just the operation JSON and run
`run-operation PROJECT --request operation.json`. Both backends use the same
reservation, budgets, publication and cancellation service. Inspect `run-status`
after an uncertain response; repeat the same UUID only to retrieve its retained
outcome. A fresh requirement already satisfied by an unchanged effect returns
`REUSED` without allocating another operation. Background cancellation is
`run-cancel`; live jobs also expose the existing `blender_job` status/cancel actions.

For a complete executable example, run:

```powershell
python scripts/qualify_capabilities.py --runtime . --blender "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --out runs/my-new-capability-proof --case stdio
```

This creates only disposable fixture projects. The [stdio example](../../scripts/qualify_capability_mcp.py)
contains every payload in order: discover, profile, draft, qualify, register, bind,
resolve, prepare, execute, reuse and submit in both modes and backends. Its
[provider](../../tests/fixtures/addons/legacy/capability_fixture/__init__.py) and
[adapter](../../tests/fixtures/addons/capability_adapter.py) are synthetic examples,
not implementations for a particular commercial product. Their cases deliberately
exercise failures; do not enable them in an artist project.

For a private or paid add-on, the user installs and licenses it separately. Inventory
its actual source, select it into a profile and author a recipe against its documented
API. Keep proprietary code and licenses outside the distribution. Qualify representative
inputs before binding a `require` rule; a generic operator listing cannot establish
semantic suitability. The calling agent must read `requirements` at each stage and
after refresh, then prepare missing/stale effects. The server enforces required use at
submission/completion; it does not silently watch edits or run an unattended agent.
