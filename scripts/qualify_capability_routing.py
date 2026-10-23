"""Owned background/live capability execution with both review policies."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import uuid
import zipfile


@contextmanager
def owned_bridge(args,out,engine,source=None):
    from dcc_harness import distribution,blender_bridge
    from qualify_live import wait_for,verify_private_cleanup
    out.mkdir(parents=True,exist_ok=False)
    distribution.export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive: archive.extractall(out / 'addon')
    with socket.socket() as listener: listener.bind(('127.0.0.1',0)); port=listener.getsockname()[1]
    script=out / 'gui.py'
    script.write_text('CONFIG = '+repr({'out':str(out),'port':port,'engine':engine,'source':str(source) if source else None})+'\n'+'''
import bpy,json,sys,time
from pathlib import Path
out=Path(CONFIG['out']); sys.path.insert(0,str(out / 'addon'))
assert Path(bpy.utils.user_resource('CONFIG')).resolve() == (out / 'config').resolve(), 'Owned configuration required'
bpy.context.preferences.filepaths.temporary_directory=str(out / 'temporary')
if CONFIG['source']: bpy.ops.wm.open_mainfile(filepath=CONFIG['source'])
bpy.context.scene.render.engine=CONFIG['engine']
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'artist-fixture.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out / 'artist-fixture.blend'))
attempts=[]
def audit(event,args):
    if event=='socket.connect': attempts.append(str(args[1])); raise RuntimeError('Unexpected connection')
sys.addaudithook(audit)
watched=('undo_post','redo_post','depsgraph_update_post')
before={k:tuple(getattr(bpy.app.handlers,k)) for k in watched}
import dcc_harness_bridge as bridge
bridge.register(); bridge.server=bridge.ObservationServer(CONFIG['port'],out); bridge.server.start()
(out / 'ready.json').write_text(json.dumps({'descriptor':str(bridge.server.session.descriptor_path)}))
deadline=time.monotonic()+900
def control():
    command=out / 'fixture-edit.json'
    if command.exists():
        value=json.loads(command.read_text()); command.unlink()
        try:
            obj=next((o for o in bpy.context.scene.objects if o.get('dcc_instance_id')==value.get('target')),None)
            if value['action']=='geometry': obj.data.vertices[0].co.x += .125; obj.data.update()
            elif value['action']=='delete':
                for mod in list(obj.modifiers):
                    if mod.name.startswith('DCC::'): obj.modifiers.remove(mod)
            elif value['action']=='unrelated': bpy.context.scene.camera.location.x += .25
            elif value['action']=='material': obj.active_material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.72
            elif value['action']=='reload':
                bpy.ops.wm.save_as_mainfile(filepath=str(out / 'reload.blend'))
                bpy.ops.wm.open_mainfile(filepath=str(out / 'reload.blend'))
            else: raise ValueError('Unsupported owned fixture action')
            result={'passed':True}
        except Exception as exc: result={'passed':False,'error':str(exc)}
        (out / (value['id']+'.json')).write_text(json.dumps(result))
    if (out / 'stop').exists() or time.monotonic()>deadline:
        bridge.unregister()
        assert not attempts and all(tuple(getattr(bpy.app.handlers,k))==before[k] for k in watched)
        assert not any(k=='dcc_harness' or k.startswith('dcc_harness.') for k in sys.modules)
        (out / 'audit.json').write_text(json.dumps({'outbound_attempts':attempts,'activity_handlers_unchanged':True,'standalone_export':True}))
        bpy.ops.wm.quit_blender(); return None
    return .1
bpy.app.timers.register(control,persistent=True)
''')
    config=out / 'config'; config.mkdir(); temporary=out / 'temporary'; temporary.mkdir()
    startup=None
    if os.name=='nt':
        startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    with (out / 'gui.log').open('x') as log:
        process=subprocess.Popen([args.blender,'--offline-mode','--factory-startup','--disable-autoexec',
            '--python-exit-code','1','--python',str(script)],stdout=log,stderr=subprocess.STDOUT,
            startupinfo=startup,env={**os.environ,'BLENDER_USER_CONFIG':str(config),'TEMP':str(temporary),'TMP':str(temporary),
                                   'BLENDER_USER_EXTENSIONS':str(out / 'extensions')})
        token=None
        try:
            wait_for(lambda:(out / 'ready.json').exists(),process)
            binding=json.loads((out / 'ready.json').read_text())['descriptor']
            token=blender_bridge.descriptor(binding)['token']
            yield binding
        finally:
            (out / 'stop').write_text('stop')
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)
        assert process.returncode==0 and (out / 'audit.json').exists()
    if token: verify_private_cleanup(out,token)


def reuse_qualification(source,root):
    from dcc_harness import recipes
    for name in ('profiles','recipes','qualifications'):
        shutil.copytree(source / 'capabilities' / name,root / 'capabilities' / name)
    for path in (root / 'capabilities/qualifications').glob('*/report.json'):
        if json.loads(path.read_text())['passed']:
            recipes.register_qualified(root,path)


def project_case(args,out,root,central,mode,backend):
    from dcc_harness import capabilities,workflow,coordination as c,environment_workflow as ew,execution,owner
    from dcc_harness.evidence import read_json,write_json,file_hash
    from dcc_harness.continuity_checks import OBJECT_FIELDS
    from qualify_live_modes import SyntheticOwnerConsole
    reuse_qualification(central / 'project',root)
    proof=read_json(central / 'VERIFICATION.json')
    choices=[item for item in proof['recipes'] if item['recipe']['id'] in ('capability_fixture.python_function','capability_second.python_function')]
    active=workflow.resume(root)['active']; observation=read_json(active['observation'])
    target=next(key for key,obj in observation['objects'].items() if obj['type']=='MESH')
    actor={'role':'agent','author':'synthetic capability qualification','reference':'Owned disposable scene'}
    value={'schema':'dcc.capability.policy.v1','id':'fixture-policy','version':1,'rules':[{
        'id':'surface','capability':'surface.fixture','mode':'require','providers':['capability_fixture','capability_second'],
        'fallback_providers':[],'allow_manual':False,
        'candidates':[{'provider':item['recipe']['id'].split('.')[0],'recipe_id':item['recipe']['id'],
                       'recipe_digest':item['recipe']['digest'],'profile_digest':item['profile']['digest']} for item in choices],
        'selectors':{'instance_ids':[target],'prefixes':[],'types':[]},'stages':['direction'],'slot':'finish',
        'parameters':{'amount':.15,'behavior':'normal'},'dependencies':['geometry','materials'],'benchmark':None}]}
    capabilities.bind_policy(root,value,expected_revision=c.read(root)[-1]['id'],request_id=str(uuid.uuid4()),authority=actor)
    handoff=out / 'handoff.md'; handoff.write_text('Synthetic capability result; no artistic acceptance.')
    ref=lambda p:{'path':p.relative_to(out).as_posix(),'sha256':file_hash(p)}
    def submission():
        return {'schema':'dcc.environment.submission.v1','stage_id':'direction','checkpoint':c.checkpoint_ref(workflow.resume(root)['active']),
                'deliverables':{k:'Synthetic direction' for k in ew.default_manifest()['stages'][0]['deliverables']},
                'evidence':[{'kind':'direction_record','file':ref(handoff)}],'feedback_ids':[],
                'note':'Claimed provider use alone must not satisfy policy'}
    try: ew.apply(root,'stage.submit',submission(),c.read(root)[-1]['id'],str(uuid.uuid4()),out)
    except ValueError as exc: assert 'capability' in str(exc)
    else: raise AssertionError('Required provider bypassed before execution')
    req=capabilities.requirements(root,'direction',observation)[0]
    inventory=capabilities.inventory_for_requirement(root,req)
    resolution=capabilities.resolve(root,req,inventory)
    expected='capability_fixture' if observation['scene']['render']['engine']=='BLENDER_EEVEE' else 'capability_second'
    assert resolution['state']=='RESOLVED' and resolution['selected']['provider']==expected,resolution
    import copy
    best=copy.deepcopy(req); best['rule']['mode']='best_qualified'
    assert capabilities.resolve(root,best,inventory)['state']=='TIMING_SELECTION_UNAVAILABLE'
    contract=out / 'contract.json'
    write_json(contract,{'schema':'dcc.continuity.contract.v1','spec':{'schema':'dcc.spec.v1','required':{target:{}}},
                        'allowed_new_prefixes':[],'allowed_object_prefixes':{target:sorted(OBJECT_FIELDS)}})
    operation_id=str(uuid.uuid4())
    result=capabilities.execute(root,req,resolution,req['rule']['parameters'],operation_id,
                               blender=args.blender,contract=contract,handoff=handoff,timeout=120)
    assert result['status']=='PUBLISHED' and result.get('live_state','READY')=='READY',result
    assert capabilities.execute(root,req,resolution,req['rule']['parameters'],operation_id,
                               blender=args.blender,contract=contract,handoff=handoff,timeout=120)==result
    assert len(execution._operations(root))==1
    current=workflow.resume(root)['active']; cp=c.checkpoint_ref(current)
    assert capabilities.verify_receipts(root,'direction',cp)['passed']
    try: capabilities.verify_receipts(root,'direction',c.checkpoint_ref(active))
    except ValueError: pass
    else: raise AssertionError('Stale checkpoint receipt accepted')
    submitted=ew.apply(root,'stage.submit',submission(),c.read(root)[-1]['id'],str(uuid.uuid4()),out)
    review={'submission_id':submitted['revision'],'review':{'reviewer':actor,'verdict':'pass','finding':'Technical fixture verified'}}
    approval=None
    if mode=='approval_gated':
        try: ew.apply(root,'stage.complete',review,submitted['revision'],str(uuid.uuid4()),out)
        except ValueError as exc: assert 'Artist review' in str(exc)
        else: raise AssertionError('Agent approved a gated capability stage')
        review['review']['reviewer']={**actor,'role':'artist','reference':'SYNTHETIC OWNER FIXTURE, not human approval'}
        approval=owner.confirm('stage.complete',review,SyntheticOwnerConsole())
    # An owner approval cannot override stale provider bytes.
    from dcc_harness import recipes
    _,profile=recipes.current_profile(root,resolution['selected']['profile_digest'])
    entry=Path(profile['providers'][0]['entry']); original=entry.read_bytes()
    entry.write_bytes(original+b'\n# unchanged-version source drift\n')
    try:
        try: ew.apply(root,'stage.complete',review,submitted['revision'],str(uuid.uuid4()),out,approval=approval)
        except ValueError as exc: assert 'capability' in str(exc)
        else: raise AssertionError('Stale provider bypassed completion')
    finally: entry.write_bytes(original)
    ew.apply(root,'stage.complete',review,submitted['revision'],str(uuid.uuid4()),out,approval=approval)
    return {'backend':backend,'mode':mode,'provider':expected,'operation_id':operation_id,'passed':True,
            'replay_safe':True,'required_failure_blocks':True,'owner_gate_preserved':True}


def routing(args):
    import sys
    from types import SimpleNamespace
    sys.path.insert(0,str(Path(args.runtime).resolve()))
    from qualify_capabilities import onboarding
    from dcc_harness import workflow,observe,bootstrap,execution,live
    from dcc_harness.evidence import write_json,read_json
    from dcc_harness.native import run_worker
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    central=Path(args.qualification_root).resolve() if getattr(args,'qualification_root',None) else out / 'onboarding'
    if not getattr(args,'qualification_root',None): onboarding(SimpleNamespace(**{**vars(args),'out':str(central)}))
    source=central / 'project/capabilities/qualifications/capability_fixture.python_function/background/before.blend'
    results=[]
    for backend in ('background','live'):
        for mode in ('autonomous','approval_gated'):
            folder=out / (backend+'-'+mode); engine='BLENDER_EEVEE' if mode=='autonomous' else 'CYCLES'
            if backend=='live':
                with owned_bridge(args,folder,engine) as binding:
                    brief=folder / 'brief.md'; brief.write_text('Synthetic live capability policy proof')
                    attached=live.attach(folder / 'attached',binding,scene='Scene',brief_file=brief,mode=mode,blender=args.blender,seconds=900)
                    results.append(project_case(args,folder,Path(attached['project']),central,mode,backend))
            else:
                folder.mkdir()
                worker=folder / 'source.py'
                worker.write_text('import bpy,json,sys\nfrom pathlib import Path\n_,p=sys.argv[sys.argv.index("--")+1:]\nr=json.loads(Path(p).read_text())\nbpy.ops.wm.open_mainfile(filepath=r["source"])\nbpy.context.scene.render.engine=r["engine"]\nbpy.ops.wm.save_as_mainfile(filepath=r["output"])\n')
                run_worker(args.blender,folder,worker,'source',{'source':str(source),'engine':engine,'output':str(folder / 'source.blend')})
                observed=observe.observe_file(folder / 'source.blend',folder / 'observe',args.blender)
                root=folder / 'project'; workflow.start(root,folder / 'source.blend',observed['observation'],'Synthetic capability proof',{})
                bootstrap.bind_rules(root,folder,'none',str(uuid.uuid4())); execution.create(root,mode,seconds=900)
                results.append(project_case(args,folder,root,central,mode,backend))
            print(backend,mode,'PASS',flush=True)
    write_json(out / 'VERIFICATION.json',{'passed':True,'case':'routing','results':results})
