"""Managed execution shared by CLI and future transports.

One immutable run policy, one in-flight edit, and no automatic replay of an
ambiguous dispatch. The calling agent supplies scripts and stage evidence.
This is an application boundary for trusted local scripts, not a Python sandbox.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import os
import time
import uuid

from . import coordination as c, environment_workflow as ew, workflow
from .continuity import Continuity
from .evidence import digest, file_hash, finite_number, read_json, write_json
from .files import reject_links, copy_verified
from .native import run_worker
from .execution_backends import make_backend
from .live_contracts import validate_operation

_permit = ContextVar('managed_execution_root', default=None)
_stage_context = ContextVar('managed_execution_stage', default=None)
_publication_guard = ContextVar('native_publication_guard', default=None)
WORKER = Path(__file__).with_name('_execution_blender.py')
OBSERVER = Path(__file__).with_name('_observe_blender.py')


def _folder(root):
    return reject_links(Path(root).absolute() / 'execution')


def configuration(root):
    folder = _folder(root)
    if not folder.exists():
        return None
    config = read_json(reject_links(folder / 'run.json'))
    if config.get('schema') not in ('dcc.execution.run.v1', 'dcc.execution.run.v2') or config.get('mode') not in ('autonomous', 'approval_gated'):
        raise ValueError('Invalid managed execution configuration')
    if config['schema'] == 'dcc.execution.run.v2' and config.get('backend') not in ('background', 'live'):
        raise ValueError('Invalid managed execution backend')
    return config


def require_service(root):
    if _folder(root).exists() and _permit.get() != str(Path(root).resolve()):
        raise RuntimeError('Use the managed execution service for this project')


@contextmanager
def _authorized(root, stage=None):
    token = _permit.set(str(Path(root).resolve()))
    stage_token = _stage_context.set(stage)
    try:
        yield
    finally:
        _permit.reset(token)
        _stage_context.reset(stage_token)


def check_publication(root):
    """Recheck policy under the workflow writer lock, just before publication."""
    config = configuration(root)
    if config is None:
        return
    require_service(root)
    if (_folder(root) / 'cancel.json').exists() or time.time() >= config['deadline']:
        raise RuntimeError('Run cancelled or execution time budget exhausted')
    ctx = c.Context(root, Continuity(root).status(), c.read(root), root)
    stage = _stage_context.get()
    _, states = ew._stage(ctx, stage)
    if states[stage]['state'] in ('complete', 'inherited'):
        raise ValueError('Reopen a completed stage before executing edits')
    guard = _publication_guard.get()
    if guard is not None:
        guard()


@contextmanager
def _exclusive(root):
    """Kernel lock is released on controller death; retained operations still block replay."""
    path = reject_links(_folder(root) / 'controller.lock')
    with path.open('a+b') as stream:
        if path.stat().st_size == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('A managed execution controller is already active') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def create(root, mode, *, max_operations=20, seconds=3600, backend='background'):
    if mode not in ('autonomous', 'approval_gated'):
        raise ValueError('Mode must be autonomous or approval_gated')
    if backend not in ('background', 'live'):
        raise ValueError('Unknown execution backend')
    if type(max_operations) is not int or max_operations < 1:
        raise ValueError('Operation budget must be a positive integer')
    finite_number(seconds)
    if seconds <= 0:
        raise ValueError('Time budget must be positive')
    with workflow.writer_guard(root):
        native, events = Continuity(root).status(), c.read(root)
        context = c.Context(root, native, events, root)
        context.quiet()
        bound = ew._binding(context)
        if mode == 'approval_gated' and any(row['state'] in ('complete', 'inherited') for row in ew.stages(events, native).values()):
            raise ValueError('Enable approval-gated mode before completing or inheriting stages; reopen prior stages first')
        folder = _folder(root)
        folder.mkdir(exist_ok=False)
        write_json(folder / 'run.json', {'schema': 'dcc.execution.run.v2', 'backend': backend, 'id': str(uuid.uuid4()),
                   'mode': mode, 'max_operations': max_operations, 'deadline': time.time() + seconds,
                   'binding': bound['id'], 'runtime': ew.runtime_stamp(), 'initial_checkpoint': native['active']['id']})
    return status(root)


def _operations(root):
    parent = reject_links(_folder(root) / 'operations')
    return sorted(parent.iterdir()) if parent.exists() else []


def _outcome(folder):
    request = read_json(reject_links(folder / 'request.json'))
    for name, sha in request['files'].items():
        if file_hash(reject_links(folder / name)) != sha:
            raise ValueError('Retained execution input changed: ' + name)
    path = reject_links(folder / 'outcome.json')
    if path.exists():
        return read_json(path)
    return {'operation_id': folder.name, 'status': 'NEEDS_RECONCILIATION',
            'reason': 'In flight or interrupted. Inspect; never redispatch this operation ID.'}


def status(root):
    config = configuration(root)
    if config is None:
        raise ValueError('No managed execution run')
    operations = [_outcome(reject_links(p)) for p in _operations(root)]
    native, events = Continuity(root).status(), c.read(root)
    stages = ew.stages(events, native)
    state = ('CANCELLED' if (_folder(root) / 'cancel.json').exists() else
             'NEEDS_RECONCILIATION' if any(o['status'] == 'NEEDS_RECONCILIATION' for o in operations) else
             'COMPLETE' if stages and all(s['state'] == 'complete' for s in stages.values()) else
             'BUDGET_EXHAUSTED' if time.time() >= config['deadline'] or len(operations) >= config['max_operations'] else
             'AWAITING_APPROVAL' if config['mode'] == 'approval_gated' and any(s['state'] == 'awaiting_review' for s in stages.values()) else 'READY')
    live_state = {}
    if config.get('backend') == 'live':
        from .live import read_binding
        try:
            live_state = {'live_state': read_binding(root)['state'], 'alignment': 'Use live-status for current scene comparison'}
        except (OSError, ValueError):
            live_state = {'live_state': 'UNBOUND', 'alignment': 'No verified live binding'}
        if live_state['live_state'] != 'READY' and state in ('READY', 'COMPLETE', 'AWAITING_APPROVAL'):
            state = live_state['live_state']
    return {'schema': 'dcc.execution.status.v1', 'status': state, 'run': config, 'operations': operations, **live_state,
            'stages': list(stages.values()), 'active': c.checkpoint_ref(native['active']),
            'artistic_acceptance': 'not_evaluated'}


def cancel(root):
    if configuration(root) is None:
        raise ValueError('No managed execution run')
    try:
        write_json(_folder(root) / 'cancel.json', {'requested_at': time.time()})
    except FileExistsError:
        pass
    return {'status': 'CANCEL_REQUESTED'}


def submit(root, payload, base, *, review=None):
    """Submit evidence, then attempt agent completion only in autonomous mode.

    The client supplies non-default answers and visual evidence. Failed evidence
    never advances a stage; this method does not synthesize artist acceptance.
    """
    config = configuration(root)
    if config is None:
        raise ValueError('Create a managed run first')
    events = c.read(root)
    states = ew.stages(events, Continuity(root).status())
    row = states.get(payload.get('stage_id'), {})
    previous = row.get('submission_id')
    if row.get('state') == 'complete':
        receipt = next(e for e in events if e['id'] == row['receipt_id'])
        previous = receipt['result']['submission_id']
    candidate = next((e for e in events if e['id'] == previous and e['payload'] == payload), None)
    # A retry resumes the active review cycle. Reopening (even with identical
    # evidence) is a new intent and must receive a new submission and approval.
    request = candidate['request_id'] if candidate else str(uuid.uuid5(uuid.UUID(config['id']),
                'submit:' + events[-1]['id'] + ':' + digest(payload)))
    submitted = ew.apply(root, 'stage.submit', payload, events[-1]['id'], request, base)
    if config['mode'] == 'approval_gated':
        return {'status': 'AWAITING_APPROVAL', 'submission': submitted,
                'next_action': 'Review this submission, then use stage-complete from the owner terminal or import its review page.'}
    review = review or {'reviewer': {'role': 'agent', 'author': 'managed execution', 'reference': 'Supplied stage evidence'},
                        'verdict': 'pass', 'finding': 'Submitted evidence validated; artist acceptance not evaluated.'}
    if review['reviewer']['role'] != 'agent':
        raise ValueError('Autonomous review cannot claim the artist')
    completion = {'submission_id': submitted['revision'], 'review': review}
    request = str(uuid.uuid5(uuid.UUID(config['id']), 'complete:' + digest(completion)))
    completed = ew.apply(root, 'stage.complete', completion, submitted['revision'], request, base)
    return {'status': 'COMPLETE', 'submission': submitted, 'completion': completed}


def _admit(root, stage, expected_parent):
    config = configuration(root)
    if config is None:
        raise ValueError('Create a managed run first')
    if config['runtime'] != ew.runtime_stamp():
        raise ValueError('Managed run pins another runtime; use its installed version')
    if (_folder(root) / 'cancel.json').exists():
        raise RuntimeError('Run cancelled')
    operations = _operations(root)
    if any(not (p / 'outcome.json').exists() for p in operations):
        raise RuntimeError('Unresolved operation; reconcile before executing another edit')
    if time.time() >= config['deadline'] or len(operations) >= config['max_operations']:
        raise RuntimeError('Execution budget exhausted')
    native, events = Continuity(root).status(), c.read(root)
    context = c.Context(root, native, events, root)
    context.quiet()
    spec, states = ew._stage(context, stage)
    if states[stage]['state'] in ('complete', 'inherited'):
        raise ValueError('Reopen a completed stage before executing edits')
    if native['active']['id'] != expected_parent:
        raise ValueError('Stale parent; resume the current project')
    return native['active'], config


def execute(root, stage, operation_id, script, contract, handoff, blender, expected_parent, *, timeout=300):
    """Compatibility entry point for existing managed background scripts."""
    return execute_operation(root, {'schema': 'dcc.execution.operation.v2', 'backend': 'background',
        'stage': stage, 'operation_id': operation_id, 'script': str(script), 'contract': str(contract),
        'handoff': str(handoff), 'blender': str(blender), 'expected_parent': expected_parent, 'timeout': timeout})


def execute_operation(root, value):
    """One admission/reservation/verification/publication path for all native backends."""
    value = validate_operation(value)
    stage, operation_id, timeout = value['stage'], value['operation_id'], value['timeout']
    script, contract, handoff = value['script'], value['contract'], value['handoff']
    blender, expected_parent, kind = value['blender'], value['expected_parent'], value['backend']
    config = configuration(root)
    if config is None or config.get('backend', 'background') != kind:
        raise ValueError('Operation backend does not match the managed run')
    sources = {name: reject_links(path) for name, path in [('script.py', script), ('contract.json', contract), ('handoff.md', handoff)]}
    request = {'stage': stage, 'expected_parent': expected_parent, 'blender': str(blender), 'timeout': timeout,
               'backend': kind, 'files': {name: file_hash(path) for name, path in sources.items()}}
    if 'live' in value:
        request['live'] = value['live']
    folder = reject_links(_folder(root) / 'operations' / operation_id)
    with _exclusive(root), _authorized(root, stage):
        if folder.exists():
            retained = read_json(reject_links(folder / 'request.json'))
            if retained != request:
                raise ValueError('Operation ID reused with different content')
            return _outcome(folder)
        active, config = _admit(root, stage, expected_parent)
        if kind == 'live' and request.get('live', {}).get('recipe') != 'external.capture':
            from .live import ensure_aligned
            ensure_aligned(root)
        # Validate before creating a durable reservation.
        from .continuity_checks import validate_contract
        validate_contract(read_json(sources['contract.json']))
        if not sources['script.py'].read_text(encoding='utf-8').strip() or not sources['handoff.md'].read_text(encoding='utf-8').strip():
            raise ValueError('Script and handoff must be nonempty')
        staged = reject_links(_folder(root) / 'staging' / str(uuid.uuid4()))
        staged.mkdir(parents=True, exist_ok=False)
        write_json(staged / 'request.json', request)
        for name, source in sources.items():
            copy_verified(source, staged / name, request['files'][name], 'Execution input changed during reservation')
        copy_verified(active['checkpoint'], staged / 'input.blend', active['checkpoint_sha256'], 'Checkpoint changed')
        folder.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(folder)  # Publish the complete request before any native dispatch.
        try:
            reserved = workflow.begin_edit(root, expected_parent, active['checkpoint'], active['observation'],
                                           folder / 'script.py', folder / 'contract.json', 'managed-' + operation_id)
            write_json(folder / 'reservation.json', reserved)
            deadline = min(config['deadline'], time.time() + timeout)
            cancelled = lambda: (_folder(root) / 'cancel.json').exists()
            def run(worker, action, payload):
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError('Execution time budget exhausted')
                if cancelled():
                    raise RuntimeError('Run cancelled')
                run_worker(blender, folder, worker, action, payload, timeout=remaining, cancelled=cancelled)
            candidate = folder / 'candidate.blend'
            backend = make_backend(kind, root=root, folder=folder, run=run)
            native_request = {**request, 'operation_id': operation_id,
                              'source': {'path': str(folder / 'input.blend'), 'sha256': active['checkpoint_sha256']},
                              'script': reserved['script'], 'script_sha256': request['files']['script.py'],
                              'output': str(candidate), 'deadline': deadline}
            prepared = backend.prepare(native_request)
            write_json(folder / 'prepared.json', prepared)
            if cancelled() or time.time() >= deadline:
                raise RuntimeError('Execution cancelled or expired before dispatch')
            write_json(folder / 'dispatched.json', {'operation_id': operation_id, 'backend': kind,
                                                   'request_sha256': digest(request)})
            job_id = backend.submit(native_request, prepared)
            if job_id != operation_id:
                raise ValueError('Backend returned a different operation identity')
            while True:
                if cancelled() or time.time() >= deadline:
                    backend.cancel(operation_id)
                    raise RuntimeError('Execution cancelled or expired; inspect backend outcome')
                receipt = backend.status(operation_id)
                if receipt.get('operation_id') != operation_id:
                    raise ValueError('Backend receipt identity mismatch')
                if receipt['state'] == 'SAVED':
                    if Path(receipt['candidate']).resolve() != candidate.resolve() or file_hash(candidate) != receipt['sha256']:
                        raise ValueError('Backend candidate does not match retained output')
                    break
                if receipt['state'] not in ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED'):
                    raise RuntimeError('Native operation requires reconciliation: ' + receipt['state'])
                time.sleep(.1)
            backend.verify(receipt)
            if cancelled() or time.time() >= deadline:
                raise RuntimeError('Execution cancelled or time budget exhausted before publication')
            guard = _publication_guard.set(lambda: backend.before_publish(receipt))
            try:
                updates = ({'live_external_revision': {'operation_id': operation_id, 'provenance': 'external_live_edit'}}
                           if kind == 'live' and request.get('live', {}).get('recipe') == 'external.capture' else {})
                outcome = workflow.finish_edit(root, reserved['edit'], candidate, folder / 'observation.json', folder / 'handoff.md', updates)
            finally:
                _publication_guard.reset(guard)
            result = {'operation_id': operation_id, 'status': outcome['status'], 'outcome': outcome}
            result.update(backend.published(result, receipt))
            write_json(folder / 'outcome.json', result)
            return result
        except Exception as exc:
            # No outcome receipt: this remains unresolved even if a candidate exists.
            write_json(folder / 'failure.json', {'error': str(exc), 'type': type(exc).__name__})
            return {**_outcome(folder), 'reason': str(exc)}


def reconcile(root, operation_id, *, accept=False, reason):
    """Explicitly adopt a fully observed candidate or reject an attempt; never execute a script."""
    c.identifier(operation_id); c.text(reason)
    folder = reject_links(_folder(root) / 'operations' / operation_id)
    request = read_json(reject_links(folder / 'request.json'))
    if request.get('backend') == 'live':
        raise ValueError('Use live reconciliation with an explicit current fingerprint and recovery decision')
    with _exclusive(root), _authorized(root, request['stage']):
        _outcome(folder)  # Verify retained input hashes during recovery too.
        if (folder / 'outcome.json').exists():
            return _outcome(folder)
        if not (folder / 'reservation.json').exists():
            # Recover the reservation pointer after a controller interruption.
            matches = [p for p, r in workflow._reservations(Path(root)) if r['label'] == 'managed-' + operation_id]
            if not matches:
                if accept or Continuity(root).status()['pending']:
                    raise RuntimeError('No completed reservation to reconcile; inspect project')
                result = {'operation_id': operation_id, 'status': 'REJECTED', 'reconciliation': reason, 'dispatched': False}
                write_json(folder / 'outcome.json', result)
                return result
            reserved = {'edit': matches[0].name}
        else:
            reserved = read_json(folder / 'reservation.json')
        edit = reject_links(Path(root) / 'edits' / reserved['edit'])
        if (edit / 'outcome.json').exists():
            outcome = read_json(edit / 'outcome.json')
        else:
            native = Continuity(root).status()['active']
            observed_candidate = (folder / 'observation.json').exists() and (folder / 'candidate.blend').exists()
            checkpoint = folder / 'candidate.blend' if accept or observed_candidate else native['checkpoint']
            observation = folder / 'observation.json' if accept or observed_candidate else native['observation']
            outcome = workflow.finish_edit(root, reserved['edit'], checkpoint, observation, folder / 'handoff.md', {},
                                           reconciled=True, reject_reason=None if accept else reason)
        result = {'operation_id': operation_id, 'status': outcome['status'] if outcome['passed'] else 'REJECTED',
                  'outcome': outcome, 'reconciliation': reason}
        write_json(folder / 'outcome.json', result)
        return result
