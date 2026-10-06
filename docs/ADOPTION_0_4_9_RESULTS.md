# Initial identity adoption qualification — 0.4.9

Tested October 6, 2026 on Windows, Python 3.11 and Blender 5.1.1. This release adds `adopt-preview` and `adopt-apply`, updates the entry skill, and preserves the observer and continuity formats. [Usage and limits](SCENE_ADOPTION.md).

## Results

| Check | Result |
|---|---|
| Source portable suite | 186 tests: 184 passed, two Windows symlink-permission skips |
| Installed-wheel portable suite, outside the source root | Same 186 tests: 184 passed, two skips |
| Source and installed native adoption exercises | Both passed |
| Missing identities | Seven properties assigned in a five-object fixture; existing artist IDs retained |
| Shared asset definition | Linked cube inherits the artist's existing mesh asset ID; separate sphere gets a distinct definition |
| Independent saved-state observation | Exact planned/preserved identities verified after reopen; no issues; clean saved state |
| Continuity entry | New project starts from adopted checkpoint; a fresh Python process resumes the same active ID without pending operations |
| Repeat preview | Zero missing properties after adoption |
| CLI routing | Paths containing spaces work; an existing output directory rejects replay |
| Production checkpoint 9, preview only | Zero assignments, no identity conflicts, original SHA unchanged |

Independent native snapshots before/after the positive fixture match for mesh sharing, vertices/faces, UV arrays, transforms, hierarchy, collections, hidden flags, material slots, modifier names/types, selected material inputs, camera lens, light energy/color and the artist's unrelated custom note. This is selected fixture coverage, not a complete Blender serialization equivalence claim. No visual improvement is claimed or scored.

## Rejection evidence

Each of these nine native sources produced a blocked plan with no assignments. Calling apply on those plans rejected before creating an output directory:

- Duplicate instance IDs and duplicate material IDs.
- A present empty instance ID.
- A missing asset ID with conflicting definitions among shared-mesh users.
- A proposed object write shared with another scene.
- A material used by a separate outside-scene object.
- A material used by an already identified object linked into two scenes.
- A material referenced by an unscoped Geometry Nodes group.
- A linked library object requiring new IDs.

A separate self-consistent proposal with a false inventory passed the portable plan shape check but failed native preflight against the reopened source, before any checkpoint was saved. This confirms that a supplied inventory does not replace native inspection.

A collection-instance fixture deliberately passed identity planning but failed the existing observer's supported-feature check. Apply retained its checkpoint and evidence with `NEEDS_REPAIR`, exit failure and no automatic project creation. This distinguishes complete identities from usable observation coverage.

Portable tests additionally cover source-byte changes, stale/altered plans, distinct meshes, existing semantic asset grouping, invalid property types, generated IDs, empty scenes, output reuse and incorrect saved IDs. All twelve native fixture input files retained their original bytes in each final source/installed exercise.

## Failure retained during development

The first fixture accidentally attempted to link from the currently open file; Blender rejected that setup before adoption. A separate copied library resolved it. The next qualification run exposed an incorrect expected count in the test; the assertion now names the seven actual target properties.

More substantively, an added native test reproduced a missing ownership guard: a complete-ID object linked into a second scene still exposed its unidentified shared material. The initial material-slot scan missed that relationship. The worker now uses the native datablock user map, checks all object owners of material-bearing geometry, and rejects indirect node-group users. The failing `native-shared-red` run remains alongside the corrected runs.

## Package and artifacts

The tested wheel is `dcc_harness-0.4.9-py3-none-any.whl`, SHA-256:

```text
3c7168b297ed4b150e60559aee2411d2fb10dcfa7f8beb45c436cc7e19233801
```

It was installed into a new virtual environment. The native worker imported that installed package, and the fresh continuation process ran outside the source root. Skills/docs remain repository resources; this does not install client plugins.

Retained local evidence under `runs/adoption-2026-10-06/` (excluded from Git):

- `tests-source.log`, `tests-installed.log`, `wheel-final.log`, `install.log`.
- `native-source-final/VERIFICATION.json` and `native-installed/VERIFICATION.json`.
- Their `applied/receipt.json`, saved `.blend`, compact observation, independent snapshots and process logs.
- `production-preview/plan.json`: the production native file remained SHA-256 `efb64030397fc571324ae8a444f51fa33555b420b8b7a4210e8829d2f9aa932d`.
- `VERIFICATION.json` and `CONTINUE.md` consolidate delivery evidence and the next boundary.

The accepted environment, previous runtimes and comparison results remain untouched. This closes an onboarding gap; it does not establish the broader visual-quality advantage, qualify a second DCC, or supply unattended execution guarantees.
