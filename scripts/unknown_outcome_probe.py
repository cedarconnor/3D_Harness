"""Simulate missing acknowledgement after a native write; never kill the editor."""
from pathlib import Path
import bpy
from dcc_harness.blender import observe
from dcc_harness.evidence import write_json,read_json
from dcc_harness.project import Project


def dispatch(root):
    root=Path(root).resolve()
    if bpy.context.scene.get("dcc_project")!=str(root): raise ValueError("Wrong scene")
    project=Project(root); baseline=observe()
    op=project.begin("simulate-missing-acknowledgement",Path(__file__))
    obj=bpy.data.objects.new("H_ResponseProbe",None); bpy.context.scene.collection.objects.link(obj)
    obj["dcc_instance_id"]="probe.response-loss"
    evidence={"operation":op,"baseline_revision":baseline["revision"],"native_object_id":"probe.response-loss",
              "simulation":"Native write completed; acknowledgement deliberately not recorded"}
    write_json(root/"reports/unknown-dispatched.json",evidence)
    return evidence


def reconcile_and_clean(root):
    root=Path(root).resolve(); project=Project(root)
    evidence=read_json(root/"reports/unknown-dispatched.json")
    targets=[o for o in bpy.context.scene.objects if o.get("dcc_instance_id")=="probe.response-loss"]
    if len(targets)!=1: raise RuntimeError("Native outcome is ambiguous")
    result={"native_count":len(targets),"pending":evidence["operation"] in project.pending(),
            "replayed":False,"native_revision":observe()["revision"]}
    receipt=root/"reports/unknown-reconciled.json"; write_json(receipt,result)
    project.finish(evidence["operation"],receipt,reconciled=True)
    op=project.begin("remove-owned-response-probe",Path(__file__))
    bpy.data.objects.remove(targets[0],do_unlink=True)
    result["restored"]=observe()["revision"]==evidence["baseline_revision"]
    result["passed"]=result["pending"] and result["restored"] and result["native_count"]==1
    receipt=root/"reports/unknown-cleaned.json"; write_json(receipt,result); project.finish(op,receipt)
    if not result["passed"]: raise RuntimeError("Native restoration failed")
    return result
