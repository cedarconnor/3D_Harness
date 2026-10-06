# Broadleaf recipe and garden continuation — 0.4.3

The new recipe improves the obvious diamond-shaped site shrubs and gives future workers repeatable leaf, attachment and shared-definition controls. It remains a bounded generic study. The garden still needs ground transitions, roof diagnosis and better inherited tree/other shrub foliage.

## What changed

Added `dcc_harness.vegetation` (curved UV-mapped leaf surfaces and seeded branch/petiole structure) and `vegetation_blender` (new native mesh/material consumer). Added five pure tests, a saved-garden inspector and [recipe documentation](VEGETATION_RECIPE.md). The environment-assembly skill now explains the observed difference between convincing close-up leaf shape and adequate crown coverage at scene distance.

The art continuation replaces exactly 232 site-shrub objects with 58 objects: 29 placements sharing four seed/height definitions. Each plant has 2,100 attached leaves. The original 934 objects, all other site objects, 45 existing material graphs, cameras, illumination and world remain protected. Four new leaf materials use a common procedural response. The final native contains 1,287 objects, 2,255,113 evaluated triangles, 49 materials and 14 packed used images.

Final native SHA-256: `17bdb75e2bdae5c2612cbee061b1c6dc351cfcd0d06c86d808b809e89764e5aa`.

## What the reviews caught

The first isolated shrub had more credible small leaf shapes but exposed blunt canes and a sparse crown. A second study added tapered segmented leaders and more branching. In the actual garden, this still looked too open for the planted boundary. That native-passing candidate is retained as `REJECTED_VISUAL`; it did not advance the accepted project.

The selected repair increases blade dimensions by 1.4 while retaining the same branch endpoints, attachment points and polygon count. In the inspected gate view, rounded curved leaves replace the large flat diamonds and the boundary has better coverage. The main shed views change little, as intended. This is a same-agent judgment from five native renders, not artist acceptance or a blind comparison result.

The result costs substantially more evaluated geometry than the prior garden: 572,185 to 2,255,113 triangles (within the declared 2.5M limit). Shared definitions reduce unique meshes and authoring duplication; they do not eliminate per-instance evaluation or observation cost. A general production vegetation system still needs a representation/LOD strategy. The saved observation grew from roughly 87 MB to 205 MB; the earlier six-checkpoint resume timing is not a performance claim for this heavier checkpoint.

## Validation

| Check | Result |
|---|---|
| Source and installed wheel suites | Each ran 149 tests: 147 passed, two Windows symlink skips |
| Package consistency | 21 source, pinned-runtime and installed Python modules have identical hashes |
| Fresh saved-file continuity evaluation | Passed, with three fixed camera renders and packed-image paths invalidated in the disposable renderer |
| Retained object records | 1,124 exact, 105 differing only in evaluated UV noise accepted by the existing unchanged guard; 1,229 retained in total |
| Native branch/petiole/leaf connections | Four definitions; maximum measured local error 0.0000001184 m, below unchanged 0.0000003 m tolerance |
| Ground support | 29 retained root XY anchors; origins embedded 2 mm below highest native ground/terrain sample |
| Definition sharing | Four wood/leaf mesh pairs reused across 29 placements |
| Real fault control | A separately saved 10 mm displaced leaf base was rejected |
| Duplicate identity guards | Refused without adding object, mesh or material datablocks |
| Skill metadata | Environment-assembly skill validator passed |

Two test infrastructure failures were diagnosed and retained. The initial native checker summed float32 Blender vectors to estimate ring centroids, introducing up to 0.36 micrometers of checker error. Double-precision accumulation removed that error without changing the mesh or tolerance. The first installed-suite launcher configured only its own `sys.path`; child interpreters could not find the isolated package. Passing the same installed path through `PYTHONPATH` corrected the runner. The final suites above include the fresh-process tests.

## Art and qualification limits

The new shrubs still use simplified straight shoots and procedural surfaces. No species accuracy, welded/manifold plant topology, wind behavior, UV texel-density target, export or LOD qualification is claimed. Root samples do not certify arbitrary collision clearance. Inherited coarse foliage is visible elsewhere. The broad bare ground, regular elevated roof bands and weak after-rain story remain the next visible issues.

No live artist-editor writes, external asset downloads, paid generation or changes to frozen comparison inputs occurred. There is still no evidence here that these skills beat plain MCP across fresh agents or reduce artist repair time. This cycle validates reusable controls and a scoped continuation with retained rejection evidence.

## Artifacts

- [Portable artist handoff ZIP](../runs/vegetation-2026-10-05/potting-garden-broadleaf-handoff-final.zip) with the saved scene, ten matched before/after images and checked evidence.
- [Local before/after gallery](../runs/vegetation-2026-10-05/handoff-final/index.html). Image files were inspected and local links verified; browser rendering was not tested.

- [Verification summary](../runs/vegetation-2026-10-05/VERIFICATION.json).
- [Selected saved native](../runs/vegetation-2026-10-05/garden-02/candidate.blend).
- [Matched gate view](../runs/vegetation-2026-10-05/presentation-02/gate.png) and [garden view](../runs/vegetation-2026-10-05/presentation-02/garden.png).
- [Reusable recipe](VEGETATION_RECIPE.md) and [fresh native inspector](../scripts/inspect_vegetation.py).
- [Final wheel](../dist/dcc_harness-0.4.3-py3-none-any.whl), SHA-256 `fb09aee606496581a17083e9828f0dd01c2c696e1514f8ca42b0790fa2a8cbec`.

Full local evidence is under `runs/vegetation-2026-10-05/`, including both studies, both garden candidates, source/installed logs, old and corrected inspector output, the negative-control native, pinned runtimes, and publication/continuation records.

Publication produced checkpoint 000007. A fresh installed-runtime resume verified the seven-checkpoint chain in 23.14 seconds and reported no pending operations or unresolved edits. This is one timing of a larger project, not a matched speed benchmark.
