"""Explicit initial identity adoption in owned, fresh background Blender processes."""
from __future__ import annotations

from pathlib import Path
import copy
import subprocess
import uuid

from .continuity import _plain
from .evidence import digest, file_hash, read_json, write_json


def plan_identities(inventory, source, namespace=None):
    """Plan missing properties only. Existing, even invalid, properties are never repaired."""
    namespace = str(uuid.UUID(namespace)) if namespace else str(uuid.uuid4())
    scene = inventory['scene']
    objects = inventory['objects']
    materials = inventory['materials']
    issues, assignments = [], []

    def valid(record, prop):
        value = record['properties'].get(prop)
        if prop in record['properties'] and (not isinstance(value, str) or not value.strip()):
            issues.append(f"{record['name']}: invalid existing {prop}; resolve explicitly")
        return value if isinstance(value, str) and value.strip() else None

    def unique(records, prop):
        seen = {}
        for record in records:
            value = record['properties'].get(prop)
            if isinstance(value, str) and value.strip():
                seen.setdefault(value, []).append(record)
            if record['scope']:
                valid(record, prop)
        for value, users in seen.items():
            if len(users) > 1 and any(r['scope'] for r in users):
                issues.append(f"Duplicate {prop} {value!r}: " + ', '.join(r['name'] for r in users))
        return set(seen)

    instance_ids = unique(objects, 'dcc_instance_id')
    material_ids = unique(materials, 'dcc_material_id')
    asset_ids = {r['properties'].get('dcc_asset_id') for r in objects
                 if isinstance(r['properties'].get('dcc_asset_id'), str)}

    def generated(prefix, key, existing):
        value = prefix + '.' + uuid.uuid5(uuid.UUID(namespace), key).hex
        if value in existing:
            issues.append(f"Generated ID collision: {value}; create a new preview")
        return value

    def assign(kind, record, prop, value):
        if prop in record['properties']:
            return
        if record['read_only']:
            issues.append(f"{record['name']}: linked/override data needs explicit local ownership")
        if kind == 'object' and set(record['scenes']) - {scene}:
            issues.append(f"{record['name']}: object is shared with another scene")
        if kind == 'material' and record['outside_users']:
            issues.append(f"{record['name']}: material has users outside the active scene")
        assignments.append({'kind': kind, 'name': record['name'], 'property': prop, 'value': value})

    scoped = [r for r in objects if r['scope']]
    if not scoped:
        issues.append('Active scene is empty')
    for record in scoped:
        assign('object', record, 'dcc_instance_id',
               generated('ext.adopted', 'object:' + record['name'], instance_ids)
               if 'dcc_instance_id' not in record['properties'] else None)
        if record['type'] != 'MESH':
            continue
        valid(record, 'dcc_asset_id')
        if 'dcc_asset_id' in record['properties']:
            continue
        shared = [r for r in objects if r['mesh'] == record['mesh'] and r['type'] == 'MESH']
        known = {valid(r, 'dcc_asset_id') for r in shared if 'dcc_asset_id' in r['properties']}
        known.discard(None)
        if len(known) > 1:
            issues.append(f"{record['name']}: shared mesh has ambiguous asset IDs {sorted(known)}")
            continue
        asset = next(iter(known)) if known else generated('asset.adopted', 'mesh:' + record['mesh'], asset_ids)
        assign('object', record, 'dcc_asset_id', asset)
    for record in materials:
        if record['scope']:
            assign('material', record, 'dcc_material_id',
                   generated('material.adopted', 'material:' + record['name'], material_ids)
                   if 'dcc_material_id' not in record['properties'] else None)
    issues = sorted(set(issues))
    return {'schema': 'dcc.identity-plan.v1', 'source': source, 'namespace': namespace,
            'inventory': inventory, 'inventory_sha256': digest(inventory),
            'status': 'BLOCKED' if issues else 'READY', 'issues': issues,
            'assignments': [] if issues else assignments}


def validate_plan(plan, inventory, source):
    """Rebuild the entire proposal; arbitrary ID setters are not accepted."""
    expected = plan_identities(inventory, source, plan['namespace'])
    if plan != expected:
        raise ValueError('Identity plan is stale or altered; create a new preview')
    if plan['status'] != 'READY':
        raise ValueError('Identity plan is blocked: ' + '; '.join(plan['issues']))


def verify_applied_plan(plan, inventory):
    """Check the reopened identities, including every previously present scoped ID."""
    expected = copy.deepcopy(plan['inventory'])
    for assignment in plan['assignments']:
        records = expected['objects' if assignment['kind'] == 'object' else 'materials']
        record = next(r for r in records if r['name'] == assignment['name'])
        record['properties'][assignment['property']] = assignment['value']

    def identities(value):
        return {kind: {r['name']: r['properties'] for r in value[kind] if r['scope']}
                for kind in ('objects', 'materials')}

    if identities(inventory) != identities(expected):
        raise ValueError('Saved identities do not match the applied plan; inspect retained files')


def _native(blender, folder, action, request):
    request_path = folder / (action + '-request.json')
    write_json(request_path, request)
    worker = Path(__file__).with_name('_adoption_blender.py')
    command = [str(blender), '--background', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1', '--python', str(worker), '--', action, str(request_path)]
    log_path = folder / (action + '.log')
    with log_path.open('x', encoding='utf-8') as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise RuntimeError(f'Blender {action} failed; inspect {log_path} and retained outputs before retrying')


def preview(source, out, blender):
    source = _plain(source).resolve(strict=True)
    if source.suffix.lower() != '.blend':
        raise ValueError('Source must be a saved .blend file')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source), 'sha256': file_hash(source)}
    _native(blender, folder, 'preview', {'source': descriptor, 'out': str(folder)})
    plan = read_json(folder / 'plan.json')
    return {'status': plan['status'], 'passed': plan['status'] == 'READY',
            'plan': str(folder / 'plan.json'), 'assignments': len(plan['assignments']), 'issues': plan['issues']}


def apply(plan_path, out, blender):
    plan = read_json(_plain(plan_path))
    validate_plan(plan, plan['inventory'], plan['source'])
    source = _plain(plan['source']['path']).resolve(strict=True)
    if file_hash(source) != plan['source']['sha256']:
        raise ValueError('Source changed since preview; create a new preview')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder / 'plan.json', plan)
    _native(blender, folder, 'apply', {'plan': plan, 'out': str(folder)})
    # Observe in a separate process: a successful save is not saved-state evidence.
    checkpoint = folder / 'checkpoint.blend'
    _native(blender, folder, 'observe', {'source': {'path': str(checkpoint), 'sha256': file_hash(checkpoint)},
                                       'plan': plan, 'out': str(folder)})
    observation = read_json(folder / 'observation.json')
    if file_hash(source) != plan['source']['sha256']:
        raise RuntimeError('Source changed during adoption; inspect retained outputs')
    ready = not observation['issues'] and observation['native_dirty'] is False
    result = {'schema': 'dcc.identity-adoption.v1', 'status': 'READY_FOR_START' if ready else 'NEEDS_REPAIR',
              'passed': ready, 'source': plan['source'], 'source_unchanged': True,
              'plan_sha256': file_hash(folder / 'plan.json'), 'assignments': len(plan['assignments']),
              'saved_identities_verified': True,
              'checkpoint': str(checkpoint), 'checkpoint_sha256': observation['checkpoint_sha256'],
              'observation': str(folder / 'observation.json'), 'issues': observation['issues'],
              'artistic_acceptance': 'not_assessed'}
    write_json(folder / 'receipt.json', result)
    return result
