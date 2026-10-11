# Before/after review page — 0.11.0

Version 0.11.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P4, following its [implementation plan](../plans/P4_REVIEW_PAGE.md). It gives the artist something to look at: a local page comparing two checkpoints, built from verified records. The page shows bound renders, what changed by stable ID, every feedback note, and a stage waiting for review with its questions preselected to their defaults. What the artist decides on the page comes back through one command that completes the stage and adds their notes, and can safely be run twice.

## Delivered

- **`review-page PROJECT --output-dir NEW`** writes `index.html`, `page.json` and the renders it shows, comparing the active checkpoint with its parent by default.
  - **Renders.** It either renders both stored checkpoints (`--blender`, with the project's `review_views` or `--views`) or binds render folders made by `render`. Each receipt must match its checkpoint's hash and every image hash is checked. A changed image, or a receipt for another checkpoint, is refused. Differing view settings between the two sides are flagged.
  - **Reopen.** With `--reopen`, the after checkpoint is observed again and compared by the qualified comparator, as `native_reopen` evidence is.
  - **Layout.** The page shows the stage waiting for review, a sheet of every view, before and after per view with hold-to-compare, and the changes by stable ID with linked notes. It lists every note, lets the reviewer write new notes, optionally attached to an object or pinned on an after image, and exports them.
  - **Implementation.** The page builds its DOM with `textContent` from embedded JSON, so note text cannot inject markup. The generator is its own module, imported only by its commands, and uses only the standard library.
- **`review-import PROJECT EXPORT --page FOLDER`** refuses an export whose page digest differs from the folder's `page.json`. It completes the stage first, then adds each note. Request IDs are derived from the export's content, so a repeated import returns `ALREADY_COMMITTED` without duplicating anything.
- **Submission questions.**
  - A stage submission may carry up to 12 `questions` with optional `choices` and a `default`.
  - A completion review may carry `answers`. An unanswered question takes its default, one without a default must be answered, and free answers beside the choices are allowed.
  - The receipt records each answer and whether it was the default. Submissions and reviews without them are unchanged.
- **Docs.** A [review page guide](../../guides/REVIEW_PAGE.md), a quick-reference section, the structured-feedback guide, the skill and the README describe the commands.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 356 tests: 354 passed, two Windows symlink-permission skips. 20 tests are new: 7 for questions and answers, 13 for the page, binding, reopening and import. |
| Installed-wheel suite | 356 tests from a standalone install of the wheel: 350 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 44 runtime and template files byte-identical to the sources. SHA-256 `e3e4f9e9a001cfd415fa7e1312edd34796f59d37c70380a082637d8bd8e84941` |
| Native, source and installed | `scripts/qualify_review_page.py` on a copy of the 0.6.0 comparison project |
| Regression | The guidance, render, relations and instances qualifications passed again on the 0.11.0 wheel |

The native script checked the following from both runtimes:

- **Page contents.** It rendered both checkpoints and built the page. `bench.top` was listed as changed with its two linked notes, the timber material as changed, and the two views with matching settings.
- **Reopen.** The reopened after checkpoint matched within float noise in nine objects' evaluated UVs.
- **Note round trip.** An export shaped exactly as the page writes it, a note pinned on the after detail render, committed and then replayed as `ALREADY_COMMITTED`. A rebuilt page showed the note pinned on the after image.
- **Stage review.** The script bound a three-stage workflow and submitted the direction stage with two questions. A rebuilt page showed the submission. An approval that changed one answer completed the stage and recorded `finish: Oiled` as the default, `light: Warm` as chosen, and `artist_declared`.

**Browser check, by hand.** I served the page locally and drove it in the browser:

- The images loaded and **Show before** swapped the images while held.
- **Pin a note** placed a pin where the after image was clicked, and the note form produced the export above.
- The questions appeared with their defaults selected. Choosing Warm, approving and exporting wrote only `light: Warm`, and importing that export completed the stage.
- At phone width there is no horizontal scroll.

**Fixed during qualification.**

- **Reopen comparison.** The first reopen compared revisions strictly and reported a difference that was only cross-process float noise in evaluated UVs. It now uses the qualified comparator and distinguishes an exact match from a noise-only match.
- **Narrow screens.** The view sheet's minimum column width and long paths overflowed at phone width.
- **Unpinned notes.** Notes anchored to a view without a pin are now listed under that view.

Local evidence is under `runs/review-page-0.11.0-2026-10-10/`, excluded from Git.

## Limits

- **Attribution only.** The export's artist role is the reviewer's own claim; P12 will restrict who can import an approval.
- **Local only.** The page is a local folder, not hosted or shared.
- **Pins.** A pin is a fraction of the after image, meaningful only while that view's settings stay the same.
- **Libraries.** For projects that link libraries, render the working copy beside them and pass the render folders, since the stored checkpoint cannot resolve its libraries.
- **Pending submissions.** Only the newest submission waiting for review is shown. Completing it is refused as stale if anything was recorded after it.
