"""Blender-side observation/checkpoint helpers. Import through the existing MCP.

Uses the active scene, including hidden objects. IDs are caller-owned custom
properties dcc_instance_id / dcc_asset_id; material IDs are dcc_material_id.
Never silently assign or repair identities while observing.
"""
from __future__ import annotations

import array
import hashlib
from pathlib import Path

import bpy
from mathutils import Vector

from .evidence import digest, file_hash, write_json
from .project import now


def value(v):
    if isinstance(v, (str, int, bool)) or v is None:
        return v
    if isinstance(v, float):
        return round(v, 7)
    if hasattr(v, "name"):
        return {"datablock":v.name}
    try:
        return [value(x) for x in v]
    except TypeError:
        return {"unsupported_type":type(v).__name__}


def image_record(image):
    path = Path(bpy.path.abspath(image.filepath, library=image.library)) if image.filepath else None
    packed = bool(image.packed_file)
    return {"name":image.name,"source":image.source,"path":str(path) if path else None,
            "packed":packed,"colorspace":image.colorspace_settings.name,
            "exists":packed or bool(path and path.is_file()),
            "sha256":hashlib.sha256(bytes(image.packed_file.data)).hexdigest() if packed else
                     file_hash(path) if path and path.is_file() else None}


def graph(tree):
    if tree is None:
        return None
    nodes = []
    for node in sorted(tree.nodes, key=lambda n:n.name):
        rec = {"name":node.name,"type":node.bl_idname,"inputs":{
            s.identifier:value(s.default_value) for s in node.inputs if hasattr(s,"default_value")}}
        for attr in ("operation","blend_type","projection","projection_blend","interpolation","extension","noise_dimensions","normalize"):
            if hasattr(node,attr): rec[attr] = value(getattr(node,attr))
        if getattr(node,"image",None): rec["image"] = image_record(node.image)
        if getattr(node,"node_tree",None):
            rec["group"] = node.node_tree.name
            rec["unsupported_group"] = True
        if hasattr(node,"color_ramp"):
            rec["ramp"] = [[value(e.position),value(e.color)] for e in node.color_ramp.elements]
        nodes.append(rec)
    links = sorted([[l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier] for l in tree.links])
    return {"nodes":nodes,"links":links}


def mesh_record(obj, deps):
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
    try:
        mesh.calc_loop_triangles()
        h = hashlib.sha256()
        for collection, prop, length, kind in ((mesh.vertices,"co",len(mesh.vertices)*3,"f"),
                                              (mesh.loops,"vertex_index",len(mesh.loops),"i"),
                                              (mesh.polygons,"loop_total",len(mesh.polygons),"i"),
                                              (mesh.polygons,"material_index",len(mesh.polygons),"i")):
            data = array.array(kind,[0])*length
            collection.foreach_get(prop,data)
            h.update(data.tobytes())
        uv_hash = hashlib.sha256()
        for layer in mesh.uv_layers:
            data = array.array("f",[0])*(len(layer.data)*2)
            layer.data.foreach_get("uv", data)
            uv_hash.update(layer.name.encode()); uv_hash.update(data.tobytes())
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        if points:
            lo = [min(p[i] for p in points) for i in range(3)]
            hi = [max(p[i] for p in points) for i in range(3)]
        else:
            lo = hi = [0.0,0.0,0.0]
        return {"vertices":len(mesh.vertices),"triangles":len(mesh.loop_triangles),
                "geometry_hash":h.hexdigest(),"uv_hash":uv_hash.hexdigest(),
                "uv_layers":[u.name for u in mesh.uv_layers],"bounds":[value(lo),value(hi)],
                "dimensions":value([hi[i]-lo[i] for i in range(3)])}
    finally:
        evaluated.to_mesh_clear()


