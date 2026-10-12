# UV report

Version 0.18.0 adds `uv-report`. It measures each mesh's texel density, UV self-overlap and UVs outside the unit square in a saved file, and checks them against targets. It works like `relations`: a fresh background Blender measures the file, never saving it, and the runtime classifies the results. The measurement sits beside the observation, not inside it, so checkpoints made before 0.18.0 are unaffected.

```powershell
python -m dcc_harness uv-report "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/uv-1" --targets "<work>/uv-targets.json"
python -m dcc_harness uv-report "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/uv-2" --project "<project>"
```

`--project` uses the project's `uv_targets` decision. The command exits 1 when any target fails.

## Targets

```json
{"schema": "dcc.uv.targets.v1", "targets": [
  {"id": "props", "select": "ext.prop.*", "min_density": 256, "max_density": 2048, "max_overlap": 0.02, "max_outside": 0.0},
  {"id": "ground", "select": "ext.ground*", "min_density": 64, "texture_px": 1024}]}
```

Each rule has these fields:

- **`select`** is an ID glob over meshes with stable IDs.
- **`min_density` / `max_density`** are in pixels per metre: √(UV area ÷ world area) × the texture size. World area is converted to square metres with the scene's unit scale, so a centimetre scene measures in metres too.
- **`texture_px`** is used when the object's materials have no image.
- **`max_overlap`** is the share of covered UV cells that more than one triangle covers.
- **`max_outside`** is the share of UV area whose triangles' centres lie outside 0..1. Allow it for deliberately tiling textures.

A rule must set at least one limit.

## Findings

Each object a rule selects gets one or more codes:

| Code | Meaning |
|---|---|
| `OK` | Within every limit the rule sets |
| `DENSITY_LOW` / `DENSITY_HIGH` | Texel density outside the range |
| `OVERLAP` | UV self-overlap above `max_overlap` |
| `OUTSIDE` | UV area outside the unit square above `max_outside` |
| `NO_UV` | The mesh has no UV layer |
| `UNMEASURED` | No texture size is known for a density limit, or the mesh is over the overlap budget |

A rule that selects nothing reports `MISSING_TARGET` and fails. `report.json` lists every finding with its values, and `measurement.json` holds the raw numbers per mesh.

## How it measures

The worker evaluates each mesh with its modifiers, on the active render UV layer.

- **Areas.** World and UV areas are summed over the evaluated triangles.
- **Overlap.** The worker rasterizes the mesh's UV triangles onto a 256 × 256 grid over their own bounds, sampling cell centres. A centre on an edge shared by two triangles is counted by neither, so adjoining triangles never read as overlap.
- **Budget.** Meshes over 200,000 triangles get density and outside measurements but no overlap estimate. They are reported as `UNMEASURED` where a rule asks for overlap.
- **Texture size.** It is the largest image any of the object's materials uses.

On the production garden (1,285 meshes, 2.36 million triangles) a report took 197 s.

## Limits

- **Overlap is a grid estimate of self-overlap within one mesh.** Overlap between different objects sharing a texture is not measured, and very small triangles can miss every cell centre.
- **Density is an average over the whole mesh.** Local stretching is not reported.
- **Not appearance.** None of these numbers says the texture looks right.
