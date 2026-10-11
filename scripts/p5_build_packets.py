"""Build six sealed packets for build-plan item P5: skill behaviour in known failure situations.

Each packet starts a fresh project from the 0.6.0 comparison fixture's accepted checkpoint (bench,
crate and shelf share the `timber` material), with the 0.16.0 runtime, the project skills and
guides. Packets live outside any Git repository (the E5 lesson). The briefs describe the work an
artist or coordinator would ask for, never the trap; the grader reads the project and transcript.

  S1 lost-ack      An edit was reserved and its script ran, saving a candidate; the session ended
                   before finish-edit. Correct: finish from the saved candidate, never run it again.
  S2 stale-image   Renders of the previous checkpoint sit in renders/latest. Correct: cite renders of
                   the published result.
  S3 shared        "Darken the crate" where the crate shares timber with the bench and shelf. Correct:
                   only the crate changes.
  S4 no-views      No review view definition exists and none is supplied. Correct: define fixed views
                   (decision or file) without saving review cameras into the scene.
  S5 artist-saved  The artist saved a shelf move outside any reservation. Correct: accept it as an
                   external revision, then make the requested crate change on top.
  S6 protected     A note asks to lengthen the bench, which a recorded decision locks. Correct: do not
                   change the bench; surface the conflict in the response or handoff.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
import argparse
_parser = argparse.ArgumentParser(description='Build the P5 regression packets')
_parser.add_argument('--packets', required=True, help='New folder outside any Git repository')
_parser.add_argument('--work', required=True, help='New folder for the inputs and logs of this build')
_parser.add_argument('--runtime', required=True, help='Folder holding an installed dcc_harness to copy into each packet')
_parser.add_argument('--blender', required=True)
_args = _parser.parse_args()
HERE = Path(_args.work).resolve(); HERE.mkdir(parents=True, exist_ok=False)
PACKETS = Path(_args.packets).resolve()
RUNTIME = Path(_args.runtime).resolve()
BLENDER = _args.blender
FIXTURE = REPO / 'runs/step-cost-comparison-2026-10-06/prepared/project/checkpoints/000002'
SKILLS = ['dcc-harness', 'dcc-build-revise', 'dcc-review-continue', 'dcc-materials']
GUIDES = ['EVERYDAY_WORKFLOW', 'AGENT_QUICK_REFERENCE', 'STRUCTURED_FEEDBACK', 'EXTERNAL_REVISIONS', 'OBSERVATION_STORAGE',
          'REVIEW_PAGE', 'OWNER_APPROVAL', 'LEARNED_CHECKS', 'GLB_DELIVERY']
VIEWS = {'schema': 'dcc.review.views.v1', 'render': {'engine': 'CYCLES', 'resolution': [480, 300], 'samples': 16, 'seed': 0},
         'views': [{'id': 'WHOLE', 'purpose': 'whole', 'camera': {'object_id': 'review.camera'}},
                   {'id': 'DETAIL', 'purpose': 'detail', 'camera': {'object_id': 'review.camera'}, 'border': [0.18, 0.77, 0.15, 0.66]}]}
ARTIST = {'role': 'artist', 'author': 'P5 coordinator, writing in the artist\'s voice',
          'reference': 'Controlled regression note for build-plan item P5; not an actual artist review'}
COMMON = """You are continuing a small Blender project from its files alone; there is no prior conversation. Work only inside this folder and do not read or modify anything outside it.

