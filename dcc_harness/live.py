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
    if destination.exists():
        if (destination / 'created.json').is_file():
            if read_json(destination / 'attach-request.json') != request:
                raise ValueError('Attachment request changed; refresh explicitly')
            result = read_json(destination / 'created.json')
            ensure_aligned(result['project'])
            return result
        if (destination / 'attach-request.json').exists():
            raise RuntimeError('Incomplete attachment: inspect retained state; identity assignment will not be replayed')
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
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / 'attach-request.json', request)
    write_exclusive(destination / 'brief.md', brief.encode('utf-8'))
    project = destination / 'state'
    operation_id = str(uuid.uuid4())
    payload = {'project': str(project), 'operation_id': operation_id, 'request_hash': digest(request)}
    prepared = call('attach_begin', {**payload, 'scene': scene})
    write_json(destination / 'attach-response.json', prepared)
    saved = call('attach_apply', payload)
    # The receipt is retained by Blender before the response, and cannot be rewritten by a replay.
    if saved != read_json(destination / 'attach-saved.json') or saved['operation_id'] != operation_id:
        raise ValueError('Attachment receipt mismatch')
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
    live_folder = project / 'live'; live_folder.mkdir()
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
        return self.call('job_prepare', {'request': request, 'fingerprint': expected['fingerprint'], 'snapshot': expected['snapshot']})

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
                  'asset_qualification': self.request.get('asset_qualification')})

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
        if private['session_id'] != saved['session_id'] and Path(saved['descriptor']).exists():
            raise ValueError('Previous paired session is still present; stop it before replacing the binding')
        state = blender_bridge.call('attach_rebind', {'project': str(root.resolve()), 'scene': saved['scene'],
            'allow_unresolved': bool(unresolved)}, binding=binding, expected=(private['session_id'], private['generation']))
        new = {**saved, 'descriptor': str(Path(binding).resolve()), 'generation': state['generation'],
               'session_id': state['session_id']}
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
    return {'state': result.get('live_state', result['status']), 'operation': result,
            'provenance': 'external_live_edit', 'artistic_acceptance': 'not_assessed'}
