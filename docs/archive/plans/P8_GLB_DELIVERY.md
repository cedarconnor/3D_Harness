# P8: GLB delivery receipt

Plan for [build-plan](../../BUILD_PLAN.md) item P8, written October 11, 2026, at version 0.13.1. Target version: 0.14.0.

## Problem

When a scene leaves Blender for a game engine or a web viewer, nothing checks that the exported file still holds what was accepted. Exporters drop objects, triangulate, apply or skip modifiers, rename materials and convert axes. A delivery should say what was exported from which accepted checkpoint, and show that a fresh import of the file matches it.

## Scope

`deliver-glb SOURCE.blend --blender PATH --output-dir NEW [--project PROJECT]`

1. **Export.** A fresh background Blender opens the saved file and checks that its hash is unchanged. It records every object it will export:
   - stable ID, type and parent;
   - evaluated triangle count;
   - world bounds;
   - material IDs.

   It then exports `delivery.glb` with the glTF exporter. The settings are binary output, extras for the stable IDs, applied modifiers and Y-up. The process never saves.
2. **Reimport.** A second fresh process starts from an empty scene and imports the GLB. It records the same fields for each imported object, reading the stable ID from the extras.
3. **Compare.** The runtime matches the objects by stable ID. Each finding is one of:
   - `MISSING`: exported, but absent after import;
   - `EXTRA`: present after import with no counterpart;
   - `TRIANGLES`: a different triangle count;
   - `BOUNDS`: world bounds moved by more than 1 mm plus 0.1% of the object's size, allowing for glTF's float32 storage;
   - `MATERIALS`: different material names.

   Objects the exporter skips by design, such as unsupported types, are listed as `NOT_EXPORTED` with the reason, not hidden.
4. **Receipt.** `receipt.json` (`dcc.delivery.glb.v1`) binds:
   - the source file's hash and, with `--project`, the checkpoint it equals; any other file is refused;
   - the GLB's hash and size;
   - Blender's and the exporter's versions;
   - the export settings;
   - the findings and `passed`.

   The command exits 1 when the comparison fails.

## Qualification

- **Portable tests.** The comparison, with synthetic export and import records, covers every finding code and the tolerance edge. The receipt binding covers the active checkpoint, an earlier checkpoint and a file that is not a checkpoint. They also cover the CLI.
- **Native, source and installed.** `scripts/qualify_delivery.py` runs on:
  - the relations probe's flat bench;
  - the 0.6.0 comparison project's active checkpoint, whose bench, crate, shelf, wall, ground, camera and light include shared mesh data.

  It covers:
  - delivery passes;
  - a GLB exported from a moved copy, checked against the original manifest, fails with `BOUNDS`;
  - a truncated GLB fails to import;
  - a project delivery of a file that is not the checkpoint is refused.

## Out of scope

- FBX, USD, Draco compression, texture re-encoding checks and animation.
- Visual comparison of the GLB in a viewer.
- Collection instances are reported as the exporter writes them; instance identity across the format is not checked.
