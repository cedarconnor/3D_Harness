"""Portable, conservative preservation checks for declared continuity stages."""
from __future__ import annotations

import copy
import math

from .evidence import canonical, compare, evaluate, validate_observation
from .uv_guard import evaluated_uv_noise_only, UV_NOISE_TOLERANCE, UV_ADJACENT_MAX_DELTA

SCHEMA = "dcc.continuity.contract.v1"
CONTRACT_FIELDS = {"schema", "spec", "allowed_object_prefixes", "allowed_material_inputs",
                   "allowed_new_prefixes", "centers", "center_tolerance", "preserve_centers",
                   "exact_asset_counts", "sharing_groups", "allowed_deleted_ids"}
OBJECT_FIELDS = {"name", "type", "asset_id", "matrix_world", "parent", "collections", "visibility",
                 "material_ids", "vertices", "triangles", "geometry_hash", "uv_hash", "uv_layers",
                 "bounds", "dimensions", "light", "camera", "source_mesh_hash", "source_uv_hash",
                 "modifier_settings", "evaluated_uv_values", "mesh_datablock"}


def _prefixes(items, label):
    if not isinstance(items, list) or any(not isinstance(p, str) or not p or any(c in p for c in "*?[]") for p in items):
        raise ValueError(f"{label} requires nonempty string prefixes")


def validate_contract(contract):
    canonical(contract)
    if not isinstance(contract, dict) or contract.get("schema") != SCHEMA or set(contract) - CONTRACT_FIELDS:
        raise ValueError("Unsupported continuity contract schema or rule")
    if not isinstance(contract.get("spec"), dict):
        raise ValueError("Contract requires a dcc.spec.v1 spec")
    deleted = contract.get("allowed_deleted_ids", [])
    if (not isinstance(deleted, list) or any(not isinstance(i, str) or not i for i in deleted) or
            len(set(deleted)) != len(deleted) or set(deleted) & set(contract['spec'].get('required', {}))):
        raise ValueError("Deletion permission requires distinct exact IDs outside required targets")
    allowed = contract.get("allowed_object_prefixes", {})
    if not isinstance(allowed, dict):
        raise ValueError("allowed_object_prefixes must be a mapping")
    _prefixes(list(allowed), "allowed_object_prefixes")
    for fields in allowed.values():
        if not isinstance(fields, list) or any(not isinstance(f, str) or f not in OBJECT_FIELDS for f in fields):
            raise ValueError("Unknown allowed object field")
    new = contract.get("allowed_new_prefixes", ["ext."])
    _prefixes(new, "allowed_new_prefixes")
    if any(not p.startswith("ext.") for p in new):
        raise ValueError("New object prefixes must be scoped beneath ext.")
    _prefixes(contract.get("preserve_centers", []), "preserve_centers")
    tolerance = contract.get("center_tolerance", .001)
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid center tolerance")
    centers = contract.get("centers", {})
    if not isinstance(centers, dict):
        raise ValueError("centers must be a mapping")
    for iid, center in centers.items():
        if not isinstance(iid, str) or not isinstance(center, list) or len(center) != 3 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in center):
            raise ValueError("Centers require three finite coordinates")
    counts = contract.get("exact_asset_counts", {})
    if not isinstance(counts, dict) or any(not isinstance(a, str) or isinstance(n, bool) or not isinstance(n, int) or n < 0 for a, n in counts.items()):
        raise ValueError("exact_asset_counts requires nonnegative integer counts")
    materials = contract.get("allowed_material_inputs", {})
    if not isinstance(materials, dict):
        raise ValueError("allowed_material_inputs must be a mapping")
    for mid, nodes in materials.items():
        if not isinstance(mid, str) or not isinstance(nodes, dict) or not nodes:
            raise ValueError("Invalid allowed material input declaration")
        for node, sockets in nodes.items():
            if not isinstance(node, str) or not isinstance(sockets, dict) or not sockets or any(not isinstance(s, str) for s in sockets):
                raise ValueError("Invalid allowed shader socket declaration")
    groups = contract.get("sharing_groups", [])
    if not isinstance(groups, list):
        raise ValueError("sharing_groups must be a list")
    for group in groups:
        if not isinstance(group, list) or len(group) < 2 or any(not isinstance(iid, str) for iid in group) or len(set(group)) != len(group):
            raise ValueError("Sharing groups require at least two distinct object IDs")


def _center(record):
    bounds = record.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 2 or any(not isinstance(row, list) or len(row) != 3 for row in bounds):
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for row in bounds for v in row):
        return None
    return [(bounds[0][i] + bounds[1][i]) / 2 for i in range(3)]


