# UV report — 0.18.0

Version 0.18.0, October 11, 2026, completes [build-plan](../../BUILD_PLAN.md) item P13 with texel density and UV overlap. The plan had them as observer fields. They ship instead as a separate measured report, `uv-report`, following `relations`. Adding fields to the core observation would have needed a new observation version: otherwise every checkpoint made earlier reads as changed when compared with a newer one. It would also have added their cost to every `observe`.

## Delivered

- **`uv-report SOURCE --blender PATH --output-dir NEW (--targets FILE | --project P)`.** A fresh background Blender measures every mesh with a stable ID on its active render UV layer, after modifiers:
  - world and UV areas, and so UV units per metre;
  - a 256 × 256 grid estimate of UV self-overlap, with centres on shared edges counted by neither triangle;
  - the share of UV area outside the unit square;
  - the largest texture its materials use.

  Meshes over 200,000 triangles skip the overlap estimate and say so.
- **Classification.** Portable code classifies the measurements against `dcc.uv.targets.v1` rules: `min_density`/`max_density` in pixels per metre, `max_overlap`, `max_outside`, and a `texture_px` fallback. The codes are `OK`, `DENSITY_LOW`, `DENSITY_HIGH`, `OVERLAP`, `OUTSIDE`, `NO_UV`, `UNMEASURED` and `MISSING_TARGET`. `--project` reads the project's `uv_targets` decision. The command exits 1 when a target fails.
- **Docs.** A [UV report guide](../../guides/UV_REPORT.md).

## Executed checks

| Check | Result |
|---|---|
| Source suite | 416 tests: 414 passed, two Windows symlink-permission skips. 8 tests are new: target validation, classification of every code, unmeasurable values, an empty selection, the project decision and the CLI |
| Installed-wheel suite | 416 tests from a standalone install of the wheel: 410 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 53 runtime and template files byte-identical to the sources. SHA-256 `3933c3123358c650605d3188057856aa460e4d9e272db72ad23b18c00e886c65` |
| Native, source and installed | `scripts/qualify_uv_report.py` |
| Regression | The modifiers, relocation, coverage, delivery, checks, owner, review page, guidance, render, relations, revisions and instances qualifications passed on the 0.18.0 wheel |

The native script built 2 m × 2 m planes with exactly known UVs, all using a 1024-pixel image. The targets were `min_density` 256, `max_overlap` 0.02 and `max_outside` 0.

| Plane | UVs | Result |
|---|---|---|
| `ext.good` | The unit square | `OK`: 512.0 px/m, overlap 0, outside 0 |
| `ext.small` | Scaled to 0.1 | `DENSITY_LOW`: 51.2 px/m |
| `ext.stacked` | 4 × 4 grid with every face on the whole square | `OVERLAP`: 1.0 |
| `ext.outside` | Shifted +1 in U | `OUTSIDE`: 1.0 |
| `ext.bare` | No UV layer | `NO_UV` |
| `ext.fine` | 64 × 64 grid unwrapped to the square | `OK`: overlap 0.0, through the vectorized small-triangle path |
| `ext.folded` | The same grid with both halves folded onto the top half | `OVERLAP`: 1.0 |

On the production garden's checkpoint 9, all 1,285 meshes were measured in 197 s. 1,179 had an overlap estimate, and 106 have no UV layer.

**Found during qualification.** The first production run failed in the vectorized path for small UV triangles: a broadcasting error in the edge test. The probe planes had only large UV triangles, so they never reached that path. The fix extracts each coordinate explicitly, and the probe gained `ext.fine` and `ext.folded` to exercise it.

Local evidence is under `runs/uv-0.18.0-2026-10-11/`, excluded from Git.

## Limits

- **Overlap.** It is a grid estimate of self-overlap within a mesh; overlap across objects sharing a texture is not measured.
- **Density.** It is an average per mesh; local stretching is not reported.
- **Cost.** A full report on a large scene takes minutes, not seconds.
- **Learned checks.** The report is not yet a learned-check rule kind.
