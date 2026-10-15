# Scenario for Blender review

October 15, 2026. A review of Scenario for Blender (`github.com/scenario-labs/blender-plugin`, extension version 0.11.0, read at commit `6681256`) for ideas the 3D Harness lacks. The source and docs were read through the GitHub API; nothing from the repository was cloned or run. Two claims were then checked natively on this host, as noted below.

Licensed GPL-3.0-or-later: borrow ideas, not code, unless this project adopts a compatible license.

## What Scenario for Blender does

- **Cloud generation inside Blender.** Image, video, 3D, PBR material, audio and 360 environment generation through Scenario's paid API, with cost quotes before each job, a durable job store and recovery after interruption.
- **Applying results to the scene.** Generated meshes, texture sets and panoramas are applied to a chosen object, material slot or World through explicit, reversible transactions.
- **Blockout.** A language model turns a written scene description into a greybox: a JSON list of primitives that Blender builds into an owned collection.
- **Film tasks.** A JSON recipe becomes shots, a timeline, a review scene and an exported video.
- **A local MCP server.** Authenticated loopback HTTP with main-thread dispatch, ten scene tools, many cloud tools and an opt-in Python gate that is off by default.

Everything that spends credits is outside this project's scope. The code that touches the scene is plain Blender Python, and that is where the useful ideas are.

## What the code shows

- **A mesh hash that covers more.** `scenario/blender/mesh_export_fingerprint.py` (100 lines) hashes vertex positions, edge vertices, loops, polygon `loop_start`, `loop_total`, `material_index` and `use_smooth`, and every generic attribute, read in bulk with `foreach_get`.
  - The hash begins with a versioned layout tuple: `"mesh-export-v1"`, then attribute names, types and domains, field lengths, material slots, and UV layer names with their active flags.
  - Values are byteswapped to little-endian, and a 256 MiB budget is checked before hashing.
  - The 3D Harness's `mesh_record` and `_mesh_hash` ([blender.py](../../dcc_harness/blender.py)) hash only positions, loop vertex indices, loop counts and material indices.
  - So a change limited to shading, sharp edges, creases, seams or a colour attribute leaves `geometry_hash` unchanged, and a preservation contract cannot see it.
- **A refusal list for in-place edits.** `scenario/blender/mesh_application.py` lists exactly what it will not edit in place and why: modifiers, constraints, vertex groups, shape keys, animation, linked or overridden data, bone or vertex parenting, object-linked material slots, custom mesh properties, and any mode other than Object.
  - It snapshots the target first: four matrices (basis, local, world and parent inverse), the parent and parent type, collections and the active material index, after a `view_layer.update()`, because a parent edit can leave `matrix_world` stale.
  - Validating the target is simply recapturing it and comparing.
- **Blockout schema.** `scenario/core/scene/blockout.py` (200 lines, no `bpy`) defines a flat list of elements with `name`, `category` (10 values), `primitive` (box, cylinder, plane, wedge, cone, sphere), `position`, `size`, `rotation` (yaw in degrees) and `group`.
  - Units are metres with Z up; a shape resting on the ground has `z = size_z / 2`.
  - `parse_plan` strips code fences, recovers whole objects from a truncated array and clamps every number: size 0.02–500 m, coordinates ±2000 m, at most 200 elements. Unknown categories become `other` and unknown primitives `box`. `parse_complete_plan` is the strict variant that rejects a recovered prefix.
  - Building uses one shared unit mesh per primitive, scaled to size. Groups become child collections, and every object carries a tag.
  - A rebuild stages the new tree before removing the old one, and refuses when the collection holds untagged objects, is shared or has moved.
  - Refine sends the whole current plan back with the requested change. Rebuild replays the stored plan without a model call.
- **Texture sets on a material slot.** `scenario/blender/material_application.py` never edits the existing material. It builds a new Principled BSDF material and assigns it only to the captured slot.
  - One explicit `ShaderNodeUVMap`, set to the active UV layer by name, feeds every image node.
  - Base colour is sRGB and every other map is Non-Color. Smoothness goes through an Invert node into Roughness.
  - The normal map uses the same UV layer and chains into a Bump node for height. AO and edge maps are left as labelled, unconnected nodes.
  - Texture roles come from metadata, never from file names. Duplicate roles, or roughness together with smoothness, are refused.
  - Its own limitations page notes there is no Mapping node, so tiling cannot be controlled.
- **Panoramas on the World.** `scenario/blender/world_application.py` builds a new World (Environment Texture, Background, World Output) instead of editing the current one, and requires a 2:1 image.
  - Restoring the previous World is refused if the new World's nodes, links, colour space or packed bytes have changed since it was applied.
  - `docs/WORLD_APPLICATION.md` records image decoding defects in Blender 5.0–5.2:
    - JPEG EXIF orientation and ICC profiles are ignored.
    - EXR files with AP1 or Rec.2020 primaries load as linear Rec.709.
    - A progressive JPEG with many scans took about 8 s to load on 5.1.2, and JPEG comment markers can stall the main thread for longer.
