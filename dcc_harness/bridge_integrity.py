"""Standalone bridge byte identity; shared with the host export verifier."""
import hashlib
import json
from pathlib import Path


def identity(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_contents(contents, expected=None):
    try:
        manifest = json.loads(contents['manifest.json'])
    except (KeyError, ValueError) as exc:
        raise ValueError('Bridge manifest is missing or invalid') from exc
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'files'}
            or manifest['schema'] != 'dcc.blender.bridge.manifest.v1' or not isinstance(manifest['files'], dict)):
        raise ValueError('Invalid bridge manifest schema')
    if set(contents) != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('Bridge members differ from manifest')
    for name, wanted in manifest['files'].items():
        if not isinstance(name, str) or '/' in name or '\\' in name or ':' in name or name in ('', '.', '..'):
            raise ValueError('Invalid bridge manifest member')
        if hashlib.sha256(contents[name]).hexdigest() != wanted:
            raise ValueError('Bridge member changed: ' + name)
    actual = identity(manifest)
    if expected is not None and actual != expected:
        raise ValueError('Bridge manifest differs from this runtime')
    return {'identity': actual, 'files': manifest['files']}


def describe(expected=None):
    folder = Path(__file__).resolve().parent
    contents = {}
    for path in folder.iterdir():
        if path.name == '__pycache__' and path.is_dir():
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unexpected bridge member: ' + path.name)
        contents[path.name] = path.read_bytes()
    current = verify_contents(contents)['identity']
    if expected is not None and current != expected:
        raise ValueError('Bridge installation changed after import; restart Blender with the matching export')
    return current
