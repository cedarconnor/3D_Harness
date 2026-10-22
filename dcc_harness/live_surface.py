"""Public read/status controls and bounded saved-copy previews for paired scenes."""
from pathlib import Path
import uuid

from . import blender_bridge, execution, workflow
from .evidence import read_json, write_json
from .files import reject_links


def sessions(workspace):
    folder = reject_links(Path(workspace) / '.harness-mcp/bridge')
    found = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        try:
            value = blender_bridge.call('session_describe', {}, binding=path)
            found.append({**value, 'binding': str(path)})
        except Exception as exc:
            found.append({'binding': str(path), 'state': 'UNAVAILABLE', 'reason': str(exc)})
    return {'sessions': found}


def inspect(query):
    if not isinstance(query, dict) or not isinstance(query.get('binding'), str):
        raise ValueError('Inspection requires an explicit binding descriptor')
    payload = {k: v for k, v in query.items() if k != 'binding'}
    return {'provenance': 'live_advisory_not_checkpoint_evidence',
            'result': blender_bridge.call('inspect', payload, binding=query['binding'])}


def status(root, operation_id=None):
    from .live import read_binding
    result = execution.status(root)
    if result['run'].get('backend') != 'live':
        raise ValueError('Project does not use live execution')
    binding = read_binding(root)
    current = binding['state']
    try:
        checked = blender_bridge.call('attach_check', {'fingerprint': binding['fingerprint'], 'snapshot': binding['snapshot']},
            binding=binding['descriptor'], expected=(binding['session_id'], binding['generation']))
        result['current_fingerprint'] = checked['fingerprint']
        if current == 'READY' and not checked['matches']:
            current = 'LIVE_DIVERGED'
    except Exception as exc:
        if current == 'READY': current = 'LIVE_STATE_UNAVAILABLE'
        result['live_error'] = str(exc)
    result.update(live_state=current, session_id=binding['session_id'], generation=binding['generation'],
                  scene=binding['scene'], recovery='live-refresh or explicit live-reconcile; never redispatch')
    if current != 'READY' and result['status'] not in ('CANCELLED', 'NEEDS_RECONCILIATION'):
        result['status'] = current
    if operation_id is not None:
        from .coordination import identifier
        identifier(operation_id)
        folder = reject_links(Path(root) / 'execution/operations' / operation_id)
        result['operation'] = execution._outcome(folder)
        path = reject_links(folder / 'live-status.json')
        result['native_operation'] = read_json(path) if path.exists() else {'state': 'UNKNOWN'}
    return result


def cancel(root, operation_id):
    from .coordination import identifier
    identifier(operation_id)
    folder = reject_links(Path(root) / 'execution/operations' / operation_id)
    request = read_json(reject_links(folder / 'request.json'))
    if request.get('backend') != 'live':
        raise ValueError('Operation is not live')
    path = reject_links(folder / 'live-cancel.json')
    if not path.exists():
        write_json(path, {'operation_id': operation_id})
    return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED', 'scene_reverted': False}


def execute(root, request):
    from .live_contracts import validate_operation, validate_live_recipe
    value = validate_operation(request)
    if value['backend'] != 'live':
        raise ValueError('Live execution requires the live backend')
    validate_live_recipe(value.get('live'))
    return execution.execute_operation(root, value)


def validate_preview(request):
    from .render import validate_views
    keys = {'session_id', 'generation', 'frame', 'width', 'height', 'samples', 'camera', 'compare_checkpoint'}
    if not isinstance(request, dict) or set(request) != keys:
        raise ValueError('Preview requires explicit session, generation, frame, dimensions, samples, camera and comparison')
    for key in ('session_id', 'generation'):
        if str(uuid.UUID(request[key])) != request[key]:
            raise ValueError('Invalid preview session identity')
    for key, low, high in (('frame', -1048574, 1048574), ('width', 32, 1024), ('height', 32, 1024), ('samples', 1, 32)):
        if type(request[key]) is not int or not low <= request[key] <= high:
            raise ValueError('Preview ' + key + ' exceeds supported bounds')
    if type(request['compare_checkpoint']) is not bool or set(request['camera']) != {'lens', 'location', 'target'}:
        raise ValueError('Preview needs an explicit fixed camera and comparison policy')
    validate_views(_views(request))
    return request


def _views(request):
    return {'schema': 'dcc.review.views.v1', 'render': {'engine': 'BLENDER_WORKBENCH',
        'resolution': [request['width'], request['height']], 'samples': request['samples'], 'seed': 0,
        'view_transform': 'Standard', 'look': 'None', 'exposure': 0},
        'views': [{'id': 'preview', 'purpose': 'whole', 'camera': request['camera']}]}


def preview(root, request, *, blender=None):
    from .live import read_binding
    from . import render
    validate_preview(request)
    root = reject_links(root).resolve()
    with execution._exclusive(root):
        binding = read_binding(root)
        if (request['session_id'], request['generation']) != (binding['session_id'], binding['generation']):
            raise ValueError('Wrong preview session or document generation')
        config = execution.configuration(root)
        from .environment_workflow import runtime_stamp
        if config is None or config.get('backend') != 'live' or config['runtime'] != runtime_stamp():
            raise ValueError('Preview requires an attached live project and its pinned runtime')
        op = str(uuid.uuid4())
        folder = reject_links(root / 'live/previews' / op); folder.mkdir(parents=True)
        write_json(folder / 'request.json', request)
        captured = blender_bridge.call('preview_capture', {'preview_id': op}, binding=binding['descriptor'],
            expected=(binding['session_id'], binding['generation']))
        source = reject_links(captured['source']['path']).resolve()
        if source != (folder / 'preview.blend').resolve():
            raise ValueError('Preview source escaped its owned folder')
        active = workflow.resume(root)['active']
    definition = folder / 'definition.json'; write_json(definition, _views(request))
    blender = blender or read_json(root.parent / 'attach-request.json')['blender']
    fixed = {'scene': binding['scene'], 'frame': request['frame']}
    after = render.render_file(captured['source']['path'], folder / 'current', blender, views=definition, preview=fixed)
    before = (render.render_file(active['checkpoint'], folder / 'accepted', blender, views=definition, preview=fixed)
              if request['compare_checkpoint'] else None)
    if before and read_json(before['settings']) != read_json(after['settings']):
        raise ValueError('Before/after preview settings differ; comparison is not valid')
    result = {'schema': 'dcc.live.preview.v1', 'preview_id': op, 'kind': 'saved_copy_geometry_render',
              'scene': binding['scene'], 'frame': request['frame'], 'fingerprint': captured['fingerprint'],
              'session_id': binding['session_id'], 'generation': binding['generation'],
              'accepted_checkpoint': active['id'], 'current': after, 'accepted': before,
              'artistic_acceptance': 'not_assessed', 'retention': 'Retained with project evidence; no automatic expiry'}
    write_json(folder / 'result.json', result)
    # This disposable copy is never a checkpoint or recovery source; images and provenance remain.
    from .files import file_hash
    if file_hash(source) != captured['source']['sha256']:
        raise ValueError('Preview copy changed; preserved for inspection')
    source.unlink()
    return result
