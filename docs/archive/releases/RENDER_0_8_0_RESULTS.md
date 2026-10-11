# Fixed-view render command — 0.8.0

Version 0.8.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P10, following its [implementation plan](../plans/P10_RENDER_COMMAND.md). It adds one packaged way to render a project's review views, replacing the fixture-specific render tool that every comparison agent relied on and the four camera formats spread across the scripts. Renders are bound to the source file's hash, never save it, are byte-identical when repeated, and run one at a time per machine, optionally in a detached process.

## Delivered

- **View definition `dcc.review.views.v1`.** Render settings (engine, resolution, samples, seed, and optionally view transform, look and exposure) plus a list of views. Each view has an ID, a purpose (`whole` or `detail`) and a camera: either a scene camera by stable ID or a review-only camera given by lens, location and target. A view may also crop with `border`. A project holds its definition as the decision `review_views`.
- **`render SAVED.blend --blender PATH --output-dir NEW (--project PROJECT | --views FILE) [--detach]`.** Opens the file in a fresh background Blender with the observe launcher's flags, renders each view and never saves. It checks the source bytes before opening, after opening and after rendering. It writes `<VIEW_ID>.png`, `views.json` and a `dcc.quality.renders.v1` receipt:
  - `views.json` holds the definition plus what was resolved in the scene: each camera's world matrix, lens, sensor and clipping, the frame, the colour settings and the pixel aspect.
  - The receipt's `views_digest` is that file's digest, so moving a camera or editing the definition changes the digest that feedback verification compares.
  - The result includes ready `whole_scene_render` and `detail_render` evidence entries, with paths relative to the output folder's parent.
- **Reproducible files.** Blender's stamp metadata is disabled for review renders, and the PNG text chunks that Cycles writes regardless are removed. Without that, two renders of the same file differed only in embedded dates, local paths and timings.
- **Queue.** One render at a time per machine, under an operating-system file lock that a crashed process releases. Each job records `waiting`, `running`, `done` or `failed` in its own `status.json`, with start and finish times and the result or error. `--detach` returns `QUEUED` at once, and `render-wait FOLDER [--timeout S]` returns the current state after up to that many seconds.
- **Guidance.** When a project has `review_views`, `next` and `brief` offer a render step for the active checkpoint, and a candidate render before `finish-edit` while an edit is reserved. The quick reference has a render section whose definition example the suite validates. The everyday-workflow and structured-feedback guides, the `dcc-harness` skill and the README describe the command.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 304 tests: 302 passed, two Windows symlink-permission skips. 21 tests are new: 19 for rendering and the queue, 2 for the guidance render steps. |
| Installed-wheel suite | 304 tests from a standalone install of the wheel: 298 passed and 6 skipped, the same two plus the four quick-reference tests that check source-tree documentation |
| Wheel integrity | All 41 runtime and template files byte-identical to the sources. SHA-256 `26de01b4e087d6c59b2d81bcb53c56955a9aa8dc5bf8f4366fa3a87b32e292c8` |
| Native, source and installed | `scripts/qualify_render.py` on the comparison fixture, with three views: the scene camera, a cropped detail of it, and a review-only camera |

The native script checked the following, from both runtimes:

- **Repeat renders.** Two renders were byte-identical in every image and in the settings digest.
- **Moved camera.** A copy with the scene camera moved 0.5 m changed the digest and both of that camera's images, while the review-only camera's image stayed byte-identical.
- **EEVEE.** It rendered under `BLENDER_EEVEE`, the name Blender 5.1 accepts; `BLENDER_EEVEE_NEXT` is rejected.
- **Failures.** A missing camera ID failed in Blender with a plain message and a `failed` status. An existing output folder was refused before Blender started.
- **Feedback evidence.** The returned evidence entries committed in a feedback response, and both render reports passed.
- **Project definition.** A project started with a `review_views` decision rendered through the exact command `next` printed, with the same digest as the views file.
- **Detached jobs.** Two jobs queued together finished one after the other without overlapping.
- **Source file.** It was unchanged throughout.

The 0.7.0 guidance qualification also passed again on the 0.8.0 wheel.

**Fixed during qualification.** The first native run found that repeat renders had identical pixels but different files: Blender stamps and Cycles timing chunks embed dates, local paths and timings. The worker now disables stamps and strips PNG text chunks, with a portable test that image chunks stay byte-for-byte. `BLENDER_EEVEE_NEXT` was dropped from the accepted engines after Blender 5.1 rejected it.

Local evidence is under `runs/render-0.8.0-2026-10-10/`, excluded from Git.

## Limits

- **Still images only.** A view renders the scene's current frame.
- **Device.** Renders use Blender's default device, which is the CPU under factory settings. The device and timings go in `report.json`, not the view settings, so the digest does not change between devices; GPU renders of the same settings may not be byte-identical to CPU ones.
- **Queue order.** The lock allows one render at a time; waiting jobs start in no guaranteed order.
- **Trust.** Images are evidence for review, not a quality verdict. Receipts remain producer claims, bound by hashes.
- **Old renders.** Renders made with earlier tools carry a different settings format, so a note anchored to such a render cannot be verified against a new render of the "same" view. Re-anchor the note or render with the old tool.
