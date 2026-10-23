"""Host orchestration for explicitly paired live Blender scenes."""
from pathlib import Path
import os
import uuid

from . import blender_bridge, bootstrap, execution, workflow
from .evidence import digest, finite_number, file_hash, read_json, write_json
from .files import reject_links, write_exclusive, json_bytes
from .native import run_worker
from .live_recovery import reconcile
from .live_surface import sessions, inspect, status, cancel, execute, preview, validate_preview


def attach(root, binding, *, scene=None, expected_parent=None, brief_file=None, mode=None,
           blender=None, max_operations=20, seconds=3600):
    if not scene or mode not in ('autonomous', 'approval_gated') or not brief_file or not blender:
        raise ValueError('Attachment requires an explicit scene, brief, mode and Blender verifier')
    private = blender_bridge.descriptor(binding)
    workspace = reject_links(private['workspace']).resolve(strict=True)
    destination = reject_links(root).resolve()
    if destination == workspace or not destination.is_relative_to(workspace):
        raise ValueError('Attachment destination must stay inside the paired workspace')
    brief = reject_links(brief_file).read_text(encoding='utf-8')
    if not brief.strip():
        raise ValueError('Project brief is empty')
    request = {'session_id': private['session_id'], 'generation': private['generation'],
               'scene': scene, 'mode': mode, 'brief_sha256': digest(brief), 'blender': str(blender),
               'max_operations': max_operations, 'seconds': seconds}
    retry = False
    if destination.exists():
        if (destination / 'created.json').is_file():
            if read_json(destination / 'attach-request.json') != request:
                raise ValueError('Attachment request changed; refresh explicitly')
            result = read_json(destination / 'created.json')
            ensure_aligned(result['project'])
            return result
        if (destination / 'attach-request.json').exists():
            attempts = destination / 'attach-attempts'
            previous = sorted(attempts.glob('*.json')) if attempts.exists() else []
            if read_json(destination / 'attach-request.json') != request or not previous:
                raise RuntimeError('Incomplete attachment: inspect retained state; identity assignment will not be replayed')
            for path in previous:
                intent = read_json(reject_links(path))
                retained = blender_bridge.retained_outcome('attach_begin', intent, private)
                if not _is_refusal(retained, intent):
                    raise RuntimeError('Incomplete attachment: inspect retained state; identity assignment will not be replayed')
            retry = True
        else:
            raise ValueError('Existing projects require explicit parent and refresh; new attachment requires a fresh destination')
    if expected_parent is not None:
        raise ValueError('New attachment has no expected parent')
    if type(max_operations) is not int or max_operations < 1 or not isinstance(seconds, (int, float)) or seconds <= 0:
        raise ValueError('Positive operation and time budgets required')
    finite_number(seconds)
    def call(command, payload):
        return blender_bridge.call(command, payload, binding=binding,
                                   expected=(private['session_id'], private['generation']))
    info = call('session_describe', {})
    if scene not in info['scenes'] or info['generation'] != private['generation']:
        raise ValueError('Session scene or generation changed')
    if not retry:
        destination.mkdir(parents=True, exist_ok=False)
        write_json(destination / 'attach-request.json', request)
        write_exclusive(destination / 'brief.md', brief.encode('utf-8'))
    project = destination / 'state'
    operation_id = str(uuid.uuid4())
    payload = {'project': str(project), 'operation_id': operation_id, 'request_hash': digest(request)}
    intent = {**payload, 'scene': scene}
    attempts = reject_links(destination / 'attach-attempts'); attempts.mkdir(exist_ok=True)
    write_json(attempts / (operation_id + '.json'), intent)
    prepared = call('attach_begin', intent)
    if _is_refusal(prepared, intent):
        raise RuntimeError(prepared['reason'])
    write_json(destination / 'attach-response.json', prepared)
    saved = call('attach_apply', payload)
    # The receipt is retained by Blender before the response, and cannot be rewritten by a replay.
    if saved != read_json(destination / 'attach-saved.json') or saved['operation_id'] != operation_id:
        raise ValueError('Attachment receipt mismatch')
    # Reserve exclusively before attach_check retains snapshots under live/observations.
    # An unexpected existing directory still requires inspection, never adoption.
    live_folder = reject_links(project / 'live'); live_folder.mkdir(parents=True, exist_ok=False)
    observed = destination / 'observation'; observed.mkdir()
    run_worker(blender, observed, Path(__file__).with_name('_live_verify_blender.py'), 'verify',
               {'source': saved['baseline'], 'out': str(observed), 'scene': scene,
                'inventory': saved['inventory'], 'fingerprint': saved['fingerprint'], 'snapshot': saved['snapshot']}, timeout=60)
    state = call('attach_check', {'fingerprint': saved['fingerprint'], 'snapshot': saved['snapshot']})
    if state['generation'] != saved['generation'] or not state['matches']:
        raise ValueError('LIVE_DIVERGED: scene changed while baseline was verified')
    handoff = destination / 'handoff.md'
    write_exclusive(handoff, b'Baseline adopted from the open scene, preserving unsaved content. Metadata adoption is not artistic approval.\n')
    workflow.start(project, saved['baseline']['path'], observed / 'observation.json', brief,
                   {'provenance': 'live_metadata_adoption'}, handoff)
    bootstrap.bind_rules(str(project), destination, 'none', str(uuid.uuid4()))
    result = execution.create(project, mode, backend='live', max_operations=max_operations, seconds=seconds)
    active = workflow.resume(project)['active']
    bind = {'schema': 'dcc.live.binding.v1', 'descriptor': str(Path(binding).resolve()),
            'session_id': saved['session_id'], 'generation': saved['generation'], 'scene': scene,
            'checkpoint': active['id'], 'fingerprint': saved['fingerprint'], 'snapshot': saved['snapshot'], 'state': 'LIVE_DIVERGED'}
    write_json(live_folder / 'binding.json', bind)
    call('attach_acknowledge', {'operation_id': operation_id, 'fingerprint': saved['fingerprint'],
                               'generation': saved['generation']})
    # Immutable alignment acknowledgment keeps a failed final race distinct from historical publication.
    write_json(live_folder / 'ready.json', {'checkpoint': active['id'], 'generation': saved['generation'],
                                         'fingerprint': saved['fingerprint'], 'state': 'READY'})
    result.update(project=str(project), baseline=saved['baseline']['path'], live_state='READY',
                  source_filepath=saved['baseline']['original_filepath'])
    write_json(destination / 'created.json', result)
    return result


