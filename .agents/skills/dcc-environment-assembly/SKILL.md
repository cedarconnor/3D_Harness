---
name: dcc-environment-assembly
description: Assemble Blender terrain, architecture, vegetation and activity into connected environments with believable support, scale, boundaries and shared asset consistency.
---

# Make a coherent place

Define the site's circulation, ground levels, boundaries and transitions before placing small props. Review near, middle and far distances together. Extending a textured plane to the horizon rarely supplies convincing context; use terrain shape and deliberate boundary/planting layers appropriate to the reference.

For a bounded regular-grid surround, the [terrain extension helpers](../../../docs/TERRAIN_RECIPE.md) can preserve a declared inner square while expanding and shaping the outside without adding polygons. Preserve protected vertex positions and UVs against a source snapshot; check grid folds and between-vertex support. Set vertical probe origins above the resulting terrain bounds, since combined hills can exceed individual amplitudes. Check the background from both the main camera and a lower or side view before accepting it.

Keep asset definition IDs separate from placement IDs. Inspect shared mesh/material users before editing a definition. Repeated vegetation should vary according to species, growth and location, with reproducible seeds and restrained scale variation. Avoid rotating an entire imported plant arbitrarily when that breaks root contact or upright growth.

For procedural shrubs/trees, review one representative crown at the intended image scale before duplicating it. Random detached leaves can pass geometry budgets while reading as confetti; inspect branch-to-leaf attachment, coherent crown coverage and the gap between foliage and ground. Density is a visual variable, not a sufficient quality score.

Check crown and trunk framing from the retained whole-scene cameras before multiplying distant trees. Uniformly enlarging a template can move every canopy above the image and leave a row of bare poles. Projected leaf samples can cheaply expose this, but do not measure occlusion, transparent leaf coverage or visual quality. Inspect the actual render, and treat nonuniform scaling as a study adjustment that still needs believable growth and silhouette review.

The bounded [broadleaf study recipe](../../../docs/VEGETATION_RECIPE.md) supplies seeded stems/petioles, curved leaf surfaces and a Blender consumer. Test the small asset in isolation and in the destination view: a convincing leaf close-up can still leave the distant boundary looking bare. Blade area, internode spacing and branching affect coverage independently of leaf count. Keep parent attachments fixed when testing blade size, and preserve a rejected sparse version for comparison. This recipe is a generic garden study; it does not replace species references, scanned hero foliage or an export/LOD strategy.

Worked shed continuation: preserve the building and workbench, add a planted boundary beyond the work area, connect the path to a plausible destination, and establish ground height under pots, edging and vegetation. Build the boundary and terrain first; inspect all cameras before adding pebbles or leaves. Store the layout anchors, exclusion zones and ground/contact assumptions for the next context.

Use the existing reserved-volume preflight for broad potential overlap and supported visibility probes for occlusion. Neither proves exact contact, navigability or transparency. Confirm feet/pot bases/roots against local ground and inspect visible shadows; record measured support gaps when available. Diagnose a newly conflicting reservation instead of freezing both requirements and producing an impossible plan.

For repeated stepping stones, compare actual slab footprints with adjacent slabs and retained edging before multiplying placements. A diagonal center spacing can still leave square slabs intersecting. On uneven ground, sample the native surface at the center and corners; a procedural height function may differ from the final tessellated mesh. Such samples support a local placement claim, not general collision-free navigation.

For ground transitions, define the work area and access corridors before distributing grass or litter. The [ground helpers](../../../docs/GROUND_RECIPE.md) provide metric corridor masks and explicit evaluated-surface ray snapshots. Rebuild the snapshot after source geometry changes; missing support must not silently become height zero. An open mesh boundary can be missed by a ray exactly on its edge. When an overlay shares source grid points, retain their evaluated heights and check cell interiors as well as vertices for breakthrough. Keep this repair specific to the measured terrain; a higher blanket offset can conceal the cause and float the surface.

Place activity around a readable task: tools within reach, supplies connected to their use, and space left to work. Alternate dense and quiet areas. Detail should support focal hierarchy rather than fill every surface.

Review whole environment, human-height path and contact detail views; a successful hero image cannot certify unseen zones. Retain an unchanged checkpoint, use bounded layout alternatives when uncertain, and preserve cameras/material families during placement revisions. This skill's art direction remains subject to visual testing; [qualification](../../../docs/CRAFT_SKILLS.md) distinguishes implemented checks from unproven quality gains.
