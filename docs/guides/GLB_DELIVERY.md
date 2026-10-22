# GLB delivery

Since v0.20.0, export requires `scene.unit_settings.scale_length == 1` (one metre per Blender unit). Other scales are rejected before a GLB is written. Physical conversion is not yet qualified; changing only the scene scale property is not a geometry-preserving conversion. Use a separately prepared and verified metre-scale asset. Successful bounds and tolerance comparisons below are in metres.

Version 0.14.0 adds `deliver-glb`. It exports a saved scene to a binary glTF file, imports the file into an empty scene, and records whether what arrived matches what was exported. With `--project`, the receipt is bound to the accepted checkpoint the file equals.

```powershell
python -m dcc_harness deliver-glb "<project>/checkpoints/000009/checkpoint.blend" --blender "<BLENDER>" --output-dir "<work>/delivery-1" --project "<project>"
```

## What it does

1. **Export.** A fresh background Blender opens the saved file and checks that the bytes are unchanged. It then records each object it delivers:
   - stable ID and type;
   - triangle count after modifiers;
   - world bounds;
   - material names.

   It exports `delivery.glb` and never saves. The export settings are binary glTF, Y-up, modifiers applied, and custom properties as extras, so the stable IDs travel with the objects.
2. **Reimport.** A second fresh process starts from an empty scene and imports the GLB, recording the same fields.
3. **Compare.** The runtime matches objects by stable ID and reports these codes:
   - `MISSING`: exported, but absent after import;
   - `EXTRA`: present after import, with no exported counterpart;
   - `DUPLICATE`: two imported objects share an ID;
   - `TRIANGLES`: the triangle count changed;
   - `BOUNDS`: the world bounds moved by more than 1 mm plus 0.1% of the object's size, which allows for glTF's float32 storage;
   - `MATERIALS`: the material names changed.

   Cameras, lights and collection instances are listed under `not_exported`, each with the reason. What the exporter writes for an instance, its root and the members beneath it, is set aside after import and listed under `instance_content`. An object the source itself parents beneath the instance is still compared.

The folder holds `delivery.glb`, `export.json`, `reimport/import.json`, both Blender logs and `receipt.json`. The receipt (`dcc.delivery.glb.v1`) records:

- the source file's hash;
- with `--project`, the checkpoint it equals: its ID, sequence and whether it is the active one;
- the GLB's hash and size;
- Blender's and the exporter's versions;
- the export settings;
- the comparison.

The command exits 1 when any finding is reported. With `--project`, a file that is not one of the project's checkpoints is refused.

## Limits

- **Geometry and names only.** The receipt covers objects, triangle counts, bounds and material names. It does not cover textures, shading, animation, or how another application renders the file.
- **Collection instances.** They are written as the exporter chooses; their identity is not checked across the format.
- **Libraries.** For a project that links libraries, deliver the working copy beside them; the stored checkpoint cannot resolve them. Such a copy is not byte-identical to a checkpoint, so deliver it without `--project` and keep the receipt with the checkpoint's own record.
