"""Blender-side runner for qualify_blender_skills.py; runs one skill's `python verify` blocks.

Each block runs in a fresh namespace after a factory reset to an empty scene, with `WORK` bound to
a new folder for any files it writes. A block passes when it finishes without an exception; its
own assertions are the checks. Results go to the JSON path given after `--`.
"""
import json
from pathlib import Path
import sys
import time
import traceback

import bpy

blocks_dir, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
results = []
for path in sorted(blocks_dir.glob('block-*.py')):
    work = blocks_dir / (path.stem + '-work')
    work.mkdir()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    started = time.time()
    try:
        exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), {'__name__': '__verify__', 'WORK': work})
        results.append({'block': path.name, 'passed': True, 'seconds': round(time.time() - started, 2)})
    except BaseException:
        results.append({'block': path.name, 'passed': False, 'seconds': round(time.time() - started, 2),
                        'error': traceback.format_exc()[-3000:]})
output.write_text(json.dumps({'blender': bpy.app.version_string, 'results': results}, indent=2), encoding='utf-8')
