"""Read-only native supplements used by the independent blind evaluator."""
import array
import hashlib

import bpy


def _buffer(collection, prop, length, kind="f"):
    values = array.array(kind, [0]) * length
    collection.foreach_get(prop, values)
    return values


def _uv(mesh):
    return {layer.name: list(_buffer(layer.data, "uv", len(layer.data) * 2)) for layer in mesh.uv_layers}


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


def supplement(obs):
    """Add exact source hashes and evaluated UV arrays without changing the scene."""
    from dcc_harness.evidence import digest
    from dcc_harness.uv_guard import UV_NOISE_TOLERANCE
    deps = bpy.context.evaluated_depsgraph_get()
    for record in obs["objects"].values():
        if record["type"] != "MESH":
            continue
        obj = bpy.context.scene.objects[record["name"]]
        mesh = obj.data
        h = hashlib.sha256()
        for values in (_buffer(mesh.vertices, "co", len(mesh.vertices) * 3),
                       _buffer(mesh.loops, "vertex_index", len(mesh.loops), "i"),
                       _buffer(mesh.polygons, "loop_total", len(mesh.polygons), "i"),
                       _buffer(mesh.polygons, "material_index", len(mesh.polygons), "i")):
            h.update(values.tobytes())
        record["source_mesh_hash"] = h.hexdigest()
        record["source_uv_hash"] = digest(_uv(mesh))
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
        finally:
            evaluated.to_mesh_clear()
    obs["coverage"]["independent_uv_guard"] = {
        "version": 2, "absolute_tolerance": UV_NOISE_TOLERANCE,
        "gates": "Exact authored mesh/UV, evaluated geometry and writable modifier settings; matching UV layers and array sizes",
    }
    obs["revision"] = digest({k: obs[k] for k in ("objects", "materials", "scene", "coverage", "issues")})
    return obs
