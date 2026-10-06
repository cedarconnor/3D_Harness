"""Read-only Blender observation for continuity checkpoints.

``observe()`` requires a saved native file and never saves or repairs the scene.
``enhance(raw)`` keeps the original observation intact for independent receipts.
Packed image locations are normalized only in the comparable copy; their content
hashes, names and color spaces remain measured.
"""
from __future__ import annotations

import array
import copy
import hashlib
import math
from pathlib import Path

import bpy

from .blender import observe as observe_raw
from .evidence import digest, file_hash, validate_observation
from .uv_guard import UV_NOISE_TOLERANCE


def _buffer(collection, prop, length, kind="f"):
    values = array.array(kind, [0]) * length
    collection.foreach_get(prop, values)
    return values


def _uv(mesh):
    return {layer.name: list(_buffer(layer.data, "uv", len(layer.data) * 2))
            for layer in mesh.uv_layers}


def _rna_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return {"type": value.bl_rna.identifier, "name": value.name_full,
                "library": value.library.filepath if value.library else None}
    try:
        return [_rna_value(item) for item in value]
    except TypeError:
        return {"unmeasured_type": type(value).__name__}


def _normalize_packed(item):
    if isinstance(item, dict):
        if item.get("packed") is True and item.get("sha256"):
            item["path"] = "<packed>"
        for child in item.values():
            _normalize_packed(child)
    elif isinstance(item, list):
        for child in item:
            _normalize_packed(child)


def enhance(raw):
    """Supplement a current raw observation without changing it or the scene."""
    validate_observation(raw)
    source = Path(bpy.data.filepath)
    if not bpy.data.filepath or not source.is_file():
        raise ValueError("Continuity observation requires a saved native checkpoint")
    obs = copy.deepcopy(raw)
    deps = bpy.context.evaluated_depsgraph_get()
    # Authored data is shared by linked objects; evaluated data is not. Only
    # reuse source hashes inside this call, while retaining per-object checks.
    source_hashes = {}
    for record in obs["objects"].values():
        if record["type"] != "MESH":
            continue
        obj = bpy.context.scene.objects[record["name"]]
        mesh = obj.data
        pointer = mesh.as_pointer()
        if pointer not in source_hashes:
            if any(not math.isfinite(coordinate) for vertex in mesh.vertices for coordinate in vertex.co):
                raise ValueError(f"Nonfinite source mesh coordinate: {obj.name}")
            h = hashlib.sha256()
            for values in (_buffer(mesh.vertices, "co", len(mesh.vertices) * 3),
                           _buffer(mesh.loops, "vertex_index", len(mesh.loops), "i"),
                           _buffer(mesh.polygons, "loop_total", len(mesh.polygons), "i"),
                           _buffer(mesh.polygons, "material_index", len(mesh.polygons), "i")):
                h.update(values.tobytes())
            source_hashes[pointer] = h.hexdigest(), digest(_uv(mesh))
        record["source_mesh_hash"], record["source_uv_hash"] = source_hashes[pointer]
        record["mesh_datablock"] = _rna_value(mesh)
        record["modifier_settings"] = [
            {"type": mod.type, "settings": {
                prop.identifier: _rna_value(getattr(mod, prop.identifier))
                for prop in mod.bl_rna.properties if not prop.is_readonly
            }} for mod in obj.modifiers
        ]
        evaluated = obj.evaluated_get(deps)
        evaluated_mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
        try:
            record["evaluated_uv_values"] = _uv(evaluated_mesh)
            # Measure world-oriented extents without cancellation against the
            # object's world translation. World bounds still measure placement.
            linear = evaluated.matrix_world.to_3x3()
            points = [linear @ vertex.co for vertex in evaluated_mesh.vertices]
            if any(not math.isfinite(coordinate) for point in points for coordinate in point):
                raise ValueError(f"Nonfinite evaluated extent coordinate: {obj.name}")
            record["dimensions"] = [
                round(max(p[axis] for p in points) - min(p[axis] for p in points), 7)
                for axis in range(3)
            ] if points else [0.0, 0.0, 0.0]
        finally:
            evaluated.to_mesh_clear()
    scene = bpy.context.scene
    obs["scene"]["render"].update(seed=scene.cycles.seed,
        denoising=scene.cycles.use_denoising,
        file_format=scene.render.image_settings.file_format)
    obs["coverage"]["continuity_observation"] = 2
    obs["coverage"]["dimensions_measurement"] = "world_linear_extents_v2"
    # Retain this legacy v2 producer marker for observation compatibility. It
    # does not apply a tolerance or alter extracted UV values. The comparator's
    # check report records the actual (versioned) admission policy.
    obs["coverage"]["independent_uv_guard"] = {
        "version": 2, "absolute_tolerance": UV_NOISE_TOLERANCE,
        "gates": "Exact authored mesh/UV, evaluated geometry and writable modifier settings; matching UV layers and array sizes",
    }
    _normalize_packed(obs)
    obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
    obs["checkpoint_sha256"] = file_hash(source)
    obs["native_dirty"] = bool(bpy.data.is_dirty)
    return obs


def observe(scene=None):
    return enhance(observe_raw(scene))
