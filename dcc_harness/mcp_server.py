"""Single stdio MCP boundary over the existing CLI and managed execution service.

Trusted local automation, with ordinary filesystem authority. Input helpers are
scoped; scripts and CLI artifact paths are not a security sandbox. No shell,
artist impersonation, raw live execution or automatic ambiguous retries.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import quote

from . import distribution, execution
from .bootstrap import bind_rules
from .files import reject_links, write_exclusive, file_hash

COMMANDS = frozenset(('brief', 'next', 'requirements', 'resume', 'review', 'start', 'new-project',
    'run-create', 'run-status', 'run-execute', 'run-submit', 'run-cancel', 'run-reconcile',
    'workflow-template', 'workflow-bind', 'stage-reopen',
    'feedback-add', 'feedback-respond', 'feedback-verify', 'feedback-decide', 'check-propose',
    'observe', 'render', 'render-wait', 'relations', 'uv-report', 'deliver-glb',
    'adopt-preview', 'adopt-apply', 'review-page', 'check', 'diff', 'fill-hashes', 'pack-observation',
    'live-sessions', 'live-inspect', 'live-attach', 'live-refresh', 'live-execute', 'live-status',
    'live-cancel', 'live-reconcile', 'live-preview'))
MAX_TEXT = 4 * 1024 * 1024


def write_input(workspace, name, content):
    relative = distribution._safe_name(name)
    if not relative.parts or relative == Path('.'):
        raise ValueError('Name must identify an input file')
    data = content.encode('utf-8')
    if len(data) > MAX_TEXT:
        raise ValueError('Input exceeds 4 MiB')
    target = reject_links(Path(workspace) / 'inputs' / relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_exclusive(target, data)
    return {'path': str(target), 'relative_path': target.relative_to(Path(workspace)).as_posix(), 'sha256': file_hash(target)}


async def run_cli(arguments, workspace, blender=None, *, timeout=3600):
    if not arguments or arguments[0] not in COMMANDS:
        raise ValueError('Command is not exposed by the managed MCP endpoint')
    from .__main__ import build_parser
    args = list(arguments)
    if any(arg in ('--help', '-h') for arg in args):
        raise ValueError('Use harness_command_help instead of CLI help')
    # Parse before launching. Disable parser abbreviation to keep this surface explicit.
    parser = build_parser()
    parser.allow_abbrev = False
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for subparser in action.choices.values():
                subparser.allow_abbrev = False
    try:
        parsed = parser.parse_args(args)
    except SystemExit as exc:
        raise ValueError('Invalid command arguments; consult harness_command_help') from exc
    if getattr(parsed, 'detach', False):
        raise ValueError('Detached jobs are not exposed over MCP; call render directly')
    if hasattr(parsed, 'blender') and parsed.blender and blender and Path(parsed.blender).resolve() != Path(blender).resolve():
        raise ValueError('Use the Blender executable configured for this MCP server')
    workspace = reject_links(workspace).resolve()
    if parsed.command == 'live-execute':
        source = Path(parsed.request)
        if not source.is_absolute(): source = workspace / source
        value = json.loads(reject_links(source).read_text(encoding='utf-8'))
        if blender and Path(value.get('blender', '')).resolve() != Path(blender).resolve():
            raise ValueError('Use the Blender executable configured for this MCP server')
    folder = workspace / '.harness-mcp' / 'requests' / str(uuid.uuid4())
    reject_links(folder).mkdir(parents=True, exist_ok=False)
    write_exclusive(folder / 'request.json', json.dumps({'arguments': args}).encode())
    env = dict(os.environ, DCC_HARNESS_AGENT='1', DCC_HARNESS_CANCEL_FILE=str(folder / 'cancel.request'), PYTHONIOENCODING='utf-8',
               PYTHONPATH=str(Path(__file__).resolve().parent.parent) + os.pathsep + os.environ.get('PYTHONPATH', ''))
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        # Windows venv python.exe is a redirector with a second process. Launch
        # the actual interpreter so cancellation reaps the controller itself.
        # CLI/native code is stdlib-only; PYTHONPATH selects this exact runtime.
        process = await asyncio.create_subprocess_exec(getattr(sys, '_base_executable', sys.executable), '-P', '-m', 'dcc_harness', *args,
            cwd=workspace, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except BaseException:
            # MCP cancellation is a durable run cancellation, never permission to replay.
            # Shield cleanup from AnyIO's level-triggered cancellation scope.
            import anyio
            with anyio.CancelScope(shield=True):
                write_exclusive(folder / 'cancel.request', b'Interrupted MCP request; inspect retained result before any retry.\n')
                if parsed.command in ('run-execute', 'live-execute'):
                    root = Path(parsed.project)
                    if not root.is_absolute():
                        root = workspace / root
                    try:
                        execution.cancel(root)
                    except Exception:
                        pass  # Preserve the original interruption and retained controller logs.
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except (TimeoutError, asyncio.CancelledError):
                    pass
                if process.returncode is None:
                    process.kill()
                await process.wait()
            raise
    output = folder / 'stdout.txt'
    value = output.read_text(encoding='utf-8') if output.stat().st_size <= MAX_TEXT else None
    if value is not None:
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    result = {'exit_code': process.returncode, 'result': value, 'logs': str(folder)}
    if process.returncode:
        error_path = folder / 'stderr.txt'
        with error_path.open('rb') as stream:
            error = stream.read(16384).decode('utf-8', errors='replace')
        raise RuntimeError(f'Harness command failed ({process.returncode}); inspect {folder}\n{error}')
    return result



def create_server(workspace, blender=None, bridge_port=9878):
    from mcp.server.fastmcp import FastMCP, Image
    from . import __version__, blender_bridge
    server = FastMCP('3D Harness', instructions=(
        'Start with harness_info and the bundled dcc-harness skill. Use harness_command brief/next to follow current state. '
        'Construct through managed run-execute or blender_execute. Discover a session and stable target IDs before live edits. '
        'AWAITING_APPROVAL requires the artist in their own terminal. Never impersonate the artist. '
        'Live observations are advisory, not checkpoint evidence.'))
    workspace = reject_links(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    def retained_payload(value):
        return write_input(workspace, 'live/' + str(uuid.uuid4()) + '.json',
                           json.dumps(value, allow_nan=False))['path']

    def required_blender():
        if not blender: raise ValueError('Configure the MCP server with --blender for native verification')
        return blender

    @server.tool()
    async def blender_session(action: str, payload: dict) -> dict:
        """Discover sessions, describe an explicit binding, attach a named scene, or refresh a live project.

        attach: destination,binding,scene,brief_file,mode; optional max_operations,seconds.
        refresh: project,binding,expected_parent. describe: binding. discover: empty payload.
        No approval or automatic session choice. Refresh explicitly imports external edits.
        """
        if action == 'discover' and not payload:
            return await run_cli(['live-sessions', str(workspace)], workspace, blender)
        if action == 'describe' and set(payload) == {'binding'}:
            return await asyncio.to_thread(blender_bridge.call, 'session_describe', {}, binding=payload['binding'])
        if action == 'attach':
            required = {'destination', 'binding', 'scene', 'brief_file', 'mode'}
            if not required <= set(payload) <= required | {'max_operations', 'seconds'}:
                raise ValueError('Invalid attachment fields')
            args = ['live-attach', payload['destination'], '--blender', required_blender()]
            for key, value in payload.items():
                if key != 'destination': args += ['--' + key.replace('_', '-'), str(value)]
            return await run_cli(args, workspace, blender)
        if action == 'refresh' and set(payload) == {'project', 'binding', 'expected_parent'}:
            return await run_cli(['live-refresh', payload['project'], '--binding', payload['binding'],
                                  '--parent', payload['expected_parent']], workspace, blender)
        raise ValueError('Unknown session action or invalid fields; discover, describe, attach, refresh only')

    @server.tool()
    async def blender_inspect(query: dict) -> dict:
        """Inspect explicit binding, scene and kind; paginate with offset/limit. Stable IDs are required for targets."""
        return await run_cli(['live-inspect', '--request', retained_payload(query)], workspace, blender)

    @server.tool()
    async def blender_execute(request: dict) -> dict:
        """Execute {project, operation}; operation is dcc.execution.operation.v2 with backend=live and a closed live recipe.

        Keep the UUID for identical retries, which return status only. Technical publication never grants owner approval.
        """
        if set(request) != {'project', 'operation'}: raise ValueError('Expected project and operation')
        required_blender()
        return await run_cli(['live-execute', request['project'], '--request', retained_payload(request['operation'])], workspace, blender)

    @server.tool()
    async def blender_job(action: str, operation_id: str, payload: dict) -> dict:
        """status/cancel: payload={project}. reconcile also needs decision and current expected_fingerprint.

        Cancellation is cooperative and never promises rollback. Empty operation_id is allowed only for run status.
        Recovery is explicit and archives current state before restore. No approval action exists here.
        """
        keys = {'project', 'decision', 'expected_fingerprint'} if action == 'reconcile' else {'project'}
        if action not in ('status', 'cancel', 'reconcile') or set(payload) != keys:
            raise ValueError('Invalid job action or fields')
        args = ['live-' + action, payload['project']]
        if operation_id: args += ['--operation-id', operation_id]
        elif action != 'status': raise ValueError('Operation UUID required')
        if action == 'reconcile': args += ['--decision', payload['decision'], '--fingerprint', payload['expected_fingerprint']]
        return await run_cli(args, workspace, blender)

    @server.tool()
    async def blender_preview(request: dict) -> dict:
        """Render bounded fixed-setting previews: {project, preview}. Discover session/generation first.

        preview requires session_id,generation,frame,width,height,samples,camera={lens,location,target},compare_checkpoint.
        Returns geometry-render images and provenance; never an artistic verdict or stage approval.
        """
        if set(request) != {'project', 'preview'}: raise ValueError('Expected project and preview')
        return await run_cli(['live-preview', request['project'], '--request', retained_payload(request['preview']),
                              '--blender', required_blender()], workspace, blender)

    @server.tool()
    def harness_info() -> dict:
        """Describe the package, commands, configured workspace and operating boundaries."""
        return {'version': __version__, 'workspace': str(workspace), 'blender': blender,
                'bridge_port': bridge_port, 'commands': sorted(COMMANDS), 'upstream': distribution.upstream(),
                'start_rule': '.agents/skills/dcc-harness/SKILL.md',
                'workflow_guide': 'docs/guides/COMBINED_MCP.md',
                'modes': ['autonomous', 'approval_gated'], 'owner_approval': 'separate interactive owner terminal',
                'files': 'Use harness_write_input for scripts/JSON/text, harness_read for workspace evidence. '
                         'CLI paths and trusted scripts have local filesystem authority; this is not a sandbox.'}

    @server.tool()
    def harness_command_help(command: str) -> str:
        """Read exact CLI arguments for an exposed command without executing it."""
        from .__main__ import build_parser
        if command not in COMMANDS:
            raise ValueError('Command is not exposed')
        for action in build_parser()._actions:
            if isinstance(action, argparse._SubParsersAction):
                return action.choices[command].format_help()
        raise RuntimeError('CLI parser missing commands')

    @server.tool()
    async def harness_command(arguments: list[str]) -> dict:
        """Run one allowlisted harness CLI command (argument array, no shell). Use help for arguments.

        run-create chooses autonomous or approval_gated; run-execute requires a stable UUID,
        saved script, contract, handoff and parent. Retry only the identical request. Supply
        --blender with the configured path for native commands. run-submit pauses for owner
        approval in gated mode. Timeouts or interrupted edits require run-status/reconcile.
        """
        return await run_cli(arguments, workspace, blender)

    @server.tool()
    async def harness_bind(project: str, expected_revision: str, request_id: str) -> dict:
        """Bind the default workflow and all bundled rule dependencies to an initialized project.

        Call after start and before run-create. expected_revision is 'none' for a new project.
        Use a UUID request_id; reuse that UUID only for the identical request.
        """
        return await asyncio.to_thread(bind_rules, project, workspace, expected_revision, request_id)

    @server.tool()
    def harness_write_input(name: str, content: str) -> dict:
        """Create new UTF-8 input; never overwrite. Use relative_path plus sha256 in evidence references,
        and pass the configured workspace as --evidence-root for those payloads.
        """
        return write_input(workspace, name, content)

    @server.tool()
    def harness_read(path: str):
        """Read workspace text or a PNG/JPEG review image (up to 4 MiB)."""
        target = Path(path)
        target = reject_links(target if target.is_absolute() else workspace / target).resolve()
        if not target.is_relative_to(workspace) or not target.is_file():
            raise ValueError('Read a file inside the configured workspace')
        parts = [part.casefold() for part in target.parts]
        if any(parts[i:i+2] == ['.harness-mcp', 'bridge'] for i in range(len(parts)-1)):
            raise ValueError('Private bridge descriptors are not public evidence')
        if target.stat().st_size > MAX_TEXT:
            raise ValueError('File exceeds 4 MiB; use scoped brief/resume or local inspection')
        if target.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            return Image(path=str(target))
        content = target.read_text(encoding='utf-8')
        if 'dcc.blender.session.v1' in content:
            raise ValueError('Private bridge descriptor content is not public evidence')
        return content

    @server.tool()
    def harness_rules(path: str = 'index.json'):
        """Read bundled skills/guides by repository-relative path, or list their hash index."""
        if path.endswith('.png'):
            return Image(data=distribution.read_rule_bytes(path), format='png')
        return json.dumps(distribution.catalog()) if path == 'index.json' else distribution.read_rule(path)

    @server.tool()
    async def blender_observe(command: str = 'get_scene_info', params: dict | None = None) -> dict:
        """Read the optional live observation bridge. Never builds or approves checkpoint evidence."""
        return await asyncio.to_thread(blender_bridge.observe, command, params, port=bridge_port)

    @server.resource('harness://rules/index')
    def rules_index() -> str:
        return json.dumps(distribution.catalog())

    # FastMCP 1.x templates match one URI segment, not a nested relative path.
    # Explicit resources also make every document discoverable to ordinary clients.
    def reader(name):
        def read():
            return distribution.read_rule_bytes(name) if name.endswith('.png') else distribution.read_rule(name)
        return read
    for name in distribution.catalog()['files']:
        server.resource('harness://rules/' + quote(name, safe='/'),
                        mime_type='image/png' if name.endswith('.png') else 'text/plain')(reader(name))

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--blender', help='Executable used by native harness commands')
    parser.add_argument('--bridge-port', type=int, default=9878)
    parser.add_argument('--export-addon', help='Write a new add-on zip and exit; does not install it')
    parser.add_argument('--export-rules', help='Write rules to a new directory and exit')
    args = parser.parse_args()
    if args.export_addon:
        print(json.dumps(distribution.export_addon(args.export_addon)))
    elif args.export_rules:
        print(json.dumps(distribution.export_rules(args.export_rules)))
    else:
        os.environ['DCC_HARNESS_AGENT'] = '1'
        create_server(args.workspace, args.blender, args.bridge_port).run(transport='stdio')


if __name__ == '__main__':
    main()