def observe(scene=None):
    scene = scene or bpy.context.scene
    if scene != bpy.context.scene:
        raise ValueError("Observe the active scene so depsgraph and scene agree")
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    objects, materials, issues = {}, {}, []
    # Cache by real datablock, never caller-owned IDs. Keep this local so the
    # next observation re-reads shaders and external image contents.
    material_records = {}
    for obj in sorted(scene.objects,key=lambda o:o.name):
        iid = obj.get("dcc_instance_id")
        if not isinstance(iid,str) or not iid:
            issues.append(f"Missing instance ID: {obj.name}")
            iid = "unbound:" + obj.name
        if iid in objects:
            issues.append(f"Duplicate instance ID: {iid}")
            iid = "collision:" + obj.name
        aid = obj.get("dcc_asset_id")
        if obj.type == "MESH" and not aid:
            issues.append(f"Missing asset ID: {obj.name}")
        rec = {"name":obj.name,"type":obj.type,"asset_id":aid,
               "matrix_world":value(obj.matrix_world),"parent":obj.parent.get("dcc_instance_id") if obj.parent else None,
               "collections":sorted(c.name for c in obj.users_collection),
               "visibility":{"render":not obj.hide_render,"viewport":not obj.hide_viewport,"hidden":obj.hide_get()},
               "material_ids":[]}
        if obj.instance_type != "NONE": issues.append(f"Unsupported instancer: {obj.name}")
        if obj.type == "MESH": rec.update(mesh_record(obj,deps))
        if obj.type == "LIGHT":
            rec["light"] = {key:value(getattr(obj.data,key)) for key in ("type","energy","color","shadow_soft_size","angle","size") if hasattr(obj.data,key)}
        if obj.type == "CAMERA":
            rec["camera"] = {key:value(getattr(obj.data,key)) for key in ("type","lens","sensor_width","sensor_height","sensor_fit","shift_x","shift_y","ortho_scale","clip_start","clip_end")}
            rec["camera"]["dof"] = {"enabled":obj.data.dof.use_dof,"distance":value(obj.data.dof.focus_distance),"fstop":value(obj.data.dof.aperture_fstop),"object":obj.data.dof.focus_object.name if obj.data.dof.focus_object else None}
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                issues.append(f"Unbound material slot: {obj.name}"); rec["material_ids"].append(None); continue
            mid = mat.get("dcc_material_id")
            if not mid:
                issues.append(f"Missing material ID: {mat.name}"); mid = "unbound:" + mat.name
            if mid in materials and materials[mid]["name"] != mat.name:
                issues.append(f"Duplicate material ID: {mid}")
            rec["material_ids"].append(mid)
            pointer = mat.as_pointer()
            if pointer not in material_records:
                material_records[pointer] = {"name":mat.name,"diffuse_color":value(mat.diffuse_color),"graph":graph(mat.node_tree)}
            materials[mid] = material_records[pointer]
        objects[iid] = rec
    world = graph(scene.world.node_tree) if scene.world else None
    for data in [m["graph"] for m in materials.values()] + [world]:
        for node in data["nodes"] if data else []:
            if node.get("image") and not node["image"]["exists"]: issues.append(f"Missing image: {node['image']['path']}")
            if node.get("unsupported_group"): issues.append(f"Unmeasured node group: {node['group']}")
    config = {"name":scene.name,"units":{"system":scene.unit_settings.system,"scale_length":scene.unit_settings.scale_length},
              "world":world,"camera":scene.camera.get("dcc_instance_id") if scene.camera else None,
              "frame":scene.frame_current,"fps":[scene.render.fps,scene.render.fps_base],
              "render":{"engine":scene.render.engine,"resolution":[scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage],
                        "samples":scene.cycles.samples,"transparent":scene.render.film_transparent},
              "color":{"view_transform":scene.view_settings.view_transform,"look":scene.view_settings.look,
                       "exposure":scene.view_settings.exposure,"gamma":scene.view_settings.gamma}}
    coverage = {"version":1,"measured":["active-scene object IDs and transforms","evaluated mesh coordinates/topology/material indices","evaluated UV coordinates","material binding and selected shader inputs/links","image dependencies and hashes","world nodes","camera optics","light settings","render and color settings"],
                "not_measured":["other scenes","arbitrary modifiers and node properties","animation curves across time","simulation caches","rig semantics","collection/Geometry Nodes instances","general topology quality","UV overlap/texel density","artistic quality"]}
    payload = {"objects":objects,"materials":materials,"scene":config,"issues":sorted(set(issues)),"coverage":coverage}
    return {"schema":"dcc.observation.v1","observed_at":now(),"blender":bpy.app.version_string,
            "file":bpy.data.filepath,"revision":digest(payload),**payload}


def save_checkpoint(path, observation_path=None):
    path = Path(path).resolve()
    if path.suffix.lower() != ".blend" or path.exists():
        raise ValueError("Checkpoint requires a new .blend filename")
    path.parent.mkdir(parents=True, exist_ok=True)
    observation = observe()
    if observation["issues"]:
        raise ValueError(f"Cannot accept checkpoint with observation issues: {observation['issues']}")
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    observation = observe()
    observation["checkpoint_sha256"] = file_hash(path)
    if observation_path: write_json(observation_path,observation)
    return observation

