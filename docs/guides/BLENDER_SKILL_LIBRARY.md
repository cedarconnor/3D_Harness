# Blender craft skill library

Added October 11, 2026, after 0.18.0. Twenty-five `blender-*` skills under [`.agents/skills/`](../../.agents/skills/) teach general Blender 5.x craft. The [`blender-craft`](../../.agents/skills/blender-craft/SKILL.md) index routes a task to the right ones, and [`dcc-harness`](../../.agents/skills/dcc-harness/SKILL.md) points to that index. The existing `dcc-*` skills still govern harness projects. The new skills cover what those do not: how to do the craft itself.

| Area | Skills |
|---|---|
| Foundations | `blender-python`, `blender-visual-design`, `blender-pipeline` |
| Modeling | `blender-reference-modeling`, `blender-hard-surface`, `blender-sculpt-retopo`, `blender-precision-cad`, `blender-geometry-nodes` |
| Surfaces | `blender-uv`, `blender-shading`, `blender-baking` |
| Look | `blender-lighting`, `blender-camera`, `blender-rendering`, `blender-compositing` |
| Motion | `blender-animation`, `blender-motion-design`, `blender-grease-pencil` |
| Characters | `blender-rigging`, `blender-skinning`, `blender-mocap`, `blender-hair` |
| Effects and integration | `blender-simulation`, `blender-matchmove` |
| Delivery | `blender-realtime-assets` |

## Animatica add-on skills

Added October 27, 2026: [animatica-choreographer](../../.agents/skills/animatica-choreographer/SKILL.md) covers motion generation, prompt blocks, take review and self-hosted MMCP; [animatica-marionette](../../.agents/skills/animatica-marionette/SKILL.md) covers local posing and animation repair. Both are discoverable under `.agents/skills/` and linked from the craft index. The existing rules bundler includes their files and references automatically.

These skills summarize the linked official Animatica documentation in original wording. Their frontmatter, references and scenario guidance are checked separately from the native `blender-*` examples. This addition does not install or license either add-on, configure a server, implement a managed provider, or qualify native execution. The Blender verification results below apply to the existing craft examples only.

## How the skills were written

Seven research passes read the 30 sources the owner supplied, plus Blender's manual, Python API and 4.0–5.2 release notes.

