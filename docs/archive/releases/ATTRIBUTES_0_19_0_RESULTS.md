# Authored attribute hash — 0.19.0

Version 0.19.0, October 15, 2026, completes [build-plan](../../BUILD_PLAN.md) item P15. The item came from the [Scenario for Blender review](../../reference/SCENARIO_BLENDER_PLUGIN_REVIEW_2026-10-15.md), whose export fingerprint hashes every mesh attribute.

## The gap

Preservation contracts compared three mesh hashes: `geometry_hash` (evaluated positions, loop vertex indices, loop counts and material indices), `source_mesh_hash` (the same fields on the authored mesh) and `source_uv_hash`. Nothing measured shading, sharp edges, seams, creases, color attributes, custom normals, custom data or loose edges. With the 0.18.1 runtime on both sides, the fixture's six variants of a protected bench top each passed a contract that permitted no change: smooth shading, a sharp edge, a crease, a seam, a color attribute and a loose edge.

## Delivered

- **`source_attribute_hash`.** Every mesh record carries a SHA-256 over the authored mesh's attribute layout and values:
  - **Layout first.** The hash begins with each included attribute's name, domain, type and length, then its values, read in bulk with `foreach_get`. Strings are read one by one.
  - **What it includes.** Every attribute except `position` and `material_index` (measured by `source_mesh_hash`) and the UV maps (measured by `source_uv_hash`). Internal layers are left out except `.edge_verts` and `.corner_edge`, so loose edges count but selection and hiding do not.
  - **Removal is a change.** Blender deletes a layer such as `sharp_face` or `uv_seam` when it is cleared, so shading a mesh smooth changes the hash.
  - **Caching.** It is computed once per mesh datablock in each observation, like the other source hashes.
  - **Unknown types.** A type this version cannot read becomes the observation issue `Unmeasured mesh attribute type`, and its layout is still hashed. All thirteen types in Blender 5.1 and the fourteen in 5.2, including 5.2's new `FLOAT4`, were read natively before release.
- **Coverage.** Observations declare `source_attributes` (version 1) in their coverage.
  - **Comparing with older observations.** When only one side declares it, `compare` skips the field and the coverage entry, as it already did for collection instances.
  - **Required coverage.** A contract check requires the field on every mesh of an observation that declares it.
  - **UV noise.** The qualified UV-noise allowance requires equal attribute hashes when both sides carry them.
- **Permissions.** `source_attribute_hash` is a grantable object field. A contract that permits `source_mesh_hash` for an object also permits its attribute hash, because edges and attributes belong to the authored mesh: existing mesh-edit contracts keep working. Granting `source_attribute_hash` alone permits an attribute-only change, such as new seams, and nothing else.
- **Guidance.** [Everyday workflow](../../guides/EVERYDAY_WORKFLOW.md#mesh-attributes), the agent quick reference and the README.

## Compatibility

Every 0.19.0 observation carries the new coverage entry and, for meshes, the new field, so re-observing an earlier checkpoint gives a new revision. Build-plan item P15 had asked for earlier checkpoints to observe as before. That cannot be met without losing the ability to tell "not measured" from "nothing to measure", because a smooth mesh with no seams or creases has no such attributes at all. Comparisons still work across versions: against an observation without the measurement, the field is skipped. A project keeps the runtime it is bound to, as for every runtime change. The instances qualification's compatibility step sets the field aside when the previous release lacks it, and records that it did.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 437 tests: 435 passed, two Windows symlink-permission skips. 8 tests are new: a changed and an unchanged hash, skipping against an unmeasured side in either direction, required coverage, mismatched versions, the `source_mesh_hash` implication, a grant of the field alone, and the UV-noise allowance |
| Installed-wheel suite | 437 tests from a standalone install of the wheel: 424 passed and 13 skipped, the two symlink cases plus the eleven that check the source tree's documentation and skills |
| Wheel integrity | All 53 runtime and template files byte-identical to the sources. SHA-256 `2c7ff3b63671cabc2dfcaa07348d2b3ac6f84f91fbbc5743024e6b511fed1aa5` |
| Native, new | `scripts/qualify_attribute_hash.py` passed from source on Blender 5.1.1 and from the installed wheel on 5.1.1 and 5.2.1 |
| Regression | The saved-state, UV report, modifiers, relocation, coverage, delivery, checks, owner, review page, guidance, render, relations and revisions qualifications passed on the 0.19.0 wheel. Instances passed with 0.18.1 as its baseline, setting the new field aside |

The native fixture saves a flat-shaded, UV-mapped bench top and seven variants, each changing only data the older hashes leave out:

| Variant | Change | 0.18.1 on both sides | 0.19.0 on both sides |
|---|---|---|---|
| `smooth` | `sharp_face` removed: smooth shading | Passes a zero-permission contract | Fails on `source_attribute_hash` alone |
| `sharp-edge` | One edge marked sharp | Passes | Fails on it alone |
| `crease` | One edge creased to 1.0 | Passes | Fails on it alone |
| `seam` | One edge marked as a seam | Passes | Fails on it alone |
| `color` | A byte color attribute | Passes | Fails on it alone |
| `loose-edge` | An edge joining two existing vertices; positions and faces unchanged | Passes | Fails on it alone |
| `every-type` | One attribute of every type Blender offers, 13 on 5.1 and 14 on 5.2 | Passes | Fails on it alone, observed `READY` with no unmeasured type |

In every variant `source_mesh_hash`, `source_uv_hash`, `geometry_hash`, `uv_hash` and the vertex and triangle counts were unchanged. Every variant passed a contract granting `source_mesh_hash`, and one granting `source_attribute_hash` alone. An unchanged scene saved twice observed with the same revision in separate processes. A 0.18.1 before observation against a 0.19.0 seam passed, the documented skip.

On the production garden's checkpoint 9 (1,285 meshes), observation took 44 s with 0.18.1 and 44 s with 0.19.0 on both Blender versions, so the hash adds no measurable cost.

Local evidence is under `runs/attributes-0.19.0-2026-10-15/`, excluded from Git.

## Limits

- **Authored data only.** The hash reads the authored mesh. Attributes a modifier creates are covered through `modifier_settings` and the evaluated `geometry_hash`, not hashed separately.
- **All or nothing per mesh.** A contract cannot permit a mesh's topology to change while protecting its seams: `source_mesh_hash` permission includes the attributes.
- **Across versions.** A before observation from 0.18.1 or earlier cannot catch an attribute change; the comparison skips the field.
