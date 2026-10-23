"""Regressions from the final P22 adversarial review."""
import contextlib
import io
import json
import unittest
import uuid
from unittest.mock import patch

from coordination_helpers import Console, Fixture
from dcc_harness import capabilities, coordination as c, owner, recipes
from dcc_harness.evidence import write_json
from test_capabilities import policy
from test_recipes import recipe


class CapabilityAuthorityTests(Fixture):
    def test_agent_cannot_replace_artist_bound_policy_or_clear_required_evidence(self):
        self.bind(); value=policy(); actor=self.actor('artist')
        approval=owner.confirm('capability.bind',{'policy':value,'authority':actor},Console())
        capabilities.bind_policy(self.root,value,expected_revision=self.revision(),request_id=str(uuid.uuid4()),authority=actor,approval=approval)
        before=self.revision(); changed={**value,'version':2,'rules':[]}
        with self.assertRaisesRegex(owner.OwnerRequired,'artist-bound'):
            capabilities.bind_policy(self.root,changed,expected_revision=before,request_id=str(uuid.uuid4()),authority=self.actor())
        self.assertEqual(self.revision(),before)
        self.assertFalse(capabilities.verify_receipts(self.root,'direction',self.cp())['passed'])
        with self.assertRaisesRegex(ValueError,'capability|required|receipt'): self.submit()
        approved=owner.confirm('capability.bind',{'policy':changed,'authority':actor},Console())
        capabilities.bind_policy(self.root,changed,expected_revision=before,request_id=str(uuid.uuid4()),authority=actor,approval=approved)
        self.assertTrue(capabilities.verify_receipts(self.root,'direction',self.cp())['passed'])

    def test_owner_cli_confirms_binding_and_identical_retry_does_not_prompt(self):
        from dcc_harness.__main__ import main
        self.bind(); request=self.base/'owner-policy.json'
        write_json(request,{'project':str(self.root),'policy':policy(),'authority':self.actor('artist'),
            'expected_revision':self.revision(),'request_id':str(uuid.uuid4())})
        console=Console(); argv=['dcc-harness','capability-bind','--request',str(request)]
        with patch('sys.argv',argv),patch.object(owner,'Terminal',return_value=console),contextlib.redirect_stdout(io.StringIO()):
            main(); main()
        self.assertEqual(len(console.shown),1)
        self.assertIn('project-effects',console.shown[0])
        bound=capabilities.bound_policy(c.read(self.root))
        self.assertEqual(bound['owner_approval']['channel'],'owner_terminal')

    def test_owner_cli_binding_still_refuses_agent_terminal(self):
        from dcc_harness.__main__ import main
        self.bind(); request=self.base/'agent-policy.json'; before=self.revision()
        write_json(request,{'project':str(self.root),'policy':policy(),'authority':self.actor('artist'),
            'expected_revision':before,'request_id':str(uuid.uuid4())})
        console=Console(environ={'DCC_HARNESS_AGENT':'1'})
        with patch('sys.argv',['dcc-harness','capability-bind','--request',str(request)]),patch.object(owner,'Terminal',return_value=console):
            with self.assertRaisesRegex(owner.OwnerRequired,'agent session'): main()
        self.assertEqual(console.shown,[]); self.assertEqual(self.revision(),before)


class NativeInvocationNameTests(unittest.TestCase):
    def test_node_group_names_are_native_text_in_host_and_serialized_contract(self):
        from importlib.resources import files
        from jsonschema import Draft202012Validator
        schema=json.loads(files('dcc_harness').joinpath('data/capabilities/recipe.schema.json').read_text())
        for name in ('Geometry Nodes','磨损 Finish'):
            value=recipe(); value['invocation'].update(kind='node_asset',entry=name)
            self.assertEqual(recipes.validate(value)['invocation']['entry'],name)
            Draft202012Validator(schema).validate(value)
        for name in ('','bad\x00name','x'*256):
            value=recipe(); value['invocation'].update(kind='node_asset',entry=name)
            with self.assertRaises(ValueError): recipes.validate(value)
            self.assertFalse(Draft202012Validator(schema).is_valid(value))

    def test_function_and_operator_entries_require_callable_syntax(self):
        for kind,entry in (('python_function','module..function'),('python_function','module.bad-name'),
                           ('operator','object.name.extra'),('operator','object.bad-name')):
            value=recipe(); value['invocation'].update(kind=kind,entry=entry)
            with self.assertRaises(ValueError): recipes.validate(value)
