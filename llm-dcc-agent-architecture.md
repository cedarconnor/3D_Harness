# LLM-Driven Blender / Unreal: Architecture Notes

Research digest, 2026-10-03. Covers Mixar (open-source Blender fork), the 2026 Blender/C4D/UE MCP landscape, and research code, filtered for three goals:

1. **Formalize the method** — modeling, texturing, and material workflows that stay consistent across context compactions and agent handoffs.
2. **Self-evaluation** — ways for the agent to check its own work deterministically, not just by looking at a screenshot.
3. **Long-horizon orchestration** — plans that survive many turns and multiple agents.

Plus a section on everything else that measurably improves outcomes.

---

## 0. The core thesis

Every open-source DCC MCP today is a *tool surface*: N functions the LLM can call. None of them is a *harness*. The things that actually move outcome quality live one layer up and one layer down from the tool surface:

| Layer | What it does | Who has it |
|---|---|---|
| **Workflow / profile layer** (above tools) | Encodes the *method*: stages, checkpoints, budgets, which tools are visible when | claude-3d-harness (files), Mixar (backend LangGraph modes), 3D-Agent (closed) |
| **Tool surface** | The MCP functions | Everyone |
| **Execution middleware** (below tools) | Sandbox, fenced/idempotent envelopes, diff-based results, op history, scene graph | Mixar (open but fork-bound), dcc-mcp-core (host dispatch only) |
| **Verification tools** | Deterministic asserts / measures / export validation | StraySpark (closed), BlenderAlchemy (research) |

Nobody open-source has all four. The gap is assembly, not research.

---

## 1. Formalizing the method so it survives compaction

The problem: after a context compaction (or a handoff to a fresh agent), the LLM loses *how* it was building — naming conventions, the modifier stack order it had settled on, the UV strategy, the material node layout, what it had decided not to do. It then re-derives a slightly different method and the asset becomes inconsistent.

The fix is to move method out of context and into **artifacts the agent reads back on every turn**. Four patterns, from four sources:

### 1.1 Workflow + profile files (claude-3d-harness)

Repo: https://github.com/MAX-786/claude-3d-harness

Three YAML layers:

- **`registry/capabilities.yaml`, `skills.yaml`** — route each *capability* ("bevel hard edges", "studio three-point light") to exactly one skill implementation, with fallbacks. Resolves name collisions across skill libraries.
- **Workflows** — job types (`modeling`, `product`, `photography`, `animation`, `environment`, `cinematic`), each an ordered list of **stages with checkpoints**. A stage can't be skipped; a checkpoint is a concrete deliverable (a render, a poly count, a UV island count).
- **Profiles** — `fast` / `standard` / `cinematic` scale effort: which stages run, iteration caps, render budget.

Jobs write a report to `output/<date>-<job>/` and lessons to `notes/lessons.md`, which is injected into the next job's load plan.

**Why it survives compaction:** the method is in files the agent is instructed to re-read at every stage boundary. Context can be dropped; the stage list and the lessons file can't.

**Adapt for your pipeline:** write workflow files for your actual job types — `hero-prop`, `set-dressing-batch`, `pbr-material-from-reference`, `dome-env-blockout` — each with the stage order *you* would use. The LLM is then executing your method rather than inventing one.

### 1.2 Mode-filtered tool sets (Mixar backend)

Mixar's LangGraph orchestrator has ~12 **workflow modes** (`MODELING`, `TEXTURING`, `RIGGING`, `UV_UNWRAP`, `SCENE`, `LAYER_PAINTING`, …). The mode filters which of the 200+ tools the LLM can see. A rigging lane is *prompted to always use the auto-rig tool and never hand-build armatures unless asked*.

**Why it matters:** tool visibility is method enforcement. If the agent is in TEXTURING mode it cannot wander into remodeling. This is cheap to implement in any MCP server: a `set_mode(mode)` tool that changes what `tools/list` returns.

### 1.3 Provider-neutral manifests (Mixar `director/core/manifest.py`)

