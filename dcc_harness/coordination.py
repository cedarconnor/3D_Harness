"""Immutable, optional coordination records above the native checkpoint journal."""
from __future__ import annotations

import copy
import os
from pathlib import Path, PurePosixPath
import uuid

from .continuity import Continuity, _plain, _sha, _write, _json_bytes
from .evidence import canonical, digest, file_hash, read_json
from .files import copy_verified
from .project import now


KINDS = {'feedback.add', 'feedback.respond', 'feedback.verify', 'feedback.decide',
         'workflow.bind', 'stage.submit', 'stage.complete', 'stage.reopen', 'check.propose', 'capability.bind'}


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise ValueError('Missing or unknown fields: ' + ', '.join(sorted(required)))
    canonical(value)


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Nonempty text is required')
    return value


def identifier(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('A canonical UUID is required')
    return value


def relative(base, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name or
            name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Artifact path must be a contained relative path')
    path = _plain(Path(base) / PurePosixPath(name))
    if not path.resolve().is_relative_to(_plain(base).resolve()):
        raise ValueError('Artifact path escapes its root')
    return path


def read(root):
    """Verify every retained event and artifact before deriving coordination state."""
    root = _plain(root)
    folder = _plain(root / 'coordination')
    if not folder.exists():
        return []
    events_dir = _plain(folder / 'events')
    if not folder.is_dir() or {p.name for p in folder.iterdir()} != {'events'} or not events_dir.is_dir():
        raise RuntimeError('Partial coordination storage; inspect before continuing')
    paths = sorted(events_dir.iterdir())
    if not paths:
        raise RuntimeError('Partial coordination storage; inspect before continuing')
    result, previous, requests = [], 'none', set()
    project_sha = file_hash(_plain(root / 'project.json'))
    for index, directory in enumerate(paths, 1):
        directory = _plain(directory)
        if directory.name != f'{index:06d}' or not directory.is_dir() or not (directory / 'manifest.json').is_file():
            raise RuntimeError('Partial coordination event; inspect before continuing')
        manifest = read_json(_plain(directory / 'manifest.json'))
        fields(manifest, {'schema', 'sequence', 'files'})
        if manifest['schema'] != 'dcc.coordination.manifest.v1' or type(manifest['sequence']) is not int or manifest['sequence'] != index:
            raise ValueError('Invalid coordination manifest')
        actual = set()
        for path in directory.rglob('*'):
            _plain(path)
            if path.is_file() and path != directory / 'manifest.json':
                actual.add(path.relative_to(directory).as_posix())
            elif path.is_dir() and path != directory / 'artifacts' and not path.relative_to(directory).as_posix().startswith('artifacts/'):
                raise ValueError('Unexpected coordination directory')
        inventory = manifest['files']
        if not isinstance(inventory, dict) or set(inventory) != actual or 'event.json' not in inventory:
            raise ValueError('Coordination inventory changed')
        for name, sha in inventory.items():
            if name != 'event.json' and not name.startswith('artifacts/'):
                raise ValueError('Unexpected coordination file')
            if not _sha(sha) or file_hash(relative(directory, name)) != sha:
                raise ValueError('Retained coordination evidence changed')
        event = read_json(directory / 'event.json')
        fields(event, {'schema', 'kind', 'request_id', 'request_hash', 'previous', 'project_sha256', 'created', 'payload', 'result'})
        identifier(event['request_id'])
        if (event['schema'] != 'dcc.coordination.event.v1' or event['kind'] not in KINDS or
                event['previous'] != previous or event['project_sha256'] != project_sha or
                event['request_id'] in requests or
                event['request_hash'] != digest({'kind': event['kind'], 'payload': event['payload']})):
            raise ValueError('Invalid coordination event chain')
        requests.add(event['request_id'])
        previous = file_hash(directory / 'manifest.json')
        result.append({**event, 'id': previous, 'sequence': index, 'artifacts': str(directory / 'artifacts')})
    return result


class Context:
    def __init__(self, root, native, events, base):
        self.root, self.native, self.events = Path(root), native, events
        self.base, self.files = _plain(base), {}

    def checkpoint(self, ref, *, current=False):
        fields(ref, {'checkpoint_id', 'checkpoint_sha256'})
        entry = next((e for e in self.native['task_history'] if e['id'] == ref['checkpoint_id']), None)
        if entry is None or entry['checkpoint_sha256'] != ref['checkpoint_sha256']:
            raise ValueError('Unknown checkpoint or native hash')
        if current and entry['id'] != self.native['active']['id']:
            raise ValueError('Stale checkpoint; resume before continuing')
        return entry

    def artifact(self, ref):
        fields(ref, {'path', 'sha256'})
        path = relative(self.base, ref['path'])
        # Names that differ only in case, or otherwise reach one file, would collide when retained on Windows.
        if any(name != ref['path'] and name.casefold() == ref['path'].casefold() for name in self.files):
            raise ValueError('Artifact references name the same file differently: ' + ref['path'])
        if not _sha(ref['sha256']) or not path.is_file() or file_hash(path) != ref['sha256']:
            raise ValueError('Missing or changed artifact: ' + ref['path'])
        old = self.files.get(ref['path'])
        if old is not None and old[1] != ref['sha256']:
            raise ValueError('Conflicting artifact references')
        if any(name != ref['path'] and os.path.samefile(other, path) for name, (other, _) in self.files.items()):
            raise ValueError('Artifact references name the same file differently: ' + ref['path'])
        self.files[ref['path']] = (path, ref['sha256'])
        return path

    def quiet(self):
        from .workflow import _reservations
        if self.native['pending'] or any(not (p / 'outcome.json').exists() for p, _ in _reservations(self.root)):
            raise RuntimeError('Unresolved native operation; inspect before stage completion')


def checkpoint_ref(entry):
    return {'checkpoint_id': entry['id'], 'checkpoint_sha256': entry['checkpoint_sha256']}


def transact(root, kind, payload, expected_revision, request_id, base, build, approval=None):
    """Commit once. Retried requests recover receipts without repeating native work."""
    from .workflow import writer_guard
    from . import owner
    if kind not in KINDS:
        raise ValueError('Unknown coordination operation')
    identifier(request_id)
    payload = copy.deepcopy(payload)
    request_hash = digest({'kind': kind, 'payload': payload})
    with writer_guard(root):
        native = Continuity(root).status()
        events = read(root)
        for event in events:
            if event['request_id'] == request_id:
                if event['request_hash'] != request_hash:
                    raise ValueError('Request ID reused with different content')
                return {'status': 'ALREADY_COMMITTED', 'revision': event['id'],
                        'current_revision': events[-1]['id'], 'result': event['result']}
        owner_approval = owner.require(kind, payload, request_hash, approval)
        previous = events[-1]['id'] if events else 'none'
        if expected_revision != previous:
            raise ValueError('Stale coordination revision; resume before continuing')
        context = Context(root, native, events, base)
        result = build(context, copy.deepcopy(payload))
        if owner_approval is not None:
            result = {**result, 'owner_approval': owner_approval}
        canonical(result)
        event = {'schema': 'dcc.coordination.event.v1', 'kind': kind, 'request_id': request_id,
                 'request_hash': request_hash, 'previous': previous, 'project_sha256': file_hash(Path(root) / 'project.json'),
                 'created': now(), 'payload': payload, 'result': result}
        # Validate everything before creating the exclusive bundle. A partial write remains visible.
        directory = _plain(Path(root) / 'coordination' / 'events' / f'{len(events) + 1:06d}')
        directory.mkdir(parents=True, exist_ok=False)
        for name, (source, sha) in context.files.items():
            copy_verified(source, relative(directory / 'artifacts', name), sha,
                          'Source changed during coordination publication; inspect partial event')
        _write(directory / 'event.json', _json_bytes(event))
        inventory = {p.relative_to(directory).as_posix(): file_hash(p) for p in directory.rglob('*') if p.is_file()}
        _write(directory / 'manifest.json', _json_bytes({'schema': 'dcc.coordination.manifest.v1',
               'sequence': len(events) + 1, 'files': inventory}))
        revision = file_hash(directory / 'manifest.json')
        return {'status': 'COMMITTED', 'revision': revision, 'current_revision': revision, 'result': result}
