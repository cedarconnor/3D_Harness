# Reference-led quality loop

This increment compares saved native candidates above the existing MCP. It adds no server, model provider, scheduler or autonomous writer. Use `dcc-review-continue` from the normal agent client. The CLI works from the checkout or installed `dcc-harness` package.

## Working sequence

1. Save `design.json` **before authoring**: brief, attributed references, visual targets, relevant construction/material methods, fixed review views, the existing continuity contract, and any reserved volumes. References are classified as mood, construction or dimension evidence. Keep these distinct.
2. Run the reserved-space preflight against the current native observation. A potential overlap is a scope conflict to diagnose. Editable objects are still reported; permission is not a waiver. Check affected shared mesh/material users before changing definitions. This version does not automate that dependency preflight.
3. Retain `unchanged`, then build one to three bounded alternatives in separate owned files. Journal dispatches. Keep failed candidates and their evidence. Do not regenerate until something passes without recording the failed attempts.
4. Reopen each saved native file in a fresh DCC process, observe it, then render a whole-scene view and task detail. Render workers never save over source files. Camera definitions can specify a fixed asset-relative view, but identify it as such; do not silently substitute a beauty camera for a regression view.
5. Assemble `round.json`, binding the original design, native files, observations, render receipts and images by SHA-256. Audit, inspect the actual images, record a narrow critique and a verification assessment for every target/candidate, then select. Retain reasons for rejecting alternatives, including unchanged.
6. Publish a selected checkpoint through `Continuity.publish` only with its recomputed native check and a new handoff. Selection itself does not write a native file, publish to a store, or grant artist acceptance. A new scope starts a new contract; frozen earlier experiments remain unchanged.

```powershell
python -m dcc_harness.quality preflight observation.json reservations.json --out preflight.json
python -m dcc_harness.quality audit round.json --out audit.json
python -m dcc_harness.quality select round.json review.json --out selection.json
```

Outputs use exclusive creation. Choose a new evidence filename for a new audit. A false preflight/audit returns exit code 1 and retains its report. Malformed, changed or missing evidence raises an error. Selection can retain failed alternatives but cannot select one. The first candidate must be `unchanged`; it is a legitimate winner when edits do not improve the result.

Keep the round's common preservation contract separate from a candidate's construction contract. For example, a worker adding 18 trees must prove those trees exist, but requiring them in the shared comparison contract would disqualify the unchanged control before visual review. Freeze both scopes before authoring. If this mistake is discovered later, retain the original design and a dated correction explaining its effect; do not claim the corrected comparison was fully preregistered.

## Document shape

`design.json` contains `brief`, `targets`, `methods`, `references`, `views`, `contract`, and `reservations`. `round.json` repeats those fields exactly and adds `schema: dcc.quality.round.v1`, `design: {path, sha256}`, and `candidates`. Each candidate has `id`, `checkpoint`, `observation` and `renders`; the last three are `{path, sha256}` references. All referenced paths stay within the round directory. Links and reparse points are rejected. Store the entire directory when relocating a review.

A target has `id`, `intent`, `reference_ids`. A reference has `id`, `file: {path, sha256}`, `role: mood|construction|dimension`, and `intent`. `methods` maps domain names to short recipe/version/variation notes. A view has `id`, `purpose: whole|detail`, `camera` and `render` dictionaries. Native renderers interpret these dictionaries; this portable layer compares their digest and requires both view purposes.

A render receipt has `schema: dcc.quality.renders.v1`, `checkpoint_sha256`, `views_digest`, and `images: {view_id: {path, sha256}}`. The supplied native observer must match the saved checkpoint hash, declare its coverage, have no issues, and report `native_dirty: false`. Check reports are recomputed using the existing continuity validator, not accepted from a supplied `passed` flag.

Reservations are explicit world-coordinate AABBs: `{id, bounds: [[minX,minY,minZ],[maxX,maxY,maxZ]], obstacle_prefixes, exempt_ids, tolerance}`. Use literal nonempty prefixes and existing explicit exemptions. Every prefix must match a mesh. An overlap exceeding tolerance on all three axes produces a finding; touching is allowed. Coordinates use the observed scene's world units. The example uses meters. AABBs are conservative broad-phase checks, not exact solid intersections, line-of-sight, foot contact, or navigable paths. Occlusion requires native rays or image review.

`review.json` has `schema: dcc.quality.review.v1`, the audit's `evidence_id`, `critic`, `verifier`, `selected` and `reasons`. Critic: `{author, findings: [{candidate,target,view,problem,remedy}]}`. Verifier: `{author, assessments: {candidate: {target: {result,view,evidence}}}, unresolved_blockers: []}`. Results are `improved|unchanged|worse|uncertain`. Reasons cover every candidate. A changed file, design, view definition or validator invalidates the review binding.

The roles can be supplied by different agents where delegation is authorized, or by a disclosed single reviewer. Author strings do not authenticate independent processes. The tool reports `same_author` or `different_authors_declared_not_authenticated`; it never labels a self-review independent. An assessment is a recorded visual judgment, not a computed quality score. The supplied observations and render receipts remain trusted producer claims: hashes establish consistency, not truth. There is no dispatch lock or atomic native transaction, and concurrent mutation is unsupported.

