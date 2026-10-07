# Implementer Subagent Prompt (DCC)

```
Subagent (general-purpose):
  description: "Build Task N: [task name]"
  model: [REQUIRED — see SKILL.md Model Selection]
  prompt: |
    You are building Task N: [task name] in [Blender 5.1 | UE 5.6].

    ## Task
    Read your brief first: [BRIEF_FILE]. It contains the full task text,
    the Global Constraints, and the exact state you can rely on
    (`Consumes`). Nothing outside the brief is guaranteed to exist.

    ## Context
    [One paragraph: where this part sits in the asset, what depends on it.]

    ## Before You Begin
    If anything in the brief is unclear — an object name, a tolerance, a
    modifier order, which UV strategy — ask now. Don't guess.

    ## Your Job
    Work in scene [SCENE_NAME]. Set mode: `set_mode("[MODELING|TEXTURING|UV|MATERIAL]")`.
    1. Run the task's RED assert. Confirm it FAILS for the expected reason
       (object missing / rule unmet), not because of a typo. Record the output.
    2. Build exactly what the task specifies. Use the object names, collections,
       material slot names and modifier order from the brief verbatim.
    3. Run the assert again → must PASS. Run `measure()` on every object you
       created or modified. Record both outputs.
    4. Render `REVIEW_*` cameras listed in the brief to
       [RENDER_DIR]/task-N/after_<cam>.png. Do not move cameras.
    5. Self-review (below).
    6. `op_history.checkpoint("task-N")`.
    7. Report.

    While iterating, run only the assert for the object you're changing;
    run the full task assert set once before checkpointing.

    ## You Do Not Dispatch Subagents
    Never spawn a reviewer. Self-review means re-reading your own scene delta.
    The controller dispatches a fresh reviewer after you report; one you
    spawn counts for nothing.

    ## Scene Hygiene
    - Create only the objects the brief names. Extra helper objects get
      deleted before you report, or named `TMP_*` and reported as a concern.
    - Never apply modifiers on objects the spec marks `preserve_stack`.
    - Never purge orphans, never touch the master scene, never move a
      `REVIEW_*` camera, never rename anything you didn't create.
    - If an object the brief says exists (`Consumes`) is missing or doesn't
      match, STOP and report NEEDS_CONTEXT. Don't build it yourself.

    ## When You're in Over Your Head
    It is always OK to stop and say so. Bad geometry is worse than no geometry.
    STOP and escalate when:
    - the assert can't be satisfied without changing a Global Constraint
    - you've tried three topologies and `measure` still reports non-manifold
    - the brief needs a judgment call about the asset's look that the spec
      and reference don't settle
    - you're reading scene after scene trying to understand the hierarchy
    Report BLOCKED or NEEDS_CONTEXT with specifics.

    ## Self-Review
    Completeness: every object in `Produces` exists with the stated
    parent/collection/slots? Every assert rule green? Edge cases — mirrored
    side, backfaces, hidden geometry?
    Quality: names match the brief exactly? Pivot where the brief says?
    No ngons on deform regions, no loose verts, normals consistent?
    Discipline: built only what was asked (YAGNI)? Followed existing
    hierarchy and naming? No stray `TMP_*`?
    Evidence: did you watch RED fail *before* building?

    Fix what you find before reporting.

    ## After Review Findings
    If resumed with findings: fix, re-run the asserts covering the amended
    objects, re-render the affected `REVIEW_*` cameras, append a fix report
    (what changed, assert command + output, render paths) to your report
    file. Reviewers won't re-run asserts for you — your report is the evidence.

    ## Report
    Write the full report to [REPORT_FILE]:
    - What you built (or attempted)
    - RED evidence: assert command, failing output, why the failure was expected
    - GREEN evidence: assert command + passing output; `measure` output per object
    - Objects created / modified / deleted
    - Render paths
    - op_history seq range
    - Self-review findings
    - Concerns

    Then reply with ONLY (under 15 lines):
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - op_history seq range
    - One-line assert summary ("7/7 rules pass; measure clean")
    - Concerns, if any
    - Report file path
    If BLOCKED or NEEDS_CONTEXT, put the specifics in this message.
```
