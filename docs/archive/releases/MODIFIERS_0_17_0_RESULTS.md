# Modifier and node permissions — 0.17.0

Version 0.17.0, October 11, 2026, is the first part of [build-plan](../../BUILD_PLAN.md) item P13: fine-grained contract permissions. Native UV overlap and texel density, the rest of P13, are not built. They need new observer fields and an observation version, so that checkpoints made before them are not read as changed.

## Delivered

- **`allowed_modifier_settings`.** `{object prefix: {modifier name: [setting names]}}` permits named settings of a named modifier on matching objects. Before and after must have the same stack, in the same order, with the same types and names. Any other setting, any other modifier, or an added, removed or reordered modifier fails with "Modifier settings differ beyond the permitted settings". Geometry a modifier change produces (triangles, geometry hash, bounds, UVs) still needs its own `allowed_object_prefixes` fields, so the contract says what may change downstream.
- **`allowed_material_node_fields`.** `{material: {node: {field: value}}}` sets exact desired values for node fields such as `blend_type` or `interpolation`, as `allowed_material_inputs` does for socket values. `name`, `type` and `inputs` are refused there, since inputs have their own permission. Any other difference in the material still fails.
- **Docs.** The quick reference's contract paragraph.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 408 tests: 406 passed, two Windows symlink-permission skips. 2 tests are new, one per permission, each covering its refusals |
| Installed-wheel suite | 408 tests from a standalone install of the wheel: 402 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 51 runtime and template files byte-identical to the sources. SHA-256 `98d0540130007cd3e0bcce2d4e9a10d759cd546bc7532113016bd4a7f1887aaf` |
| Native, source and installed | `scripts/qualify_modifiers.py` |
| Regression | The relocation, coverage, delivery, checks, owner, review page, guidance, render, relations, revisions and instances qualifications passed on the 0.17.0 wheel |

The native script started a project on the probe's flat bench with a Bevel modifier "Edge" (2 segments) on `bench.top` and a Mix node "Tint" (blend MIX) in `timber`. It then made four edits:

1. **Bevel width.** Changing the width to 0.02 under a contract permitting only `Edge`/`segments` was retained as `REJECTED_RETAINED`, with "Modifier settings differ beyond the permitted settings: bench.top".
2. **Bevel segments.** Changing the segments to 3 under the same contract, with the bevel's geometry fields, was published.
3. **Wrong blend value.** Changing Tint to MULTIPLY under a contract asking for SCREEN was refused, with "Material differs beyond requested inputs or desired values: timber".
4. **Right blend value.** The same change under a contract asking for MULTIPLY was published.

Local evidence is under `runs/modifiers-0.17.0-2026-10-11/`, excluded from Git.
