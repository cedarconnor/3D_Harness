# 3D Harness

**Persistent workflows, practical skills, and measured feedback for longer Blender projects.**

3D Harness helps an agent build and revise a 3D environment while preserving its assets, materials, lighting, and project decisions across sessions. One package provides the build rules, MCP server, managed execution in an open Blender scene or a background process, and a pinned Blender bridge. The artist works through their usual agent chat.

**Status: v0.24.0 — Blender-first research prototype with managed open-scene/background execution, standalone shader effects and asynchronous add-on recipes.** See [installation and MCP operation](docs/guides/COMBINED_MCP.md), the [managed execution guide](docs/guides/MANAGED_EXECUTION.md), [changelog](CHANGELOG.md), and [build plan](docs/BUILD_PLAN.md).

![A brick potting shed with a workbench, garden planting, and a paved approach, rendered in Blender](docs/images/potting-shed.png)

*A guided production study from the retained checkpoint history. The distant environment and inherited foliage remain unfinished. This image demonstrates a working scene, not a proven advantage over plain MCP. [Image provenance and asset credits](docs/images/README.md).*

## What it does

- **Delivers one package and endpoint:** `dcc-harness-mcp` exposes build rules, managed commands, paired live operations and observations. `new-project` creates an owned background baseline; live attachment adopts an explicitly selected open scene. The bundled bridge derives from upstream MCP for Blender 2.2.2 with telemetry and activity recording removed. Raw live Python is outside this endpoint.

- **Uses qualified local add-ons:** discover providers, pin their environment, qualify reusable recipes and require or prefer them at named workflow stages. Native receipts prove actual use. Unchanged inputs and verified effects reuse evidence; refreshing changed dependencies requires a newly measured native contribution. See [add-on onboarding and limits](docs/guides/ADDON_RECIPES.md).

- **Executes through one managed service:** applies bounded operations in the paired open scene or runs scripts in owned background Blender. Both paths retain recovery evidence, independently reopen saved results, check the contract and control publication. Autonomous mode can complete stages with agent review; approval-gated mode requires owner approval before the next stage. Durable operation IDs, cancellation and time/operation budgets bound execution.
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
- **Delivers checked GLB files:** exports an accepted checkpoint with unit scale 1 metre per Blender unit, imports it into an empty scene, and checks object identity, triangle counts and bounds. Other scene scales are rejected until physical conversion is qualified.
- **Separates technical and visual acceptance:** a candidate can pass its native checks and still be retained as a visual rejection without replacing the accepted checkpoint.
- **Supplies practical methods:** project skills cover planning, building, review, architecture, materials, environment assembly, and lighting. Python helpers support bounded construction, planting, ground, roof, terrain, and visibility tasks.
- **Supports evaluation:** frozen trial packets, fresh-context revisions, anonymous galleries, retained failures, per-session cost receipts and a regression suite of sealed failure situations support controlled comparisons.

The host agent provides reasoning and tool calls. The harness supplies project state, evidence and a combined MCP endpoint; it does not start a separate autonomous agent.

## Getting started

### Requirements

- Python **3.11 or newer**. The CLI/native runtime uses the standard library; the combined package installs the pinned MCP SDK and its dependencies.
- Blender for native observation and authoring. Native qualification currently covers **Blender 5.1.1 on Windows**.
- An MCP client connected to `dcc-harness-mcp`, or an agent with workspace access to the CLI and owned background Blender.

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

The source skills live in [`.agents/skills/`](.agents/skills/). The wheel includes their local reference closure, accessible through MCP or `--export-rules`, plus the exportable pinned observation add-on. It registers the CLI/MCP executables in the selected Python environment. Configuring a client to launch the MCP and configuring Blender remain explicit setup steps. Referenced executable examples are intentionally bundled and pinned with the rules; use the matching installed wheel for older projects because checkout source/doc edits change its development catalog. See [combined package setup](docs/guides/COMBINED_MCP.md).

### Choose how the agent works

Choose the mode when creating the managed run or attaching an open scene. The mode is fixed for that run.

| Mode | Stage progression | When it stops |
|---|---|---|
| `autonomous` | The agent plans, executes, verifies and advances valid agent-reviewed stages within the brief and budgets | Missing evidence, unsupported work, uncertain outcomes, exhausted budgets or an explicit artist-only decision |
| `approval_gated` | The agent prepares and verifies each stage, then returns `AWAITING_APPROVAL` | The owner reviews and approves through their own terminal or review-page import before advancement |

