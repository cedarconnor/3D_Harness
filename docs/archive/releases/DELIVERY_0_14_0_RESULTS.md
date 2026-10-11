# GLB delivery receipt — 0.14.0

Version 0.14.0, October 11, 2026, is [build-plan](../../BUILD_PLAN.md) item P8, following its [implementation plan](../plans/P8_GLB_DELIVERY.md). The tracker had held it "until export is required". It was built now under the user's instruction to push through the plan's features.

## Delivered

- **`deliver-glb SOURCE.blend --blender PATH --output-dir NEW [--project PROJECT]`.**
  - **Export.** A fresh background Blender opens the saved file, checks its bytes are unchanged and records each delivered object. It then exports `delivery.glb` and never saves. The export is binary glTF, Y-up, with modifiers applied and custom properties as extras, so the stable IDs travel.
  - **Reimport.** A second fresh process imports the GLB into an empty scene.
  - **Compare.** The runtime matches objects by stable ID and reports `MISSING`, `EXTRA`, `DUPLICATE`, `TRIANGLES`, `BOUNDS` and `MATERIALS`. Bounds allow 1 mm plus 0.1% of the object's size, for glTF's float32 storage.
  - **Not delivered.** Cameras, lights and collection instances are listed as `not_exported`, each with its reason.
- **The receipt (`dcc.delivery.glb.v1`).** It binds the source hash, the GLB's hash and size, Blender's and the exporter's versions, the settings and the comparison.
  - With `--project`, it also binds the checkpoint the file equals; any other file is refused.
  - The command exits 1 on any finding.
- **Docs.** A [GLB delivery guide](../../guides/GLB_DELIVERY.md).

## Executed checks

| Check | Result |
|---|---|
| Source suite | 397 tests: 395 passed, two Windows symlink-permission skips. 7 tests are new: four for the comparison, two for checkpoint binding and the receipt, one for the CLI |
| Installed-wheel suite | 397 tests from a standalone install of the wheel: 391 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 50 runtime and template files byte-identical to the sources. SHA-256 `0dc386550f48058e9c340ba2727dfd8ffc6fd5c113483b07069efc7cbf6ea1e0` |
| Native, source and installed | `scripts/qualify_delivery.py` |
| Production scene | The production garden's checkpoint 9: 1,289 objects, 2.36 million triangles and shared mesh data |
| Regression | The checks, owner, review page, guidance, render, relations and instances qualifications passed on the 0.14.0 wheel |

The native script checked, from both runtimes:

1. **Flat bench.** The relations probe's flat bench delivered all six meshes, and its camera and sun were listed as not delivered.
2. **Bound to a project.** The 0.6.0 comparison project's active checkpoint delivered with `--project`. Nine meshes matched, the receipt was bound to the checkpoint, and the key light and camera were listed as not delivered.
3. **Moved copy.** A copy with the bench top moved 5 cm was delivered on its own. Its reimport, compared with the original export record, failed with exactly `bench.top: BOUNDS`.
4. **Truncated GLB.** It failed to import, and no import record was written.
5. **Not a checkpoint.** A project delivery of the flat bench, which is not one of that project's checkpoints, was refused.

**The production scene.** Delivered from source with `--project`, all 1,285 meshes matched with no findings. Its three cameras and the sun were listed as not delivered. The GLB is 65.5 MB, and the run took 53 s.

Local evidence is under `runs/delivery-0.14.0-2026-10-11/`, excluded from Git.

## Limits

- **Geometry and names only.** The receipt covers objects, triangle counts, world bounds and material names. It does not cover textures, shading, animation or appearance in another application.
- **Collection instances.** Their identity across the format is not checked.
- **Libraries.** A file that links libraries must be delivered from its working copy beside them, which is not byte-identical to a checkpoint.
