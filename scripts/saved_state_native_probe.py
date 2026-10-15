"""Blender side of qualify_saved_state.py: build a clean scene, or observe it before and after a Python edit.

blender --background --factory-startup --python-exit-code 1 --python THIS -- build --runtime R --out NEW_FOLDER
blender [--background] --factory-startup --disable-autoexec --python THIS -- probe --runtime R --source S --out NEW_FILE

Without --background the probe runs in an interactive session and exits through os._exit, so no quit dialog can wait.
"""
import json
import os
from pathlib import Path
import sys
import traceback

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
action = args[0]
options = dict(zip(args[1::2], args[2::2]))
sys.path.insert(0, options['--runtime'])


def build(out):
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    cube.name = 'ProbeCube'
    cube['dcc_instance_id'] = 'probe.cube'
    cube['dcc_asset_id'] = 'probe.cube-asset'
    material = bpy.data.materials.new('ProbeMaterial')
    material['dcc_material_id'] = 'probe.material'
    cube.data.materials.append(material)
    camera = bpy.data.objects.new('ProbeCamera', bpy.data.cameras.new('ProbeCamera'))
    camera['dcc_instance_id'] = 'probe.camera'
    camera.location = (4, -4, 3)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'clean.blend'))


def state(observation):
    return {key: observation.get(key) for key in ('native_dirty', 'native_dirty_reason', 'checkpoint_sha256', 'revision')}


def probe(source, out):
    from dcc_harness.continuity_blender import observe
    from dcc_harness.evidence import write_json
    from dcc_harness.visibility_blender import observe_visibility
    bpy.ops.wm.open_mainfile(filepath=source, load_ui=False)
    result = {'background': bpy.app.background, 'blender': bpy.app.version_string}
    opened = observe()
    write_json(out.with_name(out.stem + '-opened-observation.json'), opened)
    result['opened'] = state(opened)
    try:
        observe_visibility({}, opened)
        result['visibility_opened'] = 'accepted'
    except ValueError as exc:
        result['visibility_opened'] = str(exc)
    bpy.data.objects['ProbeCube'].location.x += 1.0
    result['is_dirty_after_python_edit'] = bpy.data.is_dirty
    result['edited'] = state(observe())
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')


if action == 'build':
    build(Path(options['--out']))
elif action == 'probe':
    code = 0
    try:
        probe(options['--source'], Path(options['--out']))
    except Exception:
        traceback.print_exc()
        code = 1
    if not bpy.app.background:
        sys.stdout.flush()
        os._exit(code)
    if code:
        sys.exit(code)
else:
    raise ValueError(action)
