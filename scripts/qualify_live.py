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
    elif CONFIG['case'] == 'jobs':
        mat = bpy.data.materials.new('Material'); mat.use_nodes = True
        obj.data.materials.append(mat)
        if CONFIG['fixture'] == 'shared':
            other = obj.copy(); other.data = obj.data.copy()
            bpy.context.scene.collection.objects.link(other)
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
if CONFIG['case'] == 'jobs' and CONFIG['fixture'] == 'nodes':
    tree = bpy.data.node_groups.new('FixtureTransform', 'GeometryNodeTree')
    tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    offset = tree.interface.new_socket(name='Offset', in_out='INPUT', socket_type='NodeSocketVector')
    entry = tree.nodes.new('NodeGroupInput'); exit_node = tree.nodes.new('NodeGroupOutput')
    transform = tree.nodes.new('GeometryNodeTransform')
    tree.links.new(entry.outputs['Geometry'], transform.inputs['Geometry'])
    tree.links.new(entry.outputs['Offset'], transform.inputs['Translation'])
    tree.links.new(transform.outputs['Geometry'], exit_node.inputs['Geometry'])
    bpy.data.libraries.write(str(out / 'node-asset.blend'), {tree})
    (out / 'node-asset.json').write_text(json.dumps({'input': offset.identifier}))
    bpy.data.node_groups.remove(tree)
bridge.register()
bridge.server = bridge.ObservationServer(CONFIG['port'], out)
bridge.server.start()
if CONFIG['case'] == 'jobs' and CONFIG['fixture'] in ('fail', 'stale-recovery'):
    original_step = bridge.jobs.operations.execute_step
    def fail_after_mutation(scene, value):
        original_step(scene, value)
        raise RuntimeError('Synthetic failure after native mutation')
    bridge.jobs.operations.execute_step = fail_after_mutation
if CONFIG['case'] == 'jobs' and CONFIG['fixture'] == 'cancel':
    original_step = bridge.jobs.operations.execute_step
    def slow_step(scene, value):
        original_step(scene, value)
        time.sleep(5)
    bridge.jobs.operations.execute_step = slow_step
if CONFIG['case'] == 'jobs' and CONFIG['fixture'] in ('queued-cancel', 'queued-reload', 'context'):
    original_run = bridge.jobs.Jobs.run
    def interrupted_run(self, operation_id):
        if CONFIG['fixture'] == 'queued-cancel':
            self.cancel(operation_id)
        elif CONFIG['fixture'] == 'queued-reload':
            bpy.ops.wm.open_mainfile(filepath=str(self.folder(operation_id) / 'pre-operation.blend'))
        else:
            bpy.ops.object.mode_set(mode='EDIT')
        return original_run(self, operation_id)
    bridge.jobs.Jobs.run = interrupted_run
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
    if (out / 'restart').exists():
        (out / 'restart').unlink()
        bridge.server.stop()
        bridge.server = bridge.ObservationServer(CONFIG['port'], out)
        bridge.server.start()
        (out / 'restarted.json').write_text(json.dumps({'descriptor': str(bridge.server.session.descriptor_path)}))
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
            if args.case in ('attach', 'jobs'):
                if args.case == 'attach':
                    attach_case(args, out, binding, info, process)
                else:
                    jobs_case(args, out, binding, info, process)
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


