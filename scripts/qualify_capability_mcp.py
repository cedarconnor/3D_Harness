"""Real stdio onboarding and execution, using owned background and GUI scenes."""
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid


def mcp_cases(args):
    sys.path.insert(0,str(Path(args.runtime).resolve()))
    from qualify_capabilities import onboarding
    from qualify_capability_routing import owned_bridge
    from dcc_harness.evidence import read_json,write_json
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    central=Path(args.qualification_root).resolve() if getattr(args,'qualification_root',None) else out/'onboarding'
    if not getattr(args,'qualification_root',None): onboarding(SimpleNamespace(**{**vars(args),'out':str(central)}))
    source=central/'project/capabilities/qualifications/capability_fixture.python_function/background/before.blend'
    results=[]
    for backend in ('background','live'):
        for mode in ('autonomous','approval_gated'):
            folder=out/(backend+'-'+mode)
            if backend=='live':
                with owned_bridge(args,folder,'BLENDER_EEVEE',source) as binding:
                    results.append(asyncio.run(project_case(args,folder,central,source,backend,mode,binding)))
            else:
                folder.mkdir(); results.append(asyncio.run(project_case(args,folder,central,source,backend,mode)))
            print('stdio',backend,mode,'PASS',flush=True)
    write_json(out/'VERIFICATION.json',{'passed':True,'case':'stdio','results':results})


