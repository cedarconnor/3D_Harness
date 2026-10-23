"""Atomic publication recovery without replacing the original failure evidence."""
from pathlib import Path
import uuid

from .evidence import digest, file_hash, read_json, write_json
from .files import reject_links


def _bindings(folder, request):
    names = ['outcome.json', 'request.json', 'reservation.json', 'live-status.json']
    if 'capability' in request:
        names += ['capability-publication.json', 'capability-receipt.json']
    bindings = {name: file_hash(reject_links(folder / name)) for name in names}
    edit_id = read_json(folder / 'reservation.json')['edit']
    from .coordination import identifier
    identifier(edit_id)
    edit = reject_links(folder.parents[2] / 'edits' / edit_id / 'outcome.json')
    bindings['committed_edit'] = file_hash(edit)
    return bindings, read_json(edit)


def _validate(folder, record, original, request):
    bindings, committed = _bindings(folder, request)
    result = record.get('outcome')
    if (record.get('schema') != 'dcc.execution.recovered-outcome.v1'
            or record.get('bindings') != bindings or not isinstance(result, dict)
            or request.get('backend') != 'live'
            or original.get('status') != 'PUBLISHED' or committed.get('status') != 'PUBLISHED'
            or original.get('operation_id') != folder.name
            or result.get('operation_id') != folder.name or result.get('status') != 'PUBLISHED'
            or result.get('live_state') != 'READY' or result.get('outcome') != committed
            or original.get('outcome') != committed):
        raise ValueError('Recovered outcome publication linkage changed')
    native = read_json(folder / 'live-status.json')
    if (native.get('operation_id') != folder.name
            or native.get('sha256') != committed['active']['checkpoint_sha256']):
        raise ValueError('Recovered outcome native checkpoint changed')
    if 'capability' in request:
        from .capabilities import validate_receipt
        from .coordination import checkpoint_ref
        receipt = validate_receipt(read_json(folder / 'capability-receipt.json'))
        expected = {'path': str(folder / 'capability-receipt.json'),
                    'sha256': bindings['capability-receipt.json']}
        publication = read_json(folder / 'capability-publication.json')
        if (result.get('capability_receipt') != expected or receipt['operation_id'] != folder.name
                or receipt['request_sha256'] != digest(request)
                or receipt != {**publication, 'checkpoint': checkpoint_ref(committed['active'])}):
            raise ValueError('Recovered outcome capability receipt linkage changed')
        for name, sha in receipt['evidence'].items():
            if file_hash(reject_links(folder / name)) != sha:
                raise ValueError('Recovered outcome capability evidence changed')
    alignment = result.get('live_alignment')
    if alignment is not None:
        path = reject_links(alignment['path']).resolve(strict=True)
        if not path.is_relative_to((folder / 'live-alignments').resolve()) or file_hash(path) != alignment['sha256']:
            raise ValueError('Recovered outcome alignment changed')
    return result


def effective_outcome(folder, original, request):
    path = reject_links(folder / 'recovered-outcome.json')
    return _validate(folder, read_json(path), original, request) if path.exists() else original


def recover_outcome(folder, result):
    """Called under execution lock, only after successful native alignment."""
    folder = Path(folder)
    original = read_json(reject_links(folder / 'outcome.json'))
    request = read_json(reject_links(folder / 'request.json'))
    current = effective_outcome(folder, original, request)
    # Completed terminal results stay immutable and repeated reconciliation is read-only.
    if current.get('live_state') == 'READY' and ('capability' not in request or current.get('capability_receipt')):
        return current
    bindings, _ = _bindings(folder, request)
    record = {'schema': 'dcc.execution.recovered-outcome.v1', 'bindings': bindings, 'outcome': result}
    _validate(folder, record, original, request)
    staged = folder / ('recovered-outcome-' + str(uuid.uuid4()) + '.tmp')
    write_json(staged, record)
    # Interrupted staging leaves the original authoritative. Retry never replays native work.
    staged.rename(reject_links(folder / 'recovered-outcome.json'))
    return result
