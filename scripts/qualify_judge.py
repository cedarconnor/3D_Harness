"""Native qualification of the judge loop (build-plan item G6), with real evidence from the other commands.

Builds a small blockout, a copy with one part inside out, and a copy with one part off its spec.
Each candidate gets a real audit, spec-compare, review sheet and render. The loop must record the
inside-out and off-spec candidates as gated rounds with no judge packet, accept the good one, and
then, fed scripted verdicts that name the same gap twice with no point gained, require a change of approach, refuse a
round that does not make one, and stop and ask when the changed approach gains nothing.
"""
from _launcher import Qualification
q = Qualification(__doc__)
a, out = q.args, q.out
from dcc_harness.evidence import read_json, write_json

SPEC = {'schema': 'dcc.blockout.v1', 'name': 'stand', 'units': 'metres', 'up': 'Z', 'parts': [
    {'name': 'ground', 'category': 'ground', 'primitive': 'plane', 'position': [0, 0, 0], 'size': [3, 3, 0]},
    {'name': 'plinth', 'category': 'furniture', 'primitive': 'box', 'position': [0, 0, 0], 'size': [0.6, 0.6, 0.5], 'rests_on': 'ground'},
    {'name': 'urn', 'category': 'prop', 'primitive': 'cylinder', 'position': [0, 0, 0.5], 'size': [0.3, 0.3, 0.4], 'rests_on': 'plinth'}]}
write_json(out / 'spec.json', SPEC)
write_json(out / 'views.json', {'schema': 'dcc.review.views.v1', 'render': {'engine': 'BLENDER_WORKBENCH', 'resolution': [400, 300], 'samples': 8, 'seed': 0},
                                'views': [{'id': 'hero', 'purpose': 'whole', 'camera': {'lens': 35, 'location': [2.4, -2.4, 1.6], 'target': [0, 0, 0.4]}}]})
write_json(out / 'target.json', {'schema': 'dcc.judge.target.v1', 'brief': 'A stone urn on a plinth in a bare yard.', 'spec': {'path': 'spec.json'},
                                 'targets': [{'id': 'weathered-stone', 'intent': 'The urn and plinth read as weathered stone.'}]})
q.cli('blockout-build', out / 'spec.json', '--blender', a.blender, '--output', out / 'good.blend', '--output-dir', out / 'build')
editor = out / 'edit.py'
editor.write_text(
    "import bpy, sys\n"
    "source, target, change = sys.argv[sys.argv.index('--') + 1:]\n"
    "bpy.ops.wm.open_mainfile(filepath=source)\n"
    "urn = next(o for o in bpy.data.objects if o.get('dcc_instance_id') == 'urn')\n"
    "if change == 'inside-out': urn.data.flip_normals()\n"
    "elif change == 'off-spec': urn.scale = (2.5, 2.5, 1)\n"
    "elif change == 'nudged': urn.rotation_euler.z = 0.3\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target)\n", encoding='utf-8')
for change in ('inside-out', 'off-spec', 'nudged'):
    q.blender(f'edit-{change}.log', '--python', editor, '--', out / 'good.blend', out / f'{change}.blend', change)


def evidence(name, key, approach, **extra):
    """Run the real checks on one candidate and write the round's evidence document."""
    folder = out / key
    folder.mkdir()
    source = out / f'{name}.blend'
    q.cli('audit', source, '--blender', a.blender, '--output-dir', folder / 'audit', expect=None if name == 'inside-out' else 0)
    q.cli('spec-compare', out / 'spec.json', source, '--blender', a.blender, '--output-dir', folder / 'compare', expect=None if name == 'off-spec' else 0)
    q.cli('review-sheet', source, '--blender', a.blender, '--output-dir', folder / 'sheet', '--width', '800')
    q.cli('render', source, '--blender', a.blender, '--output-dir', folder / 'views', '--views', out / 'views.json')
    write_json(folder / 'evidence.json', {
        'schema': 'dcc.judge.evidence.v1', 'approach': approach, 'checkpoint': {'path': str(source)}, 'audit': {'path': 'audit/report.json'},
        'spec_compare': {'path': 'compare/report.json'}, 'sheet': {'path': 'sheet/receipt.json'}, 'views': {'path': 'views/receipt.json'}, **extra})
    return folder / 'evidence.json'


