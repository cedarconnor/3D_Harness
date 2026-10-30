"""Bounded shader observation, independent of bpy for portable contract tests.

Primitive RNA properties are measured by value. Unhandled pointer/collection state
is refused explicitly; UI layout and RNA identity metadata are excluded deliberately.
"""
from __future__ import annotations

import math


_UI = frozenset(('rna_type', 'bl_rna', 'name', 'name_full', 'label', 'location',
                 'location_absolute', 'width', 'width_hidden', 'height', 'dimensions', 'select', 'show_options',
                 'show_preview', 'show_texture', 'hide', 'use_custom_color', 'color',
                 'parent', 'warning_propagation', 'bl_idname', 'bl_label',
                 'bl_description', 'bl_icon', 'bl_static_type', 'type'))
_NODE_EXPLICIT = frozenset(('inputs', 'outputs', 'internal_links', 'node_tree', 'image',
                            'color_ramp', 'mute', 'texture_mapping', 'color_mapping', 'image_user'))


def _value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return {'unsupported_type': 'nonfinite_float'}
        return round(value, 7)
    try:
        return [_value(item) for item in value]
    except TypeError:
        return {'unsupported_type': type(value).__name__}


def graph(tree, *, value=None, image_record=None, max_depth=16, max_nodes=4096,
          max_links=16384, max_interface_items=4096):
    """Return v1 nodes/links plus recursive graph, RNA settings and coverage issues.

    Limits apply to the complete traversal, including repeated group instances.
    ``unsupported`` on each graph contains deterministic path-qualified reasons.
    """
    if tree is None:
        return None
    encode = value or _value
    remaining = {'nodes': max_nodes, 'links': max_links, 'interface': max_interface_items}

    def primitive(record, key, obj, errors, path):
        try:
            encoded = encode(getattr(obj, key))
            if _unsupported_value(encoded):
                errors.append(f'{path}.{key}: unsupported value')
            record[key] = encoded
        except Exception as exc:
            errors.append(f'{path}.{key}: unreadable {type(exc).__name__}')

    def settings(obj, skip, errors, path):
        result = {}
        props = getattr(getattr(obj, 'bl_rna', None), 'properties', None)
        if props is None:
            errors.append(f'{path}: missing RNA metadata')
            return result
        for prop in sorted(props, key=lambda p: p.identifier):
            key = prop.identifier
            if key in skip or key.startswith('bl_'):
                continue
            try:
                current = getattr(obj, key)
            except Exception as exc:
                errors.append(f'{path}.{key}: unreadable {type(exc).__name__}')
                continue
            if prop.type in ('POINTER', 'COLLECTION'):
                if current is not None and (prop.type != 'COLLECTION' or len(current)):
                    errors.append(f'{path}.{key}: unsupported RNA {prop.type}')
            else:
                primitive(result, key, obj, errors, path)
        return result

    def sockets(items, errors, path):
        records = []
        for index, item in enumerate(items):
            rec = {'identifier': item.identifier}
            rec.update(settings(item, {'rna_type', 'node', 'links', 'default_value',
                                        'name', 'description', 'hide', 'hide_value',
                                        'show_expanded', 'display_shape', 'select',
                                        'is_icon_visible', 'pin_gizmo'}, errors,
                                f'{path}[{index}]'))
            if hasattr(item, 'default_value'):
                primitive(rec, 'default_value', item, errors, f'{path}[{index}]')
            records.append(rec)
        return records

    def visit(current, ancestors, depth, path):
        result = {'nodes': [], 'links': []}
        errors = []
        pointer = current.as_pointer() if hasattr(current, 'as_pointer') else id(current)
        if pointer in ancestors:
            result['unsupported'] = [f'{path}: node group cycle']
            return result
        if depth > max_depth:
            result['unsupported'] = [f'{path}: depth limit exceeded']
            return result
        ancestors = ancestors | {pointer}
        if getattr(current, 'animation_data', None) is not None:
            errors.append(f'{path}.animation_data: unsupported animation or drivers')
        interface = getattr(current, 'interface', None)
        if interface is not None:
            result['interface'] = []
            for index, item in enumerate(interface.items_tree):
                if remaining['interface'] <= 0:
                    errors.append(f'{path}: interface item limit exceeded')
                    break
                remaining['interface'] -= 1
                result['interface'].append(settings(item, {'rna_type', 'parent', 'name',
                    'description', 'index', 'position', 'interface_items'}, errors,
                    f'{path}.interface[{index}]'))
        for node in sorted(current.nodes, key=lambda n: n.name):
            if remaining['nodes'] <= 0:
                errors.append(f'{path}: node limit exceeded')
                break
            remaining['nodes'] -= 1
            node_path = f'{path}/{node.name}'
            rec = {'name': node.name, 'type': node.bl_idname, 'inputs': {}}
            if hasattr(node, 'get') and node.get('dcc_effect_id') is not None:
                rec['dcc_effect_id'] = encode(node.get('dcc_effect_id'))
            for item in node.inputs:
                if hasattr(item, 'default_value'):
                    rec['inputs'][item.identifier] = encode(item.default_value)
                    if _unsupported_value(rec['inputs'][item.identifier]):
                        errors.append(f'{node_path}.inputs.{item.identifier}: unsupported value')
            rec['mute'] = bool(getattr(node, 'mute', False))
            rec['settings'] = settings(node, _UI | _NODE_EXPLICIT, errors, node_path)
            # Preserve original flat selected settings for existing consumers.
            for key in ('operation', 'blend_type', 'projection', 'projection_blend',
                        'interpolation', 'extension', 'noise_dimensions', 'normalize'):
                if hasattr(node, key):
                    primitive(rec, key, node, errors, node_path)
            rec['sockets'] = {'inputs': sockets(node.inputs, errors, node_path + '.inputs'),
                              'outputs': sockets(node.outputs, errors, node_path + '.outputs')}
            rec['outputs'] = {s.identifier: encode(s.default_value) for s in node.outputs
                              if hasattr(s, 'default_value')}
            for key in ('texture_mapping', 'color_mapping', 'image_user'):
                structured = getattr(node, key, None)
                if structured is not None:
                    rec[key] = settings(structured, {'rna_type', 'color_ramp'}, errors,
                                        node_path + '.' + key)
                    color_ramp = getattr(structured, 'color_ramp', None)
                    if color_ramp is not None:
                        rec[key]['color_ramp'] = {
                            'elements': [[encode(e.position), encode(e.color)] for e in color_ramp.elements],
                            'settings': settings(color_ramp, {'rna_type', 'elements'}, errors,
                                                 node_path + '.' + key + '.color_ramp')}
            image = getattr(node, 'image', None)
            if image is not None:
                try:
                    rec['image'] = image_record(image) if image_record else None
                    rec['image_settings'] = {key: encode(getattr(image, key)) for key in
                        ('source', 'alpha_mode', 'use_view_as_render', 'size', 'channels', 'is_float')
                        if hasattr(image, key)}
                    if getattr(image, 'is_dirty', False):
                        errors.append(f'{node_path}.image: unpersisted image pixels')
                    if getattr(image, 'source', 'FILE') not in ('FILE',):
                        errors.append(f'{node_path}.image: unsupported image source {image.source}')
                    if not rec['image'] or not rec['image'].get('sha256'):
                        errors.append(f'{node_path}.image: unsupported image content')
                    elif not rec['image'].get('exists'):
                        errors.append(f'{node_path}.image: missing image')
                except Exception as exc:
                    errors.append(f'{node_path}.image: unreadable {type(exc).__name__}')
            nested = getattr(node, 'node_tree', None)
            if nested is not None:
                rec['group'] = nested.name
                rec['graph'] = visit(nested, ancestors, depth + 1, node_path)
            ramp = getattr(node, 'color_ramp', None)
            if ramp is not None:
                rec['ramp'] = [[encode(e.position), encode(e.color)] for e in ramp.elements]
                rec['ramp_settings'] = settings(ramp, {'rna_type', 'elements'}, errors,
                                                node_path + '.color_ramp')
            result['nodes'].append(rec)
        link_flags = []
        for link in current.links:
            if remaining['links'] <= 0:
                errors.append(f'{path}: link limit exceeded')
                break
            remaining['links'] -= 1
            identity = [link.from_node.name, link.from_socket.identifier,
                        link.to_node.name, link.to_socket.identifier]
            result['links'].append(identity)
            if getattr(link, 'is_muted', False) or not getattr(link, 'is_valid', True):
                link_flags.append({'link': identity, 'muted': bool(getattr(link, 'is_muted', False)),
                                   'valid': bool(getattr(link, 'is_valid', True))})
        result['links'].sort()
        if link_flags:
            result['link_flags'] = sorted(link_flags, key=lambda r: r['link'])
        if errors:
            result['unsupported'] = sorted(set(errors))
        return result

    return visit(tree, set(), 0, getattr(tree, 'name', 'tree'))


def _unsupported_value(value):
    if isinstance(value, dict):
        return 'unsupported_type' in value or any(_unsupported_value(x) for x in value.values())
    return isinstance(value, list) and any(_unsupported_value(x) for x in value)


def graph_issues(record):
    """Collect nested coverage failures, including legacy unsupported markers."""
    if not record:
        return []
    issues = list(record.get('unsupported', []))
    for node in record.get('nodes', []):
        if node.get('unsupported_group'):
            issues.append(f"Unmeasured node group: {node.get('group', node['name'])}")
        image = node.get('image')
        if image and not image.get('exists'):
            issues.append(f"Missing image: {image.get('path')}")
        issues.extend(graph_issues(node.get('graph')))
    return sorted(set(issues))
