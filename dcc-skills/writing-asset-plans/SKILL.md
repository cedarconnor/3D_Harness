---
name: writing-asset-plans
description: Use when you have an approved asset_spec (or material/scene spec) for a multi-step modeling, texturing, or lookdev job, before executing any scene operation
---

# Writing Asset Plans

Adapted from superpowers `writing-plans`. Files/tests become objects/asserts.

## Overview

Write a plan for an implementer who has not seen this scene, this spec, or this conversation. Assume they know the DCC's Python API once they know the exact object names, the exact asserts, and the exact values from the spec, and that they will make a reasonable choice wherever the plan leaves one open. What they cannot know is what you decided: which objects, which names, which modifier order, which UV strategy, which asserts prove each task. Document those.

**Announce at start:** "Using writing-asset-plans to create the build plan."

**Save plans to:** `job/<asset-slug>/plan.md` next to `spec.json`.

## Scope Check

If the spec covers independent sub-assets (a chair *and* a table, a prop *and* its material library), split into one plan per sub-asset. Each plan must produce an asset that passes `check_asset_ready` on its own.

## Object Structure

Before defining tasks, map which objects / collections / materials / images will be created or modified and what each is responsible for. This is where decomposition is locked in.

- One object per clear responsibility. Prefer several focused meshes joined at the end over one mesh carved from a block when the spec calls for separable parts.
- Objects that change together share a collection.
- In an existing scene, follow established naming and hierarchy. Don't restructure outside the task.

## Task Right-Sizing

A task is the smallest unit that carries its own assert cycle and is worth a fresh reviewer's gate. Fold setup (collection creation, material slot allocation, camera placement for review renders) into the task whose deliverable needs it. Split only where a reviewer could meaningfully reject one task while approving its neighbor. Each task ends with an independently assertable deliverable.

## Step Granularity

Each step is one action with a checkable result:

- "Write the failing assert" — step
- "Run it to make sure it fails" — step
- "Build the minimal geometry/material to make it pass" — step
- "Run the assert and `measure`; make sure it passes" — step
- "Checkpoint" (undo marker + op_history checkpoint record + optional file snapshot) — step

## Plan Document Header

```markdown
# [Asset Name] Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: asset-driven-development (recommended) or inline execution task-by-task. Steps use `- [ ]` syntax.

**Goal:** [One sentence]

**Approach:** [2-3 sentences: blockout → hi-poly → retopo → UV → material → export, or whatever the workflow file says]

**DCC / Version:** [Blender 5.1 / UE 5.6]

**Spec:** job/<slug>/spec.json — the plan argues from the spec; executors read both.

**Workflow:** workflows/<type>.yaml — stage order and checkpoint rules.

## Global Constraints

[Copy verbatim from spec: unit scale, axis convention, naming regex, tri budget, texel density, UDIM layout, colorspace rules, export format. One line each. Every task implicitly includes these.]

## Review Focus

[The five conditions the spec implies but no task's asserts exercise that are most likely to bite — e.g. "mirror modifier before bevel leaves a seam at X=0", "roughness texture in sRGB". One line each, most likely first. Then pin each to the task that owns it with an assert.]

## Review Cameras

[Named fixed cameras every render-based check uses: `REVIEW_front`, `REVIEW_3q`, `REVIEW_top`, with location/rotation/lens. Created in Task 1. Never moved.]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Objects:**
- Create: `Chair_Seat` (MESH, collection `Chair/Parts`)
- Modify: `Chair_Frame` — add parent relationship only
- Materials: `M_Chair_Wood` slot 0

**Interfaces:**
- Consumes: `Chair_Frame` exists, pivot at base, bbox z ∈ [0, 0.45]
- Produces: `Chair_Seat` parented to `Chair_Frame`, pivot at seat center, 1 material slot `M_Chair_Wood`, ≤ 1200 tris, manifold

- [ ] **Step 1: Write the failing assert**

```python
assert_scene({
  "Chair_Seat": {"exists": True, "type": "MESH", "parent": "Chair_Frame",
                 "tri_count": "<=1200", "manifold": True,
                 "material_slots": ["M_Chair_Wood"],
                 "bbox": {"min": [-0.22, -0.22, 0.43], "max": [0.22, 0.22, 0.47], "tol": 0.01}}
})
```

- [ ] **Step 2: Run assert to verify it fails**

Run: `assert_scene(...)`
Expected: FAIL — `Chair_Seat` does not exist

- [ ] **Step 3: Build `Chair_Seat`**

One line on approach when the assert leaves a choice (cube + bevel modifier vs. inset extrude); a code block only for an algorithm the assert does not determine.

- [ ] **Step 4: Run assert + measure to verify it passes**

Run: `assert_scene(...)` then `measure("Chair_Seat")`
Expected: all rules PASS; measure reports 0 non-manifold, 0 loose, 0 ngons

- [ ] **Step 5: Checkpoint**

`op_history.checkpoint("task-N-chair-seat")`; `snapshot_file("checkpoints/task-N.blend")` if the workflow profile requires it.
````

## What a Step Contains

A step is done when the implementer can write exactly one reasonable thing from it.

- **An assert step:** the rule dict, as code, with the spec's exact values in it.
- **A build step:** exact object names, collection, modifier stack order if it matters, material slot names, and the specific values the spec pins. The implementer writes the geometry. Code appears only for an algorithm the assert does not determine (a procedural pattern, a specific Geometry Nodes graph).
- **A render-check step:** which `REVIEW_*` camera, what narrow question the VLM is asked ("is there a visible gap between seat and frame?"), and what answer passes.
- **A checkpoint step:** the label.

## What a Plan Must Not Do

- Leave object names for the implementer to invent.
- Rely on the implementer remembering an earlier task — `Consumes` must carry everything.
- Use a render as the *only* check for anything `measure` can report.
- Move a review camera.
