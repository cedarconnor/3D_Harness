"""Prove a blocked reservation stops the fixture before native authoring."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.project import Project

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("source_round"); p.add_argument("out"); p.add_argument("--blender", required=True)
a = p.parse_args()
source, out = Path(a.source_round).resolve(), Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
(out / "unchanged").mkdir()
shutil.copyfile(source / "unchanged/scene.blend", out / "unchanged/scene.blend")
design = read_json(source / "design.json")
design["reservations"] = [{"id": "deliberately_occupied", "bounds": [[6, -6.5, .1], [10, -4, 2]],
                           "obstacle_prefixes": ["ext.table."], "exempt_ids": [], "tolerance": .00001}]
write_json(out / "design.json", design)
project = Project(out); project.init("Expected failure fixture: reject occupied volume before authoring")
script = repo / "scripts/quality_courtyard_native.py"
op = project.begin("expected-preflight-rejection", script)
source_hash = file_hash(out / "unchanged/scene.blend")
command = [a.blender, "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(script),
           "--", "build", "--repo", str(repo), "--root", str(out)]
with (out / "process.log").open("x", encoding="utf-8") as stream:
    process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
check = read_json(out / "preflight.json")
assert process.returncode == 1, process.returncode
assert check["passed"] is False and check["findings"]
assert not (out / "workshop").exists() and not (out / "garden_workshop").exists()
assert file_hash(out / "unchanged/scene.blend") == source_hash
project.finish(op, out / "preflight.json")
write_json(out / "qualification.json", {"passed": True, "expected_exit_code": 1, "actual_exit_code": process.returncode,
           "preflight_sha256": file_hash(out / "preflight.json"), "candidate_directories_created": False,
           "source_unchanged": True, "pending": project.status()["pending"]})
print("Blocked preflight qualified")
