"""Narrow Blender craft operations. Call only within the owned edit scope."""
import math


def set_material_scalar(material_id, node_name, socket_name, value, expected_users):
    """Edit one unlinked scalar only after checking every bound object user.

    expected_users contains stable dcc_instance_id values. Includes hidden
    objects and other scenes so an unanticipated shared user blocks the edit.
    Does not save, journal or grant permission to edit those users.
    """
    import bpy
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('A finite scalar is required')
    if socket_name not in ('Roughness', 'Metallic', 'IOR', 'Transmission Weight'):
        raise ValueError('This recipe supports only roughness, metallic, IOR and transmission')
    if socket_name != 'IOR' and not 0 <= value <= 1:
        raise ValueError('Surface weight must be in [0, 1]')
    if socket_name == 'IOR' and not 1 <= value <= 4:
        raise ValueError('IOR recipe range is [1, 4]')
    mats = [m for m in bpy.data.materials if m.get('dcc_material_id') == material_id]
    if len(mats) != 1:
        raise ValueError('Material identity missing or duplicated')
    mat = mats[0]
    users = [o for o in bpy.data.objects if any(s.material == mat for s in o.material_slots)]
    ids = [o.get('dcc_instance_id') for o in users]
    expected_users = list(expected_users)
    if (not ids or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids)
            or len(set(expected_users)) != len(expected_users) or set(ids) != set(expected_users)):
        raise ValueError('Shared material users differ from the explicitly scoped identities')
    if not mat.use_nodes or not mat.node_tree:
        raise ValueError('Material needs a native node graph')
    node = mat.node_tree.nodes.get(node_name)
    if node is None or node.type != 'BSDF_PRINCIPLED':
        raise ValueError('Expected a Principled BSDF node')
    socket = node.inputs.get(socket_name)
    if socket is None or socket.is_linked:
        raise ValueError('Scalar is missing or driven; edit the upstream recipe explicitly')
    before = float(socket.default_value)
    socket.default_value = value
    return {'material': material_id, 'users': sorted(ids), 'node': node_name, 'socket': socket_name,
            'before': before, 'after': float(socket.default_value)}
