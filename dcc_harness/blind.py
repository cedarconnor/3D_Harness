"""File packets for a six-run comparison; isolation is procedural, not enforced.

Only a coordinator should call this module. Production agents receive one packet
path, never the private manifest. This module neither runs Blender nor scores art.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import secrets
import shutil
import stat
from typing import Any


SCHEMA = "dcc.blind-round.v1"
RUN_ID = re.compile(r"t-[0-9a-f]{12}\Z")
HELPER_FILES = ("__init__.py", "__main__.py", "evidence.py", "blender.py", "project.py")
POLICY = """Work only in this context folder and its included inputs. Do not read
parent directories, other task folders, repository source, previous chats, or
files outside this packet. The host may display a global skill catalog; only
methods explicitly included here are authorized for this task. This restriction
is procedural and does not claim filesystem or tool isolation.

The coordinator must grant exclusive ownership of the Blender writer before you
make native changes. Use execute_blender_code for native writes. Load the assigned
starter or continuation checkpoint, inspect the active Blender filepath, and
confirm it belongs to this task before authoring. Never change another task's
file. Record an uncertain write and inspect its outcome before retrying. Save
versioned checkpoints in output/.
The included inputs are frozen: write new artifacts only under output/.
"""


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _reject_link(path: Path) -> None:
    """Reject symlinks and Windows junction/reparse paths, including ancestors."""
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError(f"Linked/reparse paths are not allowed: {candidate}")


def _absolute(path: str | Path) -> Path:
    result = Path(os.path.abspath(path))
    _reject_link(result)
    return result


def _inventory(root: Path, *, output: bool = False) -> dict[str, str]:
    """Hash files without following links; optionally omit mutable output/."""
    _reject_link(root)
    if not root.is_dir():
        raise ValueError(f"Missing directory: {root}")
    result: dict[str, str] = {}

    def visit(folder: Path) -> None:
        for item in sorted(folder.iterdir()):
            _reject_link(item)
            relative = item.relative_to(root)
            if output and relative.parts[0] == "output":
                if not item.is_dir():
                    raise ValueError(f"output must be a directory: {item}")
                continue
            if item.is_dir():
                visit(item)
            elif item.is_file():
                result[relative.as_posix()] = _digest(item)
            else:
                raise ValueError(f"Unsupported filesystem entry: {item}")

    visit(root)
    return result


def _copy_file(source: Path, destination: Path, expected: str | None = None) -> None:
    _reject_link(source)
    _reject_link(destination)
    if not source.is_file():
        raise ValueError(f"Missing file: {source}")
    expected = expected or _digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as original, destination.open("xb") as copied:
        shutil.copyfileobj(original, copied)
    if _digest(destination) != expected or _digest(source) != expected:
        raise ValueError(f"Input changed during copy: {source}")


def _copy_tree(source: Path, destination: Path) -> dict[str, str]:
    inventory = _inventory(source)
    destination.mkdir(parents=True, exist_ok=False)
    for relative, checksum in inventory.items():
        _copy_file(source / relative, destination / relative, checksum)
    if _inventory(source) != inventory:
        raise ValueError(f"Input directory changed during copy: {source}")
    return inventory


def _write_text(path: Path, value: str) -> None:
    _reject_link(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    _reject_link(path)
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read coordinator record: {path}") from exc
    if not isinstance(result, dict):
        raise ValueError(f"Invalid coordinator record: {path}")
    return result


def _check_hashes(root: Path, expected: dict[str, str], *, output: bool = False) -> None:
    actual = _inventory(root, output=output)
    if actual != expected:
        changed = sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))
        raise ValueError(f"Frozen files changed in {root}: {', '.join(changed[:8])}")


def _read_template(path: Path) -> str:
    _reject_link(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Missing or invalid UTF-8 template: {path}") from exc
    if not text.strip():
        raise ValueError(f"Empty template: {path}")
    return text


def _method_text(condition: str, measured: str) -> str:
    if condition == "A":
        return "Use the ordinary brief and existing Blender tools. No additional process skills or measurement package are supplied.\n"
    text = "Read and use the three included skills under skills/.\n"
    if condition == "C":
        text += (
            "Read measured.txt. The native helper package is supplied under helper/dcc_harness/. "
            "Set sys.dont_write_bytecode = True before importing it so the frozen inputs "
            "remain unchanged.\n\n" + measured + "\n"
        )
    return text


def prepare_round(
    root: str | Path,
    starter: str | Path,
    kit: str | Path,
    templates: str | Path,
    helper_root: str | Path,
    seed: int | None = None,
) -> dict[str, Any]:
    """Create a new round. Return its PRIVATE assignment manifest.

    templates/ contains common/, skills/<three names>/SKILL.md, build.txt,
    revision.txt, measured.txt. helper_root is the dcc_harness package directory;
    only HELPER_FILES are copied, excluding experiment/coordinator source.
    Existing destinations are refused, including incomplete prior publications.
    """
    root, starter, kit, templates, helper_root = map(_absolute, (root, starter, kit, templates, helper_root))
    if root.exists():
        raise FileExistsError(f"Round destination already exists: {root}")
    if not starter.is_file() or starter.suffix.lower() != ".blend":
        raise ValueError("starter must be an existing .blend file")
    if not (helper_root / "__init__.py").is_file():
        raise ValueError("helper_root must be a Python package directory")
    for source in (kit, templates, helper_root):
        if root.is_relative_to(source) or source.is_relative_to(root):
            raise ValueError("Round destination and input directories must not overlap")
    common = _inventory(templates / "common")
    skills = _inventory(templates / "skills")
    skill_names = {Path(name).parts[0] for name in skills}
    if len(skill_names) != 3 or any(f"{name}/SKILL.md" not in skills for name in skill_names):
        raise ValueError("templates/skills must contain exactly three skill directories with SKILL.md")
    if not common:
        raise ValueError("templates/common must contain the frozen task inputs")
    for name in ("build.txt", "revision.txt", "measured.txt"):
        _read_template(templates / name)
    # Preflight all sources before creating any published destination.
    _inventory(kit)
    for name in HELPER_FILES:
        _reject_link(helper_root / name)
        if not (helper_root / name).is_file():
            raise ValueError(f"Missing runtime helper file: {name}")
    starter_hash = _digest(starter)
    root.mkdir(parents=True, exist_ok=False)
    private = root / "private"
    frozen = private / "frozen"
    frozen.mkdir(parents=True)
    _copy_file(starter, frozen / "starter.blend", starter_hash)
    _copy_tree(kit, frozen / "assets")
    _copy_tree(templates / "common", frozen / "common")
    _copy_tree(templates / "skills", frozen / "skills")
    for name in HELPER_FILES:
        _copy_file(helper_root / name, frozen / "helper" / "dcc_harness" / name)
    for name in ("build.txt", "revision.txt", "measured.txt"):
        _copy_file(templates / name, frozen / name)
    build_text = _read_template(frozen / "build.txt")
    measured = _read_template(frozen / "measured.txt")
    frozen_hashes = _inventory(frozen)
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    runs: list[dict[str, Any]] = []
    for block in (1, 2):
        conditions = list("ABC")
        rng.shuffle(conditions)
        for condition in conditions:
            run_id = "t-" + secrets.token_hex(6)
            packet = root / "trials" / run_id
            packet.mkdir(parents=True, exist_ok=False)
            _copy_file(frozen / "starter.blend", packet / "starter.blend")
            for name in ("common", "assets"):
                _copy_tree(frozen / name, packet / name)
            if condition in {"B", "C"}:
                _copy_tree(frozen / "skills", packet / "skills")
            if condition == "C":
                _copy_tree(frozen / "helper", packet / "helper")
                _copy_file(frozen / "measured.txt", packet / "measured.txt")
            prompt = (
                POLICY + "\n" + _method_text(condition, measured) + "\n" + build_text
                + "\n\nLoad this packet's starter.blend before authoring. The build work cap is "
                "75 minutes, reserving 15 further minutes for the fresh-context revision. "
                "At the build boundary, publish output/pre.blend with packed dependencies "
                "and output/CONTINUE.md. The continuation must describe only this task's saved "
                "state, open issues, and required file-based continuation information. Do not "
                "include chat transcripts. Stop after the handoff; a fresh context performs "
                "the revision.\n"
            )
            _write_text(packet / "PROMPT.md", prompt)
            (packet / "output").mkdir()
            runs.append({
                "run_id": run_id, "condition": condition, "block": block,
                "order": len(runs) + 1,
                "build_hashes": _inventory(packet, output=True),
            })
    _check_hashes(frozen, frozen_hashes)
    manifest = {
        "schema": SCHEMA,
        "seed": seed,
        "isolation": "procedural; shared filesystem and global skill catalog remain accessible",
        "frozen_hashes": frozen_hashes,
        "runs": runs,
    }
    _write_json(private / "manifest.json", manifest)
    return manifest


def _run(root: Path, run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid opaque run ID")
    manifest = _read_json(root / "private" / "manifest.json")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported round schema")
    matches = [run for run in manifest.get("runs", []) if run.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("Unknown or duplicate run ID")
    return manifest, matches[0]


def verify_packet(root: str | Path, run_id: str, phase: str = "build") -> dict[str, Any]:
    """Verify frozen packet bytes; mutable output/ is not part of the input seal."""
    root = _absolute(root)
    manifest, run = _run(root, run_id)
    _check_hashes(root / "private" / "frozen", manifest["frozen_hashes"])
    if phase == "build":
        packet = root / "trials" / run_id
        expected = run["build_hashes"]
    elif phase == "revision":
        receipt = _read_json(root / "private" / "revisions" / f"{run_id}.json")
        packet = root / "revisions" / run_id
        expected = receipt["revision_hashes"]
        _check_hashes(root / "private" / "accepted" / run_id, receipt["accepted_hashes"])
    else:
        raise ValueError("phase must be build or revision")
    _check_hashes(packet, expected, output=True)
    return {"verified": True, "run_id": run_id, "phase": phase, "packet": str(packet), "files": len(expected)}


def release_revision(root: str | Path, run_id: str) -> Path:
    """Accept the pre-revision handoff once and publish a fresh-context packet.

    This records bytes, not aesthetic acceptance or Blender validity. The native
    evaluator must separately verify reopenability and packed dependencies.
    """
    root = _absolute(root)
    manifest, run = _run(root, run_id)
    destination = root / "revisions" / run_id
    accepted = root / "private" / "accepted" / run_id
    receipt_path = root / "private" / "revisions" / f"{run_id}.json"
    if destination.exists() or accepted.exists() or receipt_path.exists():
        raise FileExistsError("Revision already released or prior release needs reconciliation")
    verify_packet(root, run_id)
    output = root / "trials" / run_id / "output"
    handoff_hashes: dict[str, str] = {}
    for name in ("pre.blend", "CONTINUE.md"):
        source = output / name
        _reject_link(source)
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing or empty required handoff: {name}")
        handoff_hashes[name] = _digest(source)
    _read_template(output / "CONTINUE.md")
    accepted.mkdir(parents=True, exist_ok=False)
    for name, checksum in handoff_hashes.items():
        _copy_file(output / name, accepted / name, checksum)
    frozen = root / "private" / "frozen"
    destination.mkdir(parents=True, exist_ok=False)
    for name in ("pre.blend", "CONTINUE.md"):
        _copy_file(accepted / name, destination / name, handoff_hashes[name])
    for name in ("common", "assets"):
        _copy_tree(frozen / name, destination / name)
    condition = run["condition"]
    if condition in {"B", "C"}:
        _copy_tree(frozen / "skills", destination / "skills")
    if condition == "C":
        _copy_tree(frozen / "helper", destination / "helper")
        _copy_file(frozen / "measured.txt", destination / "measured.txt")
    _copy_file(frozen / "revision.txt", destination / "REVISION.md")
    measured = _read_template(frozen / "measured.txt")
    _write_text(destination / "PROMPT.md", (
        POLICY + "\n" + _method_text(condition, measured)
        + "\nYou are a fresh continuation agent. Read common/, CONTINUE.md and REVISION.md. "
        "Open pre.blend and apply the revision within the reserved 15-minute cap using "
        "only the saved files in this packet. "
        "Do not retrieve the builder's chat, scripts or logs. Save the revised native scene "
        "with packed dependencies to output/post.blend and your handoff to output/CONTINUE.md.\n"
    ))
    (destination / "output").mkdir()
    # Recheck frozen source bytes and accepted handoff before recording publication.
    _check_hashes(frozen, manifest["frozen_hashes"])
    _check_hashes(accepted, handoff_hashes)
    _write_json(receipt_path, {
        "run_id": run_id,
        "accepted_hashes": handoff_hashes,
        "revision_hashes": _inventory(destination, output=True),
    })
    verify_packet(root, run_id, "revision")
    return destination


def accept_revision(root: str | Path, run_id: str) -> Path:
    """Freeze a revision result once, without claiming native or artistic success."""
    root = _absolute(root)
    verify_packet(root, run_id, "revision")
    accepted = root / "private" / "completed" / run_id
    receipt_path = root / "private" / "results" / f"{run_id}.json"
    if accepted.exists() or receipt_path.exists():
        raise FileExistsError("Result already accepted or prior acceptance needs reconciliation")
    output = root / "revisions" / run_id / "output"
    hashes = {}
    for name in ("post.blend", "CONTINUE.md"):
        source = output / name
        _reject_link(source)
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing or empty required result: {name}")
        hashes[name] = _digest(source)
    _read_template(output / "CONTINUE.md")
    accepted.mkdir(parents=True, exist_ok=False)
    for name, checksum in hashes.items():
        _copy_file(output / name, accepted / name, checksum)
    verify_packet(root, run_id, "revision")
    _check_hashes(accepted, hashes)
    _write_json(receipt_path, {
        "run_id": run_id, "result_hashes": hashes,
        "pre_sha256": _digest(root / "private" / "accepted" / run_id / "pre.blend"),
        "acceptance": "bytes only; independent native and artist evaluation required",
    })
    return accepted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Freeze inputs and prepare six packets")
    for name in ("root", "starter", "kit", "templates", "helper-root"):
        prepare.add_argument(f"--{name}", type=Path, required=True)
    prepare.add_argument("--seed", type=int)
    verify = commands.add_parser("verify", help="Check immutable packet inputs")
    revision = commands.add_parser("release-revision", help="Publish a fresh continuation packet once")
    result = commands.add_parser("accept-revision", help="Freeze the final revision bytes once")
    for command in (verify, revision, result):
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--run-id", required=True)
    verify.add_argument("--phase", choices=("build", "revision"), default="build")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare_round(args.root, args.starter, args.kit, args.templates, args.helper_root, args.seed)
            result = {"prepared": True, "root": str(_absolute(args.root)), "run_ids": [run["run_id"] for run in manifest["runs"]]}
        elif args.command == "verify":
            result = verify_packet(args.root, args.run_id, args.phase)
        elif args.command == "release-revision":
            result = {"released": True, "packet": str(release_revision(args.root, args.run_id))}
        else:
            result = {"accepted": True, "snapshot": str(accept_revision(args.root, args.run_id))}
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
