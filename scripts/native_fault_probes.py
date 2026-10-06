"""Reversible faults on the owned fixture. No source checkpoint is overwritten."""
from pathlib import Path
import bpy
from dcc_harness.blender import observe
from dcc_harness.evidence import compare,evaluate,read_json,write_json
from dcc_harness.project import Project


def run(root, spec_path):
    root=Path(root).resolve()
    if bpy.context.scene.get("dcc_project") != str(root): raise ValueError("Not the owned fixture")
    project=Project(root); op=project.begin("reversible-native-fault-probes",Path(__file__))
    baseline=observe(); checks=[]
    scene=bpy.context.scene
    bench=next(o for o in scene.objects if o.get("dcc_instance_id")=="bench.seat.0")
    duplicate=bench.copy(); duplicate.data=bench.data; scene.collection.objects.link(duplicate)
    try:
        observed=observe()
        checks.append({"fault":"duplicate instance ID","detected":any("Duplicate instance ID" in e for e in observed["issues"])})
    finally: bpy.data.objects.remove(duplicate,do_unlink=True)
    x=bench.location.x
    try:
        bench.location.x += .15
        delta=compare(baseline,observe())
        checks.append({"fault":"unapproved placement change","detected":not delta["passed"],"changes":delta["changes"]})
    finally: bench.location.x=x
    sun=next(o for o in scene.objects if o.get("dcc_instance_id")=="light.sun")
    energy=sun.data.energy
    try:
        sun.data.energy=energy*1.1
        delta=compare(baseline,observe(),{"materials":{"stone":["graph"]}})
        checks.append({"fault":"lighting drift during material revision","detected":not delta["passed"],"changes":delta["changes"]})
    finally: sun.data.energy=energy
    iid=bench["dcc_instance_id"]
    try:
        del bench["dcc_instance_id"]
        report=evaluate(observe(),read_json(spec_path))
        checks.append({"fault":"missing required identity","detected":not report["passed"],"failures":report["failures"]})
    finally: bench["dcc_instance_id"]=iid
    image=next(i for i in bpy.data.images if i.name.startswith("sandstone_blocks_05_diff"))
    filepath=image.filepath
    try:
        image.filepath=str(root/"assets/not-present.png")
        checks.append({"fault":"missing texture dependency","detected":any("Missing image" in e for e in observe()["issues"])})
    finally: image.filepath=filepath
    restored=observe()
    report={"schema":"dcc.native-faults.v1","tests":checks,"restored_revision":restored["revision"],
            "baseline_revision":baseline["revision"],"restored":restored["revision"]==baseline["revision"]}
    report["passed"]=report["restored"] and all(c["detected"] for c in checks)
    evidence=root/"reports/native-fault-probes.json"; write_json(evidence,report)
    project.finish(op,evidence)
    if not report["passed"]: raise RuntimeError("Native fault probes failed")
    return report
