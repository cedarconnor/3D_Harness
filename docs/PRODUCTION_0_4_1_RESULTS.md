# Version 0.4.1 — guided production evidence

October 5, 2026. The interrupted realistic potting shed was adopted into a separate production project. This exercise developed a surrounding garden and used the everyday workflow across five accepted revisions. It is same-agent production work with separate native evaluator processes, not a completion of the interrupted blind comparison or proof of an advantage over plain MCP.

## Implemented change

`finish-edit --reject-reason` closes a reviewed attempt without publishing it even when native checks pass. The outcome distinguishes `native_check_passed` from publication; the accepted parent and decisions remain unchanged, and the rejection appears on resume. The caller can then reserve a repair from that accepted parent. It returns exit code 1 for nonpublication, which is a selection outcome rather than permission to replay.

This was needed when the first planting candidate passed preservation but looked too sparse. That attempt records `REJECTED_VISUAL`; a denser repair was independently reopened, rendered, inspected and published. Candidate files remain at their original paths; rejected native files are not automatically copied into accepted history.

Five skills were updated: entry/review skills explain visual rejection; architecture covers timber grain orientation; environment assembly covers representative crown review and diagonal slab overlap. These are narrow lessons from this run. No new general-purpose topology, navigation or automatic aesthetic evaluator is claimed.

## Executed checks

| Check | Result |
|---|---|
| Source test suite | 140 run, 138 passed, two host symlink-permission skips |
| Installed-wheel suite outside the checkout | Same result; CLI reports 0.4.1 and exposes `--reject-reason` |
| Package integrity | All 19 Python modules identical to source; wheel SHA-256 `2c657dc00fd0a36a320cc2981a0144aa35e7075456b2388e34c257f47af0e643` |
| Skill structure | Nine skills validated; five relative Markdown links resolved |
| Production outcomes | Five published revisions; one native-passing visual rejection retained |
| Cumulative native verification | Blender 5.1.1 reopened the final file using the installed 0.4.1 runtime; contract and extra native requirements passed |
| Original objects | All 934 preserved under the existing observed-field policy; geometry, authored UV hashes, placements and bindings remain exact |
| Evaluated UV detail | 827 original records exactly equal; 107 differ only in evaluated UV buffers/hash, maximum absolute delta 5.96e-8, within the existing qualified noise policy |
| Final scene | 1,461 objects, 572,185 evaluated triangles, 45 materials, 14 packed used file images |
| Timber repair | UV-only correction of 135 new vertical timber members |
| Path repair | Six adjacent-slab and one retained-edging AABB intersections reduced to zero; 35 native terrain samples across seven slabs |
| Visual inspection | All stages inspected at fixed hero/context/detail cameras; final garden and gate views also inspected |

The author stages used a pinned 0.4.0 observer/check runtime. The coordinator changed to 0.4.1 for the visual-rejection feature. Final cumulative native verification used the installed 0.4.1 package. No live artist editor was changed. The original source native remains SHA-256 `8aae1bb85afa5656bd3df3bb7a42d986109c08092779177087bd6e3d7fc9490c`.

Final native SHA-256: `203571d9d52a82b19352ebf330c8f976cfe1a49e068727e8030d5e64f86be883`.

## Errors retained and corrected

The final reporting script first expected six baseline path conflicts but its query also included retained edging, correctly measuring a seventh. Bounds showed 55 mm of overlap at the old first slab; the repaired route has a 195 mm X separation from that edging. The zero-final-conflict requirement was unchanged.

A second reporting assertion incorrectly demanded exact equality of evaluated UV buffers, bypassing the existing bevel-float-noise policy. All 107 differences were limited to evaluated UV fields and satisfied that policy. The report now distinguishes authored equality from evaluated numerical variability. Both failed script versions and diagnostic reports remain in the run. No native candidate, core observer, tolerance or frozen contract was changed to force a pass.

## Quality assessment

The added boundary and planting give the shed more context, and the glass reads with more depth. The final working checkpoint still needs art refinement: angular procedural leaves are unsuitable for close hero views; broad ground areas look repetitive; aging and the after-rain story are uneven. An elevated camera reveals regular dark bands on the inherited roof. The three original review cameras and lighting were retained, including the context camera's roof crop.

The wider view is useful diagnostic evidence, not a photorealism claim. AABB separation and five ground samples per slab do not prove general collision-free navigation. No artist acceptance, independent-agent skill benefit or repair-time savings was measured.

## Artifacts and next work

- [Native scene, renders and evidence ZIP](../runs/shed-production-2026-10-05/potting-shed-garden-handoff.zip).
- [Handoff notes](../runs/shed-production-2026-10-05/handoff/README.md) and [static before/after gallery](../runs/shed-production-2026-10-05/handoff/index.html).
- Full local project: `runs/shed-production-2026-10-05/project`; use the [everyday workflow](EVERYDAY_WORKFLOW.md) to resume before further edits.
- The run retains scripts, contracts, accepted/rejected outcomes, native observations, test logs, final reports and a final resume profile.

Next craft work should refine one representative vegetation asset and ground transition before more scatter, and separately inspect roof construction/shading from elevated views. Next engineering work should use the recorded resume profile to address large-observation/history latency without weakening preservation. Observations are about 87 MB at the final scene size. No performance optimization was applied in this version. Asset provenance from the existing kit is included; private photographic references are excluded.

The final profiled resume took **37.32 seconds** across six checkpoints, returned `READY_FOR_INSPECTION`, and reported zero pending/unresolved edits. JSON encoding accounted for 29.50 seconds of self time; native file hashing accounted for under one second cumulatively. Repeated canonical serialization in observation/mapping/registry validation is the measured first optimization target. This is one local profiled run, not a comparative benchmark; any optimization must retain digest/hash and malformed-evidence rejection behavior.
