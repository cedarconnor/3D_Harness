"""One contact-sheet image of chosen objects from all sides, for a quick look at shape and topology.

A fresh background Blender copies the targets' evaluated geometry into a temporary scene and renders
it with Workbench: columns are orbit views, rows are silhouette, clay with cavity, wireframe, and a
backface pass that paints faces pointing away from the viewer red. The source is never saved, and
the receipt binds the image to the file's hash. One image per call, at most 1600 pixels wide, so it
is cheap to read. It is evidence for review, not a quality verdict.
"""
from __future__ import annotations

from pathlib import Path
import struct
import zlib

from .continuity import _plain
from .evidence import digest, file_hash, read_json
from .native import run_worker
from .render import render_lock

WORKER = Path(__file__).with_name('_review_sheet_blender.py')
SIGNATURE = b'\x89PNG\r\n\x1a\n'
ROWS = {'silhouette': 'Black shape on white: outline, proportions and detached parts.',
        'clay': 'Even grey with cavity shading: surface form, without materials.',
        'wireframe': 'Edges of the evaluated mesh over a white surface: topology and density.',
        'backface': 'Faces pointing at the viewer are grey; faces pointing away are red, so flipped or inward faces show.'}
COLOURS = ('clay', 'random')
MAX_WIDTH, MIN_WIDTH = 1600, 400


def encode_png(width, height, rgb):
    """An 8-bit RGB PNG from row-major bytes, with no metadata, so equal pixels give equal files."""
    if len(rgb) != width * height * 3:
        raise ValueError('Pixel data does not match the image size')
    stride = width * 3
    raw = b''.join(b'\x00' + rgb[row * stride:(row + 1) * stride] for row in range(height))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def decode_png(data):
    """(width, height, RGB bytes) of a PNG written by encode_png."""
    if not data.startswith(SIGNATURE):
        raise ValueError('Not a PNG image')
    position, header, body = len(SIGNATURE), None, b''
    while position < len(data):
        length = struct.unpack('>I', data[position:position + 4])[0]
        kind, payload = data[position + 4:position + 8], data[position + 8:position + 8 + length]
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', payload)
        elif kind == b'IDAT':
            body += payload
        position += 12 + length
    if header is None or header[2:] != (8, 2, 0, 0, 0):
        raise ValueError('Not a review-sheet PNG')
    width, height = header[:2]
    raw, stride = zlib.decompress(body), width * 3 + 1
    if len(raw) != stride * height or any(raw[row * stride] for row in range(height)):
        raise ValueError('Not a review-sheet PNG')
    return width, height, b''.join(raw[row * stride + 1:(row + 1) * stride] for row in range(height))


def sheet_file(source, out, blender, *, targets=None, views=4, colour='clay', width=MAX_WIDTH):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    if views not in (4, 6):
        raise ValueError('Views must be 4 (orbit) or 6 (orbit, top and bottom)')
    if colour not in COLOURS:
        raise ValueError('Colour must be one of: ' + ', '.join(COLOURS))
    if isinstance(width, bool) or not isinstance(width, int) or not MIN_WIDTH <= width <= MAX_WIDTH:
        raise ValueError(f'Width must be from {MIN_WIDTH} to {MAX_WIDTH} pixels')
    targets = list(targets or [])
    if any(not isinstance(t, str) or not t for t in targets) or len(set(targets)) != len(targets):
        raise ValueError('Targets must be distinct ID globs')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    settings = {'targets': targets, 'views': views, 'colour': colour, 'width': width}
    with render_lock():
        run_worker(blender, folder, WORKER, 'sheet', {'source': descriptor, 'out': str(folder.resolve()), **settings}, timeout=600)
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during rendering; inspect retained outputs')
    receipt = read_json(folder / 'receipt.json')
    if receipt.get('schema') != 'dcc.review.sheet.v1' or receipt.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Sheet receipt is not bound to the source bytes')
    if receipt.get('settings_digest') != digest(settings):
        raise RuntimeError('Sheet receipt was made with other settings')
    image = _plain(folder / receipt['image']['path'])
    if file_hash(image) != receipt['image']['sha256']:
        raise RuntimeError('Sheet image changed after its receipt')
    layout = receipt['layout']
    return {'schema': 'dcc.review.sheet.result.v1', 'status': 'RENDERED', 'passed': True, 'image': str(image), 'receipt': str(folder / 'receipt.json'),
            'source': descriptor, 'source_unchanged': True, 'size': layout['size'],
            'rows': [{'row': name, 'shows': ROWS[name]} for name in layout['rows']], 'columns': layout['columns'],
            'targets': receipt['targets'], 'notes': receipt['notes'], 'artistic_acceptance': 'not_assessed'}
