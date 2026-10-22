"""Measured initial Geometry Nodes asset subset, shared by live and saved observers."""
import bpy
from .blender import graph, value
from .evidence import digest

NODE_TYPES = {'NodeGroupInput', 'NodeGroupOutput', 'GeometryNodeTransform'}
SOCKET_TYPES = {'NodeSocketGeometry', 'NodeSocketFloat', 'NodeSocketInt', 'NodeSocketVector'}


def describe(tree):
    if tree is None or tree.bl_idname != 'GeometryNodeTree' or tree.animation_data or tree.library:
        raise ValueError('UNSUPPORTED_COVERAGE: node tree is missing, linked or animated')
    if any(n.bl_idname not in NODE_TYPES or getattr(n, 'node_tree', None) for n in tree.nodes):
        raise ValueError('UNSUPPORTED_COVERAGE: node asset contains an unqualified node type')
    if not any(n.bl_idname == 'NodeGroupOutput' for n in tree.nodes):
        raise ValueError('Node asset has no group output')
    interface = []
    for socket in tree.interface.items_tree:
        if socket.item_type != 'SOCKET' or socket.socket_type not in SOCKET_TYPES:
            raise ValueError('UNSUPPORTED_COVERAGE: node asset interface')
        record = {'identifier': socket.identifier, 'name': socket.name, 'direction': socket.in_out,
                  'socket_type': socket.socket_type}
        for key in ('default_value', 'min_value', 'max_value'):
            if hasattr(socket, key):
                record[key] = value(getattr(socket, key))
        interface.append(record)
    result = graph(tree)
    for record in result['nodes']:
        node = tree.nodes[record['name']]
        record['mute'] = node.mute
        if hasattr(node, 'mode'):
            record['mode'] = node.mode
        if hasattr(node, 'is_active_output'):
            record['is_active_output'] = node.is_active_output
    return {'schema': 'dcc.node-asset.graph.v1', 'interface': interface, 'graph': result}


def modifier_record(modifier):
    tree = modifier.node_group
    description = describe(tree)
    inputs = {s['identifier']: value(modifier.get(s['identifier'], s.get('default_value')))
              for s in description['interface'] if s['direction'] == 'INPUT' and s['socket_type'] != 'NodeSocketGeometry'}
    # Attribute-driven input selection is not part of this initial subset.
    if any(modifier.get(key + '_use_attribute', False) for key in inputs):
        raise ValueError('UNSUPPORTED_COVERAGE: attribute-driven node asset inputs')
    return {'description': description, 'graph_sha256': digest(description), 'inputs': inputs,
            'source_sha256': tree.get('dcc_asset_source'), 'source_group': tree.get('dcc_asset_group')}
