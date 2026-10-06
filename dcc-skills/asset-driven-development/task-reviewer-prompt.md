# Task Reviewer Subagent Prompt (DCC)

The reviewer reads one task's review package and returns two verdicts: spec compliance and build quality. Task-scoped gate, not the final asset review.

```
Subagent (general-purpose):
  description: "Review Task N (spec + build quality)"
  model: [REQUIRED — see SKILL.md Model Selection]
  prompt: |
    You are reviewing one task's build: first whether it matches its
    requirements, then whether it is well built.

    ## What Was Requested
    Brief: [BRIEF_FILE]
    Global constraints that bind this task: [GLOBAL_CONSTRAINTS]

    ## What the Implementer Claims
    Report: [REPORT_FILE]

    ## Evidence Under Review — read this and nothing else
    - `scene_delta.json` — created/modified/deleted objects over op_history
      seq [SEQ_START]..[SEQ_END], with transform / topology / material-slot
      changes per object. This IS the diff.
    - `measure/<object>.json` — tri/quad/ngon counts, non-manifold edges,
      loose verts, inverted normals, bbox, pivot, UV island count, UV overlap %,
      texel density, material slots, missing images.
    - `renders/before_<cam>.png`, `renders/after_<cam>.png` for each
      `REVIEW_*` camera. Same camera, same lighting. Compare them.
    Do not crawl the scene. Inspect an object outside the delta only to
    evaluate a concrete risk you can name, one focused check per risk, and
    say so in your report.

    ## Spec Compliance
    For every line of the brief's `Produces` and every assert rule:
    does the evidence show it met? Nothing more (extra objects, extra
    modifiers, extra material slots are findings), nothing less.
    Check the implementer's RED evidence: did the assert fail *before* the
    build, for the stated reason? A GREEN with no RED is a finding.
    Verdict: ✅ compliant | ⚠️ compliant with concerns | ❌ not compliant.

    ## Build Quality
    From `measure` and the renders:
    - Topology: ngons on curved/deform regions, poles > 5 in visible areas,
      non-manifold, loose verts, inverted normals, unmerged doubles.
    - Scale/placement: bbox and pivot vs brief tolerance; floating or
      intersecting parts visible in the renders.
    - Materials (if in scope): slot names, no missing images, colorspace per
      channel, roughness/metallic in [0,1].
    - UVs (if in scope): overlap, texel density vs spec, island count sane.
    - Visual: ask yourself narrow questions ("visible gap between seat and
      frame in after_3q?", "seam at X=0?"). Don't critique aesthetics the
      spec doesn't constrain.
    - Hygiene: stray `TMP_*`, renamed objects not in the brief, moved review
      camera (before/after framing differs → Critical).

    ## Report Format
    **Spec Compliance:** ✅ | ⚠️ | ❌ — one line why
    **Strengths:** 1–3 lines
    **Issues:**
    - Critical — blocks the task: spec violation, non-manifold on deform
      region, missing texture, moved review camera, no RED evidence
    - Important — must fix before asset is done: ngons on visible curvature,
      texel density out of tolerance, extra objects
    - Minor — ledger-able: naming nit, hidden-face ngon, harmless extra slot
    Each issue: object name, what the evidence shows, which rule or quality
    criterion it fails, and the fix if obvious.
    **Build Quality:** approved | needs fixes
    Under 40 lines. The controller acts on this directly.
```
