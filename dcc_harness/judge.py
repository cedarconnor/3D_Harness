"""Target-led judge loop: a small append-only record, with no scheduler and no agent runtime.

A loop fixes its target before anything is built. Each round binds a saved file to its code
checks and images; a round whose `audit` has an error or whose `spec-compare` fails is recorded
as gated and never reaches the judge. A judged round stores a rubric score and named gaps. The
record then says what happens next: continue, change approach, or stop. It launches nothing: the
calling agent builds, hands the printed packet to a fresh-context judge, and records the verdict.

A judge score is an agent's opinion. It is recorded as that and never stands for owner acceptance.
"""
from __future__ import annotations

from pathlib import Path
import re

from .continuity import _plain
from .evidence import digest, file_hash, read_json, write_json
from .project import now

RUBRIC = {'composition': 3, 'lighting': 3, 'materials': 3, 'detail': 1}
RUBRIC_TEXT = {
    'composition': '0 unreadable or wrong subject; 1 subject present but proportions or placement are off; 2 reads correctly with minor issues; 3 matches the target',
    'lighting': '0 flat or wrong; 1 direction or mood is off; 2 right mood with minor issues; 3 matches the target',
    'materials': '0 placeholder or wrong; 1 plausible but uniform or the wrong scale; 2 right with minor issues; 3 matches the target',
    'detail': '0 missing the small things the target names; 1 present'}
CAP = 5
FULL = sum(RUBRIC.values())
SLUG = re.compile(r'[a-z0-9][a-z0-9-]{0,47}')
ATTRIBUTION = 'A judge score is an agent\'s opinion. It is not owner acceptance and cannot stand in for it.'
NEXT = {
    'build': 'Build the first candidate, run audit, review-sheet and render (and spec-compare if the target has a spec), then judge-round.',
    'fix_gates': 'The last round failed its code checks and was not judged. Repair those findings, then judge-round again.',
    'judge': 'Give the packet to a fresh-context judge and record its answer with judge-verdict.',
    'continue': 'Address the named gaps, largest first, then judge-round.',
    'change_approach': 'Progress has stalled. The next round must take a materially different approach and declare changed_approach with what changed.',
    'stop_ask': 'Stop. A changed approach also failed to make progress; show the owner the rounds and ask how to proceed.',
    'stop_cap': f'Stop. The loop has used all {CAP} rounds; show the owner the rounds and ask how to proceed.',
    'stop_target_met': 'Stop. The judge scored the result at or above the pass score. Present it to the owner; this is not acceptance.'}


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f'Expected fields {sorted(required)}; optional {sorted(optional)}')


def _text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{what} must be nonempty text')
    return value


def _bound(base, reference, what):
    """Resolve a {path, sha256} reference beside its document and verify the bytes."""
    _fields(reference, {'path'}, {'sha256'})
    path = _plain(Path(base) / _text(reference['path'], what + ' path'))
    if not path.is_file():
        raise ValueError(f'{what} is missing: {reference["path"]}')
    actual = file_hash(path)
    if reference.get('sha256') not in (None, actual):
        raise ValueError(f'{what} changed after it was referenced')
    return {'path': str(path.resolve()), 'sha256': actual}


def _numbered(folder):
    names = sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []
    if any(not re.fullmatch(r'\d\d\.json', n) for n in names):
        raise RuntimeError(f'Unexpected files in {folder}; inspect before continuing')
    return {int(n[:2]): read_json(folder / n) for n in names}


def _load(root):
    root = _plain(root)
    if not (root / 'loop.json').is_file():
        raise ValueError(f'No judge loop in {root}')
    loop = read_json(root / 'loop.json')
    rounds, verdicts = _numbered(root / 'rounds'), _numbered(root / 'verdicts')
    if sorted(rounds) != list(range(1, len(rounds) + 1)) or not set(verdicts) <= set(rounds):
        raise RuntimeError('The judge loop record has gaps; inspect before continuing')
    return root, loop, rounds, verdicts


