"""Owned v2 async material onboarding, live/background publication and receipt reuse."""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--source',required=True,help='Owned baseline before.blend from shader async qualifier')
    parser.add_argument('--runtime',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--backend',choices=['background','live'],action='append')
    parser.add_argument('--mode',choices=['autonomous','approval_gated'],action='append')
    parser.add_argument('--effect-kind',choices=['material','shader_nodes'],default='material')
    parser.add_argument('--legacy',action='store_true',help='Run existing v1 modifier fixture through the same public paths')
    args=parser.parse_args()
    args.source=str(Path(args.source).resolve(strict=True))
    runtime=Path(args.runtime).resolve();sys.path.insert(0,str(runtime))
    from qualify_shader_async import recipe
    from qualify_capability_mcp import project_case
    from qualify_capability_routing import owned_bridge
    from dcc_harness.evidence import write_json
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    fixtures=Path(__file__).resolve().parents[1]/'tests/fixtures/addons'
    provider_id='capability_fixture' if args.legacy else 'shader_async_fixture'
    central=out/'central';shutil.copytree(fixtures/'legacy'/provider_id,central/'providers'/provider_id)
    def factory(provider):
        if args.legacy:
            from qualify_capabilities import fixture_recipe,fixture_case
            return fixture_recipe(provider,'python_function','capability_fixture.mark',
                [fixture_case('background'),fixture_case('live','live')],name='legacy.public.function')
        value,parameters=recipe(provider,args.effect_kind,True,'copy' if args.effect_kind=='shader_nodes' else 'normal')
        # Managed bridge round trips and full-scene verification share this budget.
        # Deadline refusal is exercised separately by the native negative cases.
        value['invocation']['timeout']=30
        value['cases']=[{'name':context,'parameters':dict(parameters),'context':context,'expect':'pass'}
                        for context in ('background','live')]
        return value
    config=SimpleNamespace(**vars(args),provider_id=provider_id,
        provider_preferences={} if args.legacy else {'shader_async_fixture':{'quality':3}},recipe_factory=factory,
        adapter=str(fixtures/('capability_adapter.py' if args.legacy else 'shader_async_adapter.py')))
    results=[]
    for backend in args.backend or ('background','live'):
        for mode in args.mode or ('autonomous','approval_gated'):
            folder=out/(backend+'-'+mode)
            print('RUN managed',backend,mode,flush=True)
            if backend=='live':
                with owned_bridge(config,folder,'BLENDER_EEVEE',Path(args.source)) as binding:
                    result=asyncio.run(project_case(config,folder,central,Path(args.source),backend,mode,binding))
            else:
                folder.mkdir()
                result=asyncio.run(project_case(config,folder,central,Path(args.source),backend,mode))
            results.append(result)
            print('PASS managed',backend,mode,flush=True)
    write_json(out/'VERIFICATION.json',{'passed':True,'partial':bool(args.backend or args.mode),
        'recipe_schema':'dcc.capability.recipe.v1' if args.legacy else 'dcc.capability.recipe.v2',
        'effect':'modifier' if args.legacy else args.effect_kind,
        'completion':'synchronous' if args.legacy else 'asynchronous','results':results})
    print(json.dumps({'passed':True,'cases':len(results),'report':str(out/'VERIFICATION.json')}))


if __name__=='__main__':main()
