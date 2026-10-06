"""Bounded quality-loop fixture. Run only in disposable background Blender.

build reads starter.blend and writes two new candidates. review reopens exactly
one saved candidate, observes before rendering, and never saves it. The design
must exist before build. This script is not a generic authoring adapter.
"""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("mode", choices=["build", "review", "conflict"])
parser.add_argument("--repo", required=True)
parser.add_argument("--root", required=True)
parser.add_argument("--candidate", choices=["unchanged", "workshop", "garden_workshop"])
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
if not bpy.app.background:
    raise RuntimeError("Use a disposable background process")
sys.path.insert(0, args.repo)
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.quality import reserved_space

root = Path(args.root).resolve()
design = read_json(root / "design.json")


def ref(path):
    return {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}


def load(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    bpy.context.view_layer.update()


if args.mode == "build":
    source = root / "unchanged" / "scene.blend"
    source_hash = file_hash(source)
    load(source)
    preflight = reserved_space(observe(), design["reservations"], list(design["contract"]["allowed_object_prefixes"]))
    write_json(root / "preflight.json", {"checkpoint_sha256": source_hash,
               "design_sha256": file_hash(root / "design.json"), **preflight})
    if not preflight["passed"]:
        raise RuntimeError("Reserved-space preflight failed before candidate authoring")
    variants = {
        "workshop": {"table_delta": [-7, .4, 0], "pots": [(-2.7, -6.5), (-3.1, -5.6), (4.8, -4.4), (5.5, -4.9)],
                     "stools": [(0, -4.6), (1.4, -4.6), (-1, -5.6), (3, -5.6)], "roof_scale": .84},
        "garden_workshop": {"table_delta": [0, 1.2, 0], "pots": [(0, -6.2), (-.8, -5.8), (4.8, -6.1), (4.1, -5.5)],
                            "stools": [(7, -5.8), (8.4, -5.7), (9.6, -5.3), (9.8, -4.2)], "roof_scale": .94},
    }
    for name, variant in variants.items():
        load(source)
        out = root / name
        out.mkdir(exist_ok=False)
        for obj in bpy.context.scene.objects:
            iid = obj.get("dcc_instance_id", "")
            delta = None
            if iid.startswith(("ext.table.", "ext.tool.")) or iid == "ext.plaque":
                delta = variant["table_delta"]
            for index, xy in enumerate(variant["pots"], 1):
                if iid.startswith(f"ext.planter.{index:02d}."):
                    delta = [xy[0] - (index - 1) * 2, xy[1] + 7, 0]
            for index, xy in enumerate(variant["stools"], 1):
                if iid.startswith(f"ext.stool.{index:02d}."):
                    oldx = [6, 7, 9, 10][index - 1]
                    oldy = -5.35 if index == 1 else -5
                    delta = [xy[0] - oldx, xy[1] - oldy, 0]
            if delta is not None:
                if obj.parent:
                    raise RuntimeError("Fixture expects unparented owned parts")
                obj.matrix_world = Matrix.Translation(Vector(delta)) @ obj.matrix_world
            if iid.startswith("ext.pergola."):
                obj.matrix_world = Matrix.Diagonal((1, 1, variant["roof_scale"], 1)) @ obj.matrix_world
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
        write_json(out / "build.json", {"source_sha256": source_hash, "design_sha256": file_hash(root / "design.json"),
                   "script_sha256": file_hash(__file__), "variant": variant, "checkpoint": ref(out / "scene.blend")})
    if file_hash(source) != source_hash:
        raise RuntimeError("Starter changed")
    write_json(root / "build-result.json", {"source_sha256": source_hash, "source_unchanged": True,
               "candidates": {name: ref(root / name / "scene.blend") for name in variants}})
elif args.mode == "review":
    if not args.candidate:
        raise ValueError("Review requires --candidate")
    out = root / args.candidate
    path = out / "scene.blend"
    source_hash = file_hash(path)
    load(path)
    obs = observe()
    write_json(out / "observation.json", obs)
    scene = bpy.context.scene
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "OPTIX"
    scene.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    images, actual = {}, {}
    for view in design["views"]:
        settings, camera = view["render"], view["camera"]
        scene.render.engine = settings["engine"]
        scene.render.resolution_x, scene.render.resolution_y = settings["resolution"]
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.cycles.samples = settings["samples"]
        scene.cycles.seed = settings["seed"]
        scene.cycles.use_denoising = settings["denoising"]
        if "object_id" in camera:
            cam = next(o for o in scene.objects if o.get("dcc_instance_id") == camera["object_id"])
        else:
            anchor = obs["objects"][camera["anchor_id"]]["bounds"]
            center = Vector([(anchor[0][i] + anchor[1][i]) / 2 for i in range(3)])
            cam = bpy.data.objects.new("ReviewOnly", bpy.data.cameras.new("ReviewOnly"))
            scene.collection.objects.link(cam)
            cam.location = center + Vector(camera["offset"])
            cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam.data.lens = camera["lens"]
        scene.camera = cam
        image = out / (view["id"] + ".png")
        if image.exists():
            raise FileExistsError(image)
        scene.render.filepath = str(image)
        bpy.ops.render.render(write_still=True)
        images[view["id"]] = ref(image)
        actual[view["id"]] = {"matrix_world": [list(row) for row in cam.matrix_world],
                               "lens": cam.data.lens, "color": obs["scene"]["color"], "settings": settings}
    if file_hash(path) != source_hash:
        raise RuntimeError("Render source changed")
    write_json(out / "captures.json", actual)
    write_json(out / "renders.json", {"schema": "dcc.quality.renders.v1", "checkpoint_sha256": source_hash,
               "views_digest": digest(design["views"]), "images": images})
else:
    source = Path(args.repo) / "runs/continuity-round-2026-10-04/private/accepted/t-7a293d736a98/s04/scene.blend"
    original = file_hash(source)
    load(source)
    obs = observe()
    tray_ids = [iid for iid in obs["objects"] if "tray" in iid and obs["objects"][iid]["type"] == "MESH"]
    rules = [{"id": "plaque_patch", "bounds": [[7.75, -6.15, .951], [8.25, -5.85, 1.1]],
              "obstacle_prefixes": tray_ids, "exempt_ids": [], "tolerance": .000001}]
    before = reserved_space(obs, rules)
    if before["passed"] or not any(f["kind"] == "potential_overlap" for f in before["findings"]):
        raise AssertionError("Expected historical tray/plaque conflict")
    # Native positive control in this unsaved disposable process only.
    for obj in bpy.context.scene.objects:
        if obj.get("dcc_instance_id") in tray_ids:
            obj.location.x += 2
    bpy.context.view_layer.update()
    after = reserved_space(observe(), rules, tray_ids)
    if not after["passed"] or file_hash(source) != original:
        raise AssertionError("Moving tray should clear the patch without changing the source")
    write_json(root / "conflict-regression.json", {"source_sha256": original, "before": before, "after": after,
               "source_unchanged": True, "native_saves": 0, "limits": "Broad phase only; positive control was not adopted."})
print("QUALITY_NATIVE_OK", args.mode, args.candidate or "")
