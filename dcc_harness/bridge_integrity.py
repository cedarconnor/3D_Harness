"""Standalone bridge byte identity; shared with the host export verifier."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat


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
        path=PurePosixPath(name) if isinstance(name,str) else None
        if (path is None or path.is_absolute() or '..' in path.parts or str(path)!=name
                or '\\' in name or ':' in name or name in ('', '.', '..')):
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
    pending=[folder]; directories=set()
    while pending:
        for path in pending.pop().iterdir():
            info=path.lstat()
            if path.is_symlink() or getattr(info,'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('Unexpected redirecting bridge member')
            if path.is_dir():
                if path.name=='__pycache__': continue
                directories.add(path.relative_to(folder).as_posix()); pending.append(path)
            elif path.is_file(): contents[path.relative_to(folder).as_posix()]=path.read_bytes()
            else: raise ValueError('Unexpected bridge member: '+path.name)
    declared=json.loads(contents.get('manifest.json',b'{}')).get('files',{})
    expected_directories={str(parent) for name in declared for parent in PurePosixPath(name).parents if str(parent)!='.'}
    if directories!=expected_directories: raise ValueError('Unexpected bridge directory')
    current = verify_contents(contents)['identity']
    if expected is not None and current != expected:
        raise ValueError('Bridge installation changed after import; restart Blender with the matching export')
    return current
