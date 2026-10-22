"""Installed stdio MCP + actual owned Blender UI bridge + managed construction proof."""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
import zipfile
from contextlib import suppress


async def qualify(args):
    sys.path.insert(0, str(Path(args.runtime).resolve()))
    from dcc_harness import distribution, blender_bridge, workflow
    from dcc_harness.evidence import file_hash, read_json
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    addon = out / 'bridge.zip'; distribution.export_addon(addon)
    with zipfile.ZipFile(addon) as archive:
        archive.extractall(out / 'addon')  # Only the package's fixed, generated archive.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    fixture = out / 'bridge_fixture.py'
    fixture.write_text('''import bpy, sys, time, json
from pathlib import Path
sys.path.insert(0, ADDON)
outbound_attempts = []
def audit(event, args):
    if event == 'socket.connect':
        outbound_attempts.append(repr(args[1]))
        raise RuntimeError('Observation add-on attempted an outbound connection')
sys.addaudithook(audit)
watched_handlers = ('undo_post', 'redo_post', 'depsgraph_update_post')
def handler_state():
    return {name: tuple(getattr(bpy.app.handlers, name)) for name in watched_handlers}
initial_handlers = handler_state()
import dcc_harness_bridge as bridge
assert handler_state() == initial_handlers
assert not outbound_attempts
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.temporary_directory = str(Path(SCENE).parent)
bpy.ops.mesh.primitive_cube_add(size=1)
bpy.data.objects["Cube"].name = "Cube_模型"
bpy.ops.wm.save_as_mainfile(filepath=SCENE)
initial_handlers = handler_state()
bridge.register()
bridge.server = bridge.ObservationServer(PORT)
bridge.server.start()
assert bridge.server.running
assert handler_state() == initial_handlers
assert not outbound_attempts
Path(READY).write_text("ready")
deadline = time.monotonic() + 240
def finish():
    if Path(STOP).exists() or time.monotonic() > deadline:
        bridge.unregister()
        assert handler_state() == initial_handlers
        assert not outbound_attempts, outbound_attempts
        Path(SCENE).with_suffix('.audit.json').write_text(json.dumps({
            'outbound_connection_attempts': outbound_attempts,
            'activity_handlers_unchanged': True, 'stopped_cleanly': True}))
        bpy.ops.wm.quit_blender()
        return None
    return .2
bpy.app.timers.register(finish)
'''.replace('ADDON', repr(str(out / 'addon'))).replace('SCENE', repr(str(out / 'live.blend')))
        .replace('PORT', str(port)).replace('READY', repr(str(out / 'ready'))).replace('STOP', repr(str(out / 'stop'))), encoding='utf-8')
    startup = None
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    log = (out / 'bridge.log').open('x', encoding='utf-8')
    process = subprocess.Popen([args.blender, '--offline-mode', '--factory-startup', '--disable-autoexec',
                                '--python-exit-code', '1', '--python', str(fixture)],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
    results = []
    try:
        deadline = time.monotonic() + 60
        while not (out / 'ready').exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Owned Blender bridge did not start; inspect bridge.log')
            await asyncio.sleep(.2)
        original_sha = file_hash(out / 'live.blend')
        params = StdioServerParameters(command=sys.executable,
            args=['-m', 'dcc_harness.mcp_server', '--workspace', str(out), '--blender', args.blender, '--bridge-port', str(port)],
            cwd=out, env={**os.environ, 'PYTHONPATH': str(Path(args.runtime).resolve())})
        with (out / 'mcp-stderr.log').open('x', encoding='utf-8') as stderr:
            async with stdio_client(params, errlog=stderr) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=180)) as session:
                    await session.initialize()
                    async def call(name, values=None, error=False):
                        result = await session.call_tool(name, values or {})
                        assert bool(result.isError) == error, result
                        if error:
                            return result.model_dump(mode='json')
                        if result.structuredContent is not None:
                            return result.structuredContent
                        return json.loads(result.content[0].text)
                    async def cli(*arguments, error=False):
                        result = await call('harness_command', {'arguments': list(arguments)}, error=error)
                        return result if error else result['result']
                    tools = [t.name for t in (await session.list_tools()).tools]
                    assert (await call('blender_observe', {'command': 'ping'}))['result'] == {'pong': True}
                    assert (await call('blender_observe', {'command': 'get_addon_info'}))['result']['harness_protocol'] == 3
                    items = (await call('blender_observe', {'command': 'list_scene_items',
                                                        'params': {'query': 'Cube_模型'}}))['result']
                    assert items['total'] == 1 and items['items'][0]['name'] == 'Cube_模型', items
                    live = await call('blender_observe', {'command': 'get_object_info', 'params': {'name': 'Cube_模型'}})
                    assert live['result']['name'] == 'Cube_模型'
                    assert live['result']['mesh']['vertices'] == 8
                    # Probe the actual socket, bypassing the MCP-side allowlist.
                    try:
                        blender_bridge._request(port, 'execute_code', {'code': 'bpy.data.objects.clear()'}, 10)
                        raise AssertionError('Bridge accepted raw execution')
                    except RuntimeError as exc:
                        assert 'observation' in str(exc)
                    assert (await call('blender_observe'))['result']['object_count'] == 1
                    for mode in ('autonomous', 'approval_gated'):
                        brief = await call('harness_write_input', {'name': mode + '-brief.md', 'content': 'Disposable MCP qualification. Build a one-metre cube.'})
                        initialized = await cli('new-project', str(out / mode), '--brief-file', brief['path'], '--blender', args.blender,
                                                '--mode', mode, '--max-operations', '5', '--seconds', '600')
                        root = initialized['project']
                        parent = workflow.resume(root)['active']['id']
                        baseline_sha = file_hash(initialized['baseline'])
                        script = await call('harness_write_input', {'name': mode + '-build.py', 'content':
                            "import bpy\nbpy.ops.mesh.primitive_cube_add(size=1)\nbpy.context.object['dcc_instance_id']='ext.cube'\nbpy.context.object['dcc_asset_id']='ext.cube'\n"})
                        contract = await call('harness_write_input', {'name': mode + '-contract.json', 'content': json.dumps({
                            'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1', 'required': {'ext.cube': {'type': 'MESH', 'dimensions': [1, 1, 1]}}},
                            'allowed_new_prefixes': ['ext.cube'], 'allowed_object_prefixes': {'ext.': ['matrix_world', 'bounds']}})})
                        handoff = await call('harness_write_input', {'name': mode + '-handoff.md', 'content': 'Synthetic fixture, not artist acceptance.'})
                        arguments = ['run-execute', root, '--stage', 'direction', '--operation-id', str(uuid.uuid4()), '--script', script['path'],
                                     '--contract', contract['path'], '--handoff', handoff['path'], '--blender', args.blender, '--parent', parent]
                        published = await cli(*arguments); assert published['status'] == 'PUBLISHED', published
                        assert await cli(*arguments) == published
                        active = workflow.resume(root)['active']
                        from dcc_harness.coordination import checkpoint_ref
                        manifest = distribution.read_rule('docs/guides/MANAGED_EXECUTION.md')
                        assert 'approval_gated' in manifest
                        from dcc_harness.environment_workflow import default_manifest
                        submission = {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': checkpoint_ref(active),
                            'deliverables': {key: 'Synthetic qualification direction' for key in default_manifest()['stages'][0]['deliverables']},
                            'evidence': [{'kind': 'direction_record', 'file': {'path': handoff['relative_path'], 'sha256': handoff['sha256']}}],
                            'feedback_ids': [], 'note': 'Fixture ready'}
                        payload = await call('harness_write_input', {'name': mode + '-submission.json', 'content': json.dumps(submission)})
                        submitted = await cli('run-submit', root, '--submission', payload['path'], '--evidence-root', str(out))
                        expected = 'COMPLETE' if mode == 'autonomous' else 'AWAITING_APPROVAL'
                        assert submitted['status'] == expected, submitted
                        second = arguments.copy()
                        second[second.index('--stage') + 1] = 'blockout'
                        second[second.index('--operation-id') + 1] = str(uuid.uuid4())
                        second[second.index('--parent') + 1] = active['id']
                        if mode == 'approval_gated':
                            await cli(*second, error=True)
                        else:
                            move = await call('harness_write_input', {'name': 'move.py', 'content': "import bpy\nbpy.data.objects['Cube'].location.x = .25\n"})
                            second[second.index('--script') + 1] = move['path']
                            assert (await cli(*second))['status'] == 'PUBLISHED'
                            # Send a real MCP cancellation while the owned native script is sleeping.
                            before_cancel = workflow.resume(root)['active']['id']
                            slow = await call('harness_write_input', {'name': 'slow.py', 'content': 'import time\ntime.sleep(30)\n'})
                            pending = second.copy(); operation_id = str(uuid.uuid4())
                            pending[pending.index('--operation-id') + 1] = operation_id
                            pending[pending.index('--parent') + 1] = before_cancel
                            pending[pending.index('--script') + 1] = slow['path']
                            request_id = session._request_id  # Pin the outgoing request's protocol ID in this test client.
                            task = asyncio.create_task(session.call_tool('harness_command', {'arguments': pending}))
                            operation = Path(root) / 'execution/operations' / operation_id
                            deadline = time.monotonic() + 20
                            while not (operation / 'execute-request.json').exists():
                                if time.monotonic() > deadline or task.done():
                                    raise AssertionError('Cancellation fixture did not dispatch')
                                await asyncio.sleep(.1)
                            from mcp import types
                            await session.send_notification(types.ClientNotification(types.CancelledNotification(
                                params=types.CancelledNotificationParams(requestId=request_id, reason='Qualification cancellation'))))
                            deadline = time.monotonic() + 15
                            while not (operation / 'failure.json').exists():
                                if time.monotonic() > deadline:
                                    raise AssertionError('MCP cancellation did not stop native execution')
                                await asyncio.sleep(.1)
                            task.cancel()
                            with suppress(asyncio.CancelledError, Exception):
                                await task
                            assert workflow.resume(root)['active']['id'] == before_cancel
                            assert (Path(root) / 'execution/cancel.json').exists()
                            assert not (operation / 'candidate.blend').exists()
                        assert file_hash(initialized['baseline']) == baseline_sha
                        obs = read_json(workflow.resume(root)['active']['observation'])
                        assert 'ext.cube' in obs['objects']
                        from dcc_harness.continuity import Continuity
                        results.append({'mode': mode, 'submission': expected, 'checkpoint_count': len(Continuity(root).status()['task_history']),
                                        'baseline_unchanged': True, 'saved_cube_observed': True,
                                        'mcp_cancellation_preserved_checkpoint': mode == 'autonomous'})
                    assert file_hash(out / 'live.blend') == original_sha
                    (out / 'VERIFICATION.json').write_text(json.dumps({'passed': True, 'tools': tools, 'live_bridge': live,
                        'raw_socket_mutation_refused': True, 'live_scene_unchanged': True, 'workflows': results,
                        'limits': 'Owned GUI fixture; no user installation, provider tools, production scene or artist acceptance.'}, indent=2), encoding='utf-8')
    finally:
        (out / 'stop').write_text('stop')
        try:
            await asyncio.to_thread(process.wait, timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        log.close()
    audit = json.loads((out / 'live.audit.json').read_text())
    assert audit == {'outbound_connection_attempts': [], 'activity_handlers_unchanged': True, 'stopped_cleanly': True}
    report_path = out / 'VERIFICATION.json'
    report = json.loads(report_path.read_text()); report['bridge_audit'] = audit
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender', required=True); parser.add_argument('--runtime', required=True); parser.add_argument('--out', required=True)
    asyncio.run(qualify(parser.parse_args()))

