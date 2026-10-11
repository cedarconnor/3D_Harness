---
name: blender-pipeline
description: Organize Blender 5.x files and exchange data with other tools. Covers project folders and naming, versioned saves, relative paths and packing, linking versus appending, library overrides, asset libraries and marking assets, collections as units of work, USD, Alembic, FBX, glTF, OBJ and STL interchange with their axis and scale conventions, and checking every exchange by re-importing.
---

# Pipeline, files and interchange

A pipeline is the set of conventions that let a project survive many sessions, people and tools. Make the conventions explicit and check them; a file that only works on one machine has failed. In a harness project, checkpoints, identities and edits are tracked by [the harness](../dcc-harness/SKILL.md); these practices cover the files around it.

## Project structure and naming

- **Folders.** One project root with fixed folders: `source/` (.blend files), `textures/`, `references/`, `cache/` (simulation and bake caches), `renders/`, `exports/`, `delivery/`. Keep paths relative to the .blend (`//textures/wood.png`) so the project moves as one.
- **Versioned saves.** Use `asset_v001.blend`, then `v002` and so on, and never overwrite a published version. Use `bpy.ops.wm.save_as_mainfile(filepath=..., copy=True)` for snapshots that leave the open document unchanged. Keep `.blend1` backups out of deliveries.
- **Prefixes.** Use them for datablocks: `GEO-`, `MAT-`, `LGT-`, `CAM-`, `COL-`, `NG-` (node groups), `ACT-` (actions), or the engine's conventions (`SM_`, `M_`, `T_`). Stable names survive linking; `.001` suffixes are a sign of an accidental duplicate.
- **Collections.** Use them as units of work: one collection per asset or set piece, with a clear owner. Scripts create their content in their own collection, and on a rerun replace only what they own.

## Paths and packing

- **Relative paths** need a saved file: `bpy.ops.file.make_paths_relative()` does nothing in an unsaved file. Find missing files with `bpy.ops.file.find_missing_files`, and report them with `bpy.data.file_path_foreach` (5.0+) or by walking `bpy.data.images` and libraries.
- **Packing.** `bpy.ops.file.pack_all()` (or `image.pack()`) makes a self-contained .blend for handoffs and archives. Unpack to `//textures/` for editing. Packed images are part of the file's identity: changing them changes the asset. The harness's relocation flow packs external textures for exactly this reason (see [external revisions](../../../docs/guides/EXTERNAL_REVISIONS.md)).
- **Losing datablocks.** Datablocks with zero users are dropped on save. Give a fake user (`use_fake_user = True`) to node groups, actions, materials and brushes you are keeping for later.

## Linking, appending and overrides

- **Appending** copies data into the current file; the copy no longer updates. Use it for one-off reuse.
- **Linking** references data in another file (`bpy.data.libraries.load(path, link=True, relative=True)`); edits happen in the source file and propagate. Use it for shared assets, sets and characters used in many shots.
- **Library overrides** make a linked hierarchy locally editable where its author allowed it: posing a linked character, moving a linked prop. Create them with `collection_or_object.override_hierarchy_create(scene, view_layer)`. Called from Python on a collection that an instance empty shows, it adds the override beside the instance; remove the empty, or the asset appears twice. Measured on 5.1, where a USD export then contained two crates. Prefer overrides to making the data local, which breaks the link.
- **Asset libraries.** Mark reusable items with `id.asset_mark()`, plus `asset_data.tags` and a description, and generate a preview. Register the library folders in Preferences (`filepaths.asset_libraries`). Store assets in dedicated library files, not in shot files.

## Interchange formats

