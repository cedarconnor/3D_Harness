"""Owned native shader/async proof, with retained evidence and explicit coverage.

Run from a source checkout with Blender 5.1+: python scripts/qualify_shader_async.py
--blender PATH --out FRESH_DIRECTORY. Every Blender process uses factory startup,
offline mode and its own configuration. Existing artist processes are untouched.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys


def runtime_stamp(runtime):
    """Retain exact package and qualifier source bytes around every native worker."""
    runtime=Path(runtime)
    paths=sorted(p for p in (runtime/'dcc_harness').rglob('*') if p.suffix in ('.py','.json') and p.is_file())
    files={str(p.relative_to(runtime)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for name in ('qualify_shader_async.py','_shader_async_qualify.py'):
        p=Path(__file__).with_name(name)
        files['qualifier/'+name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return {'sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'files':files}


def recipe(provider, kind, asynchronous, behavior):
    invocation={'kind':'python_function','entry':'shader_async_fixture.mark',
                'completion':'synchronous','cancellation':'between_calls'}
    if asynchronous:
        invocation.update(entry='shader_async_fixture.submit',completion='asynchronous',cancellation='cooperative',
            poll='shader_async_fixture.poll',cancel='shader_async_fixture.cancel',collect='shader_async_fixture.collect',
            poll_interval=.05,timeout=(30 if behavior in ('normal','copy','shared_allowed') else .2 if behavior=='hang' else 5),cancel_grace=5)
    effect={'kind':kind,'material_id':'{effect_name}' if kind=='material' else 'fixture.material','slot':0}
    if kind=='shader_nodes':effect['nodes']=['{effect_name}']
    if behavior=='copy':effect['material_id']='{effect_name}'
    parameters={'amount':.25,'behavior':behavior,'delay':1 if behavior in ('cancel','hang','cancel_refuses') else .2}
    schema={'type':'object','properties':{'amount':{'type':'number','minimum':0,'maximum':1},
        'behavior':{'type':'string','enum':['normal','noop','hang','cancel','fail','cancel_refuses','shared_group','mutate_fail','copy','shared_allowed']},
        'delay':{'type':'number','minimum':.05,'maximum':10}},'required':['amount','behavior','delay'],'additionalProperties':False}
    value={'schema':'dcc.capability.recipe.v2','id':'fixture.'+kind+('.async' if asynchronous else '.sync')+'.'+behavior,
        'version':1,'capabilities':['surface.shader_fixture'],
        'provider':{'id':provider['id'],'source_digest':provider['source_digest']}, 'effect':effect,
        'parameters':schema,'compatibility':{'blender_min':[5,1,0],'blender_max':[6,0,0],
            'engines':['BLENDER_EEVEE'],'target_types':['MESH'],'contexts':['background','live']},
        'coverage':{'reads':['geometry','materials','nodes'],'writes':['materials','nodes'],
                    'dependencies':['geometry','materials','nodes']},
        'invocation':invocation,'update':{'identity':'effect_key','shared_materials':'single_user_copy'},
        'validators':['inspect_output','verify_saved'],
        'cases':[{'name':'owned_fixture','parameters':parameters,'context':'background','expect':'pass'}]}
    if behavior=='shared_allowed':value['update']['shared_materials']='all_users'
    if behavior not in ('normal','copy','shared_allowed'):
        case=value['cases'][0];case['expect']='fail'
        case['failure_contains']={'noop':'owned native nodes','shared_group':'protected scene state',
            'cancel':'CANCELLED','hang':'CANCELLED','fail':'Asynchronous recipe FAILED','cancel_refuses':'NEEDS_RECONCILIATION',
            'mutate_fail':'Fixture mutation then failure'}[behavior]
    return value,parameters


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--runtime',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--background-only',action='store_true',help='Explicit partial qualification without owned GUI cases')
    parser.add_argument('--case',action='append',help='Run only named cases; output is explicitly partial')
    args=parser.parse_args()
    runtime=Path(args.runtime).resolve();sys.path.insert(0,str(runtime))
    from dcc_harness import environments,recipes
    from dcc_harness.native import run_worker
    from dcc_harness.evidence import digest,write_json
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    fixtures=Path(__file__).resolve().parents[1]/'tests/fixtures/addons'
    shutil.copytree(fixtures/'legacy/shader_async_fixture',out/'providers/shader_async_fixture')
    inventory=environments.inventory(blender=args.blender,
        roots=[{'path':str(out/'providers'),'namespace':''}],out=out/'inventory')
    provider=next(p for p in inventory['providers'] if p['id']=='shader_async_fixture')
    profile=environments.create_profile(out/'project',inventory,['shader_async_fixture'],{'shader_async_fixture':{'quality':3}})
    worker=Path(__file__).with_name('_shader_async_qualify.py').resolve()
    adapter=fixtures/'shader_async_adapter.py'
    report={'passed':False,'partial':bool(args.background_only or args.case),'cases':[],
            'profile':profile,'runtime':str(runtime),'blender':str(Path(args.blender).resolve()),
            'limits':['Synthetic owned provider only; no commercial add-on qualification.',
                      'Native lifecycle tests exercise recipe execution; managed checkpoint publication is tested separately.',
                      'Native uncertain-stop guard retention and confirmed cleanup are exercised; process-loss replay guards require portable durable lifecycle tests.']}
    report['runtime_sources_before']=runtime_stamp(runtime)
    modes=['background'] if args.background_only else ['background','live']
    matrix=[]
    for mode in modes:
        for kind in ('material','shader_nodes'):
            for asynchronous in (False,True):matrix.append((mode,kind,asynchronous,'normal'))
        matrix.extend((mode,'shader_nodes',asynchronous,behavior) for asynchronous,behavior in
            [(True,'copy'),(False,'shared_allowed'),(False,'noop'),(False,'shared_group'),(True,'cancel'),(True,'fail'),(True,'hang'),(True,'cancel_refuses')])
    for mode,kind,asynchronous,behavior in matrix:
        name='-'.join((mode,kind,'async' if asynchronous else 'sync',behavior))
        if args.case and name not in args.case:continue
        print('RUN '+name,flush=True)
        value,parameters=recipe(provider,kind,asynchronous,behavior)
        ref=recipes.draft(out/'project',value,str(adapter),[])
        request={'runtime':str(runtime),'root':str(out/'project'),'recipe':ref,'parameters':parameters,
            'effect_id':digest({'case':name}),'engine':'BLENDER_EEVEE','behavior':behavior,
            'asynchronous':asynchronous,'expect':'success' if behavior in ('normal','copy','shared_allowed') else 'refusal'}
        folder=out/name;folder.mkdir()
        row={'name':name,'passed':False,'folder':str(folder),'runtime_stamps':{'apply':{'before':runtime_stamp(runtime)}}}
        try:
            run_worker(args.blender,folder,worker,'recipe_apply',request,profile=profile,gui=mode=='live',timeout=90)
            row['runtime_stamps']['apply']['after']=runtime_stamp(runtime)
            assert row['runtime_stamps']['apply']['before']==row['runtime_stamps']['apply']['after'],'Runtime sources changed during native apply'
            applied=json.loads((folder/'result.json').read_text())
            row.update(passed=applied['passed'],apply=applied)
            if not row['passed']:raise AssertionError(applied.get('error','Native apply failed'))
            if behavior in ('normal','copy','shared_allowed'):
                verify_folder=folder/'reopen';verify_folder.mkdir()
                verified_request={**request,'verify':True,'applied':applied,
                                  'parameters':{**parameters,'amount':.75}}
                row['runtime_stamps']['reopen']={'before':runtime_stamp(runtime)}
                run_worker(args.blender,verify_folder,worker,'recipe_verify',verified_request,profile=profile,timeout=90)
                row['runtime_stamps']['reopen']['after']=runtime_stamp(runtime)
                assert row['runtime_stamps']['reopen']['before']==row['runtime_stamps']['reopen']['after'],'Runtime sources changed during native reopen'
                verified=json.loads((verify_folder/'result.json').read_text())
                row.update(passed=verified['passed'],reopen=verified)
            assert not any(folder.rglob('userpref.blend')),'Artist preferences persisted in owned profile'
        except Exception as exc:
            row.update(passed=False,error=str(exc))
        report['cases'].append(row)
        write_json(out/('progress-%02d.json' % len(report['cases'])),report)
        print(('PASS ' if row['passed'] else 'FAIL ')+name,flush=True)
    report['runtime_sources_after']=runtime_stamp(runtime)
    report['runtime_sources_unchanged']=report['runtime_sources_before']==report['runtime_sources_after']
    report['passed']=report['runtime_sources_unchanged'] and bool(report['cases']) and all(case['passed'] for case in report['cases'])
    report['full_matrix_complete']=not report['partial'] and len(report['cases'])==len(matrix)
    write_json(out/'VERIFICATION.json',report)
    print(json.dumps({'passed':report['passed'],'full_matrix_complete':report['full_matrix_complete'],
                      'cases':len(report['cases']),'report':str(out/'VERIFICATION.json')},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

