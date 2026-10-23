"""Owned revision sequence: no artist scene or global preferences are touched."""
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import uuid


def revisions(args):
    sys.path.insert(0,str(Path(args.runtime).resolve()))
    from qualify_capabilities import onboarding
    from qualify_capability_routing import owned_bridge, reuse_qualification
    from dcc_harness import capabilities as cap, workflow, observe, bootstrap, execution, live, coordination as c, recipes
    from dcc_harness.evidence import read_json,write_json
    from dcc_harness.continuity_checks import OBJECT_FIELDS
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    central=Path(args.qualification_root).resolve() if getattr(args,'qualification_root',None) else out/'onboarding'
    if not getattr(args,'qualification_root',None): onboarding(SimpleNamespace(**{**vars(args),'out':str(central)}))
    proof=read_json(central/'VERIFICATION.json'); assert proof['passed']
    source=central/'project/capabilities/qualifications/fixture.shared/shared_valid/before.blend'
    actor={'role':'agent','author':'owned revision qualifier','reference':'Synthetic fixture only'}
    reports=[]

    def sequence(folder,root,backend,binding=None,*,constant=False):
        recipe_id='capability_fixture.python_function' if constant else 'capability_fixture.adaptive'
        choice=next(r for r in proof['recipes'] if r['recipe']['id']==recipe_id)
        reuse_qualification(central/'project',root)
        current=lambda: workflow.resume(root)['active']
        observed=lambda: read_json(current()['observation'])
        target=next(k for k,o in observed()['objects'].items() if o['name']=='Cube')
        shared=next(k for k,o in observed()['objects'].items() if k!=target and o['type']=='MESH')
        value={'schema':'dcc.capability.policy.v1','id':'revision-fixture','version':1,'rules':[{
            'id':'finish','capability':'surface.fixture','mode':'require','providers':['capability_fixture'],
            'fallback_providers':[],'allow_manual':False,'candidates':[{'provider':'capability_fixture',
            'recipe_id':choice['recipe']['id'],'recipe_digest':choice['recipe']['digest'],'profile_digest':choice['profile']['digest']}],
            'selectors':{'instance_ids':[target],'prefixes':[],'types':[]},'stages':['direction'],'slot':'finish',
            'parameters':{'amount':.15,'behavior':'normal'},'dependencies':['geometry','materials'],'benchmark':None}]}
        def bind(): cap.bind_policy(root,value,expected_revision=c.read(root)[-1]['id'],request_id=str(uuid.uuid4()),authority=actor)
        bind()
        contract=folder/'contract.json'
        write_json(contract,{'schema':'dcc.continuity.contract.v1','spec':{'schema':'dcc.spec.v1','required':{target:{},shared:{}}},
            'allowed_object_prefixes':{key:sorted(OBJECT_FIELDS) for key in observed()['objects']}})
        handoff=folder/'handoff.md'; handoff.write_text('Owned capability revision fixture, no artistic acceptance.')
        steps=[]; contributions=[]
        def required(): return cap.requirements(root,'direction',observed())[0]
        def apply(expected,count):
            req=required(); decision=cap.resolve(root,req,cap.inventory_for_requirement(root,req))
            before=len(execution._operations(root))
            result=cap.execute(root,req,decision,req['rule']['parameters'],str(uuid.uuid4()),blender=args.blender,
                               contract=contract,handoff=handoff,timeout=120)
            assert result['status']==expected,result
            assert len(execution._operations(root))==before+(expected=='PUBLISHED')
            mods=observed()['objects'][target]['modifier_settings']
            assert len(mods)==count,mods
            assert cap.verify_receipts(root,'direction',c.checkpoint_ref(current()))['passed']
            if expected=='PUBLISHED':
                operation=Path(result['capability_receipt']['path']).parent
                output=read_json(operation/'capability-output.json')
                verified=read_json(operation/'capability-verified.json')
                assert verified['passed'] and verified['native_effect']==output['native_effect']
                invocation=output['invocation_evidence']; assert len(invocation)==1
                assert invocation[0]['native_effect_before']!=invocation[0]['native_effect_after']
                width=output['native_effect']['state']['settings']['width']
                measured=next(m for m in mods if m['settings']['name']==output['native_effect']['name'])
                assert math.isclose(measured['settings']['width'],width,rel_tol=1e-6)
                contributions.append({'operation_id':operation.name,'native_effect_before':invocation[0]['native_effect_before'],
                    'native_effect_after':output['native_effect'],'independent_saved_verification':str(operation/'capability-verified.json')})
            return result
        def edit(action):
            before=observed(); parent=current()['id']; name=str(uuid.uuid4())
            if backend=='live':
                write_json(folder/'fixture-edit.json',{'id':name,'action':action,'target':target})
                deadline=time.monotonic()+30
                while not (folder/(name+'.json')).exists():
                    if time.monotonic()>deadline: raise TimeoutError('Owned edit control')
                    time.sleep(.1)
                assert read_json(folder/(name+'.json'))['passed']
                result=live.refresh(root,binding,expected_parent=parent)
                assert result['state']=='READY',result
            elif action!='reload':
                script=folder/(name+'.py')
                commands={'geometry':"obj.data.vertices[0].co.x += .125; obj.data.update()",
                    'delete':"[obj.modifiers.remove(m) for m in list(obj.modifiers) if m.name.startswith('DCC::')]",
                    'unrelated':"bpy.context.scene.camera.location.x += .25",
                    'material':"obj.active_material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.72"}
                script.write_text('import bpy\nobj=next(o for o in bpy.context.scene.objects if o.get("dcc_instance_id")=='+repr(target)+')\n'+commands[action]+'\n')
                edit_contract=contract
                if action=='material':
                    edit_contract=folder/(name+'-contract.json')
                    write_json(edit_contract,{**read_json(contract),'allowed_material_inputs':
                        {mid:{'Principled BSDF':{'Roughness':.72}} for mid in observed()['materials']}})
                result=execution.execute(root,'direction',name,script,edit_contract,handoff,args.blender,parent,timeout=120)
                assert result['status']=='PUBLISHED',result
            else:
                reopened=observe.observe_file(current()['checkpoint'],folder/('reopen-'+name),args.blender)
                from dcc_harness.live_snapshot import equivalent
                assert equivalent({'objects':read_json(reopened['observation'])['objects']},{'objects':before['objects']})
            return cap.changes(root,before,observed())
        first=apply('PUBLISHED',1); effect=read_json(first['capability_receipt']['path'])['effect_id']
        apply('REUSED',1); steps.append('same-input-zero-jobs')
        edit('unrelated'); apply('REUSED',1); steps.append('unrelated-checkpoint-inherited')
        if constant:
            edit('geometry'); active=c.checkpoint_ref(current()); prior=observed()['objects'][target]['modifier_settings']
            req=required(); decision=cap.resolve(root,req,cap.inventory_for_requirement(root,req))
            operation_id=str(uuid.uuid4()); before=len(execution._operations(root))
            result=cap.execute(root,req,decision,req['rule']['parameters'],operation_id,blender=args.blender,
                               contract=contract,handoff=handoff,timeout=120)
            assert result['status']=='NEEDS_RECONCILIATION',result
            assert len(execution._operations(root))==before+1
            operation=root/'execution/operations'/operation_id
            reason=(operation/'execute.log').read_text() if backend=='background' else str(read_json(operation/'live-status.json'))
            assert 'Unchanged provider invocation has no prior exact successful proof' in reason,reason
            assert c.checkpoint_ref(current())==active and observed()['objects'][target]['modifier_settings']==prior
            assert not (operation/'capability-receipt.json').exists() and not (operation/'capability-output.json').exists()
            assert not cap.verify_receipts(root,'direction',active)['passed']
            # Leave this failed disposable operation retained. Never retry/recover its mutation.
            return {'backend':backend,'passed':True,'recipe_id':recipe_id,'steps':steps+['constant-output-refresh-refused'],
                    'refused_operation':operation_id,'status':result['status'],'active_checkpoint_unchanged':True,
                    'contributions':contributions,'operation_count':before+1}
        for action in ('geometry','material','delete'):
            if action=='delete':
                effect_name='DCC::'+effect[:48]
                assert [m['settings']['name'] for m in observed()['objects'][target]['modifier_settings']]==[effect_name]
            changed=edit(action)
            if action=='delete':
                assert observed()['objects'][target]['modifier_settings']==[]
                # Output receipt invalidation is distinct from authored dependency changes.
            else:
                assert changed,(action,'missing lifecycle delta')
            assert not cap.verify_receipts(root,'direction',c.checkpoint_ref(current()))['passed']
            result=apply('PUBLISHED',1)
            assert read_json(result['capability_receipt']['path'])['effect_id']==effect
            assert observed()['objects'][target]['material_ids']==observed()['objects'][shared]['material_ids']
            if action in ('geometry','material'):
                old,new=contributions[-1]['native_effect_before'],contributions[-1]['native_effect_after']
                assert old['state']['settings']['width']!=new['state']['settings']['width']
            steps.append(action+'-one-update')
        edit('reload'); apply('REUSED',1); steps.append('reload-retained')
        value['version']=2; value['rules'][0]['slot']='second'; bind(); result=apply('PUBLISHED',2)
        assert read_json(result['capability_receipt']['path'])['effect_id']!=effect
        steps.append('explicit-slot-second-layer')
        _,profile=recipes.current_profile(root,choice['profile']['digest'])
        entry=Path(profile['providers'][0]['entry']); original=entry.read_bytes(); count=len(execution._operations(root))
        entry.write_bytes(original+b'\n# provider source revision\n')
        try:
            req=required(); decision=cap.resolve(root,req,cap.inventory_for_requirement(root,req))
            assert decision['state']!='RESOLVED'
            assert not cap.verify_receipts(root,'direction',c.checkpoint_ref(current()))['passed']
        finally: entry.write_bytes(original)
        assert len(execution._operations(root))==count
        steps.append('source-change-requalification-stop')
        return {'backend':backend,'passed':True,'recipe_id':recipe_id,'steps':steps,'operation_count':count,
                'shared_users':2,'contributions':contributions}

    for backend in ('background','live'):
        for constant in (False,True):
            folder=out/(backend+'-constant' if constant else backend)
            if backend=='live':
                with owned_bridge(args,folder,'BLENDER_EEVEE',source) as binding:
                    brief=folder/'brief.md'; brief.write_text('Owned lifecycle proof')
                    attached=live.attach(folder/'attached',binding,scene='Scene',brief_file=brief,mode='autonomous',
                                         blender=args.blender,seconds=2400,max_operations=30)
                    reports.append(sequence(folder,Path(attached['project']),backend,binding,constant=constant))
            else:
                folder.mkdir(); measured=observe.observe_file(source,folder/'observe',args.blender)
                root=folder/'project'; workflow.start(root,source,measured['observation'],'Owned lifecycle proof',{})
                bootstrap.bind_rules(root,folder,'none',str(uuid.uuid4())); execution.create(root,'autonomous',seconds=2400,max_operations=30)
                reports.append(sequence(folder,root,backend,constant=constant))
            print(folder.name,'revisions PASS',flush=True)
    write_json(out/'VERIFICATION.json',{'passed':True,'case':'revisions','results':reports,
        'limits':'Synthetic technical scale/finish rule only. Changed-dependency idempotent refresh without qualifying contribution remains unsupported.'})
