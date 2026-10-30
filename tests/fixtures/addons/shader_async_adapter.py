"""Independent fixture inspector; provider reports cannot establish native success."""


def preflight(context, parameters):
    return {'ready':context['target'].mode == 'OBJECT', 'shared_users':context['shared_users']}


def apply(context, parameters, effect_id): return context['invoke']()


def inspect_output(context, effect_id):
    spec = context['recipe']['effect']; name = context['effect_name']
    materials = [slot.material for slot in context['target'].material_slots if slot.material]
    if spec['kind'] == 'material':
        selected = [m for m in materials if m.get('dcc_material_id') == name and m.get('dcc_effect_id') == effect_id]
        values = [{'id':m.get('dcc_material_id'), 'color':list(next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value)} for m in selected]
        return {'effect_id':effect_id, 'effect_count':len(selected), 'measurements':{'materials':values}}
    material_id = spec['material_id'].replace('{effect_name}',name)
    material = next((m for m in materials if m.get('dcc_material_id')==material_id), None)
    selected = [] if material is None else [n for n in material.node_tree.nodes if n.name in [v.replace('{effect_name}',name) for v in spec['nodes']] and n.get('dcc_effect_id')==effect_id]
    values = []
    for node in selected:
        nested = next(n for n in node.node_tree.nodes if n.type=='GROUP')
        bsdf = next(n for n in nested.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        values.append({'name':node.name,'color':list(bsdf.inputs['Base Color'].default_value)})
    return {'effect_id':effect_id, 'effect_count':len(selected), 'measurements':{'nodes':values}}


def verify_saved(observation, output): return {'passed':output['effect_count']==1}
