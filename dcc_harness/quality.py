"""Reference-led candidate review over saved evidence; no executor or scheduler.

All files are relative to the round document and hash-bound. Re-run the audit
before selection. Reviewer records are attributed claims, not proof of separate
people/processes, native execution, visual quality, or artist acceptance.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from .continuity import _load_observation, _plain
from .continuity_checks import evaluate_stage
from .evidence import canonical, digest, file_hash, read_json, validate_observation, write_json
from .spatial import check_visibility


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"Expected fields {sorted(required)}; optional {sorted(optional)}")
    canonical(value)


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")


def _named(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty list")
    ids = [r.get("id") if isinstance(r, dict) else None for r in rows]
    for name in ids:
        _text(name)
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate IDs")
    return ids


def _bounds(value):
    if (not isinstance(value, list) or len(value) != 2 or
            any(not isinstance(row, list) or len(row) != 3 for row in value) or
            any(type(v) not in (int, float) or not math.isfinite(v) for row in value for v in row) or
            any(value[0][i] > value[1][i] for i in range(3))):
        raise ValueError("Bounds require ordered finite XYZ min/max in scene world units")
    return value


def reserved_space(observation, reservations, editable_prefixes=()):
    """Conservative world-AABB broad phase, not exact collision or visibility.

    Each obstacle prefix must match an observed mesh. Empty/missing coverage
    fails, rather than interpreting an absent object as available space.
    Editable is advice for resolution, never an exemption from the check.
    """
    validate_observation(observation)
    if not isinstance(reservations, list):
        raise ValueError("Reservations must be a list")
    for prefix in editable_prefixes:
        _text(prefix)
    findings, checked = [], []
    if reservations:
        _named(reservations)
    for rule in reservations:
        _fields(rule, {"id", "bounds", "obstacle_prefixes", "exempt_ids", "tolerance"})
        box = _bounds(rule["bounds"])
        prefixes = rule["obstacle_prefixes"]
        if not isinstance(prefixes, list) or not prefixes or not isinstance(rule["exempt_ids"], list):
            raise ValueError("A reservation needs explicit obstacle coverage and exemptions")
        tolerance = rule["tolerance"]
        if type(tolerance) not in (float, int) or not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("Invalid intersection tolerance")
        for iid in rule["exempt_ids"]:
            if iid not in observation["objects"]:
                raise ValueError(f"Unknown reservation exemption: {iid}")
        targets = set()
        for prefix in prefixes:
            _text(prefix)
            if any(c in prefix for c in "*?[]"):
                raise ValueError("Use literal obstacle prefixes, not globs")
            matches = {iid for iid, obj in observation["objects"].items()
                       if iid.startswith(prefix) and obj.get("type") == "MESH"}
            if not matches:
                findings.append({"reservation": rule["id"], "kind": "missing_coverage", "prefix": prefix})
            targets.update(matches)
        for iid in sorted(targets - set(rule["exempt_ids"])):
            checked.append({"reservation": rule["id"], "object": iid})
            try:
                occupied = _bounds(observation["objects"][iid].get("bounds"))
            except ValueError:
                findings.append({"reservation": rule["id"], "object": iid, "kind": "missing_bounds"})
                continue
            overlap = [min(box[1][i], occupied[1][i]) - max(box[0][i], occupied[0][i]) for i in range(3)]
            if all(v > tolerance for v in overlap):
                findings.append({"reservation": rule["id"], "object": iid, "kind": "potential_overlap",
                                 "overlap": overlap,
                                 "resolution": "within_edit_scope" if any(iid.startswith(p) for p in editable_prefixes)
                                 else "requires_scope_decision"})
    return {"schema": "dcc.reserved_space.v1", "revision": observation["revision"],
            "passed": not findings and not observation["issues"], "findings": findings,
            "checked": checked, "issues": observation["issues"],
            "limits": "World-AABB broad phase for declared obstacles only; touching is allowed. Not exact collision, support, visibility or traversability."}


def _file(root, ref):
    _fields(ref, {"path", "sha256"})
    _text(ref["path"])
    relative = Path(ref["path"])
    path = _plain(root / relative)
    if relative.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Evidence path must stay inside its round directory")
    if not path.is_file() or file_hash(path) != ref["sha256"]:
        raise ValueError(f"Missing or changed evidence: {ref['path']}")
    return path


def audit(round_path):
    round_path = _plain(round_path)
    root, spec = round_path.parent, read_json(round_path)
    spatial = spec.get('schema') == 'dcc.quality.round.v2'
    _fields(spec, {"schema", "design", "brief", "targets", "methods", "references", "views", "contract", "reservations", "candidates"} | ({'visibility_contract'} if spatial else set()))
    if spec["schema"] not in ("dcc.quality.round.v1", "dcc.quality.round.v2"):
        raise ValueError("Unsupported quality round")
    design = read_json(_file(root, spec["design"]))
    if design != {k: v for k, v in spec.items() if k not in ("schema", "design", "candidates")}:
        raise ValueError("Round differs from its retained design")
    _text(spec["brief"])
    if not isinstance(spec["methods"], dict) or not spec["methods"]:
        raise ValueError("Record the relevant construction/material methods")
    for key, value in spec["methods"].items():
        _text(key); _text(value)
    references = _named(spec["references"])
    for ref in spec["references"]:
        _fields(ref, {"id", "file", "role", "intent"})
        if ref["role"] not in ("mood", "construction", "dimension"):
            raise ValueError("Unknown reference role")
        _text(ref["intent"])
        _file(root, ref["file"])
    targets = _named(spec["targets"])
    for target in spec["targets"]:
        _fields(target, {"id", "intent", "reference_ids"})
        _text(target["intent"])
        if not isinstance(target["reference_ids"], list) or not target["reference_ids"] or any(r not in references for r in target["reference_ids"]):
            raise ValueError("Visual target needs known reference IDs")
    view_ids = _named(spec["views"])
    for view in spec["views"]:
        _fields(view, {"id", "purpose", "camera", "render"})
        if view["purpose"] not in ("whole", "detail") or not isinstance(view["camera"], dict) or not view["camera"] or not isinstance(view["render"], dict) or not view["render"]:
            raise ValueError("Views need a camera and render definition")
    if {v["purpose"] for v in spec["views"]} != {"whole", "detail"}:
        raise ValueError("Review needs whole-scene and task-detail views")
    candidates = spec["candidates"]
    ids = _named(candidates)
    if not 2 <= len(ids) <= 4 or ids[0] != "unchanged":
        raise ValueError("Compare unchanged first and one to three edits")
    observations, results = {}, {}
    for candidate in candidates:
        _fields(candidate, {"id", "checkpoint", "observation", "renders"} | ({'visibility'} if spatial else set()))
        native = _file(root, candidate["checkpoint"])
        obs = _load_observation(_file(root, candidate["observation"]), native)
        if obs.get("native_dirty") is not False:
            raise ValueError("Candidate observation must be made from a saved native checkpoint")
        observations[candidate["id"]] = obs
        receipt = read_json(_file(root, candidate["renders"]))
        _fields(receipt, {"schema", "checkpoint_sha256", "views_digest", "images"})
        if (receipt["schema"] != "dcc.quality.renders.v1" or
                receipt["checkpoint_sha256"] != candidate["checkpoint"]["sha256"] or
                receipt["views_digest"] != digest(spec["views"]) or
                not isinstance(receipt["images"], dict) or set(receipt["images"]) != set(view_ids)):
            raise ValueError("Render receipt has different checkpoint or review views")
        for ref in receipt["images"].values():
            _file(root, ref)
        check = evaluate_stage(observations["unchanged"], obs, spec["contract"])
        space = reserved_space(obs, spec["reservations"], list(spec["contract"].get("allowed_object_prefixes", {})))
        results[candidate["id"]] = {"eligible": check["passed"] and space["passed"],
                                    "check": check, "reserved_space": space}
        if spatial:
            visibility = check_visibility(read_json(_file(root, candidate['visibility'])), spec['visibility_contract'], obs)
            results[candidate['id']]['visibility'] = visibility
            results[candidate['id']]['eligible'] &= visibility['passed']
    runtime = {name: file_hash(Path(__file__).with_name(name)) for name in
               ("quality.py", "continuity.py", "continuity_checks.py", "evidence.py",
                "observation_storage.py", "uv_guard.py")}
    if spatial:
        runtime['spatial.py'] = file_hash(Path(__file__).with_name('spatial.py'))
    binding = {"round_sha256": file_hash(round_path), "validator": runtime}
    return {"schema": "dcc.quality.audit.v1", **binding, "evidence_id": digest(binding),
            "targets": targets, "views": view_ids, "candidates": results,
            "passed": all(r["eligible"] for r in results.values()),
            "limits": "Hash bindings and checks over supplied observations/receipts; not proof those producers were truthful. No aesthetic score, native sandbox, dispatch fencing or artist acceptance."}


def select(round_path, review):
    """Revalidate all evidence; failed candidates stay recorded but cannot win."""
    report = audit(round_path)
    _fields(review, {"schema", "evidence_id", "critic", "verifier", "selected", "reasons"})
    if review["schema"] != "dcc.quality.review.v1" or review["evidence_id"] != report["evidence_id"]:
        raise ValueError("Review is stale or uses another evidence bundle/validator")
    _fields(review["critic"], {"author", "findings"})
    _fields(review["verifier"], {"author", "assessments", "unresolved_blockers"})
    for role in ("critic", "verifier"):
        _text(review[role]["author"])
    if not isinstance(review["critic"]["findings"], list) or not review["critic"]["findings"]:
        raise ValueError("Critic must identify a concrete issue and bounded remedy")
    for finding in review["critic"]["findings"]:
        _fields(finding, {"candidate", "target", "view", "problem", "remedy"})
        if finding["candidate"] not in report["candidates"] or finding["target"] not in report["targets"] or finding["view"] not in report["views"]:
            raise ValueError("Critique refers to unknown evidence")
        _text(finding["problem"]); _text(finding["remedy"])
    assessments = review["verifier"]["assessments"]
    if not isinstance(assessments, dict) or set(assessments) != set(report["candidates"]):
        raise ValueError("Verifier must compare every candidate including unchanged")
    for candidate, target_map in assessments.items():
        if not isinstance(target_map, dict) or set(target_map) != set(report["targets"]):
            raise ValueError("Verifier must address every visual target")
        for item in target_map.values():
            _fields(item, {"result", "view", "evidence"})
            if item["result"] not in ("improved", "unchanged", "worse", "uncertain") or item["view"] not in report["views"]:
                raise ValueError("Unsupported visual assessment")
            _text(item["evidence"])
    selected = review["selected"]
    if selected not in report["candidates"] or not report["candidates"][selected]["eligible"]:
        raise ValueError("Selected candidate failed a deterministic gate")
    if review["verifier"]["unresolved_blockers"] != []:
        raise ValueError("Resolve blockers before selecting")
    if not isinstance(review["reasons"], dict) or set(review["reasons"]) != set(report["candidates"]):
        raise ValueError("Explain the selected and rejected candidates")
    for reason in review["reasons"].values():
        _text(reason)
    return {"schema": "dcc.quality.selection.v1", "evidence_id": report["evidence_id"],
            "selected": selected, "review": review, "audit": report,
            "review_independence": "same_author" if review["critic"]["author"] == review["verifier"]["author"] else "different_authors_declared_not_authenticated",
            "artist_acceptance": "not_requested", "native_adoption": "not_performed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "select"):
        p = sub.add_parser(command)
        p.add_argument("round")
        if command == "select":
            p.add_argument("review")
        p.add_argument("--out", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("observation"); p.add_argument("reservations"); p.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = reserved_space(read_json(args.observation), read_json(args.reservations))
    elif args.command == "audit":
        result = audit(args.round)
    else:
        result = select(args.round, read_json(args.review))
    write_json(args.out, result)
    print(f"{result['schema']}: {args.out}")
    if result.get("passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
