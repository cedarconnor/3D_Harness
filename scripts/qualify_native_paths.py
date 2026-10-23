"""Qualify embedded-Python evidence I/O at the retained recovery-verifier path shape.

Uses only new disposable scenes and four precreated owned native user directories.
Never retries a native mutation. Every launch checks the exact effective CONFIG
before its action. Run with --blender BLENDER --out NEW_FOLDER [--runtime CHECKOUT].
"""
import os
from pathlib import Path
import subprocess
import uuid

from _launcher import Qualification, BLENDER_FLAGS
from verify_release import release_environment, native_config_probe

q = Qualification(__doc__)
from dcc_harness import evidence, files

env = release_environment(q.out)
deep = (q.out / 'native-live/11-jobs-stale-recovery-autonomous/attached/state/execution/operations'
        / str(uuid.uuid4()) / 'recovery' / ('archive-check-' + str(uuid.uuid4())))
if len(str(deep)) < 243:
    deep = deep.parent / (deep.name + '-' + 'x' * (243 - len(str(deep))))
deep.mkdir(parents=True)
assert len(str(deep)) >= 243, 'Output must retain the demonstrated deep directory shape'
evidence.write_json(q.out / 'layout.json', {'deep': str(deep), 'directory_characters': len(str(deep)),
                                         'request_characters': len(str(deep / 'verify-request.json'))})
probe = q.out / 'native-paths-probe.py'
probe.write_bytes(Path(__file__).with_name('native_paths_probe.py').read_bytes())
runtime_modules = ('files.py', 'evidence.py', 'live_snapshot.py', '_live_verify_blender.py', '_profile_blender.py')
runtime_hashes = {name: files.file_hash(q.runtime / 'dcc_harness' / name) for name in runtime_modules}
evidence.write_json(q.out / 'probe-source.json', {'probe_sha256': files.file_hash(probe),
    'runtime': str(q.runtime), 'module_hashes': runtime_hashes,
    'scope': 'Focused path boundary modules; not a full release runtime freeze'})


def launch(name, mode):
    # The bootstrap's read-only check precedes even importing the probe/runtime.
    script = q.out / (name + '-bootstrap.py')
    script.write_text(native_config_probe(Path(env['BLENDER_USER_CONFIG']), q.out / (name + '-config.json'))
                      + '\nimport runpy\nrunpy.run_path(' + repr(str(probe)) + ", run_name='__main__')\n",
                      encoding='utf-8')
    with (q.out / (name + '.log')).open('x', encoding='utf-8') as log:
        result = subprocess.run([q.args.blender, *BLENDER_FLAGS, '--python', str(script), '--',
                                 mode, str(q.runtime), str(q.out), str(deep)],
                                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    return result.returncode


payload = {'path': str(deep / 'verify-request.json'), 'unicode': '\u96ea', 'number': 7}
evidence.write_json(deep / 'verify-request.json', payload)
evidence.write_json(q.out / 'input-hash.json', {'sha256': files.file_hash(deep / 'verify-request.json')})
# A junction component itself beyond MAX_PATH catches false "missing" lstat.
junction_parent = deep / ('reparse-parent-' + 'x' * 30)
junction_parent.mkdir()
target = q.out / 'junction-target'; target.mkdir()
evidence.write_json(target / 'marker.json', {'outside': True})
junction = junction_parent / 'redirect'
junction_result = {'path': str(junction), 'created': False, 'reason': 'Windows junctions only'}
if os.name == 'nt':
    # Creation only: both arguments are fresh owned paths, no deletion or move.
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', '\\\\?\\' + str(junction), str(target)],
                             capture_output=True, text=True)
    junction_result.update(created=created.returncode == 0, exit_code=created.returncode,
                           reason=created.stdout + created.stderr)
evidence.write_json(q.out / 'junction.json', junction_result)
code = launch('io', 'io')
if code:
    raise RuntimeError('Native evidence I/O failed; inspect ' + str(q.out / 'io.log'))
profile = deep / 'profile'; profile.mkdir()
for name in ('config', 'scripts', 'datafiles', 'extensions'):
    (profile / ('verify-user-' + name)).mkdir()
evidence.write_json(profile / 'verify-request.json', {'profile': 'must not be loaded'})
assert launch('profile-refusal', 'profile-refusal') == 0, 'Exact profile CONFIG guard failed'
assert launch('fixture', 'fixture') == 0, 'Fixture failed; do not replay it'
fixture = evidence.read_json(q.out / 'fixture.json')
for spelling in ('ordinary', 'extended'):
    files.copy_verified(fixture['source']['path'], deep / ('native-open-' + spelling + '.blend'),
                        fixture['source']['sha256'], 'Native open fixture changed')
# Separate fresh verifier: use the production worker, retaining the deep request
# and outputs without copying/staging or substituting short evidence paths.
verification = deep / 'independent'
verification.mkdir()
evidence.write_json(verification / 'verify-request.json', {
    'source': fixture['source'], 'out': str(verification), 'scene': fixture['scene'],
    'snapshot': fixture['snapshot'], 'fingerprint': fixture['fingerprint'], 'inventory': fixture['inventory']})
assert launch('verify', 'verify') == 0, 'Independent saved verifier failed'
assert evidence.read_json(verification / 'verified.json') == {
    'saved_inventory_matches': True, 'saved_fingerprint_matches': True}
assert files.file_hash(fixture['source']['path']) == fixture['source']['sha256']
for spelling in ('ordinary', 'extended'):
    assert launch('native-open-' + spelling, 'native-open-' + spelling) == 0, 'Native open probe failed'
assert runtime_hashes == {name: files.file_hash(q.runtime / 'dcc_harness' / name) for name in runtime_modules}
q.finish({'io': evidence.read_json(q.out / 'io-proof.json'),
          'blender': fixture['blender'],
          'profile_guard': evidence.read_json(q.out / 'profile-refusal.json'),
          'native_save': evidence.read_json(q.out / 'native-save.json'),
          'native_open': {spelling: evidence.read_json(q.out / ('native-open-' + spelling + '.json'))
                          for spelling in ('ordinary', 'extended')},
          'junction': junction_result, 'verifier': str(verification), 'source_unchanged': True,
          'scope': 'Python evidence I/O and saved verification; bpy long asset paths are measurements, not support claims'})
