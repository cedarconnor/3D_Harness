"""Host orchestration for explicitly paired live Blender scenes."""
from pathlib import Path
import uuid

from . import blender_bridge, bootstrap, execution, workflow
from .evidence import digest, finite_number, read_json, write_json
from .files import reject_links, write_exclusive
from .native import run_worker


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
                'inventory': saved['inventory'], 'fingerprint': saved['fingerprint']}, timeout=60)
    state = call('attach_check', {})
    if state['generation'] != saved['generation'] or state['fingerprint'] != saved['fingerprint']:
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
            'checkpoint': active['id'], 'fingerprint': saved['fingerprint'], 'state': 'LIVE_DIVERGED'}
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
    binding = read_json(reject_links(folder / 'binding.json'))
    ready = read_json(reject_links(folder / 'ready.json')) if (folder / 'ready.json').exists() else None
    active = workflow.resume(root)['active']
    if ready is None or active['id'] != ready['checkpoint'] or active['id'] != binding['checkpoint']:
        raise ValueError('LIVE_DIVERGED: live binding does not match the active accepted checkpoint')
    state = blender_bridge.call('attach_check', {}, binding=binding['descriptor'])
    if (state['session_id'] != binding['session_id'] or state['generation'] != ready['generation']
            or state['fingerprint'] != ready['fingerprint'] or state['scene'] != binding['scene']):
        raise ValueError('LIVE_DIVERGED: preserve current edits and refresh or reconcile explicitly')
    return state


def refresh(root, binding, *, expected_parent):
    """Read-only alignment check until explicit external-edit import is admitted."""
    active = workflow.resume(root)['active']
    if expected_parent != active['id']:
        raise ValueError('Expected parent is stale')
    saved = read_json(reject_links(Path(root) / 'live/binding.json'))
    if Path(binding).resolve() != Path(saved['descriptor']).resolve():
        raise ValueError('Different live session requires explicit reattachment with baseline verification')
    return {'state': 'READY', **ensure_aligned(root)}
