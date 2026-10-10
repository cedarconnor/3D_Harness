# Agent guidance — 0.7.0

Version 0.7.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P9, following its [implementation plan](../plans/P9_AGENT_GUIDANCE.md). It adds three read-only commands that tell an agent where a project stands and exactly what to run next, and a one-page quick reference. A fresh agent on the 0.6.0 comparison task finished in **3 min 1 s**, against 8 min 16 s and 9 min 41 s for the two earlier runs. It reserved its edit after 51 seconds instead of 4 to 5 minutes, and read one runtime source file instead of 10 and 19. This is one run, so it is a directional result, not a measured advantage.

## Delivered

- **`brief PROJECT [--focus ID ...] [--out FILE.md]`** prints Markdown generated from the verified record:
  - where the project stands;
  - the permitted next steps, each with its command filled in with the project path, parent ID, checkpoint path, edit ID, coordination revision and a fresh request ID;
  - each open note's text, acceptance, targets and review view;
  - the stage table;
  - the recorded brief, handoff and decisions, fenced and labelled as records rather than instructions;
  - the rules that do not bend.
- **`next PROJECT`** returns the same steps as JSON (`dcc.next.v1`). Steps come in this order: inspection or finishing of anything unresolved; then reviews of submitted stages and responses; then a new edit; then the responses and submissions that cite it. While anything is unresolved, only the reconciliation steps appear.
- **`requirements PROJECT STAGE`** returns a stage's state, blocking predecessors, review policy, deliverables, required evidence with the fields each needs, the exact `feedback_ids` and unresolved blockers (`dcc.requirements.v1`). Its `skeleton` is a submission ready for `fill-hashes` once its placeholders are replaced.
- **[Agent quick reference](../../guides/AGENT_QUICK_REFERENCE.md).** The exact sequences for an edit, a feedback response and a stage submission, payload examples and common stops. The suite parses every command on the page with the real argument parser and validates its contract and response examples. It also confirms that every error message the page quotes exists in the runtime.
- **The `dcc-harness` skill** now starts with `brief`; the everyday-workflow and structured-feedback guides and the README describe the new commands.
- **Not built: `demo`.** The plan deferred it until orientation was measured, and the measurement below falls under the one-minute threshold.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 283 tests: 281 passed, two Windows symlink-permission skips. 23 tests are new: 19 for the commands, 4 for the quick reference. |
| Installed-wheel suite | 283 tests from a standalone install of the wheel: 277 passed and 6 skipped, the same two plus the four quick-reference tests, which check the source tree's documentation and skip where it is absent |
| Wheel integrity | All 39 runtime and template files byte-identical to the committed sources. SHA-256 `527d5669102bdb5359f18571ca445749201083544c58988e87294a512a8c881f` |
| Native, source and installed | `scripts/qualify_guidance.py` on copies of two retained projects. On the comparison fixture, with open notes and no workflow, `brief` detailed the open note, `next` offered observe, begin-edit and a response, and `requirements` refused plainly. On the October 6 feedback project, whose materials stage a note had reopened, the brief showed materials `needs_review` and delivery blocked by lighting. `requirements` agreed, and `next` offered the reopened note's response and the materials submission. Neither project changed. The printed `observe` and `begin-edit` commands then ran as printed against real Blender; afterwards `next` offered only that edit's `finish-edit`, and `brief` reported `RECONCILE`. |

## Fresh-agent comparison

Packet C repeats the 0.6.0 comparison task: change the shared timber roughness to 0.8 through the reservation workflow, render, publish and record a feedback response. It has the same project, scene, before-views, render tool and `BRIEF.md`, byte for byte, and the same prompt to a fresh agent of the same model. It differs from packet B only in the 0.7.0 runtime, the `dcc-harness` skill, the two guides that mention the new commands, and the added quick reference. The measurements come from the three agents' transcripts by one script (`runs/guidance-0.7.0-2026-10-10/orientation.py`), not from self-reports.

| | A: 0.5.1 | B: 0.6.0 | C: 0.7.0 |
|---|---|---|---|
| Wall time | 8 min 16 s | 9 min 41 s | **3 min 1 s** |
| Tool calls / tokens | 60 / 217k | 62 / 245k | 34 / 115k |
| First `python -m dcc_harness` command | 40 s (`--help`, then `resume`) | 3 min 49 s | 10 s (`brief`) |
| Edit reserved (`begin-edit`) | 4 min 18 s | 5 min 16 s | **51 s** |
| Runtime source files read | 10 | 19 | 1 (a `grep` for the material helper) |
| Outcome | Published sequence 3; response committed; check passed | Same | Same |

I verified packet C's project independently with the installed runtime. Checkpoint 3, `timber-roughness-0.8`, holds Roughness 0.8 on the shared timber material with a passing native check and no failures. The note is `awaiting_verification`, and all three response evidence reports, the contract and the whole and detail renders, pass on recomputation.

**What changed in the agent's behavior.** Agents A and B read every guide and skill, then most of the runtime source, before acting. B paused for 147 seconds after reading before its first command. Agent C read the entry skill and the quick reference, ran `brief` at 10 seconds, and worked from the commands it printed. Later it read two craft skills, one guide section and one runtime helper as specific questions came up. The 0.6.0 report's "about 3 to 3.7 minutes" of orientation was self-reported; the transcripts put the start of real work at 4 min 18 s and 5 min 16 s.

**Limits of the comparison.**
- **One run per arm.** This is directional evidence, not a measured advantage.
- **Bundled treatment.** The commands and the quick reference arrived together, so their effects cannot be separated.
- **Timing.** C ran four days after A and B, on the same model.
- **Before-views.** C noticed that the packet's before-views were rendered from an older checkpoint than the active parent, and rendered the parent itself. A and B had the same packet.

## Implications for the plan

- Orientation is no longer the dominant cost on this task: C spent most of its three minutes on the edit, the render check and the response. `demo` stays unbuilt.
- P10's fixed-view render command is next. All three agents relied on the fixture-specific render tool, and C spent time establishing which checkpoint the provided before-views came from.
- A larger sample on a harder task, such as E5's continuation on the production garden, would test whether the effect holds beyond a one-parameter change.

Local evidence is under `runs/guidance-0.7.0-2026-10-10/`, excluded from Git.

## Limits

- The commands read the saved record only. They do not observe a live editor or judge quality, and suggested commands are not approvals.
- `requirements` gives skeletons; the agent still fills in deliverables, notes and paths.
- The brief is generated on demand. Nothing writes it automatically before a session, because there is no runner (X2).
