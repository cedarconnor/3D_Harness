# Agent quick reference

Version 0.17.0. The exact command sequences for the most common work, for an agent continuing a 3D Harness project. Every command below is checked against the real parser by `tests/test_quick_reference.py`. Values in `<angle brackets>` and capitalized placeholders such as `PARENT_ID` are yours to fill; quote every path.

## 1. Orient

```powershell
python -m dcc_harness brief "<project>"
python -m dcc_harness next "<project>"
```

`brief` prints where the project stands, the permitted next steps with commands already filled from the record, open feedback and stages, the recorded brief, the latest handoff and the rules. `next` returns the same steps as JSON. Both only read. Start every session with `brief`, and run it again after any command that changes the project. If the status is `RECONCILE`, do only what `next` lists.

## 2. Make a scoped edit

```powershell
python -m dcc_harness observe "<active checkpoint .blend>" --blender "<BLENDER>" --output-dir "<work>/observe-current"
python -m dcc_harness begin-edit "<project>" --parent PARENT_ID --current "<active checkpoint .blend>" --observation "<work>/observe-current/observation.json" --script "<work>/edit.py" --contract "<work>/contract.json" --label "<new step label>"
```

`brief` fills `PARENT_ID` and the checkpoint path. Labels must be new. `begin-edit` returns `edit` (an ID) and `script`, the retained copy. Run that retained copy once, in background Blender, against an owned copy of the checkpoint. The script must save a new `.blend`; it never overwrites the accepted file.

```text
& "<BLENDER>" --background --factory-startup --python-exit-code 1 "<owned copy .blend>" --python "<retained script path>"
```

Then observe the saved result, render it (section 3) and look at the images, and finish:

```powershell
python -m dcc_harness observe "<work>/result.blend" --blender "<BLENDER>" --output-dir "<work>/observe-result"
python -m dcc_harness render "<work>/result.blend" --blender "<BLENDER>" --output-dir "<work>/result-views" --project "<project>"
python -m dcc_harness finish-edit "<project>" EDIT_ID --checkpoint "<work>/result.blend" --observation "<work>/observe-result/observation.json" --handoff "<work>/HANDOFF.md" --updates "<work>/decision-updates.json"
python -m dcc_harness finish-edit "<project>" EDIT_ID --checkpoint "<work>/result.blend" --observation "<work>/observe-result/observation.json" --handoff "<work>/HANDOFF.md" --updates "<work>/decision-updates.json" --reject-reason "<the visible defect>"
```

Use the second form, not the first, when the renders show a defect that the numbers miss. `decision-updates.json` may be `{}`. The handoff says what changed, what's next and any gotchas.

A contract names everything that must hold afterwards and permits only the intended change. This one allows one material input and requires the objects it must preserve:

```json
{
  "schema": "dcc.continuity.contract.v1",
  "allowed_material_inputs": {"timber": {"Principled BSDF": {"Roughness": 0.8}}},
  "allowed_new_prefixes": [],
  "allowed_object_prefixes": {},
  "spec": {
    "schema": "dcc.spec.v1",
    "required": {"bench.top": {"type": "MESH"}, "review.camera": {"type": "CAMERA"}},
    "required_materials": ["timber"],
    "material_nodes": {"timber": {"Principled BSDF": {"Roughness": 0.8}}}
  }
}
```

List every object that must survive under `required`; `resume PROJECT --focus ID` shows an object's measured fields. New objects need an `ext.` prefix in `allowed_new_prefixes`. Grant per-object fields with `allowed_object_prefixes`, such as `{"ext.bench.": ["matrix_world", "bounds", "dimensions"]}`, never the whole scene. A new light also needs `allowed_new_lights` (for example `["ext.lamp."]`), and a world or other scene-setting change needs `allowed_scene_fields` (for example `["world"]`). Deleting an object needs its exact ID in `allowed_deleted_ids`. To change one modifier setting, name it in `allowed_modifier_settings` (for example `{"bench.top": {"Edge": ["segments"]}}`) and grant the geometry fields it changes; to set a node field, use `allowed_material_node_fields` (for example `{"timber": {"Tint": {"blend_type": "MULTIPLY"}}}`).

## 3. Render review views

```powershell
python -m dcc_harness render "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/after-views" --project "<project>"
python -m dcc_harness render "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/after-views" --views "<work>/views.json" --detach
python -m dcc_harness render-wait "<work>/after-views" --timeout 100
```

