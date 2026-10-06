"""Run the small saved-file quality fixture with journaled, bounded native steps."""
import argparse
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
from dcc_harness.evidence import file_hash, write_json
from dcc_harness.project import Project

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root")
parser.add_argument("--blender", required=True)
args = parser.parse_args()
root = Path(args.root).resolve()
subprocess.run([sys.executable, str(repo / "scripts/prepare_quality_courtyard.py"), str(root)], check=True)
project = Project(root)
project.init("Bounded layout study; design.json is frozen before native candidate authoring.")
script = repo / "scripts/quality_courtyard_native.py"
calls = [("build", None, root / "build-result.json")]
calls += [("review", c, root / c / "renders.json") for c in ("unchanged", "workshop", "garden_workshop")]
calls += [("conflict", None, root / "conflict-regression.json")]
receipts = []
for mode, candidate, evidence in calls:
    label = mode + ("-" + candidate if candidate else "")
    operation = project.begin(label, script)
    command = [args.blender, "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(script),
               "--", mode, "--repo", str(repo), "--root", str(root)]
    if candidate:
        command += ["--candidate", candidate]
    with (root / (label + ".log")).open("x", encoding="utf-8") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    receipt = {"command": command, "exit_code": result.returncode, "operation": operation,
               "script_sha256": file_hash(script), "evidence": str(evidence)}
    write_json(root / (label + "-process.json"), receipt)
    if result.returncode:
        raise RuntimeError(f"{label} failed; retained pending operation {operation}, inspect without replay")
    project.finish(operation, evidence)
    receipts.append(receipt)
    print("Finished", label, flush=True)
subprocess.run([sys.executable, str(repo / "scripts/assemble_quality_round.py"), str(root),
                "unchanged", "workshop", "garden_workshop"], check=True)
write_json(root / "processes.json", {"calls": receipts, "pending": project.status()["pending"]})
