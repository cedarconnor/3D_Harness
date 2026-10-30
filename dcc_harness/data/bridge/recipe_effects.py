"""Scoped ownership and preservation for version-two native recipe effects."""
import copy
import bpy
from . import inspection
try:
    from .effect_evidence import selector
    from .continuity_blender import measure_live
    from .blender import graph
except ModuleNotFoundError:
    from dcc_harness.effect_evidence import selector
    from dcc_harness.continuity_blender import measure_live
    from dcc_harness.blender import graph
try:
    from .shader_graph import graph_issues
except ModuleNotFoundError:
    from dcc_harness.shader_graph import graph_issues


def owned(context):
    spec = context['recipe']['effect']
    if spec['kind'] == 'modifier':
        item = context['target'].modifiers.get(context['effect_name'])
        return [item] if item else []
    mid = selector(spec['material_id'], context['effect_id'])
    mats = [m for m in bpy.data.materials if m.get('dcc_material_id') == mid]
    if len(mats) > 1:
        raise ValueError('Duplicate effect material identity')
    if not mats:
        return []
    material = mats[0]
    if spec['kind'] == 'material':
        return [material]
    containers = [material] if spec['material_id'] == '{effect_name}' else []
    if not material.node_tree:
        return containers
    names = [selector(n, context['effect_id']) for n in spec['nodes']]
    return containers + [node for node in material.node_tree.nodes if node.name in names]


def ownership_before(context):
    items = owned(context)
    if any(owner(context,item) != context['effect_id'] for item in items):
        raise ValueError('Cannot adopt a pre-existing unowned native effect')
    return {item.as_pointer() for item in items}


def claim(context, original):
    for item in owned(context):
        if item.as_pointer() in original and owner(context,item) != context['effect_id']:
            raise ValueError('Owned effect identity changed')
        if owner(context,item) not in (None, context['effect_id']):
            raise ValueError('Native effect belongs to another effect key')
        if context['recipe']['effect']['kind']=='modifier':
            owners=dict(context['target'].get('dcc_modifier_effects',{}))
            owners[item.name]=context['effect_id']
            context['target']['dcc_modifier_effects']=owners
        else:
            item['dcc_effect_id'] = context['effect_id']


def owner(context,item):
    if context['recipe']['effect']['kind']=='modifier':
        return context['target'].get('dcc_modifier_effects',{}).get(item.name)
    return item.get('dcc_effect_id')


def preserved(context, allowed_materials):
    """Keep all measured scene state outside the explicit target/write fields.

    Also measure unused materials and every world: shared nested groups cannot hide
    an edit in a datablock outside the active scene's material-user projection.
    """
    current = measure_live(context['scene'])
    if current['issues']:
        raise ValueError('UNSUPPORTED_COVERAGE: ' + '; '.join(current['issues']))
    current = copy.deepcopy({k:current[k] for k in ('objects','materials','scene','coverage')})
    target = current['objects'][context['target_id']]
    writes = set(context['recipe']['coverage']['writes'])
    spec = context['recipe']['effect']
    scoped_shader = spec['kind'] in ('material', 'shader_nodes') and bool(writes & {'materials','nodes'})
    if writes & {'materials','nodes'}:
        if scoped_shader:
            bindings = target['material_ids']
            while len(bindings) <= spec['slot']:
                bindings.append(None)
            bindings[spec['slot']] = '<declared-effect-slot>'
        else:
            target.pop('material_ids', None)
            for mid in allowed_materials:
                current['materials'].pop(mid, None)
    if 'transform' in writes:
        for key in ('matrix_world','bounds','dimensions','geometry_hash'):
            target.pop(key, None)
    if 'geometry' in writes or 'modifiers' in writes:
        for key in ('source_mesh_hash','source_uv_hash','source_attribute_hash','geometry_hash',
                    'uv_hash','triangles','vertices','bounds','dimensions','evaluated_uv_values'):
            target.pop(key, None)
    if 'modifiers' in writes:
        target.pop('modifier_settings', None)
        if hasattr(context['target'], 'get'):
            target['modifier_owners'] = {name: owner for name, owner in
                context['target'].get('dcc_modifier_effects', {}).items()
                if name != context['effect_name']}
    if scoped_shader:
        # Use the full datablock inventory so unbinding a replaced artist material
        # cannot make its graph disappear from protection. Shader-node recipes own
        # their declared nodes, while a material recipe owns its selected material.
        current['materials'] = {}
    current['other_materials'] = {}
    selected_mid = selector(spec['material_id'], context['effect_id']) if scoped_shader else None
    for material in bpy.data.materials:
        mid = material.get('dcc_material_id')
        measured_graph = graph(material.node_tree)
        _covered(measured_graph)
        if scoped_shader:
            if mid == selected_mid and (spec['kind'] == 'material' or spec['material_id'] == '{effect_name}'):
                if material.get('dcc_effect_id') != context['effect_id']:
                    raise ValueError('Cannot preserve an unowned effect material container')
                continue
            if spec['kind'] == 'shader_nodes' and mid == selected_mid:
                measured_graph = _outside_nodes(measured_graph, context)
            record = {'name': material.name, 'material_id': mid,
                      'diffuse_color': list(material.diffuse_color), 'graph': measured_graph}
            if material.get('dcc_effect_id') is not None:
                record['dcc_effect_id'] = material.get('dcc_effect_id')
            current['other_materials'][material.name_full] = record
        elif mid not in allowed_materials:
            current['other_materials'][material.name_full] = measured_graph
    current['other_worlds'] = {}
    for world in bpy.data.worlds:
        measured_graph = graph(world.node_tree)
        _covered(measured_graph)
        current['other_worlds'][world.name_full] = measured_graph
    return current


def _covered(measured_graph):
    issues = graph_issues(measured_graph)
    if issues:
        raise ValueError('UNSUPPORTED_COVERAGE: ' + '; '.join(issues))


def _outside_nodes(measured_graph, context):
    if measured_graph is None:
        return None
    result = copy.deepcopy(measured_graph)
    names = {selector(name, context['effect_id']) for name in context['recipe']['effect']['nodes']}
    outputs = {node['name'] for node in result['nodes']
               if node['type'] == 'ShaderNodeOutputMaterial'
               and node.get('settings', {}).get('is_active_output', True)}

    def permitted(link):
        return (link[0] in names or link[2] in names
                or (link[2] in outputs and link[3] in ('Surface', 'Volume', 'Displacement')))

    result['nodes'] = [node for node in result['nodes'] if node['name'] not in names]
    result['links'] = [link for link in result['links'] if not permitted(link)]
    if 'link_flags' in result:
        flags = [row for row in result['link_flags'] if not permitted(row['link'])]
        if flags:
            result['link_flags'] = flags
        else:
            result.pop('link_flags')
    # Linking/unlinking owned nodes changes these derived flags on neighbouring
    # artist sockets; defaults and all configurable RNA properties stay protected.
    for node in result['nodes']:
        for sockets in node.get('sockets', {}).values():
            for socket in sockets:
                socket.pop('is_linked', None)
                socket.pop('is_inactive', None)
    return result


def allowed_materials(context):
    writes = set(context['recipe']['coverage']['writes'])
    if not writes & {'materials','nodes'}:
        return set()
    spec = context['recipe']['effect']
    if spec['kind'] != 'modifier':
        return {selector(spec['material_id'], context['effect_id'])}
    return {s.material.get('dcc_material_id') for s in context['target'].material_slots if s.material}
