# P10: Fixed-view render command

Plan for [build-plan](../../BUILD_PLAN.md) item P10, written October 10, 2026, at version 0.7.0. Target version: 0.8.0, because it adds commands.

## Problem

Feedback evidence and stage submissions need review renders bound to a checkpoint: a `dcc.quality.renders.v1` receipt, the images, and the view settings whose digest the receipt carries. The package has no command that makes them. Every comparison agent relied on a fixture-specific tool (`scripts/feedback_native_probe.py render`), and the scripts define cameras four different ways: the scene camera with a hardcoded crop, `native_id`, `object_id`, and an anchor with an offset. In the 0.7.0 run the agent also had to work out which checkpoint the packet's before-views came from.

Renders are also the slowest native step. Cycles at production settings can exceed an agent tool's time limit, and two sessions rendering at once compete for the GPU.

## Scope

### View definition

One packaged format, `dcc.review.views.v1`:

```json
{
  "schema": "dcc.review.views.v1",
  "render": {"engine": "CYCLES", "resolution": [960, 540], "samples": 32, "seed": 0},
  "views": [
    {"id": "REVIEW_WHOLE", "purpose": "whole", "camera": {"object_id": "review.camera"}},
    {"id": "REVIEW_DETAIL", "purpose": "detail", "camera": {"object_id": "review.camera"}, "border": [0.18, 0.77, 0.15, 0.66]},
    {"id": "GARDEN", "purpose": "whole", "camera": {"lens": 48, "location": [11, -16, 7], "target": [0, 3, 1.3]}}
  ]
}
```

- A camera is either an existing camera object by stable ID (`object_id`) or a review-only camera given by `lens`, `location` and `target`, created in the disposable process and never saved.
- `border` crops a view as fractions `[min_x, max_x, min_y, max_y]`.
- `render` holds the engine (`CYCLES`, `BLENDER_EEVEE` or `BLENDER_WORKBENCH`, the names Blender 5.1 accepts), resolution, samples and seed, and optionally `view_transform`, `look` and `exposure`. Values not given are recorded from the scene.
- View IDs are unique; purposes are `whole` and `detail`, matching the evidence kinds.

A project holds its definition as the decision `review_views`, set at `start` or through any edit's decision updates, so every session renders the same views.

### `render`

```text
python -m dcc_harness render SAVED.blend --blender PATH --output-dir NEW_FOLDER (--project PROJECT | --views FILE) [--detach]
```

- Opens the saved file in a fresh background Blender with the observe launcher's flags, renders each view, and never saves. Checks that the source bytes are unchanged before opening, after opening and after rendering.
- Writes `<VIEW_ID>.png`, `views.json` and `receipt.json` into the new folder. `views.json` holds the definition plus what was resolved in the scene: each camera's world matrix, lens, sensor and clipping, the frame and the colour settings. Its digest is the receipt's `views_digest`, so changing the camera or the definition changes the digest that feedback verification compares.
- Returns `RENDERED` with the image paths, timing and ready-made evidence entries (`whole_scene_render` or `detail_render`, by purpose) whose paths are relative to the output folder's parent, ready for `fill-hashes`.
- Rejects links and junctions, a non-`.blend` source, an existing output folder, both or neither of `--project` and `--views`, a project without `review_views`, an invalid definition, and an `object_id` that is not a camera.

### Queue

- One render at a time per machine. A job waits for an operating-system file lock in the temporary folder, which is released if the process dies, so a crash cannot leave the queue stuck.
- Each job records its state in `status.json` inside its output folder: `waiting`, `running`, `done` or `failed`, with the result or error.
- `--detach` starts the job in a separate process and returns at once with `QUEUED` and the output folder, which is the job's ID. `render-wait FOLDER [--timeout SECONDS]` waits up to the timeout (default 100 s) and returns the current state; call it again until the state is `done` or `failed`.

### Guidance

`brief` and `next` gain a render step when the project has `review_views`, with the command filled in. The quick reference and the everyday-workflow guide show the definition and both modes.

## Qualification

- **Portable tests.** Definition validation; argument and path rejection; `--project` reading the current decision; status transitions and the error record with a stand-in worker; the lock admitting one job at a time across processes; `render-wait` timing out with the current state; evidence entries that pass coordination validation once hashed; guidance steps.
- **Native, source and installed.** On the comparison fixture: an `object_id` view with a crop, and a review-only camera. Renders twice with identical bytes and digests, and the digest changes when the camera moves. The source file stays unchanged. A response citing the render's evidence entries commits. Two detached jobs started together run one after the other, and `render-wait` reports both done. A missing camera and an existing output folder fail before any render.
- **Comparison.** None planned: the render tool already made renders cheap for agents. The native fixtures establish correctness, and later fresh-agent runs use the packaged command instead of the fixture tool.

## Out of scope

- Animation and frame ranges. A view renders the scene's current frame.
- Visual judgement. The command makes images; people and agents review them.
- GPU selection. Renders use Blender's default device; the device is recorded in the run report, not in the view settings.
