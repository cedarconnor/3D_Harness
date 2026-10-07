# P1: Lower the cost of each step

Plan for [build-plan](../BUILD_PLAN.md) item P1, written October 6, 2026, at version 0.5.1. Target version: 0.6.0, because it adds commands.

## Problem

Every harness step currently needs work that plain MCP does not:

- **Observation.** `start`, `begin-edit`, `finish-edit` and `preview-revision` each require a saved-state observation. Agents produce one by writing an ad hoc Blender script that opens the file and calls `continuity_blender.observe()`.
- **Hashes.** Feedback, stage and evidence payloads reference files as `{path, sha256}`. Agents compute each SHA-256 separately and paste it in.

The 0.5.0 fresh agent spent 6 min 12.6 s on a one-parameter revision of a micro fixture. Without lower overhead, the harness cannot match plain MCP's effort, which is half of the investment gate.

## Scope

### `observe`

```text
python -m dcc_harness observe SOURCE.blend --blender PATH --output-dir NEW_FOLDER [--expanded]
```

- Starts a fresh background Blender with `--factory-startup --disable-autoexec --python-exit-code 1`, opens the saved file without its UI, runs `continuity_blender.observe()`, and writes `observation.json`. Compact storage is the default; `--expanded` writes the formatted form.
- Never saves. Checks that the source bytes are unchanged before opening, after opening and after observing.
- Rejects links and junctions in either path, a non-`.blend` source, and an existing output folder. Retains the request and the Blender log beside the observation.
- Reports `READY` when the observation has no issues and is clean, otherwise `HAS_ISSUES` with exit status 1. The report includes the issue list, object and material counts, declared coverage, checkpoint hash and revision.
- Reuses the adoption worker launcher, which moves into a small shared module.

### `fill-hashes`

```text
python -m dcc_harness fill-hashes PAYLOAD.json --out NEW.json [--evidence-root FOLDER]
```

- Walks the payload and fills `sha256` for every reference object, meaning an object whose only keys are `path` and an absent or null `sha256`.
- Verifies hashes that are already present, and fails on a mismatch instead of overwriting: a stale hash may mean the file changed after review.
- Uses exactly the coordination path rules, so contained relative paths, no traversal and no links. The default base is the payload's folder, as for the coordination commands.
- Writes a new file and never rewrites its input. Checkpoint references stay explicit; agents copy them from `resume`.

### Guides and skills

Show the shorter flow in the everyday-workflow and structured-feedback guides. Update `dcc-harness`, `dcc-build-revise` and `dcc-review-continue` to use both commands.

## Qualification

- **Portable tests.** For `fill-hashes`: nested references, mismatch, traversal, absolute paths, links, untouched non-reference objects and exclusive output. For `observe`: argument and path rejection, using an unlaunchable Blender path where no native process is needed.
- **Native fixtures, source and installed.** A clean scene with stable IDs reports `READY`, and its observation equals an in-process observation of the same file apart from timestamps. A scene with a collection instance reports `HAS_ISSUES`. A scene missing asset IDs reports `HAS_ISSUES`. A source path with spaces works. The source file's bytes stay unchanged throughout.
- **Comparison.** Repeat the 0.5.0 fresh-agent revision on the same micro fixture with 0.6.0, using a sealed packet and a fresh context. Record elapsed time against the 372.6 s baseline, plus the number of hand-built hashes and observation scripts. One run is directional, not a measured advantage.

## Out of scope

- Observing the live editor. The command reads saved files only.
- Automatic checkpoint-reference filling and MCP integration.
- Collection-instance support. The command reports instancers as issues until P3.