def ensure_aligned(root):
    folder = reject_links(Path(root) / 'live')
    binding = read_binding(root)
    ready = binding if binding['state'] == 'READY' else None
    active = workflow.resume(root)['active']
    if ready is None or active['id'] != ready['checkpoint'] or active['id'] != binding['checkpoint']:
        raise ValueError('LIVE_DIVERGED: live binding does not match the active accepted checkpoint')
    state = blender_bridge.call('attach_check', {'fingerprint': ready['fingerprint'], 'snapshot': binding['snapshot']}, binding=binding['descriptor'],
                                expected=(binding['session_id'], binding['generation']))
    if (state['session_id'] != binding['session_id'] or state['generation'] != ready['generation']
            or not state['matches'] or state['scene'] != binding['scene']):
        raise ValueError('LIVE_DIVERGED: preserve current edits and refresh or reconcile explicitly')
    return state


def _is_refusal(result, payload):
    return (isinstance(result, dict) and set(result) == {'state', 'request', 'reason'}
            and result['state'] == 'REFUSED_BEFORE_MUTATION' and result['request'] == payload
            and isinstance(result['reason'], str))


def read_binding(root):
    folder = reject_links(Path(root) / 'live')
    pointer = folder / 'current.json'
    if pointer.exists():
        reference = read_json(reject_links(pointer))
        name = str(uuid.UUID(reference['revision'])) + '.json'
        value = read_json(reject_links(folder / 'bindings' / name))
        if digest(value) != reference['sha256']:
            raise ValueError('Live binding revision changed')
        return value
    value = read_json(reject_links(folder / 'binding.json'))
    if (folder / 'ready.json').exists():
        value.update(read_json(reject_links(folder / 'ready.json')))
    return value


def write_binding(root, value):
    folder = reject_links(Path(root) / 'live')
    history = reject_links(folder / 'bindings'); history.mkdir(exist_ok=True)
    revision = str(uuid.uuid4())
    write_json(history / (revision + '.json'), value)
    temporary = folder / (revision + '.tmp')
    write_exclusive(temporary, json_bytes({'revision': revision, 'sha256': digest(value)}))
    os.replace(temporary, reject_links(folder / 'current.json'))