Version 0.4.8 includes the observation storage decoder in the validator fingerprint. A decoder change now invalidates a cached review ID even when all retained input files are unchanged. Keep historical reviews with their pinned runtime; intentionally upgrading requires a newly named audit and review.

## Native visibility in version 0.3.0

Use `dcc.quality.round.v2` when visibility is a required gate. It adds `visibility_contract` to the frozen design and a `visibility: {path, sha256}` receipt to **every** candidate, including unchanged. Version 1 remains supported for rounds without this gate. Current validator changes invalidate cached review IDs; retain old reports and use their pinned runtime, or generate a newly named audit and review.

```json
{
  "schema": "dcc.visibility.contract.v1",
  "requirements": {
    "hero-readable": {
      "query": {"camera_id": "camera.garden", "target_ids": ["ext.hero.body"], "grid": 64},
      "minimum_visible_fraction": 0.55,
      "minimum_target_samples": 500
    }
  }
}
```

In fresh background Blender, open the immutable checkpoint, call `continuity_blender.observe()`, then `visibility_blender.observe_visibility(queries, observation)` before changing render settings or creating temporary cameras. `spatial.check_visibility` binds results to the observed revision/checkpoint and frozen query, verifies count consistency, then computes admission. Missing coverage, dirty/stale evidence and mismatched queries do not pass.

The native metric samples a uniform grid over the target's projected bounding region. A target-only BVH establishes sampled silhouette coverage; the full-scene first hit identifies visible samples and blocking object IDs. It supports perspective and orthographic cameras, including shifts. It is an **opaque geometric occlusion metric**, not exact rendered pixels, alpha/transmission, perceptual recognition, depth of field or motion blur. A mostly off-screen target can still be unobstructed within its clipped ROI; composition remains a separate visual decision.

Current native support is deliberately narrow: mesh geometry with matching render/viewport visibility and Bevel, Weighted Normal, Solidify, Array, Mirror or Triangulate modifiers. Other enabled modifiers, render-visible viewport-hidden meshes, divergent modifier visibility, scaled cameras, instances and non-mesh occluders are rejected. This matters because Blender's ordinary dependency graph is evaluated for the viewport even in a background process. A reproduced render-only Array modifier otherwise reported 50% visible where a render-matching geometry snapshot reported 0%.

The continuity contract also accepts `allowed_deleted_ids`: distinct **exact** IDs that existed before the stage and are absent from its required targets. It grants deletion only; it does not permit arbitrary transforms or mesh edits to those objects. A prefix is not deletion permission. Keep the list narrow and save the new contract before authoring.

Version **0.3.1** qualifies a second native numeric issue from fresh continuation: tiled evaluated UV coordinates around 5–10 differed by one float32 step when reopening the same file. The old `2e-7` absolute guard rejected these values. Comparator policy v3 retains that legacy allowance and additionally admits exactly adjacent native float32 values, with a `1e-6` absolute cap. Authored mesh/UV hashes, evaluated geometry, UV layout and writable modifier settings must still match exactly. Nonadjacent larger drift, arbitrary double values and authored edits do not receive the waiver. A native authored UV edit of `2.9802322387695312e-8` was rejected. This is a bounded numerical correction, not general UV-edit permission.

The observation's legacy `independent_uv_guard` producer marker is retained for v2 data compatibility; observation does not apply a tolerance or modify extracted values. The check report's `evaluated_uv_noise.policy_version` and parameters identify the actual comparator policy. Validator hashes invalidate old review IDs after an upgrade. Keep pinned old runtimes and reports; audit/critique again under a new filename when intentionally upgrading.

`scripts/qualify_visibility.py` runs positive and negative native fixtures in an empty disposable process. `scripts/probe_visibility.py` measures a saved file without modifying it. `scripts/evaluate_quality_candidate.py` independently observes and renders a prepared candidate. `scripts/run_quality_stage.py` freezes helper/script copies and journals a bounded authored fixture; it is not an agent scheduler. The fresh-worker study also retains input seals, a separate writer journal and independent output checks. Filesystem isolation and execution permissions remain procedural.

## Failure handling

Keep the failed checkpoint/report and classify the cause in the handoff:

- **Unmet requirement:** revise within the existing scope and bounded repair allowance.
- **Uncertain native outcome:** inspect the journal and actual file; do not replay a write.
- **Invalid evidence:** regenerate missing/stale observation or render evidence from the named immutable source.
- **Validator defect:** retain the failure, reproduce with positive and negative native fixtures, version the validator, then audit again. Do not quietly widen tolerances or replace the baseline.

## Reproducible native exercise

The repository has a bounded courtyard fixture, not a general scene generator:

```powershell
python scripts/run_quality_fixture.py runs/NEW-QUALITY-RUN --blender 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
```

It needs the retained local continuity round, creates an owned copy, freezes design references, runs preflight, journals native operations, authors two layouts, reopens all three checkpoints in separate Blender processes, renders nine images, and audits. The source remains unchanged. The separate historical tray regression checks a real failure plus an unsaved native positive control. A process failure leaves its pending operation and log for inspection, with no automatic retry. The script stops before subjective selection.

The fixture uses prior scene captures as palette/construction references, not external professional reference images. It exercises the process but does not qualify external-reference reconstruction, taste improvement across projects, independent agent review, or unattended execution.