- **Python edits do not mark the file modified.** `scenario/blender/file_state.py` pushes one named `bpy.ops.ed.undo_push` after a change that really happened, because data written from Python, timers or MCP does not set `bpy.data.is_dirty`.
  - The push is deferred while a sculpt or paint stroke is running, needs a window override, and is never made inside an operator that pushes its own undo.
  - **Checked here:** on Blender 5.1.1 and 5.2.1, a background session that opened a saved file, moved an object and added a material still reported `is_dirty == False`.
- **A scene revision counter.** `scenario/blender/job_session.py` keeps a revision counter per scene.
  - Any non-empty `depsgraph_update_post`, `frame_change_pre`, undo, redo or file load invalidates it.
  - A target is checked as still alive by touching `target.name` and catching `ReferenceError`, never by looking it up by name.
  - A pending write is refused once the counter has moved. This covers changes inside a live session, which file hashes cannot see.
- **Isolated child renders.** Review renders write a private `.blend` snapshot and render it in a child process started with `--offline-mode --factory-startup --disable-autoexec --background`. The harness launchers already use the last three flags; Blender 5.1 also accepts `--offline-mode` ("Disallow internet access, overriding the preference").
- **Doc drift checks.** Each canonical doc has a record in `docs/knowledge.json`: what kind of coverage it has, the revision it was reviewed at, a short statement of its limits, and a sorted list of the source files it describes. A script flags the doc when any of those sources changes after its reviewed revision. This is drift detection for docs, not a way of keeping Blender API knowledge current.
- **Honest timeouts.** The MCP server reports a request that expired before it started as "not executed", and one that timed out mid-run as "outcome unknown, do not resubmit automatically". The harness already treats unresolved operations the same way.

## Comparison with the 3D Harness at 0.18.0

| Scenario for Blender | 3D Harness | Gap |
|---|---|---|
| Mesh hash over topology, smoothing and every generic attribute, with a versioned layout prefix | `geometry_hash` over positions, loop vertex indices, loop counts and material indices | **P15** |
| Blockout JSON built into an owned, tagged collection; rebuild refused if the collection was edited | Planning skill and bounded construction helpers; no greybox spec | **P16** |
| Texture-set and World application conventions, plus Blender 5.x image decoding defects | `dcc-materials`, `blender-shading` and `blender-lighting` skills without these notes | **P17** |
| An undo push after Python edits so the file reads as modified | `native_dirty` read from `is_dirty` as a readiness condition, and `blender-python` without the note | **M6**, **P17** |
| `--offline-mode` on child Blender processes | `--factory-startup --disable-autoexec` | **M6** |
| Per-doc source lists, a reviewed revision and a drift check | Each skill's `python verify` block run on Blender 5.1.1 and 5.2.1; no record of sources or the version checked | **P18** |
| A scene revision counter that refuses writes after live edits | File hashes bound to saved checkpoints | **X9**, deferred |
| A refusal list and a full target snapshot for in-place mesh replacement | Not applicable without generated assets | **X7**, deferred |
| Outcomes reported as executed, not executed or unknown | Unresolved operations and no blind replay ([D4](../DESIGN_DECISIONS.md#d4-operation-identity-and-retry-ownership)) | None |
| Fixed-camera renders that leave the user's scene untouched | `render` binds a saved file's hash and never saves it | None |

## The `native_dirty` condition

Observation records `native_dirty` from `bpy.data.is_dirty`. `observe`, adoption, coordination evidence, quality, spatial and workflow checks all require it to be `False`, and `observe_visibility` refuses when `is_dirty` is set, with the message "requires a saved, unmodified native checkpoint". The native probe above shows that edits made from Python in the same process do not set the flag. In the owned background process, observation runs on a freshly opened file, so the condition holds. A caller that edits the scene from Python and then observes in the same session would still pass it, and would record the saved file's hash next to a different scene in memory. M6 should find every path that can reach these checks after an in-process edit, then either compare a fresh in-memory hash with the saved file or state the limit in the guides.

## Not adopted

- **Cloud generation, quotes, the job store, uploads and Film tasks.** They need Scenario's paid API and an account. The only transferable lesson is already a rule here: record the intent before acting, and never replay an uncertain submission.
- **The MCP server's security model.** Loopback binding, Host and Origin checks, a bearer token compared with `hmac.compare_digest`, sanitized errors and a Python gate that is off by default. All of it is sound, but this project does not ship an MCP server. Revisit with X3.
- **Live API introspection.** `blender_api_help` resolves a `bpy` path in the running Blender. The Blender MCP used here already offers `search_api_docs` and `get_python_api_docs`.
- **Provenance stored on objects.** Scenario keeps provenance in a durable store and strips its own identifier properties before sharing a bundle. The harness's checkpoint records already work this way.
