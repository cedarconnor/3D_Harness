"""Real stdio live workflows on the disposable bridge owned by qualify_live."""
import json
import os
from pathlib import Path
import re
import sys
import uuid
from datetime import timedelta


class SyntheticOwnerConsole:
    """Authority-path fixture only; never used for a human project."""
    environ = {}
    def isatty(self): return True
    def ask(self, text): return re.search(r'Type ([A-Z0-9]{4})', text).group(1)


async def qualify(args, out, binding, before, process):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from dcc_harness import workflow, coordination as c, environment_workflow as ew, review_page, blender_bridge
    from dcc_harness.evidence import read_json, write_json, file_hash
    from dcc_harness.continuity_checks import OBJECT_FIELDS
    from qualify_live import wait_for
    original_sha = file_hash(before['filepath'])
    params = StdioServerParameters(command=sys.executable,
        args=['-m', 'dcc_harness.mcp_server', '--workspace', str(out), '--blender', args.blender],
        cwd=out, env={**os.environ, 'PYTHONPATH': str(Path(args.runtime).resolve())})
    with (out / 'mcp.log').open('x', encoding='utf-8') as log:
        async with stdio_client(params, errlog=log) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=180)) as session:
                await session.initialize()
                async def call(name, values, error=False):
                    result = await session.call_tool(name, values)
                    assert bool(result.isError) == error, result
                    if error: return result
                    value = result.structuredContent or json.loads(result.content[0].text)
                    return value['result'] if 'exit_code' in value else value
                async def cli(*args, error=False):
                    return await call('harness_command', {'arguments': list(args)}, error)
                async def input_file(name, text):
                    return await call('harness_write_input', {'name': name, 'content': text})
                found = await call('blender_session', {'action': 'discover', 'payload': {}})
                assert len(found['sessions']) == 1
                brief = await input_file('brief.md', 'Disposable live MCP qualification')
                attached = await call('blender_session', {'action': 'attach', 'payload': {
                    'destination': str(out / 'attached'), 'binding': str(binding), 'scene': before['scenes'][0],
                    'brief_file': brief['path'], 'mode': args.mode, 'seconds': 600}})
                root = Path(attached['project'])
                inspected = await call('blender_inspect', {'query': {'binding': str(binding),
                    'scene': before['scenes'][0], 'kind': 'objects'}})
                target = inspected['result']['items'][0]['id']
                preview_request = {'session_id': before['session_id'], 'generation': before['generation'],
                    'frame': 1, 'width': 128, 'height': 128, 'samples': 1,
                    'camera': {'lens': 50, 'location': [7, -7, 5], 'target': [1, 0, 0]}, 'compare_checkpoint': True}
                first_preview = await call('blender_preview', {'request': {'project': str(root), 'preview': preview_request}})
                assert read_json(first_preview['current']['settings'])['resolved']['preview']['antialiasing'] == '5'
                await call('blender_preview', {'request': {'project': str(root), 'preview': {
                    **preview_request, 'session_id': str(uuid.uuid4())}}}, error=True)
                contract = await input_file('contract.json', json.dumps({'schema': 'dcc.continuity.contract.v1',
                    'spec': {'schema': 'dcc.spec.v1', 'required': {target: {}}},
                    'allowed_object_prefixes': {target: sorted(OBJECT_FIELDS)}}))
                script = await input_file('recipe.py', '# Declarative live operation only\n')
                handoff = await input_file('handoff.md', 'Synthetic live qualification, no human approval implied')
                operation = {'schema': 'dcc.execution.operation.v2', 'backend': 'live', 'operation_id': str(uuid.uuid4()),
                    'stage': 'direction', 'script': script['path'], 'contract': contract['path'], 'handoff': handoff['path'],
                    'blender': args.blender, 'expected_parent': workflow.resume(root)['active']['id'], 'timeout': 90,
                    'live': {'recipe': 'object.transform', 'target': target, 'parameters': {'location': [2, 0, 0]}}}
                executed = await call('blender_execute', {'request': {'project': str(root), 'operation': operation}})
                assert executed['status'] == 'PUBLISHED' and executed['live_state'] == 'READY', executed
                checked = await call('blender_job', {'action': 'status', 'operation_id': operation['operation_id'],
                                                    'payload': {'project': str(root)}})
                assert checked['live_state'] == 'READY' and len(checked['current_fingerprint']) == 64
                assert await call('blender_execute', {'request': {'project': str(root), 'operation': operation}}) == executed
                second_preview = await call('blender_preview', {'request': {'project': str(root), 'preview': preview_request}})
                assert first_preview['kind'] == second_preview['kind'] == 'saved_copy_geometry_render'
                assert file_hash(first_preview['accepted']['images']['preview']) != file_hash(second_preview['accepted']['images']['preview'])
                active = workflow.resume(root)['active']
                submission = {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': c.checkpoint_ref(active),
                    'deliverables': {key: 'Synthetic direction' for key in ew.default_manifest()['stages'][0]['deliverables']},
                    'evidence': [{'kind': 'direction_record', 'file': {'path': handoff['relative_path'], 'sha256': handoff['sha256']}}],
                    'feedback_ids': [], 'note': 'Fixture ready'}
                submitted_file = await input_file('submission.json', json.dumps(submission))
                submitted = await cli('run-submit', str(root), '--submission', submitted_file['path'], '--evidence-root', str(out))
                assert submitted['status'] == ('COMPLETE' if args.mode == 'autonomous' else 'AWAITING_APPROVAL'), submitted
                successor = {**operation, 'operation_id': str(uuid.uuid4()), 'stage': 'blockout', 'expected_parent': active['id'],
                             'live': {**operation['live'], 'parameters': {'location': [3, 0, 0]}}}
                for name, values in [('blender_session', {'action': 'approve', 'payload': {}}),
                                     ('blender_job', {'action': 'approve', 'operation_id': operation['operation_id'], 'payload': {'project': str(root)}})]:
                    await call(name, values, error=True)
                if args.mode == 'approval_gated':
                    await call('blender_execute', {'request': {'project': str(root), 'operation': successor}}, error=True)
                    page = out / 'review-page'
                    built = review_page.build(root, page, before_views=Path(first_preview['accepted']['receipt']).parent,
                                              after_views=Path(second_preview['accepted']['receipt']).parent)
                    export = out / 'owner-fixture.json'
                    write_json(export, {'schema': 'dcc.review.export.v1', 'page': built['page_digest'], 'notes': [],
                        'review': {'reviewer': {'role': 'artist', 'author': 'Synthetic owner fixture',
                        'reference': 'Disposable qualification only'}, 'verdict': 'pass', 'finding': 'Fixture verified'}})
                    # A later manual edit invalidates the pending owner review before any import.
                    (out / 'mutate').write_text('mutate')
                    wait_for(lambda: (out / 'mutated').exists(), process)
                    try:
                        review_page.import_review(root, export, page, SyntheticOwnerConsole())
                    except (ValueError, RuntimeError) as exc:
                        assert 'DIVERGED' in str(exc), str(exc)
                    else:
                        raise AssertionError('Stale review approved a changed live scene')
                    # Restore only this fixture's known change using its owned UI control, then re-review.
                    (out / 'undo-fixture-mutate').write_text('restore fixture position')
                    wait_for(lambda: (out / 'fixture-restored').exists(), process)
                    imported = review_page.import_review(root, export, page, SyntheticOwnerConsole())
                    assert imported['results'][0]['status'] == 'COMMITTED'
                advanced = await call('blender_execute', {'request': {'project': str(root), 'operation': successor}})
                assert advanced['status'] == 'PUBLISHED', advanced
                assert file_hash(before['filepath']) == original_sha
                write_json(out / 'result.json', {'passed': True, 'case': 'modes', 'mode': args.mode,
                    'real_stdio_live_publication': True, 'preview_comparison_verified': True, 'wrong_session_refused': True,
                    'original_artist_file_unchanged': True, 'owner_import': args.mode == 'approval_gated',
                    'stale_review_refused': args.mode == 'approval_gated', 'synthetic_owner_only': True})
