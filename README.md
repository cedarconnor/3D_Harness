# 3D Harness

**Persistent workflows, practical skills, and measured feedback for longer Blender projects.**

3D Harness helps an agent build and revise a 3D environment while preserving its assets, materials, lighting, and project decisions across sessions. It runs above an existing Blender MCP or owned background Blender process, with the artist working through their usual agent chat.

**Status: v0.19.0 · Blender-first research prototype · one cooperating native writer.** See the [changelog](CHANGELOG.md) for version history and the [build plan](docs/BUILD_PLAN.md) for open gates and next work.

![A brick potting shed with a workbench, garden planting, and a paved approach, rendered in Blender](docs/images/potting-shed.png)

*A guided production study from the retained checkpoint history. The distant environment and inherited foliage remain unfinished. This image demonstrates a working scene, not a proven advantage over plain MCP. [Image provenance and asset credits](docs/images/README.md).*

## What it does

- **Continues from files:** retains the brief, decisions, checkpoint history, handoff notes, and unresolved operations so a fresh context can resume the project.
- **Orients a new session in seconds:** `brief` prints where the project stands and the permitted next steps, with each command filled in from the verified record.
- **Starts from existing scenes:** previews missing identity assignments, applies the chosen plan to a new native file, and independently checks its saved identities and observation.
- **Scopes revisions:** records the intended script and preservation contract before an edit, then checks the saved result against that contract. Contracts can permit narrow changes such as one modifier setting, one node field, a named new light or a world change, and nothing else.
- **Retains deliberate artist edits:** freezes an externally saved revision for review, then accepts it with a checked contract, updated decisions, and attributed review notes. Textures the artist left beside their file are packed into an owned copy.
- **Keeps review feedback actionable:** records notes against a checkpoint, object, material, or rendered view, so a fresh session sees every open issue. Responses, verification, and artist acceptance stay separate, and a resolved note asks for a recheck only when something it depends on changed. An optional pinned seven-stage environment workflow routes the craft skills.
- **Measures native state:** observes identities, shared assets, collection instances and their libraries, evaluated geometry, authored/evaluated UV data, authored mesh attributes such as shading, seams and creases, materials, image dependencies, cameras, lights, and selected render settings, with explicit coverage limits.
- **Renders fixed review views:** renders a project's declared cameras of any saved file without saving it, bound to that file's hash, one render at a time.
- **Checks what rests on what:** measures whether objects such as bench legs rest on their support, says how each finding was established, and remembers which repairs did not work.
- **Gives the artist a review page:** a local before/after page with the renders, what changed by stable ID, open notes and one-click answers to the agent's questions; the artist's notes come back with one command, and their approval through their own terminal.
- **Learns from caught errors:** an error the artist found becomes a computed check, proven on the checkpoint where it happened and the one where it was fixed. The owner approves it into a versioned library, and later projects that pin the library run it before a stage completes.
- **Measures UV quality:** reports each mesh's texel density, UV overlap and UVs outside the unit square against targets, without saving the scene.
- **Delivers checked GLB files:** exports an accepted checkpoint to GLB, imports the file into an empty scene, and records whether every object, triangle count and bound arrived intact.
- **Separates technical and visual acceptance:** a candidate can pass its native checks and still be retained as a visual rejection without replacing the accepted checkpoint.
- **Supplies practical methods:** project skills cover planning, building, review, architecture, materials, environment assembly, and lighting. Python helpers support bounded construction, planting, ground, roof, terrain, and visibility tasks.
- **Supports evaluation:** frozen trial packets, fresh-context revisions, anonymous galleries, retained failures, per-session cost receipts and a regression suite of sealed failure situations support controlled comparisons.

The host agent provides reasoning and tool calls. The harness supplies project state and evidence; it does not start an autonomous agent or replace the existing MCP server.

## Getting started

### Requirements

- Python **3.11 or newer**. The core runtime has no third-party Python dependencies.
- Blender for native observation and authoring. Native qualification currently covers **Blender 5.1.1 on Windows**.
- An agent client with workspace access and either an existing Blender MCP connection or access to an owned background Blender process.

Clone the repository and inspect the CLI:

```sh
git clone https://github.com/cedarconnor/3D_Harness.git
cd 3D_Harness
python -m dcc_harness --help
```

