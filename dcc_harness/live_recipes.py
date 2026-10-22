"""Portable, closed schemas for the initially qualified live operations."""
import json
import math

MODIFIERS = {'BEVEL': {'width': (float, 0, 100), 'segments': (int, 1, 32), 'profile': (float, 0, 1)},
             'SUBSURF': {'levels': (int, 0, 3), 'render_levels': (int, 0, 4)},
             'SOLIDIFY': {'thickness': (float, -100, 100), 'offset': (float, -1, 1)}}


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError('Nonempty bounded text required')


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite numeric value required')


def validate(value):
    if not isinstance(value, dict) or set(value) != {'recipe', 'target', 'parameters'}:
        raise ValueError('Invalid live recipe fields')
    text(value['target'])
    params, recipe = value['parameters'], value['recipe']
    if not isinstance(params, dict):
        raise ValueError('Recipe parameters must be an object')
    if recipe == 'external.capture':
        if set(params) != {'snapshot', 'fingerprint'}:
            raise ValueError('External import requires the explicitly inspected snapshot')
        text(params['snapshot']); text(params['fingerprint'])
    elif recipe == 'object.transform':
        if not params or set(params) - {'location', 'rotation_euler', 'scale'}:
            raise ValueError('Unsupported transform property')
        for vector in params.values():
            if not isinstance(vector, list) or len(vector) != 3:
                raise ValueError('Transform requires three finite components')
            for item in vector:
                number(item)
    elif recipe == 'modifier.settings':
        if set(params) != {'name', 'type', 'settings'} or params['type'] not in MODIFIERS:
            raise ValueError('Unsupported modifier recipe')
        text(params['name'])
        settings = params['settings']
        if not isinstance(settings, dict) or not settings or set(settings) - MODIFIERS[params['type']].keys():
            raise ValueError('Unsupported modifier property')
        for key, v in settings.items():
            number(v)
            kind, minimum, maximum = MODIFIERS[params['type']][key]
            if (kind is int and type(v) is not int) or not minimum <= v <= maximum:
                raise ValueError('Modifier property outside qualified bounds')
    elif recipe == 'material.input':
        if set(params) != {'material_id', 'node', 'socket', 'value', 'shared_users'}:
            raise ValueError('Material edits require an explicit shared user scope')
        for key in ('material_id', 'node', 'socket'):
            text(params[key])
        users = params['shared_users']
        if not isinstance(users, list) or not users or any(not isinstance(u, str) or not u for u in users) or len(set(users)) != len(users):
            raise ValueError('Distinct shared user IDs required')
        values = params['value'] if isinstance(params['value'], list) else [params['value']]
        if len(values) not in (1, 3, 4):
            raise ValueError('Unsupported socket dimensions')
        for item in values:
            number(item)
    elif recipe == 'node.asset':
        if set(params) != {'path', 'sha256', 'group', 'modifier', 'inputs'}:
            raise ValueError('Node asset requires pinned source and explicit inputs')
        for key in ('path', 'sha256', 'group', 'modifier'):
            text(params[key])
        if len(params['sha256']) != 64 or any(c not in '0123456789abcdef' for c in params['sha256']):
            raise ValueError('Node asset requires SHA-256')
        if not isinstance(params['inputs'], dict):
            raise ValueError('Node inputs must be an object')
        for key, v in params['inputs'].items():
            text(key)
            for item in v if isinstance(v, list) else [v]:
                number(item)
    else:
        raise ValueError('Unsupported live recipe; arbitrary Python and operators are not admitted')
    json.dumps(value, allow_nan=False)
    return value.copy()