```python
SCHEMA_ID = "mixar.camera_direction.v1"
# shot: {id, name, version, scene, camera, prompt, guidance_strength}
# timeline: {frame_start, frame_end, fps}
# beats[]: {id, index, frame, time_seconds, image_name,
#           camera: {location, rotation_quaternion, projection, lens_mm,
#                    ortho_scale, sensor_mm, sensor_fit, shift}}
```

This is a *versioned, renderer-agnostic description of intent*. The agent writes the manifest; a thin adapter turns it into Blender cameras, or UE CineCamera actors, or a ComfyUI camera-conditioning sequence.

**Generalize:** define the same thing for your other domains —

- `asset_spec.v1` — name, category, target tri budget, LOD count, pivot convention, scale unit, UV strategy (`single_udim | multi_udim | atlas`), texel density target, material slots, export format and axis convention.
- `material_spec.v1` — PBR channel list, resolution per channel, which channels are procedural vs painted vs generated, source references, colorspace per texture.
- `scene_spec.v1` — collection hierarchy, naming regex, which objects are instanced, render passes required.

The agent's first action on any job is to **write or read the spec**. Every later turn starts by reading it. Compaction loses the conversation; it doesn't lose the spec file.

### 1.4 Operation history as agent-readable memory (Mixar `operation_history`)

```python
@dataclass
class OperationRecord:
    source: str            # "agent" | "user"
    kind: str              # operation | checkpoint | …
    category: str          # modeling | material | uv | …
    session_id, instance_id, request_id, tool_name, op_idname, label
    params: dict
    success: bool
    error: Optional[str]
    affected: dict         # created / modified / deleted object names
    scene_delta: dict      # before/after snapshot diff
    script_file: Optional[str]
    seq, id, ts
```

Appended to `operations.jsonl` with the full script saved to `scripts/`. Manual user ops are captured too (depsgraph handler → quiet window → snapshot diff). The agent has a `run_tool("operation_history", …)` to query it. Pruned after 15 days.

**Why it survives compaction:** the agent can ask "what did I do to `Hero_Chair` in the last 40 operations" and get the actual scripts back — including what the *user* changed by hand while the agent wasn't looking. This is the single biggest thing missing from every MCP in the landscape.

**Porting:** `record.py` and `store.py` are pure Python. The capture side needs a per-DCC hook: Blender `bpy.app.handlers.depsgraph_update_post`; UE `unreal.EditorActorSubsystem` delegates + `unreal.register_slate_post_tick_callback`; C4D `CoreMessage(EVMSG_CHANGE)`.

### 1.5 Compaction-resilient turn protocol (synthesis)

Combine the above into a protocol the agent follows at every turn boundary:

```
on_turn_start:
  spec      = read(job/asset_spec.json)
  workflow  = read(workflows/<job.type>.yaml)
  stage     = spec.current_stage
  lessons   = read(notes/lessons.md)
  recent    = op_history.query(last=30, object=spec.focus_object)
  graph     = scene_graph.summary()
  set_mode(workflow.stages[stage].mode)

on_stage_complete:
  run checkpoint asserts for stage          # §2
  write op_history checkpoint record
  spec.current_stage += 1 ; write(spec)
  append lessons if any assert failed and was fixed
```

The agent never has to *remember* the method; it re-reads it. Cost is a few hundred tokens per turn.

---

## 2. Self-evaluation: deterministic before visual

