"""Portable evidence, assertions and declared-change checks (no bpy dependency)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    def reject(value):
        raise ValueError(f"Nonfinite JSON number: {value}")
    value = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)
    from .observation_storage import unpack_observation
    return unpack_observation(value)


def write_json(path, value, *, compact_observation=False):
    """Evidence is immutable by default; retries cannot replace earlier observations."""
    if compact_observation:
        from .observation_storage import pack_observation
        value = pack_observation(value)
    data = json.dumps(value, indent=None if compact_observation else 2,
                      separators=(",", ":") if compact_observation else None,
                      sort_keys=True, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(data)


def validate_observation(observation):
    if observation.get("schema") != "dcc.observation.v1":
        raise ValueError("Unsupported observation schema")
    for field in ("objects", "materials", "scene", "coverage", "issues", "revision"):
        if field not in observation:
            raise ValueError(f"Observation missing {field}")
    payload = {k: observation[k] for k in ("objects", "materials", "scene", "coverage", "issues")}
    if digest(payload) != observation["revision"]:
        raise ValueError("Observation revision does not match measured content")


def evaluate(observation, spec):
    """Only implemented rules are accepted. Missing/empty coverage is never a pass."""
    validate_observation(observation)
    canonical(spec)  # Reject NaN/Infinity even when called directly, not through JSON.
    permitted = {"schema", "required", "min_asset_definitions", "required_materials", "units", "material_nodes"}
    if spec.get("schema") != "dcc.spec.v1" or set(spec) - permitted:
        raise ValueError("Unsupported spec schema or rule")
    if not spec.get("required"):
        raise ValueError("Spec must declare at least one required target")
    objects = observation["objects"]
    failures = list(observation["issues"])
    checked = []
    if not objects:
        failures.append("No objects observed")
    if spec.get("units") and observation["scene"]["units"] != spec["units"]:
        failures.append("Unit settings differ")
    for iid, rules in spec["required"].items():
        if set(rules) - {"type", "asset_id", "dimensions", "tolerance", "min_triangles", "max_triangles", "material_ids", "require_uv"}:
            raise ValueError(f"Unknown rule on {iid}")
        obj = objects.get(iid)
        if obj is None:
            failures.append(f"Missing target: {iid}")
            continue
        checked.append(iid)
        for key in ("type", "asset_id", "material_ids"):
            if key in rules and obj.get(key) != rules[key]:
                failures.append(f"{iid}: {key} differs")
        if "dimensions" in rules:
            tolerance = rules.get("tolerance", 0.001)
            dims = rules["dimensions"]
            if len(dims) != 3 or tolerance < 0:
                raise ValueError("Invalid dimensions or tolerance")
            if any(abs(a-b) > tolerance for a, b in zip(obj["dimensions"], dims)):
                failures.append(f"{iid}: dimensions {obj['dimensions']} != {dims}")
        for key, wrong in (("min_triangles", lambda n,v: n < v), ("max_triangles", lambda n,v: n > v)):
            if key in rules and wrong(obj.get("triangles", 0), rules[key]):
                failures.append(f"{iid}: {key} violated")
        if rules.get("require_uv") and not obj.get("uv_layers"):
            failures.append(f"{iid}: no UV layer")
    assets = {o["asset_id"] for o in objects.values() if o["type"] == "MESH" and o.get("asset_id")}
    if len(assets) < spec.get("min_asset_definitions", 0):
        failures.append("Too few asset definitions")
    for mid in spec.get("required_materials", []):
        if mid not in observation["materials"]:
            failures.append(f"Missing material: {mid}")
    for mid, nodes in spec.get("material_nodes", {}).items():
        material = observation["materials"].get(mid, {})
        observed_nodes = {n["name"]:n for n in (material.get("graph") or {}).get("nodes", [])}
        for name, inputs in nodes.items():
            node = observed_nodes.get(name, {})
            for socket, expected in inputs.items():
                if node.get("inputs", {}).get(socket) != expected:
                    failures.append(f"{mid}/{name}/{socket}: desired input differs or is missing")
    return {"schema":"dcc.check.v1", "revision":observation["revision"],
            "passed":not failures, "checked_targets":checked, "failures":failures,
            "asset_definitions":len(assets), "artistic_acceptance":"not_evaluated"}


def compare(before, after, allowed=None):
    """Exact observed-field comparison; unmeasured native state is explicitly excluded."""
    validate_observation(before)
    validate_observation(after)
    allowed = allowed or {}
    if set(allowed) - {"objects", "materials", "scene"}:
        raise ValueError("Unknown change-contract section")
    changes = []
    for category in ("objects", "materials"):
        old, new = before[category], after[category]
        for key in sorted(old.keys() | new.keys()):
            if key not in old or key not in new:
                fields = ["created" if key not in old else "deleted"]
            else:
                fields = [f for f in sorted(old[key].keys() | new[key].keys()) if old[key].get(f) != new[key].get(f)]
            for field in fields:
                changes.append({"category":category,"id":key,"field":field,
                                "allowed":field in allowed.get(category, {}).get(key, [])})
    for field in sorted(before["scene"].keys() | after["scene"].keys()):
        if before["scene"].get(field) != after["scene"].get(field):
            changes.append({"category":"scene","id":"scene","field":field,
                            "allowed":field in allowed.get("scene", [])})
    coverage_matches = before["coverage"] == after["coverage"]
    issues = before["issues"] + after["issues"]
    return {"schema":"dcc.delta.v1","before":before["revision"],"after":after["revision"],
            "changes":changes,"coverage_matches":coverage_matches,"issues":issues,
            "passed":coverage_matches and not issues and all(c["allowed"] for c in changes),
            "limits":before["coverage"]["not_measured"]}

