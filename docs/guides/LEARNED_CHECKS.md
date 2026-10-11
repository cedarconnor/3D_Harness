# Learned checks

Version 0.13.0 turns an error the artist found into a check that later projects run automatically. A check is a rule the runtime computes. It is proven on the checkpoint where the error happened and on the one where it was fixed, and only the owner can approve it into a versioned library outside any project. A project uses only the library version its workflow binding pinned. The decision is [D19](../DESIGN_DECISIONS.md#d19-learned-checks-are-computed-rules-in-an-owner-approved-library).

## Rules

A rule is a `dcc.check.rule.v1`. Selectors take a `type`, such as `MESH`, and/or an `id` glob, such as `bench.leg.*`.

An object field rule bounds one measured field of every selected object:

```json
{"schema": "dcc.check.rule.v1", "kind": "object_field", "select": {"type": "MESH", "id": "bench.*"},
 "field": "bounds.min.z", "min": -0.005}
```

The fields are:

- `bounds.min.x|y|z` and `bounds.max.x|y|z`;
- `dimensions.x|y|z`;
- `scale.min`, `scale.max` and `determinant`, from the world matrix;
- `triangles` and `vertices`;
- `materials`, the number of material slots;
- `visible.render`, which is 1 or 0.

A supported-by rule is the [relations](AGENT_QUICK_REFERENCE.md#4-measure-what-rests-on-what) family with selectors:

```json
{"schema": "dcc.check.rule.v1", "kind": "supported_by", "subjects": {"id": "bench.leg.*"}, "support": {"id": "ground"},
 "max_gap": 0.005, "max_penetration": 0.01, "footprint": 0.002}
```

On a checkpoint, it resolves to a `dcc.relations.v1` definition with the matching IDs. It is evaluated from a `relations --spec` measurement of that exact checkpoint.

Both kinds fail when nothing matches, unless `"require_match": false`. A lesson that no rule can express stays a note in the skill.

## Propose a check

Only an error becomes a check. Taste stays project direction, in the brief or decisions. Write a proposal naming the note, the rule, the stages it applies to (from the environment template) and two fixtures:

- **`fails`**: the note's own checkpoint, where the error is.
- **`passes`**: a later checkpoint where it is fixed.

For a supported-by rule, measure both checkpoints with the resolved definition and add each `measurement`.

```json
{"schema": "dcc.check.proposal.v1", "id": "bench-legs-on-ground", "note_id": "NOTE_ID", "classification": "error",
 "rule": {"...": "..."}, "stages": ["assembly"], "rationale": "Furniture legs rest on the ground",
 "proposer": {"role": "agent", "author": "<your name>", "reference": "<where this came from>"},
 "fails": {"checkpoint": {"checkpoint_id": "...", "checkpoint_sha256": "..."}, "measurement": {"path": "legs-fails/measurement.json"}},
 "passes": {"checkpoint": {"checkpoint_id": "...", "checkpoint_sha256": "..."}, "measurement": {"path": "legs-passes/measurement.json"}}}
```

```powershell
python -m dcc_harness fill-hashes "<proposal.draft.json>" "<proposal.json>"
python -m dcc_harness check-propose "<project>" --proposal "<proposal.json>" --expected-revision REVISION --request-id REQUEST_UUID
```

The runtime evaluates the rule on both fixtures. It refuses the proposal unless the rule fails on the note's checkpoint and passes on the fix.

## Approve it: owner only

```powershell
python -m dcc_harness checks "<library folder>"
python -m dcc_harness check-approve "<library folder>" --project "<project>" --proposal PROPOSAL_REVISION --expected-version VERSION
```

Run these in your own terminal; an agent's request is refused, as described in [owner approval](OWNER_APPROVAL.md). Approval:

1. proves the check again on the retained fixtures;
2. shows the rule, stages, rationale and note;
3. asks for the code;
4. writes the next library version.

`--expected-version` is the version `checks` listed, or 0 for a new library.

The library folder holds:

- `versions/NNNNNN/library.json`, one per approval, each chained to the previous;
- `fixtures/<check>/`, the fixtures each check was proven on;
- `occurrences/`, the counted repeats.

`checks` re-proves every check on its fixtures, so a damaged library is refused.

## Pin a library in a new project

Export one version and pin it in the workflow binding, beside the skills:

```powershell
python -m dcc_harness checks "<library folder>" --export "<binding folder>/library.json"
```

Add `"checks": {"path": "library.json"}` to the binding draft, run `fill-hashes`, then run `workflow-bind`. The binding retains that exact file. Later approvals never reach a project already bound, and a project bound without `checks` runs none.

## What runs, and when

A pinned check runs when a stage is submitted, at the stages it lists and always at `delivery`. `requirements PROJECT STAGE` lists the stage's checks with their current result. For a supported-by check, it also gives the resolved `spec`, the `relations ... --spec` command and a `check_measurements` entry in the skeleton. The receipt records every result. Completion is refused while any check fails or a relation check has no measurement.

## Count a repeat

When a note in another project describes an error a library check covers, count it:

```powershell
python -m dcc_harness check-occurrence "<library folder>" --project "<project>" --note NOTE_ID --check CHECK_ID
```

The runtime verifies that the check fails on the note's checkpoint; add `--measurement` for a supported-by check. `checks` ranks checks by their origin plus counted repeats.

## Limits

- **Two rule kinds.** Object fields and supported-by relations only. There are no material, scene or Geometry Nodes rules yet.
- **No upgrades.** A project keeps the library version it was bound with.
- **Structure, not provenance.** A pinned file is checked for structure and owner approvals, not for having come from a particular library folder.
- **Repeats are counted by hand.** A failed check at a submission is not counted automatically.
- **Approval is a guard.** It has the same guard-not-wall limit as [owner approval](OWNER_APPROVAL.md).