Screenshots are the default verification everywhere (Blender Lab, ahujasid, Mixar's `render_viewport`). Screenshots are necessary but weak: VLMs miss flipped normals, non-manifold edges, overlapping UVs, 0.001-unit scale errors, and missing texture files. The agents that produce clean output put **deterministic checks first** and vision second.

### 2.1 Diff-based result shape (Mixar `executor_result.py`)

Every tool execution returns:

```json
{
  "success": true,
  "...__RESULT__ keys flattened...",
  "output": "<stdout+stderr>",
  "created_objects": ["Chair_Leg.003"],
  "modified_objects": ["Chair_Seat"],
  "deleted_objects": [],
  "error": null,
  "traceback": null
}
```

The created/modified/deleted lists come from a **before/after snapshot diff**, not from the script self-reporting. The LLM sees what *actually* changed. If it asked for one object and three appeared, it knows immediately.

Implement in any DCC: snapshot `{name: (type, hash(transform, vertex_count, material_slots))}` before exec, diff after.

### 2.2 Assertion tools (StraySpark pattern — closed source, reimplement)

StraySpark ships `assert_scene`, `measure`, `verify_export`, `check_asset_ready`. The design is the useful part:

| Tool | Checks |
|---|---|
| `assert_scene(rules)` | object exists / count / parent / collection / naming regex / transform within tolerance / modifier stack order |
| `measure(object)` | bbox dims, tri/quad/ngon count, non-manifold edges, loose verts, inverted normals, UV island count, UV overlap %, texel density, material slot count, empty slots |
| `verify_export(path, format)` | re-import the exported file headless, compare counts/bounds/materials against the source |
| `check_asset_ready(object, spec)` | runs the spec's acceptance criteria (tri budget, LODs, pivot, scale, UDIMs, no missing textures) |

Each returns pass/fail per rule plus the measured value. The LLM gets `{"rule": "tri_count <= 20000", "actual": 23410, "pass": false}` instead of a picture.

**Implementation note:** `measure` is ~150 lines of `bmesh` in Blender; UE equivalent uses `unreal.StaticMesh.get_num_triangles`, `EditorStaticMeshLibrary`, and the `MeshDescription` API.

### 2.3 Visual verification done properly (BlenderAlchemy)

Repo: https://github.com/ianhuang0630/BlenderAlchemyOfficial (ECCV 2024)

Pattern: for an *edit* task, the VLM is given target reference + current render + **a set of candidate edits rendered side by side**, and picks the one closest to the target. Then iterates. It is a tournament, not a single-shot "does this look right."

Transferable rules:

- Always render from **fixed, named camera positions** stored in the spec (front/side/top/three-quarter). Otherwise the VLM compares apples to oranges across turns.
- Render **before and after** for every stage and diff them (pixel diff mask + VLM description of what changed).
- For materials: render a **lookdev turntable on a standard shader ball / Cornell-style stage**, not in the hero scene. Lighting must be constant across comparisons.
- Ask the VLM narrow questions ("are there visible seams on the backrest?") not open ones ("critique this").

### 2.4 LL3M critic/verifier split

Paper: https://arxiv.org/abs/2508.08228

Multi-agent code-based asset generation: planner → coder → **critic** (reads code + render, proposes fixes) → **verifier** (checks the fix actually landed). Key finding: separating "propose fix" from "confirm fix" measurably reduces regressions, because the critic is biased toward believing its own proposal worked.

For you: the agent that checks a stage checkpoint should **not** be the agent that built it. Spawn a verifier sub-agent with only read-only tools (`measure`, `assert_scene`, `render_viewport`, `scene_graph`) and the spec.

### 2.5 Checkpoint matrix (synthesis)

Per workflow stage, define which checks gate progression:

| Stage | Deterministic | Visual |
|---|---|---|
| Blockout | bbox vs spec ±5%, object count, naming regex, pivot at origin/base | three-quarter render vs reference silhouette |
| Hi-poly | manifold, no loose geo, modifier stack matches spec, tri count ≤ budget | matcap render, normal-map-style shading check |
| Retopo / LOD | quad % ≥ target, LOD tri ratios, no ngons on deform regions | wireframe over shaded |
| UV | island count, overlap 0% (or allowed mirrored), texel density ±10%, UDIM tile assignment | UV checker render |
| Material | every slot assigned, no missing images, colorspace correct per channel, roughness/metal in [0,1] | shader-ball turntable, 3 lighting setups |
| Export | `verify_export` re-import round-trip, axis convention, scale 1.0 | re-imported render matches source render |

---

## 3. Long-horizon orchestration across agents

### 3.1 Fenced, idempotent execution (Mixar `common/agent_execution/request.py`)

```python
@dataclass
class ExecutionEnvelope:
    protocol_version, run_id, session_id, turn_epoch
    task_id, task_generation, attempt
    fence_token          # reject stale writers
    operation_id         # idempotency key
    payload_hash         # detect tampered/replayed scripts
    execution_target     # which scene/instance
    document_id, document_epoch   # reject if scene changed under you
    scene_id, snapshot_id
    deadline
```

Every tool call carries this. The executor rejects a script if `document_epoch` is behind the live scene (someone else edited), if `fence_token` belongs to a superseded agent, or if `operation_id` was already applied. This is what makes **multiple agents on one scene** safe, and what makes **retry after a dropped connection** safe (never re-POST a lost stream; re-attach and replay by `seq`).

Without this, two agents editing the same scene will silently clobber each other and the LLM won't know.

### 3.2 One scene per agent, lanes per tab (Mixar `script_lanes.py`, `agent_scene_strip`)

> One FIFO per scene tab (chat session), served round-robin one script per tick: a long build in one tab delays another tab's script by at most the script executing right now.

Mixar's parallelism model: **each agent owns a Blender scene**; scripts are queued per-scene and executed round-robin, one per main-thread tick. A bottom-docked strip renders live tiles of every non-active scene so the human can monitor N agents without switching.

Blender's scene datablock is the natural isolation unit (shared `bpy.data`, separate object sets). In UE the equivalent is **one Level per agent** with a persistent master; or one World Partition cell. Merge via `bpy.ops.object.make_links_scene` / Level streaming at the end.

### 3.3 Plan-as-file, not plan-in-context

Both claude-3d-harness and Mixar's `addon_project` (transactional patches with `stage_patch → run_checks → commit_patch → rollback`) put long-horizon state in files with explicit transitions. The pattern for a multi-agent asset job:

```
job/
  spec.json            # §1.3 — the contract
  plan.md              # stages, owner agent, status, blocking deps
  stages/
    01-blockout/   {report.md, before.png, after.png, asserts.json}
    02-hipoly/     …
  lessons.md           # appended on every failed→fixed assert
  operations.jsonl     # §1.4
```

An orchestrator agent only reads `plan.md` + `asserts.json`; it never sees the worker's conversation. Worker agents get `spec.json` + their stage's workflow entry + `lessons.md`. This is how you keep the orchestrator's context small over a 200-step job.

### 3.4 Skill-first routing (dcc-mcp-core)

Repo: https://github.com/dcc-mcp (Rust core + Python adapters for Maya/Blender/Houdini/UE/Max/Unity)

"Skills" are versioned, typed tool packages separate from the host adapter. The adapter knows how to execute on the main thread; the skill knows the studio method. This is the right factoring for Blender + UE in one pipeline: one `asset_spec` skill, two adapters.

### 3.5 Lessons loop (claude-3d-harness)

Every job appends to `notes/lessons.md`; the next job's load plan includes it. Keep lessons **terse and conditional**: "When bevel modifier precedes mirror, seam appears at X=0 → mirror first." Prune lessons that stop firing.

---

## 4. Execution safety (prerequisite for unattended runs)

If agents run for hours without a human watching, `exec()` of LLM-written Python needs guardrails. The landscape:

| Project | Exec policy |
|---|---|
| Blender Lab (official) | Unguarded; "use a VM" |
| ahujasid mcp-for-blender | On by default; opt-in safe mode blocks file I/O / subprocess / network |
| StraySpark | Denied by default; read/write path jails; audit log |
| Mixar | AST validator + restricted builtins + module allowlist + import hook + undo checkpoint per turn |

Mixar's sandbox (`space_mixie_chat/core/sandbox_*.py`, pure Python, portable) does:

- `sandbox_validator.py` — AST walk rejecting `__subclasses__`, `__globals__`, `__bases__`, `__mro__`, `__code__`, and attribute-string equivalents.
- `sandbox_builtins.py` — restricted builtins; `open`, `tempfile`, `base64`, `urllib` are wrappers with path jails.
- `safe_module()` — wraps allowed modules so `bpy.utils._os` style cross-package hops fail.
- `__import__` hook — allowlist (`numpy`, `mathutils`, `bmesh`, `bpy_extras`, project modules).
- `sandbox_transform.py` — AST rewrite snapshotting collection iterations (mutating `bpy.data.objects` while iterating is the #1 LLM crash).
- Handler cleanup after each script, exempting known-good handlers by object identity.
- Undo checkpoint per turn → `rollback` is one op.

Swap the namespace allowlist for `unreal`/`c4d` and this is DCC-neutral.

---

## 5. Other things in the landscape that improve outcomes

### 5.1 Live API introspection
ahujasid's `bpy_api_lookup` and StraySpark's offline version-matched index. LLMs hallucinate bpy signatures constantly (especially across 4.x→5.x). Give the agent a `lookup_api(path)` tool that returns the real signature + docstring from the running process. Trivial to build (`inspect` + `bpy.types.X.bl_rna`); large effect on first-try success.

### 5.2 Compact scene graph (Mixar `scene_graph`)
```json
{"schema": "mixar.scene_graph", "version": 5,
 "nodes": [{"id": "Chair", "type": "MESH", "coll": "Props", "root": true}, …],
 "layers": {"hierarchy": {"edges": [[0, 1, 1], …], "legend": {"1": "parent_of"}}}}
```
Tools: `roots / children / descendants / ancestors / describe_object / summary`. Lazy — depsgraph marks dirty, rebuilt on query. ~500 lines, ~50 of them bpy. Far cheaper in tokens than dumping `bpy.data.objects`.

### 5.3 Scribble-to-reference (Mixar `scribble_mark`)
User draws on the viewport; gestures are classified, projected, and resolved to **object/vertex references** that ride with the prompt. "Fix *this* seam" becomes `{"marks": [{"object": "Backrest", "verts": [1021, 1022, …]}]}`. The gesture/payload code is pure Python. Worth building for review passes.

### 5.4 Agent-callable generation queue (Mixar `job_queue`)
State machine `PENDING → RUNNING_SUBMIT → RUNNING_POLL → RUNNING_DOWNLOAD → SUCCESS | FAILED | CANCELLED | PAUSED_AUTH`, reconciled by push + periodic sync. Point it at ComfyUI (`/prompt`, `/history`, websocket) instead of Hunyuan-via-Mixar. The agent fires generation as a tool, gets a receipt, and keeps working; result import is a separate op with its own op_history record.

### 5.5 Schema-driven parameters (Mixar `generation_params`)
UI and payload built from a service's parameter schema at runtime (`visible_if`, `order`, `group`). Maps directly onto ComfyUI workflow inputs: expose each saved workflow's inputs as a typed schema, and the agent gets correct param names without a client release.

### 5.6 Reference-based reconstruction skill
https://github.com/Evan1108-Coder/blender-cinematic-modeling-skill — Claude/Codex skill for building from reference images with visual verification and perf measurement. Useful as a worked example of a stage-based skill file.

### 5.7 Instance discovery
marble810/blender-mcp-connect and Mixar's `mcp_bridge/discovery` both solve "which of the three running Blenders do I mean" via JSON lease files + dynamic ports. Needed the moment you run one agent per instance.

### 5.8 First-party MCPs to target rather than replace
- **Blender Lab MCP** (Blender 5.1+, projects.blender.org/lab/blender_mcp, mirror https://github.com/leolee9086/blender_mcp): 26 tools, headless CLI variants, bundled API docs. Build your middleware as an add-on that *extends* this rather than a parallel server.
- **Cinema 4D 2026.4 MCP** (Maxon, built-in, undo-stack integrated, Python escape hatch).
- **UE**: no first-party yet. https://github.com/sam-david/unreal-mcp (127 tools, Remote Control + editor Python, no C++ plugin) is the most complete base.

---

## 6. Recommended build (minimum viable harness)

Priority order, each independently useful:

1. **`asset_spec.v1` + `material_spec.v1` JSON schemas** and the turn-start read protocol (§1.3, §1.5). Zero code in the DCC; immediate consistency gain.
2. **`measure` + `assert_scene`** in Blender (bmesh) and UE (MeshDescription). ~300 lines each. Enables §2.5 checkpoint matrix.
3. **Diff-based result wrapper** around `execute_code` (§2.1). ~80 lines per DCC.
4. **`operation_history`** — lift Mixar's `record.py`/`store.py`, write the capture hook per DCC (§1.4).
5. **Workflow YAML + profiles** per job type, cloned from claude-3d-harness's structure (§1.1).
6. **`set_mode` tool-visibility filter** (§1.2).
7. **Verifier sub-agent** with read-only tool set, run at each checkpoint (§2.4).
8. **Sandbox** — lift Mixar's `sandbox_*.py`, swap allowlist (§4). Required before unattended multi-hour runs.
9. **ExecutionEnvelope + fence tokens** (§3.1) — only once you run >1 agent per scene.
10. **ComfyUI job queue adapter** (§5.4).

Host it as a skill package over dcc-mcp-core if you want Maya/Houdini later; otherwise as an add-on extending Blender Lab MCP plus a sam-david/unreal-mcp fork.

---

## 7. Borrowing from software-engineering agent methodology (obra/superpowers)

Repo: https://github.com/obra/superpowers — a process framework for coding agents (brainstorming → spec → plan → subagent execution → review → verify). The DCC projects above are tool surfaces; this is the missing *process* layer, and most of it translates. Adapted skill files are in `dcc-skills/` alongside this doc.

### 7.1 What translates directly

| Superpowers concept | DCC translation | Why it matters |
|---|---|---|
| **Red/green TDD** — no production code without a failing test first | **Assert-first modeling** — write `assert_scene`/`assert_uv`/`assert_material` for the deliverable, run it, watch it FAIL, build, run again → PASS, then `measure` as the refactor gate | Forces acceptance criteria to be written *before* geometry exists. Watching RED fail proves the assert is wired to the right object. Every task's assert becomes a re-runnable regression contract that survives compaction and handoffs. |
| **Spec / Plan / Ledger** — three artifacts with separate authority | `spec.json` (binding, human-approved) / `plan.md` (argues from spec, tasks sized to a reviewer's gate) / `progress.md` (git-ignored ledger; first line names its plan; `Task N: complete` lines) | "After compaction, trust the ledger and git log over your own recollection." Ledger replaces "did I already do the backrest?" with a file read. |
| **`Interfaces: Consumes / Produces`** per task | "Consumes: `Chair_Frame` exists, pivot at base, bbox z ∈ [0,0.45]. Produces: `Chair_Seat` parented to it, 1 slot `M_Chair_Wood`, ≤1200 tris, manifold." | Lets a fresh implementer who sees *only its task* build correctly; enables parallel workers in separate scenes. |
| **Rulings, not stalls** — `Ruling: <decision> — <why> — <cost if wrong>` | Same line, same ledger | Long autonomous runs die when an agent parks on a question. Only four stop conditions: irreversible op, security/credits, side effect outside the job scene, plan so broken every path is a guess. |
| **Controller never implements; implementer never reviews** | Controller dispatches fresh implementer per task → fresh reviewer sees *only* brief + report + `scene_delta` + `measure` + fixed-camera before/after renders → 5-round fix cap with model escalation at round 4 → one whole-asset review | LL3M's critic/verifier split, operationalized. Reviewer context stays small and uncontaminated. |
| **Status contract** — `DONE \| DONE_WITH_CONCERNS \| BLOCKED \| NEEDS_CONTEXT`, <15 lines, detail in report file | Identical | Keeps the orchestrator's context alive over 50+ tasks. "Never silently produce work you're unsure about." |
| **Verification before completion** — "if you haven't run it in this message you can't claim it" | Claims→evidence table: "clean" ⇒ `measure` 0/0/0; "textures applied" ⇒ `assert_material` 0 missing; "export works" ⇒ `verify_export` round-trip; "agent done" ⇒ `scene_delta` matches `Produces` | Stops "looks right in the render" from counting as verification. |
| **Worktrees** — isolate each plan; never work on main without consent | Scene-per-job (Blender `scenes.new`) / level-per-job (UE); never edit the master scene directly | Same isolation rule, same merge-at-end step (link into master / mark library asset / discard). |
| **Model selection** — cheapest model that can do the role; final review on the most capable | Mechanical build tasks → cheap; judgment (silhouette match, lookdev) → standard; whole-asset review and fix round ≥4 → most capable | Cost control for 200-step jobs. |
| **Brainstorming three-path gate** — spike / bounded / architectural, one-way ratchet up | spike = "can GeoNodes do this? throwaway"; bounded = tweak existing asset; architectural = new asset → written spec + plan required | Stops building a hero prop with no spec because it "seemed simple." |
| **Lessons file** fed into next job | `notes/lessons.md`: one conditional line per assert that failed-then-fixed; prune after 10 quiet jobs | Same as claude-3d-harness §1.1. |

### 7.2 What doesn't translate, and the substitute

| Superpowers relies on | Problem in DCC | Substitute |
|---|---|---|
| **Git commits** as diff, rollback, and ledger recovery | `.blend` / `.uasset` are binary; no meaningful diff | `op_history` seq ranges + `scene_delta` (before/after snapshot diff) as the diff; undo checkpoint per task; `snapshot_file("checkpoints/task-N.blend")` when the workflow profile requires |
| **"Delete code written before the test"** | Too expensive for 20 min of sculpt or a 4K bake | Soften: un-asserted work gets asserted *now*, before the next task |
| **Pristine test output** | No analogue | `measure` and render produce no warnings |
| **Systematic debugging's "reproduce"** | "It looks wrong" isn't deterministic | Fixed `REVIEW_*` cameras + same lighting so repro is a stable render pair; narrow VLM questions |
| **Diff file as the reviewer's only view** | Scene can't be read as text | Review package = brief + report + `scene_delta.json` + `measure/*.json` + before/after renders; reviewer forbidden from crawling the scene |

### 7.3 Adapted skill files (in `dcc-skills/`)

- `writing-asset-plans/SKILL.md` — plan template with Objects/Asserts in place of Files/Tests, `Consumes/Produces`, Global Constraints copied from spec, Review Focus, fixed Review Cameras.
- `asset-driven-development/SKILL.md` + `implementer-prompt.md` + `task-reviewer-prompt.md` — controller loop, ledger format, four stop conditions, review package contents, model selection, fix-round cap.
- `assert-first-modeling/SKILL.md` — RED → GREEN → MEASURE with example `assert_scene` / `assert_material` / `assert_uv` rules.
- `verification-before-completion-dcc/SKILL.md` — claims→evidence table for DCC.

These presuppose the §2.2 assert/measure tools and the §1.4 op_history exist; they're the process half, those are the tooling half.

---

## Appendix A — Mixar modules by portability

Repo: https://github.com/Mixar-AI/mixar-app (GPL-3.0; Blender 5.0 fork; agent backend closed). Paths under `src/scripts/mixar/modules/`.

**Lift as-is (pure Python, no bpy, no backend):**
`space_mixie_chat/core/sandbox_*.py` · `common/agent_execution/{request,pump}.py` · `scene_graph/core/traversal.py` + serializer · `operation_history/core/{record,store}.py` · `director/core/{frame_math,interpolation,rotation_curves,camera_moves,handheld,retime,manifest}.py` · `virtual_camera/core/{server,ws_codec,tls_utils,qr_encoder,rig_math}.py` · `context_folder/core/*` · `local_models/core/{relay,server_supervisor,download}.py` · `mcp_bridge/core/{stdio_server,relay,connector,discovery}.py` · `connector/core/protocol.py` (already a UE export sidecar: `/scene`, `/viewport.jpg`, `/export` → USD/FBX/GLB with `-Z`/`Y`)

**Pattern portable, implementation Blender:**
`executor.py` / `main_thread_executor.py` / `script_lanes.py` · `common/job_queue` · `common/generation_params` · `addon_project` · `scribble_mark/core/{gesture,simplify,payload}` · `sculpt_agent/mapping.py`

**Skip:** `workflow`, `agent_viewport_lock`, `byok`, `onboarding`, `plugin_import`, `scene_render`, `paint`, anything touching `SpaceMixie*` or `mixar_*` C++ RNA. `common/` is 43 MB because of 41 MB of `.po` translations.

Not in the repo: the 200+ tool script templates and the LangGraph orchestrator (closed `mixar-backend`).

## Appendix B — Landscape index

| Project | Type | Notable |
|---|---|---|
| [Blender Lab MCP](https://github.com/leolee9086/blender_mcp) (mirror) | Official, Blender 5.1+ | 26 tools, headless CLI, bundled docs, unguarded exec |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Community, 29k★ | `bpy_api_lookup`, safe mode, asset/gen integrations |
| StraySpark Blender MCP | Paid, closed | assert/measure/verify_export, path jails, audit log |
| [MAX-786/claude-3d-harness](https://github.com/MAX-786/claude-3d-harness) | Harness over MCPs | registry/workflows/profiles/lessons |
| [dcc-mcp org](https://github.com/dcc-mcp) | Multi-DCC framework | Rust core + Maya/Blender/Houdini/UE/Max/Unity adapters, skill packages |
| [loonghao/dcc-mcp](https://github.com/loonghao/dcc-mcp), [MooseGoose dcc-mcp-core](https://github.com/MooseGooseConsulting/dcc-mcp-core) | Predecessor / variant | adapter launcher |
| [HurtzDonutStudios/ai-forge-mcp](https://github.com/HurtzDonutStudios/ai-forge-mcp) | Multi-DCC | 565 tools, 16 servers, 50 agent personas |
| [sam-david/unreal-mcp](https://github.com/sam-david/unreal-mcp) | UE | 127 tools, 4 transports, no C++ plugin |
| [FFZackFair92](https://github.com/FFZackFair92/unreal-engine-mcp), [GenOrca](https://github.com/GenOrca/unreal-mcp), [runeape-sats](https://github.com/runeape-sats/unreal-mcp), [radial-hks](https://github.com/radial-hks/MCP-Unreal-Server), [conaman ue4](https://github.com/conaman/unreal-mcp-ue4) | UE | variants |
| [tahooki/unreal-blender-mcp](https://github.com/tahooki/unreal-blender-mcp) | Bridge | Blender↔UE |
| [C4D 2026.4 MCP](https://www.cgchannel.com/2026/09/maxon-releases-cinema-4d-2026-4-with-a-new-mcp-server/) | Official | undo-integrated, Python escape hatch |
| [marble810/blender-mcp-connect](https://github.com/marble810/blender-mcp-connect) | Blender | instance discovery, dynamic ports |
| [jlpschell](https://github.com/jlpschell/blender-mcp-server), [RFingAdam](https://github.com/RFingAdam/mcp-blender), [zorak1103](https://github.com/zorak1103/blender-mcp), [AG064](https://github.com/AG064/blender-mcp), [dhakalnirajan](https://github.com/dhakalnirajan/blender-open-mcp) | Blender | breadth variants |
| [Evan1108 cinematic-modeling-skill](https://github.com/Evan1108-Coder/blender-cinematic-modeling-skill) | Skill | reference-based reconstruction, visual verification |
| [3D-Agent](https://3d-agent.com/blender-mcp) | Closed desktop app | hosted agent, clean-topology claims, Roblox |
| [LL3M](https://arxiv.org/abs/2508.08228) | Research | planner/coder/critic/verifier |
| [BlenderAlchemy](https://github.com/ianhuang0630/BlenderAlchemyOfficial) | Research | VLM tournament edit selection |
| [SceneCraft](https://huggingface.co/papers/2403.01248) | Research | scene-as-code, learned function library |
| [Strayspark comparison](https://www.strayspark.studio/blog/official-blender-mcp-server-comparison-2026) | Article | Lab vs ahujasid vs paid |
