"""Everyday entry points over the existing continuity store.

Reservations serialize cooperating callers. They do not intercept MCP, launch
agents, authenticate observations, or prevent manual edits in Blender.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import uuid

from .continuity import Continuity, _load_observation, _plain, _mapping
from .continuity_checks import evaluate_stage, validate_contract
from .evidence import digest, evaluate, file_hash, read_json, write_json
from .project import now


@contextmanager
def writer_guard(root):
    """Short exclusive metadata lock; a crash leaves an explicit inspection stop."""
    root = _plain(root)
    root.mkdir(parents=True, exist_ok=True)
    path = _plain(root / 'workflow.lock')
    try:
        stream = path.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise RuntimeError('Workflow lock exists; inspect the owner and native outcome before recovery') from exc
    try:
        with stream:
            json.dump({'pid': os.getpid(), 'created': now()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        path.unlink()


def _clean_observation(observation, checkpoint):
    obs = _load_observation(_plain(observation), _plain(checkpoint))
    if obs.get('native_dirty') is not False:
        raise ValueError('Observe a saved, clean native checkpoint before continuing')
    return obs


def start(root, checkpoint, observation, brief, decisions, handoff=None):
    _clean_observation(observation, checkpoint)
    with writer_guard(root):
        Continuity(root).initialize(checkpoint, observation, brief, decisions, handoff=handoff)
    return resume(root)


def _reservations(root):
    folder = _plain(Path(root) / 'edits')
    result = []
    if folder.exists():
        for path in sorted(folder.iterdir()):
            path = _plain(path)
            if not path.is_dir() or not (path / 'request.json').is_file():
                raise RuntimeError('Partial edit reservation; inspect before new writes')
            request = read_json(_plain(path / 'request.json'))
            for name, sha in request['files'].items():
                if name not in ('script.py', 'contract.json') or file_hash(_plain(path / name)) != sha:
                    raise ValueError('Reserved edit inputs changed')
            if set(request['files']) != {'script.py', 'contract.json'}:
                raise ValueError('Incomplete reserved edit inputs')
            result.append((path, request))
    return result


def resume(root, focus=()):
    store = Continuity(root)
    state = store.status()
    active = state['active']
    obs = read_json(active['observation'])
    reservations = _reservations(store.root)
    unresolved = [str(p) for p, _ in reservations if not (p / 'outcome.json').exists()]
    recent_edits = []
    for path, request in reservations:
        outcome = read_json(_plain(path / 'outcome.json')) if (path / 'outcome.json').exists() else None
        recent_edits.append({'edit': path.name, 'created': request['created'], 'label': request['label'],
                             'status': outcome['status'] if outcome else 'UNRESOLVED',
                             'failures': outcome.get('failures', []) if outcome else [], 'path': str(path)})
    recent_edits.sort(key=lambda e: (e['created'], e['edit']))
    lock_exists = (store.root / 'workflow.lock').exists()
    selected = {}
    for iid in focus:
        if iid not in obs['objects']:
            raise ValueError('Unknown focus object ID: ' + iid)
        o = obs['objects'][iid]
        selected[iid] = {k: o.get(k) for k in ('name', 'type', 'asset_id', 'dimensions', 'bounds', 'material_ids', 'parent')}
        mesh = o.get('mesh_datablock')
        selected[iid]['shared_mesh_users'] = [i for i, x in obs['objects'].items()
                                             if mesh is not None and x.get('mesh_datablock') == mesh]
        selected[iid]['material_users'] = {m: state['registry']['materials'][m]['users']
                                           for m in set(o['material_ids'])}
    return {
        'schema': 'dcc.resume.v1', 'project': str(store.root), 'active': active,
        'status': 'RECONCILE' if state['pending'] or unresolved or lock_exists else 'READY_FOR_INSPECTION',
        'brief': state['brief'], 'decisions': state['decisions'],
        'handoff': Path(active['handoff']).read_text(encoding='utf-8'),
        'pending': state['pending'], 'unresolved_edits': unresolved, 'metadata_lock': lock_exists,
        'recent_edits': recent_edits[-5:],
        'recent_steps': [{'step_id': h['step_id'], 'report_passed': h['report_passed']}
                         for h in state['task_history'][-5:]],
        'counts': {'objects': len(obs['objects']), 'materials': len(obs['materials']),
                   'assets': len(state['registry']['assets']),
                   'triangles': sum(o.get('triangles', 0) for o in obs['objects'].values())},
        'focus': selected, 'coverage': obs['coverage'],
        'next_action': 'Inspect unresolved outcomes; do not replay' if state['pending'] or unresolved or lock_exists
                       else 'Inspect the saved checkpoint and scope a contract before begin-edit',
        'limits': 'Saved-file packet only; live scene freshness and artistic acceptance are not established. '
                  'Direct MCP writes and legacy APIs bypass workflow reservations.'}


def review(root, focus=()):
    packet = resume(root, focus)
    bundle = Path(packet['active']['checkpoint']).parent
    check_path = bundle / 'check.json'
    check = read_json(check_path) if check_path.exists() else None
    packet['last_native_check'] = None if check is None else {
        'path': str(check_path), 'passed': check['passed'], 'failures': check['failures'],
        'checked_targets': check['checked_targets']}
    if check is not None and 'external_revision' in check:
        revision = check['external_revision']
        packet['external_revision'] = {'preview_sha256': revision['preview_sha256'],
            'note': revision['preview_manifest']['note'], 'review_note': revision['review_note'],
            'review_attribution': revision['review_attribution']}
    packet['artistic_acceptance'] = 'not_evaluated'
    packet['visual_review'] = 'Inspect checkpoint-bound whole-scene and detail renders; this command does not grade images.'
    return packet


def begin_edit(root, expected_parent, current, observation, script, contract, label):
    if not isinstance(label, str) or not label.strip():
        raise ValueError('Edit label is required')
    current, script, contract = map(_plain, (current, script, contract))
    if not script.is_file() or not script.stat().st_size:
        raise ValueError('An immutable nonempty script is required')
    rules = read_json(contract)
    validate_contract(rules)
    source_script_sha = file_hash(script)
    fresh = _clean_observation(observation, current)
    evaluate(fresh, rules['spec'])  # Validate supported spec syntax; missing future deliverables may fail now.
    with writer_guard(root):
        packet = resume(root)
        # The current caller owns this short metadata lock.
        if packet['pending'] or packet['unresolved_edits']:
            raise RuntimeError('Unresolved edit; inspect and reconcile before another write')
        active = packet['active']
        if label in {h['step_id'] for h in Continuity(root).status()['task_history']}:
            raise ValueError('Edit label has already been published; choose a new step ID')
        if expected_parent != active['id']:
            raise ValueError('Stale parent; resume the current project')
        if file_hash(current) != active['checkpoint_sha256']:
            raise ValueError('Current saved file differs from the accepted checkpoint; adopt external edits explicitly')
        baseline = read_json(active['observation'])
        required = next(iter(baseline['objects']))
        unchanged = evaluate_stage(baseline, fresh, {
            'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': {required: {}}},
            'allowed_new_prefixes': []})
        if not unchanged['passed']:
            raise ValueError('Fresh observation differs from the accepted baseline')
        edit = Path(root).absolute() / 'edits' / str(uuid.uuid4())
        edit.mkdir(parents=True)
        for src, name in ((script, 'script.py'), (contract, 'contract.json')):
            shutil.copyfile(src, edit / name)
            if file_hash(src) != file_hash(edit / name):
                raise ValueError('Edit input changed while reserving; inspect partial reservation')
        if digest(read_json(edit / 'contract.json')) != digest(rules) or file_hash(edit / 'script.py') != source_script_sha:
            raise ValueError('Edit input changed since validation; inspect partial reservation')
        request = {'schema': 'dcc.edit.v1', 'created': now(), 'expected_parent': expected_parent,
                   'label': label, 'checkpoint_sha256': active['checkpoint_sha256'],
                   'files': {n: file_hash(edit / n) for n in ('script.py', 'contract.json')}}
        write_json(edit / 'request.json', request)
        operation = Continuity(root).project.begin(label, edit / 'script.py')
        write_json(edit / 'operation.json', {'id': operation})
    return {'edit': edit.name, 'operation': operation, 'script': str(edit / 'script.py'),
            'contract': str(edit / 'contract.json'), 'status': 'RESERVED_NOT_EXECUTED',
            'next_action': 'Execute the retained script once against an owned copy; save and observe the result.'}


def finish_edit(root, edit_id, checkpoint, observation, handoff, updates, *, reconciled=False, reject_reason=None):
    if str(uuid.UUID(edit_id)) != edit_id:
        raise ValueError('Invalid edit ID')
    _mapping(updates, 'Decision updates')
    if reject_reason is not None and (not isinstance(reject_reason, str) or not reject_reason.strip()):
        raise ValueError('Visual rejection requires a nonempty reason')
    obs = _clean_observation(observation, checkpoint)
    handoff = _plain(handoff)
    if not handoff.read_text(encoding='utf-8').strip():
        raise ValueError('Handoff is required')
    with writer_guard(root):
        store = Continuity(root)
        state = store.status()
        records = {p.name: (p, r) for p, r in _reservations(store.root)}
        edit, request = records[edit_id]
        if (edit / 'outcome.json').exists() or (edit / 'check.json').exists():
            raise RuntimeError('Edit outcome already recorded or partial; inspect, do not replay')
        if state['active']['id'] != request['expected_parent']:
            raise ValueError('Stale edit parent')
        operation = read_json(_plain(edit / 'operation.json'))['id']
        if [e['id'] for e in state['pending']] != [operation]:
            raise RuntimeError('Reservation does not match the pending operation')
        before = read_json(state['active']['observation'])
        check = evaluate_stage(before, obs, read_json(edit / 'contract.json'))
        write_json(edit / 'check.json', check)
        write_json(edit / 'native-outcome.json', {'checkpoint': str(Path(checkpoint).resolve()),
                   'checkpoint_sha256': file_hash(checkpoint), 'observation_sha256': file_hash(observation),
                   'check_sha256': file_hash(edit / 'check.json'), 'passed': check['passed']})
        store.project.finish(operation, edit / 'native-outcome.json', reconciled=reconciled)
        accepted = None
        if check['passed'] and reject_reason is None:
            accepted = store.publish(request['label'], request['expected_parent'], checkpoint, observation,
                                     handoff, updates, edit / 'check.json')['active']
        outcome = {'schema': 'dcc.edit.outcome.v1', 'passed': accepted is not None,
                   'native_check_passed': check['passed'], 'review_rejection': reject_reason,
                   'status': 'PUBLISHED' if accepted else ('REJECTED_VISUAL' if check['passed'] and reject_reason else 'REJECTED_RETAINED'),
                   'active': accepted or state['active'], 'failures': check['failures'] + ([reject_reason] if reject_reason else []),
                   'artistic_acceptance': 'not_evaluated'}
        write_json(edit / 'outcome.json', outcome)
    return outcome