def start(root, target_path):
    """Fix the target and open an empty loop in a new folder."""
    target_path = _plain(target_path)
    target = read_json(target_path)
    _fields(target, {'schema', 'brief', 'targets'}, {'references', 'spec', 'pass_score'})
    if target['schema'] != 'dcc.judge.target.v1':
        raise ValueError('A judge target needs schema dcc.judge.target.v1')
    _text(target['brief'], 'The brief')
    if not isinstance(target['targets'], list) or not target['targets']:
        raise ValueError('A judge target needs at least one visual target')
    seen = set()
    for item in target['targets']:
        _fields(item, {'id', 'intent'})
        if not isinstance(item['id'], str) or not SLUG.fullmatch(item['id']) or item['id'] in seen:
            raise ValueError('Target IDs must be unique lowercase slugs')
        seen.add(item['id'])
        _text(item['intent'], 'A target intent')
    references = []
    for item in target.get('references', []):
        _fields(item, {'id', 'file', 'role', 'intent'})
        if not isinstance(item['id'], str) or not SLUG.fullmatch(item['id']) or item['id'] in seen or item['role'] not in ('target', 'mood', 'construction', 'dimension'):
            raise ValueError('References need a unique slug and a role of target, mood, construction or dimension')
        seen.add(item['id'])
        references.append({'id': item['id'], 'role': item['role'], 'intent': _text(item['intent'], 'A reference intent'),
                           'file': _bound(target_path.parent, item['file'], 'Reference ' + item['id'])})
    spec = None
    if 'spec' in target:
        spec = _bound(target_path.parent, target['spec'], 'The blockout spec')
        from .blockout import validate_spec
        spec['digest'] = digest(validate_spec(read_json(spec['path'])))
    pass_score = target.get('pass_score', FULL - 1)
    if isinstance(pass_score, bool) or not isinstance(pass_score, int) or not 1 <= pass_score <= FULL:
        raise ValueError(f'pass_score must be a whole number from 1 to {FULL}')
    root = _plain(root)
    root.mkdir(parents=True, exist_ok=False)
    for name in ('rounds', 'verdicts', 'packets', 'notes'):
        (root / name).mkdir()
    loop = {'schema': 'dcc.judge.loop.v1', 'created': now(), 'brief': target['brief'], 'targets': target['targets'], 'references': references,
            'spec': spec, 'pass_score': pass_score, 'cap': CAP, 'rubric': RUBRIC, 'attribution': ATTRIBUTION}
    write_json(root / 'loop.json', loop)
    return status(root)


def _replay(loop, rounds, verdicts):
    """What the record says happens next, and why."""
    judged = [(n, verdicts[n]) for n in sorted(verdicts)]
    used, last = len(rounds), max(rounds) if rounds else None
    owed = forced = 0     # owed: a change of approach is required; forced: how often one has been
    start, decision, reason = 0, 'build', 'No round yet.'
    for index, (number, verdict) in enumerate(judged):
        total, gaps = verdict['total'], {g['id'] for g in verdict['gaps']}
        window = judged[start:index + 1]
        if total >= loop['pass_score']:
            decision, reason = 'stop_target_met', f'Round {number} scored {total} of {FULL}; the pass score is {loop["pass_score"]}.'
        elif owed and rounds[number]['changed_approach']:
            owed, gain = 0, total - judged[index - 1][1]['total']
            if gain < 1:
                decision, reason = 'stop_ask', f'The changed approach in round {number} gained {gain} points.'
            else:
                start, decision, reason = index - 1, 'continue', f'The changed approach in round {number} gained {gain} points.'
        else:
            # A repeated gap is a stall only when the score is not rising: a judge that lists many gaps repeats some every round.
            repeated = sorted(gaps & {g['id'] for g in window[-2][1]['gaps']}) if len(window) >= 2 and total - window[-2][1]['total'] < 1 else []
            flat = len(window) >= 3 and total - window[-3][1]['total'] < 1
            if repeated or flat:
                why = (f'gap named twice with {total - window[-2][1]["total"]} points gained: {", ".join(repeated)}' if repeated else
                       f'{total - window[-3][1]["total"]} points gained across rounds {window[-3][0]} to {number}')
                if forced:
                    decision, reason = 'stop_ask', f'Stalled again after a change of approach ({why}).'
                else:
                    owed, forced, decision, reason = 1, forced + 1, 'change_approach', f'Stalled ({why}).'
            else:
                decision, reason = 'continue', f'Round {number} scored {total} of {FULL}.'
    if decision.startswith('stop'):
        return decision, reason, False
    if last is not None and last not in verdicts:
        if rounds[last]['status'] == 'awaiting_verdict':
            return 'judge', f'Round {last} passed its code checks and has no verdict yet.', bool(owed)
        if used >= loop['cap']:
            return 'stop_cap', f'Round {last} failed its code checks and was the last allowed.', False
        return ('change_approach' if owed else 'fix_gates'), f'Round {last} failed its code checks: {"; ".join(rounds[last]["gate_failures"])}', bool(owed)
    if used >= loop['cap']:
        return 'stop_cap', f'{reason} All {loop["cap"]} rounds are used.', False
    return decision, reason, bool(owed)


