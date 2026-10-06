---
name: assert-first-modeling
description: Use when about to create or modify any geometry, UVs, material, or texture in a DCC — write the scene assert first, watch it fail, then build to green
---

# Assert-First Modeling

Adapted from superpowers `test-driven-development`. Tests become `assert_scene` rules; the test runner is `measure`.

## The Iron Law

```
NO GEOMETRY, UV, OR MATERIAL CHANGE WITHOUT A FAILING ASSERT FIRST
```

**Core principle:** If you didn't watch the assert fail, you don't know it checks the right thing. An assert that passes before you build is asserting the wrong object, the wrong rule, or a rule already met — fix the assert.

**Exceptions (ask first):** throwaway spikes ("can Geometry Nodes do this?"), imported generated meshes (assert *after* import, before any edit), review-camera placement.

## Red → Green → Measure

```
RED      write one assert for one deliverable; run it; confirm it FAILS for the expected reason
GREEN    build the minimal geometry/material that satisfies it; run it; PASS
MEASURE  run measure() on every touched object; fix anything it flags that the assert didn't cover; stay green
NEXT
```

### RED — write the failing assert

One deliverable, exact names, spec values:

```python
assert_scene({
  "Lamp_Shade": {
    "exists": True, "type": "MESH",
    "collection": "Lamp/Parts", "parent": "Lamp_Stem",
    "tri_count": "<=800", "manifold": True, "ngons": 0,
    "bbox": {"min": [-0.15,-0.15,0.42], "max": [0.15,0.15,0.60], "tol": 0.005},
    "material_slots": ["M_Lamp_Fabric"],
  }
})
```

Good: one object, named rules, spec values pinned.
Bad: `assert_scene({"Lamp_Shade": {"exists": True}})` — passes with a cube.

For materials:
```python
assert_material("M_Lamp_Fabric", {
  "base_color": {"image": "T_Lamp_Fabric_BC.png", "colorspace": "sRGB"},
  "roughness":  {"image": "T_Lamp_Fabric_R.png",  "colorspace": "Non-Color"},
  "normal":     {"image": "T_Lamp_Fabric_N.png",  "colorspace": "Non-Color"},
  "missing_images": 0,
})
```

For UVs:
```python
assert_uv("Lamp_Shade", {"overlap_pct": 0, "islands": "<=4",
                         "texel_density": {"target": 1024, "tol_pct": 10}})
```

### Verify RED — watch it fail

Run it. Confirm:
- it FAILS (not errors)
- the failure is the expected one ("object does not exist", not "unknown rule")
- it fails because the thing is missing, not because of a typo in the name

Passes? You're asserting existing state. Fix the assert.
Errors? Fix the assert until it fails correctly.

### GREEN — minimal build

Simplest geometry that satisfies the assert. Not the prettiest, not with extra bevels the spec didn't ask for. Run the assert → PASS.

### MEASURE — the refactor gate

`measure("Lamp_Shade")` reports everything the assert didn't pin: poles, loose verts, inverted normals, doubles, unused slots. Clean what it flags. Re-run the assert; must stay green. This is where you improve topology — not before green.

## When the assert can't go green

Three honest attempts at a topology and `measure` still reports non-manifold → stop, report. Don't widen the assert to make it pass. Changing a Global Constraint is a ruling for the controller, not the implementer.

## Red Flags — STOP

- "I'll build it first and assert after" → build gets shaped by what you made, not what was asked
- "The assert is obvious, skip RED" → you don't know it's wired to the right object
- "I'll loosen the tolerance" → that's a spec change; ledger a ruling or escalate
- "`measure` is noisy, ignore it" → it's the only thing that sees flipped normals
- "The render looks right" → renders don't see overlap, scale, or manifoldness

## What this buys over a long job

Each task's assert is a **re-runnable contract**. After compaction, after a different agent takes over, after the user edits by hand — run every assert in the plan and you know exactly which deliverables still hold. That's regression testing for a scene.