| Format | Use | Points to set |
|---|---|---|
| glTF/GLB | Web, realtime, AR | Y-up conversion (`export_yup`), `export_apply` for modifiers (not object scale), Principled BSDF and image textures only, at most 4 skin influences. See [realtime assets](../blender-realtime-assets/SKILL.md) |
| FBX | Unity, Unreal, DCC exchange | `apply_scale_options`, `axis_forward` and `axis_up`, `add_leaf_bones=False` for engines, `use_armature_deform_only=True`. The 5.x default importer is `wm.fbx_import` |
| USD (`wm.usd_export`) | Pipeline interchange, Omniverse, Houdini, Apple | Materials as UsdPreviewSurface. Its subdivision setting decides whether a cage or the subdivided mesh is exported. Instancing is preserved. Check the axes and the metres-per-unit setting |
| Alembic (`wm.alembic_export`) | Baked animated geometry for lighting and FX | Frame range and subframes for motion blur. Geometry only: no rigs, limited materials |
| OBJ, STL, PLY (`wm.obj_export`, `wm.stl_export`, `wm.ply_export`) | Static meshes, printing, scans | STL has no units: state them, and convert millimetres to metres once (see [precision CAD](../blender-precision-cad/SKILL.md)) |

Collada was removed in 5.0. Collection exporters (`collection.exporters`, 5.0+) store per-collection export settings, so repeated exports are consistent.

## Check every exchange

Re-import the exported file into an empty scene (`read_factory_settings(use_empty=True)`), then compare it with the source:

- object names and count;
- dimensions and facing, against a known measurement;
- triangle and vertex counts;
- material count and slots;
- UV maps;
- animation frame range and a sampled pose;
- that every texture resolves.

Do the same in the receiving application when you can. Record the export settings with the delivery. An exporter that "finished" proves nothing about what arrived.

```python verify
import bpy

# A library file with a marked asset, saved to disk.
bpy.ops.mesh.primitive_cube_add(size=1); crate = bpy.context.object; crate.name = 'GEO-crate'
lib_col = bpy.data.collections.new('COL-crate'); bpy.context.scene.collection.children.link(lib_col)
lib_col.objects.link(crate); bpy.context.scene.collection.objects.unlink(crate)
lib_col.asset_mark(); lib_col.asset_data.tags.new('prop'); lib_col.asset_data.description = 'Shipping crate, 1 m'
group = bpy.data.node_groups.new('NG-unused', 'GeometryNodeTree'); group.use_fake_user = True
library_path = str(WORK / 'crate_v001.blend')
bpy.ops.wm.save_as_mainfile(filepath=library_path)

# A shot file links the collection and overrides it so it can be moved locally.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / 'shot_v001.blend'))
with bpy.data.libraries.load(library_path, link=True, relative=True) as (data_from, data_to):
    assert 'COL-crate' in data_from.collections and 'NG-unused' in data_from.node_groups   # the fake user kept it
    data_to.collections = ['COL-crate']
linked = data_to.collections[0]
assert linked.library is not None and linked.library.filepath.startswith('//')
instance = bpy.data.objects.new('crate_instance', None)
instance.instance_type, instance.instance_collection = 'COLLECTION', linked
bpy.context.scene.collection.objects.link(instance)
override = linked.override_hierarchy_create(bpy.context.scene, bpy.context.view_layer)
assert override.override_library is not None and override.override_library.reference == linked
bpy.data.objects.remove(instance)          # the Python call keeps the instance empty: remove it, or the crate is in the scene twice

# USD and Alembic round trips, checked by re-importing into an empty scene.
usd = str(WORK / 'crate.usdc'); abc = str(WORK / 'crate.abc')
assert bpy.ops.wm.usd_export(filepath=usd) == {'FINISHED'}
assert bpy.ops.wm.alembic_export(filepath=abc) == {'FINISHED'}
for path, importer in ((usd, bpy.ops.wm.usd_import), (abc, bpy.ops.wm.alembic_import)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert importer(filepath=path) == {'FINISHED'}
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 1 and all(abs(d - 1.0) < 1e-4 for d in meshes[0].dimensions), (path, [o.name for o in meshes])
```