Commands work directly from the checkout. For an optional editable installation on Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m dcc_harness --help
```

### Activate the workflow in your agent

Open the repository in your normal Codex, Claude Code, or Cursor workspace. Where project skill discovery is available, use the `dcc-harness` entry skill; it starts every session with `python -m dcc_harness brief PROJECT`. The [agent quick reference](docs/guides/AGENT_QUICK_REFERENCE.md) has the exact command sequences and payload shapes. A portable explicit prompt is:

> Read `.agents/skills/dcc-harness/SKILL.md` and use its workflow to start or resume my Blender project. Preserve the accepted scene, inspect pending operations before editing, and load the craft skills relevant to the task.

The executable skills live in [`.agents/skills/`](.agents/skills/). Keep the repository available: the skills refer to its runtime and documentation. A Python wheel contains the runtime only; it does not install skills, register an MCP, or configure the client. Marketplace plugins and standalone client installers are future work.

## Everyday workflow

```text
Run brief → inspect the accepted checkpoint → reserve a scoped edit
          ↓
Execute the retained script once → save a new native file → observe, render and measure relations
          ↓
Publish the checked result, or retain the rejection → write the next handoff
          ↓
Build a review page for the artist → import their notes; they approve in their own terminal
```

For a new project, first save an owned `.blend` and observe it with `python -m dcc_harness observe SAVED.blend --blender PATH --output-dir NEW_FOLDER`. This opens the file in a fresh background Blender, never saves it, and reports `READY` or the issues to fix. If the scene lacks stable harness identities, use [initial scene adoption](docs/guides/SCENE_ADOPTION.md): `adopt-preview` lists proposed assignments, then `adopt-apply` writes and independently observes a new file. Existing IDs are preserved; ambiguous identities block adoption. See the [everyday workflow](docs/guides/EVERYDAY_WORKFLOW.md) for preparation and exact edit commands.

Example commands below assume you have prepared your own baseline, observation, brief, decisions, and handoff files. They are not bundled demo files.

```sh
python -m dcc_harness start ./my-project/state --checkpoint ./my-project/baseline.blend --observation ./my-project/baseline.json --brief-file ./my-project/BRIEF.md --decisions ./my-project/decisions.json --handoff ./my-project/CONTINUE.md
python -m dcc_harness brief ./my-project/state
python -m dcc_harness resume ./my-project/state
python -m dcc_harness review ./my-project/state
```

| Command | Purpose |
|---|---|
| `brief` | Start here: where a project stands and the permitted next steps with filled-in commands, as Markdown |
| `next` / `requirements` | The same next steps as JSON; a stage's required evidence and a submission skeleton |
| `observe` | Observe a saved `.blend` in a fresh background Blender, without saving it, for `start`, edits and revisions |
| `render` / `render-wait` | Render a project's fixed review views of a saved `.blend` without saving it, one at a time per machine, with a bound receipt and evidence entries |
| `relations` | Measure whether declared subjects rest on their support surfaces in a saved `.blend`, classify findings by evidence strength, and record repair attempts in the project's history |
| `review-page` / `review-import` | Write a local before/after page for the artist, with renders, changes by stable ID, notes and stage questions; bring their notes back, and their approval through their own terminal |
| `check-propose` / `check-approve` / `checks` / `check-occurrence` | Propose a learned check from an artist note, approve it into a library (owner only), list and export the library, or count a repeat |
| `uv-report` | Measure texel density, UV overlap and UVs outside the unit square of a saved file against targets |
| `deliver-glb` | Export a saved file to GLB, reimport it into an empty scene and compare by stable ID, with a receipt bound to the checkpoint |
| `fill-hashes` | Fill and verify `{path, sha256}` file references in a payload, writing a new file |
| `adopt-preview` / `adopt-apply` | Preview initial identity assignments, then save and independently observe a new Blender file |
| `preview-revision` / `accept-revision` | Freeze, review and accept a deliberate saved edit into an existing project |
| `start` | Establish a continuity project from a saved native file and matching observation |
| `resume` | Verify the checkpoint chain and retrieve decisions, handoff, shared users, and pending work |
| `review` | Retrieve the current project and latest check for inspection |
| `begin-edit` | Retain a script/contract and reserve one scoped edit; execution is separate |
| `finish-edit` | Recompute checks and publish, reconcile, or retain a rejected result |
| `feedback-add` / `feedback-respond` / `feedback-verify` / `feedback-decide` | Record a note, a response with evidence, a verification, or an attributed disposition |
| `workflow-template` / `workflow-bind` | Inspect the packaged environment workflow, then pin it and its skills to a project |
| `stage-submit` / `stage-complete` / `stage-reopen` | Freeze a stage's evidence, complete it under its review policy, or reopen it |
| `check` / `diff` | Evaluate observed requirements or declared changes |
| `pack-observation` | Write a new lossless compact observation without rewriting retained evidence |

The pilot's `init`, `status`, `begin`, and `finish` journal commands remain for legacy journal-only projects. Use the commands above for new work.

If acknowledgement is lost, inspect the saved native result and reconcile it before sending another write. Direct MCP edits remain outside the reservation mechanism. Use one native writer and preserve the accepted file.

For an artist edit made outside a reservation, use [external revision review](docs/guides/EXTERNAL_REVISIONS.md). It requires a separate saved candidate, fresh observation, explicit change contract, handoff and decision updates. With `--blender`, textures referenced beside the candidate are packed into an owned copy first. The workflow preserves existing history and records caller-supplied review provenance; it does not settle a pending native operation.

[Structured feedback and environment stages](docs/guides/STRUCTURED_FEEDBACK.md) are optional. Notes keep their checkpoint, object, and view anchors across sessions; implementation claims, verification, and artist acceptance remain separate records. A pinned seven-stage workflow routes the existing skills and requires current evidence before a stage completes. Coordination adds no background agent or MCP server.

## Skills

| Skill | Use |
|---|---|
| [`dcc-harness`](.agents/skills/dcc-harness/SKILL.md) | Start, resume, review, and route ordinary work |
| [`dcc-plan-environment`](.agents/skills/dcc-plan-environment/SKILL.md) | Define the brief, shared assets, constraints, and review views |
| [`dcc-build-revise`](.agents/skills/dcc-build-revise/SKILL.md) | Author scoped changes and save measured checkpoints |
| [`dcc-review-continue`](.agents/skills/dcc-review-continue/SKILL.md) | Inspect results, preserve accepted work, and prepare a handoff |
| [`dcc-architecture`](.agents/skills/dcc-architecture/SKILL.md) | Openings, dimensions, construction joins, and roof details |
| [`dcc-materials`](.agents/skills/dcc-materials/SKILL.md) | Shared material users, physical texture scale, glass, and wear |
| [`dcc-environment-assembly`](.agents/skills/dcc-environment-assembly/SKILL.md) | Ground support, planting, circulation, boundaries, and purposeful detail |
| [`dcc-lighting-review`](.agents/skills/dcc-lighting-review/SKILL.md) | Lighting intent, camera framing, and controlled comparisons |
| [`dcc-blind-test`](.agents/skills/dcc-blind-test/SKILL.md) | Coordinate explicitly requested independent comparisons |
| [`blender-craft`](.agents/skills/blender-craft/SKILL.md) | Index of 25 general Blender craft skills: modeling, sculpting, CAD, Geometry Nodes, UVs, shading, baking, lighting, camera, rendering, compositing, animation, motion design, Grease Pencil, rigging, skinning, mocap, hair, simulation, matchmove, realtime export and pipeline |

Read [craft capabilities and recipe boundaries](docs/guides/CRAFT_SKILLS.md) before treating a skill as a general-purpose geometry or artistic-quality validator. The `blender-*` skills each carry code that `scripts/qualify_blender_skills.py` runs in Blender; they passed on 5.1.1 and 5.2.1 ([library guide](docs/guides/BLENDER_SKILL_LIBRARY.md)). That proves their methods work, not that following them produces good-looking results.

## Validation and current limits

The v0.19.0 source suite ran **437 tests: 435 passed, two Windows symlink-permission cases skipped**; the installed-wheel suite ran the same tests, also skipping the eleven that check source-tree documentation and skills. Every version also runs native Blender fixtures; see the [0.19.0 report](docs/archive/releases/ATTRIBUTES_0_19_0_RESULTS.md) for the attribute hash, the [0.18.1 report](docs/archive/releases/MAINTENANCE_0_18_1_RESULTS.md) for saved-state evidence and offline mode, the [0.18.0 report](docs/archive/releases/UV_0_18_0_RESULTS.md) for the UV report, the [0.17.0 report](docs/archive/releases/MODIFIERS_0_17_0_RESULTS.md) for modifier and node permissions, the [0.16.0 report](docs/archive/releases/RELOCATION_0_16_0_RESULTS.md) for revision relocation, the [0.15.0 report](docs/archive/releases/COVERAGE_0_15_0_RESULTS.md) for coverage and rechecks, the [0.14.0 report](docs/archive/releases/DELIVERY_0_14_0_RESULTS.md) for GLB delivery, the [0.13.1 report](docs/archive/releases/MAINTENANCE_0_13_1_RESULTS.md) for maintenance, the [0.13.0 report](docs/archive/releases/CHECKS_0_13_0_RESULTS.md) for learned checks, the [0.12.0 report](docs/archive/releases/OWNER_APPROVAL_0_12_0_RESULTS.md) for owner approval, the [0.11.0 report](docs/archive/releases/REVIEW_PAGE_0_11_0_RESULTS.md) for the review page, the [0.10.0 report](docs/archive/releases/INSTANCES_0_10_0_RESULTS.md) for collection instances, the [0.9.0 report](docs/archive/releases/RELATIONS_0_9_0_RESULTS.md) for `relations`, the [0.8.0 report](docs/archive/releases/RENDER_0_8_0_RESULTS.md) for `render` and `render-wait`, the [0.7.0 report](docs/archive/releases/GUIDANCE_0_7_0_RESULTS.md) for `brief`, `next` and `requirements`, the [0.6.0 report](docs/archive/releases/STEP_COST_0_6_0_RESULTS.md) for the `observe` and `fill-hashes` commands and the [0.5.1 report](docs/archive/releases/MAINTENANCE_0_5_1_RESULTS.md) for the latest maintenance fixes. The [changelog](CHANGELOG.md) summarizes each version's evidence, and the [scripts index](scripts/README.md) lists its qualification scripts.

The [0.5.0 report](docs/archive/releases/FEEDBACK_0_5_0_RESULTS.md) covers feedback retention, evidence binding, and native revision tests. Its native exercise completed all seven workflow stages on a synthetic micro-scene. The first fresh agent exposed a missing view-definition artifact; the corrected package retains actual settings alongside their digest. In the corrected sealed trial, an independent reviewer verified three notes and left the visual note uncertain. These results test continuity mechanisms, not visual-quality improvement.

The comparisons so far have **not established a general visual-quality or long-horizon advantage** for the harness:

- In the short comparison, six independent builds and six fresh revisions all passed technical checks. Both artist-preferred entries used plain MCP.
- In the longer comparison, sixteen fresh sessions produced fourteen native-check passes and two incomplete stages. Plain MCP completed 8/8 stages and the harness 6/8.
- A realistic held-out comparison was interrupted after one partial build.

[Short comparison](docs/archive/studies/BLIND_RESULTS.md) · [Longer comparison](docs/archive/studies/CONTINUITY_RESULTS.md) · [Realistic comparison](docs/studies/REALISM_COMPARISON.md)

The harness's own overhead has improved. On the same one-parameter revision, a fresh agent took 8 to 10 minutes on 0.5.1 and 0.6.0 and 3 minutes on 0.7.0, starting its edit after 51 seconds instead of 4 to 5 minutes ([report](docs/archive/releases/GUIDANCE_0_7_0_RESULTS.md)). On 0.9.0, two fresh agents each fixed a bench on sloping ground on the first attempt without repeating a failed whole-bench move ([report](docs/archive/releases/RELATIONS_0_9_0_RESULTS.md)). On 0.13.0, a fresh agent continuing the 1,289-object production garden found and answered all three open notes in 32 minutes ([E5 results](docs/studies/E5_CONTINUATION_RESULTS.md)). On 0.16.0, fresh agents handled all six known failure situations correctly: a lost acknowledgement, a stale image, a shared material, a missing view definition, an artist-saved revision and a conflicting late request ([P5 results](docs/studies/P5_SKILL_REGRESSIONS.md)). These are single runs, not a measured advantage over plain MCP.

Current boundaries:

- Advisory execution: no native sandbox, exactly-once guarantee, external-write interception, or unattended agent scheduler.
- Collection instances, local or from linked libraries, are observed since 0.10.0. Vertex, face, particle and Geometry Nodes instancing and library overrides are still reported as issues. External revisions pack their textures since 0.16.0 but still reject linked libraries, because packing one changes its collections' asset identity. Libraries are referenced, not copied into the project store.
- Blender qualification only; Unreal and other DCC adapters remain planned.
- Observation coverage is explicit and incomplete: animation over time, arbitrary procedural instances, rig semantics and general topology quality are not certified. UV overlap and texel density are measured by the separate `uv-report`, as grid and per-mesh estimates, not in observations ([UV report](docs/guides/UV_REPORT.md)).
- Hashes bind evidence to files; they do not authenticate producer truthfulness or establish artistic quality.
- Agent reviews are caller-attributed. Since 0.12.0 an artist's approval needs the artist's own terminal, and agent sessions are refused. This guards against an agent approving its own work through the commands; an agent with an unrestricted shell on the same account could still get around it ([owner approval](docs/guides/OWNER_APPROVAL.md)).
- Learned checks cover object fields and supported-by relations only. A project keeps the library version it was bound with, and repeats are counted by hand ([learned checks](docs/guides/LEARNED_CHECKS.md)).
- Animation and motion design have craft skills, but the harness does not yet observe or check animation over time. Design taste stays the artist's call, and client installers remain future work.

## Development and tests

Run the portable suite from the repository:

```sh
python -m unittest discover -s tests -v
```

Native scripts must run inside Blender. For example, this visibility fixture uses a new output directory and a separate background process:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/qualify_visibility.py -- --repo . --out runs/my-visibility-check
```

