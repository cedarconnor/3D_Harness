---
name: dcc-review-continue
description: Review a 3D Harness Blender checkpoint, check revision preservation and prepare a file-based continuation or artist handoff with explicit evidence limits.
---

# Review and continue

Read the project's brief and pending operations before editing. For a continuity project use `python -m dcc_harness resume PROJECT`; use `review PROJECT` for the retained latest check. Legacy journal-only projects use `status PROJECT`. See `docs/EVERYDAY_WORKFLOW.md` for reserved edits and explicit reconciliation. If a write is unresolved, inspect its saved/native effects before permitting another write; never replay arbitrary code automatically.

Inspect actual images at the specified views, projection, exposure, lighting, frame and render settings. Compare against the visual brief, including negative space, silhouette, material hierarchy, texture scale and repetition. Diagnose concrete defects rather than requesting generic polish. Two materially different repairs per failed requirement is the pilot ceiling unless the project sets another budget.

For the everyday workflow, a native pass is only one acceptance input. Use `finish-edit --reject-reason "visible defect"` to close and retain a reviewed candidate without publishing it. Start a repair from the accepted parent under a new reservation; keep the rejected images and reason. This outcome is not a failed native check and does not grant artist acceptance to another candidate.

For revisions, run the before/after comparison against the allowed fields and recheck required targets. State the coverage limits with preservation claims. Save evidence that identifies its source checkpoint hash and camera settings. A render file existing is not a visual review.

For an external saved edit to an existing continuity project, read [external revision review](../../../docs/EXTERNAL_REVISIONS.md). `preview-revision` retains a frozen candidate and contract; inspect its actual content, shared users, handoff and decision updates. Accept only the intended preview hash, with a note attributing the review honestly. A passing contract does not require publication. Prepared previews do not block other work; resume before acceptance, and expect a stale-parent rejection if the project advanced. Never use this route to bypass an unresolved reserved edit.

Reopen the native checkpoint in a fresh Blender process and regenerate the observation before claiming persistence. Use `--python-exit-code 1`, examine the process exit status and read the report; success text alone is insufficient. A render worker reads an immutable checkpoint and writes images/reports only.

If unchanged inherited data fails comparison, reopen the unchanged source through the same evaluator before requesting an asset repair. Distinguish authored changes, evaluated numeric variability and validator defects. Retain the failed reports; any justified validator correction needs a versioned policy, negative tests and uniform re-evaluation of the baseline and candidates. Do not weaken a check solely to admit the preferred image.

Write `CONTINUE.md` with the project path, last verified checkpoint, pending operation IDs, current brief/spec, completed and failed checks, unresolved artistic decisions, remaining budget and the next action. New context should be able to continue from these files without the transcript.

Mark source inspection, live execution, independent evaluation and artist acceptance separately. Contact sheets help inspect sampled appearance; later animation tasks also require full-speed playback and endpoint checks. Do not claim comparative benefit from one guided engineering scene.

For a substantial layout/look decision, use the reference-led loop in `docs/QUALITY_LOOP_USAGE.md`. Save the design targets and methods before authoring. Compare a retained unchanged candidate with a bounded set of edits under common whole-scene and relevant detail views. Run `python -m dcc_harness.quality audit ROUND --out NEW_REPORT`, inspect actual images, and bind the critique/verification record to that audit's evidence ID before `select`. Selection records a recommendation; publish through the existing continuity store separately.

Separate candidate construction requirements from common comparison rules. An edit adding trees should prove the new trees exist, but the unchanged control should still qualify for comparison without them. Preserve shared assets and acceptance limits in the common contract; retain any later correction explicitly rather than silently replacing the frozen design.

Run reserved-space preflight before building near protected assets. Missing obstacle coverage and potential overlap require diagnosis; being allowed to edit an obstacle does not clear the conflict. AABB clearance is not visibility or exact collision. Keep regressions and rejected alternatives in the review. When the same agent critiques and verifies, attribute both roles honestly; do not claim independent review. If a native outcome is uncertain, evidence is stale, or a validator is defective, retain the failed evidence and classify the cause before continuing.

