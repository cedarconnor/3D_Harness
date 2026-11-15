# G7 trial: geometry-script, November 15

One of the two extension trials in build-plan item G7. It asks whether building Geometry Nodes trees with the geometry-script DSL makes a fresh agent more likely to succeed than writing plain `bpy`. One run per cell, so the result is directional. Evidence is retained in `runs/g7-extension-trials-2026-11-15/gn-trial/`.

## Setup

- **Extension.** [carson-katri/geometry-script](https://github.com/carson-katri/geometry-script) 1.0.0, GPL-3.0-or-later, from its `nightly` release of November 9 (`geometry_script-1.0.0-blender-5.2.zip`, 189 KB, SHA-256 `f07635f2…0c936e41`). It requires Blender 5.2 or newer.
- **Install.** Into a separate Blender user folder used only for this trial, with the owner's approval. The everyday Blender 5.2 profile was not touched. No source was copied into this package.
- **Blender.** 5.2.1, background, factory settings.
- **Tasks.** Five trees, each with exact input names, types and defaults: copy a cube onto a grid; scatter spheres on a plane by density and seed; displace a generated grid by noise; delete vertices below an X threshold; store a named attribute and set a material.
- **Arms.** Each task was built once by a fresh agent using plain `bpy` and once by a fresh agent using the DSL. Both could read the `blender-geometry-nodes` and `blender-python` skills. The DSL agents could also read the installed extension's README, `api/` and examples.
- **Counting.** Agents could run Blender only through one script, which ran their file, checked the saved result and logged the attempt. At most five attempts.
- **Checker.** It changes the group's inputs and re-evaluates, so a tree that only matches the defaults fails. It was proven beforehand with reference solutions for all five tasks, which the agents never saw.

## Results

| Task | `bpy`: attempts | `bpy`: tokens | `bpy`: script lines | DSL: attempts | DSL: tokens | DSL: script lines |
|---|---|---|---|---|---|---|
| repeat-grid | 1 | 81,898 | 73 | 1 | 104,370 | 24 |
| scatter | 1 | 92,176 | 61 | 1 | 108,039 | 28 |
| displace | 1 | 81,318 | 47 | 1 | 105,656 | 20 |
| cut | 1 | 81,138 | 39 | 1 | 103,391 | 19 |
| attribute | 1 | 81,542 | 58 | 1 | 117,169 | 33 |
| **Mean** | **1.0** | **83,614** | **56** | **1.0** | **107,725** | **25** |

All ten agents passed on their first attempt. Tokens are each agent's total for the run. Script lines exclude blanks and comments and include the scene setup around the tree.

Mean wall time was 35 s for `bpy` and 40 s for the DSL. The `bpy` agents made four or five tool calls each; the DSL agents made eleven to fifteen, most of them reading the extension's API files.

## What it shows

- **The trial could not separate the arms on success.** First-attempt success was five of five on both sides, so "attempts to a valid tree" is 1.0 for both. These tasks were too easy for the question; with the existing skill, plain `bpy` was already reliable on trees of five to ten nodes.
- **The DSL halves the script.** Scripts were 25 lines against 56 on average. The tree itself reads as ordinary expressions (`h = (z + 1.0) / 2.0`) where `bpy` needs a node and two links per operation.
- **The DSL cost about 29% more tokens here.** The agents had to read the extension's API to use it. A bundled skill or prior familiarity would reduce that; this trial did not test either.
- **Its agent report is worth copying.** `geometry_script.api.agent.run()` runs a script and returns `{"ok", "report"}`: each tree built, the evaluated geometry's counts and bounds, and node warnings read from `modifier.node_warnings`. Our Geometry Nodes verify blocks check geometry but do not read node warnings.

## Limits

- One run per cell, five small tasks, one model.
- Trees of five to ten nodes. The DSL's claimed advantage is on large trees, repeat and simulation zones, and reorganising existing trees; none was tested.
- The `bpy` arm had a skill written for it; the DSL arm had the extension's own files and no skill.

## Decision

**Dropped as a harness dependency.** The owner accepted this recommendation on November 15.

## Recommendation

**Drop it as a harness dependency for now, and keep one idea.**

- It needs Blender 5.2, which is not the primary qualified version, and it is a GPL add-on that every user would have to install.
- On tasks of this size it did not make agents more successful, and it cost more tokens.
- Adopt the idea in its report: read `modifier.node_warnings` in the `blender-geometry-nodes` verify step. That needs no dependency.

Revisit if large procedural trees become a regular part of the work; the right trial then is trees of forty nodes or more, where the script-length difference should start to matter.
