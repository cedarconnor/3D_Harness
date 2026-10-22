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
    config = {'out': str(out), 'port': port, 'case': args.case, 'fixture': args.fixture}
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
bpy.context.preferences.filepaths.temporary_directory = str(out)
if CONFIG['fixture'] != 'empty':
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.data.objects['Cube']
    if CONFIG['case'] == 'protocol':
        obj['dcc_instance_id'] = 'instance.fixture'
        obj.modifiers.new('Bevel', 'BEVEL')
        mat = bpy.data.materials.new('Material'); mat.use_nodes = True
        obj.data.materials.append(mat)
        other = obj.copy(); other.data = obj.data.copy(); other['dcc_instance_id'] = 'instance.other'
        bpy.context.scene.collection.objects.link(other)
        for i in range(2):
            duplicate = obj.copy(); duplicate['dcc_instance_id'] = 'instance.duplicate'
            bpy.context.scene.collection.objects.link(duplicate)
    elif CONFIG['fixture'] == 'relative':
        image = bpy.data.images.new('Texture', width=2, height=2)
        image.filepath_raw = str(out / 'texture.png'); image.file_format = 'PNG'; image.save()
        bpy.data.images.remove(image)
        image = bpy.data.images.load(str(out / 'texture.png')); image.filepath = '//texture.png'
        mat = bpy.data.materials.new('Material'); mat.use_nodes = True
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = image
        obj.data.materials.append(mat)
    elif CONFIG['fixture'] == 'duplicate':
        obj['dcc_instance_id'] = 'instance.duplicate'
        other = obj.copy(); bpy.context.scene.collection.objects.link(other)
    elif CONFIG['fixture'] == 'linked':
        bpy.data.libraries.write(str(out / 'library.blend'), {obj})
        bpy.data.objects.remove(obj, do_unlink=True)
        with bpy.data.libraries.load(str(out / 'library.blend'), link=True) as (source, target):
            target.objects = ['Cube']
        bpy.context.scene.collection.objects.link(target.objects[0])
if CONFIG['case'] == 'protocol' or CONFIG['fixture'] in ('dirty', 'relative', 'duplicate', 'linked'):
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'fixture.blend'))
if CONFIG['case'] == 'attach' and CONFIG['fixture'] in ('untitled', 'dirty', 'relative'):
    obj.location.x = 2.5
    obj.data.vertices[0].co.z += 1.25
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
    if (out / 'mutate').exists():
        (out / 'mutate').unlink()
        bpy.data.objects['Cube'].location.x += 1
        bpy.context.view_layer.update()
        (out / 'mutated').write_text('done')
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
            # File readiness precedes the first GUI timer tick on a busy startup.
            # This read-only startup probe has no mutation to replay.
            blender_bridge.observe('ping', port=port, timeout=10)
            info = blender_bridge.call('session_describe', {}, binding=binding)
            scene = info['scenes'][0]
            assert private['token'] not in json.dumps(info)
            if args.case == 'attach':
                attach_case(args, out, binding, info, process)
                (out / 'stop').write_text('stop')
                process.wait(timeout=20)
                assert process.returncode == 0
                assert not binding.exists()
                print((out / 'result.json').read_text())
                return
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


def attach_case(args, out, binding, before, process):
    from dcc_harness import live, workflow, execution, blender_bridge
    from dcc_harness.evidence import file_hash, read_json
    brief = out / 'brief.md'; brief.write_text('Qualify live scene adoption')
    original = before['filepath']
    sha = file_hash(original) if original else None
    options = {'scene': before['scenes'][0], 'brief_file': brief, 'mode': 'autonomous', 'blender': args.blender}
    if args.fixture in ('interrupted', 'stale'):
        import uuid
        folder = out / 'attached'; folder.mkdir()
        (folder / 'attach-request.json').write_text('{}')
        payload = {'project': str(folder / 'state'), 'operation_id': str(uuid.uuid4()), 'request_hash': 'fixture'}
        blender_bridge.call('attach_begin', {**payload, 'scene': before['scenes'][0]}, binding=binding)
        if args.fixture == 'stale':
            (out / 'mutate').write_text('mutate')
            wait_for(lambda: (out / 'mutated').exists(), process)
            try:
                blender_bridge.call('attach_apply', payload, binding=binding)
            except RuntimeError as exc:
                assert 'STALE' in str(exc)
            else:
                raise AssertionError('Stale preparation mutated the scene')
        try:
            live.attach(folder, binding, **options)
        except RuntimeError as exc:
            assert 'Incomplete' in str(exc)
        else:
            raise AssertionError('Incomplete attachment replayed')
        objects = blender_bridge.call('inspect', {'kind': 'objects', 'scene': before['scenes'][0]}, binding=binding)
        assert all(o['id'] is None for o in objects['items'])
        assert not (folder / 'attach-dispatched.json').exists()
        result = {'case': 'attach', 'fixture': args.fixture, 'passed': True, 'no_identity_assignment': True,
                  'precopy_preserved': (folder / 'pre-adoption.blend').exists()}
    elif args.fixture in ('duplicate', 'linked'):
        try:
            live.attach(out / 'attached', binding, **options)
        except RuntimeError as exc:
            assert 'blocked' in str(exc), str(exc)
        else:
            raise AssertionError('Unsupported identities were adopted')
        assert not (out / 'attached/attach-dispatched.json').exists()
        result = {'case': 'attach', 'fixture': args.fixture, 'passed': True, 'blocked_before_identity_writes': True}
    else:
        attached = live.attach(out / 'attached', binding, **options)
        assert attached == live.attach(out / 'attached', binding, **options)
        assert execution.configuration(attached['project'])['backend'] == 'live'
        observation = read_json(workflow.resume(attached['project'])['active']['observation'])
        assert len(observation['objects']) == 1
        saved = read_json(out / 'attached/attach-saved.json')
        after = blender_bridge.call('session_describe', {}, binding=binding)
        assert after['filepath'] == original
        if sha:
            assert file_hash(original) == sha
        if args.fixture in ('untitled', 'dirty', 'relative'):
            objects = blender_bridge.call('inspect', {'kind': 'objects', 'scene': before['scenes'][0]}, binding=binding)
            assert objects['items'][0]['transform'][0][3] == 2.5
        verified = read_json(out / 'attached/observation/verified.json')
        assert verified['saved_inventory_matches'] and verified['saved_fingerprint_matches']
        if args.fixture == 'relative':
            images = [node['image'] for material in observation['materials'].values()
                      for node in material['graph']['nodes'] if 'image' in node]
            assert len(images) == 1 and images[0]['sha256'] == file_hash(out / 'texture.png') and images[0]['exists']
        if args.fixture == 'dirty':
            (out / 'mutate').write_text('mutate')
            wait_for(lambda: (out / 'mutated').exists(), process)
            try:
                live.refresh(attached['project'], binding, expected_parent=workflow.resume(attached['project'])['active']['id'])
            except ValueError as exc:
                assert 'LIVE_DIVERGED' in str(exc)
            else:
                raise AssertionError('External artist edit silently accepted')
        result = {'case': 'attach', 'fixture': args.fixture, 'passed': True,
                  'original_filepath_unchanged': True, 'original_disk_unchanged': True,
                  'saved_copy_independently_verified': True, 'replay_did_not_reassign': True,
                  'observation_issues': observation['issues']}
    (out / 'result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--blender', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--case', choices=['protocol', 'attach'], default='protocol')
    parser.add_argument('--fixture', choices=['untitled', 'dirty', 'relative', 'empty', 'duplicate', 'linked',
                                              'interrupted', 'stale'], default='untitled')
    protocol(parser.parse_args())
