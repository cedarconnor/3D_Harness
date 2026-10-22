"""Disposable GUI qualification of the exported live bridge; never uses an artist process."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile


def wait_for(predicate, process, seconds=60):
    end = time.monotonic() + seconds
    while not predicate():
        if process.poll() is not None or time.monotonic() >= end:
            raise RuntimeError('Owned live fixture stopped or timed out; inspect bridge.log')
        time.sleep(.1)


def protocol(args):
    sys.path.insert(0, str(Path(args.runtime).resolve()))
    from dcc_harness import blender_bridge, distribution
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    distribution.export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive:
        archive.extractall(out / 'addon')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
    config = {'out': str(out), 'port': port}
    fixture = out / 'fixture.py'
    fixture.write_text('CONFIG = ' + repr(config) + '\n' + '''
import bpy, json, sys, time
from pathlib import Path
out = Path(CONFIG['out'])
sys.path.insert(0, str(out / 'addon'))
attempts = []
def audit(event, args):
    if event == 'socket.connect':
        attempts.append(str(args[1]))
        raise RuntimeError('Unexpected outbound connection')
sys.addaudithook(audit)
watched = ('undo_post', 'redo_post', 'depsgraph_update_post')
before = {n: tuple(getattr(bpy.app.handlers, n)) for n in watched}
import dcc_harness_bridge as bridge
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.data.objects['Cube']
obj['dcc_instance_id'] = 'instance.fixture'
obj.modifiers.new('Bevel', 'BEVEL')
mat = bpy.data.materials.new('Material'); mat.use_nodes = True
obj.data.materials.append(mat)
other = obj.copy(); other.data = obj.data.copy(); other['dcc_instance_id'] = 'instance.other'
bpy.context.scene.collection.objects.link(other)
for i in range(2):
    duplicate = obj.copy(); duplicate['dcc_instance_id'] = 'instance.duplicate'
    bpy.context.scene.collection.objects.link(duplicate)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'fixture.blend'))
bridge.register()
bridge.server = bridge.ObservationServer(CONFIG['port'], out)
bridge.server.start()
assert bridge.server.running
(out / 'ready.json').write_text(json.dumps({'descriptor': str(bridge.server.session.descriptor_path)}))
deadline = time.monotonic() + 120
def control():
    if (out / 'stop').exists() or time.monotonic() > deadline:
        bridge.unregister()
        assert {n: tuple(getattr(bpy.app.handlers, n)) for n in watched} == before
        assert not attempts
        (out / 'audit.json').write_text(json.dumps({'outbound_attempts': attempts, 'activity_handlers_unchanged': True}))
        bpy.ops.wm.quit_blender()
        return None
    if (out / 'reload').exists():
        (out / 'reload').unlink()
        bpy.ops.wm.open_mainfile(filepath=str(out / 'fixture.blend'))
    return .1
bpy.app.timers.register(control, persistent=True)
''', encoding='utf-8')
    startup = None
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    with (out / 'bridge.log').open('x') as log:
        process = subprocess.Popen([args.blender, '--offline-mode', '--factory-startup', '--disable-autoexec',
                                    '--python-exit-code', '1', '--python', str(fixture)],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            wait_for(lambda: (out / 'ready.json').exists(), process)
            binding = Path(json.loads((out / 'ready.json').read_text())['descriptor'])
            private = blender_bridge.descriptor(binding)
            info = blender_bridge.call('session_describe', {}, binding=binding)
            scene = info['scenes'][0]
            assert private['token'] not in json.dumps(info)
            query = {'kind': 'objects', 'scene': scene, 'limit': 1}
            result = blender_bridge.call('inspect', query, binding=binding)
            assert result['total'] == 4 and len(result['items']) == 1 and result['next_offset'] == 1
            for kind in ('materials', 'images', 'cameras', 'lights', 'collections', 'assets'):
                blender_bridge.call('inspect', {'kind': kind, 'scene': scene}, binding=binding)
            modifiers = blender_bridge.call('inspect', {'kind': 'modifiers', 'scene': scene,
                                                        'target': 'instance.fixture'}, binding=binding)
            assert modifiers['items'][0]['type'] == 'BEVEL'
            operator = blender_bridge.call('inspect', {'kind': 'operators', 'scene': scene,
                                                       'operator': 'object.modifier_add'}, binding=binding)
            assert operator['items'][0]['id'] == 'object.modifier_add'
            def refused(command, params, expected):
                try:
                    blender_bridge._request(port, command, params, 2)
                except RuntimeError as exc:
                    assert expected in str(exc), str(exc)
                    assert private['token'] not in str(exc)
                else:
                    raise AssertionError('Unsafe command accepted: ' + command)
            auth = {k: private[k] for k in ('token', 'session_id', 'generation')}
            refused('inspect', {'payload': query}, 'Unauthorized')
            refused('inspect', {'auth': {**auth, 'token': 'wrong'}, 'payload': query}, 'Unauthorized')
            refused('inspect', {'auth': auth, 'payload': {**query, 'fields': ['animation']}}, 'UNSUPPORTED_COVERAGE')
            refused('inspect', {'auth': auth, 'payload': {'kind': 'modifiers', 'scene': scene,
                                                        'target': 'instance.duplicate'}}, 'ambiguous')
            refused('execute_code', {'code': 'raise AssertionError()'}, 'observation')
            with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                connection.sendall(b' ' * 65537)
                try:
                    assert connection.recv(1) == b''
                except ConnectionResetError:
                    pass
            (out / 'reload').write_text('reload')
            wait_for(lambda: blender_bridge.descriptor(binding)['generation'] != private['generation'], process)
            refused('inspect', {'auth': auth, 'payload': query}, 'Unauthorized')
            after = blender_bridge.call('session_describe', {}, binding=binding)
            assert info['session_id'] == after['session_id'] and info['generation'] != after['generation']
            assert info['filepath'] == after['filepath']
            (out / 'stop').write_text('stop')
            process.wait(timeout=20)
            assert process.returncode == 0
            assert not binding.exists()
            audit = json.loads((out / 'audit.json').read_text())
            result = {'case': 'protocol', 'passed': True, 'same_path_reload_invalidated': True,
                      'stable_id_ambiguity_refused': True, 'private_token_not_disclosed': True, **audit}
            (out / 'result.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
        finally:
            if process.poll() is None:
                (out / 'stop').touch(exist_ok=True)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()  # Only this disposable fixture's owned process.


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--blender', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--case', choices=['protocol'], default='protocol')
    protocol(parser.parse_args())
