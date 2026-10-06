"""Frozen file packets for four continuity workflows, with four fresh sessions each.

Coordinator use only. This module makes no model calls or native writes. Agent
isolation is procedural on a shared host; accepting bytes is not a native grade.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import secrets

from .blind import (_absolute, _check_hashes, _copy_file, _copy_tree, _digest,
                    _inventory, _read_json, _read_template, _reject_link,
                    _write_json, _write_text, POLICY)
from .continuity import Continuity, _load_observation
from .evidence import canonical, validate_observation
from .project import Project


SCHEMA = "dcc.continuity-trial.v1"
RUN_ID = re.compile(r"t-[0-9a-f]{12}\Z")
HELPER_FILES = ("__init__.py", "evidence.py", "project.py", "blender.py",
                "uv_guard.py", "continuity.py", "continuity_blender.py",
                "continuity_checks.py")
STAGES = (1, 2, 3, 4)


def _stage(stage):
    if type(stage) is not int or stage not in STAGES:
        raise ValueError("stage must be an integer from 1 through 4")
    return f"s{stage:02d}"


def _bound_observation(path, checkpoint):
    obs = _read_json(path)
    canonical(obs)
    validate_observation(obs)
    if obs.get("checkpoint_sha256") != _digest(checkpoint):
        raise ValueError("Observation checkpoint_sha256 does not match native checkpoint")
    return obs


def _native(path):
    _reject_link(path)
    if not path.is_file() or path.suffix.lower() != ".blend" or not path.stat().st_size:
        raise ValueError("checkpoint must be a nonempty .blend file")


def _run(root, run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid opaque run ID")
    manifest = _read_json(root / "private" / "manifest.json")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported continuity trial schema")
    matches = [run for run in manifest.get("runs", []) if run.get("run_id") == run_id]
    if len(matches) != 1:
        raise ValueError("Unknown or duplicate run ID")
    _check_hashes(root / "private" / "frozen", manifest["frozen_hashes"])
    return manifest, matches[0]


def _accepted(root, run_id, stage):
    name = _stage(stage)
    receipt = _read_json(root / "private" / "results" / run_id / f"{name}.json")
    path = root / "private" / "accepted" / run_id / name
    _check_hashes(path, receipt["result_hashes"])
    return path, receipt


def prepare_round(root, starter, observation, templates, helper_root, seed=None):
    """Freeze shared inputs and return the PRIVATE randomized assignment manifest.

    templates contains common/BRIEF.md, common/DECISIONS.json, METHOD-H.md,
    stage-01..04.md and contract-01..04.json. No session is issued implicitly.
    """
    root, starter, observation, templates, helper_root = map(
        _absolute, (root, starter, observation, templates, helper_root))
    if root.exists():
        raise FileExistsError(f"Round destination already exists: {root}")
    for source in (starter, observation, templates, helper_root):
        if root.is_relative_to(source) or source.is_relative_to(root):
            raise ValueError("Round destination and inputs must not overlap")
    _native(starter)
    _bound_observation(observation, starter)
    # Both methods start from the same observation; ensure it can initialize the
    # continuity method before reserving any round or packet directory.
    _load_observation(observation, starter)
    _read_template(templates / "common" / "BRIEF.md")
    decisions = _read_json(templates / "common" / "DECISIONS.json")
    canonical(decisions)
    if any(not key for key in decisions):
        raise ValueError("Initial decision keys must be nonempty")
    _inventory(templates / "common")
    _read_template(templates / "METHOD-H.md")
    for stage in STAGES:
        _read_template(templates / f"stage-{stage:02d}.md")
        canonical(_read_json(templates / f"contract-{stage:02d}.json"))
    for name in HELPER_FILES:
        _reject_link(helper_root / name)
        if not (helper_root / name).is_file():
            raise ValueError(f"Missing runtime helper file: {name}")
    root.mkdir(parents=True, exist_ok=False)
    frozen = root / "private" / "frozen"
    _copy_file(starter, frozen / "starter.blend")
    _copy_file(observation, frozen / "observation.json")
    _copy_tree(templates / "common", frozen / "common")
    for name in HELPER_FILES:
        _copy_file(helper_root / name, frozen / "helper" / "dcc_harness" / name)
    for name in ("METHOD-H.md", *(f"stage-{s:02d}.md" for s in STAGES),
                 *(f"contract-{s:02d}.json" for s in STAGES)):
        _copy_file(templates / name, frozen / name)
    _bound_observation(frozen / "observation.json", frozen / "starter.blend")
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    runs = []
    for block in (1, 2):
        conditions = list("AH")
        rng.shuffle(conditions)
        for condition in conditions:
            runs.append({"run_id": "t-" + secrets.token_hex(6), "condition": condition,
                         "block": block, "order": len(runs) + 1})
    manifest = {"schema": SCHEMA, "seed": seed, "stages": list(STAGES), "runs": runs,
                "isolation": "procedural; shared filesystem and ambient tool/skill catalog",
                "frozen_hashes": _inventory(frozen)}
    _write_json(root / "private" / "manifest.json", manifest)
    return manifest


def issue_stage(root, run_id, stage, checkpoint=None, observation=None,
                event=None, pending_script=None, event_contract=None):
    """Publish exactly one fresh packet after accepting the preceding stage.

    Native injections are allowed only at stages 3/4, require an explicit bound
    observation and EVENT.md, and retain the previous accepted hash privately.
    Later stages use a supplied observation or the prior accepted observation.
    """
    root, name = _absolute(root), _stage(stage)
    manifest, run = _run(root, run_id)
    packet = root / "packets" / run_id / name
    receipt_path = root / "private" / "issued" / run_id / f"{name}.json"
    if packet.exists() or receipt_path.exists():
        raise FileExistsError("Stage already issued or partial publication needs reconciliation")
    if stage < 3 and (checkpoint is not None or event is not None):
        raise ValueError("Native injections/events are allowed only at stages 3 and 4")
    if pending_script is not None and stage != 4:
        raise ValueError("Pending operation injection is allowed only at stage 4")
    if checkpoint is not None and (observation is None or event is None):
        raise ValueError("Injected checkpoint requires its observation and event note")
    if pending_script is not None and event is None:
        raise ValueError("Pending operation requires an event note")
    if event_contract is not None and event is None:
        raise ValueError("Event contract requires an event note")
    frozen = root / "private" / "frozen"
    previous, previous_receipt = (None, None) if stage == 1 else _accepted(root, run_id, stage - 1)
    native = frozen / "starter.blend" if stage == 1 else previous / "scene.blend"
    native = _absolute(checkpoint) if checkpoint is not None else native
    obs = (frozen / "observation.json" if stage == 1 else previous / "observation.json")
    if observation is not None:
        obs = _absolute(observation)
        if stage == 1 and _digest(obs) != _digest(frozen / "observation.json"):
            raise ValueError("Stage 1 observation must be the frozen initial observation")
    _native(native)
    _bound_observation(obs, native)
    event = _absolute(event) if event is not None else None
    pending_script = _absolute(pending_script) if pending_script is not None else None
    event_contract = _absolute(event_contract) if event_contract is not None else None
    for source in (event, pending_script):
        if source is not None:
            _read_template(source)
    if event_contract is not None:
        canonical(_read_json(event_contract))
    packet.mkdir(parents=True, exist_ok=False)
    _copy_file(native, packet / "start.blend")
    _copy_file(obs, packet / "input-observation.json")
    _copy_tree(frozen / "common", packet / "common")
    _copy_file(frozen / f"stage-{stage:02d}.md", packet / "REQUEST.md")
    _copy_file(frozen / f"contract-{stage:02d}.json", packet / "CONTRACT.json")
    if previous is None:
        _write_text(packet / "CONTINUE.md", "Initial saved environment. Inspect start.blend and the shared brief before beginning.\n")
    else:
        _copy_file(previous / "CONTINUE.md", packet / "CONTINUE.md")
    if event is not None:
        _copy_file(event, packet / "EVENT.md")
    if pending_script is not None:
        _copy_file(pending_script, packet / "PENDING_OPERATION.py")
    if event_contract is not None:
        _copy_file(event_contract, packet / "EVENT_CONTRACT.json")
    pending_id, pending_error = None, None
    if run["condition"] == "H":
        _copy_tree(frozen / "helper", packet / "helper")
        _copy_file(frozen / "METHOD-H.md", packet / "CONTINUITY.md")
        if previous is None:
            Continuity(packet / "state").initialize(
                packet / "start.blend", packet / "input-observation.json",
                _read_template(packet / "common" / "BRIEF.md"),
                _read_json(packet / "common" / "DECISIONS.json"))
        elif (previous / "state").is_dir():
            _copy_tree(previous / "state", packet / "state")
        else:
            _write_text(packet / "STATE_UNAVAILABLE.md", "The previous handoff did not supply continuity state. Preserve this failure in your handoff; do not invent a history.\n")
        if pending_script is not None:
            try:
                pending_id = Project(packet / "state").begin(
                    "delivery-plaque-unknown", packet / "PENDING_OPERATION.py")
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
                pending_error = str(exc)
            _write_json(packet / "PENDING_OPERATION.json", {
                "operation_id": pending_id, "outcome": "unknown",
                "journal_injection_recorded": pending_id is not None,
                "instruction": "Inspect native state and EVENT.md; do not blindly replay the script."})
        method = ("Read CONTINUITY.md and use the supplied helper package. Set sys.dont_write_bytecode = True before importing it. "
                  "Copy frozen state/ into output/state/ before any journal, reconciliation or publication. Never modify input state/. "
                  "Historical paths in the journal and handoff are provenance, not permission to read previous packets. "
                  "The current packet's PENDING_OPERATION.py, when present, is available for reconciliation.\n")
    else:
        method = "Use the shared brief, saved scene, handoff and existing Blender tools. No additional process helper or persistent state package is supplied.\n"
    _write_text(packet / "METHOD.md", POLICY + "\n" + method + (
        "\nYou are a fresh continuation agent. Read common/, REQUEST.md, CONTRACT.json, CONTINUE.md and EVENT.md/EVENT_CONTRACT.json when present. "
        "Open this packet's start.blend. Do not retrieve previous agents' chats, scripts or logs. "
        "Publish output/scene.blend with packed dependencies, output/CONTINUE.md, and output/USAGE.json. "
        "Record actual elapsed time, still captures and rendering time; use null for unavailable token/cost data. "
        "Keep failed attempts and diagnostics in output/. Stop after this stage; a fresh agent receives the next request.\n"))
    (packet / "output").mkdir()
    _check_hashes(frozen, manifest["frozen_hashes"])
    if previous is not None:
        _check_hashes(previous, previous_receipt["result_hashes"])
    _bound_observation(packet / "input-observation.json", packet / "start.blend")
    _write_json(receipt_path, {"run_id": run_id, "stage": stage,
                "previous_accepted_sha256": _digest(previous / "scene.blend") if previous else None,
                "input_sha256": _digest(packet / "start.blend"),
                "injected_checkpoint": checkpoint is not None,
                "pending_operation_id": pending_id, "pending_injection_error": pending_error,
                "packet_hashes": _inventory(packet, output=True)})
    verify_packet(root, run_id, stage)
    return packet


def verify_packet(root, run_id, stage):
    root, name = _absolute(root), _stage(stage)
    _run(root, run_id)
    receipt = _read_json(root / "private" / "issued" / run_id / f"{name}.json")
    packet = root / "packets" / run_id / name
    if stage > 1:
        previous, _ = _accepted(root, run_id, stage - 1)
        if receipt["previous_accepted_sha256"] != _digest(previous / "scene.blend"):
            raise ValueError("Previous accepted native provenance changed")
    _check_hashes(packet, receipt["packet_hashes"], output=True)
    return {"verified": True, "run_id": run_id, "stage": stage,
            "packet": str(packet), "files": len(receipt["packet_hashes"])}


def accept_stage(root, run_id, stage, observation=None):
    """Freeze required results, retaining invalid/missing continuity as a failure.

    Passing a separately observed saved-file observation is preferred. Otherwise
    output/observation.json is retained when supplied. Neither implies a native
    or artistic grade. Missing required native/handoff/usage refuses acceptance.
    """
    root, name = _absolute(root), _stage(stage)
    _, run = _run(root, run_id)
    verify_packet(root, run_id, stage)
    accepted = root / "private" / "accepted" / run_id / name
    receipt_path = root / "private" / "results" / run_id / f"{name}.json"
    if accepted.exists() or receipt_path.exists():
        raise FileExistsError("Stage already accepted or partial publication needs reconciliation")
    output = root / "packets" / run_id / name / "output"
    _native(output / "scene.blend")
    _read_template(output / "CONTINUE.md")
    canonical(_read_json(output / "USAGE.json"))
    obs = _absolute(observation) if observation is not None else output / "observation.json"
    if obs.exists() or observation is not None:
        _bound_observation(obs, output / "scene.blend")
    else:
        obs = None
    # Preflight state without discarding invalid states, native failures, or logs.
    state = output / "state"
    state_present = run["condition"] == "H" and state.exists()
    if state_present:
        _reject_link(state)
        if state.is_dir():
            _inventory(state)
    accepted.mkdir(parents=True, exist_ok=False)
    for filename in ("scene.blend", "CONTINUE.md", "USAGE.json"):
        _copy_file(output / filename, accepted / filename)
    if obs is not None:
        _copy_file(obs, accepted / "observation.json")
        _bound_observation(accepted / "observation.json", accepted / "scene.blend")
    continuity_valid, continuity_error, active_id = None, None, None
    if run["condition"] == "H":
        if state_present:
            if state.is_dir():
                _copy_tree(state, accepted / "state")
            else:
                _copy_file(state, accepted / "state")
        try:
            status = Continuity(accepted / "state").status()
            active_id = status["active"]["id"]
            incoming = root / "packets" / run_id / name / "state"
            if not incoming.is_dir():
                raise ValueError("No frozen continuity history was supplied; a new history cannot replace it")
            if _digest(incoming / "project.json") != _digest(accepted / "state" / "project.json"):
                raise ValueError("Continuity project identity replaced the supplied history")
            for relative, checksum in _inventory(incoming / "checkpoints").items():
                if _digest(accepted / "state" / "checkpoints" / relative) != checksum:
                    raise ValueError("Continuity replaced a supplied committed checkpoint")
            old_events = Project(incoming).events()
            if Project(accepted / "state").events()[:len(old_events)] != old_events:
                raise ValueError("Continuity replaced the supplied journal history")
            if status["active"]["checkpoint_sha256"] != _digest(accepted / "scene.blend"):
                raise ValueError("Continuity active checkpoint does not match output scene")
            if status["pending"] or status["unaccepted_journal_events"]:
                raise ValueError("Continuity contains unreconciled or unaccepted operations")
            continuity_valid = True
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            continuity_valid, continuity_error = False, str(exc)
    verify_packet(root, run_id, stage)
    _write_json(receipt_path, {"run_id": run_id, "stage": stage,
                "result_hashes": _inventory(accepted), "continuity_valid": continuity_valid,
                "continuity_error": continuity_error, "continuity_active_id": active_id,
                "observation_source": "independent_supplied" if observation is not None else "agent_output" if obs else "not_supplied",
                "acceptance": "bytes only; independent native and artistic evaluation required"})
    return accepted


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    for field in ("root", "starter", "observation", "templates", "helper-root"):
        prepare.add_argument("--" + field, type=Path, required=True)
    prepare.add_argument("--seed", type=int)
    for name in ("issue", "verify", "accept"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--run-id", required=True)
        command.add_argument("--stage", type=int, choices=STAGES, required=True)
        if name != "verify":
            command.add_argument("--observation", type=Path)
        if name == "issue":
            for field in ("checkpoint", "event", "pending-script", "event-contract"):
                command.add_argument("--" + field, type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "prepare":
            manifest = prepare_round(**args)
            result = {"prepared": True, "run_ids": [r["run_id"] for r in manifest["runs"]]}
        elif command == "verify":
            result = verify_packet(**args)
        elif command == "issue":
            result = {"issued": True, "packet": str(issue_stage(**args))}
        else:
            result = {"accepted": True, "snapshot": str(accept_stage(**args))}
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
