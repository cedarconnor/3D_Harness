"""Fresh-process fixture setup/continuation and regression check for unused materials."""
import argparse
from pathlib import Path
import shutil
import sys
import bpy

p=argparse.ArgumentParser(); p.add_argument("--repo",required=True); p.add_argument("--root",required=True)
p.add_argument("--stage",choices=["setup","palette","continue"],required=True); p.add_argument("--assets")
a=p.parse_args(sys.argv[sys.argv.index("--")+1:]); sys.path.insert(0,a.repo)
from dcc_harness.project import Project
from dcc_harness.evidence import read_json,write_json,evaluate
from dcc_harness.blender import observe
from examples.courtyard import run_step

root=Path(a.root)
if a.stage=="setup":
    if root.exists(): raise ValueError("Use a new isolated test directory")
    Project(root).init("Fresh process continuation regression, not a creative trial")
    shutil.copytree(a.assets,root/"assets",dirs_exist_ok=True)
    print(run_step(root,"00-start"))
else:
    expected={"plaster","stone","teal-paint","wood","bronze","terracotta","foliage","soil","grout"}
    actual={m.get("dcc_material_id") for m in bpy.data.materials}
    missing=expected-actual
    print("PALETTE_MISSING",sorted(missing))
    if missing: raise RuntimeError("Starter lost unused material palette on reopen")
    if a.stage=="continue":
        run_step(root,"01-architecture"); run_step(root,"02-furnishings")
        result=evaluate(observe(),read_json(Path(a.repo)/"examples/courtyard-spec.json"))
        write_json(root/"reports/resume-check.json",result)
        if not result["passed"]: raise RuntimeError(result["failures"])
        print("RESUME_PASS",result["asset_definitions"])
