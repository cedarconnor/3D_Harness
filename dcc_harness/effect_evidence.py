"""Native effect identities resolved from independent observation data, without bpy."""
import copy


def selector(value, effect_id):
    return value.replace('{effect_name}', 'DCC::' + effect_id[:48])


def native_effect(measured, target, effect_id, *, required=True, recipe=None):
    spec = (recipe or {}).get('effect', {'kind':'modifier'})
    name = 'DCC::' + effect_id[:48]
    if spec['kind'] == 'modifier':
        matches = [(i, row) for i, row in enumerate(measured.get('modifiers', []))
                   if row['settings'].get('name') == name]
        if not matches and not required:
            return None
        if len(matches) != 1:
            raise ValueError('Claimed output requires exactly one measured owned effect (native modifier)')
        index, row = matches[0]
        if (recipe or {}).get('schema')=='dcc.capability.recipe.v2' and row.get('dcc_effect_id')!=effect_id:
            raise ValueError('Native modifier ownership marker is missing or differs')
        state = copy.deepcopy(row)
        for field in ('show_expanded', 'is_active'):
            state['settings'].pop(field, None)
        return {'kind':'modifier', 'target_id':target, 'name':name, 'stack_index':index, 'state':state}
    mid = selector(spec['material_id'], effect_id)
    materials = measured.get('materials', measured.get('nodes', {}))
    bindings = measured.get('material_bindings', [])
    slot = spec['slot']
    material = materials.get(mid)
    if material is None:
        if not required:
            return None
        raise ValueError('Claimed native material is missing')
    if slot >= len(bindings) or bindings[slot] != mid:
        if not required:
            return None
        raise ValueError('Claimed native material slot binding differs')
    if spec['kind'] == 'material':
        if material['name'] != name:
            raise ValueError('Claimed material is not owned by this effect')
        if (recipe or {}).get('schema')=='dcc.capability.recipe.v2' and material.get('dcc_effect_id')!=effect_id:
            raise ValueError('Native material ownership marker is missing or differs')
        state = copy.deepcopy(material)
    else:
        if (spec['material_id']=='{effect_name}' and (recipe or {}).get('schema')=='dcc.capability.recipe.v2'
                and material.get('dcc_effect_id')!=effect_id):
            raise ValueError('Native shader material container ownership marker differs')
        graph = material.get('graph') or {}
        names = [selector(item, effect_id) for item in spec['nodes']]
        selected = [row for row in graph.get('nodes', []) if row['name'] in names]
        if len(selected) != len(names) or {row['name'] for row in selected} != set(names):
            if not required and not selected:
                return None
            raise ValueError('Claimed shader effect requires exactly its owned native nodes')
        if (recipe or {}).get('schema')=='dcc.capability.recipe.v2' and any(row.get('dcc_effect_id')!=effect_id for row in selected):
            raise ValueError('Native shader ownership marker is missing or differs')
        links = graph.get('links', [])
        blocked = [row['link'] for row in graph.get('link_flags',[]) if row.get('muted') or row.get('valid') is False]
        muted = {row['name'] for row in graph['nodes'] if row.get('mute')}
        active_links = [link for link in links if link not in blocked
                        and link[0] not in muted and link[2] not in muted]
        outputs = {row['name'] for row in graph['nodes'] if row['type'] == 'ShaderNodeOutputMaterial'
                   and row.get('settings', {}).get('is_active_output', True)}
        for owned in names:
            visited, pending = set(), [owned]
            while pending:
                current = pending.pop()
                if current in visited:
                    continue
                visited.add(current)
                pending.extend(link[2] for link in active_links if link[0] == current)
            if not visited & outputs:
                raise ValueError('Claimed shader node is disconnected from native material output')
        state = {'nodes':copy.deepcopy(selected),
                 'links':copy.deepcopy([link for link in links if link[0] in names or link[2] in names])}
    return {'kind':spec['kind'], 'target_id':target, 'material_id':mid, 'slot':slot,
            'bindings':list(bindings), 'users':copy.deepcopy(measured.get('material_users', {}).get(mid, [])),
            'state':state}