async def project_case(args,folder,central,source,backend,mode,binding=None):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from dcc_harness import coordination as c,workflow,environment_workflow as ew,owner,execution
    from dcc_harness.evidence import read_json,write_json
    from dcc_harness.continuity_checks import OBJECT_FIELDS
    from qualify_capabilities import fixture_recipe,fixture_case
    from qualify_live_modes import SyntheticOwnerConsole
    actor={'role':'agent','author':'stdio fixture','reference':'Owned synthetic qualification'}
    params=StdioServerParameters(command=sys.executable,args=['-m','dcc_harness.mcp_server','--workspace',str(folder),'--blender',args.blender],
        cwd=folder,env={**os.environ,'PYTHONPATH':str(Path(args.runtime).resolve())})
    with (folder/'mcp.log').open('x',encoding='utf-8') as log:
        async with stdio_client(params,errlog=log) as (reader,writer):
            async with ClientSession(reader,writer,read_timeout_seconds=timedelta(seconds=600)) as session:
                await session.initialize()
                async def call(name,values,error=False):
                    result=await session.call_tool(name,values)
                    assert bool(result.isError)==error,result
                    if error: return result
                    value=result.structuredContent or json.loads(result.content[0].text)
                    return value['result'] if 'exit_code' in value else value
                async def cli(*arguments,error=False): return await call('harness_command',{'arguments':list(arguments)},error)
                async def cap(action,payload): return await call('blender_capabilities',{'action':action,'payload':payload})
                async def recipe(action,payload): return await call('blender_recipe',{'action':action,'payload':payload})
                async def input_file(name,text): return await call('harness_write_input',{'name':name,'content':text})
                brief=await input_file('brief.md','Owned add-on MCP workflow, no artistic acceptance.')
                if backend=='live':
                    attached=await call('blender_session',{'action':'attach','payload':{'destination':str(folder/'attached'),
                        'binding':str(binding),'scene':'Scene','brief_file':brief['path'],'mode':mode,'seconds':1800}})
                    root=Path(attached['project'])
                else:
                    measured=await cli('observe',str(source),'--blender',args.blender,'--output-dir',str(folder/'observe'))
                    decisions=await input_file('decisions.json','{}'); root=folder/'project'
                    await cli('start',str(root),'--checkpoint',str(source),'--observation',measured['observation'],
                              '--brief-file',brief['path'],'--decisions',decisions['path'])
                    await call('harness_bind',{'project':str(root),'expected_revision':'none','request_id':str(uuid.uuid4())})
                    await cli('run-create',str(root),'--mode',mode,'--seconds','1800')
                inventory=await cap('inventory',{'roots':[{'path':str(central/'providers'),'namespace':''}],'out':str(folder/'inventory')})
                provider=next(p for p in inventory['providers'] if p['id']=='capability_fixture')
                profile=await cap('profile',{'project':str(root),'inventory':inventory,'selected':['capability_fixture'],'preferences':{}})
                value=fixture_recipe(provider,'python_function','capability_fixture.mark',
                    [fixture_case('background'),fixture_case('live','live')],name='public.function')
                draft=await recipe('draft',{'project':str(root),'recipe':value,
                    'adapter':str(Path(__file__).resolve().parents[1]/'tests/fixtures/addons/capability_adapter.py'),'assets':[]})
                assert draft['state']=='DRAFT'
                assert (await recipe('inspect',{'project':str(root),'recipe_id':draft['id'],'recipe_digest':draft['digest']}))['state']=='DRAFT'
                qualified=await recipe('qualify',{'project':str(root),'recipe_id':draft['id'],'recipe_digest':draft['digest'],
                    'profile_digest':profile['digest'],'out':str(root/'capabilities/qualifications/public-function')})
                assert qualified['state']=='QUALIFIED',qualified
                await recipe('register',{'project':str(root),'report':qualified['report']})
                observation=read_json(workflow.resume(root)['active']['observation']); target=next(k for k,o in observation['objects'].items() if o['type']=='MESH')
                policy={'schema':'dcc.capability.policy.v1','id':'public-policy','version':1,'rules':[{
                    'id':'finish','capability':'surface.fixture','mode':'require','providers':['capability_fixture'],
                    'fallback_providers':[],'allow_manual':False,'candidates':[{'provider':'capability_fixture','recipe_id':draft['id'],
                    'recipe_digest':draft['digest'],'profile_digest':profile['digest']}],
                    'selectors':{'instance_ids':[target],'prefixes':[],'types':[]},'stages':['direction'],'slot':'finish',
                    'parameters':{'amount':.15,'behavior':'normal'},'dependencies':['geometry','materials'],'benchmark':None}]}
                await cap('bind',{'project':str(root),'policy':policy,'expected_revision':c.read(root)[-1]['id'],
                                 'request_id':str(uuid.uuid4()),'authority':actor})
                handoff=await input_file('handoff.md','Synthetic capability evidence only.')
                contract=await input_file('contract.json',json.dumps({'schema':'dcc.continuity.contract.v1',
                    'spec':{'schema':'dcc.spec.v1','required':{target:{}}},'allowed_object_prefixes':{target:sorted(OBJECT_FIELDS)}}))
                async def submit(name,error=False):
                    payload={'schema':'dcc.environment.submission.v1','stage_id':'direction','checkpoint':c.checkpoint_ref(workflow.resume(root)['active']),
                        'deliverables':{k:'Synthetic direction' for k in ew.default_manifest()['stages'][0]['deliverables']},
                        'evidence':[{'kind':'direction_record','file':{'path':handoff['relative_path'],'sha256':handoff['sha256']}}],
                        'feedback_ids':[],'note':'Provider use must be verified'}
                    ref=await input_file(name,json.dumps(payload))
                    return await cli('run-submit',str(root),'--submission',ref['path'],'--evidence-root',str(folder),error=error)
                await submit('missing.json',True)
                needed=await cap('requirements',{'project':str(root),'stage':'direction'}); req=needed['requirements'][0]['requirement']
                assert not needed['passed']; resolved=await cap('resolve',{'project':str(root),'requirement':req})
                prepared=await cap('prepare',{'project':str(root),'requirement':req,'resolution':resolved,'parameters':req['rule']['parameters'],
                    'operation_id':str(uuid.uuid4()),'contract':contract['path'],'handoff':handoff['path'],'timeout':120})
                assert prepared['status']=='PREPARED'
                request={'project':str(root),'operation':prepared['operation']}
                result=await call('blender_execute',{'request':request})
                assert result['status']=='PUBLISHED' and result.get('live_state','READY')=='READY',result
                assert await call('blender_execute',{'request':request})==result
                needed=await cap('requirements',{'project':str(root),'stage':'direction'}); assert needed['passed']
                req=needed['requirements'][0]['requirement']; resolved=await cap('resolve',{'project':str(root),'requirement':req})
                reused=await cap('prepare',{'project':str(root),'requirement':req,'resolution':resolved,'parameters':req['rule']['parameters'],
                    'operation_id':str(uuid.uuid4()),'contract':contract['path'],'handoff':handoff['path']})
                assert reused['status']=='REUSED' and len(execution._operations(root))==1
                entry=Path(provider['entry']); original=entry.read_bytes(); entry.write_bytes(original+b'\n# stdio source drift\n')
                try: await submit('stale.json',True)
                finally: entry.write_bytes(original)
                completed=await submit('valid.json')
                await call('blender_capabilities',{'action':'approve','payload':{}},True)
                if mode=='approval_gated':
                    assert completed['status']=='AWAITING_APPROVAL'
                    await cli('stage-complete',str(root),error=True)
                    payload={'submission_id':completed['submission']['revision'],'review':{'reviewer':{**actor,'role':'artist',
                        'reference':'SYNTHETIC OWNER CONSOLE, not actual human acceptance'},'verdict':'pass','finding':'Owned technical fixture'}}
                    approval=owner.confirm('stage.complete',payload,SyntheticOwnerConsole())
                    ew.apply(root,'stage.complete',payload,c.read(root)[-1]['id'],str(uuid.uuid4()),folder,approval)
                else: assert completed['status']=='COMPLETE'
                return {'passed':True,'backend':backend,'mode':mode,'stdio_onboarding':True,'missing_and_stale_blocked':True,
                        'stable_uuid_replay':True,'reuse_zero_jobs':True,'agent_approval_refused':True}
