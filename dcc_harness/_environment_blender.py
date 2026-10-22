"""Read actual factory-worker provider availability without activating providers."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.evidence import read_json, write_json
from dcc_harness.data.bridge import addons

action, request_path = sys.argv[sys.argv.index('--') + 1:]
if not bpy.app.background or action != 'inventory':
    raise ValueError('Inventory worker requires an owned background process')
request = read_json(request_path)
write_json(Path(request['out']) / 'inventory.json', addons.inventory(request.get('roots')))