def evaluate_stage(before, after, contract):
    """Check required results and exact preservation outside concrete permissions.

    Required targets should be cumulative across stages. Material permissions set
    exact desired values and permit no other graph/property/binding change.
    """
    validate_contract(contract)
    validate_observation(before)
    validate_observation(after)
    check = evaluate(after, contract["spec"])
    failures = check["failures"]
    for label, obs in (("Before", before), ("After", after)):
        version = obs["coverage"].get("continuity_observation")
        if type(version) is not int or version not in (1, 2):
            failures.append(f"{label} continuity observation coverage missing or unsupported")
        elif (version == 2 and obs["coverage"].get("dimensions_measurement") != "world_linear_extents_v2") or (
                version == 1 and "dimensions_measurement" in obs["coverage"]):
            failures.append(f"{label} dimensions measurement coverage differs from its version")
        for iid, obj in obs["objects"].items():
            if obj.get("type") == "MESH" and any(field not in obj for field in (
                    "source_mesh_hash", "source_uv_hash", "modifier_settings", "evaluated_uv_values", "mesh_datablock")):
                failures.append(f"{label} mesh coverage missing: {iid}")
    allow = {"objects": {}, "materials": {}}
    deleted = contract.get('allowed_deleted_ids', [])
    if any(i not in before['objects'] for i in deleted):
        failures.append('Deletion scope names objects missing from the before observation')
    uv_noise = []
    for iid, old in before["objects"].items():
        fields = set()
        for prefix, declared in contract.get("allowed_object_prefixes", {}).items():
            if iid.startswith(prefix):
                fields.update(declared)
        new = after["objects"].get(iid, {})
        if old.get("type") == "MESH" and evaluated_uv_noise_only(old, new):
            fields.update(("uv_hash", "evaluated_uv_values"))
            if any(old.get(k) != new.get(k) for k in ("uv_hash", "evaluated_uv_values")):
                uv_noise.append(iid)
        allow["objects"][iid] = sorted(fields)
        if iid in deleted:
            allow['objects'][iid].append('deleted')
    for iid in after["objects"].keys() - before["objects"].keys():
        if after["objects"][iid].get("type") == "LIGHT":
            failures.append(f"New light is outside the fixed illumination contract: {iid}")
        if any(iid.startswith(p) for p in contract.get("allowed_new_prefixes", ["ext."])):
            allow["objects"][iid] = ["created"]
    for mid in after["materials"].keys() - before["materials"].keys():
        allow["materials"][mid] = ["created"]
    for mid, node_inputs in contract.get("allowed_material_inputs", {}).items():
        expected = copy.deepcopy(before["materials"].get(mid))
        if expected is None:
            failures.append(f"Material input target missing before stage: {mid}")
            continue
        graph = expected.get("graph") or {}
        nodes = {node["name"]: node for node in graph.get("nodes", [])}
        for name, inputs in node_inputs.items():
            node = nodes.get(name, {})
            for socket, value in inputs.items():
                if socket not in node.get("inputs", {}):
                    failures.append(f"Material input target missing: {mid}/{name}/{socket}")
                elif any(link[2:] == [name, socket] for link in graph.get("links", [])):
                    failures.append(f"Material input target is linked: {mid}/{name}/{socket}")
                else:
                    node["inputs"][socket] = copy.deepcopy(value)
        if expected != after["materials"].get(mid):
            failures.append(f"Material differs beyond requested inputs or desired values: {mid}")
        allow["materials"][mid] = ["graph"]
    preservation = compare(before, after, allow)
    if not preservation["passed"]:
        failures.append("Observed preservation check failed")
    tolerance = contract.get("center_tolerance", .001)
    centers = copy.deepcopy(contract.get("centers", {}))
    for prefix in contract.get("preserve_centers", []):
        targets = [iid for iid in before["objects"] if iid.startswith(prefix)]
        if not targets:
            failures.append(f"Preserved center prefix matches no prior object: {prefix}")
        for iid in targets:
            desired = _center(before["objects"][iid])
            observed = _center(after["objects"].get(iid, {}))
            if desired is None or observed is None or any(abs(a-b) > tolerance for a,b in zip(desired, observed)):
                failures.append(f"Preserved center moved or missing: {iid}")
    for iid, desired in centers.items():
        observed = _center(after["objects"].get(iid, {}))
        if observed is None or any(abs(a-b) > tolerance for a,b in zip(desired, observed)):
            failures.append(f"Desired center differs or missing: {iid}")
    for aid, count in contract.get("exact_asset_counts", {}).items():
        actual = sum(obj.get("type") == "MESH" and obj.get("asset_id") == aid for obj in after["objects"].values())
        if actual != count:
            failures.append(f"Asset count differs: {aid}: {actual} != {count}")
    for group in contract.get("sharing_groups", []):
        records = [after["objects"].get(iid, {}) for iid in group]
        if any(obj.get("type") != "MESH" or not obj.get("mesh_datablock") for obj in records) or any(
                obj.get("mesh_datablock") != records[0].get("mesh_datablock") for obj in records[1:]):
            failures.append("Mesh sharing group differs or missing: " + ", ".join(group))
    check.update(passed=not failures, preservation=preservation,
                 evaluated_uv_noise={"objects": uv_noise, "policy_version": 3,
                                     "absolute_tolerance": UV_NOISE_TOLERANCE,
                                     "adjacent_float32_max_delta": UV_ADJACENT_MAX_DELTA},
                 native_runtime_validation="not_performed",
                 limits=after["coverage"]["not_measured"] + [
                     "Portable checks compare observed mesh identities; native pointer sharing, scene count and dependency packing require the independent Blender evaluator"])
    return check
