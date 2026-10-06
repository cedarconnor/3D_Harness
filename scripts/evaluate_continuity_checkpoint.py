"""Independently inspect a loaded native continuity checkpoint; never save it.

blender --background CHECKPOINT --python-exit-code 1 --python THIS --
  --repo REPO --out NEWDIR --contract CONTRACT --before OBSERVATION [--observe-only]

Exit zero means inspection completed. Read report.json's passed flag for verdict.
The raw observer output is retained beside the supplemented comparable output.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import bpy

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--contract", required=True)
parser.add_argument("--before", required=True)
parser.add_argument("--observe-only", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
sys.path.insert(0, args.repo)

from dcc_harness.blender import observe as observe_raw
from dcc_harness.continuity_blender import enhance
from dcc_harness.continuity_checks import evaluate_stage, validate_contract
from dcc_harness.evidence import file_hash, read_json, write_json, validate_observation

contract = read_json(args.contract)
validate_contract(contract)
before = read_json(args.before)
validate_observation(before)
source = Path(bpy.data.filepath)
if not bpy.data.filepath or not source.is_file():
    raise ValueError("Load an existing checkpoint before evaluation")
source_hash = file_hash(source)
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
raw = observe_raw()
write_json(out / "raw-observation.json", raw)
obs = enhance(raw)
write_json(out / "observation.json", obs)
check = evaluate_stage(before, obs, contract)
write_json(out / "check.json", check)
write_json(out / "preservation.json", check["preservation"])
extra = []
views = ("hero", "reverse", "detail", "overview", "garden", "forecourt")
native = {}
for obj in scene.objects:
    iid = obj.get("dcc_instance_id")
    if iid in native:
        extra.append("Duplicate native identity: " + str(iid))
    native[iid] = obj
if len(bpy.data.scenes) != 1:
    extra.append("Expected exactly one native scene")
if len(scene.objects) >= 2000:
    extra.append("Expected fewer than 2000 scene objects")
if sum(obj.type == "CAMERA" for obj in scene.objects) != 6:
    extra.append("Expected exactly six native cameras")
for view in views:
    obj = native.get("camera." + view)
    if obj is None or obj.type != "CAMERA":
        extra.append("Missing native camera." + view)
prior_lights = {iid for iid, obj in before["objects"].items() if obj.get("type") == "LIGHT"}
native_lights = {obj.get("dcc_instance_id") for obj in scene.objects if obj.type == "LIGHT"}
if native_lights != prior_lights:
    extra.append("Native light identities differ from the fixed illumination baseline")
if any(not image.packed_file for image in bpy.data.images if image.source == "FILE" and image.users):
    extra.append("Used file image dependency is not packed")
for group in contract.get("sharing_groups", []):
    objects = [native.get(iid) for iid in group]
    if any(obj is None or obj.type != "MESH" for obj in objects) or len({
            obj.data.as_pointer() for obj in objects if obj is not None and obj.type == "MESH"}) != 1:
        extra.append("Native mesh sharing group differs or missing: " + ", ".join(group))
    # Scene placements establish sharing; fake-user and out-of-scene datablock users never count.
if scene.camera is None or scene.camera.get("dcc_instance_id") != "camera.hero":
    extra.append("Active native camera differs from camera.hero")
if scene.render.engine != "CYCLES" or scene.cycles.samples != 32 or scene.cycles.seed != 0 or not scene.cycles.use_denoising:
    extra.append("Native Cycles engine/samples/seed/denoising differs from fixed preset")
if (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage) != (960, 540, 100):
    extra.append("Native resolution differs from fixed preset")
if scene.render.image_settings.file_format != "PNG":
    extra.append("Native output format differs from PNG")
if (scene.view_settings.view_transform, scene.view_settings.look, scene.view_settings.exposure, scene.view_settings.gamma) != (
        "AgX", "AgX - Medium High Contrast", 0.0, 1.0):
    extra.append("Native color management differs from fixed preset")
for mid, nodes in contract.get("allowed_material_inputs", {}).items():
    material = bpy.data.materials.get(obs["materials"].get(mid, {}).get("name", ""))
    for name, sockets in nodes.items():
        node = material.node_tree.nodes.get(name) if material and material.node_tree else None
        for socket in sockets:
            value = node.inputs.get(socket) if node else None
            if value is None or value.is_linked:
                extra.append(f"Native material input missing or linked: {mid}/{name}/{socket}")

report = {
    "source_sha256": source_hash,
    "evaluator_sha256": file_hash(__file__),
    "runtime_sha256": {name: file_hash(Path(args.repo) / "dcc_harness" / name)
                       for name in ("blender.py", "continuity_blender.py", "continuity_checks.py", "evidence.py", "uv_guard.py")},
    "contract_sha256": file_hash(args.contract), "before_sha256": file_hash(args.before),
    "blender": bpy.app.version_string, "check": check, "extra_failures": extra,
    "native_runtime_validation": "performed", "captures": [], "artistic_acceptance": "not_evaluated",
    "dependency_comparison": "Packed image path spelling normalized; raw observation and content SHA256 retained",
    "unmeasured": obs["coverage"]["not_measured"],
}
if not args.observe_only:
    # All actual native settings were observed and checked before this disposable render normalization.
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == "OPTIX"
        scene.cycles.device = "GPU" if any(device.use for device in prefs.devices) else "CPU"
    except Exception:
        scene.cycles.device = "CPU"
    for view in views:
        camera = native.get("camera." + view)
        if camera is None or camera.type != "CAMERA":
            continue
        scene.camera = camera
        scene.render.filepath = str(out / (view + ".png"))
        started = time.monotonic()
        fallback = None
        try:
            try:
                bpy.ops.render.render(write_still=True)
            except RuntimeError as error:
                if scene.cycles.device != "GPU":
                    raise
                fallback = str(error)
                scene.cycles.device = "CPU"
                bpy.ops.render.render(write_still=True)
            report["captures"].append({"view": view, "seconds": round(time.monotonic() - started, 3),
                "sha256": file_hash(out / (view + ".png")), "device": scene.cycles.device,
                "gpu_fallback_error": fallback})
        except Exception as error:
            extra.append(f"Capture failed: {view}: {type(error).__name__}: {error}")
report["source_unchanged"] = file_hash(source) == source_hash
report["passed"] = check["passed"] and not extra and report["source_unchanged"]
write_json(out / "report.json", report)
print("DCC_CONTINUITY_CHECK " + json.dumps({"passed": report["passed"], "failures": check["failures"] + extra}))
