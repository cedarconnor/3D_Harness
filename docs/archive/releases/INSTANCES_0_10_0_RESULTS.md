# Collection instances and linked libraries — 0.10.0

Version 0.10.0, October 10, 2026, is [build-plan](../../BUILD_PLAN.md) item P3, following its [implementation plan](../plans/P3_COLLECTION_INSTANCES.md). Before it, the observer reported every instancer as an issue, so scenes that place assets as collection instances, the ordinary way artists reuse furniture, plants and linked library assets, could not `start`. They now can. Each instance is measured by identity, library provenance, a placement-independent definition and its world extent, and [D5](../../DESIGN_DECISIONS.md#d5-file-ownership-and-asset-publishing) is settled.

## Delivered

- **Collection instances observed.** An empty that instances a collection, local or linked from a library, gets an `instance` record:
  - the collection;
  - its asset identity: the collection's `dcc_asset_id`, or `library:<path>#<collection>` for a linked collection without one;
  - the library's stored path, with forward slashes, whether it is relative and exists, and its SHA-256;
  - a definition hash over the collection's objects, nested sets included, each in the collection's own space;
  - member and triangle counts.

  The record also gets world `bounds`, orientation-only `dimensions`, `vertices` and `triangles`. Moving an instance changes only its transform and bounds.
- **Still issues.** Vertex, face and particle instancing, unsupported instancers inside a collection, library overrides, a missing library file, a local instanced collection without an asset ID, and an instancer whose own asset ID differs from its collection's.
- **Compatibility.** Instance coverage is added only when a scene has instances, and the comparator ignores that one key when only one side has it. Scenes without instances observe byte-for-byte as before.
- **Contracts.** `instance` is an object field a contract can permit, and `exact_asset_counts` counts instances.
- **Adoption.** Adoption inventories the collections the active scene instances. It assigns `dcc_asset_id` to local ones that lack it and leaves linked ones to their library identity.
- **Guidance.** When the active checkpoint links libraries, `brief` lists them and `next` fills the working copy beside them into its native commands, because the stored checkpoint cannot resolve relative library paths.
- **D5 settled.** Asset changes are published as new versioned libraries and switched in by a scoped edit that permits `instance`. An in-place library edit is caught at the next reservation, not accepted. Libraries are referenced, not copied into the store, and library overrides stay unsupported.

## Executed checks

| Check | Result |
|---|---|
| Source suite | 336 tests: 334 passed, two Windows symlink-permission skips. 12 tests are new: contracts, comparison coverage, adoption of collections, and library guidance. |
| Installed-wheel suite | 336 tests from a standalone install of the wheel: 330 passed and 6 skipped, the same two plus the four source-tree documentation tests |
| Wheel integrity | All 43 runtime and template files byte-identical to the sources. SHA-256 `e70ec0773f6badd5b7600e8b092358bd2a8e41778e765eb1cb2d8c6c04e526e4` |
| Native, source and installed | `scripts/qualify_instances.py` with scenes and libraries built by `scripts/instances_native_probe.py` |
| Regression | The 0.7.0 guidance, 0.8.0 render and 0.9.0 relations qualifications passed again on the 0.10.0 wheel |

The native script checked the following from both runtimes:

- **Observation.** A scene with two instances of a local bench collection, one instance of a crate linked from `//lib/crate-v1.blend`, and a nested set of two benches observed `READY`. The benches had the expected world bounds, `[[-0.8, -0.3, 0], [0.8, 0.3, 0.9]]` and the same shifted 3 m in x, identical definitions and dimensions of exactly 1.6 × 0.6 × 0.9 m. The crate recorded its relative library path and the library file's hash. The nested set counted 72 triangles.
- **Issues.** A missing library, a vertex instancer, a library override and a local collection without an asset ID were each reported.
- **Compatibility.** The comparison fixture, which has no instances, observed with the same revision under 0.9.0 and 0.10.0.
- **Stored copy.** Observing the project's stored checkpoint reported the library missing, as expected, and `next` pointed its native commands at the working copy.
- **Scoped edits.**
  - Moving one bench with its transform and bounds permitted published.
  - Moving the other bench as well was retained as rejected for exactly that bench's `matrix_world` and `bounds`.
  - Switching the crate to `crate-v2.blend` without permission was rejected for its `instance`, `bounds` and `dimensions`, and published once `instance` was permitted.
- **In-place library edit.** Rebuilding `crate-v1.blend` taller left the scene file's bytes unchanged but changed the library hash and the crate's definition, and `begin-edit` refused the changed observation.
- **Adoption.** `adopt-preview` planned an asset ID for the unlabelled bench collection, and `adopt-apply` produced `READY_FOR_START`.
- **Source files.** No source scene changed.

**Fixed during qualification.**

- **Invalid instance references.** The first observer kept references to depsgraph instance objects after iteration, which Blender documents as invalid. Bounds came out wrong, ±0.95 m instead of ±0.8 m, so evaluated data is now read during iteration.
- **Placement dependence.** The definition hash and dimensions were then computed through the instance's world placement. Moving a bench from x = 3 to 3.5 changed its dimensions to 1.9000001 and its definition hash through float rounding, so a move would have required permission for fields it never touched. The definition and dimensions are now computed in the collection's own space.
- **Separators.** Library paths and the derived asset identity used the Windows separator; they now use forward slashes, so the same project records the same values on any system.

Local evidence is under `runs/instances-0.10.0-2026-10-10/`, excluded from Git.

## Limits

- **Other instancing.** Geometry Nodes, particle and vertex or face instancing remain unsupported ([D6](../../DESIGN_DECISIONS.md#d6-asset-and-instance-identity-are-separate)).
- **Overrides.** Library overrides and edits to linked data in the assembly are not supported.
- **External revisions.** They still reject linked-library data; rebasing library paths is P7.
- **Store completeness.** Libraries are referenced, not stored. The project records each library's hash and catches a change, but it cannot restore a library that is lost or edited.
- **Instance members.** Relations and render views address scene objects, not the members of an instance; a relation subject must be a mesh object.
- **Shader detail.** A definition records member geometry, transforms and material names. Shader inputs inside a local collection are covered only through those names, while a linked library's are covered by the library's hash.
