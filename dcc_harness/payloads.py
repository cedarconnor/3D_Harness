"""Fill and verify {path, sha256} file references in coordination payloads.

Paths follow the coordination artifact rules: contained, relative and free of
links. A present hash is verified, never replaced: a mismatch may mean the file
changed after review. The input is never rewritten.
"""
from __future__ import annotations

from .continuity import _plain
from .coordination import relative
from .evidence import file_hash, read_json, write_json


def fill_hashes(payload, destination, base=None):
    source, destination = _plain(payload), _plain(destination)
    value = read_json(source)
    base = _plain(base) if base is not None else source.parent
    filled, verified = [], []

    def visit(item):
        if isinstance(item, dict):
            if isinstance(item.get('path'), str) and set(item) <= {'path', 'sha256'}:
                path = relative(base, item['path'])
                if not path.is_file():
                    raise ValueError(f"Referenced file not found: {item['path']}")
                actual = file_hash(path)
                if item.get('sha256') in (None, ''):
                    item['sha256'] = actual
                    filled.append(item['path'])
                elif item['sha256'] != actual:
                    raise ValueError(f"Hash mismatch for {item['path']}: the file changed or the hash is wrong")
                else:
                    verified.append(item['path'])
                return
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    write_json(destination, value)
    return {'schema': 'dcc.fill-hashes.v1', 'destination': str(destination), 'base': str(base),
            'filled': filled, 'verified': verified}
