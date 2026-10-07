# Correctness maintenance — 0.5.1

Version 0.5.1, October 6, 2026, is [build-plan](../../BUILD_PLAN.md) item M1. It fixes six defects confirmed in the October 6 repository review and adds no feature. Each fix has a regression test that failed before the change. No production art, retained checkpoint or prior run was modified.

## Defects and fixes

| Defect | Fix | Regression test |
|---|---|---|
| The path guard `continuity._plain` called `stat()`, which follows Windows junctions, so a junction anywhere in a retained path passed. The symlink tests skip on this host, while junctions need no privilege. | Inspect each path component with `lstat()` and reject symlinks and reparse points. | A real junction ancestor is rejected by `_plain` and by `Continuity` |
| Trial packets from `blind` and `continuity_trial` omitted `observation_storage.py`, which `evidence.read_json` imports, so a newly prepared packet's helper copy could not read JSON. | Add the module to both helper lists. Existing packets keep verifying against their frozen manifests. | Each helper list, copied alone into a temporary package, reads JSON in a separate process |
| The pinned workflow runtime digest hashed raw bytes, so a CRLF checkout pinned a different runtime than an LF one: `1c9dfe8c…` against `686e69d9…` for the same 0.5.0 sources. | Normalize CRLF to LF inside the digest. `.gitattributes`, added earlier the same day, forces LF checkouts. | LF and CRLF trees share a digest; a content change alters it |
| `--out` was written before the result was printed, so an existing path failed after a committed transaction and hid its result. | Print first, then write the receipt. A failed receipt exits 2 with a message saying the committed change stands. | The result prints, exit status is 2 and the existing file is unchanged |
| Coordination commands nest `passed`, so a failed or uncertain verification exited 0, unlike a rejected `finish-edit`. | Exit 1 when the nested result did not pass. The event is still committed. | A real `fail` verification through the CLI is committed and exits 1 |
| `begin-edit` verified the full checkpoint chain twice and `finish-edit` three times. Legacy `status` listed no checkpoints for a continuity store, and the legacy pilot commands were unlabeled. | Verify once under the workflow lock and hand that state to publication; the new chain is still verified in full afterward. Publication refuses a stale handed-over state. Legacy `status` lists bundle checkpoints and points to `resume`, and help labels the pilot commands. | Verification counts of 1 and 2; a stale state is refused; legacy status and help output |

## Executed checks

| Check | Result |
|---|---|
| Source suite | 244 tests: 242 passed, two Windows symlink-permission skips. The eleven new tests are included. |
| Installed-wheel suite, run from a standalone install | Same result; imports resolved to the installed copy |
| Wheel integrity | All 34 runtime and template files byte-identical to source, with no stale extras. SHA-256 `0749c9b960d954acfe85a980b343a9a8b6eabd72557f68556af689ce4e7f704e` |
| Native external revisions (0.4.10 launcher), source and installed | Passed: fresh-process resume, acknowledgement recovery, duplicate-ID, unrequested-light and relocation faults rejected; original files unchanged |
| Native adoption (0.4.9 launcher), source and installed | Passed: identities preserved, false inventory and output replay rejected, unsupported scene reported as `NEEDS_REPAIR` |
| Native feedback workflow (0.5.0 launcher), source and installed | Passed: preservation fault, stale image and forgotten note rejected; all seven stages completed; acknowledgement recovered; reopened note survives a fresh process |
| Runtime pin | Source and installed runtimes pin the same digest, `635f67b8…`, and prepare and finish phases agree |
| Verification cost on the nine-checkpoint production store, read-only | One full verification took 29.8–29.9 s under both 0.5.0 and 0.5.1, so `lstat()` adds no cost. Removing one pass saves about 30 s from each of `begin-edit` and `finish-edit` on this store. The store's manifests and journal were unchanged. |

The feedback exercise's visual note was reviewed by the coordinating agent, not an artist. The bench-top length change is plainly visible. The timber roughness change to 0.65 is subtle at native size; it was judged a pass only after an enlarged crop of the bound detail view showed the pale sheen gone and the timber more saturated, with crop luminance 155.8 before and 149.9 after. The source and installed renders are pixel-identical. Both review records disclose this, and the 0.5.0 independent reviewer's `uncertain` verdict on the same fixture remains on record.

Local evidence is under `runs/maintenance-0.5.1-2026-10-06/`, summarized in `VERIFICATION.json`. It is excluded from Git.

## Compatibility and limits

- Changing package sources changes the pinned workflow runtime digest. Projects bound under 0.5.0 need the 0.5.0 runtime for workflow mutations; no in-place upgrade command exists yet.
- Packets prepared before 0.5.1 still lack `observation_storage.py`. Prepare a new round rather than editing a frozen packet.
- Coordination commands can now exit 1 after committing an event, for a failed or uncertain verification. Callers must read the printed `status`, which says `COMMITTED`, rather than treating exit 1 as "nothing was recorded".
- `finish-edit` still verifies the chain twice: once before publication and once after, against the new bundle. Incremental verification remains future work.
- The visual review is an agent judgment on a synthetic fixture. It establishes no environment realism or artist acceptance.
