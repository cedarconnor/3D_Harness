# P11: Learned check library

Plan for [build-plan](../../BUILD_PLAN.md) item P11, written October 10, 2026, at version 0.12.0. Target version: 0.13.0. The decision is [D19](../../DESIGN_DECISIONS.md#d19-learned-checks-are-computed-rules-in-an-owner-approved-library).

## Problem

When the artist finds an error that no check reported, the fix stays in that project. The next project can make the same mistake, and nothing catches it until the artist looks again. Mortiflix keeps a library of learned checks, but its checks are plain-language rules that the session marks as passed. Here a learned check must be computed by the runtime, proven against the error it came from, approved by the owner and not the proposing agent, and pinned so that a library change never alters a project already under way.

## Scope

### Rules

A check is a `dcc.check.rule.v1` rule of one of two kinds, both computed by the runtime.

- **`object_field`** selects objects by `type` and an `id` glob, and bounds one measured field with `min` and/or `max`. The fields are:
  - the bounds corners `bounds.min.x|y|z` and `bounds.max.x|y|z`;
  - `dimensions.x|y|z`, `scale.min` and `scale.max` (axis lengths of the world matrix), and `determinant`;
  - `triangles`, `vertices` and `materials`, which is the count of material slots;
  - `visible.render`, which is 1 or 0.

  `require_match` fails the check when nothing matches. The rule is evaluated from the checkpoint's stored observation.
- **`supported_by`**, P2's relation family, selects its subjects and support by glob. Against a checkpoint's observation, it resolves to a `dcc.relations.v1` definition with the check's tolerances. It is evaluated from a `relations --spec` measurement whose definition digest and checkpoint hash must match.

A proposal without a computable rule is refused. Such a lesson stays a skill note.

### Proposing: `check-propose`

`check-propose` is a coordination command, kind `check.propose`, recorded in the project. A `dcc.check.proposal.v1` carries:

- a check `id`;
- the `note_id` it comes from;
- a `classification`;
- the `rule`, its `stages` (from the packaged environment template) and a `rationale`;
- the proposer;
- two fixtures:
  - `fails`: the note's anchor checkpoint;
  - `passes`: a later checkpoint where the error is fixed.

  Each fixture carries a measurement file for a `supported_by` rule.

The runtime evaluates the rule on both fixtures and refuses the proposal unless it fails on `fails` and passes on `passes`. A `taste` classification is refused, because taste stays project direction.

### Approving: `check-approve`

`check-approve LIBRARY --project P --proposal REVISION --expected-version N` approves a proposal into the library.

- **Owner only.** It always needs the owner through the P12 channel.
- **Re-proven.** It verifies the proposal in the project's record and evaluates the rule again on the retained fixtures. It refuses an ID already in the library.
- **New version.** It writes the next library version.

The library lives outside any project:

- `fixtures/<check>/` holds the fixture observations and measurements, written once.
- `versions/NNNNNN/library.json` is created exclusively. It holds every check with its rule, stages, rationale, origin (project, proposal, note text), fixture hashes and owner approval, and chains to the previous version's hash.
- `checks LIBRARY` verifies the chain and fixture hashes, and re-evaluates every check against its fixtures, so a damaged library is refused.

### Counting repeats: `check-occurrence`

`check-occurrence LIBRARY --project P --note NOTE --check ID` is for a note in another project that describes an error an existing check covers. The runtime verifies that the check fails on the note's anchor checkpoint, then appends an occurrence. `checks` ranks checks by origin plus occurrences, the way Mortiflix's `--same-as` counts repeats. Counting needs no owner.

### Pinning and running

- **Pinning.** A workflow binding may carry `checks`, a reference to one version's `library.json`, exported byte-identical with `checks LIBRARY --export FILE`. The binding retains the file and records its version and digest. Projects bound without it, or bound earlier, are unaffected.
- **Running.** At `stage.submit`, every pinned check whose stages include the submitted stage, and every pinned check at `delivery`, is evaluated on the submitted checkpoint.
  - `object_field` checks are computed from the stored observation.
  - `supported_by` checks use the submission's optional `check_measurements` entries.
  - The receipt lists each result, with `failed_checks` for failures and anything not measured. Completion is refused while any remain.
- **Guidance.** `requirements` lists the stage's pinned checks. For a relation check it gives the resolved definition and the `relations --spec` command, and adds the measurement placeholders to the skeleton.

## Qualification

- **Portable tests.**
  - Rule validation, selection, each field and the relation resolution.
  - Proposal refusals: taste, an unmeasurable rule, a rule that passes on the note's checkpoint or fails on the fix, an unknown note.
  - Approval: refused without the owner, the version chain, a duplicate ID and a damaged fixture.
  - Occurrences and ranking.
  - Pinning: by version, and earlier bindings unaffected.
  - Running: a failing check blocks completion, a relation check without a measurement is reported as not measured, and the receipt is checked.
  - The CLI.
- **Native, source and installed.** `scripts/qualify_checks.py` on the bench scenes from the relations probe.
  1. **Project A** starts on the raised bench. It gets a note that the bench floats, an over-correction into the ground, a second note that the legs sink, and the fix.
  2. The agent proposes `bench-legs-on-ground` (`supported_by`, measured natively on the raised and fixed checkpoints) and `nothing-below-ground` (`object_field`). A proposal of the field check against the floating note is refused, because it passes there.
  3. Approval from this agent session is refused. A scripted owner console approves both.
  4. **Project B** starts on the sunk bench and pins the library. The assembly submission fails both checks and completion is refused. A note and `check-occurrence` count the repeat. After the fix, both checks pass and the stage completes.

## Out of scope

- Material and scene rules, and Geometry Nodes.
- Upgrading a project's pinned library after binding.
- Signed or shared libraries.
- Counting occurrences automatically from failed submissions.
