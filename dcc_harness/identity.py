"""Portable identity planning shared by background and live adoption."""
import copy
import hashlib
import json
import uuid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


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
    # Collections instanced by the active scene. A linked collection's identity is its library
    # provenance, and its properties belong to the library, so only local ones are assigned.
    collections = inventory.get('collections', [])
    collection_ids = unique(collections, 'dcc_asset_id')
    for record in collections:
        if record['scope'] and not record['read_only'] and 'dcc_asset_id' not in record['properties']:
            assign('collection', record, 'dcc_asset_id',
                   generated('asset.adopted', 'collection:' + record['name'], asset_ids | collection_ids))
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
    pools = {'object': 'objects', 'material': 'materials', 'collection': 'collections'}
    for assignment in plan['assignments']:
        records = expected[pools[assignment['kind']]]
        record = next(r for r in records if r['name'] == assignment['name'])
        record['properties'][assignment['property']] = assignment['value']

    def identities(value):
        return {kind: {r['name']: r['properties'] for r in value.get(kind, []) if r['scope']}
                for kind in ('objects', 'materials', 'collections')}

    if identities(inventory) != identities(expected):
        raise ValueError('Saved identities do not match the applied plan; inspect retained files')
