# Owner approval channel — 0.12.0

Version 0.12.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P12, following its [implementation plan](../plans/P12_OWNER_APPROVAL.md) and decision [D18](../../DESIGN_DECISIONS.md#d18-artist-authority-comes-only-through-the-owners-terminal).

Before this version, every role in the coordination record was the caller's claim. An agent could write `role: "artist"` and complete a stage that needed the artist, waive a blocking note, or import a review-page approval it wrote itself. Now an artist's authority is recorded only when the owner confirms that exact request at an interactive terminal outside an agent session.

## Delivered

- **Which records.** A payload needs the owner when its reviewer or authority is the artist:
  - `stage.complete`, `feedback.verify`, `feedback.decide`, `stage.reopen` and `workflow.bind`;
  - a binding that relaxes a stage the manifest marks `artist_required`, which must also carry the artist's authority.

  Notes and evidence producers stay attributions, so an agent can still import a page's notes.
- **The channel, `owner.py`.** `confirm` refuses when `CLAUDECODE`, `AI_AGENT`, `CODEX_SANDBOX`, `GEMINI_CLI` or `DCC_HARNESS_AGENT` is set, and when standard input is not a terminal. It shows what will be recorded and requires a four-character code taken from the request hash. It then returns an approval bound to that hash.
- **Where it is checked.** `transact` checks after the replay check and before building. A missing approval, or one for another request, is refused with `Owner approval required`. The receipt adds `owner_approval` (channel, time, operating-system user, code) and `artistic_acceptance: artist_confirmed`. Earlier records keep `artist_declared`.
- **Commands.**
  - The coordination commands ask only when their payload claims the artist.
  - `review-import` asks once before committing anything, and imports nothing, notes included, if the owner does not confirm.
  - A committed request replays without asking.
  - `brief` and `next` tell agents to hand an artist-required stage to the artist through a review page.
- **Docs.** An [owner approval guide](../../guides/OWNER_APPROVAL.md) for the artist; the quick reference, review page and structured feedback guides; the `dcc-harness` skill and the README.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 365 tests: 363 passed, two Windows symlink-permission skips. 9 tests are new: 8 for the owner channel and 1 for an agent-session review import; three existing tests changed to approve through a scripted console or to check the new guidance |
| Installed-wheel suite | 365 tests from a standalone install of the wheel: 359 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 45 runtime and template files byte-identical to the sources. SHA-256 `323a10863a8997d6858572127eba417ebe3bba50c819b659e09e09afc6159592` |
| Native, source and installed | `scripts/qualify_owner.py` on a copy of the 0.6.0 comparison project, run from this agent session with `CLAUDECODE` and `AI_AGENT` set |
| Regression | `qualify_review_page.py`, now approving through the scripted console, and the guidance, render, relations and instances qualifications passed on the 0.12.0 wheel |

The native script did the following from both runtimes:

1. **Relaxing binding.** An agent binding that relaxed the artist-required direction stage was refused.
2. **Setup.** It bound the workflow and submitted the stage. `next` told the agent to build a page and hand it to the artist.
3. **Page.** It rendered both checkpoints and built a review page. An export approving the stage, with one changed answer and a note, was written as the page writes it.
4. **Refusals.** These were refused, with the record unchanged each time:
   - `review-import` and `stage-complete` from the agent session, with "Owner approval is refused inside an agent session (CLAUDECODE is set)";
   - the same with the agent variables removed and a code piped in, with "Owner approval needs an interactive terminal";
   - an agent-role review of the stage, with the existing "Artist review is required by the stage policy".
5. **Scripted owner.** A scripted console stood in for the owner's terminal and imported the export. The stage completed with `artist_confirmed` and the owner provenance, and the note was added. The prompt showed the verdict, finding and answers.
6. **Replay and notes.** From the agent session, replaying the import returned `ALREADY_COMMITTED` for both items without asking. A notes-only export committed.

**Not checked: a real terminal.** The prompt has not been answered at a real terminal by a person. An agent cannot do this check without defeating the guard it tests. The scripted console exercises the same code path apart from `Terminal.isatty` and `Terminal.ask`.

Local evidence is under `runs/owner-0.12.0-2026-10-10/`, excluded from Git.

## Strength and limits

- **A guard, not a wall.** It stops an agent from approving its own work through the documented commands, payload files or a page export, whether by accident or casually. An agent with an unrestricted shell on the same account can still:
  - remove the variables and fake a terminal;
  - construct an `Approval` in Python;
  - rewrite the record and its hashes.

  A wall needs the owner's records written by a process the agent's account cannot reach.
- **Known agents only.** The variable list covers the agents known here. An unknown agent without them reaches the terminal check, and with no person at the keyboard it cannot type the code.
- **Custom manifests.** A caller who supplies its own manifest still chooses each stage's default policy. Only relaxing a policy the manifest itself sets needs the artist.
- **Earlier records.** Records made before 0.12.0 are not re-attributed. They keep `artist_declared`.