class LiveBackend:
    def __init__(self, root, folder, run):
        self.root, self.folder, self.run = Path(root), Path(folder), run
        self.binding = read_binding(root)

    def call(self, command, payload):
        return blender_bridge.call(command, payload, binding=self.binding['descriptor'],
                                    expected=(self.binding['session_id'], self.binding['generation']))

    def prepare(self, request):
        from .live_contracts import validate_live_recipe
        validate_live_recipe(request.get('live'))
        expected = self.binding
        if request['live']['recipe'] == 'external.capture':
            params = request['live']['parameters']
            if (self.binding['state'] != 'EXTERNAL_PENDING'
                    or params != self.binding.get('external_snapshot')):
                raise ValueError('External capture requires an explicit managed refresh')
            expected = params
        else:
            ensure_aligned(self.root)
        self.request = request
        if request['live']['recipe'] == 'node.asset':
            parameters = request['live']['parameters']
            source = reject_links(parameters['path']).resolve(strict=True)
            private = blender_bridge.descriptor(self.binding['descriptor'])
            if not source.is_relative_to(Path(private['workspace']).resolve()) or file_hash(source) != parameters['sha256']:
                raise ValueError('Node asset escapes workspace or changed')
            self.run(Path(__file__).with_name('_node_asset_probe_blender.py'), 'qualify-asset',
                     {'source': {'path': str(source), 'sha256': parameters['sha256']},
                      'group': parameters['group'], 'out': str(self.folder)})
            report = self.folder / 'asset-qualification.json'
            request['asset_qualification'] = {'path': str(report), 'sha256': file_hash(report)}
        write_binding(self.root, {**self.binding, 'state': 'BUSY', 'operation_id': request['operation_id']})
        payload = {'request': request, 'fingerprint': expected['fingerprint'], 'snapshot': expected['snapshot']}
        private = blender_bridge.descriptor(self.binding['descriptor'])
        write_json(self.folder / 'live-transport.json', {'payload': payload,
                   'private': {k: private[k] for k in ('workspace', 'session_id', 'generation')}})
        prepared = self.call('job_prepare', payload)
        if _is_refusal(prepared, payload):
            write_json(self.folder / 'live-refusal.json', prepared)
            raise RuntimeError(prepared['reason'])
        return prepared

    def recover_failure(self):
        """Close only proven pre-mutation refusals; never dispatch native work."""
        transport = self.folder / 'live-transport.json'
        if not transport.exists() or (self.folder / 'dispatched.json').exists():
            return None
        retained = read_json(transport)
        payload = retained['payload']
        path = self.folder / 'live-refusal.json'
        refusal = (read_json(path) if path.exists() else
                   blender_bridge.retained_outcome('job_prepare', payload, retained['private']))
        if not _is_refusal(refusal, payload):
            return None
        if not path.exists():
            write_json(path, refusal)
        request = read_json(self.folder / 'request.json')
        if any(payload['request'].get(k) != v for k, v in request.items()):
            raise ValueError('Refusal request differs from managed reservation')
        active = workflow.resume(self.root)['active']
        reserved = read_json(self.folder / 'reservation.json')
        edit = self.root / 'edits' / reserved['edit']
        outcome = (read_json(edit / 'outcome.json') if (edit / 'outcome.json').exists() else
                   workflow.finish_edit(self.root, reserved['edit'], active['checkpoint'], active['observation'],
                                        self.folder / 'handoff.md', {}, reconciled=True,
                                        reject_reason='Native preparation refused before mutation: ' + refusal['reason']))
        current = {**self.binding, 'state': 'LIVE_DIVERGED'}
        try:
            state = self.call('attach_check', {'fingerprint': self.binding['fingerprint'], 'snapshot': self.binding['snapshot']})
            if (state.get('matches') and state.get('session_id') == self.binding['session_id']
                    and state.get('generation') == self.binding['generation'] and state.get('scene') == self.binding['scene']):
                current['state'] = 'READY'
        except Exception:
            current['state'] = 'LIVE_STATE_UNAVAILABLE'
        write_binding(self.root, current)
        result = {'operation_id': self.folder.name, 'status': 'REJECTED', 'outcome': outcome,
                  'reason': refusal['reason'], 'mutation_started': False, 'live_state': current['state']}
        write_json(self.folder / 'outcome.json', result)
        return result

    def recover_published(self):
        """Finish alignment/receipt persistence for an already committed checkpoint."""
        reserved = self.folder / 'reservation.json'
        if not reserved.exists():
            return None
        edit = self.root / 'edits' / read_json(reserved)['edit']
        path = edit / 'outcome.json'
        if not path.exists() or read_json(path).get('status') != 'PUBLISHED':
            return None
        outcome = read_json(path)
        active = workflow.resume(self.root)['active']
        if active['id'] != outcome['active']['id']:
            raise ValueError('Published live checkpoint is no longer active; inspect retained evidence')
        receipt = read_json(self.folder / 'live-status.json')
        if receipt['operation_id'] != self.folder.name:
            raise ValueError('Live receipt operation identity changed')
        if receipt['sha256'] != active['checkpoint_sha256'] or file_hash(receipt['candidate']) != receipt['sha256']:
            raise ValueError('Live receipt does not identify the published checkpoint bytes')
        result = {'operation_id': self.folder.name, 'status': 'PUBLISHED', 'outcome': outcome}
        if self.binding['session_id'] != receipt['session_id']:
            result.update(self.realign_published(receipt, active))
        else:
            self.before_publish(receipt)  # Same-session checking/acknowledgement remains mandatory.
            result.update(self.published(result, receipt))
        request = read_json(self.folder / 'request.json')
        if 'capability' in request:
            from .capabilities import record_operation
            result['capability_receipt'] = record_operation(self.root, self.folder, result, request)
        if not (self.folder / 'outcome.json').exists():
            write_json(self.folder / 'outcome.json', result)
        elif result.get('live_state') == 'READY':
            from .execution_outcomes import recover_outcome
            recover_outcome(self.folder, result)
        return result

    def realign_published(self, receipt, active):
        """An explicitly refreshed replacement may prove the already published state."""
        from .live_snapshot import fingerprint
        reference = self.binding.get('refresh_admission')
        if not isinstance(reference, dict):
            raise ValueError('Explicit refresh admission is required for published-state alignment')
        admission_path = reject_links(reference['path']).resolve(strict=True)
        if not admission_path.is_relative_to((self.root / 'live/refreshes').resolve()) or file_hash(admission_path) != reference['sha256']:
            raise ValueError('Explicit refresh admission changed')
        admission = read_json(admission_path)
        if (admission.get('from_session_id') != receipt['session_id']
                or admission.get('session_id') != self.binding['session_id']
                or admission.get('generation') != self.binding['generation']
                or admission.get('descriptor') != self.binding['descriptor']
                or admission.get('checkpoint') != active['id'] or admission.get('scene') != receipt['scene']):
            raise ValueError('Explicit refresh does not admit this published operation')
        snapshot_path = reject_links(receipt['snapshot']).resolve(strict=True)
        if not snapshot_path.is_relative_to(self.folder.resolve()) or fingerprint(read_json(snapshot_path)) != receipt['fingerprint']:
            raise ValueError('Published live snapshot changed')
        state = self.call('attach_check', {'fingerprint': receipt['fingerprint'], 'snapshot': str(snapshot_path)})
        if 'active_operation' not in state or state['active_operation'] is not None:
            raise ValueError('BUSY: replacement session has an active native operation')
        if (state.get('matches') is not True or state.get('session_id') != self.binding['session_id']
                or state.get('generation') != self.binding['generation'] or state.get('scene') != receipt['scene']):
            raise ValueError('Published live state does not match the refreshed replacement')
        aligned = {'schema': 'dcc.live.publication-alignment.v1', 'operation_id': self.folder.name,
                   'checkpoint': active['id'], 'candidate_sha256': receipt['sha256'],
                   'snapshot': {'path': str(snapshot_path), 'sha256': file_hash(snapshot_path), 'fingerprint': receipt['fingerprint']},
                   'session_id': self.binding['session_id'], 'generation': self.binding['generation'],
                   'refresh_admission': reference, 'native_mutation': False, 'stage_approval': False}
        history = reject_links(self.folder / 'live-alignments'); history.mkdir(exist_ok=True)
        path = reject_links(history / (self.binding['session_id'] + '-' + self.binding['generation'] + '.json'))
        if path.exists():
            if read_json(path) != aligned:
                raise ValueError('Published live alignment evidence changed')
        else:
            write_json(path, aligned)
        current = {k: v for k, v in self.binding.items() if k != 'operation_id'}
        write_binding(self.root, {**current, 'state': 'READY', 'checkpoint': active['id'],
                                 'snapshot': str(snapshot_path), 'fingerprint': receipt['fingerprint']})
        return {'live_state': 'READY', 'live_alignment': {'path': str(path), 'sha256': file_hash(path)}}

    def submit(self, request, prepared):
        return self.call('job_submit', {'operation_id': request['operation_id'], 'prepared': prepared})

    def status(self, operation_id):
        if operation_id != self.folder.name:
            raise ValueError('Live operation identity mismatch')
        path = reject_links(self.folder / 'live-status.json')
        return read_json(path) if path.exists() else {'operation_id': operation_id, 'state': 'NEEDS_RECONCILIATION'}

    def cancel(self, operation_id):
        if operation_id != self.folder.name:
            raise ValueError('Live operation identity mismatch')
        path = reject_links(self.folder / 'live-cancel.json')
        try:
            write_json(path, {'operation_id': operation_id})
        except FileExistsError:
            pass
        return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED'}

    def verify(self, receipt):
        self.run(Path(__file__).with_name('_live_verify_blender.py'), 'verify',
                 {'source': {'path': receipt['candidate'], 'sha256': receipt['sha256']},
                  'out': str(self.folder), 'scene': receipt['scene'], 'inventory': receipt['inventory'],
                  'fingerprint': receipt['fingerprint'], 'snapshot': receipt['snapshot'], 'recipe': self.request['live'],
                  'asset_qualification': self.request.get('asset_qualification'),
                  **({'capability':self.request['capability']} if 'capability' in self.request else {})})

    def before_publish(self, receipt):
        checked = self.call('job_check', {'operation_id': receipt['operation_id']})
        if checked['fingerprint'] != receipt['fingerprint'] or checked['sha256'] != receipt['sha256']:
            raise ValueError('Live candidate changed before publication')

    def published(self, result, receipt):
        if result['status'] != 'PUBLISHED':
            write_binding(self.root, {**self.binding, 'state': 'NEEDS_RECONCILIATION', 'operation_id': receipt['operation_id']})
            return {'live_state': 'NEEDS_RECONCILIATION'}
        checkpoint = result['outcome']['active']['id']
        new = {**self.binding, 'checkpoint': checkpoint, 'fingerprint': receipt['fingerprint'],
               'snapshot': receipt['snapshot'], 'state': 'LIVE_DIVERGED'}
        write_binding(self.root, new)
        try:
            self.call('job_acknowledge', {'operation_id': receipt['operation_id'], 'checkpoint': checkpoint})
            write_binding(self.root, {**new, 'state': 'READY'})
            return {'live_state': 'READY'}
        except Exception as exc:
            return {'live_state': 'LIVE_DIVERGED', 'live_error': str(exc)}


