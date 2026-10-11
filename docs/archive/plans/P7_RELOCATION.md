# P7: Revision dependency relocation

Plan for [build-plan](../../BUILD_PLAN.md) item P7, written October 11, 2026, at version 0.15.0, alongside its tests. Target version: 0.16.0.

## Problem

An artist saves an edited scene in their own folder, with its textures referenced by relative path. `preview-revision` copies the native bytes into the project, so it refused any unpacked texture, because the relative path would break. The artist had to prepare a self-contained copy by hand.

## Scope

- **Packing.** `preview-revision ... --blender PATH` packs a candidate's unpacked textures into an owned copy in a fresh background Blender. The worker opens the candidate and checks each texture file against the hash the candidate's observation recorded. It packs each texture and saves a new file; the candidate is never saved. A second fresh process observes the owned copy, which must be `READY`.
- **Equivalence.** The owned observation must equal the candidate's in everything except the named textures' storage (`path`, `packed`, `exists`) and qualified cross-process evaluated-UV noise. Anything else refuses the preview.
- **The contract.** It is evaluated on the owned copy against the parent, with the parent's records of the same textures, matched by name and hash, compared as packed. Storage is not a change. This lets a parent that still references the external file accept a candidate that only changed something else.
- **The preview.** It holds the owned copy as `checkpoint.blend` and its observation, the candidate's observation and `relocation.json`. Acceptance proves the equivalence again and records the relocation in the published check report.
- **Libraries stay refused**, with the reason. Packing a library makes Blender report its path as `<packed>`, which would change the asset identity of its collections.

## Qualification

- **Portable tests.** The packing flow with stand-ins for the worker and observer; acceptance; a refusal without `--blender`; a missing texture; an owned copy that differs beyond packing.
- **Native.** `scripts/qualify_relocation.py`:
  - a panel whose material reads an external PNG by relative path;
  - a candidate saved elsewhere with only roughness changed;
  - refused without `--blender`, and ready with it;
  - published as the owned copy, which observes `READY` with its texture packed after the PNG is renamed away;
  - a texture changed after observation is refused by the worker.
