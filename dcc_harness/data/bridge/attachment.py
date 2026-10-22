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
except ModuleNotFoundError:
    from dcc_harness.files import file_hash, json_bytes, reject_links, write_exclusive
    from dcc_harness.identity import plan_identities, validate_plan
    from dcc_harness.adoption_inventory_blender import inventory
    from dcc_harness.continuity_blender import measure_live
from . import inspection


def scene_for(name):
    scene = bpy.data.scenes.get(name) if isinstance(name, str) else None
    if scene is None or scene != bpy.context.scene:
        raise ValueError('Select the explicitly paired scene in Blender before attachment')
    return scene


def measured(scene):
    """Same measured fields as independent saved verification, including source mesh/UV."""
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
    return hashlib.sha256(json.dumps(result, sort_keys=True, allow_nan=False).encode()).hexdigest()


def save_copy(session, path):
    target = reject_links(path).resolve()
    if session.project is None or not target.is_relative_to(session.project.parent):
        raise ValueError('Save copy must stay in the bound project')
    if target.suffix.lower() != '.blend' or target.exists():
        raise FileExistsError('Recovery copy must be a new .blend file')
    target.parent.mkdir(parents=True, exist_ok=True)
    original = bpy.data.filepath
    disk_sha = file_hash(original) if original and Path(original).is_file() else None
    result = bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, relative_remap=True,
                                        check_existing=False)
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
        before = measured(scene)
        source = save_copy(session, folder / 'pre-adoption.blend')
        if before != measured(scene):
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
    session.consume(retained['prepared'], payload['request_hash'], measured(scene))
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
    before_save = measured(scene)
    baseline = save_copy(session, folder / 'baseline.blend')
    if before_save != measured(scene):
        raise RuntimeError('Save-copy changed the adopted live scene')
    receipt = {'schema': 'dcc.live.adoption.v1', 'operation_id': payload['operation_id'],
               'session_id': session.session_id, 'generation': session.generation,
               'scene': scene.name, 'baseline': baseline, 'fingerprint': before_save,
               'inventory': inventory(scene), 'provenance': 'live_metadata_adoption',
               'artistic_acceptance': 'not_assessed'}
    write_exclusive(folder / 'attach-saved.json', json_bytes(receipt))
    # Active until the independently checked baseline is acknowledged by the host.
    return receipt


def acknowledge(session, payload):
    if set(payload) != {'operation_id', 'fingerprint', 'generation'}:
        raise ValueError('Invalid attachment acknowledgment')
    if payload['generation'] != session.generation or measured(scene_for(session.scene)) != payload['fingerprint']:
        raise ValueError('LIVE_DIVERGED: adopted scene changed during verification')
    session.release(payload['operation_id'])
    return {'state': 'READY', **session.describe()}
