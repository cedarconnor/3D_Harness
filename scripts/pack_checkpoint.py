"""Create a portable native checkpoint in the owned project through the MCP."""
from pathlib import Path
import bpy
from dcc_harness.blender import save_checkpoint
from dcc_harness.project import Project


def run(root):
    root=Path(root).resolve()
    if bpy.context.scene.get("dcc_project")!=str(root): raise ValueError("Wrong scene")
    output=root/"checkpoints/05-portable.blend"
    if output.exists(): raise ValueError("Portable checkpoint already exists")
    project=Project(root); op=project.begin("pack-dependencies",Path(__file__))
    used=[i for i in bpy.data.images if i.source=="FILE" and i.users]
    for image in used:
        if not image.packed_file: image.pack()
    receipt=root/"evidence/05-portable.json"
    observation=save_checkpoint(output,receipt); project.finish(op,receipt)
    return {"checkpoint":str(output),"revision":observation["revision"],"packed_images":len(used)}