def status(root):
    root, loop, rounds, verdicts = _load(root)
    decision, reason, _ = _replay(loop, rounds, verdicts)
    latest = verdicts[max(verdicts)] if verdicts else None
    return {'schema': 'dcc.judge.status.v1', 'loop': str(root), 'next': decision, 'reason': reason, 'instruction': NEXT[decision],
            'stopped': decision.startswith('stop'), 'rounds_used': len(rounds), 'cap': loop['cap'], 'pass_score': loop['pass_score'],
            'rounds': [{'round': n, 'status': 'judged' if n in verdicts else rounds[n]['status'], 'approach': rounds[n]['approach'],
                        'changed_approach': rounds[n]['changed_approach'], 'gate_failures': rounds[n]['gate_failures'],
                        'score': verdicts[n]['total'] if n in verdicts else None, 'scores': verdicts[n]['scores'] if n in verdicts else None,
                        'gaps': [g['id'] for g in verdicts[n]['gaps']] if n in verdicts else None,
                        'then': _replay(loop, {k: v for k, v in rounds.items() if k <= n}, {k: v for k, v in verdicts.items() if k <= n})[0]}
                       for n in sorted(rounds)],
            'open_gaps': latest['gaps'] if latest else [], 'brief': loop['brief'], 'targets': loop['targets'], 'attribution': ATTRIBUTION}


def _report(base, reference, what, schema, checkpoint):
    bound = _bound(base, reference, what)
    report = read_json(bound['path'])
    if report.get('schema') != schema:
        raise ValueError(f'{what} is not a {schema} document')
    held = report.get('checkpoint_sha256') or (report.get('source') or {}).get('sha256')
    if held != checkpoint['sha256']:
        raise ValueError(f'{what} was made for another file')
    return bound, report


def _images(receipt_path, receipt):
    """Verify and list the images a render or sheet receipt names."""
    folder = Path(receipt_path).parent
    listed = {'sheet': receipt['image']} if 'image' in receipt else receipt['images']
    result = {}
    for name, image in sorted(listed.items()):
        path = _plain(folder / image['path'])
        if not path.is_file() or file_hash(path) != image['sha256']:
            raise ValueError(f'Image {name} is missing or changed after its receipt')
        result[name] = {'path': str(path.resolve()), 'sha256': image['sha256']}
    return result


