"""Explicit recovery preserves current work before opening a separate restored working file."""
import json
import uuid
from pathlib import Path

import bpy
from . import attachment
try:
    from .files import copy_verified, file_hash, json_bytes, reject_links, write_exclusive
    from .adoption_inventory_blender import inventory
except ModuleNotFoundError:
    from dcc_harness.files import copy_verified, file_hash, json_bytes, reject_links, write_exclusive
    from dcc_harness.adoption_inventory_blender import inventory


def capture(jobs, payload):
    # Only this read-only region can issue a definitive no-mutation refusal.
    # Every exception after destination creation remains an uncertain outcome.
    try:
        if set(payload) != {'operation_id', 'decision', 'expected_fingerprint', 'attempt_id'}:
            raise ValueError('Explicit recovery decision and current fingerprint required')
        if str(uuid.UUID(payload['attempt_id'])) != payload['attempt_id']:
            raise ValueError('Canonical recovery attempt UUID required')
        op, decision = payload['operation_id'], payload['decision']
        if decision not in ('keep-current', 'restore-precopy'):
            raise ValueError('Unsupported recovery decision')
        session, folder = jobs.session, jobs.folder(op)
        state = jobs.status(op)
        if ((state['state'] in ('RUNNING', 'QUEUED') and state.get('generation') == session.generation)
                or session.active not in (None, op)):
            raise ValueError('BUSY: wait for the actual native outcome before recovery')
        scene = attachment.scene_for(session.scene)
        current = attachment.snapshot(scene)
        if not attachment.matches_retained(session.project,payload['expected_fingerprint'],current):
            raise ValueError('STALE_SCENE: later edits must be inspected before recovery')
        if decision == 'restore-precopy':
            prepared = json.loads(reject_links(folder / 'live-prepared.json').read_text())
            pre = prepared['precopy']
            if file_hash(pre['path']) != pre['sha256']:
                raise ValueError('Pre-operation copy changed; restore refused')
        archived_inventory = inventory(scene)
    except Exception as exc:
        return {'state': 'REFUSED_BEFORE_MUTATION', 'request': payload, 'reason': str(exc)}
    destination = reject_links(folder / 'recovery'); destination.mkdir(exist_ok=False)
    write_exclusive(destination / 'request.json', json_bytes(payload))
    write_exclusive(destination / 'archive-snapshot.json', json_bytes(current))
    archive = attachment.save_copy(session, destination / 'archive.blend')
    if not attachment.equivalent(current, attachment.snapshot(scene)):
        raise ValueError('STALE_SCENE: changed while archiving; nothing restored')
    target = archive
    if decision == 'restore-precopy':
        working = destination / 'restored-working.blend'
        copy_verified(pre['path'], working, pre['sha256'], 'Restore copy changed')
        write_exclusive(destination / 'restore-dispatched.json', json_bytes({'source': pre, 'working': str(working)}))
        if bpy.ops.wm.open_mainfile(filepath=str(working)) != {'FINISHED'}:
            raise RuntimeError('Restore did not finish; inspect native state')
        target = {'path': str(working), 'sha256': file_hash(working)}
        scene = attachment.scene_for(session.scene)
    restored = attachment.snapshot(scene)
    snapshot_path = destination / 'current-snapshot.json'
    write_exclusive(snapshot_path, json_bytes(restored))
    result = {'operation_id': op, 'decision': decision, 'attempt_id': payload['attempt_id'], 'archive': archive,
              'archive_snapshot': str(destination / 'archive-snapshot.json'), 'archive_inventory': archived_inventory,
              'source': target, 'snapshot': str(snapshot_path), 'fingerprint': attachment.fingerprint(restored),
              'inventory': inventory(scene), 'scene': scene.name, 'session_id': session.session_id,
              'generation': session.generation, 'working_filepath': bpy.data.filepath}
    write_exclusive(destination / 'receipt.json', json_bytes(result))
    jobs.write(op, 'RECOVERY_SAVED', recovery=str(destination / 'receipt.json'))
    return result


def acknowledge(jobs, payload):
    op = payload['operation_id']; session = jobs.session
    receipt = json.loads(reject_links(jobs.folder(op) / 'recovery/receipt.json').read_text())
    state = attachment.check(session, {'fingerprint': receipt['fingerprint'], 'snapshot': receipt['snapshot']})
    if state['generation'] != receipt['generation'] or not state['matches']:
        raise ValueError('LIVE_DIVERGED during recovery verification')
    if session.active == op:
        session.release(op)
    elif session.active is not None:
        raise ValueError('Another operation is active')
    jobs.write(op, 'RECONCILED', decision=receipt['decision'])
    return {'state': 'READY'}
