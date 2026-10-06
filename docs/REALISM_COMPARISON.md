# Realistic environment comparison — October 5, 2026

The user selected **a more realistic, more detailed environment** after the courtyard evaluation. The previous stylized checkpoint and evidence remain intact. This round tests that direction on a new scene: a working brick potting shed after rain, presented at human height with a material/construction close-up.

**Current status:** the first author was interrupted by the account usage limit before its final handoff. Its last saved checkpoint passes independent diagnostic evaluation and renders in all three views. Zero trial builds and zero fresh revisions are accepted as complete. See [progress and image review](REALISM_PROGRESS.md); the protocol below describes the intended comparison, not a completed experiment.

Four runs form two randomized blocks, each with one plain workflow and one workflow receiving the same brief plus the three process skills and qualified 0.3.1 observation/check/journal package. Every build and its late revision use different fresh agent contexts. The authoring order is recorded privately. Images are anonymized for separate review. Shared host tools and filesystem mean procedural isolation, not a sandbox or double-blind experiment.

The brief is unseen by prior creative workers and uses no previous generated geometry, but remains in the garden-environment domain. This tests generalization within that domain, not to unrelated DCC tasks. The new scanned kit and camera style differ from the courtyard, so a better image than the old courtyard would not by itself establish a harness benefit. The valid comparison is between these four equally supplied runs.

## Fixed inputs and stages

- Geometry-free Blender 5.1.1 starter; three fixed perspective cameras, one sun and packed HDRI; 1280×720 Cycles, 48 samples, seed 0, AgX.
- Common Poly Haven kit: red brick, weathered brown planks, forest ground, fern variants and partly cloudy daylight, all pinned by provider MD5/size plus local SHA-256. [Asset license](https://polyhaven.com/license) and [API terms](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md) were checked. The native import confirms four fern meshes and resolving image dependencies.
- Two private photographic references illustrate masonry/window relationships and vegetation/construction detail. They are credited to National Trust Images/Hugh Mothersole and National Trust/Marianne Majerus through the [original article](https://www.nationaltrust.org.uk/discover/history/gardens-landscapes/history-of-glasshouses-orangeries-and-garden-sheds). They are not measurement data, textures or media for redistribution in the artist package. The authored shed is not a reconstruction of those whole buildings.
- Build: 45 minutes, at most eight previews, two repairs per failed requirement. Model the architecture, bench and useful prop groups; use the common fern library. Pack native dependencies.
- Fresh-context revision: 20 minutes, four previews. Extend the bench from 1.80 to 2.10 m, preserve its center/depth/height and texture scale; change the real shared metal roughness from 0.38 to 0.58; preserve all other objects and material graphs. Prior builder scripts/transcript are excluded.

The live Blender MCP probe still fails at localhost:9876. Each agent therefore receives one owned background process/file and no live editor access. This evaluates authoring method and saved-file continuation; it does not qualify MCP transport or unattended scheduling. Native writers run sequentially; separate read-only evaluators can inspect immutable outputs. There is no paid generation or new account/API credential requirement.

## Evaluation and qualification

The independent evaluator is frozen before dispatch and applies to both methods. It reopens each saved file, checks declared geometry/identity/material requirements, camera/light/settings preservation, packed images, real material-face assignment, reachable PBR color images and data-map color spaces. Packed paths are redirected to absent locations in the disposable renderer. The source native file must remain byte-identical. It emits a report even for rejected candidates; process completion and passing assessment are separate.

Native qualification uses disposable fixture geometry excluded from every author packet. All eight cases passed their expected outcomes: one valid control accepted; missing deliverables, wrong bench dimensions, camera drift, wrong roughness, an unused metal decoy, incorrect data-map color space and an unpacked image rejected. The report is `runs/realism-heldout-2026-10-05/evaluator-fixtures/qualification.json`. These are evaluator tests, not eight successful creative scenes.

Artistic evaluation separately assesses real scale and construction, physical material scale/response, vegetation/contact, purposeful composition/activity, and consistency across views. It uses a five-point scale with 4 meaning usable with minor cleanup **for this realistic brief**. Imported asset quality must not be credited as newly modeled work. Technical acceptance does not prove general UV/topology quality, exact collision or artist editability. Critic scores are advisory, not artist acceptance.

Retain failed and capped runs. No selective coaching, hidden retry, changed budget or post-hoc tolerance adjustment is allowed to improve one condition. If a validator defect is reproduced on an unchanged control, retain the old evidence, version the correction and re-evaluate every affected condition uniformly.

Run root: `runs/realism-heldout-2026-10-05/`. Creative inputs are in `experiments/realism-heldout/`; assignments and the predeclared late revision remain in the run's private folder until image review. Token/billing totals are unavailable unless the host exposes them; elapsed time is not token cost. Two repeats can inform a product decision, not establish statistical superiority. Broader runtime, host installer and Unreal work remain deferred until the quality/continuation evidence warrants them.
