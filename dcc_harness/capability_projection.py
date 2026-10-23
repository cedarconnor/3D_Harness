"""One checkpoint/native capability projection, scoped to measured scene identities."""


def observed_scope(observation, target, fields):
    obj=observation['objects'].get(target)
    if obj is None: raise ValueError('Capability target is missing')
    result={}
    for field in fields:
        if field=='geometry':
            result[field]={k:obj[k] for k in ('source_mesh_hash','source_uv_hash','source_attribute_hash','geometry_hash') if k in obj}
        elif field=='transform': result[field]=obj['matrix_world']
        elif field=='modifiers': result[field]=obj.get('modifier_settings',[])
        elif field in ('materials','nodes'):
            result[field]={mid:observation['materials'][mid] for mid in obj['material_ids'] if mid is not None}
            result['material_users']={mid:sorted(oid for oid,o in observation['objects'].items() if mid in o.get('material_ids',[])) for mid in result[field]}
        else: raise ValueError('UNSUPPORTED_COVERAGE: '+field)
    return result
