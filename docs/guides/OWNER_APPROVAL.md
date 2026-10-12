# Owner approval

Since version 0.12.0, an approval that rests on the artist's authority has to come from the artist's own terminal. An agent's request is refused. The decision is [D18](../DESIGN_DECISIONS.md#d18-artist-authority-comes-only-through-the-owners-terminal).

## What needs it

Any payload whose reviewer or authority is the artist:

- a stage completion, for example an approval exported from the [review page](REVIEW_PAGE.md);
- a feedback verification;
- a feedback decision, such as deferring a blocking note;
- reopening a stage;
- binding a workflow, including a binding that relaxes a stage the manifest marks `artist_required`.

Approving a [learned check](LEARNED_CHECKS.md) into a library (`check-approve`) needs the owner too. The prompt shows the rule, its stages, its rationale and the note it came from.

Notes, including those written on the review page, are not approvals. An agent may still import them.

## How to approve

Open a terminal yourself, such as PowerShell from the Start menu, rather than one an agent started. Then run the command the agent hands you, for example:

```powershell
python -m dcc_harness review-import "<project>" "<downloaded export .json>" --page "<review page folder>"
```

The command shows what will be recorded, such as the stage, verdict, finding and answers, and a four-character code:

```text
Record stage.complete as the artist's decision, by Ana.
  verdict: pass
  finding: Direction reads well
  answers: {"finish": "Raw"}
Type 5864 to record this as your decision, or press Enter to cancel:
```

Type the code to approve it. Press Enter, or type anything else, to cancel, and nothing is recorded. Repeating a command that already committed returns `ALREADY_COMMITTED` without asking again.

The receipt records `artistic_acceptance: artist_confirmed` and `owner_approval`, which holds:

- the channel;
- the time;
- your operating-system user name;
- the code.

Records made before 0.12.0 say `artist_declared`. The artist role in those was never checked.

## When it refuses

| Message | Cause |
|---|---|
| `Owner approval is refused inside an agent session (CLAUDECODE is set)` | The command ran inside an agent's shell. The variables checked are `CLAUDECODE`, `AI_AGENT`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, `GEMINI_CLI` and `DCC_HARNESS_AGENT`. |
| `Owner approval needs an interactive terminal` | Input was piped or redirected. |
| `Owner approval not confirmed` | The typed code was wrong or empty. |
| `Owner approval required` | A caller used the Python API without an approval for this exact request. |

## How strong it is

It is a guard, not a wall. It stops an agent from approving its own work through the documented commands, payload files or a page export, whether by accident or casually.

An agent with an unrestricted shell on your account can still get around it:

- remove the variables and fake a terminal;
- construct an approval in Python;
- rewrite the record files and their hashes.

Real separation would mean the approvals are written by a process the agent's account cannot reach, and these sessions do not have that. To keep the guard meaningful, give agents their own sandbox or user account when you can, and tell them never to work around a refusal.
