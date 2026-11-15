"""Native qualification of the blockout spec commands (build-plan item G5).

spec-check     a valid spec passes; eight broken specs are each refused for their own reason
blockout-build the spec builds into a new file that observes READY, audits without an error, and
               passes its own generated relations; a rebuild over an untouched blockout replaces it;
               a rebuild over an edited one, one holding a foreign object, or a scene that already
               uses a part's ID is refused, and the source is never written
spec-compare   the built file matches; five edited files each report exactly their own codes; a
               part named through `ids` is found; a floating part fails the generated relations
study          the potting-shed study spec passes against the production garden; its door ranges
               were widened after the owner judged the door as built to be right
"""
import copy

from _launcher import REPO, Qualification
q = Qualification(__doc__)
a, out = q.args, q.out
from dcc_harness.evidence import file_hash, read_json, write_json

SPEC = {'schema': 'dcc.blockout.v1', 'name': 'yard', 'units': 'metres', 'up': 'Z', 'parts': [
    {'name': 'ground', 'category': 'ground', 'primitive': 'plane', 'position': [0, 0, 0], 'size': [8, 8, 0]},
    {'name': 'shed', 'category': 'structure', 'primitive': 'box', 'position': [0, 1.5, 0], 'size': [3, 2, 2.2], 'group': 'building', 'rests_on': 'ground'},
    {'name': 'roof', 'category': 'roof', 'primitive': 'wedge', 'position': [0, 1.5, 2.2], 'size': [2.8, 1.8, 0.6], 'group': 'building', 'rests_on': 'shed'},
    {'name': 'door', 'category': 'opening', 'primitive': 'box', 'position': [0, 0.48, 0], 'size': [0.9, 0.06, 2.0]},
    {'name': 'bench', 'category': 'furniture', 'primitive': 'box', 'position': [-2, -1, 0], 'size': [1.6, 0.6, 0.9], 'yaw': 30, 'rests_on': 'ground'},
    {'name': 'pot', 'category': 'prop', 'primitive': 'cylinder', 'position': [-2, -1, 0.9], 'size': [0.3, 0.3, 0.25], 'rests_on': 'bench'},
    {'name': 'tree', 'category': 'vegetation', 'primitive': 'cone', 'position': [2.5, -2, 0], 'size': [1, 1, 2], 'rests_on': 'ground'},
    {'name': 'ball', 'category': 'prop', 'primitive': 'sphere', 'position': [1, -1.5, 0], 'size': [0.4, 0.4, 0.4]}],
    'proportions': [
        {'id': 'door-to-shed', 'ratio': [{'part': 'door', 'measure': 'height'}, {'part': 'shed', 'measure': 'height'}], 'target': 0.9, 'tolerance': 0.05},
        {'id': 'bench-top', 'value': {'part': 'bench', 'measure': 'top'}, 'min': 0.85, 'max': 0.95},
        {'id': 'building-height', 'value': {'part': 'building', 'measure': 'height'}, 'max': 3.0}],
    'never': [{'id': 'bench-clear-of-shed', 'rule': 'no_overlap', 'parts': ['bench', 'building']},
              {'id': 'pot-above-ground', 'rule': 'not_below', 'part': 'pot', 'z': 0},
              {'id': 'pot-on-bench', 'rule': 'within', 'part': 'pot', 'footprint': 'bench'}],
    'avoid': ['The door must not read as wider than a person can reach across.'],
    'tolerance': {'size': 0.05, 'position': 0.05}}


def variant(change):
    spec = copy.deepcopy(SPEC)
    change(spec)
    return spec


def save(name, spec):
    write_json(out / f'{name}.json', spec)
    return out / f'{name}.json'


# spec-check
checked = q.cli('spec-check', save('spec', SPEC))
assert checked['passed'] and checked['parts'] == 8 and checked['supported_parts'] == 5 and checked['proportions'] == 3 and checked['never'] == 3
BROKEN = {
    'unknown-field': (lambda s: s['parts'][1].update(colour='red'), 'unknown field'),
    'size-out-of-range': (lambda s: s['parts'][1].update(size=[3, 2, 5000]), 'must be three numbers'),
    'plane-with-height': (lambda s: s['parts'][0].update(size=[8, 8, 0.1]), 'a plane has height 0'),
    'duplicate-name': (lambda s: s['parts'][2].update(name='shed'), 'unique'),
    'unknown-support': (lambda s: s['parts'][5].update(rests_on='table'), 'must name another part'),
    'unknown-primitive': (lambda s: s['parts'][7].update(primitive='torus'), 'must be one of'),
    'own-proportion': (lambda s: s['parts'][4].update(size=[1.6, 0.6, 1.4]), 'breaks its own rules'),
    'own-never': (lambda s: s['parts'][5].update(position=[-2, -1, -0.5]), 'breaks its own rules')}