def add_round(root, evidence_path):
    """Bind one candidate to its checks and images. Failed checks record a gated round that is never judged."""
    root, loop, rounds, verdicts = _load(root)
    decision, _, owed = _replay(loop, rounds, verdicts)
    if decision.startswith('stop') or decision == 'judge':
        raise ValueError('The loop is stopped' if decision.startswith('stop') else 'The last round still needs its verdict')
    evidence_path = _plain(evidence_path)
    base, evidence = evidence_path.parent, read_json(evidence_path)
    required = {'schema', 'approach', 'checkpoint', 'audit', 'views', 'sheet'} | ({'spec_compare'} if loop['spec'] else set())
    _fields(evidence, required, {'changed_approach', 'project_checkpoint'})
    if evidence['schema'] != 'dcc.judge.evidence.v1':
        raise ValueError('Round evidence needs schema dcc.judge.evidence.v1')
    approach = _text(evidence['approach'], 'The approach')
    changed = evidence.get('changed_approach')
    if changed is not None:
        _text(changed, 'changed_approach')
    if owed and (changed is None or approach.strip() == rounds[max(rounds)]['approach'].strip()):
        raise ValueError('Progress stalled: this round must describe a different approach and say what changed in changed_approach')
    checkpoint = _bound(base, evidence['checkpoint'], 'The checkpoint')
    failures = []
    audit_ref, audit = _report(base, evidence['audit'], 'The audit report', 'dcc.audit.report.v1', checkpoint)
    if not audit['passed']:
        failures.append('audit errors: ' + ', '.join(sorted({f['code'] for f in audit['findings'] if f['severity'] == 'error'})))
    spec_ref = None
    if loop['spec']:
        spec_ref, compared = _report(base, evidence['spec_compare'], 'The spec-compare report', 'dcc.blockout.report.v1', checkpoint)
        if compared['spec_digest'] != loop['spec']['digest']:
            raise ValueError('The spec-compare report was made for another spec')
        if not compared['passed']:
            failures.append('spec-compare findings: ' + ', '.join(sorted({f['code'] + ' ' + f['path'] for f in compared['findings']})))
    views_ref, views = _report(base, evidence['views'], 'The render receipt', 'dcc.quality.renders.v1', checkpoint)
    sheet_ref, sheet = _report(base, evidence['sheet'], 'The review-sheet receipt', 'dcc.review.sheet.v1', checkpoint)
    images = {**_images(views_ref['path'], views), **_images(sheet_ref['path'], sheet)}
    project_checkpoint = evidence.get('project_checkpoint')
    if project_checkpoint is not None:
        _fields(project_checkpoint, {'checkpoint_id', 'checkpoint_sha256'})
        if project_checkpoint['checkpoint_sha256'] != checkpoint['sha256']:
            raise ValueError('project_checkpoint names another file')
    number = len(rounds) + 1
    record = {'schema': 'dcc.judge.round.v1', 'round': number, 'created': now(), 'approach': approach, 'changed_approach': changed,
              'checkpoint': checkpoint, 'audit': audit_ref, 'spec_compare': spec_ref, 'views': views_ref, 'sheet': sheet_ref, 'images': images,
              'project_checkpoint': project_checkpoint, 'gate_failures': failures, 'status': 'gated' if failures else 'awaiting_verdict'}
    result = {'schema': 'dcc.judge.round.result.v1', 'round': number, 'status': record['status'], 'passed': not failures, 'gate_failures': failures}
    if not failures:
        previous = verdicts[max(verdicts)] if verdicts else None
        packet = {'schema': 'dcc.judge.packet.v1', 'round': number, 'brief': loop['brief'], 'targets': loop['targets'],
                  'references': [{'id': r['id'], 'role': r['role'], 'intent': r['intent'], 'image': r['file']['path']} for r in loop['references']],
                  'images': {name: image['path'] for name, image in images.items()},
                  'rubric': {key: f'0 to {RUBRIC[key]}: {RUBRIC_TEXT[key]}' for key in RUBRIC},
                  'previous': None if previous is None else {'round': previous['round'], 'scores': previous['scores'], 'total': previous['total'],
                                                             'gaps': previous['gaps']},
                  'instructions': [
                      'Judge only what the images show against the brief and targets. You did not build this and have no stake in it.',
                      'Score each rubric line as a whole number. Do not round up for effort.',
                      'List specific gaps: where in which image, and what is wrong. Name symptoms; do not guess at causes or fixes.',
                      'If a gap from the previous verdict is still there, reuse its id exactly. Give a new gap a new lowercase-hyphen id.',
                      'Answer with one JSON object: {"schema": "dcc.judge.verdict.v1", "judge": {"author": "...", "context": "fresh"}, '
                      '"scores": {"composition": n, "lighting": n, "materials": n, "detail": n}, '
                      '"gaps": [{"id": "...", "where": "...", "problem": "..."}], "summary": "..."}'],
                  'attribution': ATTRIBUTION}
        write_json(root / 'packets' / f'{number:02d}.json', packet)
        result['packet'] = str(root / 'packets' / f'{number:02d}.json')
    write_json(root / 'rounds' / f'{number:02d}.json', record)
    current = status(root)
    return {**result, 'next': current['next'], 'instruction': current['instruction'], 'rounds_used': number, 'cap': loop['cap']}


