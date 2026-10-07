# Lower the cost of each step — 0.6.0

Version 0.6.0, October 6, 2026, is [build-plan](../../BUILD_PLAN.md) item P1, following its [implementation plan](../plans/P1_LOWER_STEP_COST.md). It adds two commands that replace work agents previously did by hand. A paired fresh-agent comparison found **no reduction in elapsed time**: most of each run went to orientation and payload preparation, not to the steps these commands shorten.

## Delivered

- **`observe SAVED.blend --blender PATH --output-dir NEW_FOLDER`** opens a saved file in a fresh background Blender and observes it, without the file's UI or embedded scripts. It never saves, and checks that the source bytes are unchanged before opening, after opening and after observing. It reports `READY`, or `HAS_ISSUES` with exit status 1 and the issue list. The request and Blender log stay beside `observation.json`, which is compact unless `--expanded` is given.
- **`fill-hashes PAYLOAD DESTINATION`** fills the SHA-256 of every `{path}` reference in a payload and verifies hashes already present; a mismatch fails. It applies the coordination path rules to the references and the link guard to every path, including the destination. It writes a new file.
- **Shared launcher.** Adoption and `observe` now share one background-Blender launcher, `dcc_harness/native.py`.
- **Guides and skills.** The everyday-workflow, external-revision and structured-feedback guides, and the `dcc-harness`, `dcc-build-revise` and `dcc-review-continue` skills, show the new commands.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 260 tests: 258 passed, two Windows symlink-permission skips. Sixteen tests are new: six for `observe`, ten for `fill-hashes`. |
| Installed-wheel suite | Same result, from a standalone install of the final wheel |
| Wheel integrity | All 38 runtime and template files byte-identical to the committed sources. Final SHA-256 `32a65f7541cef5b1db60063d68628748ee437ca1f8addd23a0ca2cf8df6a97f8` |
| Native `observe`, source and installed | A clean scene and a copy at a path containing spaces reported `READY`. A missing asset ID (`Missing asset ID: ProbeCube`) and a collection instancer (`Unsupported instancer: ProbeInstancer`) reported `HAS_ISSUES`. An existing output folder was refused before Blender started. The fresh-process observation's revision equalled an in-process observation of the same saved file exactly. Source files were unchanged, and `start` accepted the command's output directly. |
| Native adoption, source and installed | Passed after the launcher moved |

The native exercises and the comparison used the first 0.6.0 build (`5320916d…`). The final wheel differs from it only in `payloads.py`, which now checks the destination for links and junctions before writing. That fix came from a failing test written after the first build, and both suites were rerun on the final wheel.

**Line-ending correction.** The 0.5.1 wheel (`0749c9b9…`) and the first two 0.6.0 builds packaged CRLF copies of `adoption.py` and `_adoption_blender.py`. Those copies came from a checkout made before `.gitattributes` existed. The committed sources are LF, and the runtime digest normalizes line endings since 0.5.1, so pinning was unaffected. The final wheel above was rebuilt from LF files byte-identical to the commit, and the installed suite passed again on it. A wheel rebuilt from a clean checkout of 0.5.1 will therefore not reproduce the hash in that report.

## Fresh-agent comparison

Two fresh agents of the same model received sealed packets that were identical except for the runtime and its matching skills and guides: 0.5.1 in packet A, 0.6.0 in packet B. Each had to change the shared timber roughness from 0.65 to 0.8 through the reservation workflow, observe and render the candidate, publish it, and record a feedback response with evidence. B ran first, so any warm-cache advantage went to A.

| | A: 0.5.1 | B: 0.6.0 |
|---|---|---|
| Measured wall time | 8 min 16 s | 9 min 41 s |
| Tool calls / tokens | 60 / 217k | 62 / 245k |
| Outcome | Published checkpoint 3; response committed; check passed | Same |
| Scripts written | One, the required edit script | One, the required edit script |
| Observation | The provided render tool's `observe` action, twice | The `observe` command, twice |
| Hashes | `sha256sum`, copied into JSON by hand | `fill-hashes` |
| Blender time | About 20 s | About 11 s |
| Orientation before the first command (self-reported) | About 3 min | About 3.7 min |

I verified both projects independently. Each published roughness 0.8 at sequence 3 under the stated runtime, with a passing native check and the visual note awaiting verification.

**The comparison was confounded.** The render tool given to both packets also exposes an `observe` action, so the 0.5.1 agent had a one-command observation path too. Only hashing and the documentation genuinely differed. With one run per arm, a difference of 85 seconds in either direction is noise. The 0.5.0 baseline of 372.6 s came from a different model, on a task without a render tool, and is not comparable.

What the runs do show is where the time goes. Both agents spent roughly three minutes reading skills, guides and runtime source before acting, then about a minute each on the contract, handoff and response JSON. Native work took seconds. The 0.5.0 agent, which had no render tool, wrote five scripts; both of these agents wrote one. A ready-made tool for a step therefore removes scripts, but not elapsed time spent understanding the workflow.

## Implications for the plan

- `observe` and `fill-hashes` stay: they remove a script and a source of hash errors per step.
- Further single-step commands are unlikely to change the investment gate on their own. The next cost to attack is orientation: a short task-oriented reference for agents, and a fixed-view render command that generalizes the render tool both agents relied on. Measure the effect before building more composite commands.

Local evidence is under `runs/observe-0.6.0-2026-10-06/` and `runs/step-cost-comparison-2026-10-06/`, excluded from Git.

## Limits

- `observe` reads saved files only; it does not observe a live editor.
- Collection instances are still reported as issues; supporting them is item P3.
- `fill-hashes` fills file hashes only. Checkpoint references stay explicit.
- One paired run per version is directional evidence, not a measured advantage, and agent review is not artist acceptance.
