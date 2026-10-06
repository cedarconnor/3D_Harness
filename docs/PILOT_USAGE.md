# Run the advisory pilot

The Python package, three project skills and native Blender observer are implemented. They are an advisory, single-writer prototype above an existing MCP. The courtyard is a procedural engineering rehearsal, not evidence that condition C wins the planned creative experiment.

Run commands from the repository with Python 3.11 or later. The core has no third-party Python dependencies. `dcc_harness.blender` runs inside Blender, not system Python. The tested native version is Blender 5.1.1 on Windows. The asset fetcher uses Poly Haven's public API with a project user-agent and pins hashes. Normal-map intake is included in the kit, but the fixture uses box-projected base color/roughness with scalar bump; it does not claim a tangent-normal workflow.

## Entry points

The project skills live in `.agents/skills/`: `dcc-plan-environment`, `dcc-build-revise`, and `dcc-review-continue`. Read the relevant `SKILL.md` from the current agent client, along with the run's `CONTINUE.md`. New client sessions can discover project skills according to their configuration. There is no global installation or marketplace plugin yet; the repository and explicit skill-file paths are the working entry point.

```powershell
python -m dcc_harness status runs/engineering-2026-10-03
python -m dcc_harness check runs/engineering-2026-10-03/evidence/05-portable.json runs/engineering-2026-10-03/revised-spec-v2.json
python -m unittest discover -s tests -v
```

An optional wheel provides the same `dcc-harness` console command. It contains the runtime package, not the project skills, examples, asset kit or Blender executable. Keep the repository for those resources. Installing a wheel does not register an MCP or start an agent.

## Native observation through the existing MCP

For the connected Blender Lab execute tool, assign a JSON-compatible dictionary to `result`:

```python
import sys
repo = r"C:\Users\Cedar\Documents\3D_Harness"
if repo not in sys.path:
    sys.path.insert(0, repo)
from dcc_harness.blender import observe
observation = observe()
result = {"revision": observation["revision"], "issues": observation["issues"]}
```

To retain evidence, call `dcc_harness.evidence.write_json(new_path, observation)`. Existing evidence cannot be overwritten. Use `save_checkpoint(new_blend_path, new_observation_path)` at task boundaries. It refuses overwrite and known observation issues; then it records the saved file's hash. A checkpoint alone does not imply that the task spec passed.

The fixture's `examples.courtyard.run_step(project_root, step)` logs intent, applies one owned stage, saves and records the result. It checks target ownership and the predecessor's observed revision. Steps are `00-start`, `01-architecture`, `02-furnishings`, `03-revision`, `04-look-refinement`. They require the pinned asset kit under the run's `assets` folder. Use a new project and preserve the user's existing scene before starting; do not replay stages into the current completed scene.

For arbitrary scripts, use `begin PROJECT SCRIPT --label LABEL` before dispatch and `finish PROJECT OPERATION EVIDENCE` after native observation. On a timeout, keep the operation pending. Inspect the native result, save a reconciliation report, then use `finish ... --reconciled`. The journal prevents its own next dispatch while pending; it cannot prevent a separate actor from calling Blender directly. Concurrent writers are unsupported.

## Checks and coverage

`check` requires `dcc.spec.v1` with at least one declared target. Implemented rules cover target identity/type, evaluated world dimensions, triangle bounds, material binding, presence of UV layers, minimum asset-family count, units and exact named shader input values. Unknown rules are errors. A UV layer's presence does not establish a usable unwrap.

`diff BEFORE AFTER --allow CONTRACT` checks every observed changed field against a concrete allowlist. Absence of an allowed change is permitted; require the intended final state through `check`. Reports name the unmeasured fields. There is no claim to measure arbitrary node properties, rig behavior, animation over time, simulation caches, procedural instances, manifold quality, UV overlap or artistic taste.

Instance IDs, asset IDs and material IDs are separate custom properties. Duplicate instance/material IDs fail observation. Shared mesh definitions are deliberately reused by the pavers. The observer reads actual evaluated mesh state; it does not silently assign IDs or infer success from the requested script.

## Fresh-process qualification

Use the actual Blender binary, `--background`, `--python-exit-code 1` and `scripts/render_checkpoint.py` with `--repo`, a new `--out` folder and optional `--spec`. The script writes an observation, camera renders and capture sidecars; verifies the input .blend hash is unchanged; and exits unsuccessfully on a failed check. `--observe-only` skips rendering. `--packed-only` tests packed image dependencies with external paths redirected inside the disposable process. It never saves the loaded file.

Native render testing uses OptiX when available, otherwise CPU, 960x540 and 32 Cycles samples. Check the report's actual device and timings. Do not confuse a background camera render with a GUI screenshot.

`scripts/resume_fixture.py` tests a setup checkpoint and continued construction in separate processes. Its palette assertion reproduced a real defect: zero-user materials disappeared on reopen. The fixture now retains its palette with fake users. The original failed checkpoint is kept for regression evidence; use the corrected starter in `runs/resume-validation` for further engineering work.

## Project handoff and limits

Run folders hold the brief, immutable checkpoints, source hashes, JSON observations, desired specs, operation journal, reports, renders and continuation note. They are ignored by Git because native artifacts and local environments are large; the small qualification summary in `docs` is retained with source. Copy the whole run directory for evidence handoff, or use the packed .blend for native viewing.

The six independent A/B/C runs are complete; both user-preferred entries used plain MCP. Full artist acceptance, native editability, held-out creative evaluation and multi-hour unattended operation remain open gates. The authorized next [continuity experiment](./CONTINUITY_EXPERIMENT.md) tests accumulated revisions and controlled recovery with fresh agents. No automatic promotion follows a passing engineering fixture. The wider managed-operation protocol and client installers remain deferred.
