"""Execute one prepared stage with frozen helper/script copies and a journal.

This bounded fixture runner is not an agent scheduler. An interrupted or failed
native call remains pending; inspect the owned artifacts before reconciliation.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(repo))
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.project import Project

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('root'); p.add_argument('--builder',required=True); p.add_argument('--blender',required=True)
p.add_argument('--candidates',nargs='+',required=True)
a=p.parse_args(); root=Path(a.root).resolve()
runtime=root/'runtime'; runtime.mkdir(exist_ok=False); (runtime/'scripts').mkdir()
shutil.copytree(repo/'dcc_harness',runtime/'dcc_harness',ignore=shutil.ignore_patterns('__pycache__'))
builder=Path(a.builder).resolve()
for script in (builder,repo/'scripts/evaluate_quality_candidate.py',repo/'scripts/assemble_quality_round.py'):
    shutil.copyfile(script,runtime/'scripts'/script.name)
write_json(root/'runtime.json',{'files':{p.relative_to(runtime).as_posix():file_hash(p) for p in runtime.rglob('*.py')}})
project=Project(root); project.init(read_json(root/'design.json')['brief'])
steps=[('build',runtime/'scripts'/builder.name,[],root/'build.json')]
steps += [('review-'+c,runtime/'scripts/evaluate_quality_candidate.py',['--candidate',c],root/c/'renders.json') for c in a.candidates]
receipts=[]
for label,script,extra,evidence in steps:
    op=project.begin(label,script)
    command=[a.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(script),'--',
             '--repo',str(runtime),'--round',str(root),*extra]
    with (root/(label+'.log')).open('x',encoding='utf-8') as stream:
        process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    receipt={'command':command,'exit_code':process.returncode,'operation':op,'script_sha256':file_hash(script),'evidence':str(evidence)}
    write_json(root/(label+'-process.json'),receipt)
    if process.returncode: raise RuntimeError(f'{label} failed; inspect pending {op}; do not replay')
    project.finish(op,evidence); receipts.append(receipt); print('Finished',label,flush=True)
subprocess.run([sys.executable,str(runtime/'scripts/assemble_quality_round.py'),str(root),*a.candidates],check=True)
write_json(root/'processes.json',{'calls':receipts,'pending':project.status()['pending']})
