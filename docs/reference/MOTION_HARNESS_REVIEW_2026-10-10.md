# Motion design harness review

October 10, 2026. A review of a four-page independent field guide, "Opus 5.5 Motion Design Harness" (October 2026, not an Anthropic publication), for ideas the 3D Harness lacks. The guide pairs a gated prompt for Remotion explainer videos with Mortiflix, an open-source harness by GTKottman (`github.com/GTKottman/mortiflix-oss`) that enforces the same rules in code. Everything below about Mortiflix comes from the guide; the repository itself was not inspected.

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

## Comparison with the 3D Harness at 0.6.0

| Mortiflix | 3D Harness | Gap |
|---|---|---|
| Reviewed files copied out of the session's reach | Evidence frozen with each event; immutable checkpoints | None |
| Every note answered in `pin_changes` | `feedback-respond` per note with a required `change` | None |
| Required checks per review mode; incomplete submissions refused | Stage evidence registry; incomplete submissions retained but cannot complete | None |
| Step ordering and handoff/resume | Stage dependencies, `handoff` evidence and `resume` packets | None |
| `mfx checks <step>` and a `demo` backend | Guides and skills; orientation took about 3 to 3.7 min in the 0.6.0 comparison | **P9** |
| Queued `mfx render` with an ID to wait on | Fixture-specific render tools | **P10** |
| Owner-approved checks learned from caught errors | Fixed evidence registry; unknown checks rejected | **P11** |
| Approval reachable only outside the agent's tool | Caller-attributed roles; an agent can write an artist authority | **P12** |
| Owner questions with defaults; a frame sheet at the final gate | No structured questions; renders reviewed one by one | **P4** |
| Turns, minutes and spend per gate | Elapsed time in trial reports | **M5** |
| Runaway guards and session time limits | No runner | **X2**, deferred |
| Remotion motion pipeline | Not started | **X5**, deferred |

## Not adopted

- **A global taste file.** Taste remains project direction, as the [structured feedback guide](../guides/STRUCTURED_FEEDBACK.md) states. Learned checks (P11) carry only measurable errors across projects. Revisit with a design decision if artist reviews show repeated cross-project preferences.
- **Continuing past failures.** The guide's prompt tells sessions to route around a missing asset or failed render and mark the work unverified. The harness keeps its stop-and-report behavior for failed verification; the trade-off belongs to the unattended runner (X2).
