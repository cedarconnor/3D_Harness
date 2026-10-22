"""Inspect a pinned node asset in an owned process before importing it into a live scene."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.evidence import read_json, write_json, file_hash, digest
from dcc_harness.node_asset_blender import describe

if not bpy.app.background:
    raise RuntimeError('Node asset qualification requires an owned background process')
action, request_file = sys.argv[sys.argv.index('--') + 1:]
request = read_json(request_file)
source = request['source']
if action != 'qualify-asset' or file_hash(source['path']) != source['sha256']:
    raise ValueError('Pinned node asset changed')
bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
description = describe(bpy.data.node_groups.get(request['group']))
if file_hash(source['path']) != source['sha256']:
    raise ValueError('Pinned node asset changed during qualification')
write_json(Path(request['out']) / 'asset-qualification.json',
           {'source': source, 'group': request['group'], 'description': description,
            'graph_sha256': digest(description), 'blender': bpy.app.version_string})
