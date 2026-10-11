# P3: Collection instances and linked libraries

Plan for [build-plan](../../BUILD_PLAN.md) item P3, written October 10, 2026, at version 0.9.0. Target version: 0.10.0.

## Problem

The observer reports every instancer as an issue, so `start`, adoption and external revisions reject scenes that place assets as collection instances. That is the ordinary way artists reuse furniture, plants and props, and the way linked libraries enter a scene. The production study worked around it with shared mesh datablocks. [D5](../../DESIGN_DECISIONS.md#d5-file-ownership-and-asset-publishing) describes publishing versioned libraries and linking them into an assembly, but the harness cannot observe the result, so D5 is unsettled.

A Blender 5.1 probe established the mechanics. The evaluated depsgraph lists every instanced mesh with the top-level instancing empty as its `parent`, including meshes from nested collection instances, and with its world matrix. A linked collection keeps its custom properties and its library's stored path, which is relative (`//lib.blend`) once the file is saved.

## Scope

### Observation

- **Supported instancers.** An empty with `instance_type` `COLLECTION` and an instanced collection is supported. Every other instancer, such as vertices, faces or particles, is still an issue, as are library overrides.
- **Instance record.** An instancer's object record gains `instance`:
  - the collection's full name;
  - its asset identity and the identity's source. A local collection must carry `dcc_asset_id`, or the observation reports a missing asset ID. A linked collection uses its `dcc_asset_id` if set, otherwise `library:<stored path>#<collection name>`;
  - the library, if linked: stored path, whether it is relative, whether the file exists, and its SHA-256. A missing file is an issue. The absolute resolved path is not recorded, so a project that moves with its libraries observes the same;
  - a definition hash over the instanced meshes in the instancer's own space: each member's name, library, transform, evaluated geometry and material names;
  - member and triangle counts.

  The record also gets world `bounds`, `dimensions`, `vertices` and `triangles` aggregated over the instanced geometry, so dimension rules and centres work on instances. An instancer's own `dcc_asset_id`, if set, must match its collection's.
- **Coverage.** It gains a `collection_instances` entry only when the scene has instances. Scenes without instances observe byte-for-byte as in 0.9.0, so existing projects keep comparing. The comparator ignores that one coverage key when checking that both sides were measured alike, because a scene without instances measured nothing to compare.

### Contracts and adoption

- `instance` joins the object fields a contract can permit, so a scoped edit can swap an instance to a new library version or another collection.
- `exact_asset_counts` counts instance records as well as meshes.
- Adoption inventories collections instanced by the active scene. It plans `dcc_asset_id` for local ones that lack it, and leaves linked ones alone, since their identity comes from library provenance.

### D5, settled

- Publish asset changes as new versioned library files referenced by relative paths, and switch instances to them with a scoped edit that permits `instance`.
- Editing a library in place changes its hash and every instance's definition hash, so preservation fails unless the change is explicitly permitted. It is never accepted silently.
- Library overrides stay unsupported.
- One writer owns the assembly file.

## Qualification

- **Portable tests.** Comparator coverage handling; the `instance` field in contracts; asset counts that include instances; adoption plans for local and linked collections, including linked ones that are read-only.
- **Native, source and installed.** Generated scenes and libraries:
  - Two instances of a local collection, one of a linked library collection and a nested set observe `READY` with correct world bounds, a relative library path and a hash, then `start`.
  - The comparison fixture, which has no instances, observes with the same revision under 0.9.0 and 0.10.0.
  - A scoped edit that moves one instance publishes; moving an instance outside the contract is retained as rejected.
  - Editing the library in place is rejected by preservation. Switching to a new versioned library with `instance` permitted publishes.
  - A missing library, a vertex instancer and a library override are reported as issues.
  - A local collection without an asset ID is reported, then adopted and observed `READY`.

## Out of scope

- Geometry Nodes, particle and vertex or face instancing ([D6](../../DESIGN_DECISIONS.md#d6-asset-and-instance-identity-are-separate)).
- Library overrides, and editing linked data in place.
- Rebasing library paths when accepting external revisions (P7).
- Relations and renders addressing instance members; relations measure mesh objects only.
