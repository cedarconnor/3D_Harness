"""Owned native C1-C8 fixtures: populated textures, delay, lost reply and crashed reconnect.

This is a focused preservation/transport qualification, not general scene support.
All Blender processes, scenes and configuration directories are created here.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile


def worker(config_path):
    import bpy
    config = json.loads(Path(config_path).read_text())
    out = Path(config['out']); control = Path(config['control'])
    sys.path.insert(0, str(out / 'addon'))
    outbound = []
    def audit(event, args):
        if event == 'socket.connect':
            outbound.append(str(args[1])); raise RuntimeError('Unexpected outbound connection')
    sys.addaudithook(audit)
    import dcc_harness_bridge as bridge
    watched = ('undo_post', 'redo_post', 'depsgraph_update_post')
    handlers = {name: tuple(getattr(bpy.app.handlers, name)) for name in watched}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if config.get('source'):
        bpy.ops.wm.open_mainfile(filepath=config['source'], load_ui=False)
    else:
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'owned-artist.blend'))
        image = bpy.data.images.new('OwnedTexture', width=64, height=64)
        image.pixels[:] = [1, 0, 0, 1] * (64 * 64)
        image.filepath_raw = str(out / 'texture.png'); image.file_format = 'PNG'; image.save()
        bpy.data.images.remove(image)
        image = bpy.data.images.load(str(out / 'texture.png')); image.name = 'OwnedTexture'; image.filepath_raw = '//texture.png'
        cached = list(image.pixels[:]); original_path = image.filepath
        other = bpy.data.images.new('DiskReplacement', width=64, height=64)
        other.pixels[:] = [0, 0, 1, 1] * (64 * 64)
        other.filepath_raw = str(out / 'texture.png'); other.file_format = 'PNG'; other.save()
        bpy.data.images.remove(other)
        assert not image.is_dirty and list(image.pixels[:]) == cached
        from types import SimpleNamespace
        bridge.attachment.save_copy(SimpleNamespace(project=out / 'copy-test/state'), out / 'copy-test/candidate.blend')
        assert list(image.pixels[:]) == cached and image.filepath == original_path and not image.is_dirty
        (out / 'image-preservation.json').write_text(json.dumps({'passed': True, 'live_cached_pixels_unchanged': True,
            'live_path_unchanged': True, 'live_dirty_flag_unchanged': True,
            'saved_copy_stale_cache_preservation': 'not_claimed'}))
        image.reload()
        material = bpy.data.materials.new('TexturedMaterial'); material.use_nodes = True
        tex = material.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = image
        material.node_tree.links.new(tex.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        for index in range(32):
            bpy.ops.mesh.primitive_cube_add(location=(index % 8 * 3, index // 8 * 3, index * .03))
            obj = bpy.data.objects['Cube' if index == 0 else 'Cube.%03d' % index]; obj.data.materials.append(material)
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'owned-artist.blend'))
        image.pixels[0] = .123; image.update(); assert image.is_dirty
    original_copy = bridge.attachment.save_copy
    original_snapshot = bridge.attachment.snapshot
    snapshot_count = 0
    def snapshot(scene):
        nonlocal snapshot_count
        result = original_snapshot(scene)
        if (control / 'debug-snapshots').exists():
            snapshot_count += 1
            (control / ('measured-%03d.json' % snapshot_count)).write_text(json.dumps(result, sort_keys=True))
        return result
    bridge.attachment.snapshot = snapshot
    def slow_copy(session, path):
        time.sleep(2.5)
        return original_copy(session, path)
    bridge.attachment.save_copy = slow_copy
    original_step = bridge.jobs.operations.execute_step
    def step(scene, value):
        original_step(scene, value)
        if (control / 'fail-next').exists():
            (control / 'fail-next').unlink()
            raise RuntimeError('Owned failure after native mutation')
    bridge.jobs.operations.execute_step = step
    original_capture = bridge.recovery.capture
    def capture(jobs, payload):
        path = out / 'capture-count.json'
        count = json.loads(path.read_text()) if path.exists() else 0
        path.write_text(json.dumps(count + 1))
        return original_capture(jobs, payload)
    bridge.recovery.capture = capture
    bridge.register(); bridge.server = bridge.ObservationServer(config['port'], out); bridge.server.start()
    (control / 'ready.json').write_text(json.dumps({'descriptor': str(bridge.server.session.descriptor_path)}))
    deadline = time.monotonic() + 480
    def tick():
        if (control / 'clean-image').exists():
            (control / 'clean-image').unlink(); bpy.data.images['OwnedTexture'].reload()
            (control / 'cleaned').write_text('done')
        if time.monotonic() >= deadline or (control / 'stop').exists():
            bridge.unregister()
            assert {name: tuple(getattr(bpy.app.handlers, name)) for name in watched} == handlers
            assert not outbound
            (control / 'audit.json').write_text(json.dumps({'outbound_attempts': outbound, 'activity_handlers_unchanged': True}))
            bpy.ops.wm.quit_blender()
            return None
        return .05
    bpy.app.timers.register(tick, persistent=True)


def wait(predicate, process, seconds=90):
    deadline = time.monotonic() + seconds
    while not predicate():
        if process.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError('Owned native fixture failed or timed out; inspect native logs')
        time.sleep(.1)


def qualify(args):
    sys.path.insert(0, str(Path(args.runtime).resolve()))
    from dcc_harness import blender_bridge, distribution, execution, live, workflow
    from dcc_harness.evidence import read_json, write_json
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    distribution.export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive: archive.extractall(out / 'addon')
    processes = []
    logs = []
    def start(name, source=None):
        control = out / name; control.mkdir()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        config = control / 'config.json'
        write_json(config, {'out': str(out), 'control': str(control), 'port': port, 'source': source})
        env = dict(os.environ)
        for key in ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS'):
            directory = control / ('user-' + key.lower()); directory.mkdir()
            env['BLENDER_USER_' + key] = str(directory)
        log = (control / 'native.log').open('w'); logs.append(log)
        startup = None
        if os.name == 'nt':
            startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
        process = subprocess.Popen([args.blender, '--factory-startup', '--offline-mode', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--worker', str(config)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, startupinfo=startup)
        processes.append((process, control))
        wait(lambda: (control / 'ready.json').exists(), process)
        binding = Path(read_json(control / 'ready.json')['descriptor'])
        blender_bridge.observe('ping', port=port, timeout=10)
        return process, control, binding
    try:
        process, control, descriptor = start('first')
        private = blender_bridge.descriptor(descriptor)
        brief = out / 'brief.md'; brief.write_text('Owned populated textured transport qualification')
        options = dict(scene='Scene', brief_file=brief, mode='autonomous', blender=args.blender)
        destination = out / 'attached'
        try: live.attach(destination, descriptor, **options)
        except RuntimeError as exc: assert 'UNSAVED_IMAGE' in str(exc), str(exc)
        else: raise AssertionError('Dirty-image attachment accepted')
        info = blender_bridge.call('session_describe', {}, binding=descriptor)
        assert info['active_operation'] is None and info['project'] is None
        (control / 'clean-image').write_text('clean')
        wait(lambda: (control / 'cleaned').exists(), process)
        began = time.monotonic()
        attached = live.attach(destination, descriptor, **options)
        elapsed = time.monotonic() - began; assert elapsed > 5
        root = Path(attached['project']); active = workflow.resume(root)['active']
        observation = read_json(active['observation']); assert len(observation['objects']) == 32
        target = next(iter(observation['objects']))
        inputs = out / 'inputs'; inputs.mkdir()
        script = inputs / 'operation.py'; script.write_text('# Bounded native transport fixture\n')
        handoff = inputs / 'handoff.md'; handoff.write_text('Owned transport proof; not artist acceptance.\n')
        contract = inputs / 'contract.json'
        write_json(contract, {'schema':'dcc.continuity.contract.v1',
            'spec':{'schema':'dcc.spec.v1','required':{target:{}}},
            'allowed_object_prefixes':{target:['matrix_world','bounds','geometry_hash','evaluated_uv_values','uv_hash']}})
        import uuid
        def request(target_id):
            return {'schema':'dcc.execution.operation.v2','backend':'live','operation_id':str(uuid.uuid4()),
                'stage':'direction','script':str(script),'contract':str(contract),'handoff':str(handoff),
                'blender':args.blender,'expected_parent':workflow.resume(root)['active']['id'],'timeout':90,
                'live':{'recipe':'object.transform','target':target_id,'parameters':{'location':[1,2,3]}}}
        refusal = live.execute(root, request('missing.owned.target'))
        assert refusal['status'] == 'REJECTED' and not refusal['mutation_started'], refusal
        assert live.read_binding(root)['state'] == 'READY'
        (control / 'fail-next').write_text('fail')
        operation = request(target); failed = live.execute(root, operation)
        assert failed['status'] == 'NEEDS_RECONCILIATION', failed
        (control / 'debug-snapshots').write_text('retain')
        current = blender_bridge.call('attach_check', {}, binding=descriptor)
        write_json(out / 'recovery-fingerprint.json', current)
        original_request = blender_bridge._request
        def short_reply(port, command, payload, timeout):
            return original_request(port, command, payload, .2 if command == 'recovery_capture' else timeout)
        blender_bridge._request = short_reply
        try:
            try: live.reconcile(root, operation['operation_id'], 'keep-current', current['fingerprint'])
            except blender_bridge.BridgeTransportError: pass
            else: raise AssertionError('Deliberately lost capture response was not lost')
        finally: blender_bridge._request = original_request
        intent = {'operation_id':operation['operation_id'],'decision':'keep-current','expected_fingerprint':current['fingerprint']}
        wait(lambda: blender_bridge.retained_outcome('recovery_capture', intent, private) is not None, process)
        recovered = live.reconcile(root, operation['operation_id'], 'keep-current', current['fingerprint'])
        assert recovered['live_state'] == 'READY', recovered
        assert read_json(out / 'capture-count.json') == 1
        # Kill the owned bridge exactly after checkpoint publication and before
        # live acknowledgement. Replacement alignment must never enter old job
        # acknowledgement or capture, and must not publish another checkpoint.
        publication = request(target)
        publication['live']['parameters']['location'] = [4, 5, 6]
        def crash_before_ack(port, command, payload, timeout):
            if command == 'job_acknowledge':
                process.kill(); process.wait(timeout=20)
                raise ConnectionError('Owned crash after publication and before acknowledgement')
            return original_request(port, command, payload, timeout)
        blender_bridge._request = crash_before_ack
        try:
            published = live.execute(root, publication)
        finally:
            blender_bridge._request = original_request
        assert published['status'] == 'PUBLISHED' and published['live_state'] == 'LIVE_DIVERGED', published
        accepted = workflow.resume(root)['active']
        assert descriptor.exists() and blender_bridge.session_presence(descriptor) == 'DEAD'
        second, second_control, replacement = start('second', accepted['checkpoint'])
        refreshed = live.refresh(root, replacement, expected_parent=accepted['id'])
        assert refreshed['state'] == 'READY' and refreshed['reconnected'], refreshed
        history_count = len(workflow.Continuity(root).status()['task_history'])
        aligned = live.reconcile(root, publication['operation_id'], 'keep-current', live.read_binding(root)['fingerprint'])
        assert aligned['status'] == 'PUBLISHED' and aligned['live_state'] == 'READY', aligned
        assert len(workflow.Continuity(root).status()['task_history']) == history_count
        assert Path(aligned['live_alignment']['path']).is_file() and read_json(out / 'capture-count.json') == 1
        (second_control / 'stop').write_text('stop'); second.wait(timeout=30)
        assert second.returncode == 0 and read_json(second_control / 'audit.json')['activity_handlers_unchanged']
        result = {'passed':True,'populated_objects':32,'external_texture':True,
            'delayed_attachment_seconds':elapsed,'deliberate_copy_delay_seconds':2.5,
            'dirty_attach_refusal_retried_safely':True,'prepare_refusal_closed_without_dispatch':True,
            'lost_capture_reply_resolved_without_recapture':True,'capture_count':1,
            'crashed_descriptor_reconnected':True,'image_preservation':read_json(out/'image-preservation.json'),
            'crash_between_publication_and_ack_realigned':True, 'alignment_did_not_publish_checkpoint':True,
            'limits':'Owned GUI Blender main-thread bridge fixtures; no arbitrary-scene or saved stale-cache claim.'}
        write_json(out / 'VERIFICATION.json', result); print(json.dumps(result, indent=2))
    finally:
        for process, control in processes:
            if process.poll() is None:
                (control / 'stop').write_text('stop')
                try: process.wait(timeout=20)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=20)
        for log in logs: log.close()


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker(sys.argv[sys.argv.index('--worker') + 1])
    else:
        parser=argparse.ArgumentParser()
        parser.add_argument('--runtime',required=True); parser.add_argument('--blender',required=True); parser.add_argument('--out',required=True)
        qualify(parser.parse_args())