An `artist_required` manifest stage or bound review policy requires owner review in either mode. Both modes enforce the same technical checks. MCP cannot provide owner approval or waive missing evidence. The host agent drives the work; the server does not run an unattended reasoning loop.

### Work directly in the open scene

Export and enable the bundled bridge, select its workspace, and start it in Blender. Use `blender_session` to discover and describe sessions, then attach the chosen scene to a new managed project with either mode. Attachment retains recovery copies and independently verifies the baseline. Use `blender_inspect` to identify targets and `blender_execute` for supported operations. See [pairing, execution, external edits and recovery](docs/guides/LIVE_BLENDER.md) for exact payloads and coverage.

Manual edits require an explicit refresh before continuing. After a lost response, inspect the retained operation using its existing UUID; do not create a new operation to repeat an uncertain edit.

### Make add-on use part of the workflow

Discover an installed provider with `blender_capabilities`, pin its environment, and qualify a reusable function, operator or node-asset recipe with `blender_recipe`. Then bind its capability to the relevant objects and stages:

- **`require`:** the stage cannot complete without a verified effect from the named qualified provider.
- **`prefer`:** use the provider when applicable; substitution or manual work requires an explicitly configured fallback.
- **`best_qualified`:** timing selection is unavailable; only explicitly configured fallbacks may proceed. Whole-worker timing cannot rank provider performance.