Choose a fresh output path. Inspect the process exit code and report; a success message alone is insufficient. The [scripts index](scripts/README.md) lists each version's qualification scripts and whether they run from a fresh clone. See [validation](docs/archive/releases/VALIDATION.md) and [observer performance qualification](docs/guides/OBSERVATION_PERFORMANCE.md) for the scope of earlier tests.

## Repository guide

| Path | Contents |
|---|---|
| `dcc_harness/` | CLI, continuity store, observations, checks, review utilities, and bounded recipes |
| `.agents/skills/` | Current project skills |
| `scripts/` | Native qualification fixtures, benchmarks, asset intake, and study tooling; see the [scripts index](scripts/README.md) |
| `tests/` | Portable regression suite |
| `examples/` | Procedural courtyard example and spec |
| `experiments/` | Retained briefs, contracts, and comparison methods |
| `docs/` | The tracked [build plan](docs/BUILD_PLAN.md), decisions, guides, recipes and open studies. `docs/archive/` holds addressed work: release reports, completed studies, implemented plans, and superseded inputs. See the [documentation index](docs/README.md). |
| `runs/` | Local native files, observations, rendered galleries, and test logs; excluded from Git |

Downloaded asset kits, private photographic references, large `.blend` checkpoints, and local run galleries are not included in a clone. Some detailed reports link to those local artifacts; the written reports and representative README render are included. The example render's source assets are credited [here](docs/images/README.md).

