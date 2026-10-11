"""Native qualification of the relations command and its project history.

Builds exact bench scenes (scripts/relations_native_probe.py), checks each finding against
values computed by hand, then starts a project on the equal-legged bench on sloped ground,
records the two rigid translations a repair might try, and checks the history warnings and
the guidance. Also leaves two project copies for the fresh-agent continuation: one with the
history and one without.
"""
import json
from pathlib import Path
import shlex
import shutil

from _launcher import Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
import dcc_harness
from dcc_harness.evidence import file_hash, write_json

SPEC = {'schema': 'dcc.relations.v1', 'relations': [
    {'id': 'bench-on-ground', 'kind': 'supported_by', 'subjects': [f'bench.leg.{i}' for i in range(4)], 'support': ['ground'],
     'max_gap': 0.005, 'max_penetration': 0.01, 'footprint': 0.002}]}
DOWN, UP = ('bench.leg.0', 'bench.leg.1'), ('bench.leg.2', 'bench.leg.3')  # downhill at y = -0.23, uphill at y = +0.23


cli = q.cli


probe = Path(__file__).with_name('relations_native_probe.py').resolve()
q.blender('scenes.log', '--python', probe, '--', '--out', out / 'scenes')
write_json(out / 'relations.json', SPEC)
sources = {path.name: file_hash(path) for path in (out / 'scenes').glob('*.blend')}

# Expected finding per leg: (code, signed error in metres or None).
EXPECTED = {
    'flat': {leg: ('OK', 0.0) for leg in DOWN + UP},
    'raised': {leg: ('GAP', 0.03) for leg in DOWN + UP},
    'sunk': {leg: ('PENETRATION', -0.03) for leg in DOWN + UP},
    'off-edge': {'bench.leg.0': ('OFF_SUPPORT', None), **{leg: ('OK', 0.0) for leg in DOWN[1:] + UP}},
    'slope-fitted': {leg: ('OK', 0.0) for leg in DOWN + UP},
    'slope-equal': {**{leg: ('GAP', 0.0185) for leg in DOWN}, **{leg: ('PENETRATION', -0.0275) for leg in UP}},
    'slope-lowered': {**{leg: ('PENETRATION', -0.0215) for leg in DOWN}, **{leg: ('PENETRATION', -0.0675) for leg in UP}},
    'slope-raised': {**{leg: ('GAP', 0.0585) for leg in DOWN}, **{leg: ('GAP', 0.0125) for leg in UP}},
}
summary = {'runtime': str(runtime), 'version': dcc_harness.__version__, 'scenes': {}}
for name, expected in EXPECTED.items():
    passes = all(code == 'OK' for code, _ in expected.values())
    report = cli('relations', out / 'scenes' / (name + '.blend'), '--blender', a.blender, '--output-dir', out / ('measure-' + name),
                 '--spec', out / 'relations.json', expect=0 if passes else 1)
    relation = report['relations']['bench-on-ground']
    for leg, (code, error) in expected.items():
        found = relation['findings'][leg]
        assert found['code'] == code, (name, leg, found)
        assert error is None or abs(found['error'] - error) < 2e-4, (name, leg, found)
    summary['scenes'][name] = {'passed': report['passed'], 'conflict': relation['conflict'],
                               'codes': {leg: (f['code'], f['error']) for leg, f in relation['findings'].items()}}
assert summary['scenes']['slope-equal']['conflict'] and not summary['scenes']['slope-raised']['conflict']
fitted = json.loads((out / 'measure-slope-fitted/report.json').read_text(encoding='utf-8'))
for leg, found in fitted['relations']['bench-on-ground']['findings'].items():
    assert found['bounds_estimate']['code'] == 'PENETRATION' and not found['bounds_estimate']['agrees'], (leg, found)
    assert found['bounds_estimate']['permitted'] == 'inspect' and abs(found['spread'] - 0.009) < 2e-4, (leg, found)
flat = json.loads((out / 'measure-flat/report.json').read_text(encoding='utf-8'))
assert all(f['bounds_estimate']['agrees'] for f in flat['relations']['bench-on-ground']['findings'].values())
summary['bounds'] = {'slope-fitted': 'native OK; bounds-only PENETRATION, inspect only', 'flat': 'agrees'}

# A project on the equal-legged bench: measure through the printed step, then record two rigid translations.
observed = cli('observe', out / 'scenes/slope-equal.blend', '--blender', a.blender, '--output-dir', out / 'observe-start')
assert observed['status'] == 'READY', observed
(out / 'BRIEF.md').write_text('A bench in a sloping garden. It must stand on the ground: every leg resting on the surface, '
                              'none floating or sunk into it. Keep the bench top level and where it is.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the saved scene. The bench legs have not been checked against the slope.\n', encoding='utf-8')
write_json(out / 'decisions.json', {'relations': SPEC})
cli('start', out / 'project', '--checkpoint', out / 'scenes/slope-equal.blend', '--observation', observed['observation'],
    '--brief-file', out / 'BRIEF.md', '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
shutil.copytree(out / 'project', out / 'project-without-history')
steps = {s['id']: s for s in cli('next', out / 'project')['steps']}
command = (steps['relations']['command'].replace('<BLENDER>', a.blender).replace('<new folder>', (out / 'measure-project-initial').as_posix())
           .replace('<what you changed, or initial>', 'initial measurement'))
assert '<' not in command, command
initial = cli(*shlex.split(command)[3:], expect=1)
assert initial['recorded']['sequence'] == 1 and [w['code'] for w in initial['history']['warnings']] == ['CONFLICT'], initial['history']
for name, strategy in (('slope-lowered', 'Lowered the whole bench 4 cm'), ('slope-raised', 'Raised the whole bench 4 cm')):
    cli('relations', out / 'scenes' / (name + '.blend'), '--blender', a.blender, '--output-dir', out / ('measure-project-' + name),
        '--project', out / 'project', '--strategy', strategy, expect=1)
warnings = cli('next', out / 'project')['relation_warnings']
assert sorted((w['code'], w['subject']) for w in warnings) == [('OPPOSING', leg) for leg in DOWN + UP], warnings
assert [a['strategy'] for a in warnings[0]['attempts']] == ['Lowered the whole bench 4 cm', 'Raised the whole bench 4 cm']
brief = cli('brief', out / 'project')
assert '## Relation history' in brief and 'Raised the whole bench 4 cm' in brief and 'OPPOSING' in brief
summary['history'] = {'entries': 3, 'warnings': sorted({w['code'] for w in warnings}), 'subjects': len(warnings)}

assert {path.name: file_hash(path) for path in (out / 'scenes').glob('*.blend')} == sources, 'a measured scene changed'
summary['sources_unchanged'] = True
summary['passed'] = True
write_json(out / 'summary.json', summary)
print(json.dumps(summary, indent=2))
