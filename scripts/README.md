# Scripts index

Updated October 6, 2026. These scripts qualify releases, benchmark the runtime, and reproduce dated studies. The package does not import them. Scripts tied to finished studies stay here because retained local evidence records their absolute paths; frozen copies also live inside the study packets under `runs/`.

**How to run them.** Scripts marked *Blender* run inside a disposable background process:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/qualify_visibility.py -- --repo . --out runs/NEW-FOLDER
```

Scripts marked *launcher* run under system Python and start Blender themselves, so pass `--blender PATH`. Always choose a fresh output folder, and check both the process exit code and the report. Several studies were run on local scenes that are not in Git; those scripts cannot run from a fresh clone.

## Release qualification

| Version | Scripts | Mode | Runs from a clone |
|---|---|---|---|
| 0.8.0 | `qualify_render.py`: repeat, moved-camera, EEVEE, failure, evidence, project-definition and detached-queue renders on a copy of the comparison fixture; `qualify_guidance.py` rerun | launcher | No: copies a local fixture from `runs/` |
| 0.7.0 | `qualify_guidance.py`: `brief`, `next` and `requirements` on copies of two retained projects, then the printed `observe` and `begin-edit` commands executed | launcher | No: copies local projects from `runs/` |
| 0.6.0 | `qualify_observe.py` with `observe_native_probe.py`; the 0.4.9 adoption launcher rerun after the launcher move | launcher | Yes |
| 0.5.1 | The 0.5.0, 0.4.10 and 0.4.9 launchers rerun against source and installed runtimes | launcher | Yes |
| 0.5.0 | `qualify_feedback_workflow.py` with `feedback_native_probe.py` | launcher, in phases with an explicit image-review file | Yes |
| 0.4.10 | `qualify_revisions.py` with `revision_native_probe.py` | launcher | Yes |
| 0.4.9 | `qualify_adoption.py` with `adoption_native_probe.py` | launcher | Yes |
| 0.4.8 | `qualify_observation_cache.py`, which compares two installed runtimes | Blender | Yes |
| 0.4.0–0.4.8 | `qualify_workflow.py` with `workflow_native_probe.py`; add `--compact-after` for 0.4.6 | launcher | No: needs a saved local scene |
| 0.4.5 | `inspect_roof_laps.py` | Blender, read-only | No: needs the production garden |
| 0.4.4 | `qualify_ground_sampler.py` (owned fixture) and `inspect_ground.py` (production garden) | Blender | Fixture only |
| 0.4.3 | `inspect_vegetation.py` | Blender, read-only | No: needs the production garden |
| 0.3.x | `qualify_visibility.py`: 18 positive and negative visibility fixtures | Blender | Yes |
| 0.1.1 | `qualify_continuity_extents.py`: observation v2 extents | Blender | Yes |

## Benchmarks and utilities

| Script | Purpose |
|---|---|
| `benchmark_observation.py` | Fresh-process observation read and validation timing (0.4.6). Its optional packing duplicates the `pack-observation` command. |
| `benchmark_resume.py` | Fresh-process `resume` timing with store-integrity checks (0.4.2). |
| `probe_visibility.py` | Read-only visibility queries against a saved file (Blender). |
| `render_checkpoint.py` | Reopen, observe and render fixed cameras from an immutable checkpoint (Blender). It uses the pilot observer. |
| `assemble_quality_round.py`, `evaluate_quality_candidate.py`, `run_quality_stage.py` | Quality-loop round assembly and evaluation, documented in [QUALITY_LOOP_USAGE](../docs/guides/QUALITY_LOOP_USAGE.md). Packets copy these evaluators; keep them self-contained. |

## Study tooling

These scripts are retained so finished studies remain reproducible. Many hardcode `runs/` folders, scene IDs or the Blender 5.1 path.

| Study | Scripts |
|---|---|
| Pilot, October 3 ([usage](../docs/archive/historical/PILOT_USAGE.md)) | `fetch_pilot_assets.py`, `make_review.py`, `pack_checkpoint.py`, `native_fault_probes.py`, `unknown_outcome_probe.py`, `resume_fixture.py` (which imports `examples/courtyard.py`) |
| Short comparison ([protocol](../docs/archive/studies/BLIND_TRIALS.md)) | `blind_starter.py`, `blind_evaluator_probe.py`, `blind_uv_probe.py`, `blind_uv_snapshot.py`, `evaluate_blind_checkpoint.py` |
| Continuity comparison ([protocol](../docs/archive/studies/CONTINUITY_EXPERIMENT.md)) | `prepare_continuity_starter.py`, `inject_continuity_event.py`, `evaluate_continuity_checkpoint.py` |
| Quality loop, 0.2.0 ([results](../docs/archive/releases/QUALITY_LOOP_RESULTS.md)) | `prepare_quality_courtyard.py`, `quality_courtyard_native.py`, `run_quality_fixture.py`, `qualify_quality_preflight.py` |
| Overnight study, 0.3.x ([evaluation](../docs/archive/studies/OVERNIGHT_EVALUATION.md)) | `prepare_canopy_study.py`, `prepare_birdbath_study.py`, `prepare_foreground_study.py`, `prepare_activity_study.py`, `prepare_tool_study.py`, `build_canopy_candidates.py`, `build_birdbath_candidates.py`, `evaluate_worker_stage.py`, `publish_quality_stage.py`, `prepare_anonymous_quality_review.py`, `render_quality_presentation.py`, `qualify_quality_deletion.py` |
| Realistic comparison, interrupted ([protocol](../docs/studies/REALISM_COMPARISON.md)) | `fetch_realism_assets.py`, `prepare_realism_comparison.py`, `manage_realism_comparison.py`, `realism_starter.py`, `evaluate_realism_checkpoint.py`, `qualify_realism_evaluator.py`, `export_realism_review.py` (requires Pillow) |

## Known issues

- Fifteen scripts locate the repository with `Path(__file__).resolve().parents[1]`, and several build sibling paths as `repo/'scripts'/...`. Moving a script into another folder requires editing both.
- `qualify_workflow.py` defaults to the Blender 5.1 install path, and `manage_realism_comparison.py` runs it directly. Pass `--blender` on other machines.
- `prepare_tool_study.py` prompt text says the frozen runtime is 0.3.1, but the script copies the live package.
- `fetch_pilot_assets.py` and `make_review.py` do not add the repository to `sys.path`; run them with the package installed.
- Background-Blender launching, Blender argument parsing and folder hashing are reimplemented in many scripts. A shared helper would suit the orchestrators (`qualify_*`, `run_*`) only; evaluators copied into packets must stay self-contained.
