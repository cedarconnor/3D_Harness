# Learned check library — 0.13.0

Version 0.13.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P11, following its [implementation plan](../plans/P11_LEARNED_CHECKS.md) and decision [D19](../../DESIGN_DECISIONS.md#d19-learned-checks-are-computed-rules-in-an-owner-approved-library).

An error the artist finds now becomes a check that later projects run, on these conditions:

- the runtime can compute it;
- it fails on the checkpoint where the error happened and passes on the fix;
- the owner, not the proposing agent, approves it.

## Delivered

- **Rules (`dcc.check.rule.v1`).**
  - `object_field` bounds one measured field of the objects a type/ID-glob selector matches. The fields are bounds corners, dimensions, scale, determinant, triangle, vertex and material counts, and render visibility.
  - `supported_by` resolves its selectors to a `dcc.relations.v1` definition. It is evaluated from a native `relations --spec` measurement whose checkpoint hash and definition digest must match.
  - Nothing matching fails unless `require_match` is false. Any other kind is refused as a lesson for a skill note.
- **`check-propose`.** A coordination command that records a proposal from a feedback note.
  - It refuses taste, unknown stages and duplicate IDs.
  - The failing fixture must be the note's own checkpoint and the passing one later.
  - The runtime must see the rule fail on the first and pass on the second.
- **`check-approve`.** Owner only, through the 0.12.0 channel.
  - It proves the proposal again from the project's verified record and its retained measurements.
  - It refuses a stale library version or a duplicate ID.
  - It shows the rule, stages, rationale and note, then copies the fixtures under `fixtures/<check>/` and writes `versions/NNNNNN/library.json`, chained to the previous version.
- **`checks`.** Verifies the chain and fixture hashes, re-proves every check on its fixtures, ranks checks by origin plus counted repeats, and exports a version byte for byte.
- **`check-occurrence`.** Counts a note from any project whose checkpoint the check fails on. It refuses the check's own origin note and repeats.
- **Pinning and running.**
  - A binding may carry `checks`, one exported version. It is retained and recorded with its version, digest and IDs.
  - At `stage.submit`, the pinned checks for that stage, and all of them at delivery, are evaluated on the submitted checkpoint. The receipt lists every result and `failed_checks`, and completion is refused while any fails or is unmeasured.
  - `requirements` lists the checks with their current result, the resolved relation definition and command, and `check_measurements` placeholders.
- **Docs.** The [learned checks guide](../../guides/LEARNED_CHECKS.md); quick-reference section 8 and three new stops; the owner approval and structured feedback guides; the `dcc-harness` skill and the README.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 381 tests: 379 passed, two Windows symlink-permission skips. 16 tests are new, all for learned checks |
| Installed-wheel suite | 381 tests from a standalone install of the wheel: 375 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 46 runtime and template files byte-identical to the sources. SHA-256 `11bdeb7a604e3d56a4eb78184ed7dea40e001a04333ca2f5f1736ac9dfe4eaaf` |
| Native, source and installed | `scripts/qualify_checks.py` on the relations probe's bench scenes, run from this agent session |
| Regression | The owner, review page, guidance, render, relations and instances qualifications passed on the 0.13.0 wheel |

### Native run

The script did the following from both runtimes.

**Project A, the errors.** The project started on the raised bench, and an artist note said "The bench floats above the ground". A scoped edit then lowered the bench 6 cm into the ground, and a second note said "The legs now sink into the ground". A third edit rested it on the ground.

**Proposals.**

- **`bench-legs-on-ground` (`supported_by`).** Its definition resolved to the four `bench.leg.*` subjects on `ground`. It was measured natively on the raised and fixed checkpoints, and the proposal recorded FAIL then PASS.
- **`nothing-below-ground` (`object_field`, `bounds.min.z ≥ -0.005` for `MESH` `bench.*`).** Proposed against the floating note, it was refused: the rule passes there. Classified as taste, it was refused. Against the sinking note, it recorded FAIL then PASS.

**Approval.** `check-approve` from the agent session was refused with "Owner approval is refused inside an agent session", and no library was written. A scripted console stood in for the owner's terminal and approved both checks, as versions 1 and 2. The prompt showed the check ID, note, rationale, rule and stages. `checks` re-proved both and exported version 2.

**Project B, the same mistake.**

1. **Setup.** A new project started on the sunk bench and pinned version 2 in its binding.
2. **Requirements.** `requirements` reported `nothing-below-ground` as FAIL and `bench-legs-on-ground` as NOT_MEASURED, with the resolved definition and command.
3. **Submission.** Running that command measured PENETRATION of -0.030 m on every leg. The assembly submission recorded both checks as failed: the legs' bounds were at -0.03 m and they penetrated the ground. Completion was refused with "Pinned library checks failed or were not measured".
4. **Repeat.** A note in project B was counted as an occurrence. `checks` then ranked `nothing-below-ground` (2) above `bench-legs-on-ground` (1).
5. **Fix.** After an edit rested the bench, both checks passed and the stage completed.

Local evidence is under `runs/checks-0.13.0-2026-10-10/`, excluded from Git.

**Not checked:**

- **A real terminal.** As in 0.12.0, no person answered the approval prompt at a real terminal.
- **Fresh agents.** No fresh agent has used the library to show that it changes behaviour on a new project.

## Limits

- **Two rule kinds.** Material, scene and Geometry Nodes rules are not supported.
- **No upgrades.** A project keeps the version it was bound with.
- **Structure, not provenance.** A pinned file is checked for structure and owner approvals, not for having come from a particular library folder.
- **Repeats are counted by hand.** Failed submissions are not counted automatically.
- **Approval is a guard.** It has the same guard-not-wall limit as D18.
- **Checks are not quality.** They measure one rule each and say nothing about artistic quality.
