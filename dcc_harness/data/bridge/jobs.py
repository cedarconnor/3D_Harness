"""Main-thread jobs with durable outcomes and cooperative cancellation."""
import json
import os
from pathlib import Path
import time
import uuid

import bpy
from . import attachment, operations
try:
    from .files import file_hash, json_bytes, reject_links, write_exclusive
    from .identity import digest
    from .adoption_inventory_blender import inventory
except ModuleNotFoundError:
    from dcc_harness.files import file_hash, json_bytes, reject_links, write_exclusive
    from dcc_harness.identity import digest
    from dcc_harness.adoption_inventory_blender import inventory


class Jobs:
    def __init__(self, session):
        self.session = session

    def folder(self, operation_id):
        if str(uuid.UUID(operation_id)) != operation_id or self.session.project is None:
            raise ValueError('Invalid operation or unbound session')
        return reject_links(self.session.project / 'execution/operations' / operation_id)

    def status(self, operation_id):
        path = self.folder(operation_id) / 'live-status.json'
        if not path.exists():
            return {'operation_id': operation_id, 'state': 'NEEDS_RECONCILIATION'}
        return json.loads(reject_links(path).read_text())

    def write(self, operation_id, state, **values):
        folder = self.folder(operation_id)
        previous = self.status(operation_id)
        result = {**previous, **values, 'operation_id': operation_id, 'state': state,
                  'sequence': previous.get('sequence', 0) + 1, 'updated_at': time.time()}
        history = folder / 'live-history'; history.mkdir(exist_ok=True)
        write_exclusive(history / ('%06d.json' % result['sequence']), json_bytes(result))
        temporary = folder / ('live-status.' + uuid.uuid4().hex + '.tmp')
        write_exclusive(temporary, json_bytes(result))
        os.replace(temporary, reject_links(folder / 'live-status.json'))
        return result

    def prepare(self, payload):
        if set(payload) != {'request', 'fingerprint', 'snapshot'}:
            raise ValueError('Invalid job preparation')
        request = payload['request']; op = request['operation_id']; folder = self.folder(op)
        original = json.loads(reject_links(folder / 'request.json').read_text())
        if original.get('backend') != 'live' or any(request.get(k) != v for k, v in original.items()):
            raise ValueError('Job differs from managed reservation')
        if not (folder / 'reservation.json').is_file() or Path(request['output']).resolve() != (folder / 'candidate.blend').resolve():
            raise ValueError('Managed reservation or candidate path mismatch')
        if time.time() >= request['deadline'] or (self.session.project / 'execution/cancel.json').exists():
            raise ValueError('Job cancelled or expired')
        scene = attachment.scene_for(self.session.scene)
        if request['live']['recipe'] == 'node.asset':
            source = reject_links(request['live']['parameters']['path']).resolve()
            reference = request.get('asset_qualification', {})
            if not source.is_relative_to(self.session.workspace) or Path(reference.get('path', '')).resolve() != (folder / 'asset-qualification.json').resolve():
                raise ValueError('Node asset or qualification escapes managed scope')
            operations.load_qualification(reference, request['live']['parameters'])
        operations.prepare(scene, request['live'])
        if not attachment.check(self.session, payload)['matches']:
            raise ValueError('LIVE_DIVERGED: current scene is not the accepted checkpoint')
        current = attachment.snapshot(scene); before = attachment.fingerprint(current)
        self.session.acquire(op)
        # Immutable reservation before any save or edit; an interrupted prepare is never replayed.
        write_exclusive(folder / 'live-request.json', json_bytes(request))
        write_exclusive(folder / 'live-before.json', json_bytes(current))
        self.write(op, 'PREPARING', session_id=self.session.session_id, generation=self.session.generation)
        pre = attachment.save_copy(self.session, folder / 'pre-operation.blend')
        if not attachment.equivalent(current, attachment.snapshot(scene)):
            raise ValueError('STALE_SCENE during pre-copy')
        prepared = self.session.prepare(op, digest(request), before)
        prepared.update(precopy=pre, scene=self.session.scene)
        # Token payload retained by Session remains separate from this artifact metadata.
        write_exclusive(folder / 'live-prepared.json', json_bytes(prepared))
        self.write(op, 'PREPARED', precopy=pre)
        return prepared

    def submit(self, payload):
        if set(payload) != {'operation_id', 'prepared'}:
            raise ValueError('Invalid job dispatch')
        op = payload['operation_id']; folder = self.folder(op)
        if self.session.active != op:
            raise ValueError('Active operation mismatch')
        prepared = payload['prepared']
        if prepared != json.loads(reject_links(folder / 'live-prepared.json').read_text()):
            raise ValueError('Prepared artifact changed')
        request = json.loads(reject_links(folder / 'live-request.json').read_text())
        if self.status(op)['state'] != 'PREPARED':
            raise ValueError('Job already submitted; inspect status without replay')
        scene = attachment.scene_for(self.session.scene)
        token = {k: v for k, v in prepared.items() if k not in ('precopy', 'scene')}
        before = json.loads(reject_links(folder / 'live-before.json').read_text())
        if attachment.fingerprint(before) != prepared['fingerprint'] or not attachment.equivalent(before, attachment.snapshot(scene)):
            raise ValueError('STALE_SCENE: prepared state changed')
        self.session.consume(token, digest(request), prepared['fingerprint'])
        if not (folder / 'dispatched.json').exists():
            raise ValueError('Managed dispatch marker is missing')
        write_exclusive(folder / 'live-dispatched.json', json_bytes({'operation_id': op, 'request_hash': digest(request)}))
        self.write(op, 'QUEUED')
        bpy.app.timers.register(lambda: self.run(op), first_interval=.1)
        return op

    def cancelled(self, operation_id, request):
        return ((self.folder(operation_id) / 'live-cancel.json').exists()
                or (self.session.project / 'execution/cancel.json').exists() or time.time() >= request['deadline'])

    def run(self, operation_id):
        folder = self.folder(operation_id)
        request = json.loads((folder / 'live-request.json').read_text())
        prepared = json.loads((folder / 'live-prepared.json').read_text())
        try:
            if self.cancelled(operation_id, request):
                self.write(operation_id, 'CANCELLED', mutation_started=False)
                return None
            scene = attachment.scene_for(self.session.scene)
            before = json.loads(reject_links(folder / 'live-before.json').read_text())
            if (prepared['generation'] != self.session.generation
                    or prepared['expires_at'] <= time.time() or attachment.fingerprint(before) != prepared['fingerprint']
                    or not attachment.equivalent(before, attachment.snapshot(scene))):
                raise ValueError('STALE_SCENE: queued preparation is no longer current')
            self.write(operation_id, 'RUNNING', mutation_started=True)
            operations.execute_step(scene, request['live'])
            candidate = attachment.save_copy(self.session, request['output'])
            captured = attachment.snapshot(scene)
            write_exclusive(folder / 'live-snapshot.json', json_bytes(captured))
            state = 'NEEDS_RECONCILIATION' if self.cancelled(operation_id, request) else 'SAVED'
            self.write(operation_id, state, candidate=candidate['path'], sha256=candidate['sha256'],
                       fingerprint=attachment.fingerprint(captured), snapshot=str(folder / 'live-snapshot.json'),
                       inventory=inventory(scene), scene=scene.name,
                       cancellation_requested=state != 'SAVED')
        except Exception as exc:
            self.write(operation_id, 'NEEDS_RECONCILIATION', error=str(exc), error_type=type(exc).__name__)
        return None

    def cancel(self, operation_id):
        path = self.folder(operation_id) / 'live-cancel.json'
        if not path.exists():
            write_exclusive(path, json_bytes({'operation_id': operation_id}))
        return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED'}

    def check(self, payload):
        op = payload['operation_id']; status = self.status(op)
        if status['state'] not in ('SAVED', 'VERIFIED', 'PUBLISHED'):
            raise ValueError('Live job does not have a saved candidate')
        scene = attachment.scene_for(self.session.scene)
        current = attachment.check(self.session, {'fingerprint': status['fingerprint'], 'snapshot': status['snapshot']})
        if (status['generation'] != self.session.generation or status.get('session_id') != self.session.session_id
                or not current['matches']):
            raise ValueError('LIVE_DIVERGED: scene changed after candidate save')
        if file_hash(status['candidate']) != status['sha256']:
            raise ValueError('Candidate changed after save')
        return status

    def acknowledge(self, payload):
        status = self.check(payload)
        op = payload['operation_id']
        self.write(op, 'PUBLISHED', checkpoint=payload['checkpoint'])
        self.session.release(op)
        return {'state': 'READY', 'fingerprint': status['fingerprint'], 'generation': self.session.generation}
