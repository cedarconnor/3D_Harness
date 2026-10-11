# Revision relocation — 0.16.0

Version 0.16.0, October 11, 2026, is [build-plan](../../BUILD_PLAN.md) item P7 for textures, following its [plan](../plans/P7_RELOCATION.md). The plan was written alongside the tests. Linked libraries are still refused, with the reason stated.

## Delivered

- **`preview-revision ... --blender PATH`.** An external revision whose textures are unpacked is packed into an owned copy:
  1. A fresh background Blender opens the artist's candidate, checks each texture file against its observed hash, packs it and saves a new file. The candidate is never saved.
  2. A second fresh process observes the owned copy, which must be `READY`.
  3. The owned observation must equal the candidate's apart from the packed textures' storage fields and qualified evaluated-UV noise.
- **The contract.** It is judged on the owned copy against the parent, with the parent's records of the same textures, matched by name and hash, compared as packed. Packing is not counted as a change.
- **The preview.** It holds the owned copy, its observation, the candidate's observation and `relocation.json` (`dcc.revision.relocation.v1`). Acceptance re-proves the equivalence, publishes the owned copy, and records the relocation in the check report.
- **Refusals.** Without `--blender` the message names the option. Linked libraries remain refused: packing one makes Blender report its path as `<packed>`, which would change the asset identity of its collections.
- **Docs.** The external revisions guide.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 406 tests: 404 passed, two Windows symlink-permission skips. 3 tests are new: packing and acceptance, refusals without `--blender` and for a missing texture, and an owned copy differing beyond packing |
| Installed-wheel suite | 406 tests from a standalone install of the wheel: 400 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 51 runtime and template files byte-identical to the sources. SHA-256 `8bc096b8177c517428a8aecbcd141244bdd47702b809913238aa19f7327d06cd` |
| Native, source and installed | `scripts/qualify_relocation.py` |
| Regression | The 0.4.10 external-revision qualification `qualify_revisions.py`, and the coverage, delivery, checks, owner, review page, guidance, render, relations and instances qualifications, passed on the 0.16.0 wheel |

The native script did the following from both runtimes:

1. **Setup.** It built a panel whose material reads `//tex/grain.png`, unpacked, and started a project on it.
2. **The candidate.** An artist candidate was saved in another folder with only `panel_paint` Roughness changed from 0.4 to 0.8. Blender remapped the relative texture path, so it observed `READY` with the texture unpacked.
3. **Without `--blender`.** The preview was refused: "pass --blender to pack them into an owned copy".
4. **With `--blender`.** The preview was `READY_FOR_REVIEW`, with `grain` packed. Its only change was `panel_paint/graph`, permitted by a contract allowing only that roughness, against a parent that still references the external PNG.
5. **A changed texture.** Changing the PNG's bytes after the candidate was observed made the worker refuse: "Texture file missing or changed since observation: grain".
6. **Acceptance.** The owned copy was published. With `tex/` renamed away, the published checkpoint still observes `READY`, and its texture is packed with the same SHA-256 as the original file.

The 0.4.10 `qualify_revisions.py` first failed on 0.16.0 because it asserted the old refusal wording for an unpacked-texture candidate previewed without `--blender`. The refusal itself was unchanged. Its assertion now checks the new wording, and it passed; the failing log is kept beside the passing one.

Local evidence is under `runs/relocation-0.16.0-2026-10-11/`, excluded from Git.

## Limits

- **Linked libraries.** They are still refused. Accepting them needs either library identity that survives packing, or the D5 working-copy-beside-libraries rule extended to external revisions.
- **Textures only.** Movie clips, sound and other external files are not observed, so they are not relocated.
- **Larger checkpoints.** The owned copy carries its textures' bytes.
