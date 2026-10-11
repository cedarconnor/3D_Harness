"""Native qualification of the Blender craft skill library.

Extracts every `python verify` block from `.agents/skills/blender-*/SKILL.md` and runs each skill's
blocks in its own background Blender through blender_skills_native.py. Every block must pass.
`--only NAME` limits the run to named skills.
"""
import json
import re

from _launcher import REPO, Qualification

q = Qualification(__doc__, [('--only', {'nargs': '*', 'default': None})])
VERIFY = re.compile(r'^```python verify\n(.*?)^```', re.M | re.S)

summary, failures = {}, []
for skill in sorted((REPO / '.agents/skills').glob('blender-*/SKILL.md')):
    name = skill.parent.name
    blocks = VERIFY.findall(skill.read_text(encoding='utf-8'))
    if not blocks or (q.args.only and name not in q.args.only):
        continue
    folder = q.out / name
    folder.mkdir()
    for index, block in enumerate(blocks):
        (folder / f'block-{index:02d}.py').write_text(block, encoding='utf-8')
    q.blender(f'{name}.log', '--python', REPO / 'scripts/blender_skills_native.py', '--', folder, folder / 'results.json')
    report = json.loads((folder / 'results.json').read_text(encoding='utf-8'))
    summary[name] = {'blocks': len(blocks), 'seconds': round(sum(r['seconds'] for r in report['results']), 1),
                     'blender': report['blender']}
    failures += [{'skill': name, **r} for r in report['results'] if not r['passed']]

for failure in failures:
    print(f"FAILED {failure['skill']} {failure['block']}\n{failure['error']}")
assert summary and not failures, f'{len(failures)} failing blocks'
q.finish({'skills': summary, 'blocks': sum(s['blocks'] for s in summary.values())})