refusals = {name: q.refused(['spec-check', save('broken-' + name, variant(change))], message) for name, (change, message) in BROKEN.items()}

# blockout-build
built = q.cli('blockout-build', out / 'spec.json', '--blender', a.blender, '--output', out / 'yard.blend', '--output-dir', out / 'build')
assert built['status'] == 'BUILT' and built['parts'] == sorted(p['name'] for p in SPEC['parts']) and not built['replaced']
assert built['collection'] == 'dcc.blockout.yard' and file_hash(out / 'yard.blend') == built['output_sha256']
observed = q.cli('observe', out / 'yard.blend', '--blender', a.blender, '--output-dir', out / 'observe')
assert observed['status'] == 'READY' and observed['issues'] == [], observed
audit = q.cli('audit', out / 'yard.blend', '--blender', a.blender, '--output-dir', out / 'audit')
assert audit['passed'] and not {'NORMALS_INCONSISTENT', 'NORMALS_INWARD', 'SCALE_NONUNIFORM', 'ZERO_AREA_FACES'} & set(audit['by_code']), audit['by_code']
supported = q.cli('relations', out / 'yard.blend', '--blender', a.blender, '--output-dir', out / 'relations', '--spec', built['relations'])
assert supported['passed'] and len(supported['relations']) == 5, supported

editor = out / 'edit.py'
editor.write_text(
    "import bpy, sys\n"
    "source, target, change = sys.argv[sys.argv.index('--') + 1:]\n"
    "bpy.ops.wm.open_mainfile(filepath=source)\n"
    "part = lambda name: next(o for o in bpy.data.objects if o.get('dcc_instance_id') == name)\n"
    "if change == 'tall-bench': part('bench').scale.z = 1.5\n"
    "elif change == 'pot-off-bench': part('pot').location.x += 1.5\n"
    "elif change == 'no-pot': bpy.data.objects.remove(part('pot'))\n"
    "elif change == 'bench-in-shed': part('bench').location = (0.5, 1.5, 0)\n"
    "elif change == 'sunk-pot': part('pot').location.z = -0.4\n"
    "elif change == 'detailed-bench': part('bench')['dcc_instance_id'] = 'ext.bench.body'\n"
    "elif change == 'foreign':\n"
    "    mesh = bpy.data.meshes.new('stray'); mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])\n"
    "    bpy.data.collections['dcc.blockout.yard'].objects.link(bpy.data.objects.new('stray', mesh))\n"
    "elif change == 'id-taken':\n"
    "    bpy.data.collections.remove(bpy.data.collections['dcc.blockout.yard'])\n"
    "    for o in list(bpy.data.objects):\n"
    "        if o.get('dcc_instance_id') != 'shed': bpy.data.objects.remove(o)\n"
    "        else: bpy.context.scene.collection.objects.link(o)\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target)\n", encoding='utf-8')
for change in ('tall-bench', 'pot-off-bench', 'no-pot', 'bench-in-shed', 'sunk-pot', 'detailed-bench', 'foreign', 'id-taken'):
    q.blender(f'edit-{change}.log', '--python', editor, '--', out / 'yard.blend', out / f'{change}.blend', change)


def rebuild(source, key, refusal=None):
    before = file_hash(out / f'{source}.blend')
    arguments = ['blockout-build', out / 'spec.json', '--blender', a.blender, '--output', out / f'{key}.blend', '--output-dir', out / key,
                 '--source', out / f'{source}.blend']
    if refusal is None:
        result = q.cli(*arguments)
    else:
        q.refused(arguments, 'Native process failed')
        assert refusal in (out / key / 'build.log').read_text(encoding='utf-8') and not (out / f'{key}.blend').exists(), key
        result = None
    assert file_hash(out / f'{source}.blend') == before
    return result


