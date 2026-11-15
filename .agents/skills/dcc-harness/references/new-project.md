# New project

Read this when there is no project store yet, or the saved scene lacks stable IDs. [The everyday workflow](../../../../docs/guides/EVERYDAY_WORKFLOW.md) has the command arguments.

## Starting

1. Inspect the intended Blender instance and record the brief and decisions.
2. Save an owned native checkpoint and observe it with `observe SAVED.blend --blender PATH --output-dir NEW_FOLDER`. In a background Blender script, `dcc_harness.continuity_blender.observe()` is equivalent straight after opening or saving the file.
3. Run `start`. It requires clean saved-state evidence.

- Use `fill-hashes` to complete `{path}` references in coordination payloads instead of hashing files by hand.
- An existing untracked .blend is input for a new project, not a reason to overwrite a previous store.
- Initial adoption establishes a baseline, not artistic acceptance.

## Scenes without stable IDs

Use [initial scene adoption](../../../../docs/guides/SCENE_ADOPTION.md). `adopt-preview` produces a readable plan. `adopt-apply` applies it to a new file and independently observes the saved result.

- Inspect the plan within the user's authorized scope.
- Never guess through duplicate IDs, ambiguous shared assets or outside-scene ownership.
- `NEEDS_REPAIR` retains a candidate with observation issues. Only `READY_FOR_START` is ready for `start`.
- This helper does not adopt manual revisions into an existing store.

## Large instance-heavy observations

Use the optional [compact storage](../../../../docs/guides/OBSERVATION_STORAGE.md) when every consumer has runtime 0.4.6 or later. Write new files with `write_json(..., compact_observation=True)` and read them with `evidence.read_json`. Full checks still apply. Never repack a retained checkpoint in place or discard UV evidence to shorten a resume.
