# Relationship checks — 0.9.0

Version 0.9.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P2, following its [implementation plan](../plans/P2_RELATIONSHIP_CHECKS.md). It adds one qualified relation family, `supported_by`, measured where the relation happens: at each subject's contact footprint. Findings say how they were established, and a bounding-box estimate can only ask for inspection. Every measurement made for a project joins a retained history, which warns when repairs swing back and forth or stop improving.

Two fresh agents were asked to make an equal-legged bench stand on sloping ground. One project had a recorded history of two failed whole-bench moves; the other had none. Both fixed the bench on their first attempt by adjusting each leg, and neither tried a whole-bench move. The agent with history cited it. The agent without history was steered by the first measurement's `CONFLICT`. So the measured classification was enough on this task, and the history's own effect was not isolated.

## Delivered

- **Definition `dcc.relations.v1`.** A project holds it as the decision `relations`, or it can be passed as a file. Each relation has an ID, the kind `supported_by`, subject IDs, support IDs, and tolerances in metres: `max_gap`, `max_penetration` and the `footprint` band above each subject's lowest point.
- **`relations SAVED.blend --blender PATH --output-dir NEW (--project PROJECT | --spec FILE) [--strategy TEXT]`.** A fresh background Blender opens the file and never saves it. It casts vertical rays through every footprint point of each subject against the evaluated support meshes, reusing the ground sampler, and also computes a bounding-box estimate. The report is bound to the file's hash and the definition's digest, and the command exits 1 when a relation fails. Each subject's finding has:
  - a code: `OK`, `GAP`, `PENETRATION`, `OFF_SUPPORT` or `MISSING_TARGET`;
  - a signed error in metres from the footprint point closest to contact;
  - the footprint's spread and its coverage;
  - the permitted action (`none`, `repair` or `inspect`);
  - the bounding-box estimate, labelled `bounds_only` with the permitted action `inspect`.

  A relation whose subjects both float and sink is a `CONFLICT`: no rigid move of the group can fix it.
- **Repair history.** With `--project`, each measurement is appended to the project's `relations/` record under the workflow lock, with the parent checkpoint, the file's hash and the `--strategy` text. Entries are never rewritten. Per subject, the history reports one of three trends:
  - `OPPOSING`: the last two failing attempts had opposite codes;
  - `NO_PROGRESS`: the same code, with the error shrinking by less than 20%;
  - `IMPROVING`: the error shrinking by at least 20%; no warning.

  It also carries the latest measurement's `CONFLICT`.
- **Guidance.** `next` returns the warnings and offers a `relations` step, for the active checkpoint or for a reserved edit's result before `finish-edit`. `brief` adds a relation history section: the latest result and trend per subject, and each warning with the strategies tried. The quick reference has a section whose definition example the suite validates. The everyday-workflow guide, the `dcc-harness` skill and the README describe the command.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 324 tests: 322 passed, two Windows symlink-permission skips. 20 tests are new: definition, classification, history, command and guidance. |
| Installed-wheel suite | 324 tests from a standalone install of the wheel: 318 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 43 runtime and template files byte-identical to the sources. SHA-256 `00d26ef4fd1f65c5f24a568ff8f64267bb61db348f3551afa73678079f51ba62` |
| Native, source and installed | `scripts/qualify_relations.py` with scenes built by `scripts/relations_native_probe.py`. The ground is a single quad whose height is 0.1 × y, so every expected value was computed by hand; all findings matched within 0.2 mm. |
| Regression | The 0.7.0 guidance and 0.8.0 render qualifications passed again on the 0.9.0 wheel |

| Scene | Expected and measured |
|---|---|
| Bench on flat ground | All legs `OK`; the bounds estimate agrees |
| Raised 3 cm, sunk 3 cm | `GAP` +0.030 m, `PENETRATION` −0.030 m on every leg |
| One leg past the ground's edge | That leg `OFF_SUPPORT`, the others `OK` |
| Sloped ground, legs cut to fit | All legs `OK` with a 9 mm spread across each footprint. The bounds estimate reports `PENETRATION` of about 0.2 m, labelled `bounds_only` and `inspect` |
| Sloped ground, equal legs | Downhill legs `GAP` +0.0185 m, uphill legs `PENETRATION` −0.0275 m: `CONFLICT` |
| Equal legs, whole bench lowered 4 cm | All `PENETRATION`: −0.0215 m downhill, −0.0675 m uphill |
| Equal legs, whole bench raised 4 cm | All `GAP`: +0.0585 m downhill, +0.0125 m uphill |

The script then started a project on the equal-legged bench with the definition as a decision. It ran the `relations` command that `next` printed, which recorded the `CONFLICT`. It then recorded the lowered and raised files with their strategies. `next` reported `OPPOSING` on all four legs with both strategies, and `brief` showed the history. No measured scene changed.

## Fresh-agent continuation

Packets H and N held the equal-legged bench on sloped ground as the active checkpoint of a project with the `relations` decision. Both had the 0.9.0 runtime, the same skills, guides and `BRIEF.md`, and the same prompt to a fresh agent. The brief asked for every leg resting on the slope, with the top level and in place, and for publishing only a candidate whose relations pass. The packets differed only in H's three history entries: the initial `CONFLICT`, then "Lowered the whole bench 4 cm" and "Raised the whole bench 4 cm", both `OPPOSING`. N's project had no history.

| | H: with history | N: without |
|---|---|---|
| Wall time | 3 min 18 s | 2 min 40 s |
| Tool calls / tokens | 31 / 123k | 24 / 108k |
| First harness command | 7 s (`brief`) | 7 s (`brief`) |
| Edit reserved | 1 min 47 s | 1 min 21 s |
| Whole-bench moves tried | None; the handoff says the history ruled them out | None; the first measurement's `CONFLICT` ruled them out |
| Repair | Moved each leg's bottom vertices onto the ground at their own XY | The same, by a vertical ray per vertex |
| Attempts to pass | 1 | 1 |
| Published | Sequence 2; native check passed; relations `OK` on all legs within 5 µm | The same, within 1 µm |

I verified both projects independently with the installed runtime. Each published checkpoint is byte-for-byte the file whose relation measurement passed, its contract check passed with no failures, and neither edit touched the bench top. Both agents also reported the bounding-box estimate's false `PENETRATION` and said they did not act on it.

**Reading the result.**
- **Exit criterion met.** A fresh continuation avoided repeating an ineffective repair, and agent H explicitly used the history to do so.
- **History effect not isolated.** The control shows the measured `CONFLICT` already tells an agent that no rigid move works. On this task the classification did the work. A failure the classification cannot explain, such as two different per-leg repairs that each make `NO_PROGRESS`, would test the history on its own.
- **Missing review views.** Both agents had to write their own views file to render, because the project had no `review_views` decision. A project template that records both decisions at `start` would remove that step.
- **Directional evidence.** These are two runs on a small, exactly measured scene.

Local evidence is under `runs/relations-0.9.0-2026-10-10/`, excluded from Git.

## Limits

- **One family.** Only `supported_by` is qualified. Clearance along a path, a downpipe meeting its gutter and contact between arbitrary objects are not covered.
- **Vertical rays.** Each footprint point is tested straight down and up against the declared supports only. Objects resting on walls or steep faces need another method, and undeclared objects in between are ignored.
- **Thresholds.** The 20% `NO_PROGRESS` threshold and the two-attempt window are design choices, not calibrated values.
- **Trust.** Measurements are producer claims bound by hashes. The history records what an agent says it tried; it does not verify the strategy text.
- **Evidence kinds.** Relation reports are not yet a coordination evidence kind.
