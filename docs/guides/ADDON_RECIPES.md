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
never saves global preferences. A pre-enabled provider without proven loaded-byte
identity requires clean activation; a file hash alone cannot identify loaded Python.
Extension wheels, unavailable licenses and required networking are initially refused.
No package installation, purchasing, downloading or updating is implicit.

## Author an inert draft

Each recipe declares semantic capability IDs, a provider source digest, parameter
bounds, Blender/engine/target compatibility, supported live/background context,
read/write/dependency coverage, deterministic entry point, synchronous completion,
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

`best_qualified` currently compares measured execution time only, on matching fixture
inputs, parameters, Blender build, engine and invocation context. It returns
`NO_COMPARABLE_EVIDENCE` when those conditions do not match. It does not rank visual
quality. Initial qualification proves the MESH fixture and first declared engine;
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
The isolated qualifier can inspect broader recipe properties, but that does not make
them eligible for managed use. Existing projects keep their pinned runtime and rules.

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
| `blender_capabilities/profile` | `project`, `inventory`, `selected`, `preferences` | Immutable selected environment; `selected` is a provider-ID list |
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
