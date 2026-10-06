"""Blender process: reopen, observe, optionally check, render fixed cameras.

blender --background FILE --python-exit-code 1 --python THIS -- --repo REPO
        --out NEW_DIRECTORY [--spec SPEC] [--observe-only]
Never saves the loaded .blend. Source checksum must be unchanged on exit.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import bpy

parser=argparse.ArgumentParser()
parser.add_argument("--repo",required=True); parser.add_argument("--out",required=True)
parser.add_argument("--spec"); parser.add_argument("--observe-only",action="store_true")
parser.add_argument("--packed-only",action="store_true",help="Require packed images and redirect their external paths in this disposable process")
parser.add_argument("--cameras",nargs="+",default=["camera.hero","camera.reverse","camera.detail"])
args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
sys.path.insert(0,args.repo)
from dcc_harness.blender import observe
from dcc_harness.evidence import write_json,read_json,file_hash,evaluate

out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
source=Path(bpy.data.filepath); source_hash=file_hash(source)
scene=bpy.context.scene
observation=observe(); write_json(out/"observation.json",observation)
report={"source":str(source),"source_sha256":source_hash,"scene":scene.name,"blender":bpy.app.version_string,
        "revision":observation["revision"],"captures":[],"check":None}
if args.spec:
    report["check"]=evaluate(observation,read_json(args.spec)); write_json(out/"checks.json",report["check"])
if args.packed_only:
    used=[i for i in bpy.data.images if i.source=="FILE" and i.users]
    if not used or any(not i.packed_file for i in used): raise RuntimeError("Used image is not packed")
    for image in used: image.filepath=str(out/"absent-external-assets"/image.name)
    report["packed_only"]={"images":len(used),"external_paths_redirected":True}
if not args.observe_only:
    prefs=bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type="OPTIX"; prefs.get_devices()
    gpu=False
    for device in prefs.devices:
        device.use=device.type=="OPTIX"; gpu |= device.use
    scene.cycles.device="GPU" if gpu else "CPU"
    for iid in args.cameras:
        camera=next((o for o in scene.objects if o.get("dcc_instance_id")==iid),None)
        if camera is None or camera.type!="CAMERA": raise ValueError(f"Missing camera {iid}")
        path=out/(iid+".png"); scene.camera=camera; scene.render.filepath=str(path)
        start=time.monotonic(); bpy.ops.render.render(write_still=True)
        report["captures"].append({"camera_id":iid,"camera":observation["objects"][iid],
             "image":str(path),"sha256":file_hash(path),"seconds":round(time.monotonic()-start,3),
             "engine":scene.render.engine,"device":scene.cycles.device,"samples":scene.cycles.samples,"seed":scene.cycles.seed,
             "resolution":[scene.render.resolution_x,scene.render.resolution_y],"color":observation["scene"]["color"]})
report["source_unchanged"]=file_hash(source)==source_hash
report["passed"]=report["source_unchanged"] and not observation["issues"] and (report["check"] is None or report["check"]["passed"])
write_json(out/"report.json",report)
print("DCC_RESULT "+json.dumps({"passed":report["passed"],"revision":report["revision"],"captures":len(report["captures"])}))
if not report["passed"]: raise RuntimeError("Checkpoint verification failed; inspect reports")
