# P12: Owner approval channel

Plan for [build-plan](../../BUILD_PLAN.md) item P12, written October 10, 2026, at version 0.11.0. Target version: 0.12.0. The decision is [D18](../../DESIGN_DECISIONS.md#d18-artist-authority-comes-only-through-the-owners-terminal).

## Problem

Every role in the coordination record is the caller's claim. An agent can write `reviewer: {role: "artist"}` into a stage review and complete a stage whose policy requires the artist. It can also waive a blocking note with an "artist" decision, or import a review-page export it wrote itself. Nothing distinguishes the artist's decision from the agent's. P11's learned checks need the same distinction: a check the agent proposes must not be approved by the agent.

## Scope

### Which records need the owner

A payload needs an owner approval when it claims the artist's authority:

| Kind | Field |
|---|---|
| `stage.complete` | `review.reviewer.role` |
| `feedback.verify` | `reviewer.role` |
| `feedback.decide` | `authority.role` |
| `stage.reopen` | `authority.role` |
| `workflow.bind` | `binding.authority.role` |

A binding whose `review_policies` relax a stage that the manifest marks `artist_required` must also carry the artist's authority, and so needs the owner too.

Notes (`feedback.add`) and evidence producers stay attributions. A note adds work and cannot accept anything, so an agent may still import the notes from a review page.

### The channel

A new module, `owner.py`, issues an `Approval` for one request, bound to the request hash that `transact` computes. It issues one only when:

- no known agent-session variable is set: `CLAUDECODE`, `AI_AGENT`, `CODEX_SANDBOX`, `GEMINI_CLI` and the harness's own `DCC_HARNESS_AGENT`;
- standard input is an interactive terminal;
- the owner, shown what will be recorded, types a four-character code derived from the request hash.

Each failure stops with a message saying who must run the command and where.

`transact` checks the approval after the replay check, so a committed request still replays without a prompt, and before building. A missing or mismatched approval is refused with `Owner approval required`. The result records `owner_approval`: channel, time, operating-system user and the code. Artist acceptance becomes `artist_confirmed`; records committed before 0.12.0 keep `artist_declared`.

### Commands

- The coordination commands prompt for the owner only when their payload needs one; everything else is unchanged.
- `review-import` asks once, before committing anything, when the export carries a stage review. It imports nothing if the owner does not confirm. Exports with only notes import as before.
- `brief` and `next` tell the agent to hand artist-required stages and notes to the artist through a review page, and never to complete them.

## Qualification

- **Portable tests.**
  - Each kind is refused without an approval, and with an approval for another request.
  - It commits with an approval from a scripted console.
  - The binding relaxation rule.
  - The console refuses agent variables, a non-terminal input and a wrong code.
  - The CLI refuses inside an agent session without prompting, and replays still return `ALREADY_COMMITTED`.
  - A review import with an approval is refused in full, while a notes-only import succeeds.
  - Guidance wording.
- **Native, source and installed.** `scripts/qualify_owner.py`, on a copy of the comparison project with a workflow whose direction stage requires the artist:
  - from this agent session, `stage-complete` and `review-import` with an approval are refused, and the record is unchanged;
  - with the agent variables removed but input piped, they are refused again;
  - an approval from a scripted console commits, and its receipt carries the owner provenance;
  - the notes-only import still commits from the agent session.
  - The review-page qualification is updated to take its approval through the same scripted console.
- **By hand.** The owner runs one approval in their own terminal. I cannot do this from an agent session; if it isn't done, the report says so.

## Strength

This is a guard, not a wall. It stops an agent from approving its own work through the documented commands, payload files or a page export, whether by accident or casually. An agent with an unrestricted shell can still remove the variables and fake a terminal, construct an `Approval` in Python, or rewrite the record and its hashes. A wall needs the owner's records to be written by a process the agent's account cannot reach. These Windows sessions don't have that separation.

## Out of scope

- Signed approvals and per-user keys.
- Approving learned checks. That is P11, which will reuse this channel.
- Owner approval inside the review page itself. The page cannot hold a secret.