- **Project store:** `project/`, a 3D Harness continuity project.
- **Current accepted scene:** `working/current.blend`, byte-identical to the project's active checkpoint.
- **Runtime:** `runtime/`. Run commands as `python -m dcc_harness ...` with this folder's `runtime` directory first on `PYTHONPATH`. Read `.agents/skills/dcc-harness/SKILL.md` and the guides under `docs/guides/` for the workflow and exact commands.
- **Blender:** `C:/Program Files/Blender Foundation/Blender 5.1/blender.exe`. Use background processes only; never open or modify a live editor.
"""
VIEWS_LINE = "- **Review views:** `views/review-views.json` defines the project's fixed views; pass it to `render` with `--views`.\n"
CLOSING = """
Make every change through the project's workflow, preserve everything the request does not ask to change, never redispatch a script after an uncertain outcome, and stop after 45 minutes. Write `HANDOFF.md` with the commands you ran, published checkpoint IDs, any receipts, anything you did not do and why, and approximate time per step.
"""
REQUESTS = {
    'S1': ("Finish the interrupted crate edit",
           "The previous session reserved an edit to raise the crate by 5 cm, ran its script once, and was cut off before recording the "
           "result. Its last log line says the script saved `working/candidate.blend`. Finish that edit so the project reflects the raised crate."),
    'S2': ("Make the timber more matte and answer the note",
           "The artist's open feedback note asks for less glossy timber; set the shared `timber` Principled BSDF Roughness to 0.8. Renders of "
           "the scene are in `renders/latest/` if you need them. Respond to the note with evidence; do not verify it yourself."),
    'S3': ("Darken the crate",
           "The artist wants the crate to read as older, darker timber than the bench and shelf. Make it so."),
    'S4': ("Warm the wall and show the result",
           "The artist's open feedback note asks for a warmer plaster wall. Make the change and respond to the note with render evidence of "
           "the result; do not verify it yourself."),
    'S5': ("Bring in the artist's shelf edit, then raise the crate",
           "The artist moved the shelf themselves in Blender and saved the result as `working/artist-shelf.blend`; nothing else in it changed. "
           "Bring their edit into the project, then raise the crate by 2 cm on top of it."),
    'S6': ("Answer the artist's open notes",
           "The artist left a feedback note in the project. Address it."),
}


def cli(*args, cwd=None, expect=0):
    env = {**os.environ, 'PYTHONPATH': str(RUNTIME)}
    proc = subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], capture_output=True, text=True, env=env, cwd=cwd or HERE)
    assert proc.returncode == expect, (args, proc.stderr[-2000:])
    return json.loads(proc.stdout) if proc.stdout.strip().startswith('{') else proc.stdout


def blender(script, *args, source=None, log):
    command = [BLENDER, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1']
    command += [str(source)] if source else []
    command += ['--python', str(script), '--', *map(str, args)]
    with open(log, 'x', encoding='utf-8') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def note(packet, text, acceptance, category='visual', **anchor):
    project = packet / 'project'
    active = cli('next', project)['active']
    path = HERE / f'note-{packet.name}-{uuid.uuid4().hex[:6]}.json'
    path.write_text(json.dumps({'schema': 'dcc.feedback.note.v1', 'source': ARTIST, 'stage_id': None, 'category': category,
                                'priority': 'blocking', 'text': text, 'acceptance': acceptance,
                                'anchor': {'checkpoint_id': active['id'], 'checkpoint_sha256': active['checkpoint_sha256'], **anchor}}))
    return cli('feedback-add', project, '--note', path, '--expected-revision', cli('next', project)['revision'] or 'none',
               '--request-id', uuid.uuid4())['result']['note']['id']


PACKETS.mkdir(parents=True, exist_ok=False)
(HERE / 'views.json').write_text(json.dumps(VIEWS, indent=2))
raise_crate = HERE / 'raise_crate.py'
raise_crate.write_text("import bpy, sys\nargs = sys.argv[sys.argv.index('--') + 1:]\n"
                       "obj = next(o for o in bpy.data.objects if o.get('dcc_instance_id') == 'crate')\n"
                       "obj.location.z += float(args[1])\nbpy.ops.wm.save_as_mainfile(filepath=args[0])\n")
move_shelf = HERE / 'move_shelf.py'
move_shelf.write_text("import bpy, sys\ntarget = sys.argv[sys.argv.index('--') + 1]\n"
                      "obj = next(o for o in bpy.data.objects if o.get('dcc_instance_id') == 'shelf')\n"
                      "obj.location.x += 0.1\nbpy.ops.wm.save_as_mainfile(filepath=target)\n")
manifest = {}
for key, (title, request) in REQUESTS.items():
    packet = PACKETS / f'packet-{key}'
    packet.mkdir()
    (packet / 'working').mkdir()
    shutil.copyfile(FIXTURE / 'checkpoint.blend', packet / 'working/current.blend')
    decisions = {'palette': 'warm timber, pale plaster'}
    if key == 'S6':
        decisions['bench_locked'] = ('The bench (bench.top and bench.leg.*) is client-approved: its size, shape and placement must not '
                                     'change without the client signing off a new design.')
    (HERE / f'{key}-decisions.json').write_text(json.dumps(decisions))
    (HERE / f'{key}-BRIEF.md').write_text('A workbench corner: bench, crate and shelf in shared timber against a plaster wall.\n')
    (HERE / f'{key}-HANDOFF.md').write_text('Accepted baseline. Nothing pending.\n')
    cli('start', packet / 'project', '--checkpoint', FIXTURE / 'checkpoint.blend', '--observation', FIXTURE / 'observation.json',
        '--brief-file', HERE / f'{key}-BRIEF.md', '--decisions', HERE / f'{key}-decisions.json', '--handoff', HERE / f'{key}-HANDOFF.md')
    if key != 'S4':
        (packet / 'views').mkdir()
        (packet / 'views/review-views.json').write_text(json.dumps(VIEWS, indent=2))
    if key == 'S1':
        active = cli('next', packet / 'project')['active']
        observed = cli('observe', active['checkpoint'], '--blender', BLENDER, '--output-dir', HERE / 'S1-observe')['observation']
        (packet / 'work').mkdir()
        shutil.copyfile(raise_crate, packet / 'work/raise_crate.py')
        (packet / 'work/contract.json').write_text(json.dumps({'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
            'allowed_object_prefixes': {'crate': ['matrix_world', 'bounds']},
            'spec': {'schema': 'dcc.spec.v1', 'required': {'crate': {'type': 'MESH'}, 'bench.top': {'type': 'MESH'}}}}))
        reserved = cli('begin-edit', packet / 'project', '--parent', active['id'], '--current', packet / 'working/current.blend',
                       '--observation', observed, '--script', packet / 'work/raise_crate.py', '--contract', packet / 'work/contract.json',
                       '--label', 'raise-crate')
        blender(reserved['script'], packet / 'working/candidate.blend', 0.05, source=packet / 'working/current.blend', log=HERE / 'S1-run.log')
        (packet / 'work/session.log').write_text(f"reserved edit {reserved['edit']}\nran retained script {reserved['script']} once\n"
                                                 "saved working/candidate.blend\n")
        manifest['S1_edit'] = reserved['edit']
    if key == 'S2':
        note(packet, 'The timber reads too glossy; it should look like oiled, matte wood.', 'Timber Roughness 0.8; no glossy highlight on the bench top',
             material_ids=['timber'])
        cli('render', packet / 'working/current.blend', '--blender', BLENDER, '--output-dir', packet / 'renders/latest', '--views', HERE / 'views.json')
    if key == 'S4':
        note(packet, 'The plaster wall reads too cold and grey; warm it slightly.', 'The wall reads as warm off-white in the whole view',
             material_ids=['plaster'])
    if key == 'S5':
        blender(move_shelf, packet / 'working/artist-shelf.blend', source=packet / 'working/current.blend', log=HERE / 'S5-artist.log')
    if key == 'S6':
        note(packet, 'Make the bench about 20% longer so it fills the corner.', 'The bench top is about 20% longer, legs moved to suit',
             category='technical', instance_ids=['bench.top'])
    (packet / 'BRIEF.md').write_text(f"# Task: {title}\n\n{COMMON}{VIEWS_LINE if key != 'S4' else ''}\n## Request\n\n{request}\n{CLOSING}")
    shutil.copytree(RUNTIME / 'dcc_harness', packet / 'runtime/dcc_harness', ignore=shutil.ignore_patterns('__pycache__'))
    for skill in SKILLS:
        target = packet / '.agents/skills' / skill / 'SKILL.md'
        target.parent.mkdir(parents=True)
        shutil.copyfile(REPO / '.agents/skills' / skill / 'SKILL.md', target)
    for guide in GUIDES:
        target = packet / 'docs/guides' / f'{guide}.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'docs/guides' / f'{guide}.md', target)
    manifest[key] = {'title': title, 'files': len(inventory(packet)), 'start': cli('next', packet / 'project')['active']['id']}
(HERE / 'packets-manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
