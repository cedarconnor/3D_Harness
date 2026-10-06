# Bring a saved artist edit into an existing project

Version 0.4.10 adds `preview-revision` and `accept-revision`. Use them when an artist or an external tool deliberately changed an owned copy of an accepted scene outside `begin-edit`. They preserve the old checkpoint, check the proposed change against an explicit contract, and retain its origin and review note with the new checkpoint.

For an untracked scene missing IDs, use [initial identity adoption](SCENE_ADOPTION.md) instead. These commands do not assign or repair identities, execute Blender code, or resolve an unknown pending native operation.

## Prepare and inspect the preview

Run `resume` first. Save the intended external edit as a separate `.blend` and freshly observe that saved file with `dcc_harness.continuity_blender.observe()`. Use a separate native reopen where practical. Preserve the existing IDs and write a narrow `dcc.continuity.contract.v1` contract describing allowed changes and cumulative requirements. Never infer permission for every difference simply because it exists.

Prepare a handoff, a JSON object of decision updates, a unique step label, and a short account of the edit. Then:

```powershell
python -m dcc_harness preview-revision C:/project/state --parent PARENT_ID --checkpoint C:/project/artist-edit.blend --observation C:/project/artist-edit.json --contract C:/project/material-contract.json --handoff C:/project/CONTINUE.md --updates C:/project/decision-updates.json --label artist-material-01 --note 'Saved adjustment to shared stone roughness' --output-dir C:/project/revision-preview-01
```

`PARENT_ID` is the actual `active.id` from resume. Paths and labels here are examples. The output directory must be new and outside the project store.

The command copies the candidate, observation, contract, handoff and updates into a frozen preview, writes a computed `check.json`, and writes `manifest.json` last. It leaves the store unchanged. Its JSON response supplies the `preview_sha256` needed for acceptance, changed fields, changed material users, and native check failures. The preview captures a particular saved edit; later changes to the original artist file are separate work.

- `READY_FOR_REVIEW`: the supplied evidence passes the contract. Inspect the frozen native candidate, actual review images, contract, handoff and decision updates within the user's authorized scope.
- `REJECTED_CONTRACT`: the failed candidate and checks are retained in the preview; the accepted project stays unchanged. Correct a new owned candidate and prepare another preview.
- Invalid evidence, dirty state, unsupported dependencies, stale parent or unresolved workflow: an error stops preparation. Inspect the cause; never erase prior evidence or pending operations to force acceptance.

A preview does not reserve the project. Other cooperating work may continue; advancing the parent makes the preview stale. Prepared previews are not pending operations and are not listed by `resume`. Keep their paths in the working handoff when review spans sessions.

## Accept the reviewed copy

Use the exact preview hash returned above and a factual review note. An agent may record its own review within the user's authorized scope; it must not claim the artist reviewed or accepted work they have not seen.

```powershell
python -m dcc_harness accept-revision C:/project/state C:/project/revision-preview-01 --preview-sha PREVIEW_SHA256 --review-note 'Reviewed the saved candidate and fixed views; shared stone changed, layout and lighting preserved'
python -m dcc_harness review C:/project/state
```

Acceptance checks project identity, preview hashes, current parent and pending work under the workflow metadata lock. It recomputes the native contract instead of trusting the preview's check report. A passing result publishes a new checkpoint with the handoff and cumulative decision updates. The retained `check.json` includes the original contract, preview manifest, edit description and caller-supplied review note. `review` exposes a compact provenance summary.

No native operation is dispatched and no fictional build script is entered in the journal. This records acceptance of work that already exists. A technically passing preview may still be visually unsuitable: leave it unaccepted, retain the review reason in the working notes, and prepare a new candidate if needed.

## Interruptions

If acknowledgement is lost after acceptance, inspect with `resume`/`review`. Calling `accept-revision` again with the same verified preview finds its committed history entry and returns `ALREADY_PUBLISHED` without publishing again or changing the original review note. It reports both that accepted entry and the current active checkpoint, which may be newer. Cooperating calls still use the metadata lock.

A partial checkpoint without its final manifest remains an inspection stop. This command does not delete partial bundles, expire locks, finish pending native edits, or replay a native write. A failure before publication can leave an unused acceptance report under `reports/`; preserve it while diagnosing. This is checked metadata publication, not general exactly-once DCC execution.

## Relocation and evidence limits

Preview and publication copy native bytes to new folders. This version requires observed images to be packed and rejects observed linked-library references before copying. Relative texture paths can break after relocation; even absolute unpacked images are conservatively unsupported here. Prepare an owned self-contained copy and capture a new saved observation. Do not modify the accepted source to satisfy this requirement.

Packing or localizing dependencies can itself change observed material/data fields and fail the preservation contract. If the accepted baseline relies on external dependencies, establish a separately qualified self-contained baseline or a deliberately checked dependency migration first. These commands do not supply that migration, and the legacy `start`/publication APIs do not automatically package dependencies.

These guards cover observed dependencies only. Fonts, caches, simulation data, unmeasured links and other unsupported native state still require independent native reopening and review. The command does not launch Blender, pack assets, certify dependency completeness, or authenticate an observation producer. Packed images, material graphs, UVs and geometry retain the current observer/comparator limits. A native pass and a caller review note do not establish independent artist acceptance.

Both commands use the existing continuity format and preservation policy. Older consumers can read published checkpoint bundles; only 0.4.10 and later provide this workflow and the extra compact `review` provenance field. See [qualification results](REVISIONS_0_4_10_RESULTS.md).
