"""Lossless, opt-in JSON pooling of repeated evaluated UV arrays.

The storage envelope is not an observation schema. Decoding restores ordinary
independent lists and leaves the logical observation revision unchanged.
"""
import copy
import math

SCHEMA = 'dcc.observation.storage.v1'
MIN_BLOCK_VALUES = 256
MAX_UV_VALUES = 50_000_000


def _uv_values(values):
    if not isinstance(values, list) or any(type(v) not in (int, float) for v in values):
        raise ValueError('UV blocks require flat numeric lists')
    if any(isinstance(v, float) and not math.isfinite(v) for v in values):
        raise ValueError('Nonfinite UV value')


def _parts(observation):
    if (not isinstance(observation, dict) or observation.get('schema') != 'dcc.observation.v1'
            or not isinstance(observation.get('objects'), dict)):
        raise ValueError('Compact storage requires an observation with objects')
    for record in observation['objects'].values():
        if not isinstance(record, dict):
            raise ValueError('Observation object records must be mappings')
        if 'evaluated_uv_values' in record and not isinstance(record['evaluated_uv_values'], dict):
            raise ValueError('Evaluated UV layers must be a mapping')


def pack_observation(observation):
    """Build a new storage document; never quantize or edit the input."""
    from .evidence import digest, validate_observation
    validate_observation(observation)
    _parts(observation)
    payload = copy.deepcopy({k: v for k, v in observation.items() if k != 'objects'})
    payload['objects'] = {}
    blocks = {}
    total = 0
    for iid, record in observation['objects'].items():
        copied = copy.deepcopy({k: v for k, v in record.items() if k != 'evaluated_uv_values'})
        payload['objects'][iid] = copied
        if 'evaluated_uv_values' not in record:
            continue
        layers = copied['evaluated_uv_values'] = {}
        for name, values in record['evaluated_uv_values'].items():
            _uv_values(values)
            total += len(values)
            if total > MAX_UV_VALUES:
                raise ValueError('Compact observation exceeds expanded UV value limit')
            if len(values) < MIN_BLOCK_VALUES:
                layers[name] = list(values)
                continue
            key = digest(values)
            if key not in blocks:
                blocks[key] = list(values)
            layers[name] = {'uv_block': key}
    if not blocks:
        return payload
    return {'schema': SCHEMA, 'observation': payload, 'uv_blocks': blocks}


def unpack_observation(document):
    """Verify pooled content and restore independent UV arrays.

    Logical revision/native binding are still checked by existing consumers.
    No verification result is cached across calls, files or native edits.
    """
    from .evidence import digest
    if not isinstance(document, dict):
        return document
    schema = document.get('schema')
    if not isinstance(schema, str) or not schema.startswith('dcc.observation.storage.'):
        return document
    if schema != SCHEMA or set(document) != {'schema', 'observation', 'uv_blocks'}:
        raise ValueError('Unsupported compact observation envelope')
    payload, blocks = document['observation'], document['uv_blocks']
    _parts(payload)
    if not isinstance(blocks, dict) or not blocks:
        raise ValueError('Compact observation must contain UV blocks')
    unique_values = 0
    for key, values in blocks.items():
        _uv_values(values)
        unique_values += len(values)
        if unique_values > MAX_UV_VALUES:
            raise ValueError('Compact UV blocks exceed value limit')
        if key != digest(values):
            raise ValueError('Compact UV block content hash differs')
    used, total = set(), 0
    for record in payload['objects'].values():
        for value in record.get('evaluated_uv_values', {}).values():
            if isinstance(value, dict):
                if set(value) != {'uv_block'} or not isinstance(value['uv_block'], str) or value['uv_block'] not in blocks:
                    raise ValueError('Invalid or missing compact UV block reference')
                used.add(value['uv_block']); count = len(blocks[value['uv_block']])
            else:
                _uv_values(value); count = len(value)
            total += count
            if total > MAX_UV_VALUES:
                raise ValueError('Compact observation exceeds expanded UV value limit')
    if used != set(blocks):
        raise ValueError('Unused compact UV block')
    output = copy.deepcopy(payload)
    for record in output['objects'].values():
        for name, value in record.get('evaluated_uv_values', {}).items():
            if isinstance(value, dict):
                # Separate mutable lists: editing one instance cannot edit another.
                record['evaluated_uv_values'][name] = list(blocks[value['uv_block']])
    return output
