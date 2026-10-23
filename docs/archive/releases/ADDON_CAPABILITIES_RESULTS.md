# Reusable add-on capability qualification

Qualified: 0.23.0, Python 3.11, MCP SDK 1.26.0 and Blender 5.1.1 on Windows. All
17 maintained release checks passed. Source and clean-installed suites each ran
588 tests: 586 passed and two existing Windows symlink-permission cases skipped.
The source suite took 271.768 seconds; the installed suite took 238.060 seconds.

## Delivered behavior

- Static inventory distinguishes installed, enabled, compatible and source-identifiable
  providers. Explicit profiles pin source/assets, Blender build, dependencies and
  non-secret preferences without changing global preferences.
- Immutable draft adapters qualify through owned native function, operator or node-asset
  cases, repeat application, measured outputs and independent reopen. Failed, changed
  or unsupported recipes remain unavailable.
- Versioned `require`, `prefer` and timing-only `best_qualified` policies select providers
  for explicit targets/stages. Stage submission and completion require actual verified
  service receipts; a direct script or prose claim cannot stand in for required use.
- Geometry/material changes and deleted effects require an update to the same effect
  key. Unchanged effects reuse proof across unrelated checkpoints; another layer needs
  an explicit new slot. Relevant source changes require requalification.
- Public MCP/CLI onboarding and execution use the existing shared journal, UUID,
  cancellation, budgets and owner-review boundary. No telemetry, activity recording,
  provider download or implicit installation was added.

See [the capability guide](../../guides/ADDON_RECIPES.md) for payloads, limitations and
an executable example, and [the implementation plan](../../superpowers/plans/2026-10-22-addon-capabilities.md)
for the task breakdown.

## Retained release evidence

The machine-readable report is `runs/p22-release/VERIFICATION.json`. Its native-qualified
wheel SHA-256 is `b9488d87e049f700206f1bc29066acd600898249c2abea38841e755a7c372b45`.
The final documentation artifact is rebuilt separately and must retain identical runtime
and bridge bytes; its report is `runs/p22-delivery/VERIFICATION.json`. Local run artifacts
are excluded from Git and the rules distribution.

The release checks source tests, wheel/source-archive byte parity, clean installation,
installed tests and CLI/MCP entry points, source/installed standalone bridge equality,
native units/adoption/execution/MCP, all 26 P21 live scenarios, dirty-image and external
dependency preservation, and the complete P22 matrix. Export tests also reject missing
recipe modules, changed members and unsafe nested manifest paths. The telemetry scan
covers all exported Python members; owned GUI fixtures audit outbound sockets, activity
handlers, standalone imports and private pairing cleanup.

`native-capabilities/VERIFICATION.json` indexes five completed groups:

| Group | Evidence |
|---|---|
| Profiles | Static legacy/extension discovery, explicit activation, source identity, worker/observer propagation, unavailable dependencies and loaded-source refusals |
| Onboarding | Eight recipes: seven qualified and one expected poll failure refused; function/operator/node asset, actual viewport, shared material/copy, repeat/reopen, no-op, mutation-before-error, modal and network failures, source drift |
| Routing | Background/live × autonomous/gated; primary/secondary engine selection, required-use and stale-source stops, stable UUID publication |
| Revisions | Both backends; eight scenarios and nine published operations each, with two shared material users preserved: zero-job reuse, unrelated checkpoint, geometry, material, deletion, reload, second slot and source drift |
| Stdio | Four backend/mode combinations using public inventory/profile/draft/qualify/register/bind/resolve/prepare/execute/submit tools; missing/stale receipts and agent approval refused, identical UUID retry and zero-job reuse proven |

## Corrections established during development

Focused tests reproduced and fixed public native-ID validation for Unicode/colon/space
IDs, runtime-pinned reuse before mutation-only admission, reuse of a current effect after
its benchmark input has changed through the effect itself, and capability query exit
status. An unmet requirement is query data; a stage submission with missing evidence
still fails. Typed MCP cancellation marks the run and reaps its owned controller.

Earlier native fixtures exposed Blender's embedded-Python long-path limit for nested
registration hashes. Registrations now use one full report hash as their filename while
retaining full recipe/profile identities inside. An unused factory material and reopened
evaluated-UV float noise were fixture corrections; production inventory checks and the
existing narrow P21 equivalence rules were not relaxed.

## Limits

These are synthetic-provider technical results, not artist acceptance, arbitrary-product
compatibility or evidence of better art. Initial managed recipes cover measured MESH
fixtures and qualified engines/contexts. Custom-property coverage and GUI-only providers
without independent background verification are refused. Broad overlapping output scopes
can conservatively require another update. `best_qualified` compares fixture execution
time only on comparable inputs; it does not score visual quality.

Qualification binds the harness runtime as well as provider/recipe/profile/build bytes;
upgrades require new proof. Existing projects keep their pinned installed runtime. The
local filesystem and provider Python remain trusted automation, not an OS sandbox.
Private/paid add-ons remain user-installed and separately licensed/qualified. No artist
scene, global MCP registration, purchase, GitHub push or `main` update was part of this work.
