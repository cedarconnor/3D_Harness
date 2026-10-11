# Agent quick reference

Version 0.8.0. The exact command sequences for the most common work, for an agent continuing a 3D Harness project. Every command below is checked against the real parser by `tests/test_quick_reference.py`. Values in `<angle brackets>` and capitalized placeholders such as `PARENT_ID` are yours to fill; quote every path.

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

List every object that must survive under `required`; `resume PROJECT --focus ID` shows an object's measured fields. New objects need an `ext.` prefix in `allowed_new_prefixes`. Grant per-object fields with `allowed_object_prefixes`, such as `{"ext.bench.": ["matrix_world", "bounds", "dimensions"]}`, never the whole scene.

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

## 4. Respond to a feedback note

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

`result` is the current checkpoint, from `brief`. Paths are relative to the response file's folder. Say exactly what changed, never "addressed". Don't verify your own response; a separate reviewer does, with `feedback-verify`.

## 5. Submit a stage

```powershell
python -m dcc_harness requirements "<project>" STAGE_ID --out "<work>/requirements.json"
python -m dcc_harness fill-hashes "<work>/stage.draft.json" "<work>/stage.json"
python -m dcc_harness stage-submit "<project>" --submission "<work>/stage.json" --expected-revision REVISION --request-id REQUEST_UUID
```

`requirements` lists the evidence the stage needs and returns a `skeleton`. Save the skeleton as `stage.draft.json`, replace every `<placeholder>`, and keep `feedback_ids` exactly as given.

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
| `HAS_ISSUES` from `observe`, exit 1 | The saved file has missing IDs or unsupported data | Read the issues; see the scene adoption guide |
