# Reusable add-on recipes

P22 development contract. A retained draft is not qualified, and technical qualification
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
