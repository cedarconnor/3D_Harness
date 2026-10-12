# Review page

Version 0.11.0 adds a before/after review page for two checkpoints and a command that brings the reviewer's notes and decisions back into the project. The page is meant for the artist: large images, what changed by stable ID, and one-click answers.

## Build it

```powershell
python -m dcc_harness review-page "<project>" --output-dir "<work>/review-1" --blender "<BLENDER>" --reopen
python -m dcc_harness review-page "<project>" --output-dir "<work>/review-2" --before-views "<before render folder>" --after-views "<after render folder>"
```

By default the page compares the active checkpoint with its parent; `--from` and `--to` pick any two. Give it the review images in one of two ways:

- **`--blender`** renders both stored checkpoints with the project's `review_views` decision, or with `--views FILE`.
- **Render folders** made by `render` beforehand. Use this for a project that links libraries, rendering the working copy that sits beside them.

Each receipt must be bound to its checkpoint's hash, and every image hash is checked. Image paths must be relative and inside the render folder; both folders are checked before the page folder is created, and each file is copied to a new file and verified. With `--reopen`, the after checkpoint is observed again in a fresh Blender and compared with the stored observation by the qualified comparator. The page reports an exact match, a match within float noise in evaluated UVs, or the differences.

The folder holds `index.html`, `page.json` and the renders. Open `index.html` in a browser; it works offline from the folder.

## What the reviewer sees

1. **Stage waiting for review.** Shown when the newest submission is waiting and is for the after checkpoint on this page. A page built with `--to` an earlier checkpoint offers no approval; its build result lists the submission under `submissions_not_shown`, and `review-import` refuses an approval whose submission is for another checkpoint. It gives the stage's note and deliverables and the agent's questions, each with its default selected. **Accept every default and approve** does both in one click; a different choice or a free answer replaces the default.
2. **All review views.** One sheet of the after checkpoint from every camera.
3. **Before and after.** One panel per view. **Show before** swaps in the earlier image while held, and **Pin a note** places a note on the after image. Notes anchored to the view are listed under it.
4. **What changed.** Objects moved (with the distance), changed (with the fields), added and removed, and changed materials and scene settings, each with its linked notes.
5. **Feedback notes.** Every recorded note with its status and acceptance.
6. **Add a note**, then **Export.** The export holds the new notes and, if the stage was approved, the review with the answers that differ from the defaults.

## Bring the export back

```powershell
python -m dcc_harness review-import "<project>" "<downloaded export .json>" --page "<work>/review-1"
```

`review-import` refuses an export from another or changed page. It completes the stage first, then adds each note as a `dcc.feedback.note.v1` anchored to the after checkpoint, with the pinned render. Request IDs come from the export's content, so running the same import again returns `ALREADY_COMMITTED` for each item instead of adding duplicates. If anything was recorded after the submission, completion is refused as stale; build a new page.

Since 0.12.0, an export that approves a stage is imported only by the artist, in their own terminal. The command shows the review and asks for a short code before committing anything. From an agent session it is refused and nothing is imported, notes included. An export with only notes imports from anywhere. See [owner approval](OWNER_APPROVAL.md).

## Limits

- **Owner approval is a guard.** An approval needs the artist's own terminal, which stops an agent approving its own work through the commands. It is not a wall against an agent with an unrestricted shell. Notes stay attributions.
- **Local only.** The page is a local folder; sharing or hosting it is up to you.
- **Pins.** Pins are fractions of the after image. A note pinned on a view keeps meaning only while that view's settings stay the same.
