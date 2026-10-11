"""Private fresh-process worker for revisions.py: pack a candidate's external textures into an owned copy.

Opens the artist's saved candidate, checks each named image's file against the observed hash, packs
it, and saves the result as a new file. The candidate itself is never saved.
"""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.evidence import file_hash, read_json


def pack(request):
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Candidate changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    for name, sha in request['images'].items():
        image = bpy.data.images.get(name)
        if image is None or image.packed_file:
            raise ValueError(f'Texture not found unpacked in the candidate: {name}')
        path = Path(bpy.path.abspath(image.filepath, library=image.library))
        if not path.is_file() or file_hash(path) != sha:
            raise ValueError(f'Texture file missing or changed since observation: {name}')
        image.pack()
    target = Path(request['target'])
    if target.exists():
        raise ValueError('Owned copy already exists; use a new folder')
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Candidate changed during packing')


def main():
    if not bpy.app.background:
        raise RuntimeError('Relocation requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'pack':
        raise ValueError('Unknown relocation worker action')
    pack(read_json(request_path))


main()
