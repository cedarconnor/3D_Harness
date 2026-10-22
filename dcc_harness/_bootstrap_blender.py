"""Fixed empty-scene initializer, always in a disposable background process."""
import json
from pathlib import Path
import sys
import bpy

action, request_file = sys.argv[sys.argv.index('--') + 1:]
if action != 'initialize' or not bpy.app.background:
    raise RuntimeError('Only background initialization is supported')
request = json.loads(Path(request_file).read_text(encoding='utf-8'))
output = Path(request['output'])
if output.exists():
    raise ValueError('Baseline already exists; never overwrite')
bpy.ops.wm.read_factory_settings(use_empty=True)
root = bpy.data.objects.new('HarnessRoot', None)
root['dcc_instance_id'] = 'harness.root'
root['dcc_asset_id'] = 'harness.root'
bpy.context.scene.collection.objects.link(root)
bpy.ops.wm.save_as_mainfile(filepath=str(output))
