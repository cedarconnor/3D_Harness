"""Independently reopen a sealed worker task's immutable output candidates.

No authoring and no retries. Native evaluator processes never save scene files.
Task-specific scope constraints remain separate from the generic quality audit.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('root'); p.add_argument('--package-root',required=True); p.add_argument('--blender',required=True)
a=p.parse_args(); sys.path.insert(0,a.package_root)
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.project import Project

root=Path(a.root).resolve(); package=Path(a.package_root).resolve()
manifest=read_json(root/'packet-manifest.json')['files']
def verify():
    for name,sha in manifest.items():
        if file_hash(root/name)!=sha: raise ValueError('Frozen input changed: '+name)
verify()
scope=read_json(root/'scope.json'); design=read_json(root/'design.json')
before=read_json(root/'source-observation.json')
out=root/'independent'; out.mkdir(exist_ok=False)
assembler=out/'assemble_quality_round.py'
shutil.copyfile(Path(__file__).resolve().parent/'assemble_quality_round.py',assembler)
write_json(out/'provenance.json',{'package_root':str(package),'files':{p.name:file_hash(p) for p in sorted((package/'dcc_harness').glob('*.py'))},
 'frozen_evaluator_sha256':file_hash(root/'runtime/scripts/evaluate_quality_candidate.py'),
 'independent_assembler_sha256':file_hash(assembler),'packet_verified':True})
journal=Project(out); journal.init('Independent saved-file evaluation of '+str(root))
results={}
for name in ['unchanged',*scope['candidate_ids']]:
    script=root/'runtime/scripts/evaluate_quality_candidate.py'; op=journal.begin('evaluate-'+name,script)
    command=[a.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(script),'--',
             '--repo',str(package),'--round',str(root),'--candidate',name]
    with (out/(name+'.log')).open('x',encoding='utf-8') as stream:
        process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    write_json(out/(name+'-process.json'),{'command':command,'exit_code':process.returncode,'operation':op})
    if process.returncode: raise RuntimeError(f'{name} evaluation failed; inspect pending operation, do not replay')
    journal.finish(op,root/name/'renders.json')
    obs=read_json(root/name/'observation.json'); added=set(obs['objects'])-set(before['objects'])
    meshes={i:obs['objects'][i] for i in added if obs['objects'][i]['type']=='MESH'}
    failures=[]; bounds=scope['bounds']
    if name!='unchanged':
        if not scope['minimum_new_meshes']<=len(meshes)<=scope['maximum_new_meshes']: failures.append('Added mesh count outside scope')
        if sum(o.get('triangles',0) for o in meshes.values())>scope['maximum_new_triangles']: failures.append('New triangle budget exceeded')
        for iid,o in meshes.items():
            b=o['bounds']
            if any(b[0][k]<bounds[0][k]-1e-5 or b[1][k]>bounds[1][k]+1e-5 for k in range(3)): failures.append('Outside owned volume: '+iid)
        if scope['reuse_materials_only'] and set(obs['materials'])!=set(before['materials']): failures.append('Material library changed')
        if 'allowed_new_material_ids' in scope:
            extra=set(obs['materials'])-set(before['materials'])
            if extra-set(scope['allowed_new_material_ids']) or set(before['materials'])-set(obs['materials']): failures.append('Material library outside scoped additions')
        for iid,rule in scope.get('edited_objects',{}).items():
            record=obs['objects'].get(iid,{})
            if record.get('type')!='MESH':
                failures.append('Edited target missing or not a mesh: '+iid); continue
            b=record['bounds']; limit=rule['bounds_limits']
            if any(b[0][k]<limit[0][k]-1e-5 or b[1][k]>limit[1][k]+1e-5 for k in range(3)): failures.append('Edited target outside footprint: '+iid)
            if not 1<=record.get('triangles',0)<=rule['maximum_triangles']: failures.append('Edited target triangle budget: '+iid)
            if set(record['material_ids'])-set(rule['allowed_material_ids']): failures.append('Edited target material outside scope: '+iid)
            if name=='craft_only' and record['material_ids']!=before['objects'][iid]['material_ids']: failures.append('Geometry-only candidate changed material bindings: '+iid)
            if name=='readable_metal' and 'tool.steel' not in record['material_ids']: failures.append('Metal candidate lacks shared tool steel: '+iid)
    results[name]={'passed':not failures,'failures':failures,'new_meshes':len(meshes),'new_triangles':sum(o.get('triangles',0) for o in meshes.values()),
                   'revision':obs['revision'],'checkpoint_sha256':obs['checkpoint_sha256']}
    print('Independently evaluated',name,results[name]['passed'],flush=True)
verify()
write_json(root/'scope-checks.json',results)
subprocess.run([sys.executable,str(assembler),str(root),'unchanged',*scope['candidate_ids'],'--package-root',str(package)],check=True)
write_json(out/'complete.json',{'packet_verified':True,'pending':journal.status()['pending'],'scope_checks':results})
