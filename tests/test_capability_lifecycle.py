"""Lifecycle decisions use measured dependencies and retained service evidence."""
import copy
from pathlib import Path
import uuid
from unittest.mock import patch

from coordination_helpers import Fixture
from test_capabilities import policy
from dcc_harness import capabilities as cap, coordination as c, recipes, execution, guidance
from dcc_harness.evidence import read_json, write_json, digest


class LifecycleTests(Fixture):
    def bind_capability(self, value=None):
        self.bind()
        cap.bind_policy(self.root,value or policy(),expected_revision=self.revision(),request_id=str(uuid.uuid4()),authority=self.actor())

    def test_enrollment_dependencies_and_irrelevant_changes(self):
        value=policy(); value['rules'][0]['selectors']={'instance_ids':[],'prefixes':['ext.table.'],'types':[]}
        self.bind_capability(value)
        changed=copy.deepcopy(self.obs); changed['scene']['world']='unrelated'
        self.assertEqual(cap.changes(self.root,self.obs,changed),[])
        with_effect=copy.deepcopy(self.obs)
        with_effect['objects']['ext.table.top']['modifier_settings']=[{'type':'BEVEL','settings':{'width':.2}}]
        without_effect=copy.deepcopy(with_effect)
        without_effect['objects']['ext.table.top']['modifier_settings']=[]
        self.assertEqual(cap.changes(self.root,with_effect,without_effect),[])
        changed['objects']['ext.table.new']=copy.deepcopy(changed['objects']['ext.table.top'])
        self.assertIn('ENROLLED',[r['state'] for r in cap.changes(self.root,self.obs,changed)])
        changed=copy.deepcopy(self.obs); changed['objects']['ext.table.top']['source_mesh_hash']='changed'
        self.assertEqual(cap.changes(self.root,self.obs,changed)[0]['state'],'DEPENDENCIES_CHANGED')
        changed=copy.deepcopy(self.obs); changed['materials']['stone']['diffuse_color']=[1,0,0,1]
        self.assertEqual(cap.changes(self.root,self.obs,changed)[0]['state'],'DEPENDENCIES_CHANGED')
        self.assertEqual(cap.requirements(self.root,'delivery',self.obs),[])

    def evidence(self,value=None):
        self.bind_capability(value)
        execution.create(self.root,'autonomous')
        native=c.Continuity(self.root).status(); active=native['active']; observation=read_json(active['observation'])
        req=cap.requirements(self.root,'direction',observation)[0]
        selected=req['rule']['candidates'][0]
        resolution={'selected':selected,'state':'RESOLVED'}
        identity=str(uuid.uuid4()); folder=self.root/'execution/operations'/identity; folder.mkdir(parents=True)
        context={'root':str(self.root),'requirement':req,'resolution':resolution,'parameters':req['rule']['parameters'],
                 'effect_id':cap.effect_key(req['rule']['capability'],req['target_id'],req['rule']['slot'])}
        request={'backend':'background','capability':context,'files':{},'operation_id':identity}
        coverage={'reads':['geometry','materials'],'writes':['modifiers'],'dependencies':['geometry','materials']}
        measured=cap.observed_scope(observation,req['target_id'],['geometry','materials','modifiers'])
        write_json(folder/'request.json',request)
        output={'effect_id':context['effect_id'],'effect_count':1,'measurements':measured}
        write_json(folder/'capability-output.json',{'after':measured,'output':output,'output_fingerprint':digest(output)})
        write_json(folder/'capability-verified.json',{'passed':True,'output_fingerprint':digest(output),'measurements':measured,'output':output})
        write_json(folder/'observation.json',observation)
        result={'status':'PUBLISHED','outcome':{'active':active}}
        with patch.object(recipes,'require_qualified',return_value={'recipe':{'coverage':coverage}}):
            cap.prepare_operation_receipt(self.root,folder,request)
        result['capability_receipt']=cap.record_operation(self.root,folder,result,request)
        write_json(folder/'outcome.json',result)
        return native,req,folder,{'recipe':{'coverage':coverage}}

    def test_receipt_inherits_only_when_actual_output_and_dependencies_match(self):
        native,req,folder,bundle=self.evidence()
        changed=read_json(native['active']['observation']); changed['scene']['world']='unrelated'
        path=self.base/'later.json'; write_json(path,changed)
        later=copy.deepcopy(native); later['active'].update(id='b'*64,checkpoint_sha256='c'*64,observation=str(path))
        later['task_history'].append(later['active'])
        with patch.object(recipes,'require_qualified',return_value=bundle),patch.object(c,'Continuity') as store:
            store.return_value.status.return_value=later
            self.assertTrue(cap.verify_operation_receipt(self.root,folder,req,c.checkpoint_ref(later['active'])))
            changed['objects'][req['target_id']]['modifier_settings']=[{'type':'BEVEL','settings':{'width':.2}}]
            path.write_text(__import__('json').dumps(changed))
            self.assertFalse(cap.verify_operation_receipt(self.root,folder,req,c.checkpoint_ref(later['active'])))

    def test_fresh_request_reuses_without_new_job_or_input_folder(self):
        native,req,folder,bundle=self.evidence()
        decision={'state':'RESOLVED','selected':req['rule']['candidates'][0]}
        with patch.object(recipes,'require_qualified',return_value=bundle),patch.object(cap,'resolve',return_value=decision),patch.object(execution,'execute_operation') as dispatch:
            result=cap.execute(self.root,req,decision,req['rule']['parameters'],str(uuid.uuid4()),
                               blender='not invoked',contract=self.contract,handoff=self.handoff)
        self.assertEqual(result['status'],'REUSED'); dispatch.assert_not_called()
        self.assertFalse((self.root/'capabilities/inputs').exists())
        self.assertEqual(len(list((self.root/'execution/operations').iterdir())),1)

    def test_unmeasured_properties_and_underdeclared_dependencies_cannot_be_selected(self):
        from test_recipes import recipe
        from test_capabilities import requirement
        value=recipe(); value['provider']['id']='primary'; value['capabilities']=['surface.fixture']
        value['compatibility']['engines']=['BLENDER_EEVEE']
        req=requirement(); req['rule']['parameters']={'amount':.1}
        bundle={'recipe':value,'report':{'blender':{'version':[5,1,1]}},'qualification':{}}
        for field in ('properties','transform'):
            value['coverage']['dependencies']=[field]
            with patch.object(recipes,'require_qualified',return_value=bundle):
                self.assertFalse(cap.candidate_evidence(self.root,req['rule']['candidates'][0],req)['qualified'])

    def test_completed_stage_and_next_recheck_capability_sources(self):
        from dcc_harness import environment_workflow as ew
        self.bind_capability()
        with patch.object(cap,'verify_receipts',return_value={'passed':True,'requirements':[]}):
            self.complete(self.submit())
        native=c.Continuity(self.root).status()
        self.assertEqual(ew.stages(c.read(self.root),native)['direction']['state'],'needs_review')
        result=guidance.next_steps(self.root)
        self.assertIn('capability-required',[row['id'] for row in result['steps']])

    def test_effect_identity_is_stable_and_slots_are_explicit(self):
        self.assertEqual(cap.effect_key('surface.fixture','one','finish'),cap.effect_key('surface.fixture','one','finish'))
        self.assertNotEqual(cap.effect_key('surface.fixture','one','finish'),cap.effect_key('surface.fixture','one','second'))

    def test_verified_best_selection_can_reuse_when_output_no_longer_matches_empty_benchmark_input(self):
        native,req,folder,bundle=self.evidence(policy('best_qualified'))
        decision={'state':'NO_COMPARABLE_EVIDENCE','selected':None}
        with patch.object(recipes,'require_qualified',return_value=bundle),patch.object(cap,'resolve',return_value=decision):
            result=cap.execute(self.root,req,decision,req['rule']['parameters'],str(uuid.uuid4()),
                               blender='not invoked',contract=self.contract,handoff=self.handoff)
        self.assertEqual(result['status'],'REUSED')

    def test_reuse_still_requires_the_pinned_runtime(self):
        native,req,folder,bundle=self.evidence()
        config=execution.configuration(self.root); config['runtime']={'version':'old','source_digest':'a'*64}
        decision={'state':'RESOLVED','selected':req['rule']['candidates'][0]}
        with patch.object(execution,'configuration',return_value=config),patch.object(recipes,'require_qualified',return_value=bundle),patch.object(cap,'resolve',return_value=decision):
            with self.assertRaisesRegex(ValueError,'runtime'):
                cap.reuse(self.root,req,decision,req['rule']['parameters'])
