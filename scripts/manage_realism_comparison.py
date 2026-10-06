"""Coordinator file operations for the frozen four-run realism study.

Explicit commands only; does not launch agents or retry a native operation.
"""
import argparse,copy,json,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.project import Project
root=repo/'runs/realism-heldout-2026-10-05'

def verify(packet):
    m=read_json(packet/'manifest.json')['files']
    for name,sha in m.items():
        if file_hash(packet/name)!=sha:raise ValueError('Changed frozen input '+name)
    return len(m)

def identity(run_id):
    return next(x for x in read_json(root/'private/manifest.json')['runs'] if x['id']==run_id)

def dispatch(run_id,stage,agent):
    packet=root/('trials' if stage=='pre' else 'revisions')/run_id
    write_json(root/'private'/f'{run_id}-{stage}-dispatch.json',{'agent':agent,'utc':datetime.now(timezone.utc).isoformat(),'packet':str(packet),'verified_files':verify(packet),'stage':stage,'model_settings':'Inherited without override; tokens/billing unavailable'})

def accept(run_id,stage):
    packet=root/('trials' if stage=='pre' else 'revisions')/run_id;verify(packet)
    source=packet/'output'/(stage+'.blend');handoff=packet/'output/CONTINUE.md'
    if not source.is_file() or not handoff.is_file():raise ValueError('Incomplete author output; retain and record, do not replace')
    dest=root/'private/completed'/run_id/stage;dest.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(source,dest/'scene.blend');shutil.copyfile(handoff,dest/'CONTINUE.md')
    # Freeze all author artifact hashes; producer files remain untouched.
    hashes={p.relative_to(packet/'output').as_posix():file_hash(p) for p in (packet/'output').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    journals=[]
    for path in (packet/'output').rglob('project.json'):
        if not (path.parent/'operations.jsonl').exists():continue
        j=Project(path.parent);events=j.events()
        for event in events:
            key='script' if event['event']=='begin' else 'evidence'
            if file_hash(event[key])!=event['sha256']:raise ValueError('Journal artifact changed '+event[key])
        journals.append({'path':str(path.parent),'pending':j.status()['pending'],'events':len(events)})
    write_json(dest/'acceptance.json',{'utc':datetime.now(timezone.utc).isoformat(),'source':str(source),'source_sha256':file_hash(source),'checkpoint_sha256':file_hash(dest/'scene.blend'),'files':hashes,'journals':journals})
    print('ACCEPTED',run_id,stage,file_hash(source))

def evaluate(run_id,stage):
    dest=root/'private/completed'/run_id/stage
    before=root/'starter-observation.json' if stage=='pre' else root/'private/completed'/run_id/'pre/evaluation/observation.json'
    contract=root/'contract-pre.json' if stage=='pre' else root/'private/contract-post.json'
    out=dest/'evaluation';command=['C:/Program Files/Blender Foundation/Blender 5.1/blender.exe','--background','--factory-startup','--python-exit-code','1','--python',str(root/'evaluation-runtime/evaluate_realism_checkpoint.py'),'--','--source',str(dest/'scene.blend'),'--before',str(before),'--contract',str(contract),'--repo',str(root/'evaluation-runtime'),'--out',str(out)]
    for name,sha in read_json(root/'evaluation-runtime/manifest.json')['files'].items():
        if file_hash(root/'evaluation-runtime'/name)!=sha:raise ValueError('Frozen evaluator changed')
    start=time.perf_counter()
    with (dest/'evaluation.log').open('x',encoding='utf-8') as f:proc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    write_json(dest/'process.json',{'command':command,'exit_code':proc.returncode,'seconds':time.perf_counter()-start})
    if proc.returncode:raise RuntimeError('Inspection failed; retain and diagnose outcome before rerun')
    report=read_json(out/'report.json');cumulative=copy.deepcopy(read_json(root/'contract-pre.json'))
    if stage=='post':cumulative['spec']=read_json(root/'private/contract-post.json')['spec']
    check=evaluate_stage(read_json(root/'starter-observation.json'),read_json(out/'observation.json'),cumulative)
    write_json(dest/'cumulative-check.json',check)
    print('EVALUATED',run_id,stage,'sequential',report['passed'],'cumulative',check['passed'])

def revision(run_id):
    record=identity(run_id);source=root/'trials'/run_id;verify(source)
    saved=root/'private/completed'/run_id/'pre';acceptance=read_json(saved/'acceptance.json')
    if any(j['pending'] for j in acceptance['journals']):raise ValueError('Unresolved native operation requires inspection before continuation')
    if file_hash(saved/'scene.blend')!=acceptance['checkpoint_sha256']:raise ValueError('Accepted checkpoint changed')
    packet=root/'revisions'/run_id;packet.mkdir(parents=True,exist_ok=False);(packet/'output').mkdir()
    shutil.copyfile(saved/'scene.blend',packet/'input.blend');shutil.copyfile(saved/'CONTINUE.md',packet/'PRIOR_HANDOFF.md')
    shutil.copyfile(saved/'evaluation/observation.json',packet/'source-observation.json');shutil.copyfile(saved/'evaluation/report.json',packet/'prior-evaluation.json')
    shutil.copyfile(source/'BRIEF.md',packet/'BRIEF.md');shutil.copytree(source/'assets',packet/'assets');shutil.copytree(source/'references',packet/'references')
    shutil.copyfile(root/'private/REVISION.md',packet/'REVISION.md');shutil.copyfile(root/'private/contract-post.json',packet/'contract.json')
    extra='Use your normal Blender problem-solving workflow. No project process skills or harness runtime are included.'
    if record['method']=='harness':
        shutil.copytree(source/'runtime',packet/'runtime');shutil.copytree(source/'skills',packet/'skills');shutil.copyfile(source/'METHOD.md',packet/'METHOD.md')
        extra='Read METHOD.md and the included process skills. Use the runtime to check the actual parent and scoped revision.'
    (packet/'PROMPT.md').write_text('''You are a fresh independent Blender revision worker. Read REVISION.md, the common BRIEF.md, contract.json, source-observation.json, prior-evaluation.json and PRIOR_HANDOFF.md. '''+extra+'''

Only this packet is input. Prior handoff paths are historical; open only input.blend. Do not follow links to former runs/scripts. You own only output/ here. You are not alone in the repository: preserve others' work. No parent/sibling reads, outside research, global skill bodies, prior conversation, other agents, or evaluator code. No spawning or messaging agents. Record ambient metadata exposure honestly.

The coordinator grants exclusive ownership of an owned background Blender writer. Use C:/Program Files/Blender Foundation/Blender 5.1/blender.exe with --background --factory-startup --python-exit-code 1 and a script under output/. Confirm background mode and file ownership; do not touch the live editor/MCP. Keep scripts and failures immutable. Save new native versions rather than overwriting attempts. Inspect your own renders and packed-file reopen. Do not retry uncertain writes without inspection.

Finish within 20 minutes and four preview images. Save output/post.blend, output/CONTINUE.md, scripts, checks, actual capture/repair counts and unresolved issues. The former worker's transcript and author scripts are absent deliberately. No artist acceptance claim. Inherited out-of-scope problems must remain visible in the report, not silently repaired.
''',encoding='utf-8')
    write_json(packet/'manifest.json',{'files':{p.relative_to(packet).as_posix():file_hash(p) for p in packet.rglob('*') if p.is_file()}})
    print('REVISION_PACKET',packet)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['dispatch','accept','evaluate','revision','verify']);p.add_argument('run_id');p.add_argument('--stage',choices=['pre','post'],default='pre');p.add_argument('--agent');a=p.parse_args()
    identity(a.run_id)
    if a.action=='dispatch':dispatch(a.run_id,a.stage,a.agent)
    elif a.action=='accept':accept(a.run_id,a.stage)
    elif a.action=='evaluate':evaluate(a.run_id,a.stage)
    elif a.action=='revision':revision(a.run_id)
    elif a.action=='verify':print('VERIFIED',verify(root/('trials' if a.stage=='pre' else 'revisions')/a.run_id))
