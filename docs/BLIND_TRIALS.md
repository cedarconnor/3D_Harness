# Independent agent comparison

Entry point: invoke the project skill `$dcc-blind-test` in a client that discovers `.agents/skills`, or ask the coordinator to read `.agents/skills/dcc-blind-test/SKILL.md`. The skill dispatches fresh agents when the host supports them; it is not given to trial builders.

The coordinator now prepares six frozen packets in two randomized blocks, each containing one plain-MCP build, one build with three process skills, and one build with those skills plus the native measurement helper. Each build uses a new agent with `fork_turns="none"`. A different fresh agent performs each late revision. Neither agent receives the planning chat or another trial's output. The engineering courtyard is excluded from trial inputs.

This is a single-blind artist comparison with procedural context isolation. Builders can see their own available methods. The coordinator knows assignments. Agent filesystem/tool access, the host's ambient skill catalog and automatically supplied general memory summary are shared; packet rules do not create a sandbox. A clean-room or double-blind claim would be incorrect. Record any exposure and protocol deviations. Model parameters inherit the same coordinator defaults without per-run overrides; where exact client metadata, tokens or billing are unavailable, record that fact rather than inventing usage.

## Prepare and dispatch

Use a fresh geometry-free native starter and the pinned asset kit. The supplied recipe creates three cameras, a sun, a packed HDRI and a retained shared stone material, with no completed geometry. It does not import the engineering construction fixture.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/blind_starter.py -- --out runs/new-fixtures/starter.blend --kit runs/engineering-2026-10-03/assets
python -m dcc_harness.blind prepare --root runs/new-round --starter runs/new-fixtures/starter.blend --kit runs/engineering-2026-10-03/assets --templates experiments/courtyard-blind --helper-root dcc_harness
```

The destination must not exist. Preparation copies the fixed inputs and hashes them, including the exact prompts, skills and five-file runtime helper. The private assignment manifest is `private/manifest.json`; production agents receive only `trials/<opaque-id>/`. No generated scene, fixture construction code, earlier transcript or private manifest is included. Global skills are not copied into packets. A receives no process skill bodies or helper. B receives three frozen task-specific skills. C receives exactly the same skills plus the measurement package and instructions.

Dispatch manifest `run_ids` in order. The host coordinator uses `collaboration.spawn_agent` with `fork_turns="none"`, unchanged model settings, and a short instruction to read that packet's `PROMPT.md`. This is an agent-client orchestration step, not a Python function that can silently launch models. The file CLI does not schedule agents, charge a model account or implement a background daemon.

Only one agent at a time may own the live Blender writer. Preserve the user's current native file and remember it for restoration. Confirm the writer has finished or reconcile an unknown mutation before another agent loads its file. Directory separation alone cannot protect a shared live scene. Read-only rendering/evaluation may use separate background processes against immutable files.

In this host's October 3 session, live `execute_blender_code` works. The MCP background endpoint fails with `Blender executable not found at 'blender'`; it needs a correctly configured `BLENDER_PATH` and server restart before it can be qualified. Trials therefore use the live MCP writer sequentially. The independent evaluator uses the known native binary directly. No third-party server files or user settings were patched to conceal that limitation.

Verify frozen inputs before and after each agent:

```powershell
python -m dcc_harness.blind verify --root runs/new-round --run-id t-0123456789ab
```

The common brief requires a packed `output/pre.blend` and `output/CONTINUE.md`. Record agent task identity, start/end time, output hashes, known render/capture usage and any leaks privately. Time and capture ceilings are coordinator obligations; the file packager is not a resource sandbox. Keep failed/capped trials in the six-slot comparison. Do not silently replace them, coach one method using another's results, or revise the frozen method halfway through a round.

## Replace the context

```powershell
python -m dcc_harness.blind release-revision --root runs/new-round --run-id t-0123456789ab
python -m dcc_harness.blind verify --root runs/new-round --run-id t-0123456789ab --phase revision
```

Release accepts the pre-revision bytes once and copies only the native scene and handoff note into a new `revisions/<opaque-id>/` context. It reissues the frozen common inputs and assigned methods plus the identical late revision. It deliberately excludes builder scripts, logs and transcript. It rejects missing handoffs, changed frozen inputs and repeated publication. File acceptance is not native validity or artistic approval.

Spawn a new agent with `fork_turns="none"`; do not use a follow-up on the original builder. The revision changes the shared stone color and bench-seat width while preserving layout, lighting, cameras and unrelated assets. The pre-revision lighting is a preservation baseline, not an assertion that an artist approved every build. The new agent writes `output/post.blend` and `output/CONTINUE.md`.

Historical paths in the handoff are informational; uniformly instruct revision agents to open only their packet's supplied `pre.blend`. After the writer stops, `python -m dcc_harness.blind accept-revision --root runs/new-round --run-id t-0123456789ab` verifies its inputs and freezes only the two result files under `private/completed/`. Evaluate that immutable snapshot. Missing files, changed inputs and repeated acceptance are refused; byte acceptance still does not imply a passed trial.

## Independent evidence and artist review

`scripts/evaluate_blind_checkpoint.py` opens each native checkpoint in a fresh process, observes actual content, runs the same common checks and optionally compares pre/post. Its process success means the evaluation finished; read `report.json.passed` for the technical verdict. Failed checks still produce evidence instead of disappearing from the comparison. The evaluator never saves over its input and verifies the source checksum.

Checks include required identities and seat dimensions, six to eight mesh families, shared materials, linked repeats, packed images, fixed camera/sun/world/preset values, and the specified revision. The only permitted material edit is the named stone input; bench geometry can change while transforms and seat center stay fixed. Packed-image locations are normalized for comparison while image content hashes and color settings remain checked. General topology quality, arbitrary node/modifier semantics, animation and artistic quality are not certified.

The audit found low-bit differences in Blender's evaluated bevel UV coordinates when extracting the same unchanged file. The independent evaluator retains raw observations and permits at most `2e-7` absolute evaluated-UV drift only with exact authored mesh/UV hashes, evaluated geometry, modifier settings, layer names and array sizes. Same-file drift reached `1.1920928955078125e-7`; the earlier `1e-7` guard produced a retained false failure. Every pre/post checkpoint was reobserved under the corrected coverage, without rerunning production agents or replacing images. Authored UV changes remain exact, and geometry hashes are never relaxed. The round's copied helper remains frozen, including its exact evaluated-UV hash limitation; this evaluator correction is not silently added to one trial method.

The evaluator captures the same three views before and after. Its render preset is fixed in a disposable process; it first records and flags any actual checkpoint preset violation. Reserve capture/render budget for these independent captures. Compare hard-check results separately from aesthetic preference and do not feed comparative grades back to production agents.

`dcc_harness.blind_review.export_review(entries, public_folder, private_receipt)` exports six anonymous image slots with randomized labels, stripped PNG descriptive metadata, a common gallery and score form. The private receipt retains the source mapping and hashes. Missing or invalid images remain explicit unavailable cells. The public package excludes method names, source paths, scripts and technical reports. Image-only review cannot score native editability; leave it unassessed until a separate native review. AI critiques can supplement, but cannot replace, the artist's scores or measured repair time.

The two-repeat investment gate in the build plan remains unchanged. Separate agents and passing engineering tests do not establish that one method wins, that long-horizon production is qualified, or that an unseen brief will succeed.

The exported HTML was checked through source inspection and a separate agent's image/metadata audit. Browser interaction/download was not exercised: the browser tool blocked the local file URL, and no alternate route was used to bypass that restriction.
