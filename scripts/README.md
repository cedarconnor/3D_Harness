# Scripts index

## Maintained release verification

Run `python scripts/verify_release.py --out <fresh evidence folder> --blender <Blender executable>` from a development environment with the declared dependencies for source tests, complete wheel/sdist runtime parity, clean-environment installation, installed-runtime tests and native units, adoption, managed execution, MCP and live execution gates. Omit `--blender` for portable checks only. Logs and wheel hashes are retained; user configuration is not changed.

The MCP native fixture exercises all five live observation commands and both managed modes. It also audits Python outbound socket attempts and activity-handler registration across add-on import, start, reads and shutdown. These checks run against the exported add-on from the requested runtime.

`qualify_units.py`, `qualify_adoption.py`, `qualify_execution.py` and `qualify_mcp.py` can run individually with `--runtime`, `--out` and `--blender`. The MCP qualification opens and closes an owned Blender GUI fixture to test real timers/socket dispatch, then drives both managed modes over real stdio. Historical scripts below remain evidence for their original versions.

`qualify_live.py --case all` uses the same runtime/out/blender arguments and runs 26 owned GUI scenarios: protocol/reload, initial attachment, built-in edits, node assets/shared materials, external refresh/reconnect, failure/recovery, cancellation/lost replies, publication races and both MCP modes. `--case protocol|attach|jobs|modes`, `--fixture`, `--mode` and `--recovery` select individual cases. The exported add-on must run without importing the host harness package; outbound sockets, activity handlers and retained pairing-secret leakage are checked. Synthetic owner confirmation is used only inside disposable qualification projects.

Updated October 6, 2026. These scripts qualify releases, benchmark the runtime, and reproduce dated studies. The package does not import them. Scripts tied to finished studies stay here because retained local evidence records their absolute paths; frozen copies also live inside the study packets under `runs/`.

**How to run them.** Scripts marked *Blender* run inside a disposable background process:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/qualify_visibility.py -- --repo . --out runs/NEW-FOLDER
```

Scripts marked *launcher* run under system Python and start Blender themselves, so pass `--blender PATH`. Since 0.13.1 the current qualifications share `_launcher.py` for their arguments, runtime selection, CLI calls and Blender runs. `python -m dcc_harness.session_cost TRANSCRIPT` records a trial session's turns, minutes, tokens, cache-read share and spend against the trial ceilings. Always choose a fresh output folder, and check both the process exit code and the report. Several studies were run on local scenes that are not in Git; those scripts cannot run from a fresh clone.

## Release qualification

| Version | Scripts | Mode | Runs from a clone |
|---|---|---|---|
| 0.19.0 | `qualify_attribute_hash.py` with `attribute_hash_native_probe.py`: a flat-shaded bench top and variants that change only shading, a sharp edge, a crease, a seam, a color attribute, a loose edge or one attribute of every type. Each fails a zero-permission contract on `source_attribute_hash` alone and passes unnoticed with the `--baseline-runtime` (0.18.1); the production garden's observation time on both. The earlier qualifications rerun | launcher | Yes: builds its scene; the timing needs the local garden |
| 0.18.1 | `qualify_saved_state.py` with `saved_state_native_probe.py`: a saved scene observed in background and interactive Blender before and after an unsaved Python edit; `start` refuses the interactive observation; the `observe` command passes with `--offline-mode`. The interactive half opens a Blender window. Passed on 5.1.1 and 5.2.1; the earlier twelve rerun | launcher | Yes: builds its scene; needs a desktop session |
| Skills, after 0.18.0 | `qualify_blender_skills.py` with `blender_skills_native.py`: every `python verify` block in the 25 `blender-*` skills, one background Blender per skill; `--only NAME...` limits the run. Passed on 5.1.1 and 5.2.1 | launcher | Yes: every block builds its own scene |
| 0.18.0 | `qualify_uv_report.py`: seven planes with exactly known UVs (density, overlap, outside, no UV, small-triangle path) and the production garden's timing. The earlier twelve rerun | launcher | Yes: builds its scene; the production timing needs the local garden |
| 0.17.0 | `qualify_modifiers.py`: a bevel-segment change published and a bevel-width change refused under `allowed_modifier_settings`; a Mix blend change published at the desired value and refused at another. The earlier eleven rerun. Also `p5_build_packets.py` and `p5_grade.py`, the P5 skill regression suite | launcher | Yes: builds its scenes |
| 0.16.0 | `qualify_relocation.py`: a panel reading an external PNG; an artist candidate changing only roughness is refused without `--blender`, packed and accepted with it, still `READY` after the PNG is moved, and a changed PNG is refused. The 0.4.10 `qualify_revisions.py` and the earlier nine rerun | launcher | Yes: builds its scene |
| 0.15.0 | `qualify_coverage.py`: a lamp and world edit on the probe bench refused without permissions and published with them; a verified technical note on one leg stays current, then needs a recheck after the leg moves. The earlier eight rerun | launcher | Yes: builds its scenes |
| 0.14.0 | `qualify_delivery.py`: the probe bench and the comparison project delivered and reimported, a moved copy caught by `BOUNDS`, a truncated GLB refused at import and a non-checkpoint refused; the earlier seven rerun | launcher | Yes: builds its scenes, plus the comparison project from `runs/` |
| 0.13.1 | The seven current qualifications (`checks`, `owner`, `review_page`, `guidance`, `render`, `relations`, `instances`) moved onto `_launcher.py` and rerun unchanged in what they assert | launcher | As for each script |
| 0.13.0 | `qualify_checks.py`: on the relations probe's bench scenes, two checks proposed and proven natively, a wrong and a taste proposal refused, approval refused from the agent session and given by a scripted owner console, then a second project that pins the library: blocked by both checks, a counted repeat, and completion after the fix. The 0.7.0–0.12.0 qualifications rerun | launcher | Yes: builds its scenes |
| 0.12.0 | `qualify_owner.py`: from an agent session, approvals through `review-import` and `stage-complete` are refused, and again with the agent variables removed but input piped; a scripted owner console commits with provenance; replay and notes-only import still work. `qualify_review_page.py` takes its approval through the same console; the 0.7.0–0.10.0 qualifications rerun | launcher | No: copies a local project from `runs/` |
| 0.11.0 | `qualify_review_page.py`: a rendered and reopened page on the comparison project, a pinned note and a stage approval imported and replayed; the 0.7.0–0.10.0 qualifications rerun | launcher | No: copies a local project from `runs/` |
| 0.10.0 | `qualify_instances.py` with `instances_native_probe.py`: observation, compatibility with the previous release (`--baseline-runtime`), scoped instance edits, an in-place library edit, issues and adoption; the 0.7.0–0.9.0 qualifications rerun | launcher | Needs a previous release for the compatibility check |
| 0.9.0 | `qualify_relations.py` with `relations_native_probe.py`: eight exact bench scenes, the project history and the guidance; `qualify_guidance.py` and `qualify_render.py` rerun | launcher | Yes |
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
