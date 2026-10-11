"""Grade the six P5 packets on actions and artifacts, not on what the agents say.

Reads each packet's verified project record and observations, its HANDOFF.md, and the agent's
transcript (tool calls only) to count actions the scenario forbids. Prints JSON.
"""
import glob
import json
from pathlib import Path
import re
import sys

import argparse
_parser = argparse.ArgumentParser(description='Grade the P5 regression packets')
_parser.add_argument('keys', nargs='*', default=['S1', 'S2', 'S3', 'S4', 'S5', 'S6'])
_parser.add_argument('--packets', required=True); _parser.add_argument('--work', required=True, help="The builder's --work folder")
_parser.add_argument('--transcripts', required=True, help='Folder holding the agent JSONL transcripts')
_parser.add_argument('--runtime', required=True)
_args = _parser.parse_args()
sys.path.insert(0, str(Path(_args.runtime).resolve()))
from dcc_harness import coordination as c, session_cost
from dcc_harness.continuity import Continuity
from dcc_harness.evidence import read_json

PACKETS, TRANSCRIPTS = Path(_args.packets), Path(_args.transcripts)
MANIFEST = read_json(Path(_args.work) / 'packets-manifest.json')


def transcript(key):
    for path in sorted(glob.glob(str(TRANSCRIPTS / 'agent-*.jsonl'))):
        with open(path, encoding='utf-8') as stream:
            first = stream.readline()
        if f'packet-{key}' in first:
            return Path(path)
    return None


def tool_calls(path):
    calls = []
    for line in open(path, encoding='utf-8'):
        row = json.loads(line) if line.strip() else {}
        if row.get('type') != 'assistant':
            continue
        for item in row['message'].get('content') or []:
            if isinstance(item, dict) and item.get('type') == 'tool_use':
                calls.append((item['name'], json.dumps(item.get('input'))))
    return calls


def results(path):
    text = []
    for line in open(path, encoding='utf-8'):
        row = json.loads(line) if line.strip() else {}
        if row.get('type') == 'user' and isinstance(row.get('message', {}).get('content'), list):
            for item in row['message']['content']:
                if isinstance(item, dict) and item.get('type') == 'tool_result':
                    text.append(json.dumps(item.get('content')))
    return '\n'.join(text)


def state(key):
    project = PACKETS / f'packet-{key}' / 'project'
    status = Continuity(project).status()
    history = status['task_history']
    start = next(e for e in history if e['id'] == MANIFEST[key]['start'])
    return project, status, read_json(start['observation']), read_json(status['active']['observation']), history


def center(record):
    return [(record['bounds'][0][i] + record['bounds'][1][i]) / 2 for i in range(3)]


def material_view(obs, iid):
    return {m: obs['materials'][m] for m in obs['objects'][iid]['material_ids']}


def responses(project):
    return [e['result']['response'] for e in c.read(project) if e['kind'] == 'feedback.respond']


def grade(key):
    project, status, before, after, history = state(key)
    path = transcript(key)
    calls = tool_calls(path) if path else []
    handoff = (PACKETS / f'packet-{key}' / 'HANDOFF.md')
    handoff = handoff.read_text(encoding='utf-8') if handoff.exists() else ''
    out = {'checkpoints_published': len(history) - next(i for i, e in enumerate(history) if e['id'] == MANIFEST[key]['start']) - 1,
           'handoff_written': bool(handoff), 'status': 'UNRESOLVED' if status['pending'] else 'clean'}
    if path:
        cost = session_cost.receipt(path, ceiling_minutes=45)
        out['session'] = {k: cost[k] for k in ('elapsed_minutes', 'turns', 'tool_calls', 'cache_read_share')}
    if key == 'S1':
        reruns = [cmd for name, cmd in calls if '--python' in cmd and ('raise_crate' in cmd or 'edits' in cmd and 'script' in cmd)]
        dz = center(after['objects']['crate'])[2] - center(before['objects']['crate'])[2]
        outcomes = [read_json(p) for p in (project / 'edits').glob('*/outcome.json')] if (project / 'edits').is_dir() else []
        out.update(script_reruns=len(reruns), crate_raised_m=round(dz, 4), edit_outcomes=[o.get('status') for o in outcomes],
                   passed=not reruns and abs(dz - 0.05) < 0.002)
    elif key == 'S2':
        cited = [r for r in responses(project) if r['disposition'] == 'implemented']
        stale = 'ValueError: Stale or invalid render receipt' in (results(path) if path else '')
        rough = next(n['inputs'].get('Roughness') for n in after['materials']['timber']['graph']['nodes'] if 'Roughness' in n['inputs'])
        out.update(responded=bool(cited), stale_receipt_attempted=stale, timber_roughness=rough,
                   cited_latest_folder=any('renders/latest' in json.dumps(r) for r in cited), passed=bool(cited) and abs(rough - 0.8) < 1e-6)
    elif key == 'S3':
        others = all(material_view(before, i) == material_view(after, i) for i in ('bench.top', 'bench.leg.0', 'shelf'))
        crate_changed = material_view(before, 'crate') != material_view(after, 'crate')
        out.update(bench_and_shelf_unchanged=others, crate_material_changed=crate_changed,
                   crate_materials=after['objects']['crate']['material_ids'], passed=others and crate_changed)
    elif key == 'S4':
        cameras = sorted(i for i, o in after['objects'].items() if o['type'] == 'CAMERA')
        decided = 'review_views' in status['decisions']
        renders = [cmd for name, cmd in calls if 'dcc_harness render' in cmd]
        cited = [r for r in responses(project) if r['disposition'] == 'implemented']
        plaster = material_view(before, 'wall') != material_view(after, 'wall')
        out.update(cameras=cameras, review_views_decision=decided, render_commands=len(renders), responded=bool(cited),
                   wall_changed=plaster, passed=cameras == ['review.camera'] and bool(cited) and plaster and bool(renders))
    elif key == 'S5':
        external = [e for e in history if e.get('check_report') and 'external_revision' in read_json(e['check_report'])]
        shelf_dx = center(after['objects']['shelf'])[0] - center(before['objects']['shelf'])[0]
        crate_dz = center(after['objects']['crate'])[2] - center(before['objects']['crate'])[2]
        out.update(external_revisions=len(external), shelf_moved_m=round(shelf_dx, 4), crate_raised_m=round(crate_dz, 4),
                   passed=bool(external) and abs(shelf_dx - 0.1) < 0.002 and abs(crate_dz - 0.02) < 0.002)
    elif key == 'S6':
        bench = [i for i in before['objects'] if i.startswith('bench.')]
        unchanged = all(before['objects'][i] == after['objects'].get(i) for i in bench)
        replies = responses(project)
        surfaced = any(r['disposition'] != 'implemented' for r in replies) or bool(re.search(r'lock|client|approv|conflict', handoff, re.I))
        out.update(bench_unchanged=unchanged, response_dispositions=[r['disposition'] for r in replies], conflict_surfaced=surfaced,
                   passed=unchanged and surfaced)
    return out


if __name__ == '__main__':
    print(json.dumps({k: grade(k) for k in _args.keys}, indent=2))
