# Coverage and rechecks — 0.15.0

Version 0.15.0, October 11, 2026, is the first part of [build-plan](../../BUILD_PLAN.md) item P6, following its [plan](../plans/P6_COVERAGE.md). The plan was written alongside the tests, not before them. UV overlap, texel density and fine-grained modifier and node fields need new native observer fields; they move to the new item P13.

## Delivered

- **`allowed_new_lights`.** A contract may permit new lights whose IDs begin with a prefix beneath `ext.`. Other new lights are still refused as outside the fixed illumination contract.
- **`allowed_scene_fields`.** A contract may permit named top-level scene fields, such as `world`, to change. Every other scene field is still compared exactly.
- **Dependency-aware rechecks.** A closed note stays `current` after a later checkpoint in two cases:
  - nothing observed changed, so the revisions are equal;
  - it is a technical note with targets, and its objects, their materials and its named materials are unchanged.

  Visual notes need a recheck after any other observed change. Notes now carry a `validity_reason`, also shown in the resume packet.
- **`removed_targets`.** A feedback response may declare objects it removed deliberately: the note's own objects, absent at the result, whose deletion a contract in the response's evidence permits. Verification then accepts them as missing. This answers the E5 finding that an agent hid an object instead of deleting it so its note could still be verified.
- **Docs.** The quick reference's contract section and the structured feedback guide.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 403 tests: 401 passed, two Windows symlink-permission skips. 6 more than 0.14.0: 2 for the contract permissions, 2 for removal, and the old blanket recheck test replaced by 3 for dependency-aware validity |
| Installed-wheel suite | 403 tests from a standalone install of the wheel: 397 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 50 runtime and template files byte-identical to the sources. SHA-256 `5f97dc42583bf365d2c531a39b146029c881cd333a55a0de2509eb6ffe15fc7c` |
| Native, source and installed | `scripts/qualify_coverage.py` |
| Regression | The delivery, checks, owner, review page, guidance, render, relations and instances qualifications passed on the 0.15.0 wheel |

The native script built lit copies of the probe's flat and sunk benches. Each adds a point lamp `ext.lamp.light` and sets the world background strength to 0.6. On a project started on the flat bench:

1. **The note.** A technical note on `bench.leg.0` was answered with a recomputed contract and verified, and was `current`.
2. **The lit edit without permissions.** It was retained as `REJECTED_RETAINED`, with "New light is outside the fixed illumination contract: ext.lamp.light" and a failed preservation check, because of the world.
3. **With permissions.** The same edit with `allowed_new_lights` and `allowed_scene_fields: ["world"]` was published. The note stayed `current`: "targets unchanged since verification".
4. **Moving the leg.** Moving the bench 6 cm into the ground was published, and the note became `needs_recheck`.

Local evidence is under `runs/coverage-0.15.0-2026-10-11/`, excluded from Git.

## Limits

- **Recheck is still conservative.** Visual notes recheck on any observed change. Technical notes compare only their anchored objects and materials, so a note whose meaning depends on a neighbouring object should anchor that object too.
- **Scene permissions are coarse.** They are per top-level field: permitting `world` permits any change inside the world graph.
- **Deferred to P13.** UV overlap, texel density and modifier or node granularity.