## Further reading

- [Documentation index](docs/README.md) and [changelog](CHANGELOG.md)
- [Agent quick reference](docs/guides/AGENT_QUICK_REFERENCE.md), [review page](docs/guides/REVIEW_PAGE.md), [owner approval](docs/guides/OWNER_APPROVAL.md), [learned checks](docs/guides/LEARNED_CHECKS.md), [GLB delivery](docs/guides/GLB_DELIVERY.md) and [UV report](docs/guides/UV_REPORT.md)
- [Everyday workflow](docs/guides/EVERYDAY_WORKFLOW.md) and [continuity APIs](docs/guides/CONTINUITY_USAGE.md)
- [Structured feedback and environment stages](docs/guides/STRUCTURED_FEEDBACK.md)
- [Reference-led quality loop](docs/guides/QUALITY_LOOP_USAGE.md)
- [Craft skills](docs/guides/CRAFT_SKILLS.md) and [terrain study](docs/archive/releases/TERRAIN_0_4_7_RESULTS.md)
- [Active build plan](docs/BUILD_PLAN.md) and [design decisions](docs/DESIGN_DECISIONS.md)
- [Packaging and entry points](docs/reference/DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md)
- [Skill and motion-design plans](docs/reference/DCC_HARNESS_SKILL_SYSTEM.md)
- [Research](docs/reference/DCC_HARNESS_RESEARCH.md) and [UE-MCP review](docs/reference/DCC_HARNESS_UE_MCP_REVIEW.md)

The active build plan and decision log take precedence over the original architecture note and historical proposals. Broader capabilities described in those studies are proposals, not shipped features.
