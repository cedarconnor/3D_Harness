"""Owned, staged engineering fixture. Run functions through the live Blender MCP.

This is a authored procedural rehearsal, not independent agent trial evidence.
All geometry is generated here. Poly Haven supplies the pinned HDRI/stone maps.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

from dcc_harness.blender import observe, save_checkpoint
from dcc_harness.evidence import write_json, read_json, evaluate, compare
from dcc_harness.project import Project

SCENE = "HARNESS_Courtyard"


def material(name, color, roughness=0.6, metallic=0):
    mat = bpy.data.materials.new("H_" + name)
    mat["dcc_material_id"] = name
    mat.use_fake_user = True  # The palette must survive a setup checkpoint before assignment.
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color,1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mesh(name, verts, faces, mat, asset):
    data = bpy.data.meshes.new("H_" + name)
    data.from_pydata(verts,[],faces); data.update()
    obj = bpy.data.objects.new("H_" + name,data)
    bpy.context.scene.collection.objects.link(obj)
    obj["dcc_instance_id"] = name; obj["dcc_asset_id"] = asset
    if mat: data.materials.append(mat)
    return obj


def box(name, size, pos, mat, asset, bevel=0.025):
    x,y,z = (s/2 for s in size)
    verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    obj=mesh(name,verts,faces,mat,asset); obj.location=pos
    if bevel:
        mod=obj.modifiers.new("Crafted edges","BEVEL"); mod.width=bevel; mod.segments=3
    return obj


def prism(name, outline, depth, y, mat, asset):
    count=len(outline)
    verts=[(x,y+dy,z) for dy in (-depth/2,depth/2) for x,z in outline]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    return mesh(name,verts,faces,mat,asset)


def lathe(name, profile, location, mat, asset, sides=48):
    verts=[(r*math.cos(a*2*math.pi/sides),r*math.sin(a*2*math.pi/sides),z) for r,z in profile for a in range(sides)]
    faces=[]
    for j in range(len(profile)-1):
        for i in range(sides): faces.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    obj=mesh(name,verts,faces,mat,asset); obj.location=location
    for polygon in obj.data.polygons: polygon.use_smooth=True
    return obj


def mat(mid):
    return next(m for m in bpy.data.materials if m.get("dcc_material_id")==mid)


def aim(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def start(root):
    if bpy.data.scenes.get(SCENE): raise ValueError("Fixture exists; resume instead of rebuilding")
    scene=bpy.data.scenes.new(SCENE); bpy.context.window.scene=scene
    scene["dcc_project"]=str(root)
    scene.unit_settings.system="METRIC"; scene.unit_settings.scale_length=1
    scene.render.engine="CYCLES"; scene.cycles.samples=32; scene.cycles.use_denoising=True
    scene.render.resolution_x=960; scene.render.resolution_y=540; scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX"; scene.view_settings.look="AgX - Medium High Contrast"
    scene.render.image_settings.file_format="PNG"
    material("plaster",(0.65,0.57,0.43),.84)
    stone=material("stone",(.5,.45,.36),.72)
    material("teal-paint",(.028,.13,.13),.48)
    wood=material("wood",(.27,.11,.045),.48)
    material("bronze",(.16,.085,.03),.28,.8)
    material("terracotta",(.35,.105,.05),.84)
    material("foliage",(.075,.13,.036),.72)
    material("soil",(.05,.028,.014),1)
    material("grout",(.2,.18,.14),.92)
    # Shared PBR stone. Object coordinates follow applied geometry, not per-object bounding-box normalization.
    nodes,links=stone.node_tree.nodes,stone.node_tree.links
    tc=nodes.new("ShaderNodeTexCoord"); mapping=nodes.new("ShaderNodeVectorMath"); mapping.operation="SCALE"
    mapping.inputs[3].default_value=.5; links.new(tc.outputs["Object"],mapping.inputs[0])
    bsdf=nodes.get("Principled BSDF")
    for channel,filename,color_space in (("Base Color","sandstone_blocks_05_diff_1k.jpg","sRGB"),("Roughness","sandstone_blocks_05_rough_1k.jpg","Non-Color")):
        texture=nodes.new("ShaderNodeTexImage"); texture.image=bpy.data.images.load(str(root/"assets"/filename),check_existing=True)
        texture.image.colorspace_settings.name=color_space; texture.projection="BOX"; texture.projection_blend=.2
        links.new(mapping.outputs["Vector"],texture.inputs["Vector"])
        if channel=="Base Color":
            tint=nodes.new("ShaderNodeMixRGB"); tint.name="StoneTint"; tint.blend_type="MULTIPLY"; tint.inputs[0].default_value=.3
            tint.inputs[2].default_value=(.85,.76,.6,1); links.new(texture.outputs["Color"],tint.inputs[1]); links.new(tint.outputs[0],bsdf.inputs[channel])
        else: links.new(texture.outputs["Color"],bsdf.inputs[channel])
    # Box-projected normal maps need consistent tangent frames; use scalar bump for this fixture.
    bump=nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=.18; bump.inputs["Distance"].default_value=.022
    links.new(texture.outputs["Color"],bump.inputs["Height"]); links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
    n,l=wood.node_tree.nodes,wood.node_tree.links
    tc=n.new("ShaderNodeTexCoord"); mp=n.new("ShaderNodeVectorMath"); mp.operation="MULTIPLY"; mp.inputs[1].default_value=(1,28,28)
    l.new(tc.outputs["Object"],mp.inputs[0]); noise=n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value=2; noise.inputs["Detail"].default_value=2
    l.new(mp.outputs[0],noise.inputs[0]); ramp=n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color=(.09,.028,.01,1); ramp.color_ramp.elements[1].color=(.36,.16,.055,1)
    l.new(noise.outputs["Fac"],ramp.inputs[0]); l.new(ramp.outputs[0],n.get("Principled BSDF").inputs["Base Color"])
    world=bpy.data.worlds.new("H_CourtyardSky"); world.use_nodes=True; scene.world=world
    env=world.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image=bpy.data.images.load(str(root/"assets/kloppenheim_06_puresky_1k.hdr"))
    world.node_tree.links.new(env.outputs[0],world.node_tree.nodes.get("Background").inputs[0])
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.45
    for name,pos,target,lens in (("camera.hero",(11,-15,9),(0,.5,1.4),47),
                                 ("camera.reverse",(-10,-10,6),(0,1.1,1.5),48),
                                 ("camera.detail",(4,-6,3.5),(-1.2,1.6,.9),57)):
        camera=bpy.data.objects.new("H_"+name,bpy.data.cameras.new("H_"+name)); scene.collection.objects.link(camera)
        camera["dcc_instance_id"]=name; camera.location=pos; camera.data.lens=lens; aim(camera,target)
        if name=="camera.hero": scene.camera=camera
    sun=bpy.data.objects.new("H_Sun",bpy.data.lights.new("H_Sun","SUN")); scene.collection.objects.link(sun)
    sun["dcc_instance_id"]="light.sun"; sun.data.energy=2.1; sun.data.angle=.12; sun.data.color=(1,.84,.64)
    sun.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-25))


def architecture(root):
    plaster,stone=mat("plaster"),mat("stone")
    box("ground.foundation",(11,9,.22),(0,0,-.16),mat("grout"),"ground",.06)
    # Linked pavers preserve one definition across placements, with alternating orientation.
    tile=None
    for row in range(11):
        for col in range(13):
            name=f"ground.tile.{row:02}.{col:02}"
            pos=(-4.95+col*.81,-3.95+row*.79,-.025)
            if tile is None: tile=box(name,(.79,.77,.065),pos,stone,"paver",.016)
            else:
                obj=tile.copy(); obj.data=tile.data; bpy.context.scene.collection.objects.link(obj)
                obj.name="H_"+name; obj["dcc_instance_id"]=name; obj.location=pos
    for i,x in enumerate((-4.8,-1.6,1.6,4.8)):
        box(f"arcade.pier.{i}",(.6,.62,3.9),(x,3.6,1.95),plaster,"arcade",.025)
        box(f"arcade.base.{i}",(.8,.78,.24),(x,3.6,.12),stone,"arcade",.015)
        box(f"arcade.capital.{i}",(.78,.8,.15),(x,3.6,2.09),stone,"arcade",.012)
    for a,cx in enumerate((-3.2,0,3.2)):
        radius=1.3; spring=2.1
        arc=[(cx+radius*math.cos(i*math.pi/32),spring+radius*math.sin(i*math.pi/32)) for i in range(33)]
        outline=arc+[(cx-radius,4.1),(cx+radius,4.1)]
        prism(f"arcade.spandrel.{a}",outline,.6,3.6,plaster,"arcade")
        for j in range(13):
            t0=j*math.pi/13+.007; t1=(j+1)*math.pi/13-.007
            outline=[(cx+r*math.cos(t),spring+r*math.sin(t)) for r,t in ((radius,t0),(radius,t1),(radius+.23,t1),(radius+.23,t0))]
            obj=prism(f"arcade.voussoir.{a}.{j:02}",outline,.18,3.23,stone,"arcade")
            mod=obj.modifiers.new("Stone edge","BEVEL"); mod.width=.009; mod.segments=2
    for level,width,height,z in ((0,10.25,.14,4.1),(1,10.5,.13,4.235),(2,10.65,.08,4.34)):
        box(f"arcade.cornice.{level}",(width,.86+level*.08,height),(0,3.6,z),stone,"arcade",.012)
    box("enclosure.back",(10.3,.22,4.2),(0,4.35,2.1),plaster,"enclosure",.025)
    box("enclosure.left",(.28,7.8,1.1),(-5.25,.3,.55),plaster,"enclosure",.025)
    box("enclosure.left-cap",(.46,7.94,.13),(-5.25,.3,1.14),stone,"enclosure",.018)
    # Teal arched entry visible in the middle opening; recess provides physical depth.
    radius=1.06; spring=1.95
    outline=[(-radius,.02),(radius,.02),(radius,spring)]+[(radius*math.cos(i*math.pi/32),spring+radius*math.sin(i*math.pi/32)) for i in range(1,33)]
    prism("door.panel",outline,.12,4.16,mat("teal-paint"),"door")
    for i in range(11):
        x=-.99+i*.198; top=spring+math.sqrt(max(0,radius*radius-x*x))
        box(f"door.batten.{i}",(.022,.035,top-.10),(x,4.075,(top+.04)/2),mat("teal-paint"),"door",.004)
    for x in (-.14,.14):
        box("door.handle."+str(x),(.026,.055,.22),(x,4.04,1.05),mat("bronze"),"door",.008)
    box("door.threshold",(2.5,.8,.12),(0,3.92,.06),stone,"door",.018)


def furnishings(root):
    wood,metal=mat("wood"),mat("bronze")
    # Each bench member has its own stable placement and shares one asset family.
    cx,cy=-2.0,1.3
    for i in range(6):
        box(f"bench.seat.{i}",(1.9,.071,.035),(cx,cy-.23+i*.086,.48),wood,"bench",.013)
    for i in range(4):
        box(f"bench.back.{i}",(1.9,.038,.075),(cx,cy+.24+(i*.083)*.17,.63+i*.096),wood,"bench",.012)
    for side,x in enumerate((cx-.73,cx+.73)):
        for j,y in enumerate((cy-.19,cy+.21)):
            box(f"bench.leg.{side}.{j}",(.047,.047,.45),(x,y,.24),metal,"bench",.008)
        box(f"bench.frame.{side}",(.05,.53,.045),(x,cy,.44),metal,"bench",.008)
        box(f"bench.upright.{side}",(.04,.04,.53),(x,cy+.28,.71),metal,"bench",.008)
    profile=[(.0,.035),(.24,.035),(.26,.08),(.37,.61),(.39,.65),(.39,.70),(.34,.70),(.33,.63),(.24,.11),(.0,.11)]
    for idx,pos in enumerate(((3.5,1.5,0),(-4.25,-1.2,0),(3.9,-2.1,0))):
        lathe(f"planter.{idx}",profile,pos,mat("terracotta"),"planter")
        lathe(f"plant.soil.{idx}",[(0,.62),(.325,.62)],pos,mat("soil"),"plant")
        lathe(f"plant.trunk.{idx}",[(.035,.61),(.022,1.6)],pos,wood,"plant",12)
        # Curved leaves authored into one mesh, not hundreds of independently managed objects.
        rng=random.Random(82+idx); verts=[]; faces=[]
        for j in range(180):
            angle=rng.uniform(0,math.tau); height=rng.uniform(.93,2.05); radius=.55*max(.2,1-abs(height-1.5))
            base=Vector((math.cos(angle)*radius,math.sin(angle)*radius,height))
            direction=Vector((math.cos(angle),math.sin(angle),rng.uniform(-.2,.5)))
            side=Vector((-math.sin(angle),math.cos(angle),0))
            n=len(verts); length=rng.uniform(.13,.23); width=rng.uniform(.025,.045)
            verts.extend([tuple(base-direction*length),tuple(base+side*width),tuple(base+direction*length),tuple(base-side*width),tuple(base+Vector((0,0,.028)))])
            faces.extend([(n,n+1,n+4),(n+1,n+2,n+4),(n+2,n+3,n+4),(n+3,n,n+4)])
        leaf=mesh(f"plant.leaves.{idx}",verts,faces,mat("foliage"),"plant"); leaf.location=pos
    # Two wall lanterns. Geometry belongs to the enclosure family; physical light is separate.
    for idx,x in enumerate((-1.6,1.6)):
        box(f"enclosure.lantern.{idx}",(.20,.22,.32),(x,3.17,2.6),metal,"enclosure",.02)
        data=bpy.data.lights.new(f"H_Practical{idx}","POINT"); data.energy=15; data.color=(1,.52,.21); data.shadow_soft_size=.08
        light=bpy.data.objects.new(f"H_Practical{idx}",data); bpy.context.scene.collection.objects.link(light)
        light.location=(x,2.97,2.5); light["dcc_instance_id"]=f"light.practical.{idx}"


def revise(root):
    # Requested late revision: increase wooden bench span 1.9 -> 2.1m and cool shared stone.
    for obj in bpy.context.scene.objects:
        if obj.get("dcc_instance_id","").startswith(("bench.seat.","bench.back.")):
            for vertex in obj.data.vertices: vertex.co.x *= 2.1/1.9
            obj.data.update()
    tint=mat("stone").node_tree.nodes["StoneTint"]
    tint.inputs[2].default_value=(.68,.76,.82,1)
    tint.inputs[0].default_value=.55


def refine_look(root):
    # Review finding: the image's masonry lines compete with the actual paver joints.
    # Retain the source texture with lower contrast; geometry/lighting remain locked.
    stone=mat("stone"); nodes,links=stone.node_tree.nodes,stone.node_tree.links
    tint=nodes["StoneTint"]; source=tint.inputs[1].links[0].from_socket
    soften=nodes.new("ShaderNodeMixRGB"); soften.name="StoneContrast"
    soften.inputs[0].default_value=.72; soften.inputs[2].default_value=(.52,.49,.43,1)
    links.new(source,soften.inputs[1]); links.new(soften.outputs[0],tint.inputs[1])


STEPS={"00-start":start,"01-architecture":architecture,"02-furnishings":furnishings,"03-revision":revise,"04-look-refinement":refine_look}


def run_step(project_root, step):
    root=Path(project_root).resolve(); project=Project(root)
    if step not in STEPS: raise ValueError("Unknown fixture step")
    output=root/"checkpoints"/(step+".blend")
    if output.exists(): raise ValueError("Already saved; inspect instead of replaying")
    if step != "00-start" and (bpy.context.scene.name != SCENE or bpy.context.scene.get("dcc_project") != str(root)):
        raise ValueError("Wrong active document/scene")
    index=list(STEPS).index(step)
    if index:
        predecessor=list(STEPS)[index-1]
        previous=read_json(root/"evidence"/(predecessor+".json"))
        if observe()["revision"] != previous["revision"]:
            raise ValueError("Native state differs from predecessor; reconcile manual edits before proceeding")
    op=project.begin(step,Path(__file__))
    STEPS[step](root)
    observation=save_checkpoint(output,root/"evidence"/(step+".json"))
    project.finish(op,root/"evidence"/(step+".json"))
    return {"step":step,"checkpoint":str(output),"objects":len(observation["objects"]),
            "revision":observation["revision"],"issues":observation["issues"]}
