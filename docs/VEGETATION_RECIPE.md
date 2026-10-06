# Seeded broadleaf study

Version 0.4.3 adds a small DCC-neutral recipe and a Blender consumer. This is a generic seven-cane garden shrub study, not a species model, tree generator or simulation asset. Its intended use is a repeatable native starting point for an environment continuation.

```python
from dcc_harness.vegetation import leaf_surface, shrub_structure
leaf = leaf_surface(length=.06, width=.025, segments=6)
plant = shrub_structure(seed=41, height=1.2, leaf_scale=1.4)
```

Dimensions are meters. `height` is woody leader height (supported range 0.6–2 m), not the final foliage bounding box. The local origin is the root. `leaf_scale` (0.5–1.5) changes blade area without moving attachment points or adding geometry. The unscaled recipe produces approximately 3.8–7.5 cm blades, with width proportional to length; object scaling changes these physical dimensions too.

`leaf_surface` returns vertices, triangle faces and per-vertex 0–1 UV coordinates. Length follows local +Y. The base stays at the origin; arch and droop are fractions of length. The open leaf surface is intentional. A six-segment blade has 17 vertices and 20 triangles. The structure returns parent indices, attachment fractions, endpoints and radii for stems/petioles, plus each blade's base, direction, shape and material variation index. Local seeded randomness leaves the caller's global random state alone.

In an owned Blender process:

```python
from dcc_harness.vegetation_blender import leaf_materials, build_shrub
foliage = leaf_materials('my_project.broadleaf')  # four new stable material IDs
wood, leaves, receipt = build_shrub(
    owned_collection, 'ext.garden.shrub.00', existing_bark_material, foliage,
    seed=41, height=1.2, leaf_scale=1.4,
)
```

The caller supplies the existing collection and actual bark material, then places both returned objects with the same transform. New material/object identity collisions are refused. Reuse the returned material list and deliberately linked mesh datablocks for instances; do not call `leaf_materials` again with an existing prefix. The consumer creates two meshes per definition and returns a receipt. It does not clear the scene, place roots, save, journal, reserve an edit or confer acceptance. Use `begin-edit`/`finish-edit` as documented in [the everyday workflow](EVERYDAY_WORKFLOW.md).

The study's default asset-definition ID derives from the seed. Keep each seed paired with one height/leaf-scale definition in a project, as in the example. If experimenting with multiple parameter sets for the same seed, assign distinct `dcc_asset_id` values explicitly in the reserved authoring script before observation; the consumer does not manage a project-wide definition registry.

The demonstrated garden uses four seed/height definitions and 29 placements. Each has 2,100 attached blades; all four use the same leaf material family. Root XY anchors come from retained shrub trunks. A native ray against both ground surfaces establishes the highest support height; the root origin is embedded 2 mm. This is a local support check, not general collision clearance.

`scripts/inspect_vegetation.py` is the scene-specific saved-garden qualification, not a generic `assert_vegetation` API. It reads actual saved stem-ring and blade-base coordinates, checks UV bounds and nonzero leaf faces, verifies definition sharing and root support, and probes duplicate-ID rejection without modifying the source. Ring centroids are accumulated in double precision: summing Blender vectors in float32 caused a retained false failure at 0.36 micrometers. The 0.3-micrometer local connection tolerance stayed unchanged after correcting the measurement. A separate displaced-leaf fixture tests whether the checker detects a real broken connection.

Limits: stem tubes intersect and are not welded; leaves are single-sided surfaces. There is no species validation, self-collision analysis, wind animation, LOD generation or topology/export qualification. Leaf shaders are procedural, without scanned veins/damage. Dense geometry has a cost even when shared; inspect native triangle counts and all intended camera distances. See [the production review](VEGETATION_0_4_3_RESULTS.md) for the observed outcome and rejected alternatives.
