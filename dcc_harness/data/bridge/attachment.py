"""Explicit main-thread adoption with retained copies and no implicit rollback."""
import hashlib
import json
from pathlib import Path

import bpy
try:
    from .files import file_hash, json_bytes, reject_links, write_exclusive
    from .identity import plan_identities, validate_plan
    from .adoption_inventory_blender import inventory
    from .continuity_blender import measure_live
    from .live_snapshot import fingerprint, equivalent
except ModuleNotFoundError:
    from dcc_harness.files import file_hash, json_bytes, reject_links, write_exclusive
    from dcc_harness.identity import plan_identities, validate_plan
    from dcc_harness.adoption_inventory_blender import inventory
    from dcc_harness.continuity_blender import measure_live
    from dcc_harness.live_snapshot import fingerprint, equivalent
from . import inspection


def scene_for(name):
    scene = bpy.data.scenes.get(name) if isinstance(name, str) else None
    if scene is None or scene != bpy.context.scene:
        raise ValueError('Select the explicitly paired scene in Blender before attachment')
    return scene


def snapshot(scene):
    """Same measured fields as independent saved verification, including source mesh/UV."""
    assert_copyable()
    observation = measure_live(scene)
    result = {key: observation[key] for key in ('objects', 'materials', 'scene', 'coverage', 'issues')}
    result['inventory'] = inventory(scene)
    def normalize(value):
        if isinstance(value, dict):
            if value.get('source') == 'FILE' and value.get('path') and value['path'] != '<packed>':
                value['path'] = str(Path(value['path']).resolve())
            for child in value.values():
                normalize(child)
        elif isinstance(value, list):
            for child in value:
                normalize(child)
    normalize(result)
    return result


def measured(scene):
    return fingerprint(snapshot(scene))


def check(session, payload):
    scene = scene_for(session.scene)
    current = snapshot(scene)
    observed = fingerprint(current)
    matches = payload.get('fingerprint') == observed
    if payload.get('snapshot'):
        path = reject_links(payload['snapshot']).resolve()
        if not path.is_relative_to(session.project.parent):
            raise ValueError('Snapshot escapes project')
        expected = json.loads(path.read_text())
        if fingerprint(expected) != payload['fingerprint']:
            raise ValueError('Expected snapshot was changed')
        matches = equivalent(expected, current)
    diagnostic = None
    if payload.get('fingerprint') is not None and not matches:
        import uuid
        folder = reject_links(session.project / 'live/divergence'); folder.mkdir(parents=True, exist_ok=True)
        diagnostic = str(folder / (str(uuid.uuid4()) + '.json'))
        write_exclusive(diagnostic, json_bytes(current))
    return {'fingerprint': observed, 'matches': matches, 'diagnostic': diagnostic, **session.describe()}


def assert_copyable():
    """A .blend copy alone cannot promise preservation of external unsaved buffers."""
    if any(image.is_dirty for image in bpy.data.images):
        raise ValueError('UNSAVED_IMAGE: save image edits explicitly before managed copying or recovery')
    if (any(getattr(bpy.data, name, ()) for name in ('sounds', 'movieclips', 'volumes', 'cache_files'))
            or any(font.filepath and font.filepath != '<builtin>' and not font.packed_file for font in bpy.data.fonts)
            or any(scene.sequence_editor and len(scene.sequence_editor.strips) for scene in bpy.data.scenes)):
        raise ValueError('UNSUPPORTED_DEPENDENCIES: audio, video, external fonts, volumes and caches need separate qualification')


