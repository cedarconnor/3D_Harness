"""Execute one retained script against an owned copy, in a fresh background process."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.evidence import file_hash, read_json
from dcc_harness.environments import assert_worker_profile

if not bpy.app.background:
    raise RuntimeError('Managed execution requires an owned background process')
action, path = sys.argv[sys.argv.index('--') + 1:]
if action != 'execute':
    raise ValueError('Unknown execution action')
request = read_json(path)
assert_worker_profile(request)
if file_hash(request['source']['path']) != request['source']['sha256'] or file_hash(request['script']) != request['script_sha256']:
    raise ValueError('Retained execution input changed')
if Path(request['output']).exists():
    raise ValueError('Candidate already exists; never replay a native mutation')
bpy.ops.wm.open_mainfile(filepath=request['source']['path'], load_ui=False)
runpy.run_path(request['script'], init_globals={'DCC_OUTPUT_PATH': request['output']}, run_name='__main__')
assert_worker_profile(request)
bpy.ops.wm.save_as_mainfile(filepath=request['output'])
