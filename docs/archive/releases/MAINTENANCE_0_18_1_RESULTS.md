# Maintenance — 0.18.1

Version 0.18.1, October 15, 2026, closes [build-plan](../../BUILD_PLAN.md) maintenance item M6 and releases the fixes for the eleven findings of the October 11 full review of `340dc9d`, listed in the [changelog](../../../CHANGELOG.md). The item came from the [Scenario for Blender review](../../reference/SCENARIO_BLENDER_PLUGIN_REVIEW_2026-10-15.md).

## The defect

Blender marks a file modified only through undo steps. Edits made from Python or an MCP do not set `bpy.data.is_dirty`. The observer recorded that flag as `native_dirty`, and six checks (`start`, `begin-edit` and `finish-edit` through workflow and coordination evidence, adoption, `observe`, quality candidates and visibility receipts) take `native_dirty: false` to mean the observed scene is the saved file. The guides and the `dcc-harness` and `dcc-build-revise` skills said that calling `continuity_blender.observe()` inside Blender was equivalent to the `observe` command.

Reproduced before the fix, on Blender 5.1.1:
1. A saved scene was opened in an interactive session, and a cube was moved from Python without saving.
2. `is_dirty` stayed false.
3. The observation reported `native_dirty: false` and carried the saved file's hash beside a revision different from that file's.
4. `observe_visibility` accepted the session.

An agent working through a live MCP could therefore submit evidence for a scene that was not in the checkpoint it named.

## Delivered

- **Interactive observations are never clean.** `continuity_blender.observe()` in an interactive session records `native_dirty: true` and a `native_dirty_reason` that names the `observe` command. Background observations are unchanged: the field is absent there, and the 0.18.0 and 0.18.1 runtimes observed the same file with the same revision, differing only in `observed_at`.
- **Visibility receipts need a background process.** `observe_visibility` refuses an interactive session with "Visibility receipt requires a fresh background process".
- **`--offline-mode`.** `native.py` and `scripts/_launcher.py` start Blender with `--offline-mode` as well as `--factory-startup --disable-autoexec`, so no owned process can reach the network whatever the preferences say.
- **Guidance.** `CONTINUITY_USAGE`, `EVERYDAY_WORKFLOW`, `EXTERNAL_REVISIONS`, `QUALITY_LOOP_USAGE` and the `dcc-harness` and `dcc-build-revise` skills now say that `observe()` is equivalent only in a background script, straight after opening or saving the file.

## Every route to a `native_dirty` check

| Route | Before | After |
|---|---|---|
| `observe` command and `observe_file` | Fresh background process opens the file and observes at once | Unchanged; safe |
| Adoption `observe` action | Fresh background process, after verifying the applied plan | Unchanged; safe |
| `observe()` in an interactive session (live MCP) | Clean after unsaved Python edits | Always `native_dirty: true`; refused as evidence |
| `observe_visibility` in an interactive session | Accepted after unsaved Python edits | Refused |
| `observe()` in a background script after an unsaved edit | Clean | **Still clean: the documented limit.** Nothing in the process records the edit. The guides now say to observe only straight after opening or saving |

## Executed checks

| Check | Result |
|---|---|
| Source suite | 429 tests: 427 passed, two Windows symlink-permission skips. M6 adds no portable test, because every changed line needs `bpy`; the native fixture below covers it |
| Installed-wheel suite | 429 tests from a standalone install of the wheel: 416 passed and 13 skipped. The skips are the two symlink-permission cases, the four quick-reference documentation tests and the seven skill-library tests, all of which check the source tree |
| Wheel integrity | All 53 runtime and template files byte-identical to the sources. SHA-256 `9ef2b2fd6133b9c3f154e0c81c673e55448fe3486c6347d6245b994889a04501` |
| Native, new | `scripts/qualify_saved_state.py` passed from source and from the installed wheel on Blender 5.1.1 and 5.2.1. Before the fix, the same fixture failed on the interactive observation |
| Compatibility | The `observe` command from the 0.18.0-based tree and from 0.18.1 on the same saved file: identical apart from `observed_at`, with the same revision |
| Regression | The UV report, modifiers, relocation, coverage, delivery, checks, owner, review page, guidance, render, relations and revisions qualifications passed on the 0.18.1 wheel, every one now launching Blender with `--offline-mode`. Instances passed with 0.18.0 as the compatibility baseline |

**Found during qualification.** `scripts/qualify_observe.py`, last changed in 0.6.0, failed: it still expects the instancer fixture to report "Unsupported instancer". Collection instances have been supported since 0.10.0, and the fixture now reports "Missing asset ID: collection ProbeGroup", which is correct. The script is not among the qualifications rerun every release and was left unchanged; its row in the scripts index stands for 0.6.0 only.

Local evidence is under `runs/maintenance-0.18.1-2026-10-15/`, excluded from Git.

## Limits

- **Background scripts.** A background script that edits the scene and then observes without saving still produces a clean observation that does not match the file. `qualify_saved_state.py` asserts this, so a Blender change that starts marking Python edits will show up.
- **No in-memory comparison.** The fix refuses interactive evidence; it does not compare the scene in memory with the saved file. An agent with only a live MCP needs the `observe` command, which starts its own background Blender from the same executable.
- **Interactive probe.** The interactive fixture opens a Blender window for a few seconds and leaves through `os._exit`. It needs a desktop session.
