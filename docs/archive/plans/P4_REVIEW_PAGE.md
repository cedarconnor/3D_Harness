# P4: Before/after review page

Plan for [build-plan](../../BUILD_PLAN.md) item P4, written October 10, 2026, at version 0.10.0. Target version: 0.11.0.

## Problem

Artist review time is the scarce input to the investment gate, and the harness gives the artist nothing to look at. A reviewer reads JSON observations, opens render folders by hand, and cannot tell which objects changed between two checkpoints, which feedback note belongs to which object, or whether the before and after images used the same views. The October 6 [artist review page](../../studies/ARTIST_REVIEW_SESSION.md) showed that one page with large images, a full-screen viewer and hold-to-compare makes review fast. It was built by hand for one study.

## Scope

### `review-page`

```text
python -m dcc_harness review-page PROJECT --output-dir NEW_FOLDER [--from CHECKPOINT_ID] [--to CHECKPOINT_ID]
    [--before-views DIR --after-views DIR | --blender PATH [--views FILE]] [--reopen]
```

It writes a self-contained static page, `index.html` with its images beside it, comparing two checkpoints. By default these are the active checkpoint and its parent.

- **Changes by stable ID.** Objects added, removed, moved and otherwise changed, with the fields that changed, and changed materials, from the verified checkpoints' observations. A move gives the centre's displacement in metres.
- **Bound renders.**
  - **Views supplied.** Either render folders from `render` for each side, or `--blender`, which renders both stored checkpoints with the project's `review_views` decision or `--views`.
  - **Binding.** Each receipt must be bound to its checkpoint's hash, and every image's hash is checked. When the two sides' settings digests differ, the page says so, because the cameras or settings changed.
  - **Layout.** The page opens with a sheet of every review view, then a comparison per view, with a full-screen viewer and hold-to-compare.
- **Linked notes.** Every feedback note is listed with its status, acceptance and targets, next to the changed objects it names. A note anchored to a review view is pinned on that view's image for the checkpoint it was written against.
- **Owner questions.** If the newest stage submission is waiting for review, its note and questions appear with each default preselected. The page exports a `stage-complete` review payload with the answers. Accepting every default takes one click.
- **Feedback from the page.** The reviewer can write notes, optionally attached to an object or pinned on an after image. The page exports them as complete `dcc.feedback.note.v1` payloads for `feedback-add`, anchored to the after checkpoint and its bound render.
- **Verification shown on the page.** The checkpoint chain is verified when the page is generated, and receipts are bound by hash. With `--reopen` and `--blender`, the after checkpoint is observed again in a fresh Blender, and its revision must equal the stored observation's. The page states what was and was not checked.

The generator is its own module, imported only by the command, and uses only the standard library.

### Submission questions

- A stage submission may carry `questions`: up to 12, each with a unique `id`, `text`, and optional `choices` and `default`. A default must be one of the choices when choices are given.
- `stage-complete` reviews may carry `answers` keyed by question ID. A question without an answer takes its default, and one without a default must be answered. Unknown IDs are refused. The completion receipt records each answer and whether it was the default.
- Existing submissions and reviews without these fields are unchanged.

## Qualification

- **Portable tests.** Change classification from synthetic observations. Question and answer validation, including defaults, required answers, unknown IDs and choices. Page generation from a fixture project: changed objects, linked notes, questions with defaults selected, receipt binding, refusal of a receipt bound to another checkpoint, and the digest-mismatch warning. The exported review and note payloads, which must commit through the real commands. The CLI.
- **Native, source and installed.** On a copy of the 0.6.0 comparison project, whose two checkpoints extend the bench top and change the timber:
  - generate the page with `--blender`, rendering both checkpoints, and with `--reopen`;
  - check that `bench.top` is listed as changed with its linked notes, that the detail note is pinned, and that the reopened revision matches.
- **Browser.** Open the page in a browser and check the camera sheet, the comparison, hold-to-compare, one-click defaults and both exports. A note exported from the page commits through `feedback-add`.

## Out of scope

- Owner-only approval (P12). Any caller can still submit the exported review; this page is the channel P12 will restrict.
- Hosting or sharing the page. It is a local folder.
- Animation and turntables.
