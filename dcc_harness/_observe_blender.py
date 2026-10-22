"""Private fresh-process worker for observe.py; never run in an artist editor."""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.environments import assert_worker_profile


def main():
    if not bpy.app.background:
        raise RuntimeError('Saved-file observation requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'observe':
        raise ValueError('Unknown observation worker action')
    request = read_json(request_path)
    assert_worker_profile(request)
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed during native open')
    from dcc_harness.continuity_blender import observe
    write_json(Path(request['out']) / 'observation.json', observe(), compact_observation=request['compact'])
    assert_worker_profile(request)
    if file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')


if __name__ == '__main__':
    main()