def verdict(key, total, gap):
    scores, left = {}, total
    for line, most in (('composition', 3), ('lighting', 3), ('materials', 3), ('detail', 1)):
        scores[line] = min(most, left)
        left -= scores[line]
    write_json(out / f'verdict-{key}.json', {'schema': 'dcc.judge.verdict.v1', 'judge': {'author': 'scripted fixture', 'context': 'same'}, 'scores': scores,
                                             'gaps': [{'id': gap, 'where': 'hero view, urn', 'problem': 'reads as flat grey, not weathered stone'}],
                                             'summary': 'Scripted verdict for the stall fixture; no image was judged.'})
    return q.cli('judge-verdict', out / 'loop', '--verdict', out / f'verdict-{key}.json')


loop = out / 'loop'
assert q.cli('judge-start', loop, '--target', out / 'target.json')['next'] == 'build'
# Code checks gate the judge: neither failing candidate produces a packet.
inward = q.cli('judge-round', loop, '--evidence', evidence('inside-out', 'r1', 'first build'), expect=1)
assert inward['status'] == 'gated' and 'NORMALS_INWARD' in inward['gate_failures'][0] and 'packet' not in inward and inward['next'] == 'fix_gates'
offspec = q.cli('judge-round', loop, '--evidence', evidence('off-spec', 'r2', 'first build, normals fixed'), expect=1)
assert offspec['status'] == 'gated' and 'SIZE parts/urn/size' in offspec['gate_failures'][0] and not list((loop / 'packets').iterdir())
q.refused(['judge-verdict', loop, '--verdict', out / 'target.json'], 'No round is waiting')
# A clean candidate reaches the judge with its images.
clean = q.cli('judge-round', loop, '--evidence', evidence('good', 'r3', 'first build, to spec'))
packet = read_json(clean['packet'])
assert clean['status'] == 'awaiting_verdict' and set(packet['images']) == {'hero', 'sheet'} and packet['previous'] is None
assert verdict('r3', 4, 'flat-grey')['next'] == 'continue'
# The same gap named twice stalls the loop.
q.cli('judge-round', loop, '--evidence', evidence('nudged', 'r4', 'first build, to spec'))
stalled = verdict('r4', 4, 'flat-grey')
assert stalled['next'] == 'change_approach' and 'flat-grey' in stalled['reason'] and not stalled['stopped']
same = evidence('good', 'r5-same', 'first build, to spec')
q.refused(['judge-round', loop, '--evidence', same], 'different approach')
assert q.cli('judge-status', loop)['rounds_used'] == 4
changed = evidence('nudged', 'r5', 'rebuilt as one sculpted mesh', changed_approach='Replaced the primitives with a single sculpted mesh.')
assert q.cli('judge-round', loop, '--evidence', changed)['status'] == 'awaiting_verdict'
ended = verdict('r5', 4, 'other-gap')
assert ended['next'] == 'stop_ask' and ended['stopped'] and 'not owner acceptance' in ended['attribution']
q.refused(['judge-round', loop, '--evidence', same], 'stopped')
state = q.cli('judge-status', loop)
assert [r['status'] for r in state['rounds']] == ['gated', 'gated', 'judged', 'judged', 'judged'] and [r['score'] for r in state['rounds']] == [None, None, 4, 4, 4]
q.finish({'blender': a.blender, 'rounds': [{k: r[k] for k in ('round', 'status', 'score', 'gaps', 'gate_failures')} for r in state['rounds']],
          'stall': stalled['reason'], 'stop': ended['reason'], 'next': state['next']})
