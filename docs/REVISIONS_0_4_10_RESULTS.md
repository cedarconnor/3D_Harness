# External revision qualification — 0.4.10

Tested October 6, 2026 on Windows, Python 3.11 and Blender 5.1.1. [Usage](EXTERNAL_REVISIONS.md) describes the new `preview-revision` and `accept-revision` commands. The existing observer, comparator policy and continuity bundle format remain unchanged.

## Results

| Check | Result |
|---|---|
| Source portable suite | 204 tests: 202 passed, two Windows symlink-permission skips |
| Installed-wheel portable suite outside the source root | Same 204 tests: 202 passed, two skips |
| Source native revision exercise | Passed |
| Installed native revision exercise | Passed, including compact provenance returned by `review` |
| Older-reader compatibility | Installed v0.4.9 resumed the new two-checkpoint source fixture |
| Production checkpoint 9 | Original native SHA unchanged; no production revision published |
| Entry and review skills | Both skill validators passed |

## Native exercise

The fixture has two objects sharing a mesh and material, a camera, an area light and a packed texture. A separately saved candidate changes only the shared material roughness. Every input is reopened in a separate background Blender process for observation; the authoring process does not certify its own saved output.

The preview leaves the project's original files unchanged and reports both material users. Acceptance retains the scoped contract, source description, review note, handoff and decision update in the new checkpoint. Reopening the published native file yields the same observed revision as the retained candidate, with no missing dependencies. A fresh Python process resumes the new parent and reads its measured shared users. The installed exercise also checks `review` provenance.

An injected exception **after the real publication commits** simulates acknowledgement loss. A fresh CLI call finds that publication and returns `ALREADY_PUBLISHED`; all retained project file hashes remain identical, there is no third checkpoint, and the original review note remains intact. No fictional native dispatch or script is entered in the journal. This tests application-level acknowledgement loss, not a real network outage or process crash during save.

Two native faults reject: an unrequested light-energy change fails preservation, while duplicated instance IDs fail observation readiness. Neither becomes the active parent.

A separate native control uses a relative external texture. Copying that `.blend` into a new folder reproduces a missing-image observation. The revised workflow rejects this unpacked candidate before copying it. The packed-texture positive fixture survives both relocations. These guards do not prove all Blender dependencies are self-contained; the observer still has explicit coverage limits, and legacy publication APIs do not automatically package dependencies.

The source and installed runs retain all six native fixture inputs and two texture files byte-for-byte. These are coordinator-authored engineering fixtures, not real artist edits, independent agent reviews, or visual-quality measurements.

## Portable fault coverage

The eighteen new tests cover preview non-mutation, retained old checkpoints, cumulative decisions, shared-user reporting, provenance, freezing against later source edits, altered preview bytes/hash, recomputed checks even after a report is rehashed, stale parents, pending operations, partial reservations, metadata locks, concurrent acceptance, partial publication, lost acknowledgement, lookup after a newer accepted step, project mismatch, unsafe output placement, external dependencies, dirty observations, review-note requirements and CLI continuation.

A test exposed a path-normalization bug: a path with `..` could evade the initial check preventing previews inside the checkpoint store. The workflow now resolves checked paths before containment comparisons. The failing and corrected logs remain retained. Two fixture issues were corrected separately: a placeholder world value incompatible with the store, and a generated image that did not reopen as packed. The texture fixture now writes a small PNG, loads it, and packs that file image; observer behavior was not relaxed.

## Package and retained evidence

Tested wheel: `dcc_harness-0.4.10-py3-none-any.whl`.

```text
SHA-256 ca8dc03cbc31d1c8728e64fd676201e10a145ae31dbb56c4c1faa16c4b693d8b
```

Local evidence under `runs/revision-2026-10-06/` is excluded from Git:

- `tests-source.log`, `tests-installed.log`, `build.log`, `install.log`.
- `native-source-final/VERIFICATION.json`, `native-installed/VERIFICATION.json`, native logs, frozen previews and checkpoint histories.
- `legacy-resume.json`: read through the separately installed v0.4.9 environment.
- `focused-path-red.log`, `focused-path-green.log`, `dependency-red.log`, `focused-final.log`, and earlier failed native runs.
- `VERIFICATION.json` and `CONTINUE.md`: consolidated delivery evidence and remaining boundaries.

Production checkpoint 9 remains SHA-256 `efb64030397fc571324ae8a444f51fa33555b420b8b7a4210e8829d2f9aa932d`. No production native file or artist editor was modified. This release improves continuity around external edits; it does not establish visual superiority, implement automatic dependency migration, or provide unattended execution guarantees.
