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
        self.async_operations = {}
        self.async_cleanup = set()

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
        # Failure before acquire/copy is definitive; after that point keep uncertainty.
        try:
            scene, current, before = self.preflight(payload)
        except (ValueError, OSError, RuntimeError) as exc:
            return {'state': 'REFUSED_BEFORE_MUTATION', 'request': payload, 'reason': str(exc)}
        request = payload['request']; op = request['operation_id']; folder = self.folder(op)
        self.session.acquire(op)
        write_exclusive(folder / 'live-request.json', json_bytes(request))
        write_exclusive(folder / 'live-before.json', json_bytes(current))
        self.write(op, 'PREPARING', session_id=self.session.session_id, generation=self.session.generation)
        pre = attachment.save_copy(self.session, folder / 'pre-operation.blend')
        if not attachment.equivalent(current, attachment.snapshot(scene)):
            raise ValueError('STALE_SCENE during pre-copy')
        prepared = self.session.prepare(op, digest(request), before)
        prepared.update(precopy=pre, scene=self.session.scene)
        write_exclusive(folder / 'live-prepared.json', json_bytes(prepared))
        self.write(op, 'PREPARED', precopy=pre)
        return prepared

    def preflight(self, payload):
        if set(payload) != {'request', 'fingerprint', 'snapshot'}:
            raise ValueError('Invalid job preparation')
        request = payload['request']; op = request['operation_id']; folder = self.folder(op)
        original = json.loads(reject_links(folder / 'request.json').read_text())
        if original.get('backend') != 'live' or any(request.get(k) != v for k, v in original.items()):
            raise ValueError('Job differs from managed reservation')
        if not (folder / 'reservation.json').is_file() or Path(request['output']).resolve() != (folder / 'candidate.blend').resolve():
            raise ValueError('Managed reservation or candidate path mismatch')
        if self.cancelled(op, request):
            raise ValueError('Job cancelled or expired')
        scene = attachment.scene_for(self.session.scene)
        if request['live']['recipe'] == 'capability.recipe':
            from . import recipes
            recipes.validate_managed(request,self.session.project)
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
        if self.session.active is not None:
            raise ValueError('BUSY: reconcile the active operation first')
        return scene, current, before

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
                or (self.session.project / 'execution/cancellations' / (operation_id + '.json')).exists()
                or (self.session.project / 'execution/cancel.json').exists() or time.time() >= request['deadline'])

    def run(self, operation_id):
        if operation_id in self.async_operations:
            return self.advance_async(operation_id)
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
            if request['live']['recipe']=='capability.recipe':
                from . import recipes, addons
                bundle,profile=recipes.validate_managed(request,self.session.project)
                cap=request['capability']; target=cap['requirement']['target_id']
                scope=sorted(set(sum(bundle['recipe']['coverage'].values(),[])))
                measured=recipes.measurements(scene,target,scope)
                if addons.ACTIVE_PROFILE!=digest(profile): addons.enable_profile(profile)
                addons.assert_profile(profile)
                if not attachment.equivalent(before,attachment.snapshot(scene)) or measured!=recipes.measurements(scene,target,scope):
                    raise ValueError('Provider activation changed the scene; reconcile before invoking the recipe')
                if bundle['recipe']['invocation']['completion']=='asynchronous':
                    from . import recipe_v2
                    execution=recipe_v2.start(*recipes.managed_args(request,profile,scene),
                        folder=folder / 'async-provider',cancelled=lambda:self.cancelled(operation_id,request),
                        operation_id=operation_id)
                    self.async_operations[operation_id]=(execution,request,prepared['generation'])
                    return self.advance_async(operation_id)
                output=recipes.apply(*recipes.managed_args(request,profile,scene))
                write_exclusive(folder / 'capability-output.json',json_bytes(output))
            else:
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

    def advance_async(self, operation_id):
        execution,request,generation=self.async_operations[operation_id]
        folder=self.folder(operation_id)
        try:
            if self.session.generation!=generation or self.session.active!=operation_id:
                raise ValueError('Asynchronous session generation or reservation changed')
            status=execution.step()
            if status['state']=='PENDING':
                self.write(operation_id,'RUNNING',phase=status['phase'],progress=status.get('progress'),
                    target_scope=request['live']['target'],provider_operation=status['operation_id'])
                # The original timer callback returns this interval; provider timers
                # and UI events can run before the next lifecycle step.
                return status['poll_interval']
            if status['state']!='SUCCEEDED':
                self.write(operation_id,'NEEDS_RECONCILIATION',provider_state=status['state'],
                    error=status.get('error',status.get('reason','Provider did not finish')))
                return None
            write_exclusive(folder / 'capability-output.json',json_bytes(status['result']))
            scene=attachment.scene_for(self.session.scene)
            candidate=attachment.save_copy(self.session,request['output'])
            captured=attachment.snapshot(scene)
            write_exclusive(folder / 'live-snapshot.json',json_bytes(captured))
            state='NEEDS_RECONCILIATION' if self.cancelled(operation_id,request) else 'SAVED'
            self.write(operation_id,state,candidate=candidate['path'],sha256=candidate['sha256'],
                fingerprint=attachment.fingerprint(captured),snapshot=str(folder / 'live-snapshot.json'),
                inventory=inventory(scene),scene=scene.name,cancellation_requested=state!='SAVED')
        except Exception as exc:
            self.write(operation_id,'NEEDS_RECONCILIATION',error=str(exc),error_type=type(exc).__name__)
        return None

    def cancel(self, operation_id):
        path = self.folder(operation_id) / 'live-cancel.json'
        if not path.exists():
            write_exclusive(path, json_bytes({'operation_id': operation_id}))
        retained = self.async_operations.get(operation_id)
        if (retained is not None and not getattr(retained[0], 'closed', False)
                and self.status(operation_id)['state'] == 'NEEDS_RECONCILIATION'
                and operation_id not in self.async_cleanup):
            self.async_cleanup.add(operation_id)
            bpy.app.timers.register(lambda: self.stop_async(operation_id), first_interval=.01)
        return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED'}

    def stop_async(self, operation_id):
        """Separate explicit cleanup timer; it never publishes or releases the job."""
        try:
            execution, request, generation = self.async_operations[operation_id]
            if self.session.generation != generation or self.session.active != operation_id:
                raise ValueError('Provider cleanup session or reservation changed')
            execution.request_stop()
            status = execution.confirm_stopped()
            self.write(operation_id, 'NEEDS_RECONCILIATION', termination=status['state'])
            if status['state'] == 'PENDING':
                return status['poll_interval']
        except Exception as exc:
            self.write(operation_id, 'NEEDS_RECONCILIATION', termination='UNKNOWN', error=str(exc), error_type=type(exc).__name__)
        self.async_cleanup.discard(operation_id)
        return None

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
        request=json.loads(reject_links(self.folder(op) / 'live-request.json').read_text())
        if request['live']['recipe']=='capability.recipe':
            from . import recipes
            _,profile=recipes.validate_managed(request,self.session.project)
            recipes.verify(*recipes.managed_args(request,profile,scene),
                           json.loads(reject_links(self.folder(op) / 'capability-output.json').read_text()))
        return status

    def acknowledge(self, payload):
        status = self.check(payload)
        op = payload['operation_id']
        self.write(op, 'PUBLISHED', checkpoint=payload['checkpoint'])
        if self.session.active == op:
            self.session.release(op)
        elif self.session.active is not None:
            raise ValueError('Another operation is active')
        return {'state': 'READY', 'fingerprint': status['fingerprint'], 'generation': self.session.generation}