def add_verdict(root, verdict_path):
    """Record the judge's answer for the round that awaits one, and say what happens next."""
    root, loop, rounds, verdicts = _load(root)
    number = max(rounds) if rounds else None
    if number is None or number in verdicts or rounds[number]['status'] != 'awaiting_verdict':
        raise ValueError('No round is waiting for a verdict')
    verdict = read_json(_plain(verdict_path))
    _fields(verdict, {'schema', 'judge', 'scores', 'gaps', 'summary'})
    if verdict['schema'] != 'dcc.judge.verdict.v1':
        raise ValueError('A verdict needs schema dcc.judge.verdict.v1')
    _fields(verdict['judge'], {'author', 'context'})
    _text(verdict['judge']['author'], 'The judge author')
    if verdict['judge']['context'] not in ('fresh', 'same'):
        raise ValueError('Judge context is fresh (a separate agent) or same (the builder judging its own work)')
    scores = verdict['scores']
    if not isinstance(scores, dict) or set(scores) != set(RUBRIC) or any(
            isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= RUBRIC[k] for k, v in scores.items()):
        raise ValueError('Scores are whole numbers: ' + ', '.join(f'{k} 0-{v}' for k, v in RUBRIC.items()))
    total = sum(scores.values())
    gaps, seen = verdict['gaps'], set()
    if not isinstance(gaps, list) or (not gaps and total < FULL):
        raise ValueError('A score below full marks must name at least one gap')
    for gap in gaps:
        _fields(gap, {'id', 'where', 'problem'})
        if not isinstance(gap['id'], str) or not SLUG.fullmatch(gap['id']) or gap['id'] in seen:
            raise ValueError('Gap IDs must be unique lowercase slugs')
        seen.add(gap['id'])
        _text(gap['where'], 'A gap\'s where'); _text(gap['problem'], 'A gap\'s problem')
    _text(verdict['summary'], 'The summary')
    record = {**verdict, 'round': number, 'total': total, 'recorded': now(), 'attribution': ATTRIBUTION}
    notes = []
    anchor = rounds[number]['project_checkpoint']
    if anchor is not None:
        for gap in gaps:
            path = root / 'notes' / f'{number:02d}-{gap["id"]}.json'
            write_json(path, {'schema': 'dcc.feedback.note.v1', 'stage_id': None, 'category': 'visual', 'priority': 'advisory',
                              'source': {'role': 'agent', 'author': verdict['judge']['author'],
                                         'reference': f'Judge loop round {number}, score {total} of {FULL}; an agent opinion, not owner acceptance'},
                              'text': f'{gap["where"]}: {gap["problem"]}', 'acceptance': f'A later judge round no longer names the gap {gap["id"]}.',
                              'anchor': dict(anchor)})
            notes.append(str(path))
    write_json(root / 'verdicts' / f'{number:02d}.json', record)
    current = status(root)
    return {'schema': 'dcc.judge.verdict.result.v1', 'round': number, 'total': total, 'of': FULL, 'scores': scores, 'gaps': [g['id'] for g in gaps],
            'judge_context': verdict['judge']['context'], 'next': current['next'], 'reason': current['reason'], 'instruction': current['instruction'],
            'stopped': current['stopped'], 'feedback_notes': notes, 'attribution': ATTRIBUTION}
