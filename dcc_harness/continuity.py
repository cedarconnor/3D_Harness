"""Portable, advisory continuity over Project's single-writer journal.

Bundles are immutable and their manifest is written last. A partial bundle is
an inspection/reconciliation stop, not permission to replay a native action.
This is not a scheduler, native-save transaction, lock, or MCP interceptor.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

from .evidence import canonical, digest, file_hash, read_json, validate_observation
from .project import Project, now


LIMITS = (
    "Advisory single writer; no concurrency control, native-save atomicity, "
    "exactly-once execution, or prevention of direct MCP writes. Reports are "
    "retained claims tied to observations, not independent native or artistic "
    "validation. External image files and unmeasured native state are not "
    "archived or certified. Partial publication requires manual inspection and "
    "reconciliation; there is no automatic replay or repair."
)


def _plain(path):
    """Reject redirecting files/directories before resolving a retained path."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and
                getattr(part.stat(), "st_file_attributes", 0) & 0x400):
            raise ValueError(f"Links/reparse points are not supported: {part}")
    return path


def _mapping_keys(value, label):
    if not isinstance(value, dict) or any(not isinstance(k, str) or not k for k in value):
        raise ValueError(f"{label} must be an object with nonempty string keys")
    return value


def _mapping(value, label):
    _mapping_keys(value, label)
    canonical(value)
    return value


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _write(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _load_observation(path, checkpoint):
    return _load_observation_and_registry(path, checkpoint)[0]


def _load_observation_and_registry(path, checkpoint):
    """Validate each read in full, deriving its registry once; no retained cache."""
    obs = read_json(path)
    _mapping_keys(obs, "Observation")
    # Digest validation already serializes every measured field, rejecting
    # nonfinite values. Metadata outside that digest still needs the same check.
    validate_observation(obs)
    canonical({k: v for k, v in obs.items()
               if k not in ("objects", "materials", "scene", "coverage", "issues")})
    if not _sha(obs.get("checkpoint_sha256")) or obs["checkpoint_sha256"] != file_hash(checkpoint):
        raise ValueError("Observation checkpoint_sha256 does not match the saved checkpoint")
    for key in ("objects", "materials", "scene", "coverage"):
        _mapping_keys(obs[key], key)
    coverage = obs["coverage"]
    if (not obs["objects"] or obs["issues"] != [] or
            not isinstance(coverage.get("measured"), list) or not coverage["measured"] or
            not isinstance(coverage.get("not_measured"), list) or
            any(not isinstance(s, str) or not s for s in coverage["measured"] + coverage["not_measured"])):
        raise ValueError("Observation must have objects, declared coverage, and no issues")
    # Deriving the registry also checks measured references and container shapes.
    return obs, _registry(obs)


def _registry(obs):
    """Derive from a digest-validated observation, retaining local shape checks."""
    assets, materials, instances, parents, images = {}, {}, {}, {}, {}
    for mid, material in obs["materials"].items():
        _mapping_keys(material, f"Material {mid}")
        materials[mid] = {"users": [], "asset_ids": []}
    for iid, obj in obs["objects"].items():
        _mapping_keys(obj, f"Object {iid}")
        if not isinstance(obj.get("type"), str) or not obj["type"]:
            raise ValueError(f"Object {iid} is missing its type")
        aid, parent = obj.get("asset_id"), obj.get("parent")
        mids, collections = obj.get("material_ids"), obj.get("collections", [])
        if ((aid is not None and (not isinstance(aid, str) or not aid)) or
                (obj["type"] == "MESH" and not aid) or
                (parent is not None and parent not in obs["objects"]) or
                not isinstance(mids, list) or any(not isinstance(m, str) or m not in materials for m in mids) or
                not isinstance(collections, list) or any(not isinstance(c, str) for c in collections)):
            raise ValueError(f"Invalid measured identity/dependency on {iid}")
        instances[iid] = {"name": obj.get("name"), "type": obj["type"], "asset_id": aid,
                          "parent": parent, "material_ids": mids, "collections": collections}
        if parent:
            parents.setdefault(parent, []).append(iid)
        if aid:
            asset = assets.setdefault(aid, {"instances": [], "material_ids": []})
            asset["instances"].append(iid)
            asset["material_ids"].extend(mids)
        for mid in set(mids):
            materials[mid]["users"].append(iid)
            if aid:
                materials[mid]["asset_ids"].append(aid)
    for owner, graph in [("material:" + mid, m.get("graph")) for mid, m in obs["materials"].items()] + [("world", obs["scene"].get("world"))]:
        if graph is None:
            continue
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise ValueError(f"Invalid measured graph for {owner}")
        for node in graph["nodes"]:
            if not isinstance(node, dict):
                raise ValueError(f"Invalid measured node for {owner}")
            image = node.get("image")
            if image is not None:
                if not isinstance(image, dict) or image.get("exists") is not True or not _sha(image.get("sha256")):
                    raise ValueError(f"Missing/unhashed measured image for {owner}")
                identity = digest(image)
                images.setdefault(identity, {"image": image, "users": []})["users"].append(owner)
    for records in (assets, materials):
        for record in records.values():
            for key in record:
                record[key] = sorted(set(record[key]))
    for record in images.values():
        record["users"] = sorted(set(record["users"]))
    return {"schema": "dcc.registry.v1", "revision": obs["revision"], "assets": assets,
            "materials": materials, "instances": instances,
            "dependencies": {"parents": {k: sorted(v) for k, v in parents.items()}, "images": images},
            "limits": "Observed active-scene identities and bindings; asset membership does not prove native datablock sharing."}


def _check_report(path, obs):
    report = read_json(path)
    if (not isinstance(report, dict) or report.get("schema") != "dcc.check.v1" or
            report.get("revision") != obs["revision"] or report.get("passed") is not True or
            report.get("failures") != [] or not isinstance(report.get("checked_targets"), list) or
            not report["checked_targets"] or
            any(not isinstance(i, str) or i not in obs["objects"] for i in report["checked_targets"])):
        raise ValueError("Check report must pass, check observed targets, and match the observation revision")
    return report


class Continuity:
    def __init__(self, root):
        self.root = _plain(root)
        self.project = Project(self.root)

    def _journal(self):
        _plain(self.root / "operations.jsonl")
        events, pending, seen = self.project.events(), {}, set()
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"]:
                raise RuntimeError("Invalid journal event; inspect and reconcile")
            op, kind = event["id"], event.get("event")
            if kind == "begin" and op not in seen:
                pending[op] = event
                seen.add(op)
            elif kind in ("observed", "reconciled") and op in pending:
                pending.pop(op)
            else:
                raise RuntimeError("Invalid journal lifecycle; inspect and reconcile")
            role = "script" if kind == "begin" else "evidence"
            if not isinstance(event.get(role), str) or not _sha(event.get("sha256")):
                raise RuntimeError("Invalid journal evidence reference; inspect and reconcile")
        return events, list(pending.values())

    def _bundles(self):
        folder = _plain(self.root / "checkpoints")
        entries = sorted(folder.iterdir()) if folder.exists() else []
        for number, path in enumerate(entries, 1):
            _plain(path)
            if path.name != f"{number:06d}" or not path.is_dir() or not (path / "manifest.json").is_file():
                raise RuntimeError(f"Incomplete/unexpected publication at {path}; inspect and reconcile manually; do not replay")
        return entries

    def status(self):
        """Verify the complete committed chain before returning any active state."""
        metadata = _plain(self.root / "project.json")
        meta = read_json(metadata)
        if not isinstance(meta, dict) or meta.get("schema") != "dcc.project.v1":
            raise ValueError("Invalid Project metadata")
        events, pending = self._journal()
        bundles = self._bundles()
        if not bundles:
            raise RuntimeError("Continuity has no committed checkpoint")
        history, decision_history, decisions, seen = [], [], {}, set()
        parent, journal_count = None, 0
        brief = None
        for number, bundle in enumerate(bundles, 1):
            manifest_path = _plain(bundle / "manifest.json")
            manifest = read_json(manifest_path)
            if (not isinstance(manifest, dict) or manifest.get("schema") != "dcc.continuity.checkpoint.v1" or
                    type(manifest.get("sequence")) is not int or manifest["sequence"] != number or
                    manifest.get("parent") != parent or manifest.get("project_sha256") != file_hash(metadata)):
                raise ValueError(f"Invalid checkpoint manifest/parent chain: {bundle}")
            step = manifest.get("step_id")
            if not isinstance(step, str) or not step or step in seen:
                raise ValueError("Invalid/duplicate committed step ID")
            seen.add(step)
            files = _mapping(manifest.get("files"), "Manifest files")
            required = {"checkpoint.blend", "observation.json", "brief.md", "handoff.md", "decisions.json", "decision_updates.json", "registry.json", "journal.json"}
            if number > 1:
                required.add("check.json")
            if not required <= files.keys() or set(p.name for p in bundle.iterdir()) != files.keys() | {"manifest.json"}:
                raise ValueError("Bundle content differs from committed file inventory")
            for name, sha in files.items():
                if name in (".", "..") or "/" in name or "\\" in name or ":" in name or not _sha(sha):
                    raise ValueError("Invalid bundle-relative path/hash")
                if file_hash(_plain(bundle / name)) != sha:
                    raise ValueError(f"Retained evidence hash changed: {bundle / name}")
            obs, registry = _load_observation_and_registry(bundle / "observation.json", bundle / "checkpoint.blend")
            if manifest.get("observation_revision") != obs["revision"] or manifest.get("checkpoint_sha256") != obs["checkpoint_sha256"]:
                raise ValueError("Manifest observation/native binding differs")
            report = _check_report(bundle / "check.json", obs) if number > 1 else None
            current_brief = (bundle / "brief.md").read_text(encoding="utf-8")
            if brief is not None and brief != current_brief:
                raise ValueError("Project brief changed within checkpoint chain")
            brief = current_brief
            updates = _mapping(read_json(bundle / "decision_updates.json"), "Decision updates")
            decisions.update(updates)
            if read_json(bundle / "decisions.json") != decisions:
                raise ValueError("Cumulative decisions differ from their update history")
            if read_json(bundle / "registry.json") != registry:
                raise ValueError("Registry differs from measured observation")
            count = manifest.get("journal_count")
            if type(count) is not int or not journal_count <= count <= len(events):
                raise ValueError("Invalid retained journal prefix")
            if read_json(bundle / "journal.json") != events[journal_count:count] or manifest.get("journal_sha256") != digest(events[:count]):
                raise ValueError("Accepted operation journal changed")
            sources = manifest.get("journal_sources")
            if not isinstance(sources, list) or len(sources) != count - journal_count:
                raise ValueError("Missing retained journal evidence")
            for index, source in enumerate(sources, journal_count):
                event = events[index]
                expected = f"journal-{index:06d}-" + ("script" if event["event"] == "begin" else "evidence")
                if source != expected or files.get(source) != event["sha256"]:
                    raise ValueError("Retained journal source hash differs from its event")
            journal_count = count
            checkpoint_id = file_hash(manifest_path)
            parent = {"id": checkpoint_id, "step_id": step, "revision": obs["revision"]}
            active = {**parent, "sequence": number, "checkpoint": str(bundle / "checkpoint.blend"),
                      "observation": str(bundle / "observation.json"), "handoff": str(bundle / "handoff.md"),
                      "checkpoint_sha256": obs["checkpoint_sha256"], "created": manifest.get("created")}
            history.append({**active, "check_report": str(bundle / "check.json") if report else None,
                            "report_passed": report["passed"] if report else None})
            decision_history.append({"step_id": step, "id": checkpoint_id, "updates": updates})
        return {"schema": "dcc.continuity.status.v1", "active": active, "brief": brief,
                "decisions": decisions, "decision_history": decision_history, "task_history": history,
                "registry": registry, "pending": pending, "accepted_journal_events": journal_count,
                "unaccepted_journal_events": len(events) - journal_count, "limits": LIMITS,
                "artistic_acceptance": "not_evaluated"}

    verify = status

    def initialize(self, checkpoint, observation, brief, decisions, *, step_id="initial", handoff=None):
        """Initialize from saved native bytes and a matching observation; no quality claim."""
        if not isinstance(brief, str) or not brief.strip():
            raise ValueError("Brief must be nonempty text")
        if self._bundles():
            raise ValueError("Continuity is already initialized")
        if not (self.root / "project.json").exists():
            self.project.init(brief)
        return self._publish(step_id, None, checkpoint, observation, handoff, decisions, None, brief)

    def publish(self, step_id, expected_parent, checkpoint, observation, handoff, decision_updates, check):
        """Accept one step; expected_parent is status()['active']['id'], not a path."""
        return self._publish(step_id, expected_parent, checkpoint, observation, handoff, decision_updates, check)

    def _publish(self, step_id, expected_parent, checkpoint, observation, handoff, updates, check, brief=None):
        if not isinstance(step_id, str) or not step_id.strip():
            raise ValueError("Step ID must be nonempty text")
        updates = _mapping(updates, "Decision updates")
        previous = self.status() if self._bundles() else None
        if previous:
            if expected_parent != previous["active"]["id"]:
                raise ValueError("Stale parent: inspect current continuity state before publishing")
            if step_id in {item["step_id"] for item in previous["task_history"]}:
                raise ValueError("Step ID has already been accepted")
            if handoff is None or check is None:
                raise ValueError("Subsequent checkpoints require a handoff file and passed check report")
        elif expected_parent is not None or brief is None:
            raise ValueError("Initialize continuity before publishing")
        events, pending = self._journal()
        if pending:
            raise RuntimeError("Unresolved Project operation: inspect native state and reconcile; do not replay")
        checkpoint, observation = _plain(checkpoint), _plain(observation)
        if checkpoint.suffix.lower() != ".blend" or not checkpoint.is_file() or not checkpoint.stat().st_size:
            raise ValueError("Checkpoint must be a nonempty saved .blend file")
        sources = {"checkpoint.blend": checkpoint, "observation.json": observation}
        if handoff is not None:
            sources["handoff.md"] = _plain(handoff)
            if not sources["handoff.md"].read_text(encoding="utf-8").strip():
                raise ValueError("Handoff file must contain text")
        if check is not None:
            sources["check.json"] = _plain(check)
        start = previous["accepted_journal_events"] if previous else 0
        journal_sources = []
        for index, event in enumerate(events[start:], start):
            role = "script" if event["event"] == "begin" else "evidence"
            name = f"journal-{index:06d}-{role}"
            path = _plain(event[role])
            if file_hash(path) != event["sha256"]:
                raise ValueError("Journal source/evidence changed since it was recorded")
            sources[name] = path
            journal_sources.append(name)
        hashes = {name: file_hash(path) for name, path in sources.items()}
        obs, registry = _load_observation_and_registry(observation, checkpoint)
        if check is not None:
            _check_report(sources["check.json"], obs)
        decisions = dict(previous["decisions"]) if previous else {}
        decisions.update(updates)
        sequence = previous["active"]["sequence"] + 1 if previous else 1
        data = {"brief.md": (previous["brief"] if previous else brief).encode("utf-8"),
                "decisions.json": _json_bytes(decisions), "decision_updates.json": _json_bytes(updates),
                "registry.json": _json_bytes(registry), "journal.json": _json_bytes(events[start:])}
        if handoff is None:
            data["handoff.md"] = b"Initial saved checkpoint. Inspect the brief, decisions, and measured registry before work.\n"
        bundle = self.root / "checkpoints" / f"{sequence:06d}"
        bundle.mkdir()  # Exclusive reservation; any interruption here is a visible stop.
        for name, source in sources.items():
            with source.open("rb") as incoming, (bundle / name).open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            if file_hash(bundle / name) != hashes[name] or file_hash(source) != hashes[name]:
                raise ValueError("Source changed during publication; inspect partial bundle")
        for name, payload in data.items():
            _write(bundle / name, payload)
        # Revalidate copied evidence, then make the final commit marker. This is
        # deliberately not claimed to transact native Blender or concurrent writers.
        copied = _load_observation(bundle / "observation.json", bundle / "checkpoint.blend")
        if copied != obs:
            raise ValueError("Observation changed during publication")
        if check is not None:
            _check_report(bundle / "check.json", copied)
        for name, source in sources.items():
            if file_hash(source) != hashes[name] or file_hash(bundle / name) != hashes[name]:
                raise ValueError("Source changed during publication; inspect partial bundle")
        for index, name in enumerate(journal_sources, start):
            if hashes[name] != events[index]["sha256"]:
                raise ValueError("Journal source/evidence changed during publication; inspect partial bundle")
        if self._journal() != (events, pending):
            raise RuntimeError("Journal changed during publication; inspect partial bundle")
        parent = {k: previous["active"][k] for k in ("id", "step_id", "revision")} if previous else None
        manifest = {"schema": "dcc.continuity.checkpoint.v1", "sequence": sequence,
                    "step_id": step_id, "created": now(), "parent": parent,
                    "project_sha256": file_hash(self.root / "project.json"),
                    "observation_revision": obs["revision"], "checkpoint_sha256": obs["checkpoint_sha256"],
                    "files": {p.name: file_hash(p) for p in bundle.iterdir()},
                    "journal_count": len(events), "journal_sha256": digest(events),
                    "journal_sources": journal_sources}
        _write(bundle / "manifest.json", _json_bytes(manifest))
        return self.status()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "verify"))
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(Continuity(args.root).status(), indent=2, sort_keys=True))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"Continuity verification failed: {exc}\n")


if __name__ == "__main__":
    main()
