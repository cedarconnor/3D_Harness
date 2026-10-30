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
import sys

import bpy

from .blender import observe as observe_raw
from .evidence import digest, file_hash, validate_observation
from .uv_guard import UV_NOISE_TOLERANCE

INTERACTIVE_REASON = ("Observed in an interactive session, where Blender does not mark edits made from Python as "
                      "modified; use the observe command for saved-state evidence")


def _buffer(collection, prop, length, kind="f"):
    values = array.array(kind, [0]) * length
    collection.foreach_get(prop, values)
    return values


def _uv(mesh):
    return {layer.name: list(_buffer(layer.data, "uv", len(layer.data) * 2))
            for layer in mesh.uv_layers}


# foreach_get property, array type and width for each attribute type; FLOAT4 arrived in Blender 5.2.
ATTRIBUTE_VALUES = {
    "FLOAT": ("value", "f", 1), "INT": ("value", "i", 1), "BOOLEAN": ("value", "b", 1), "INT8": ("value", "i", 1),
    "FLOAT2": ("vector", "f", 2), "FLOAT_VECTOR": ("vector", "f", 3), "FLOAT4": ("vector", "f", 4),
    "FLOAT_COLOR": ("color", "f", 4), "BYTE_COLOR": ("color", "f", 4), "QUATERNION": ("value", "f", 4),
    "FLOAT4X4": ("value", "f", 16), "INT16_2D": ("value", "i", 2), "INT32_2D": ("value", "i", 2),
}
# Layers measured by source_mesh_hash and source_uv_hash, or holding editor state rather than content.
ATTRIBUTES_MEASURED_ELSEWHERE = ("position", "material_index")
INTERNAL_ATTRIBUTES_MEASURED = (".edge_verts", ".corner_edge")
ATTRIBUTE_COVERAGE = {"version": 1, "excluded": [
    "position and material_index (source_mesh_hash)", "UV maps (source_uv_hash)",
    "internal layers other than .edge_verts and .corner_edge, such as selection and hiding"]}


def _attribute_hash(mesh):
    """Hash authored edges and every attribute the source mesh and UV hashes leave out.

    Covers smoothing, sharp edges, seams, creases, colors, custom normals and custom data. Blender
    removes such a layer when it is cleared, so its presence is part of the hash. Returns the hash
    and any attribute types this version cannot read; their layout is still hashed.
    """
    uv_maps = {layer.name for layer in mesh.uv_layers}
    attributes = sorted((a for a in mesh.attributes if a.name in INTERNAL_ATTRIBUTES_MEASURED or not (
        a.name.startswith(".") or a.name in ATTRIBUTES_MEASURED_ELSEWHERE or a.name in uv_maps)), key=lambda a: a.name)
    h = hashlib.sha256()
    h.update(repr(("attributes-v1", [(a.name, a.domain, a.data_type, len(a.data)) for a in attributes])).encode())
    unknown = []
    for attribute in attributes:
        if attribute.data_type == "STRING":
            for item in attribute.data:
                h.update(len(item.value).to_bytes(4, "little")); h.update(item.value)
            continue
        if attribute.data_type not in ATTRIBUTE_VALUES:
            unknown.append(attribute.data_type)
            continue
        prop, kind, width = ATTRIBUTE_VALUES[attribute.data_type]
        values = _buffer(attribute.data, prop, len(attribute.data) * width, kind)
        if sys.byteorder != "little":
            values.byteswap()
        h.update(values.tobytes())
    return h.hexdigest(), sorted(set(unknown))


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


def enhance(raw, *, saved=True):
    """Supplement a current raw observation without changing it or the scene."""
    validate_observation(raw)
    source = Path(bpy.data.filepath)
    if saved and (not bpy.data.filepath or not source.is_file()):
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
            source_hashes[pointer] = (h.hexdigest(), digest(_uv(mesh))) + _attribute_hash(mesh)
        record["source_mesh_hash"], record["source_uv_hash"], record["source_attribute_hash"], unknown = source_hashes[pointer]
        obs["issues"].extend(f"Unmeasured mesh attribute type {kind}: {obj.name}" for kind in unknown)
        record["mesh_datablock"] = _rna_value(mesh)
        record["modifier_settings"] = [
            {"type": mod.type, "settings": {
                prop.identifier: _rna_value(getattr(mod, prop.identifier))
                for prop in mod.bl_rna.properties if not prop.is_readonly
            }} for mod in obj.modifiers
        ]
        for modifier, settings in zip(obj.modifiers, record['modifier_settings']):
            owner=obj.get('dcc_modifier_effects',{}).get(modifier.name)
            if owner is not None:
                settings['dcc_effect_id']=owner
            if modifier.type == 'NODES':
                from .node_asset_blender import modifier_record
                try:
                    settings['node_asset'] = modifier_record(modifier)
                except ValueError as exc:
                    settings['node_asset'] = {'unmeasured': str(exc)}
                    obs['issues'].append(str(exc) + ': ' + obj.name)
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
    obs["coverage"]["source_attributes"] = copy.deepcopy(ATTRIBUTE_COVERAGE)
    # Retain this legacy v2 producer marker for observation compatibility. It
    # does not apply a tolerance or alter extracted UV values. The comparator's
    # check report records the actual (versioned) admission policy.
    obs["coverage"]["independent_uv_guard"] = {
        "version": 2, "absolute_tolerance": UV_NOISE_TOLERANCE,
        "gates": "Exact authored mesh/UV, evaluated geometry and writable modifier settings; matching UV layers and array sizes",
    }
    _normalize_packed(obs)
    obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
    obs["checkpoint_sha256"] = file_hash(source) if saved else None
    # Blender marks a file modified only through undo steps, so edits made from Python or an MCP
    # leave is_dirty false. Only a background process, where nothing but the calling script runs,
    # can rely on it; an interactive session cannot show that memory matches the saved file.
    obs["native_dirty"] = bool(bpy.data.is_dirty) or not bpy.app.background or not saved
    if not bpy.app.background:
        obs["native_dirty_reason"] = INTERACTIVE_REASON
    return obs


def observe(scene=None):
    return enhance(observe_raw(scene))


def measure_live(scene=None):
    """Use the same measured fields for a live guard, without claiming saved-file evidence."""
    return enhance(observe_raw(scene), saved=False)
