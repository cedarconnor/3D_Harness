# Terrain/context study — version 0.4.7

The reusable terrain helpers and scoped native checks passed. The artistic study did **not** establish a sufficiently convincing environment improvement. Three candidates are retained for comparison; the accepted garden remains checkpoint 9, with its known distant-edge defect.

## Implemented and exercised

`dcc_harness.terrain.expand_axis` expands an existing regular grid outside a protected square with a monotonic mapping and smooth join. `surrounding_height` adds bounded Gaussian landforms with a protected core. [Usage](TERRAIN_RECIPE.md) explains coordinate frames, UV preservation, support sampling and limitations.

Source and isolated installed-wheel suites each ran 170 tests: 168 passed and two Windows symlink-permission cases were skipped. Twenty-six Python module hashes match source, pinned runtime and installed 0.4.7 wheel. Later 0.4.8 changes are qualified separately; the scene trials retain their 0.4.7 runtime.

The native study in Blender 5.1.1 preserves 4,489 core surface vertices and 17,956 metric-UV loops exactly, along with the full mask layer and grid topology. Each candidate has 6,241 between-vertex support samples with no missing hits or breakthrough, plus row/column ordering and projected triangle-area checks. All pre-existing objects except the declared outer surface fields, all materials, cameras and lighting settings remain protected under the continuity observation policy.

## Visual decisions

| Candidate | Native outcome | Actual image assessment |
|---|---|---|
| Terrain only | ±180 m extent; same triangle count; protected core/UV/support checks pass | A large bare hill wall replaces the distant edge. Rejected. |
| Distant woodland | Lower ±150 m terrain; 18 trees; 2,466,894 evaluated triangles | Enlarged trunks appear as a regular pole line; canopies leave the garden frame. Rejected. |
| Lower-canopy refinement | Same counts; narrower spacing and lower crowns; native checks pass | Background has more spatial layers, but compressed umbrella crowns and coarse leaves remain artificial. No confident overall realism gain; rejected for adoption. |

The last two candidates contain 1,325 objects and retain the same 54 material definitions and 20 packed used images. Eighteen placements share four wood and four leaf mesh definitions, adapted from the existing native trees without downloading assets. Tree LOD retains leaf outlines while removing folded centers. This meets the 2.5-million-triangle ceiling, but does not qualify botanical realism.

The refinement's 162 root-footprint samples lie between approximately 4 and 57 mm beneath local support, with no footprint floating and no tree AABB entering the protected core. Three disposable faults—moving a protected vertex, folding an outer grid cell and lifting a tree base—were detected. No negative probe saved over the candidate.

A projection diagnostic explains the failed initial placement: zero of 4,410 sampled leaf polygon centers fell inside the wide garden frame. Refinement puts 1,312 inside. This is **projected sample coverage**, not occlusion, rendered pixel coverage, transparent-leaf coverage or aesthetic quality. The four matched 1680 × 945, 64-sample renders supply the visual evidence.

## Process corrections and limits

The woodland comparison originally inherited the author's requirement that all 36 new tree objects exist, which would disqualify the unchanged control. Before evaluation/review, a retained correction removed those additions from the common comparison contract; the candidate's construction contract still required them. The correction is explicit and the original design remains saved. This comparison was not fully preregistered. The refinement's corrected design was frozen before its author ran.

The environment skill now explains canopy framing and scale pitfalls. The review skill separates common preservation requirements from candidate construction deliverables. Structure/reference validation passed; these edits are lessons from guided work, not an independent test of skill effectiveness.

The coordinator authored, critiqued and made the recommendation. Fresh Blender processes supplied native observation and rendering, but there was no blind reviewer or new artist acceptance. Geometry budgets and preservation checks do not imply a better image. Background Blender was used; this run does not establish live MCP qualification.

Local evidence: [comparison gallery](../runs/context-2026-10-05/index.html), [continuation handoff](../runs/context-2026-10-05/CONTINUE.md), and [verification](../runs/context-2026-10-05/VERIFICATION.json). Each candidate retains its author script, reservation, native file, observations, four views, negative controls and rejection outcome. Start another art pass from checkpoint 9, after choosing a planting reference and an appropriate tree definition, rather than building on a rejected study.
