# Ground transitions and reusable support helpers — 0.4.4

The garden now has a clearer soil working area, two retained access routes, a grass surround and leaf litter near shrubs. The ground-related skills gained reusable metric corridor masks, evaluated native support sampling and a specific lesson from a failed overlay. This is a guided same-agent continuation, not evidence that the harness outperforms plain MCP.

## Implementation and scene scope

`dcc_harness.ground` supplies finite polyline distances and smooth corridor masks. `ground_blender.SurfaceSampler` builds an explicit world-space snapshot of evaluated mesh surfaces, including modifiers and transforms. It returns a highest downward-ray hit or `None` and requires rebuilding after a source edit. These helpers do not execute tools, save files, schedule agents or guarantee navigation. See [usage and limits](GROUND_RECIPE.md).

The scene adds one ground overlay and one merged grass object with 16,799 blades. All 1,287 prior objects and all 49 prior material records are preserved under the existing observation policy. There are no allowed deletions or prior-object changes. The new material is a copy of the original soil graph with additional scanned surfaces and masks; the original two ground users are unchanged. Cameras, illumination and world remain protected.

Added geometry is 100,325 evaluated triangles, bringing the total to 2,355,438 across 1,289 objects, 54 materials and 20 packed used images. This leaves 144,562 triangles below the current 2.5M ceiling. Geometry and saved-observation cost remain important constraints; this result does not justify indiscriminate density increases.

Two new surface sources are [Grass Ground](https://polyhaven.com/a/grass_ground) and [Leafy Grass](https://polyhaven.com/a/leafy_grass), by Charlotte Baglioni, under [Poly Haven's CC0 license](https://polyhaven.com/license). Their recorded physical widths are 2.51 m and 2 m. Source channels, URLs, sizes and hashes are retained; the API's millimeter dimensions are converted to meters. Diffuse uses sRGB, roughness and OpenGL normals use Non-Color. The saved file contains all six new source maps.

## Failure retained and corrected

The first candidate passed its initial vertex/root checks but showed a brown line behind the shed. A denser probe found 2,032 of 67,600 interior samples below the original terrain, with a worst deficit of 0.216569 m. A ray exactly on the open y=16 terrain boundary missed that mesh and hit the lower base plane. An inward offset of 0.0001 m hit the terrain roughly 25 cm higher. Interior samples away from the boundary stayed above the source.

The rejected candidate is retained as `REJECTED_VISUAL` with the parent unchanged. The repair uses evaluated source vertices at shared grid knots as well as scoped rays. It does not raise the entire surface or relax the tolerance. The stronger inspector now checks cell interiors, rejects the first candidate and accepts the repaired one. This is a bounded aligned-grid construction; it is not a general overlay/remeshing solution for arbitrary terrain.

The corrected saved native SHA-256 is `4195e03951f30b5e44092c0fca3e5f84eb119edf9ec1a811b2ede33cfbdc98a4`.

## Validation

| Check | Result |
|---|---|
| Source and isolated installed-wheel suites | Each ran 153 tests: 151 passed, two Windows symlink skips |
| Runtime consistency | 23 source, pinned and installed Python modules have identical hashes |
| Native sampler fixture, source and installed | Transformed slope, nonuniform scale, evaluated Solidify, highest overlapping surface, explicit misses, stale snapshot/rebuild and invalid inputs passed |
| Fresh saved-file preservation | Passed; 1,182 prior object records exact, 105 differ only in evaluated UV noise accepted by the existing unchanged guard |
| Existing material records | All 49 unchanged |
| Cover support vertices | 25,281 checked against scoped rays plus source knots; maximum error about 8.82e-9 m |
| Between-vertex clearance | 67,600 samples; minimum 0.00299835 m against nominal 3 mm offset |
| Grass roots | 33,598 base vertices checked; maximum offset error about 1.35e-8 m |
| Access cores | No new grass vertices inside either route or the work-area clear core |
| Mask and metric UVs | 199,712 mask components checked, along with metric UVs and actual shader/active-UV bindings |
| New scanned sources | Six packed-image hashes and color spaces, connected world-position scaling and recorded tile widths passed |
| Real negative control | A 10 mm blade-root displacement in a disposable process failed only the support check; no native save |
| Native renders | Three fixed cameras and two matched supplemental views; source unchanged, external packed-image paths invalidated during fixed-view rendering |
| Updated skills | Environment-assembly and materials frontmatter validators passed |

The inspector is a scene-specific qualification script. Its root and interior samples do not prove continuous contact, arbitrary collision clearance or navigability. The UV mask binding checks extend this particular qualification; the general observer still does not cover every arbitrary node property. Blender 5.1.1 was tested. The author emits a `Material.use_nodes` deprecation warning for Blender 6.0; that future version is not qualified here. Cycles emitted a HIP initialization warning while rendering through the available configured device; the renders completed.

## Visual judgment and next work

Five native views were inspected. The repaired terrain strip is absent; the soil/grass transition makes the working apron and planted areas easier to read. Shed and workbench views preserve their prior appearance. The far field still looks flat and repetitive and ends abruptly against the HDRI. Regular roof bands, coarse inherited trees/other shrubs and weak after-rain weathering remain. This is a more coherent procedural environment study, not photoreal production qualification.

The next useful repair is a separately scoped diagnosis of the elevated roof bands. A later background pass should address terrain shape and the distant boundary without simply adding more small geometry. No blind review, fresh-agent skill comparison, artist acceptance, repair-time savings or export/LOD qualification is established by this cycle.

## Local evidence

- [Verification summary](../runs/ground-2026-10-05/VERIFICATION.json), [selected visual review](../runs/ground-2026-10-05/ground-02/REVIEW.md) and [ground receipt](../runs/ground-2026-10-05/ground-02/ground-receipt.json).
- [Matched before/after gallery](../runs/ground-2026-10-05/handoff/index.html) and [portable artist handoff](../runs/ground-2026-10-05/potting-garden-ground-handoff.zip). Direct native images were inspected; HTML local references and ZIP member hashes are checked, without a browser-rendering claim.
- [Native sampler fixture](../scripts/qualify_ground_sampler.py), [saved-scene inspector](../scripts/inspect_ground.py), [pure helper tests](../tests/test_ground.py).
- [Built wheel](../dist/dcc_harness-0.4.4-py3-none-any.whl), SHA-256 `b0570dc0aa64360cb0e71ca5ede8eab2189aa95b37258f98a5613d0a34d7b4b4`.

The run retains both candidates, immutable reserved authors, source/installed test logs, pinned runtime hashes, diagnostic probes, the intentional fault report and matched captures. The artist's live Blender document was not edited. Full project history remains in the production continuity store.

Publication produced checkpoint 000008. A fresh isolated installed-runtime resume verified the eight-checkpoint chain in 28.00 seconds with no pending operations or unresolved edits. This is one timing of the larger project, not a matched performance benchmark. The final saved observation is approximately 214 MB; compact evidence representation remains a useful future engineering target.