`render` opens the saved file in a fresh background Blender, renders every view and never saves. It writes `<VIEW_ID>.png`, `views.json` and `receipt.json`, and returns `evidence` entries for each view, with paths relative to the output folder's parent, ready to paste into a response or submission. `--project` uses the project's `review_views` decision; `--views` takes a file. With `--detach` it returns `QUEUED` at once; call `render-wait` until the state is `done` or `failed`. Renders run one at a time on a machine.

A view definition, recorded once as the decision `review_views` (at `start`, or in any edit's decision updates):

```json
{
  "schema": "dcc.review.views.v1",
  "render": {"engine": "CYCLES", "resolution": [960, 540], "samples": 32, "seed": 0},
  "views": [
    {"id": "REVIEW_WHOLE", "purpose": "whole", "camera": {"object_id": "review.camera"}},
    {"id": "REVIEW_DETAIL", "purpose": "detail", "camera": {"object_id": "review.camera"}, "border": [0.18, 0.77, 0.15, 0.66]},
    {"id": "BENCH", "purpose": "detail", "camera": {"lens": 35, "location": [3.0, -4.0, 2.0], "target": [0.0, 0.0, 0.6]}}
  ]
}
```

`object_id` uses a camera in the scene by its stable ID. `lens`, `location` and `target` make a review-only camera that is never saved. `border` crops as fractions `[min_x, max_x, min_y, max_y]`. Engines are `CYCLES`, `BLENDER_EEVEE` and `BLENDER_WORKBENCH`. Keep the definition fixed: feedback verification compares the settings digest, so a changed view means a changed review.

## 4. Measure what rests on what

```powershell
python -m dcc_harness relations "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/relations-1" --project "<project>" --strategy "<what this file changes>"
python -m dcc_harness relations "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/relations-2" --spec "<work>/relations.json"
```

`relations` opens the saved file in a fresh background Blender and never saves. For each subject it casts vertical rays through the subject's lowest vertices, its footprint, against the declared support surfaces. Each subject gets one finding:

- **Code:** `OK`, `GAP`, `PENETRATION`, `OFF_SUPPORT` or `MISSING_TARGET`.
- **Error:** in metres, positive for a gap and negative for penetration, taken from the footprint point closest to contact.
- **Spread:** the difference between the footprint's highest and lowest points, such as a corner lifted on a slope.

`CONFLICT` means that some subjects float while others sink, so moving the whole group cannot fix it: adjust them individually. A `bounds_estimate` that disagrees comes from bounding boxes and only permits inspection; never repair from it. The command exits 1 when a relation fails.

With `--project`, each measurement joins the project's relation history, together with the `--strategy` text naming the repair the file tries. `brief` shows the history and warns when the last two attempts swung between gap and penetration (`OPPOSING`) or barely changed the error (`NO_PROGRESS`). Read it before choosing a repair, and don't repeat a strategy it marks as ineffective.

A definition, recorded once as the decision `relations`:

```json
{
  "schema": "dcc.relations.v1",
  "relations": [
    {"id": "bench-on-ground", "kind": "supported_by",
     "subjects": ["bench.leg.0", "bench.leg.1", "bench.leg.2", "bench.leg.3"], "support": ["ground"],
     "max_gap": 0.005, "max_penetration": 0.01, "footprint": 0.002}
  ]
}
```

## 5. Ask the artist to review

```powershell
python -m dcc_harness review-page "<project>" --output-dir "<work>/review-1" --blender "<BLENDER>" --reopen
python -m dcc_harness review-import "<project>" "<export .json>" --page "<work>/review-1"
```

`review-page` writes a local page comparing the active checkpoint with its parent, with renders, changes by stable ID, notes and any stage waiting for review. Give the artist `index.html`. The export they download comes back through `review-import`, which completes the stage with their answers and adds their notes. When submitting a stage the artist must decide on, add `questions` to the submission, each with a `default` where you have one; see the [review page guide](REVIEW_PAGE.md).

Only the artist can approve. An export that approves a stage, or any payload whose reviewer or authority is the artist, needs the owner's confirmation at an interactive terminal and is refused from your session. Hand the artist the exact command to run in their own terminal ([owner approval](OWNER_APPROVAL.md)). Never claim the artist role, remove the session variables or pipe in a code. Exports with only notes import from your session.

## 6. Respond to a feedback note

Write the response with `{"path": ...}` references, fill the hashes, then record it. `next` gives the expected revision and a fresh request ID.

```json
{
  "schema": "dcc.feedback.response.v1",
  "note_id": "NOTE_ID",
  "author": "<your name>",
  "disposition": "implemented",
  "change": "Set the shared timber Roughness from 0.65 to 0.8 in edit EDIT_ID; nothing else changed.",
  "result": {"checkpoint_id": "CHECKPOINT_ID", "checkpoint_sha256": "CHECKPOINT_SHA256"},
  "evidence": [
    {"kind": "native_contract", "before": {"checkpoint_id": "PARENT_ID", "checkpoint_sha256": "PARENT_SHA256"},
     "contract": {"path": "contract.json"}},
    {"kind": "whole_scene_render", "render": {"receipt": {"path": "after-views/receipt.json"},
     "settings": {"path": "after-views/views.json"}, "view_id": "REVIEW_WHOLE"}}
  ]
}
```

```powershell
python -m dcc_harness fill-hashes "<work>/response.draft.json" "<work>/response.json"
python -m dcc_harness feedback-respond "<project>" --response "<work>/response.json" --expected-revision REVISION --request-id REQUEST_UUID
```

`result` is the current checkpoint, from `brief`. Paths are relative to the response file's folder. If the change deletes one of the note's objects, list it in `removed_targets` and cite the contract that permits the deletion; never hide an object to keep a note verifiable. Say exactly what changed, never "addressed". Don't verify your own response; a separate reviewer does, with `feedback-verify`.

## 7. Submit a stage

```powershell
python -m dcc_harness requirements "<project>" STAGE_ID --out "<work>/requirements.json"
python -m dcc_harness fill-hashes "<work>/stage.draft.json" "<work>/stage.json"
python -m dcc_harness stage-submit "<project>" --submission "<work>/stage.json" --expected-revision REVISION --request-id REQUEST_UUID
```

`requirements` lists the evidence the stage needs and returns a `skeleton`. Save the skeleton as `stage.draft.json`, replace every `<placeholder>`, and keep `feedback_ids` exactly as given. If the workflow pinned learned checks, `requirements` also lists them with their current result. For each relation check, save its `spec`, run the `relations ... --spec` command it gives and keep the `check_measurements` path. A failed or unmeasured check blocks completion; fix the scene, don't argue with the check.

## 8. Propose a learned check

When the artist's note describes an error that no check caught, and a rule can measure it, propose a check. The rule must fail on the note's checkpoint and pass on the fix. Taste is not a check. See [learned checks](LEARNED_CHECKS.md) for the rule and proposal formats.

```powershell
python -m dcc_harness check-propose "<project>" --proposal "<work>/proposal.json" --expected-revision REVISION --request-id REQUEST_UUID
python -m dcc_harness checks "<library>"
python -m dcc_harness check-occurrence "<library>" --project "<project>" --note NOTE_ID --check CHECK_ID
```

Only the owner approves a check, with `check-approve` in their own terminal; give them the proposal revision. If an existing library check covers the error, count it with `check-occurrence` instead of proposing it again.

## Stops

| Message | Meaning | Do |
|---|---|---|
| `Stale parent; resume the current project` | Another checkpoint was published | Run `brief` and use the new parent |
| `Current saved file differs from the accepted checkpoint` | `--current` is not the accepted file | Pass the active checkpoint path from `brief` |
| `Unresolved edit; inspect and reconcile before another write` | A reservation has no outcome | Finish it as `next` says, with `--reconciled` if it may have run |
| `Workflow lock exists` | A command is running or stopped partway | Inspect; never delete the lock blindly |
| `REJECTED_RETAINED`, exit 1 | The contract failed | Read `failures`; fix with a new reservation |
| `Stale coordination revision; resume before continuing` | Something was recorded since you read the revision | Run `next` for the current revision and a new request ID |
| `Missing or changed artifact` | A hash or path in the payload is wrong | Rerun `fill-hashes` on the draft |
| `ALREADY_COMMITTED` | A retry of a request that already succeeded | Use the returned result; do nothing again |
| `Owner approval is refused inside an agent session` | The payload claims the artist's authority | Give the artist the exact command to run in their own terminal; never work around it |
| `Owner approval required` | An artist authority reached the record without the owner's confirmation | The same: only the artist approves |
| `Relaxing an artist-required stage` | The binding lowers a stage the manifest gives to the artist | Keep the manifest's policy, or ask the artist to bind it |
| `The rule does not fail on the note` | The proposed rule would not have caught the error | Change the rule, or keep the lesson as a skill note |
| `Taste stays project direction` | The note is taste, not an error | Record it in the brief or decisions |
| `Pinned library checks failed or were not measured` | A pinned check fails, or a relation check has no measurement | Fix the scene, or add the measurement `requirements` names, then submit again |
| `Missing library` | A collection instance's library file is not where its stored relative path points | Work on the copy beside its libraries, never the stored checkpoint |
| `HAS_ISSUES` from `observe`, exit 1 | The saved file has missing IDs or unsupported data | Read the issues; see the scene adoption guide |
