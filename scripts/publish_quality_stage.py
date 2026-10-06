"""Admit a reviewed worker output against the actual current master parent."""
import argparse
from pathlib import Path
import sys
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.continuity import Continuity
from dcc_harness.continuity_checks import evaluate_stage
from dcc_harness.evidence import read_json,write_json,file_hash
from dcc_harness.project import Project
from dcc_harness.quality import select
p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage');p.add_argument('--store',required=True);p.add_argument('--step',required=True);p.add_argument('--handoff')
a=p.parse_args();stage=Path(a.stage).resolve();store=Continuity(a.store)
review=read_json(stage/'review.json');selection=select(stage/'round.json',review);name=selection['selected']
for item,sha in read_json(stage/'packet-manifest.json')['files'].items():
    if file_hash(stage/item)!=sha: raise ValueError('Packet changed: '+item)
worker=Project(stage/'worker/journal')
if worker.status()['pending']: raise ValueError('Author operation remains unresolved')
for event in worker.events():
    key='script' if event['event']=='begin' else 'evidence'
    if file_hash(event[key])!=event['sha256']: raise ValueError('Worker journal artifact changed')
scope=read_json(stage/'scope-checks.json')[name];obs=read_json(stage/name/'observation.json')
if not scope['passed'] or scope['revision']!=obs['revision'] or scope['checkpoint_sha256']!=file_hash(stage/name/'scene.blend'):
    raise ValueError('Missing, stale or failed independent scope check')
state=store.verify();before=read_json(state['active']['observation'])
check=evaluate_stage(before,obs,read_json(stage/'design.json')['contract'])
if not check['passed']: raise ValueError('Selected file differs from the actual current parent')
write_json(stage/'selection.json',selection);write_json(stage/'publication-check.json',check)
handoff=Path(a.handoff).resolve() if a.handoff else stage/'worker/CONTINUE.md'
store.publish(a.step,state['active']['id'],stage/name/'scene.blend',stage/name/'observation.json',handoff,
 {a.step:{'selected':name,'selection_sha256':file_hash(stage/'selection.json'),'scope_check_sha256':file_hash(stage/'scope-checks.json'),
          'review_independence':selection['review_independence'],'artist_acceptance':'not_requested'}},stage/'publication-check.json')
state=store.verify();write_json(stage/'publication.json',{'active':state['active'],'pending':state['pending']})
print('PUBLISHED',name,state['active']['id'])
