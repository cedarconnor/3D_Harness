"""Single-writer advisory journal. Interrupted writes require explicit reconciliation."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .evidence import read_json, write_json, file_hash


def now():
    return datetime.now(timezone.utc).isoformat()


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def init(self, brief):
        for folder in ("checkpoints", "evidence", "reports", "assets", "logs"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        write_json(self.root / "project.json", {"schema":"dcc.project.v1", "id":str(uuid.uuid4()),
                   "created":now(),"mode":"advisory-single-writer","brief":brief})

    def events(self):
        path = self.root / "operations.jsonl"
        if not path.exists():
            return []
        try:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        except json.JSONDecodeError as exc:
            raise RuntimeError("Journal damaged; reconcile before any further writes") from exc

    def append(self, event):
        with (self.root / "operations.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time":now(), **event}, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def pending(self):
        pending = {}
        for event in self.events():
            if event["event"] == "begin":
                pending[event["id"]] = event
            elif event["event"] in ("observed", "reconciled"):
                pending.pop(event["id"], None)
        return pending

    def begin(self, label, script_path):
        read_json(self.root / "project.json")
        if self.pending():
            raise RuntimeError("Unresolved dispatch: inspect native state; do not replay")
        path = Path(script_path).resolve()
        op = str(uuid.uuid4())
        self.append({"event":"begin","id":op,"label":label,
                     "script":str(path),"sha256":file_hash(path)})
        return op

    def finish(self, op, evidence_path, reconciled=False):
        if op not in self.pending():
            raise ValueError("Operation is not pending")
        path = Path(evidence_path).resolve()
        evidence = read_json(path)
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError("Evidence must be a nonempty JSON object")
        self.append({"event":"reconciled" if reconciled else "observed","id":op,
                     "evidence":str(path),"sha256":file_hash(path)})

    def status(self):
        meta = read_json(self.root / "project.json")
        checkpoints = sorted((self.root / "checkpoints").glob("*.blend"))
        return {"project":meta,"pending":list(self.pending().values()),
                "checkpoints":[str(p) for p in checkpoints],
                "continuation":str(self.root / "CONTINUE.md"),
                "limits":"Advisory; no interception, concurrency control, or automatic replay."}

