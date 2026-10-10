# P9: Agent guidance

Plan for [build-plan](../BUILD_PLAN.md) item P9, written October 10, 2026, at version 0.6.0. Target version: 0.7.0, because it adds commands.

## Problem

In the 0.6.0 comparison both fresh agents spent about 3 to 3.7 minutes reading skills, guides and runtime source before their first command, and about another minute each writing contract, handoff and response JSON. Native work took seconds ([report](../archive/releases/STEP_COST_0_6_0_RESULTS.md)). Agents learn the workflow from prose, then work out the next command and its arguments from a JSON resume packet.

Mortiflix answers the same question by regenerating the agent's `CLAUDE.md` from the record before every session ([review](../reference/MOTION_HARNESS_REVIEW_2026-10-10.md)). This increment does the equivalent on demand: the runtime tells the agent where the project stands and what exactly to run next, using values from the verified record.

## Scope

### `next`

```text
python -m dcc_harness next PROJECT [--out FILE]
```

Returns `dcc.next.v1`: the verified status, the coordination revision when present, and an ordered list of permitted next steps. Each step has an `id`, a plain reason, and a command with every value the record knows filled in: project path, parent ID, checkpoint path, edit ID, expected revision, submission ID and a fresh request UUID. Values only the agent can know stay as `<placeholders>`.

Rules, in order:

1. A metadata lock, a pending journal operation or a reserved edit without an outcome: only inspection and `finish-edit` steps (with `--reconciled` guidance). No new edit is offered while anything is unresolved.
2. With coordination: stage submissions awaiting review (`stage-complete`, flagged when the stage requires an artist), notes awaiting a response or a fresh response after recheck (`feedback-respond`), notes awaiting verification (`feedback-verify`, by a separate reviewer), and ready stages (`requirements`, then `stage-submit`).
3. Always when ready: observe the active checkpoint and reserve a new edit with `begin-edit`, listing step labels already used.

`next` reads only. It never runs Blender, never commits and never decides that work is acceptable.

### `requirements`

```text
python -m dcc_harness requirements PROJECT STAGE [--out FILE]
```

For a bound environment workflow, returns `dcc.requirements.v1`: the stage's state, predecessors still blocking it, review policy, deliverables, required evidence kinds with the fields each needs, the exact `feedback_ids` a submission must list, unresolved blockers, and a submission skeleton. The skeleton fills the schema, stage, current checkpoint, deliverable keys and feedback IDs, and writes every file reference as `{"path": "<...>"}` ready for `fill-hashes`. A project without a bound workflow, or an unknown stage, fails with a plain message.

### `brief`

```text
python -m dcc_harness brief PROJECT [--focus ID ...] [--out FILE.md]
```

Prints Markdown generated from `resume` plus `next`: where the project stands (status, active checkpoint, counts, recent steps and rejections with their reasons), what to do next with the exact commands, the open feedback and stage table when coordination exists, the project brief and latest handoff, current decisions, and the rules that do not bend (never replay an uncertain write, never edit an accepted file, a numeric pass is not artistic acceptance). The project brief and handoff are fenced and labelled as recorded text, not instructions. `--out` creates the file exclusively, like other receipts.

### Agent quick reference

`docs/guides/AGENT_QUICK_REFERENCE.md`: one page with the exact sequence for the two most frequent tasks, a scoped edit and a feedback response, plus a stage submission, the payload shapes and the common stops and what each means. A test parses every `python -m dcc_harness` line in it with the real argument parser and validates its contract example, so the page fails the suite when the CLI drifts. The `dcc-harness` skill's first instruction becomes: run `brief`.

## Deferred: `demo`

The build plan also lists a `demo` walk on a bundled fixture. It needs a native fixture builder inside the package and Blender at run time. Following the plan's rule to measure orientation before building anything larger, it waits for this increment's measurement. Build it only if orientation stays above about one minute.

## Qualification

- **Portable tests.** `next` on a ready project, with a reserved edit, with a metadata lock, with coordination notes in each status, and with stages ready and awaiting review. `requirements` for a ready stage, a blocked stage, delivery (all notes), no binding and an unknown stage; its skeleton, once file references are hashed, passes `stage-submit` validation. `brief` contains the active ID, next commands, fenced brief and handoff, and refuses an existing `--out`. The quick-reference test described above.
- **Native.** Run `brief`, `next` and `requirements` against the prepared feedback fixture from the 0.6.0 comparison, source and installed.
- **Comparison.** Rebuild the 0.6.0 comparison packet with the 0.7.0 runtime, skills and guides, and run one fresh agent on the same task. Record orientation time before the first command (from the transcript and self-reported), total time, tool calls and tokens, against the 0.6.0 runs' roughly 3 to 3.7 minutes and 9 min 41 s. One run is directional.

## Out of scope

- Writing payloads automatically. `requirements` gives skeletons; the agent still fills deliverables, notes and paths.
- Owner-only approval (P12) and learned checks (P11).
- A per-session file written automatically before an agent starts. There is no runner (X2); `brief` is on demand.
