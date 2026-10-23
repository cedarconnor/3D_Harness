import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from test_recipes import recipe, ADAPTER


class PublicCapabilityTests(unittest.TestCase):
    def test_unfulfilled_requirements_are_query_data_not_a_cli_failure(self):
        import contextlib, io, json
        from dcc_harness.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            request=Path(tmp)/'query.json'; request.write_text('{}')
            output=io.StringIO()
            with patch('sys.argv',['dcc-harness','capability-requirements','--request',str(request)]), \
                 patch('dcc_harness.capability_api.capability_action',return_value={'passed':False,'requirements':[]}), \
                 contextlib.redirect_stdout(output):
                main()
            self.assertEqual(json.loads(output.getvalue()),{'passed':False,'requirements':[]})

    def test_draft_inspect_scaffold_and_closed_actions(self):
        from dcc_harness.capability_api import recipe_action, capability_action
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); adapter=root/'adapter.py'; adapter.write_text(ADAPTER)
            ref=recipe_action('draft',{'project':tmp,'recipe':recipe(),'adapter':str(adapter),'assets':[]})
            self.assertEqual(ref['state'],'DRAFT')
            self.assertEqual(recipe_action('inspect',{'project':tmp,'recipe_id':ref['id'],'recipe_digest':ref['digest']})['state'],'DRAFT')
            self.assertIn('NotImplementedError',recipe_action('scaffold',{'recipe':recipe()})['adapter'])
            for action in ('approve','install','download'):
                with self.assertRaises(ValueError): capability_action(action,{})
                with self.assertRaises(ValueError): recipe_action(action,{})
            with self.assertRaises(ValueError): recipe_action('draft',{'project':tmp,'recipe':recipe(),'adapter':str(adapter),'assets':[],'run':True})

    def test_inventory_uses_configured_blender_and_explicit_roots(self):
        from dcc_harness.capability_api import capability_action
        from dcc_harness import environments
        with patch.object(environments,'inventory',return_value={'providers':[]}) as inventory:
            result=capability_action('inventory',{'roots':[{'path':'providers','namespace':''}],'out':'proof'},blender='configured')
        self.assertEqual(result,{'providers':[]})
        inventory.assert_called_once_with(None,blender='configured',roots=[{'path':'providers','namespace':''}],out='proof')