def refresh(root, binding, *, expected_parent):
    """Explicitly reconnect or import measured external edits through managed execution."""
    from . import coordination as c, environment_workflow as ew
    from .continuity import Continuity
    from .continuity_checks import OBJECT_FIELDS
    from .live_snapshot import equivalent
    root = Path(root)
    config = execution.configuration(root)
    if config is None or config.get('backend') != 'live' or config['runtime'] != ew.runtime_stamp():
        raise ValueError('Refresh requires the project\'s pinned live runtime')
    private = blender_bridge.descriptor(binding)
    if not root.resolve().is_relative_to(Path(private['workspace']).resolve()):
        raise ValueError('Project is outside the paired workspace')
    with execution._exclusive(root):
        active = workflow.resume(root)['active']
        if expected_parent != active['id']:
            raise ValueError('Expected parent is stale')
        saved = read_binding(root)
        unresolved = [p for p in execution._operations(root) if not (p / 'outcome.json').exists()]
        replacement_proof = 'previous_descriptor_absent'
        if private['session_id'] != saved['session_id'] and Path(saved['descriptor']).exists():
            presence = blender_bridge.session_presence(saved['descriptor'])
            if presence != 'DEAD':
                raise ValueError('Previous paired session is present or unknown; wait or stop it before replacing the binding')
            replacement_proof = 'recorded_process_dead'
        state = blender_bridge.call('attach_rebind', {'project': str(root.resolve()), 'scene': saved['scene'],
            'allow_unresolved': bool(unresolved)}, binding=binding, expected=(private['session_id'], private['generation']))
        new = {**saved, 'descriptor': str(Path(binding).resolve()), 'generation': state['generation'],
               'session_id': state['session_id']}
        if private['session_id'] != saved['session_id']:
            admissions = reject_links(root / 'live/refreshes'); admissions.mkdir(exist_ok=True)
            path = admissions / (str(uuid.uuid4()) + '.json')
            write_json(path, {'schema': 'dcc.live.refresh-admission.v1', 'from_session_id': saved['session_id'],
                       'from_generation': saved['generation'], 'session_id': state['session_id'],
                       'generation': state['generation'], 'scene': saved['scene'], 'checkpoint': active['id'],
                       'descriptor': new['descriptor'], 'replacement_proof': replacement_proof})
            new['refresh_admission'] = {'path': str(path), 'sha256': file_hash(path)}
        if unresolved:
            write_binding(root, {**new, 'state': 'NEEDS_RECONCILIATION'})
            return {'state': 'NEEDS_RECONCILIATION', 'fingerprint': state['fingerprint'],
                    'operations': [p.name for p in unresolved], 'next_action': 'Inspect and explicitly reconcile the retained operation'}
        if equivalent(read_json(saved['snapshot']), read_json(state['snapshot'])):
            write_binding(root, {**new, 'state': 'READY'})
            return {'state': 'READY', 'checkpoint': active['id'], 'reconnected': private['session_id'] != saved['session_id']}
        current = read_json(state['snapshot'])
        if current['issues'] or not current['objects']:
            raise ValueError('External edits need explicit identity/dependency repair before import')
        write_binding(root, {**new, 'state': 'EXTERNAL_PENDING',
                            'external_snapshot': {'snapshot': state['snapshot'], 'fingerprint': state['fingerprint']}})
    # Each external import has its own normal operation reservation and consumes the run budget.
    before = read_json(active['observation'])
    operation_id = str(uuid.uuid4())
    inputs = reject_links(root / 'live/imports' / operation_id); inputs.mkdir(parents=True)
    materials, node_fields = {}, {}
    for mid, material in current['materials'].items():
        if mid not in before['materials']:
            continue
        nodes = (material.get('graph') or {}).get('nodes', [])
        values = {n['name']: n['inputs'] for n in nodes if n.get('inputs')}
        fields = {n['name']: {k: v for k, v in n.items() if k not in ('name', 'type', 'inputs')}
                  for n in nodes if set(n) - {'name', 'type', 'inputs'}}
        if values: materials[mid] = values
        if fields: node_fields[mid] = fields
    created = sorted(set(current['objects']) - set(before['objects']))
    contract = {'schema': 'dcc.continuity.contract.v1',
                'spec': {'schema': 'dcc.spec.v1', 'required': {key: {} for key in current['objects']}},
                'allowed_object_prefixes': {key: sorted(OBJECT_FIELDS) for key in before['objects']},
                'allowed_deleted_ids': sorted(set(before['objects']) - set(current['objects'])),
                'allowed_new_prefixes': created, 'allowed_material_inputs': materials,
                'allowed_material_node_fields': node_fields, 'allowed_scene_fields': sorted(current['scene'])}
    write_json(inputs / 'contract.json', contract)
    write_exclusive(inputs / 'script.py', b'# Explicit capture of external live edits; no generated native script.\n')
    write_exclusive(inputs / 'handoff.md', b'Explicit external live edit import. Prior stage decisions require review; no artistic approval is implied.\n')
    events = c.read(root)
    stage = ew._binding(c.Context(root, Continuity(root).status(), events, root))['result']['manifest']['stages'][0]['id']
    ew.apply(root, 'stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': stage,
        'reason': 'Explicit import of external live edits',
        'authority': {'role': 'agent', 'author': 'live refresh', 'reference': 'User requested refresh'}},
        events[-1]['id'], str(uuid.uuid4()), root)
    request = {'schema': 'dcc.execution.operation.v2', 'backend': 'live', 'operation_id': operation_id,
               'stage': stage, 'script': str(inputs / 'script.py'), 'contract': str(inputs / 'contract.json'),
               'handoff': str(inputs / 'handoff.md'), 'blender': read_json(root.parent / 'attach-request.json')['blender'],
               'expected_parent': expected_parent, 'timeout': 120,
               'live': {'recipe': 'external.capture', 'target': state['scene'],
                        'parameters': {'snapshot': state['snapshot'], 'fingerprint': state['fingerprint']}}}
    result = execution.execute_operation(root, request)
    from .capabilities import changes, requirements
    after=read_json(workflow.resume(root)['active']['observation'])
    return {'state': result.get('live_state', result['status']), 'operation': result,
            'capability_changes': changes(root,before,after),
            'capability_requirements': requirements(root,stage,after),
            'provenance': 'external_live_edit', 'artistic_acceptance': 'not_assessed'}
