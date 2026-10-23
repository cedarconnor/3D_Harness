"""Provider policy selects proven candidates and cannot substitute prose for use."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coordination_helpers import Fixture
from dcc_harness import coordination as c, execution
from dcc_harness.evidence import digest, write_json


def rule(mode='require'):
    return {'id':'surface','capability':'surface.fixture','mode':mode,
        'providers':['primary'],'fallback_providers':[],'allow_manual':False,
        'candidates':[{'provider':p,'recipe_id':p + '.effect','recipe_digest':v * 64,'profile_digest':v * 64}
                      for p,v in (('primary','a'),('secondary','b'))],
        'selectors':{'instance_ids':['ext.table.top'],'prefixes':[],'types':[]},
        'stages':['direction'],'slot':'finish','parameters':{'amount':.1},
        'dependencies':['geometry','materials'],'benchmark':None}


def policy(mode='require'):
    return {'schema':'dcc.capability.policy.v1','id':'project-effects','version':1,'rules':[rule(mode)]}


def requirement(mode='require'):
    value = rule(mode)
    return {'schema':'dcc.capability.requirement.v1','policy_digest':'f'*64,'rule':value,
            'target_id':'ext.table.top','target_type':'MESH','stage':'direction','engine':'BLENDER_EEVEE',
            'context':'background','blender_version':[5,1,1],'dependency_fingerprint':'d'*64}


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.inventory={'providers':[{'id':p,'availability':'AVAILABLE','compatible':True} for p in ('primary','secondary')]}

    def candidate(self, root, ref, req):
        return {'candidate':ref,'qualified':True,'score':None,'comparison':None}

    def resolve(self, req, evidence=None):
        from dcc_harness import capabilities
        with patch.object(capabilities,'candidate_evidence',side_effect=evidence or self.candidate):
            return capabilities.resolve(self.root,req,self.inventory)

    def test_require_unavailable_unqualified_and_incompatible(self):
        req=requirement(); self.inventory['providers'][0]['availability']='MISSING'
        self.assertEqual(self.resolve(req)['state'],'UNAVAILABLE')
        self.inventory['providers'][0]['availability']='AVAILABLE'
        self.assertEqual(self.resolve(req,lambda *a: {'qualified':False,'reason':'DRAFT'})['state'],'UNQUALIFIED')
        self.inventory['providers'][0]['compatible']=False
        self.assertEqual(self.resolve(req)['state'],'UNAVAILABLE')

    def test_prefer_has_no_implicit_fallback(self):
        req=requirement('prefer'); self.inventory['providers'][0]['availability']='MISSING'
        self.assertEqual(self.resolve(req)['state'],'UNAVAILABLE')
        req['rule']['fallback_providers']=['secondary']
        result=self.resolve(req)
        self.assertEqual(result['selected']['provider'],'secondary'); self.assertTrue(result['fallback_reason'])
        req['rule']['fallback_providers']=[]; req['rule']['allow_manual']=True
        result=self.resolve(req)
        self.assertEqual(result['state'],'RESOLVED'); self.assertIsNone(result['selected'])
        self.assertIn('manual',result['fallback_reason'])

    def test_timing_selection_unavailable_even_with_synthetic_scores(self):
        req=requirement('best_qualified'); req['rule']['providers']=['primary','secondary']
        req['rule']['benchmark']={'metric':'elapsed_seconds','direction':'minimize','case':'background'}
        self.assertEqual(self.resolve(req)['state'],'TIMING_SELECTION_UNAVAILABLE')
        def measured(root,ref,requirement):
            return {**self.candidate(root,ref,requirement),'score':1.0,'comparison':'same-inputs'}
        self.assertIsNone(self.resolve(req,measured)['selected'])
        req['rule']['providers'].reverse()
        self.assertIsNone(self.resolve(req,measured)['selected'])
        def different(root,ref,requirement):
            return {**measured(root,ref,requirement),'comparison':ref['provider']}
        self.assertEqual(self.resolve(req,different)['state'],'TIMING_SELECTION_UNAVAILABLE')

    def test_required_policy_cannot_enable_manual_fallback(self):
        from dcc_harness import capabilities
        value=policy(); value['rules'][0]['allow_manual']=True
        with self.assertRaises(ValueError): capabilities.validate_policy(value)

    def test_live_eligibility_requires_the_managed_background_reopen_environment(self):
        from dcc_harness import capabilities, recipes
        from test_recipes import recipe
        value=recipe(); value['provider']['id']='primary'; value['compatibility']['engines']=['BLENDER_EEVEE']
        req=requirement(); req['context']='live'
        bundle={'recipe':value,'report':{'blender':{'version':[5,1,1]},'results':[]},'qualification':{}}
        with patch.object(recipes,'require_qualified',return_value=bundle):
            result=capabilities.candidate_evidence(self.root,req['rule']['candidates'][0],req)
        self.assertFalse(result['qualified'])


class CapabilityGateTests(Fixture):
    def bind_policy(self, value=None):
        from dcc_harness import capabilities
        return capabilities.bind_policy(self.root,value or policy(),expected_revision=self.revision(),
                                         request_id=str(__import__('uuid').uuid4()),authority=self.actor())

    def test_manual_script_or_text_claim_cannot_satisfy_required_use_in_either_mode(self):
        from dcc_harness import capabilities
        self.bind(); self.bind_policy()
        execution.create(self.root, 'autonomous')
        config = execution.configuration(self.root)
        for mode in ('autonomous','approval_gated'):
            with patch.object(execution,'configuration',return_value={**config,'mode':mode}):
                with self.assertRaisesRegex(ValueError,'capability|required|receipt'):
                    self.submit(note='The required add-on was used; trust this text')
        self.assertFalse(any(e['kind']=='stage.submit' for e in c.read(self.root)))
        self.assertEqual(capabilities.verify_receipts(self.root,'direction',self.cp())['passed'],False)

    def test_rebinding_policy_invalidates_previous_stage_and_submission(self):
        self.bind(); self.complete(self.submit())
        result=self.bind_policy()
        from dcc_harness import environment_workflow as ew
        states=ew.stages(c.read(self.root),c.Continuity(self.root).status())
        self.assertEqual(states['direction']['state'],'needs_review')
        revised=policy(); revised['version']=2; revised['rules'][0]['parameters']['amount']=.2
        later=self.bind_policy(revised)
        self.assertNotEqual(result['result']['policy_digest'],later['result']['policy_digest'])

    def test_receipt_needs_service_operation_and_matching_target_checkpoint(self):
        from dcc_harness import capabilities
        self.bind(); self.bind_policy()
        fake=self.root / 'capabilities/receipts/fake.json'
        write_json(fake,{'schema':'dcc.capability.receipt.v1','target_id':'unrelated','checkpoint':self.cp(),
                         'operation_id':'00000000-0000-0000-0000-000000000001','passed':True})
        self.assertFalse(capabilities.verify_receipts(self.root,'direction',self.cp())['passed'])
        with self.assertRaisesRegex(ValueError,'capability|required|receipt'): self.submit()

    def test_projects_without_policy_keep_existing_stage_behavior(self):
        self.bind(); self.assertEqual(self.complete(self.submit())['status'],'COMMITTED')

    def test_guidance_exposes_unsatisfied_capabilities_and_resolution(self):
        from dcc_harness import guidance
        self.bind(); self.bind_policy()
        report=guidance.requirements(self.root,'direction')['capabilities']
        self.assertFalse(report['passed'])
        self.assertEqual(report['requirements'][0]['resolution']['state'],'UNAVAILABLE')

    def test_receipt_validator_rejects_incomplete_or_extra_evidence(self):
        from dcc_harness import capabilities
        with self.assertRaises(ValueError): capabilities.validate_receipt({'schema':'dcc.capability.receipt.v1'})
        value={key:'a'*64 for key in ('request_sha256','requirement_digest','current_requirement_digest','effect_id',
            'policy_digest','recipe_digest','profile_digest','parameters_digest','input_dependency_fingerprint',
            'dependency_fingerprint','output_fingerprint')}
        value.update(schema='dcc.capability.receipt.v1',operation_id=str(__import__('uuid').uuid4()),
                     target_id='ext.table.top',capability='surface.fixture',slot='finish',provider='primary',checkpoint=self.cp(),
                     evidence={name:'b'*64 for name in ('capability-output.json','capability-verified.json','observation.json')})
        self.assertEqual(capabilities.validate_receipt(value),value)
        value['target_id']='object:模型 1'
        self.assertEqual(capabilities.validate_receipt(value),value)
        value['evidence'].pop('observation.json')
        with self.assertRaises(ValueError): capabilities.validate_receipt(value)

    def test_explicit_manual_fallback_records_reason_without_claiming_provider_use(self):
        self.bind(); value=policy('prefer'); value['rules'][0]['allow_manual']=True
        self.bind_policy(value)
        submitted=self.submit()
        row=submitted['result']['capabilities']['requirements'][0]
        self.assertTrue(row['passed']); self.assertIn('manual',row['fallback_reason'])
        self.assertEqual(self.complete(submitted)['status'],'COMMITTED')
