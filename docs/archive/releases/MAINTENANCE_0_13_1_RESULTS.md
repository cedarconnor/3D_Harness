# Maintenance — 0.13.1

Version 0.13.1, October 11, 2026, closes [build-plan](../../BUILD_PLAN.md) maintenance items M2–M5. No runtime behavior changes.

## Delivered

- **M2, shared file helpers.** `dcc_harness/files.py` holds:
  - file hashing and link rejection;
  - canonical JSON text and exclusive writes;
  - verified copies, which copy to a new file and require both sides to hash to the expected value.

  Continuity, coordination, revisions, checks, evidence and the blind tooling now use it in place of their own copies. The old names (`evidence.file_hash`, `continuity._plain`, `_write`, `_json_bytes`) are the shared functions, and every error message is unchanged. Packets built by the blind and continuity-trial tooling include `files.py` among their helper files.
- **M3, experiment tooling outside the runtime digest.** `runtime_stamp` excludes `blind`, `blind_review`, `continuity_trial`, `continuity_review` and the new `session_cost`. Editing them no longer invalidates workflow bindings. A test parses every other module and fails if the pinned runtime imports one of them.
- **M4, shared launcher.** `scripts/_launcher.py` handles, for the qualifications:
  - the common arguments, and selecting the source or installed runtime;
  - the output folder;
  - CLI calls, expected refusals and background Blender;
  - a scripted owner console.

  The seven qualifications rerun every release now use it: checks, owner, review page, guidance, render, relations and instances. Older one-off scripts are tied to retired fixtures and keep their own code. Evaluators copied into packets stay self-contained.
- **M5, session cost.** `python -m dcc_harness.session_cost TRANSCRIPT` writes a `dcc.trial.session-cost.v1` receipt from a Claude Code transcript. It records only counts:
  - turns, counting each model request once with its final usage;
  - tool calls and elapsed minutes;
  - input, cache-creation, cache-read and output tokens;
  - the cache-read share;
  - spend, against the trial ceilings.

  Spend is reported only when the transcript carries a cost; otherwise it is "unavailable", never estimated.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 390 tests: 388 passed, two Windows symlink-permission skips. 9 tests are new: 4 for the file helpers, 2 for the digest exclusion and import guard, 3 for session cost. One existing test's mock now targets the shared copy |
| Installed-wheel suite | 390 tests: 384 passed, 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 48 runtime and template files byte-identical to the sources. SHA-256 `998434c83a170851a0c296f5207d423a399ba14a38f0e4800641a9c966795b81` |
| Native | Through the shared launcher, the checks qualification passed from source and from the installed wheel. The owner, review page, guidance, render and relations qualifications passed from the installed wheel. Instances passed after the fix below |

**Found during qualification.** The instances qualification's compatibility step required the 0.13.0 and 0.13.1 runtimes to observe an uninstanced file with the same revision. This time they differed: in nine objects, only `uv_hash` and `evaluated_uv_values` changed, all within the qualified cross-process noise that the comparator accepts. The 0.11.0 reopen check saw the same noise. The earlier passes were luck. The step now requires the observations to be equal apart from qualified UV noise, and it records whether the revisions happened to match. The strict run's log is kept beside the passing one.

These native runs overlapped the E5 fresh-agent session on the same machine.

Local evidence is under `runs/maintenance-0.13.1-2026-10-11/`, excluded from Git.