- **The supplied sources:** about 28 GitHub skill repositories, the composio Geometry Nodes skill, the mcpmarket and skillvault listings, and Microsoft's Resource2Skill.
- **What was taken:** the methods, numbers and failure modes they describe.
- **Wording:** all of it was written fresh. Several sources have no license, are GPL-3.0, or are CC BY-NC-ND (TMHSDigital's prose), so no source text was copied.
- **Specialist areas:** where the sources were thin (rigging, skinning, mocap, matchmove, simulation, hair, Grease Pencil v3, the Video Sequencer), the skills draw on the manual, the API and the release notes.

The useful structure common to the stronger sources shaped every skill:

- a short procedure with decision rules;
- the numbers that matter;
- the failure modes agents hit;
- a way to check the result.

Many sources contained API calls that fail on Blender 5.x, for example:

- `BLENDER_EEVEE_NEXT`;
- `action.fcurves`;
- `use_auto_smooth`;
- EEVEE Legacy bloom, SSR and GTAO;
- the `FAST` boolean solver;
- `MixRGB`;
- old Principled BSDF socket names.

Those were not carried over. The `blender-python` skill lists the replacements.

## Verification

Each skill ends with at least one `python verify` block: self-contained code that builds a scene, applies the skill's method, and asserts the outcome. `scripts/qualify_blender_skills.py` extracts every block and runs each skill's blocks in a fresh background Blender, after a factory reset per block. `tests/test_blender_skills.py` checks:

- that the library covers the required areas;
- that the index links every skill;
- frontmatter and length;
- that relative links resolve;
- that every skill has a parseable verify block that asserts something.

```powershell
python scripts/qualify_blender_skills.py --blender "<BLENDER>" --out runs/<NEW-FOLDER> --runtime .
python scripts/qualify_blender_skills.py --blender "<BLENDER>" --out runs/<NEW-FOLDER> --runtime . --only blender-rigging blender-uv
```

| Run | Result |
|---|---|
| Blender 5.1.1 | 25 blocks in 25 skills passed |
| Blender 5.2.1 LTS | 25 passed, after gating the Geometry Nodes modifier-input change described below |
| Both, October 15 | 28 blocks in 25 skills passed on each, after P17 added blocks to `blender-shading`, `blender-lighting` and `blender-python` |

Among other things, the blocks run:

- a Rigify generation and an IK chain reaching its target;
- automatic weights with the bone-heat check;
- a BVH round trip and a constraint retarget baked to keys;
- a synthetic plate tracked and solved to 0.23 px;
- rigid-body and cloth bakes;
- a Cycles bake read back from disk;
- QuadriFlow retopology;
- a Geometry Nodes scatter counted through `evaluated_geometry()`;
- a 5.x compositor render;
- glTF, STL, USD and Alembic round trips;
- a linked library with an override;
- Grease Pencil v3 drawings;
- curves hair attached to a surface;
- Workbench silhouette coverage.

A separate probe confirmed that 5.1 has the operators and properties named only in the prose, outside the blocks: the Clip, fluid, bake, deform-bind, vertex-group and Rigify operators, `file_path_foreach`, collection exporters, light linking, sky and world sun settings, File Output's 5.x fields, and others.

Local evidence is under `runs/blender-skills-2026-10-11/`, excluded from Git.

## Corrections found by running the code

Running the blocks corrected claims from the sources and from the first drafts. The skills state the measured behaviour.

| Claim | Measured on 5.1.1 |
|---|---|
| Baking needs the target image node to be the *active* node | Selection decides. A selected node bakes even when it is not active; an active, unselected node returns `CANCELLED` without raising |
| `transform_apply(scale=True)` applies scale | It also applies location and rotation, because all three default to True. A rigid body whose location was applied this way started inside the ground and launched 7 m upward |
| A rigid body resting 6 cm high means the collision margin is too large | That was the `transform_apply` fault above. With correct transforms the default margins rest exactly on the ground |
| IK pole angle 0 points the joint at the pole | On a chain with zero roll it swung the elbow 90° sideways; ±90° was needed. The skill now says to measure it |
| Editing F-curve modifiers in Python takes effect on the next `frame_set` | `fcurve.evaluate()` showed the change, but the object kept playing the old curve until `action.update_tag()` |
| The Principled Hair BSDF has a Melanin input | Only after `parametrization = 'MELANIN'`; until then the socket is absent |
| `override_hierarchy_create` replaces a collection instance | From Python it adds the override beside the instance empty, so a USD export then held two crates |
| Mirror-modifier copies have flipped UV islands | Only without `use_mirror_u`. With it the copy's islands keep positive area, but still overlap |
| The first Geometry Nodes input is `Socket_2` | In a tree built from Python it was `Socket_1`. Read identifiers from the interface |
| `mod[identifier] = value` sets a Geometry Nodes input | True on 5.1. On 5.2 it raises TypeError, and `modifier.properties.inputs.<identifier>.value` replaces it |
| A 5 mm hole needs 64 segments to stay under 0.003 mm of chord error | A 6.4 mm hole at 64 segments deviates by about 0.004 mm |
| `clip.set_floor` orients a solve | No such operator exists; it is `clip.set_plane(plane='FLOOR')`. Found by checking the API names that appear only in prose |
| A first camera solve of a synthetic plate is usable | 22 px at first, then 2.9 px with distinct features and overlapping keyframes, then 0.23 px after removing tracks over 1 px and solving again |

## Notes added from the Scenario review

P17 added notes from the [Scenario for Blender review](../reference/SCENARIO_BLENDER_PLUGIN_REVIEW_2026-10-15.md), each verified before it was written:

- **Texture sets.** In `blender-shading`: wiring a texture set, with one UV Map node, inverted smoothness, height chained after the normal map, and no AO input.
- **Image decoding.** Blender 5.1 and 5.2 ignore JPEG EXIF orientation (`blender-shading`) and label an EXR declaring ACES AP1 primaries as `Linear Rec.709` (`blender-lighting`, with HDRIs applied as a new World).
- **Unsaved edits.** Python edits leave `is_dirty` false until a named `undo_push` (`blender-python`). This was also confirmed in an interactive session.

The review also reported that JPEG ICC profiles are ignored and that some progressive JPEGs stall the main thread. Neither was reproduced here, so neither was added.

## Limits

- **What the blocks prove.** They establish that each skill's API calls and mechanics work on Blender 5.1.1 and 5.2.1. They do not establish that following a skill produces good-looking work. That needs renders reviewed by the artist.
- **Guidance numbers.** Texel-density tiers, light ratios, LOD ratios, bevel widths and timing rules are starting points from the sources and common practice, not measurements of this project.
- **No fresh-agent test yet.** No fresh agent has been tested with the new skills. The P5 regression suite covers the harness workflow, not these craft skills, and should be rerun because `dcc-harness` now links the index.
- **Interactive tools.** Several interactive tools (sculpt brushes, texture painting, the Graph Editor's Euler filter, Rigify's snapping UI) need a viewport. The skills give background-safe alternatives where they exist.
- **Clip editor workaround.** The matchmove block borrows a background window's area as a Clip Editor. That works on 5.1 and 5.2, but it is an implementation detail, not a documented API.
- **Upgrades.** Rerun `qualify_blender_skills.py` after every Blender upgrade. When a block fails, update the skill text along with the code.