def save_copy(session, path):
    assert_copyable()
    target = reject_links(path).resolve()
    if session.project is None or not target.is_relative_to(session.project.parent):
        raise ValueError('Save copy must stay in the bound project')
    if target.suffix.lower() != '.blend' or target.exists():
        raise FileExistsError('Recovery copy must be a new .blend file')
    target.parent.mkdir(parents=True, exist_ok=True)
    original = bpy.data.filepath
    disk_sha = file_hash(original) if original and Path(original).is_file() else None
    # Checkpoint storage may copy these bytes again. Freeze measured dependency paths
    # as absolute in the copy while restoring the exact artist-side path strings.
    paths = [(image, image.filepath, bpy.path.abspath(image.filepath, library=image.library))
             for image in bpy.data.images if image.filepath and not image.packed_file and not image.library]
    paths += [(library, library.filepath, bpy.path.abspath(library.filepath)) for library in bpy.data.libraries]
    try:
        for item, _, absolute in paths:
            item.filepath = absolute
        result = bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, relative_remap=False,
                                            check_existing=False)
    finally:
        for item, original_path, _ in paths:
            item.filepath = original_path
    if result != {'FINISHED'} or not target.is_file():
        raise RuntimeError('Native save-copy did not finish')
    if bpy.data.filepath != original or (disk_sha and file_hash(original) != disk_sha):
        raise RuntimeError('Save-copy changed the source document; inspect retained evidence')
    return {'path': str(target), 'sha256': file_hash(target), 'original_filepath': original,
            'original_sha256': disk_sha}


def begin(session, payload):
    if set(payload) != {'project', 'scene', 'operation_id', 'request_hash'}:
        raise ValueError('Invalid attachment preparation')
    scene = scene_for(payload['scene'])
    session.bind(payload['project'], scene.name)
    session.acquire(payload['operation_id'])
    folder = session.project.parent
    # A crash or retry cannot repeat identity writes: pre-copy and dispatch are immutable.
    try:
        initial = snapshot(scene); before = fingerprint(initial)
        write_exclusive(folder / 'attach-before.json', json_bytes(initial))
        source = save_copy(session, folder / 'pre-adoption.blend')
        if not equivalent(initial, snapshot(scene)):
            raise RuntimeError('STALE_SCENE: save-copy changed measured state')
        info = inventory(scene)
        # Empty scenes are enrolled using the same root as background bootstrap.
        plan = plan_identities(info, {'path': source['path'], 'sha256': source['sha256']}) if list(scene.objects) else None
        if plan is not None and plan['status'] != 'READY':
            write_exclusive(folder / 'blocked-plan.json', json_bytes(plan))
            raise ValueError('Identity plan is blocked: ' + '; '.join(plan['issues']))
        prepared = session.prepare(payload['operation_id'], payload['request_hash'], before)
        record = {'prepared': prepared, 'plan': plan, 'source': source, 'empty': not list(scene.objects)}
        write_exclusive(folder / 'attach-prepared.json', json_bytes(record))
        return {'operation_id': payload['operation_id'], 'prepared_path': str(folder / 'attach-prepared.json'),
                'source': source}
    except Exception:
        # Retain active identity and evidence; further mutation needs explicit reconciliation.
        raise


def apply(session, payload):
    if set(payload) != {'project', 'operation_id', 'request_hash'} or Path(payload['project']).resolve() != session.project:
        raise ValueError('Invalid attachment dispatch')
    if session.active != payload['operation_id']:
        raise ValueError('Attachment operation mismatch')
    folder = session.project.parent
    retained = json.loads(reject_links(folder / 'attach-prepared.json').read_text())
    scene = scene_for(session.scene)
    if file_hash(retained['source']['path']) != retained['source']['sha256']:
        raise ValueError('Pre-adoption recovery copy changed')
    initial = json.loads(reject_links(folder / 'attach-before.json').read_text())
    if fingerprint(initial) != retained['prepared']['fingerprint'] or not equivalent(initial, snapshot(scene)):
        raise ValueError('STALE_SCENE: attachment state changed')
    session.consume(retained['prepared'], payload['request_hash'], fingerprint(initial))
    write_exclusive(folder / 'attach-dispatched.json', json_bytes({'operation_id': payload['operation_id']}))
    plan = retained['plan']
    if retained['empty']:
        if list(scene.objects):
            raise ValueError('STALE_SCENE: empty scene changed')
        root = bpy.data.objects.new('HarnessRoot', None)
        scene.collection.objects.link(root)
        root['dcc_instance_id'] = 'harness.root'
        root['dcc_asset_id'] = 'harness.root'
        root.hide_render = True
    else:
        validate_plan(plan, inventory(scene), plan['source'])
        targets = []
        for assignment in plan['assignments']:
            pool = {'object': bpy.data.objects, 'material': bpy.data.materials,
                    'collection': bpy.data.collections}[assignment['kind']]
            item = next(x for x in pool if x.name_full == assignment['name'])
            if assignment['property'] in item:
                raise ValueError('Identity appeared after preparation')
            targets.append((item, assignment['property'], assignment['value']))
        for item, prop, value in targets:
            item[prop] = value
    before_save = snapshot(scene)
    baseline = save_copy(session, folder / 'baseline.blend')
    if not equivalent(before_save, snapshot(scene)):
        raise RuntimeError('Save-copy changed the adopted live scene')
    write_exclusive(folder / 'attach-snapshot.json', json_bytes(before_save))
    receipt = {'schema': 'dcc.live.adoption.v1', 'operation_id': payload['operation_id'],
               'session_id': session.session_id, 'generation': session.generation,
               'scene': scene.name, 'baseline': baseline, 'fingerprint': fingerprint(before_save),
               'snapshot': str(folder / 'attach-snapshot.json'),
               'inventory': inventory(scene), 'provenance': 'live_metadata_adoption',
               'artistic_acceptance': 'not_assessed'}
    write_exclusive(folder / 'attach-saved.json', json_bytes(receipt))
    # Active until the independently checked baseline is acknowledged by the host.
    return receipt


