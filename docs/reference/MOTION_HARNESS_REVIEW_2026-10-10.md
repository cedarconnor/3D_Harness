# Motion design harness review

October 10, 2026. A review of a four-page independent field guide, "Opus 5.5 Motion Design Harness" (October 2026, not an Anthropic publication), for ideas the 3D Harness lacks. The guide pairs a gated prompt for Remotion explainer videos with Mortiflix, an open-source harness by GTKottman (`github.com/GTKottman/mortiflix-oss`) that enforces the same rules in code. The source was then read directly at commit `8c86e83`; [what the code shows](#what-the-code-shows) corrects the guide where they differ.

A requested second source, `voyager.so/blog`, was not reviewed: the local network's security filter blocked it.

## What Mortiflix does

- **Gated pipeline.** A project walks ordered steps (brief, script, style frames, transitions, animatic, build, final). Each step is either reviewed by the owner or internal with checks only. A session works until it has something to review, submits it, writes a handoff and ends; a fresh session resumes from the journal when the owner responds.
- **Owner-only approval in code.** Approval is reachable from the web studio and owner CLI, never from `mfx`, the only tool a session can use. Sessions write to `projects/<id>/`; only Mortiflix writes `state/<id>/`, and submitted files are copied into the record.
- **Submission refusals.** A submission is refused if any check for the step's kind of work is unreported, if a `fixed` or `n/a` result lacks a note, if a note on the last version has no entry in `pin_changes`, if files are missing or outside the working folder, if prerequisite steps are unfinished, or if the review mode's required media are absent. Status lines come from a whitelist.
- **Small agent verb set.** `mfx status` (one sentence for the owner), `mfx render --label … -- <command>` and `mfx render-wait <id>` (one render at a time, studio-wide), `mfx checks <step>` (the checks this step must report), `mfx submit <step> submission.json` and `mfx handoff`.
- **Submission shape.** A plain-words `note`, owner `questions` with choices and a `default`, labelled `items`, one `error_checks` entry per check, and `pin_changes` answering every note with the exact change made.
- **Learned checks.** Each owner note is sorted into error or taste. For every error no check caught, the session proposes a new check; once the owner approves it, every future project runs it. Taste carries across projects in `TASTE.md`.
- **Pipelines are folders.** `pipeline.json` (steps, review modes, checks), `PIPELINE.md` (the craft) and skills. A `demo` backend walks every gate with placeholder work, free and without Claude.
- **Runaway guards.** Two sessions in a row that move nothing forward pause the project, as do eight in a row without a submission or finished step. A session past `maxSessionMinutes` (default 240) is stopped.
- **Measured cost.** The author reports turns, minutes and API list price per gate: a five-second logo sting took two sessions, 12.5 minutes and USD 3.52, with 95% of input tokens read from cache.

## What the code shows

Version 0.1.0. The core source and docs run to about 7,300 lines of Node.js and Markdown, with about 80 tests. The first commit is dated October 5, 2026. Licensed AGPL-3.0: borrow ideas, not code, unless this project adopts a compatible license (it has no license file today).

- **A generated session brief solves orientation.** Before every session, `src/torch.mjs` rewrites the working folder's `CLAUDE.md` from the record: why this session started (derived from the owner's events since the last session), which steps can be worked on now, a table of every step with its state and checks, every unanswered note with its pin location, answered questions, the brief and taste fenced as the owner's words, the latest journal entries, and the full `mfx` command list. The pinned pipeline and skills are recopied each session so they cannot drift. The session's prompt is one line: read `CLAUDE.md` and follow it. This is the most direct answer yet to P9.
- **Checks are self-reported, not executed.** A check in `checks.json` is a title, a plain-language `how` and the kinds of work it applies to. `validateChecks` refuses a submission that omits a check or gives `fixed`/`n/a` without a note, but nothing runs the check: the session declares the result. A repeated error is recorded with `propose-check --same-as`, which increments a `seen` count. The 3D Harness recomputes its contracts natively, so its P11 should keep checks measurable.
- **Owner-only approval is a guard, not a wall.** Owner commands refuse to run when `MFX_TOKEN` is set, which marks a session's environment. The project's own `docs/SECURITY.md` says an unsandboxed session could still edit `state/` with its shell; only the optional bubblewrap sandbox (Linux, `claude-code` backend) hides the record. The guard stops accidental self-approval, which is the realistic first goal for P12.
- **Sessions reach the studio through one narrow channel.** `src/bridge.mjs` serves a private Unix socket with a per-session token for the session's lifetime only; every `mfx` command maps to one gate function, and a refusal returns a sentence the agent can act on, such as which note lacks an answer.
- **Renders.** `src/renderq.mjs` runs one job at a time studio-wide, `render-wait` waits up to 100 s per call, and jobs still running when a session ends are stopped.
- **Blender.** The optional `blender-3d` skill runs the studio's own Blender with a separate profile (`BLENDER_USER_RESOURCES`) and calls the author's toolkits in-process through `mfx3d.py`, without MCP. The Camera toolkit (`GTKottman/Blender-Cam`) reports framing headroom and coverage numerically and writes contact sheets, both relevant to P10 and P4; it was not inspected. Scenes are built from re-runnable scripts. There is no observation, preservation or continuity layer: the gate record covers submissions, not scene state.
- **Windows.** Installation works on Windows; sessions do not yet, according to `docs/WINDOWS.md`.

## Comparison with the 3D Harness at 0.6.0

| Mortiflix | 3D Harness | Gap |
|---|---|---|
| Reviewed files copied out of the session's reach | Evidence frozen with each event; immutable checkpoints | None |
| Every note answered in `pin_changes` | `feedback-respond` per note with a required `change` | None |
| Required checks per review mode; incomplete submissions refused | Stage evidence registry; incomplete submissions retained but cannot complete | None |
| Step ordering and handoff/resume | Stage dependencies, `handoff` evidence and `resume` packets | None |
| A `CLAUDE.md` regenerated from the record each session, `mfx checks <step>` and a `demo` backend | Guides, skills and a JSON `resume` packet; orientation took about 3 to 3.7 min in the 0.6.0 comparison | **P9** |
| Queued `mfx render` with an ID to wait on | Fixture-specific render tools | **P10** |
| Owner-approved checks learned from caught errors, self-reported | Natively recomputed contracts from a fixed registry; unknown checks rejected | **P11** |
| Owner commands refuse inside a session; record hidden only under a Linux sandbox | Caller-attributed roles; an agent can write an artist authority | **P12** |
| Owner questions with defaults; a frame sheet at the final gate | No structured questions; renders reviewed one by one | **P4** |
| Turns, minutes and spend per gate | Elapsed time in trial reports | **M5** |
| Runaway guards and session time limits | No runner | **X2**, deferred |
| Remotion motion pipeline | Not started | **X5**, deferred |

## Not adopted

- **A global taste file.** Taste remains project direction, as the [structured feedback guide](../guides/STRUCTURED_FEEDBACK.md) states. Learned checks (P11) carry only measurable errors across projects. Revisit with a design decision if artist reviews show repeated cross-project preferences.
- **Continuing past failures.** The guide's prompt tells sessions to route around a missing asset or failed render and mark the work unverified. The harness keeps its stop-and-report behavior for failed verification; the trade-off belongs to the unattended runner (X2).
