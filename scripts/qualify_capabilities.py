"""Owned synthetic-provider qualification; never activates add-ons in an artist process."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import zipfile


def gui_profile(args, out, ref):
    from dcc_harness import distribution, environments, blender_bridge
    from qualify_live import wait_for
    distribution.export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive: archive.extractall(out / 'addon')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
    script = out / 'gui.py'
    config = {'out':str(out), 'profile':ref, 'port':port}
    script.write_text('CONFIG = ' + repr(config) + '\n' + '''
import bpy, json, sys, time
from pathlib import Path
out = Path(CONFIG['out']); sys.path.insert(0, str(out / 'addon'))
attempts = []
def audit(event, args):
    if event == 'socket.connect':
        attempts.append(str(args[1])); raise RuntimeError('Unexpected outbound connection')
sys.addaudithook(audit)
watched = ('undo_post','redo_post','depsgraph_update_post')
before = {name:tuple(getattr(bpy.app.handlers,name)) for name in watched}
import dcc_harness_bridge as bridge
from dcc_harness_bridge import addons
profile = json.loads(Path(CONFIG['profile']['path']).read_text())
# A timestamp/size-valid stale pyc must not override the profile's pinned source.
import os, py_compile
entry = Path(next(p['entry'] for p in profile['providers'] if p['id'] == 'harness_fixture'))
source = entry.read_bytes(); stamp = entry.stat()
stale = source.replace(b"['profile_fixture'] = 1", b"['profile_fixture'] = 9")
assert stale != source and len(stale) == len(source)
entry.write_bytes(stale); os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
py_compile.compile(str(entry), doraise=True)
entry.write_bytes(source); os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
delta = addons.enable_profile(profile)
assert set(delta['enabled_delta']) == {p['id'] for p in profile['providers']} and not delta['preferences_saved']
assert 'import_sentinel' not in sys.modules
assert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}
assert bpy.context.object['profile_fixture'] == 1
bridge.register(); bridge.server = bridge.ObservationServer(CONFIG['port'], out); bridge.server.start()
(out / 'ready.json').write_text(json.dumps({'descriptor':str(bridge.server.session.descriptor_path)}))
deadline = time.monotonic() + 90
def control():
    if (out / 'stop').exists() or time.monotonic() > deadline:
        bridge.server.stop(); bridge.unregister()
        assert all(tuple(getattr(bpy.app.handlers,name)) == before[name] for name in watched)
        assert not any(name == 'dcc_harness' or name.startswith('dcc_harness.') for name in sys.modules)
        (out / 'gui-audit.json').write_text(json.dumps({'outbound_attempts':attempts,
            'standalone_export':True, 'activity_handlers_unchanged':True, 'delta':delta}))
        bpy.ops.wm.quit_blender(); return None
    return .1
bpy.app.timers.register(control)
''', encoding='utf-8')
    startup = None
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    config_dir = out / 'gui-config'; config_dir.mkdir()
    with (out / 'gui.log').open('x') as log:
        process = subprocess.Popen([args.blender, '--offline-mode', '--factory-startup', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(script)], stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, startupinfo=startup, env={**os.environ, 'BLENDER_USER_CONFIG':str(config_dir),
                'BLENDER_USER_EXTENSIONS':str(out / 'gui-extensions')})
        token = None
        try:
            wait_for(lambda:(out / 'ready.json').exists(), process)
            binding = json.loads((out / 'ready.json').read_text())['descriptor']
            token = blender_bridge.descriptor(binding)['token']
            blender_bridge.observe('ping', port=port, timeout=10)
            result = environments.inventory(binding, blender=args.blender)
            provider = next(p for p in result['providers'] if p['id'] == 'harness_fixture')
            assert provider['enabled'] and provider['loaded_identity'] == 'matched'
            assert 'object.harness_fixture_mark' in provider['operators']
            assert token not in json.dumps(result)
            (out / 'gui-inventory.json').write_text(json.dumps(result, indent=2))
        finally:
            (out / 'stop').write_text('stop')
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)
        assert process.returncode == 0 and (out / 'gui-audit.json').exists()
    audit = json.loads((out / 'gui-audit.json').read_text())
    assert not audit['outbound_attempts'] and not (config_dir / 'userpref.blend').exists()
    if token:
        for path in out.rglob('*'):
            if path.is_file():
                assert token.encode() not in path.read_bytes(), 'Retained private token'
    return audit


def profiles(args):
    runtime = Path(args.runtime).resolve(); sys.path.insert(0, str(runtime))
    from dcc_harness import environments
    from dcc_harness.native import run_worker
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    fixtures = Path(__file__).resolve().parents[1] / 'tests/fixtures/addons'
    shutil.copytree(fixtures, out / 'providers')
    roots = [{'path':str(out / 'providers/legacy'), 'namespace':''},
             {'path':str(out / 'providers/extensions'), 'namespace':'bl_ext.fixture'}]
    first = environments.inventory(blender=args.blender, roots=roots, out=out / 'factory')
    provider = next(p for p in first['providers'] if p['id'] == 'harness_fixture')
    assert not provider['enabled'] and provider['loaded_identity'] == 'not_loaded'
    ref = environments.create_profile(out / 'project', first, ['harness_fixture', 'bl_ext.fixture.example_extension'],
                                      {'harness_fixture':{'quality':3}})
    gui = gui_profile(args, out, ref)
    probe = out / 'probe.py'
    probe.write_text('''
from pathlib import Path
import json, sys, bpy
from dcc_harness.environments import load_profile
from dcc_harness.data.bridge import addons
from dcc_harness.evidence import read_json, write_json
action, request_path = sys.argv[sys.argv.index('--') + 1:]
request = read_json(request_path); folder = Path(request_path).parent
profile = load_profile(request['profile']); initial = addons.assert_profile(profile)
assert bpy.context.preferences.addons['harness_fixture'].preferences.quality == 3
if action == 'execute':
    assert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}
    assert bpy.data.objects['Cube']['profile_fixture'] == 1
    bpy.ops.wm.save_as_mainfile(filepath=request['candidate'])
else:
    bpy.ops.wm.open_mainfile(filepath=request['candidate'])
    assert bpy.data.objects['Cube']['profile_fixture'] == 1
    assert bpy.ops.object.harness_fixture_mark.poll()
assert addons.assert_profile(profile) == initial
write_json(folder / 'result.json', {'passed':True, 'profile':initial,
    'quality':bpy.context.preferences.addons['harness_fixture'].preferences.quality})
''', encoding='utf-8')
    reports = []
    for action in ('execute', 'verify'):
        folder = out / action; folder.mkdir()
        run_worker(args.blender, folder, probe, action, {'candidate':str(out / 'candidate.blend')}, profile=ref, timeout=60)
        reports.append(json.loads((folder / 'result.json').read_text()))
    assert reports[0]['profile']['profile_digest'] == reports[1]['profile']['profile_digest']
    # Exercise the actual managed execution and independent observation workers.
    import dcc_harness
    from dcc_harness.evidence import file_hash
    package = Path(dcc_harness.__file__).parent
    script = out / 'managed-script.py'
    script.write_text("import bpy\nassert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}\n")
    candidate = out / 'managed.blend'
    folder = out / 'managed-execute'; folder.mkdir()
    run_worker(args.blender, folder, package / '_execution_blender.py', 'execute', {
        'source':{'path':str(out / 'candidate.blend'), 'sha256':file_hash(out / 'candidate.blend')},
        'script':str(script), 'script_sha256':file_hash(script), 'output':str(candidate)}, profile=ref, timeout=60)
    folder = out / 'managed-observe'; folder.mkdir()
    run_worker(args.blender, folder, package / '_observe_blender.py', 'observe', {
        'source':{'path':str(candidate), 'sha256':file_hash(candidate)}, 'out':str(folder), 'compact':False},
        profile=ref, timeout=60)
    assert (folder / 'observation.json').exists()
    # A GUI-only provider must fail in the verifier, never pass in factory mode.
    entry = out / 'providers/legacy/harness_fixture/__init__.py'
    entry.write_text(entry.read_text() + '\nif bpy.app.background: raise RuntimeError("GUI_ONLY")\n')
    changed = environments.inventory(blender=args.blender, roots=roots, out=out / 'changed')
    gui_only = environments.create_profile(out / 'project', changed, ['harness_fixture'], {})
    folder = out / 'gui-only-verifier'; folder.mkdir()
    try:
        run_worker(args.blender, folder, probe, 'verify', {'candidate':str(candidate)}, profile=gui_only, timeout=60)
    except RuntimeError:
        assert not (folder / 'result.json').exists()
        assert json.loads((folder / 'verify-environment.json').read_text())['state'] == 'FAILED_OR_PARTIAL'
    else:
        raise AssertionError('GUI-only verifier incorrectly passed')
    result = {'passed':True, 'case':'profiles', 'factory_provider_disabled':True,
              'execution_and_independent_verifier_profile_matched':True, 'desktop_provider_enabled':True,
              'managed_workers_passed':True, 'stale_bytecode_ignored':True, 'gui_only_verifier_refused':True,
              'gui':gui, 'reports':reports}
    (out / 'VERIFICATION.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True); parser.add_argument('--blender', required=True)
    parser.add_argument('--out', required=True); parser.add_argument('--case', choices=['profiles'], default='profiles')
    profiles(parser.parse_args())
