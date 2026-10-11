"""Native qualification of fine-grained modifier and node-field permissions (build-plan item P13, first part).

Builds the relations probe's flat bench and a baseline with a Bevel modifier "Edge" (2 segments) on
bench.top and a Mix node "Tint" (blend MIX) in the timber material, and starts a project on it.
Candidates change the bevel segments to 3, the bevel width, and the Tint blend to MULTIPLY. With
allowed_modifier_settings for Edge/segments (plus the geometry fields a bevel changes) the segment
change publishes; the width change is refused. allowed_material_node_fields with MULTIPLY publishes
the blend change, and a contract asking for SCREEN refuses it.
"""
from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
from dcc_harness.evidence import write_json

q.blender('scenes.log', '--python', REPO / 'scripts/relations_native_probe.py', '--', '--out', out / 'scenes')
maker = out / 'variant.py'
maker.write_text(
    "import bpy, sys\n"
    "target, segments, width, blend = sys.argv[sys.argv.index('--') + 1:]\n"
    "top = next(o for o in bpy.data.objects if o.get('dcc_instance_id') == 'bench.top')\n"
    "mod = top.modifiers.new('Edge', 'BEVEL'); mod.segments = int(segments); mod.width = float(width)\n"
    "tree = bpy.data.materials['timber'].node_tree\n"
    "tint = tree.nodes.new('ShaderNodeMix'); tint.name = 'Tint'; tint.data_type = 'RGBA'; tint.blend_type = blend\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target)\n", encoding='utf-8')
variants = {'base': (2, 0.01, 'MIX'), 'segments': (3, 0.01, 'MIX'), 'width': (2, 0.02, 'MIX'), 'blend': (3, 0.01, 'MULTIPLY')}
for name, (segments, width, blend) in variants.items():
    q.blender(f'variant-{name}.log', out / 'scenes/flat.blend', '--python', maker, '--', out / f'{name}.blend', segments, width, blend)
observed = {name: q.cli('observe', out / f'{name}.blend', '--blender', a.blender, '--output-dir', out / f'observe-{name}')['observation']
            for name in variants}
(out / 'BRIEF.md').write_text('Bevelled bench; qualification fixture.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the saved scene.\n', encoding='utf-8')
write_json(out / 'decisions.json', {})
project = out / 'project'
q.cli('start', project, '--checkpoint', out / 'base.blend', '--observation', observed['base'], '--brief-file', out / 'BRIEF.md',
      '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
(out / 'edit.py').write_text('# Reserved for qualification; the candidates were built beforehand.\n', encoding='utf-8')
write_json(out / 'updates.json', {})
GEOMETRY = ['geometry_hash', 'triangles', 'vertices', 'uv_hash', 'evaluated_uv_values', 'bounds', 'dimensions']
REQUIRED = {'bench.top': {'type': 'MESH'}}


def edit(label, current, candidate, rules, expect):
    contract = out / f'contract-{label}.json'
    write_json(contract, {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': REQUIRED}, **rules})
    parent = q.cli('next', project)['active']['id']
    reserved = q.cli('begin-edit', project, '--parent', parent, '--current', out / f'{current}.blend', '--observation', observed[current],
                     '--script', out / 'edit.py', '--contract', contract, '--label', label)
    outcome = q.cli('finish-edit', project, reserved['edit'], '--checkpoint', out / f'{candidate}.blend', '--observation', observed[candidate],
                    '--handoff', out / 'HANDOFF.md', '--updates', out / 'updates.json', expect=0 if expect == 'PUBLISHED' else 1)
    assert outcome['status'] == expect, (label, outcome['status'], outcome.get('failures'))
    return [f for f in outcome.get('failures', []) if 'Modifier' in f or 'Material' in f]


bevel = {'allowed_modifier_settings': {'bench.top': {'Edge': ['segments']}}, 'allowed_object_prefixes': {'bench.top': GEOMETRY}}
summary = {'width_refused': edit('width', 'base', 'width', bevel, 'REJECTED_RETAINED')}
assert summary['width_refused'] == ['Modifier settings differ beyond the permitted settings: bench.top'], summary
edit('segments', 'base', 'segments', bevel, 'PUBLISHED')
summary['segments'] = 'PUBLISHED'
summary['wrong_blend_refused'] = edit('screen', 'segments', 'blend', {'allowed_material_node_fields': {'timber': {'Tint': {'blend_type': 'SCREEN'}}}},
                                      'REJECTED_RETAINED')
assert summary['wrong_blend_refused'] == ['Material differs beyond requested inputs or desired values: timber'], summary
edit('multiply', 'segments', 'blend', {'allowed_material_node_fields': {'timber': {'Tint': {'blend_type': 'MULTIPLY'}}}}, 'PUBLISHED')
summary['blend'] = 'PUBLISHED'
q.finish(summary)
