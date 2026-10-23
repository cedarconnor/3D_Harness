"""Actual stdio protocol, no in-process transport stand-in."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import dcc_harness


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_installed_or_source_stdio_resources_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'dcc_harness.mcp_server', '--workspace', tmp], cwd=tmp,
                env={**os.environ, 'PYTHONPATH': str(Path(dcc_harness.__file__).resolve().parent.parent)})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn('harness_command', names)
                    self.assertIn('blender_observe', names)
                    self.assertTrue({'blender_capabilities','blender_recipe'} <= names)
                    self.assertTrue({'blender_session', 'blender_inspect', 'blender_execute', 'blender_job', 'blender_preview'} <= names)
                    self.assertNotIn('execute_blender_code', names)
                    from test_recipes import recipe, ADAPTER
                    adapter=Path(tmp)/'adapter.py'; adapter.write_text(ADAPTER)
                    drafted=await session.call_tool('blender_recipe',{'action':'draft','payload':{
                        'project':str(Path(tmp)/'project'),'recipe':recipe(),'adapter':str(adapter),'assets':[]}})
                    self.assertFalse(drafted.isError)
                    value=drafted.structuredContent or json.loads(drafted.content[0].text)
                    ref=value['result']; self.assertEqual(ref['state'],'DRAFT')
                    inspected=await session.call_tool('blender_recipe',{'action':'inspect','payload':{
                        'project':str(Path(tmp)/'project'),'recipe_id':ref['id'],'recipe_digest':ref['digest']}})
                    self.assertFalse(inspected.isError)
                    self.assertTrue((await session.call_tool('blender_recipe',{'action':'install','payload':{}})).isError)
                    self.assertTrue((await session.call_tool('blender_capabilities',{'action':'approve','payload':{}})).isError)
                    info = await session.call_tool('harness_info')
                    self.assertFalse(info.isError)
                    resources = await session.list_resources()
                    self.assertIn('harness://rules/index', {str(r.uri) for r in resources.resources})
                    resource = await session.read_resource('harness://rules/index')
                    self.assertIn('.agents/skills/dcc-harness/SKILL.md', json.loads(resource.contents[0].text)['files'])
                    nested = await session.read_resource('harness://rules/docs/guides/MANAGED_EXECUTION.md')
                    self.assertIn('approval_gated', nested.contents[0].text)
                    rule = await session.call_tool('harness_rules', {'path': 'docs/guides/MANAGED_EXECUTION.md'})
                    self.assertFalse(rule.isError)
                    good = await session.call_tool('harness_command', {'arguments': ['workflow-template']})
                    self.assertFalse(good.isError)
                    bad = await session.call_tool('harness_command', {'arguments': ['begin-edit']})
                    self.assertTrue(bad.isError)
                    help_result = await session.call_tool('harness_command_help', {'command': 'run-execute'})
                    self.assertFalse(help_result.isError)
                    invalid = await session.call_tool('harness_command', {'arguments': ['workflow-template', '--help']})
                    self.assertTrue(invalid.isError)
                    self.assertFalse((await session.call_tool('harness_info')).isError)
                    discovered = await session.call_tool('blender_session', {'action': 'discover', 'payload': {}})
                    self.assertFalse(discovered.isError)
                    for name, args in [('blender_session', {'action': 'approve', 'payload': {}}),
                                       ('blender_job', {'action': 'approve', 'operation_id': '', 'payload': {}})]:
                        self.assertTrue((await session.call_tool(name, args)).isError)