The agent checks capability requirements at stage boundaries and after refresh. Declared dependency changes invalidate prior evidence. Refresh must independently prove a qualifying native contribution. Unchanged inputs and verified effects reuse evidence without another job. Deleting an owned effect permits verified recreation with the same identity. Another layer requires an explicit new slot. Version-two recipes support owned modifiers, standalone materials and shader nodes, including measured nested shader groups, without requiring a dummy modifier. Source-pinned asynchronous providers use submit/poll/cancel/collect with durable intent records, cooperative GUI ticks and cancellation grace. Pending or uncertain work cannot publish; saved results still require independent reopening. Version-one recipes retain their original modifier/synchronous contract. Legacy results lacking native evidence require requalification. There is no background edit watcher. See the [v2 contracts and qualification commands](docs/guides/ADDON_RECIPES.md#version-two-shader-and-asynchronous-recipes).

Once the artist confirms a capability policy, every revision requires owner confirmation. Add-ons are installed and licensed separately, and each real provider needs its own qualification. See the [add-on guide and executable onboarding example](docs/guides/ADDON_RECIPES.md).

Portable [CI](.github/workflows/portable.yml) installs the declared `mcp==1.26.0` dependency and runs source/installed package checks on Windows and Linux. All four hosted jobs [passed on main at `7b6e470`](https://github.com/cedarconnor/3D_Harness/actions/runs/40042644685). Transitive dependencies are not fully locked. Blender checks remain a separate local Windows gate. The [external-review ledger](docs/archive/releases/EXTERNAL_REVIEW_0_23_RESULTS.md) records the earlier integrated gate and unresolved preference incident; the [recovery follow-up](docs/archive/releases/RECOVERY_FOLLOWUP_2026_10_25.md) records the subsequent defects, corrections and remaining limits.

## Everyday workflow

```text
Read brief and requirements -> inspect the accepted checkpoint -> reserve a scoped edit
  -> execute once in the selected backend -> save and independently verify
  -> publish the checked result or retain the rejection -> write the next handoff
  -> submit stage evidence -> advance autonomously or wait for owner approval
```

For a background project based on an existing file, first save an owned `.blend` and observe it with `python -m dcc_harness observe SAVED.blend --blender PATH --output-dir NEW_FOLDER`. This opens the file in a fresh background Blender, never saves it, and reports `READY` or the issues to fix. If the scene lacks stable harness identities, use [initial scene adoption](docs/guides/SCENE_ADOPTION.md): `adopt-preview` lists proposed assignments, then `adopt-apply` writes and independently observes a new file. Existing IDs are preserved; ambiguous identities block adoption. See the [everyday workflow](docs/guides/EVERYDAY_WORKFLOW.md) for preparation and exact edit commands.

Example commands below assume you have prepared your own baseline, observation, brief, decisions, and handoff files. They are not bundled demo files.

```sh
python -m dcc_harness start ./my-project/state --checkpoint ./my-project/baseline.blend --observation ./my-project/baseline.json --brief-file ./my-project/BRIEF.md --decisions ./my-project/decisions.json --handoff ./my-project/CONTINUE.md
python -m dcc_harness brief ./my-project/state
python -m dcc_harness resume ./my-project/state
python -m dcc_harness review ./my-project/state
```

| Command | Purpose |
|---|---|
| `run-create` / `run-status` | Select immutable autonomous or approval-gated policy and inspect the run's stages, budgets and operations |
| `run-execute` / `run-submit` | Execute/check/publish one operation, then submit stage evidence through the shared service |
| `live-attach` / `live-refresh` | Pair an explicitly selected open scene with a new managed project; import or reconnect measured external state |
| `live-execute` / `live-status` / `live-reconcile` | Execute a bounded live operation, inspect its retained outcome and explicitly reconcile uncertain state |
| `capability-*` / `recipe-*` / `run-operation` | Discover, qualify and select add-on recipes, then execute a typed operation in either backend |
| `run-cancel` / `run-reconcile` | Stop owned execution and resolve retained attempts without replaying scripts |
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

If acknowledgement is lost, inspect the retained operation and reconcile uncertain state before sending another write. Edits through an unrelated raw-write MCP endpoint are outside the reservation mechanism. Use one native writer and preserve the accepted file.

For an artist edit made outside a reservation, use [external revision review](docs/guides/EXTERNAL_REVISIONS.md). It requires a separate saved candidate, fresh observation, explicit change contract, handoff and decision updates. With `--blender`, textures referenced beside the candidate are packed into an owned copy first. The workflow preserves existing history and records caller-supplied review provenance; it does not settle a pending native operation.

[Structured feedback and environment stages](docs/guides/STRUCTURED_FEEDBACK.md) are optional. Notes keep their checkpoint, object, and view anchors across sessions; implementation claims, verification, and artist acceptance remain separate records. A pinned seven-stage workflow routes the existing skills and requires current evidence before a stage completes. Coordination adds no background agent.

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

The earlier v0.23.0 follow-up passed its frozen local gate on Blender 5.1.1 and Python 3.11.9 on Windows. Its hosted CI also passed, but a subsequent review found recovery deadlocks outside that coverage. Those historical results do not establish general artist-scene readiness. The [recovery follow-up](docs/archive/releases/RECOVERY_FOLLOWUP_2026_10_25.md) tracks the new fixes and their bounded verification. The earlier measured results were:

| Verification | Result |
|---|---|
| Source and clean-installed test suites | 688 tests each: source 686 passed / two skips; installed 685 passed / three skips |
| Maintained release gates | All 22 passed against the frozen source and installed wheel |
| Open-scene execution | All 27 live scenarios, dirty-image preservation and populated/textured transport recovery passed |
| Add-on capabilities | All five groups passed: profiles, nine-recipe onboarding (eight qualified; deliberate poll refusal), routing, revisions and stdio; 16 focused native review checks also passed; both live routing modes now verify missing-ack recovery, fresh-controller receipts, reuse and required submission |
| Workflow/backend combinations | Autonomous and approval-gated modes passed in background and live Blender |
| Distribution | Wheel/source-archive parity, installed entry points and standalone bridge parity passed; final documentation package retained identical qualified runtime/bridge bytes |

The final8 gate also verifies durable capability recovery after a caught final-acknowledgment failure. An atomic recovery record preserves the original failure while fresh controllers validate the recovered receipt without redispatch or checkpoint republication. Checked relative, parent-component and Windows case path aliases identify the same receipt; wrong locations, hashes and reparse points still refuse.

The historical P22 final review found three Important issues: artist-policy downgrade, missing owner CLI confirmation and rejected native node-group names. All three were fixed with five failing-before/passing-after regressions and renewed native qualification. Telemetry and activity recording remain absent from the bundled MCP.

The [follow-up ledger](docs/archive/releases/EXTERNAL_REVIEW_0_23_RESULTS.md) records the current source/installed counts, skip reasons, retained failures, package proof, warnings and unresolved historical preference incident. The two source skips require unavailable Windows symlink privileges; the installed suite additionally skips a source-build regression without the declared build backend. The separate actual-sdist/rebuilt-wheel gate passed. Native logs retain a `Material.use_nodes` deprecation and an accept-loop shutdown `WinError 10038` before normal quit; dependency warnings are also retained.

See [add-on evidence and limits](docs/archive/releases/ADDON_CAPABILITIES_RESULTS.md), [final review and decisions](docs/archive/releases/ADDON_CAPABILITIES_REVIEW.md), and [live qualification](docs/archive/releases/LIVE_EXECUTION_RESULTS.md). These results use owned disposable scenes and synthetic providers; they do not establish compatibility or artistic superiority for arbitrary third-party add-ons. The [changelog](CHANGELOG.md) links historical release evidence, and the [scripts index](scripts/README.md) lists reproducible qualification commands.

The [0.5.0 report](docs/archive/releases/FEEDBACK_0_5_0_RESULTS.md) covers feedback retention, evidence binding, and native revision tests. Its native exercise completed all seven workflow stages on a synthetic micro-scene. The first fresh agent exposed a missing view-definition artifact; the corrected package retains actual settings alongside their digest. In the corrected sealed trial, an independent reviewer verified three notes and left the visual note uncertain. These results test continuity mechanisms, not visual-quality improvement.

The comparisons so far have **not established a general visual-quality or long-horizon advantage** for the harness:

- In the short comparison, six independent builds and six fresh revisions all passed technical checks. Both artist-preferred entries used plain MCP.
- In the longer comparison, sixteen fresh sessions produced fourteen native-check passes and two incomplete stages. Plain MCP completed 8/8 stages and the harness 6/8.
- A realistic held-out comparison was interrupted after one partial build.

[Short comparison](docs/archive/studies/BLIND_RESULTS.md) | [Longer comparison](docs/archive/studies/CONTINUITY_RESULTS.md) | [Realistic comparison](docs/studies/REALISM_COMPARISON.md)

The harness's own overhead has improved. On the same one-parameter revision, a fresh agent took 8 to 10 minutes on 0.5.1 and 0.6.0 and 3 minutes on 0.7.0, starting its edit after 51 seconds instead of 4 to 5 minutes ([report](docs/archive/releases/GUIDANCE_0_7_0_RESULTS.md)). On 0.9.0, two fresh agents each fixed a bench on sloping ground on the first attempt without repeating a failed whole-bench move ([report](docs/archive/releases/RELATIONS_0_9_0_RESULTS.md)). On 0.13.0, a fresh agent continuing the 1,289-object production garden found and answered all three open notes in 32 minutes ([E5 results](docs/studies/E5_CONTINUATION_RESULTS.md)). On 0.16.0, fresh agents handled all six known failure situations correctly: a lost acknowledgement, a stale image, a shared material, a missing view definition, an artist-saved revision and a conflicting late request ([P5 results](docs/studies/P5_SKILL_REGRESSIONS.md)). These are single runs, not a measured advantage over plain MCP.

Current boundaries:

- Whole-scene checkpoint validation still refuses material node groups, unsupported Geometry Nodes setups, empty material slots and missing textures. An unrelated unsupported object can therefore block a capability. Supporting realistic node groups is the next priority; this recovery fix does not expand observation coverage.
- The follow-up review also reports modifier-panel state affecting effect reuse, mutable provider-call provenance, incomplete declared dependencies, inconsistent cancellation markers, non-atomic outcome writes and self-attributed network review. These remain outside the recovery correction; add-on receipts must not be treated as proof against hostile adapters.
- Managed execution enforces reservations, verification, publication and stage policy. It is not a native sandbox, an unconditional exactly-once guarantee, an external-write interceptor or an unattended agent scheduler.
- Windows deep Python evidence and recipe-bundle I/O are qualified at retained paths. Long native Blender `.blend`/asset paths remain unsupported; deep provider discovery/import remains unqualified.
- Real add-ons require provider-specific qualification. Managed recipes initially cover measured MESH cases and qualified engines/contexts; arbitrary custom properties and GUI-only providers without independent background verification remain unsupported. Provider-dependent preview/recovery beyond the retained fixtures needs additional native proof.
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