def jobs_case(args, out, binding, before, process):
    import uuid
    from dcc_harness import live, workflow, execution, blender_bridge
    from dcc_harness.evidence import read_json, write_json
    from dcc_harness.continuity_checks import OBJECT_FIELDS
    brief = out / 'brief.md'; brief.write_text('Qualify live object edits')
    attached = live.attach(out / 'attached', binding, scene=before['scenes'][0], brief_file=brief,
                           mode='autonomous', blender=args.blender)
    root = Path(attached['project'])
    observation = read_json(workflow.resume(root)['active']['observation'])
    target = next(iter(observation['objects'])); material = next(iter(observation['materials']))
    handoff = out / 'handoff.md'; handoff.write_text('Independent live recipe proof')
    script = out / 'recipe.py'; script.write_text('# Declarative built-in recipe; this script is not executed.\n')
    values = [
        {'recipe': 'object.transform', 'target': target, 'parameters': {'location': [2, 1, 0]}},
        {'recipe': 'material.input', 'target': target, 'parameters': {'material_id': material,
            'node': 'Principled BSDF', 'socket': 'Roughness', 'value': .25,
            'shared_users': sorted(observation['objects']) if args.fixture == 'shared' else [target]}},
        {'recipe': 'modifier.settings', 'target': target, 'parameters': {'name': 'Managed bevel', 'type': 'BEVEL',
                                                                       'settings': {'width': .1, 'segments': 2}}},
        {'recipe': 'modifier.settings', 'target': target, 'parameters': {'name': 'Managed bevel', 'type': 'BEVEL',
                                                                       'settings': {'width': .15, 'segments': 3}}},
    ]
    if args.fixture == 'nodes':
        from dcc_harness.evidence import file_hash
        socket_id = read_json(out / 'node-asset.json')['input']
        values = [{'recipe': 'node.asset', 'target': target, 'parameters': {
            'path': str(out / 'node-asset.blend'), 'sha256': file_hash(out / 'node-asset.blend'),
            'group': 'FixtureTransform', 'modifier': 'Managed node asset', 'inputs': {socket_id: [x, 0, 0]}}} for x in (1, 2)]
    results = []
    for index, recipe in enumerate(values):
        contract = out / ('contract-%d.json' % index)
        write_json(contract, {'schema': 'dcc.continuity.contract.v1',
            'spec': {'schema': 'dcc.spec.v1', 'required': {target: {}}},
            'allowed_object_prefixes': {target: sorted(OBJECT_FIELDS)},
            'allowed_material_inputs': {material: {'Principled BSDF': {'Roughness': .25}}}
                                       if recipe['recipe'] == 'material.input' else {}})
        request = {'schema': 'dcc.execution.operation.v2', 'backend': 'live', 'operation_id': str(uuid.uuid4()),
                   'stage': 'direction', 'script': str(script), 'contract': str(contract), 'handoff': str(handoff),
                   'blender': args.blender, 'expected_parent': workflow.resume(root)['active']['id'],
                   'timeout': 90, 'live': recipe}
        if args.fixture == 'cancel':
            request['timeout'] = 2
        if args.fixture in ('pre-publication', 'post-publication'):
            from unittest import mock
            method = 'before_publish' if args.fixture == 'pre-publication' else 'published'
            original_method = getattr(live.LiveBackend, method)
            def edit_at_barrier(self, *arguments):
                (out / 'mutate').write_text('mutate')
                wait_for(lambda: (out / 'mutated').exists(), process)
                return original_method(self, *arguments)
            with mock.patch.object(live.LiveBackend, method, edit_at_barrier):
                result = execution.execute_operation(root, request)
        elif args.fixture == 'lost-reply':
            from unittest import mock
            actual_request = blender_bridge._request
            def lost_response(port, command, params, timeout):
                result = actual_request(port, command, params, timeout)
                if command == 'job_submit':
                    raise ConnectionError('Synthetic lost mutation acknowledgement')
                return result
            with mock.patch.object(blender_bridge, '_request', side_effect=lost_response):
                result = execution.execute_operation(root, request)
        else:
            result = execution.execute_operation(root, request)
        if args.fixture in ('pre-publication', 'post-publication', 'queued-cancel', 'queued-reload', 'context'):
            operation = root / 'execution/operations' / request['operation_id']
            published = args.fixture == 'post-publication'
            assert result['status'] == ('PUBLISHED' if published else 'NEEDS_RECONCILIATION'), result
            active = workflow.resume(root)['active']['id']
            assert (active != request['expected_parent']) == published
            if published:
                assert result['live_state'] == 'LIVE_DIVERGED', result
            try:
                live.ensure_aligned(root)
            except (ValueError, RuntimeError):
                pass
            else:
                raise AssertionError('Unresolved live state admitted another operation')
            native = read_json(operation / 'live-status.json')
            raced = args.fixture in ('pre-publication', 'post-publication')
            if not raced:
                assert not (operation / 'candidate.blend').exists()
            objects = blender_bridge.call('inspect', {'kind': 'objects', 'scene': before['scenes'][0]}, binding=binding)
            assert objects['items'][0]['transform'][0][3] == (3 if raced else 0)
            assert process.poll() is None
            (out / 'result.json').write_text(json.dumps({'case': 'jobs', 'fixture': args.fixture, 'passed': True,
                'publication_matches_outcome': True, 'artist_edit_preserved': raced,
                'native_state': native['state'], 'next_operation_refused': True}, indent=2))
            return
        if args.fixture in ('cancel', 'lost-reply'):
            assert result['status'] == 'NEEDS_RECONCILIATION', result
            assert execution.execute_operation(root, request)['status'] == 'NEEDS_RECONCILIATION'
            operation = root / 'execution/operations' / request['operation_id']
            wait_for(lambda: read_json(operation / 'live-status.json')['state'] in ('SAVED', 'NEEDS_RECONCILIATION'), process, seconds=15)
            status = read_json(operation / 'live-status.json')
            assert process.poll() is None and status.get('mutation_started') is True
            assert sum(read_json(p)['state'] == 'RUNNING' for p in (operation / 'live-history').glob('*.json')) == 1
            current = blender_bridge.call('attach_check', {}, binding=binding)
            recovered = live.reconcile(root, request['operation_id'], 'restore-precopy', current['fingerprint'])
            assert recovered['live_state'] == 'READY'
            (out / 'result.json').write_text(json.dumps({'case': 'jobs', 'fixture': args.fixture, 'passed': True,
                'dispatch_count': 1, 'native_process_survived': True, 'eventual_outcome_recorded': True,
                'explicit_recovery_verified': True}, indent=2))
            return
        if args.fixture in ('fail', 'stale-recovery'):
            assert result['status'] == 'NEEDS_RECONCILIATION', result
            current = blender_bridge.call('attach_check', {}, binding=binding)
            if args.fixture == 'stale-recovery':
                (out / 'mutate').write_text('mutate')
                wait_for(lambda: (out / 'mutated').exists(), process)
                try:
                    live.reconcile(root, request['operation_id'], args.recovery, current['fingerprint'])
                except ValueError as exc:
                    assert 'STALE_SCENE' in str(exc)
                else:
                    raise AssertionError('Recovery erased a later edit')
                assert not (root / 'execution/operations' / request['operation_id'] / 'recovery').exists()
                current = blender_bridge.call('attach_check', {}, binding=binding)
            recovery = live.reconcile(root, request['operation_id'], args.recovery, current['fingerprint'])
            assert recovery['live_state'] == 'READY', recovery
            objects = blender_bridge.call('inspect', {'kind': 'objects', 'scene': before['scenes'][0]}, binding=binding)
            expected_x = 0 if args.recovery == 'restore-precopy' else 3 if args.fixture == 'stale-recovery' else 2
            assert objects['items'][0]['transform'][0][3] == expected_x
            assert Path(recovery['archive']['path']).exists()
            live.ensure_aligned(root)
            (out / 'result.json').write_text(json.dumps({'case': 'jobs', 'fixture': args.fixture, 'passed': True,
                'mutation_error_retained': True, 'recovery_decision': args.recovery, 'recovery_verified': True,
                'current_state_archived_before_restore': True}, indent=2))
            return
        assert result['status'] == 'PUBLISHED' and result.get('live_state') == 'READY', result
        assert execution.execute_operation(root, request) == result
        live.ensure_aligned(root)
        results.append({'recipe': recipe['recipe'], 'operation_id': request['operation_id'], 'published': True})
        if args.fixture in ('external', 'reconnect'):
            old_parent = workflow.resume(root)['active']['id']
            if args.fixture == 'external':
                (out / 'mutate').write_text('mutate')
                wait_for(lambda: (out / 'mutated').exists(), process)
            else:
                (out / 'restart').write_text('restart')
                wait_for(lambda: (out / 'restarted.json').exists(), process)
                binding = Path(json.loads((out / 'restarted.json').read_text())['descriptor'])
            refreshed = live.refresh(root, binding, expected_parent=old_parent)
            assert refreshed['state'] == 'READY', refreshed
            live.ensure_aligned(root)
            new_parent = workflow.resume(root)['active']['id']
            assert (new_parent != old_parent) == (args.fixture == 'external')
            (out / 'result.json').write_text(json.dumps({'case': 'jobs', 'fixture': args.fixture, 'passed': True,
                'explicit_refresh_verified': True, 'new_checkpoint': new_parent != old_parent}, indent=2))
            return
    modifiers = blender_bridge.call('inspect', {'kind': 'modifiers', 'scene': before['scenes'][0], 'target': target}, binding=binding)
    assert len(modifiers['items']) == 1
    if args.fixture == 'nodes':
        assert modifiers['items'][0]['type'] == 'NODES'
    else:
        assert abs(modifiers['items'][0]['properties']['values']['width'] - .15) < 1e-6
    result = {'case': 'jobs', 'passed': True, 'operations': results, 'same_modifier_updated': True,
              'saved_output_independently_verified': True, 'live_scene_retained_edits': True}
    (out / 'result.json').write_text(json.dumps(result, indent=2))


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
        from dcc_harness.native import run_worker
        reopened = out / 'accepted-reopen'; reopened.mkdir()
        accepted = workflow.resume(attached['project'])['active']
        run_worker(args.blender, reopened, Path(live.__file__).with_name('_live_verify_blender.py'), 'verify',
                   {'source': {'path': accepted['checkpoint'], 'sha256': accepted['checkpoint_sha256']},
                    'out': str(reopened), 'scene': saved['scene'], 'inventory': saved['inventory'],
                    'snapshot': saved['snapshot'], 'fingerprint': saved['fingerprint']}, timeout=60)
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
            old_parent = workflow.resume(attached['project'])['active']['id']
            refreshed = live.refresh(attached['project'], binding, expected_parent=old_parent)
            assert refreshed['state'] == 'READY' and refreshed['provenance'] == 'external_live_edit'
            assert workflow.resume(attached['project'])['active']['id'] != old_parent
            assert file_hash(original) == sha
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
    parser.add_argument('--case', choices=['protocol', 'attach', 'jobs'], default='protocol')
    parser.add_argument('--fixture', choices=['untitled', 'dirty', 'relative', 'empty', 'duplicate', 'linked',
                                              'interrupted', 'stale', 'fail', 'stale-recovery', 'cancel', 'lost-reply',
                                              'external', 'reconnect', 'nodes', 'shared', 'pre-publication', 'post-publication',
                                              'queued-cancel', 'queued-reload', 'context'], default='untitled')
    parser.add_argument('--recovery', choices=['keep-current', 'restore-precopy'], default='restore-precopy')
    protocol(parser.parse_args())
