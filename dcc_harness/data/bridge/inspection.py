"""Main-thread, bounded scene queries with explicit measured fields."""
import hashlib
import json
import math

ID_PROPERTY = 'dcc_instance_id'
FIELDS = {
    'objects': ('id', 'name', 'type', 'transform', 'data', 'materials', 'collections', 'visibility'),
    'modifiers': ('name', 'type', 'properties'),
    'materials': ('id', 'name', 'use_nodes', 'diffuse_color', 'nodes', 'links'),
    'nodes': ('name', 'type', 'inputs'),
    'assets': ('name', 'type', 'interface'),
    'images': ('name', 'filepath', 'source', 'size', 'colorspace'),
    'cameras': ('name', 'type', 'lens', 'clip_start', 'clip_end'),
    'lights': ('name', 'type', 'energy', 'color'),
    'collections': ('name', 'objects', 'children'),
    'operators': ('id', 'description', 'properties'),
}


def plain(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    try:
        return [plain(v) for v in value]
    except (TypeError, ValueError):
        raise ValueError('UNSUPPORTED_COVERAGE: non-scalar RNA value') from None


def properties(owner):
    result, omitted = {}, []
    for prop in owner.bl_rna.properties:
        key = prop.identifier
        if key == 'rna_type':
            continue
        if prop.type in ('BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'):
            try:
                result[key] = plain(getattr(owner, key))
            except (ValueError, AttributeError):
                omitted.append(key)
        else:
            omitted.append(key)
    return {'values': result, 'unmeasured': omitted}


def target(scene, identifier):
    if not isinstance(identifier, str) or not identifier:
        raise ValueError('Stable object ID is required')
    matches = [o for o in scene.objects if o.get(ID_PROPERTY) == identifier]
    if len(matches) != 1:
        raise ValueError('Stable object ID is missing or ambiguous')
    return matches[0]


def node_info(node):
    inputs = []
    for socket in node.inputs:
        entry = {'identifier': socket.identifier, 'name': socket.name, 'linked': socket.is_linked}
        if hasattr(socket, 'default_value'):
            try:
                entry['value'] = plain(socket.default_value)
            except ValueError:
                entry['unmeasured'] = 'pointer socket'
        inputs.append(entry)
    return {'name': node.name, 'type': node.bl_idname, 'inputs': inputs}


def describe(kind, item):
    if kind == 'objects':
        return {'id': item.get(ID_PROPERTY), 'name': item.name, 'type': item.type,
                'transform': [list(row) for row in item.matrix_world],
                'data': item.data.name if item.data else None,
                'materials': [s.material.name if s.material else None for s in item.material_slots],
                'collections': sorted(c.name for c in item.users_collection),
                'visibility': {'render': item.hide_render, 'viewport': item.hide_viewport}}
    if kind == 'modifiers':
        return {'name': item.name, 'type': item.type, 'properties': properties(item)}
    if kind == 'materials':
        tree = item.node_tree
        return {'id': item.get('dcc_material_id'), 'name': item.name, 'use_nodes': item.use_nodes,
                'diffuse_color': list(item.diffuse_color),
                'nodes': [node_info(n) for n in tree.nodes] if tree else [],
                'links': [[l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier]
                          for l in tree.links] if tree else []}
    if kind == 'nodes':
        return node_info(item)
    if kind == 'assets':
        return {'name': item.name, 'type': item.bl_idname,
                'interface': [{'name': i.name, 'type': i.item_type,
                               'identifier': getattr(i, 'identifier', None),
                               'socket_type': getattr(i, 'socket_type', None),
                               'direction': getattr(i, 'in_out', None)} for i in item.interface.items_tree]}
    if kind == 'images':
        return {'name': item.name, 'filepath': item.filepath, 'source': item.source,
                'size': list(item.size), 'colorspace': item.colorspace_settings.name}
    if kind in ('cameras', 'lights'):
        return {key: plain(getattr(item, key)) for key in FIELDS[kind]}
    if kind == 'collections':
        return {'name': item.name, 'objects': sorted(o.name for o in item.objects),
                'children': sorted(c.name for c in item.children)}
    raise ValueError('UNSUPPORTED_COVERAGE: unknown inspection kind')


def inspect(query):
    import bpy
    if not isinstance(query, dict) or set(query) - {'kind', 'scene', 'target', 'material', 'operator', 'offset', 'limit', 'fields'}:
        raise ValueError('Invalid inspection query')
    kind = query.get('kind', 'objects')
    fields = query.get('fields', FIELDS.get(kind))
    if kind not in FIELDS or not isinstance(fields, (tuple, list)) or set(fields) - set(FIELDS[kind]):
        raise ValueError('UNSUPPORTED_COVERAGE: requested fields are not measured')
    offset, limit = query.get('offset', 0), query.get('limit', 50)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('Invalid pagination')
    scene_name = query.get('scene')
    scene = bpy.data.scenes.get(scene_name) if isinstance(scene_name, str) else None
    if scene is None:
        raise ValueError('Explicit existing scene is required')
    if kind == 'operators':
        name = query.get('operator', '')
        if not isinstance(name, str) or name.count('.') != 1 or any(not p.isidentifier() or p.startswith('_') for p in name.split('.')):
            raise ValueError('Explicit operator identifier required')
        group, operator = name.split('.')
        try:
            rna = getattr(getattr(bpy.ops, group), operator).get_rna_type()
        except (AttributeError, RuntimeError):
            raise ValueError('Operator is not registered') from None
        rows = [{'id': name, 'description': rna.description,
                 'properties': [{'identifier': p.identifier, 'type': p.type,
                                 'readonly': p.is_readonly} for p in rna.properties if p.identifier != 'rna_type']}]
    else:
        if kind == 'objects':
            items = list(scene.objects)
        elif kind == 'modifiers':
            items = list(target(scene, query.get('target')).modifiers)
        elif kind == 'nodes':
            material = bpy.data.materials.get(query.get('material', ''))
            if material is None or material.node_tree is None:
                raise ValueError('Material node tree missing')
            items = list(material.node_tree.nodes)
        else:
            items = list(getattr(bpy.data, 'node_groups' if kind == 'assets' else kind))
        items.sort(key=lambda item: item.name)
        total = len(items)
        rows = [describe(kind, item) for item in items[offset:offset + limit]]
    if kind == 'operators':
        total = len(rows)
        rows = rows[offset:offset + limit]
    return {'schema': 'dcc.blender.inspection.v1', 'kind': kind, 'scene': scene.name,
            'total': total, 'offset': offset, 'next_offset': offset + limit if offset + limit < total else None,
            'items': [{key: row[key] for key in fields} for row in rows],
            'coverage': {'measured_fields': list(fields), 'scope': 'listed datablock metadata only',
                         'not_measured': ['evaluated appearance', 'animation', 'simulation', 'external file contents']}}


def fingerprint(scope):
    """Hash explicitly requested fields only, never imply whole-document equality."""
    query = dict(scope)
    query['offset'], query['limit'] = 0, 200
    pages, coverage = [], None
    while True:
        result = inspect(query)
        coverage = result['coverage']
        pages.extend(result['items'])
        if result['next_offset'] is None:
            break
        query['offset'] = result['next_offset']
    raw = json.dumps(pages, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'scope': scope, 'coverage': coverage}
