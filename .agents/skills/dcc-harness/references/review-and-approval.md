# Review and approval

Read this for an artist review, a stage approval, a project with pinned skills, or a learned check.

## Feedback and stages

If `resume` includes `coordination`, inspect its outstanding feedback and eligible environment stages. [Structured feedback](../../../../docs/guides/STRUCTURED_FEEDBACK.md) has the binding rules and exact commands.

- Read the project's pinned skill copies under `pinned_files_root`. Do not silently substitute newer repository instructions.
- Routine stages can use agent review within the accepted brief. Explicit artist gates remain separate.
- `requirements PROJECT STAGE` gives a stage submission skeleton. Pinned checks it lists must pass before the stage completes.
- A changed runtime or partial record requires inspection, not an invented approval.

## Artist review

1. Build the page with `review-page PROJECT --output-dir NEW --blender PATH` and give the artist its `index.html`.
2. Import what they export with `review-import PROJECT EXPORT --page FOLDER`.
3. Add `questions` with defaults to a stage submission the artist must decide on.

Only the artist approves. An export with a stage approval, or any payload with the artist as reviewer or authority, is refused from your session. Hand the artist the exact command for their own terminal, and never claim the artist role or work around the refusal.

## Your own review

Use `review PROJECT`, inspect the referenced whole-scene and detail images, and separate measured preservation from visible quality. Add `--detach` to `render` and use `render-wait` for long renders. The `finish-edit` outcome separates `native_check_passed` from publication: a numeric pass must not override a reviewer's decision, and rejected attempts appear in the next resume packet. A `CONFLICT` in the relation history means the subjects must be adjusted individually.

## Learned checks

When an artist note shows an error no check caught and a rule can measure it, propose a [learned check](../../../../docs/guides/LEARNED_CHECKS.md) with `check-propose`. Taste stays project direction, and only the owner approves.