def acknowledge(session, payload):
    if set(payload) != {'operation_id', 'fingerprint', 'generation'}:
        raise ValueError('Invalid attachment acknowledgment')
    matched = check(session, {'fingerprint': payload['fingerprint'], 'snapshot': str(session.project.parent / 'attach-snapshot.json')})
    if payload['generation'] != session.generation or not matched['matches']:
        raise ValueError('LIVE_DIVERGED: adopted scene changed during verification')
    session.release(payload['operation_id'])
    return {'state': 'READY', **session.describe()}


def rebind(session, payload):
    if set(payload) != {'project', 'scene', 'allow_unresolved'} or type(payload['allow_unresolved']) is not bool:
        raise ValueError('Explicit project, scene and unresolved-state policy required')
    scene = scene_for(payload['scene'])
    session.bind(payload['project'], scene.name)
    if session.active:
        status_path = session.project / 'execution/operations' / session.active / 'live-status.json'
        state = json.loads(reject_links(status_path).read_text()) if status_path.exists() else {}
        if (not payload['allow_unresolved'] or
                (state.get('generation') == session.generation and state.get('state') in ('QUEUED', 'RUNNING'))):
            raise ValueError('BUSY: active operation requires status/reconciliation')
    import uuid
    folder = reject_links(session.project / 'live/inspections'); folder.mkdir(parents=True, exist_ok=True)
    path = folder / (str(uuid.uuid4()) + '.json')
    current = snapshot(scene)
    write_exclusive(path, json_bytes(current))
    return {**session.describe(), 'fingerprint': fingerprint(current), 'snapshot': str(path),
            'filepath': bpy.data.filepath}


def preview_capture(session, payload):
    import uuid
    if set(payload) != {'preview_id'} or str(uuid.UUID(payload['preview_id'])) != payload['preview_id']:
        raise ValueError('Invalid preview identity')
    if session.project is None or session.active:
        raise ValueError('BUSY: preview requires an attached scene with no active operation')
    scene = scene_for(session.scene)
    if scene != bpy.context.scene or any(o.mode != 'OBJECT' for o in scene.objects):
        raise ValueError('BUSY: preview requires the paired scene in Object mode')
    folder = reject_links(session.project / 'live/previews' / payload['preview_id'])
    if not (folder / 'request.json').is_file():
        raise ValueError('Preview reservation missing')
    current = snapshot(scene)
    source = save_copy(session, folder / 'preview.blend')
    if not equivalent(current, snapshot(scene)):
        raise ValueError('Live scene changed during preview capture')
    write_exclusive(folder / 'snapshot.json', json_bytes(current))
    result = {'source': source, 'fingerprint': fingerprint(current), 'scene': scene.name}
    write_exclusive(folder / 'capture.json', json_bytes(result))
    return result
