"""Native qualification of build-plan item M6: when an observation can claim a clean saved state.

Blender does not mark edits made from Python as modified, so `bpy.data.is_dirty` stays false after them.
Checks, on a saved scene:
- a background observation straight after opening is clean and unchanged in form;
- the documented limit: a background script that edits without saving still observes as clean;
- an interactive session observes as dirty with a reason, before and after an edit, and refuses visibility;
- `start` refuses the interactive observation and accepts the background one;
- the `observe` command, whose launcher now passes --offline-mode, reports READY.

python scripts/qualify_saved_state.py --blender BLENDER --out NEW_FOLDER [--runtime CHECKOUT]
"""
from pathlib import Path
import subprocess

from _launcher import Qualification

q = Qualification(__doc__.splitlines()[0])
probe = Path(__file__).with_name('saved_state_native_probe.py').resolve()
fixtures = q.out / 'fixtures'
q.blender('build.log', '--python', probe, '--', 'build', '--runtime', q.runtime, '--out', fixtures)
source = fixtures / 'clean.blend'

from dcc_harness.evidence import file_hash, read_json, write_json

sha = file_hash(source)


def run_probe(name, interactive):
    out = q.out / (name + '.json')
    flags = ['--factory-startup', '--disable-autoexec'] + ([] if interactive else ['--background', '--python-exit-code', '1'])
    with (q.out / (name + '.log')).open('x', encoding='utf-8') as log:
        subprocess.run([q.args.blender, *flags, '--python', str(probe), '--', 'probe', '--runtime', str(q.runtime),
                        '--source', str(source), '--out', str(out)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    assert file_hash(source) == sha, 'The probe changed the saved scene'
    return read_json(out)


background = run_probe('background', interactive=False)
assert background['background'] is True
assert background['opened']['native_dirty'] is False and background['opened']['native_dirty_reason'] is None, background
assert background['opened']['checkpoint_sha256'] == sha
# The documented limit: nothing in a background process marks the Python edit.
assert background['is_dirty_after_python_edit'] is False, background
assert background['edited']['native_dirty'] is False, background
assert background['edited']['revision'] != background['opened']['revision'], background

interactive = run_probe('interactive', interactive=True)
assert interactive['background'] is False
assert interactive['is_dirty_after_python_edit'] is False, interactive
for when in ('opened', 'edited'):
    assert interactive[when]['native_dirty'] is True, (when, interactive)
    assert 'observe' in (interactive[when]['native_dirty_reason'] or ''), (when, interactive)
assert 'background process' in interactive['visibility_opened'], interactive

brief = q.out / 'brief.md'
brief.write_text('M6 saved-state qualification.\n', encoding='utf-8')
decisions = q.out / 'decisions.json'
write_json(decisions, {})
refusal = q.refused(['start', q.out / 'project-interactive', '--checkpoint', source,
                     '--observation', q.out / 'interactive-opened-observation.json',
                     '--brief-file', brief, '--decisions', decisions], 'Observe a saved, clean native checkpoint')

observed = q.cli('observe', source, '--blender', q.args.blender, '--output-dir', q.out / 'observe-command')
assert observed['status'] == 'READY', observed
request = read_json(q.out / 'observe-command' / 'observe-request.json')
assert request['source']['sha256'] == sha
started = q.cli('start', q.out / 'project-background', '--checkpoint', source,
                '--observation', q.out / 'background-opened-observation.json', '--brief-file', brief, '--decisions', decisions)

q.finish({'blender': background['blender'], 'source_sha256': sha,
          'background_opened_clean': True, 'background_edit_unmarked': True,
          'interactive_reason': interactive['opened']['native_dirty_reason'],
          'interactive_visibility': interactive['visibility_opened'],
          'start_refused_interactive': refusal, 'start_accepted_background': bool(started),
          'observe_command': observed['status']})