again = rebuild('yard', 'rebuilt')
assert again['replaced'] and again['source']['sha256'] == built['output_sha256']
assert q.cli('spec-compare', out / 'spec.json', out / 'rebuilt.blend', '--blender', a.blender, '--output-dir', out / 'compare-rebuilt')['passed']
rebuild('tall-bench', 'refused-edited', 'bench was edited after it was built')
rebuild('no-pot', 'refused-removed', 'built parts were removed: pot')
rebuild('foreign', 'refused-foreign', 'stray was not built by the blockout')
rebuild('id-taken', 'refused-id', 'Stable IDs already used outside the blockout: shed')

# spec-compare
same = q.cli('spec-compare', out / 'spec.json', out / 'yard.blend', '--blender', a.blender, '--output-dir', out / 'compare')
assert same['passed'] and same['findings'] == [] and same['parts_measured'] == 8 and same['source']['sha256'] == built['output_sha256']
assert same['not_measured'] == SPEC['avoid']
EXPECTED = {
    'tall-bench': {('SIZE', 'parts/bench/size'), ('PROPORTION', 'proportions/bench-top')},
    'pot-off-bench': {('POSITION', 'parts/pot/position'), ('NEVER_OUTSIDE', 'never/pot-on-bench')},
    'no-pot': {('PART_MISSING', 'parts/pot'), ('UNMEASURED', 'never/pot-above-ground'), ('UNMEASURED', 'never/pot-on-bench')},
    'bench-in-shed': {('POSITION', 'parts/bench/position'), ('NEVER_OVERLAP', 'never/bench-clear-of-shed'), ('NEVER_OUTSIDE', 'never/pot-on-bench')},
    'sunk-pot': {('POSITION', 'parts/pot/position'), ('NEVER_BELOW', 'never/pot-above-ground')}}
compared = {}
for name, expected in EXPECTED.items():
    before = file_hash(out / f'{name}.blend')
    report = q.cli('spec-compare', out / 'spec.json', out / f'{name}.blend', '--blender', a.blender, '--output-dir', out / f'compare-{name}', expect=1)
    got = {(f['code'], f['path']) for f in report['findings']}
    assert got == expected and not report['passed'] and file_hash(out / f'{name}.blend') == before, (name, got)
    assert all(f['message'] and f['remediation'] for f in report['findings'])
    compared[name] = sorted(map(list, got))
# A part whose objects carry other IDs is missing until the spec's ids name them.
missing = q.cli('spec-compare', out / 'spec.json', out / 'detailed-bench.blend', '--blender', a.blender, '--output-dir', out / 'compare-ids-1', expect=1)
assert ('PART_MISSING', 'parts/bench') in {(f['code'], f['path']) for f in missing['findings']}
mapped = save('spec-ids', variant(lambda s: s['parts'][4].update(ids=['ext.bench.*'])))
assert q.cli('spec-compare', mapped, out / 'detailed-bench.blend', '--blender', a.blender, '--output-dir', out / 'compare-ids-2')['passed']
# A part declared to rest on another but placed above it builds, and fails its relation.
floating = save('spec-floating', variant(lambda s: s['parts'][5].update(position=[-2, -1, 1.1])))
lifted = q.cli('blockout-build', floating, '--blender', a.blender, '--output', out / 'floating.blend', '--output-dir', out / 'build-floating')
gap = q.cli('relations', out / 'floating.blend', '--blender', a.blender, '--output-dir', out / 'relations-floating', '--spec', lifted['relations'], expect=1)
assert gap['relations']['rest.pot']['findings']['pot']['code'] == 'GAP' and gap['relations']['rest.shed']['passed']
production = REPO / 'runs/shed-production-2026-10-05/project/checkpoints/000009/checkpoint.blend'
study = None
if production.is_file():
    garden = q.cli('spec-compare', REPO / 'docs/studies/potting-shed.blockout.json', production, '--blender', a.blender, '--output-dir', out / 'garden')
    assert garden['passed'] and garden['parts_measured'] == 10, garden['findings']
    study = 'passed: 10 parts, 10 proportions, 4 never rules'
q.finish({'blender': a.blender, 'potting_shed_study': study, 'spec_check_refusals': refusals, 'built_parts': built['parts'], 'audit_by_code': audit['by_code'],
          'relations_passed': 5, 'rebuild': {'untouched': 'replaced', 'refused': ['edited', 'removed', 'foreign object', 'ID taken']},
          'compare': compared, 'ids_mapping': 'missing without ids, passed with ids', 'floating_part': 'GAP'})
