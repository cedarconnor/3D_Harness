"""Learned checks: computed rules proven on the error they came from, approved by the owner into a
versioned library outside any project, and pinned by workflow bindings (D19).

A rule is evaluated by the runtime from a checkpoint's stored observation, or for supported_by
from a native relations measurement of that exact checkpoint. A lesson that cannot be measured
stays a skill note. Approval goes through the owner channel (D18), a guard and not a wall.
"""
from __future__ import annotations

import fnmatch
import json
import math
from pathlib import Path
import shutil

from . import coordination as c, feedback, owner
from .continuity import Continuity, _plain
from .coordination_evidence import actor
from .evidence import file_hash, read_json, write_json
from .project import now
from .relations import IDENTIFIER, classify, validate_relations


RULE = 'dcc.check.rule.v1'
PROPOSAL = 'dcc.check.proposal.v1'
LIBRARY = 'dcc.checks.library.v1'
OCCURRENCE = 'dcc.checks.occurrence.v1'
AXES = {'x': 0, 'y': 1, 'z': 2}
FIELDS = ({f'bounds.{end}.{axis}' for end in ('min', 'max') for axis in AXES} | {f'dimensions.{axis}' for axis in AXES}
          | {'scale.min', 'scale.max', 'determinant', 'triangles', 'vertices', 'materials', 'visible.render'})
SELECTOR = {'type', 'id'}
TOLERANCES = ('max_gap', 'max_penetration', 'footprint')
LIMITS = ('Each check is computed from the stored observation or a native relations measurement of the checkpoint; '
          'it measures one rule and says nothing about artistic quality.')


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _selector(value):
    if not isinstance(value, dict) or not value or set(value) - SELECTOR or any(not isinstance(v, str) or not v for v in value.values()):
        raise ValueError('A selector needs a type and/or an id glob, as text')
    return value


def validate_rule(rule):
    """Check a dcc.check.rule.v1 rule and return it unchanged."""
    if not isinstance(rule, dict) or rule.get('schema') != RULE:
        raise ValueError('A check needs a dcc.check.rule.v1 rule')
    kind = rule.get('kind')
    if kind == 'object_field':
        keys, required = {'schema', 'kind', 'select', 'field', 'min', 'max', 'require_match'}, {'schema', 'kind', 'select', 'field'}
    elif kind == 'supported_by':
        keys = required = {'schema', 'kind', 'subjects', 'support', *TOLERANCES}
        keys = keys | {'require_match'}
    else:
        raise ValueError('Unsupported rule kind; a lesson the runtime cannot measure stays a skill note')
    if not required <= set(rule) or set(rule) - keys:
        raise ValueError('A rule needs exactly: ' + ', '.join(sorted(required)))
    if 'require_match' in rule and not isinstance(rule['require_match'], bool):
        raise ValueError('require_match must be true or false')
    if kind == 'object_field':
        _selector(rule['select'])
        if rule['field'] not in FIELDS:
            raise ValueError('Unknown field; measurable fields are ' + ', '.join(sorted(FIELDS)))
        bounds = [rule[k] for k in ('min', 'max') if k in rule]
        if not bounds or any(not _number(b) for b in bounds):
            raise ValueError('A field rule needs a finite min and/or max')
        if len(bounds) == 2 and rule['min'] > rule['max']:
            raise ValueError('min is above max')
    else:
        _selector(rule['subjects']); _selector(rule['support'])
        if any(not _number(rule[k]) or rule[k] < 0 for k in TOLERANCES) or rule['footprint'] <= 0:
            raise ValueError('Tolerances must be finite, nonnegative metres and the footprint positive')
    return rule


def select(observation, selector):
    """Stable IDs of the observed objects a selector matches, sorted."""
    return sorted(i for i, o in observation['objects'].items()
                  if ('type' not in selector or o.get('type') == selector['type'])
                  and ('id' not in selector or fnmatch.fnmatchcase(i, selector['id'])))


def _columns(matrix):
    if not (isinstance(matrix, list) and len(matrix) >= 3 and all(isinstance(r, list) and len(r) >= 3 for r in matrix[:3])):
        return None
    return [[matrix[r][col] for r in range(3)] for col in range(3)]


def measure(item, field):
    """One measured field of an observed object, or None when the observation lacks it."""
    try:
        if field.startswith('bounds.'):
            _, end, axis = field.split('.')
            return item['bounds'][0 if end == 'min' else 1][AXES[axis]]
        if field.startswith('dimensions.'):
            return item['dimensions'][AXES[field[-1]]]
        if field in ('triangles', 'vertices'):
            return item[field]
        if field == 'materials':
            return len(item.get('material_ids', []))
        if field == 'visible.render':
            return 1 if item['visibility']['render'] else 0
        columns = _columns(item['matrix_world'])
        if columns is None:
            return None
        if field == 'determinant':
            (a, d, g), (b, e, h), (cc, f, i) = columns
            return a * (e * i - f * h) - b * (d * i - f * g) + cc * (d * h - e * g)
        lengths = [math.sqrt(sum(v * v for v in col)) for col in columns]
        return min(lengths) if field == 'scale.min' else max(lengths)
    except (KeyError, IndexError, TypeError):
        return None


def resolve(check_id, rule, observation):
    """The dcc.relations.v1 definition a supported_by rule names on this observation."""
    support = select(observation, rule['support'])
    subjects = [i for i in select(observation, rule['subjects']) if i not in support]
    if not subjects or not support:
        return None
    return validate_relations({'schema': 'dcc.relations.v1', 'relations': [
        {'id': check_id, 'kind': 'supported_by', 'subjects': subjects, 'support': support,
         **{k: rule[k] for k in TOLERANCES}}]})


def evaluate(check_id, rule, observation, measurement=None):
    """Evaluate one check: PASS, FAIL or NOT_MEASURED, with findings."""
    validate_rule(rule)
    base = {'id': check_id, 'kind': rule['kind']}
    no_match = {**base, 'findings': [], 'detail': 'Nothing matches the rule'}
    if rule['kind'] == 'object_field':
        ids = select(observation, rule['select'])
        if not ids:
            return {**no_match, 'status': 'FAIL' if rule.get('require_match', True) else 'PASS',
                    'passed': not rule.get('require_match', True)}
        findings = []
        for i in ids:
            value = measure(observation['objects'][i], rule['field'])
            code = ('UNMEASURED' if value is None else 'BELOW' if 'min' in rule and value < rule['min']
                    else 'ABOVE' if 'max' in rule and value > rule['max'] else 'OK')
            findings.append({'id': i, 'value': value, 'code': code})
        passed = all(f['code'] == 'OK' for f in findings)
        return {**base, 'status': 'PASS' if passed else 'FAIL', 'passed': passed, 'findings': findings}
    spec = resolve(check_id, rule, observation)
    if spec is None:
        return {**no_match, 'status': 'FAIL' if rule.get('require_match', True) else 'PASS',
                'passed': not rule.get('require_match', True)}
    if measurement is None:
        return {**base, 'status': 'NOT_MEASURED', 'passed': False, 'findings': [], 'spec': spec,
                'detail': 'Measure the resolved definition with relations --spec and pass the measurement'}
    if measurement.get('checkpoint_sha256') != observation['checkpoint_sha256']:
        raise ValueError('The measurement is of another checkpoint')
    report = classify(spec, measurement)
    findings = [{'id': sid, 'code': f['code'], 'value': f['error']} for sid, f in sorted(report['relations'][check_id]['findings'].items())]
    return {**base, 'status': 'PASS' if report['passed'] else 'FAIL', 'passed': report['passed'], 'findings': findings, 'spec': spec}


def stage_ids():
    from .environment_workflow import default_manifest
    return [s['id'] for s in default_manifest()['stages']]


# Proposals: recorded in the project's coordination record.

def _fixture(ctx, value):
    c.fields(value, {'checkpoint'}, {'measurement'})
    entry = ctx.checkpoint(value['checkpoint'])
    measurement = read_json(ctx.artifact(value['measurement'])) if 'measurement' in value else None
    return entry, read_json(entry['observation']), measurement


def _propose(ctx, value):
    c.fields(value, {'schema', 'id', 'note_id', 'classification', 'rule', 'stages', 'rationale', 'proposer', 'fails', 'passes'})
    if value['schema'] != PROPOSAL:
        raise ValueError('Unsupported check proposal')
    if value['classification'] == 'taste':
        raise ValueError('Taste stays project direction: record it as a decision or in the brief, not as a check')
    if value['classification'] != 'error':
        raise ValueError('Classify the note as error or taste')
    if not isinstance(value['id'], str) or not IDENTIFIER.fullmatch(value['id']):
        raise ValueError('Check IDs must be lowercase names')
    validate_rule(value['rule'])
    if not isinstance(value['stages'], list) or not value['stages'] or len(set(value['stages'])) != len(value['stages']) \
            or not set(value['stages']) <= set(stage_ids()):
        raise ValueError('Unknown stage; use stages from the environment template: ' + ', '.join(stage_ids()))
    c.text(value['rationale']); actor(value['proposer'])
    notes = feedback.state(ctx.events, ctx.native)
    if value['note_id'] not in notes:
        raise ValueError('Unknown feedback note')
    note = notes[value['note_id']]['note']
    if any(e['kind'] == 'check.propose' and e['result']['check_id'] == value['id'] for e in ctx.events):
        raise ValueError('A check with this ID was already proposed in this project')
    fails, fails_obs, fails_m = _fixture(ctx, value['fails'])
    passes, passes_obs, passes_m = _fixture(ctx, value['passes'])
    if fails['id'] != note['anchor']['checkpoint_id']:
        raise ValueError("The failing fixture must be the note's own checkpoint")
    if passes['sequence'] <= fails['sequence']:
        raise ValueError('The passing fixture must be a later checkpoint where the error is fixed')
    results = {'fails': evaluate(value['id'], value['rule'], fails_obs, fails_m),
               'passes': evaluate(value['id'], value['rule'], passes_obs, passes_m)}
    for side, expected, message in (('fails', 'FAIL', 'The rule does not fail on the note'), ('passes', 'PASS', 'The rule does not pass on the fixed')):
        if results[side]['status'] != expected:
            raise ValueError(f"{message}'s checkpoint ({results[side]['status']}); a check must catch the error and clear the fix")
    return {'check_id': value['id'], 'proposal': value, 'results': results,
            'note': {k: note[k] for k in ('id', 'text', 'acceptance', 'source')},
            'fixtures': {side: {'checkpoint_id': e['id'], 'checkpoint_sha256': e['checkpoint_sha256'], 'sequence': e['sequence']}
                         for side, e in (('fails', fails), ('passes', passes))},
            'artistic_acceptance': 'not_evaluated'}


BUILDERS = {'check.propose': _propose}


def apply(root, kind, payload, expected_revision, request_id, base=None, approval=None):
    return c.transact(root, kind, payload, expected_revision, request_id, base or Path.cwd(), BUILDERS[kind], approval)


# The library: outside any project, one immutable version per approval.

def _ref(root, path):
    return {'path': path.relative_to(root).as_posix(), 'sha256': file_hash(path)}


def _fixture_file(root, ref):
    path = c.relative(root, ref['path'])
    if not path.is_file() or file_hash(path) != ref['sha256']:
        raise ValueError('Library fixture missing or changed: ' + ref['path'])
    return read_json(path)


def validate_document(document):
    """Structure of one library version, as retained by a binding."""
    if not isinstance(document, dict) or document.get('schema') != LIBRARY:
        raise ValueError('Not a dcc.checks.library.v1 document')
    c.fields(document, {'schema', 'version', 'previous', 'created', 'checks'})
    if type(document['version']) is not int or document['version'] < 1 or not isinstance(document['checks'], list):
        raise ValueError('Invalid library version')
    seen = set()
    for check in document['checks']:
        if not isinstance(check, dict) or not isinstance(check.get('approval'), dict) or check['approval'].get('channel') != 'owner_terminal':
            raise ValueError('Every library check needs an owner approval')
        c.fields(check, {'id', 'rule', 'stages', 'rationale', 'origin', 'fixtures', 'approval'})
        if check['id'] in seen or not IDENTIFIER.fullmatch(check['id']):
            raise ValueError('Library check IDs must be unique lowercase names')
        seen.add(check['id'])
        validate_rule(check['rule'])
    return document


def read_library(library, version=None, *, prove=True):
    """Verify the version chain, fixture hashes and, with prove, every check on its own fixtures."""
    root = _plain(library)
    folder = root / 'versions'
    names = sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []
    if names != [f'{n:06d}' for n in range(1, len(names) + 1)]:
        raise ValueError('Unexpected library versions; inspect before continuing')
    previous, document, path, checks_before = None, None, None, []
    for name in names[:version] if version else names:
        path = folder / name / 'library.json'
        document = validate_document(read_json(path))
        if document['version'] != int(name) or document['previous'] != previous or document['checks'][:-1] != checks_before \
                or len(document['checks']) != len(checks_before) + 1:
            raise ValueError('Library version chain changed')
        previous, checks_before = file_hash(path), document['checks']
    if version and version > len(names):
        raise ValueError('Unknown library version')
    current = document or {'schema': LIBRARY, 'version': 0, 'previous': None, 'checks': []}
    for check in current['checks']:
        for side, expected in (('fails', 'FAIL'), ('passes', 'PASS')):
            fixture = check['fixtures'][side]
            observation = _fixture_file(root, fixture['observation'])
            measurement = _fixture_file(root, fixture['measurement']) if 'measurement' in fixture else None
            if prove and evaluate(check['id'], check['rule'], observation, measurement)['status'] != expected:
                raise ValueError(f'Library check {check["id"]} no longer proves itself on its {side} fixture')
    occurrences = {}
    folder = root / 'occurrences'
    entries = sorted(folder.glob('*.json')) if folder.is_dir() else []
    if [p.name for p in entries] != [f'{n:06d}.json' for n in range(1, len(entries) + 1)]:
        raise ValueError('Unexpected library occurrences; inspect before continuing')
    recorded = [read_json(p) for p in entries]
    for entry in recorded:
        occurrences[entry['check_id']] = occurrences.get(entry['check_id'], 0) + 1
    return {'root': str(root), 'version': current['version'], 'document': current, 'path': str(path) if path else None,
            'sha256': previous, 'occurrences': occurrences, 'occurrence_entries': recorded}


def _proposal(project, revision):
    events = c.read(project)
    event = next((e for e in events if e['id'] == revision and e['kind'] == 'check.propose'), None)
    if event is None:
        raise ValueError('Unknown check proposal')
    return event, Continuity(project).status()


def approve(library, project, revision, expected_version, console=None):
    """Owner only: prove the proposal again on its retained fixtures and write the next library version."""
    root = _plain(library)
    event, native = _proposal(project, revision)
    proposal = event['result']['proposal']
    entries = {e['id']: e for e in native['task_history']}
    retained = Path(event['artifacts'])
    sources = {}
    for side, expected in (('fails', 'FAIL'), ('passes', 'PASS')):
        entry = entries[proposal[side]['checkpoint']['checkpoint_id']]
        measurement = proposal[side].get('measurement')
        measured = c.relative(retained, measurement['path']) if measurement else None
        result = evaluate(proposal['id'], proposal['rule'], read_json(entry['observation']), read_json(measured) if measured else None)
        if result['status'] != expected:
            raise ValueError(f'The proposal no longer proves itself on its {side} checkpoint')
        sources[side] = (Path(entry['observation']), measured)
    current = read_library(root)
    if type(expected_version) is not int or expected_version != current['version']:
        raise ValueError('Stale library version; list the library and approve again')
    if proposal['id'] in {x['id'] for x in current['document']['checks']}:
        raise ValueError('A check with this ID is already in the library')
    note = event['result']['note']
    payload = {'library': str(root.resolve()), 'project': str(Path(project).resolve()), 'proposal': revision,
               'expected_version': expected_version, 'check_id': proposal['id'], 'rule': proposal['rule'],
               'stages': proposal['stages'], 'rationale': proposal['rationale'], 'note': note['text']}
    approval = owner.confirm('check.approve', payload, console)
    fixtures = root / 'fixtures' / proposal['id']
    if fixtures.exists():
        raise RuntimeError('Partial library write for this check; inspect before continuing')
    fixtures.mkdir(parents=True)
    kept = {}
    for side, (observation, measured) in sources.items():
        kept[side] = {'checkpoint_sha256': event['result']['fixtures'][side]['checkpoint_sha256']}
        for label, source in (('observation', observation), ('measurement', measured)):
            if source is not None:
                target = fixtures / f'{side}.{label}.json'
                with source.open('rb') as incoming, target.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                kept[side][label] = _ref(root, target)
    check = {'id': proposal['id'], 'rule': proposal['rule'], 'stages': proposal['stages'], 'rationale': proposal['rationale'],
             'origin': {'project': payload['project'], 'proposal': revision, 'note': note, 'proposer': proposal['proposer']},
             'fixtures': kept, 'approval': approval.provenance}
    version = current['version'] + 1
    document = {'schema': LIBRARY, 'version': version, 'previous': current['sha256'], 'created': now(),
                'checks': current['document']['checks'] + [check]}
    directory = root / 'versions' / f'{version:06d}'
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'library.json', document)
    return {'status': 'APPROVED', 'version': version, 'check': check, 'library': str(directory / 'library.json'),
            'limits': LIMITS}


def occurrence(library, project, note_id, check_id, measurement=None):
    """Count a repeat: a note in a project whose checkpoint the library check fails on."""
    root = _plain(library)
    current = read_library(root)
    check = next((x for x in current['document']['checks'] if x['id'] == check_id), None)
    if check is None:
        raise ValueError('Unknown library check')
    events, native = c.read(project), Continuity(project).status()
    notes = feedback.state(events, native)
    if note_id not in notes:
        raise ValueError('Unknown feedback note')
    note = notes[note_id]['note']
    entry = next(e for e in native['task_history'] if e['id'] == note['anchor']['checkpoint_id'])
    result = evaluate(check_id, check['rule'], read_json(entry['observation']), read_json(_plain(measurement)) if measurement else None)
    if result['status'] != 'FAIL':
        raise ValueError(f"The check {'passes' if result['status'] == 'PASS' else 'was not measured'} on the note's checkpoint; "
                         'this is not an occurrence of it')
    project_path = str(Path(project).resolve())
    if check['origin']['project'] == project_path and check['origin']['note']['id'] == note_id:
        raise ValueError('This note is already counted for the check: it is the note the check came from')
    if any(o['check_id'] == check_id and o['project'] == project_path and o['note']['id'] == note_id for o in current['occurrence_entries']):
        raise ValueError('This note is already counted for the check')
    folder = root / 'occurrences'
    folder.mkdir(exist_ok=True)
    sequence = len(current['occurrence_entries']) + 1
    value = {'schema': OCCURRENCE, 'sequence': sequence, 'check_id': check_id, 'project': project_path,
             'note': {'id': note_id, 'text': note['text']}, 'checkpoint_sha256': entry['checkpoint_sha256'],
             'created': now(), 'evaluation': result}
    with (folder / f'{sequence:06d}.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True))
    return value


def listing(library, version=None):
    current = read_library(library, version)
    rows = [{'id': x['id'], 'kind': x['rule']['kind'], 'stages': x['stages'], 'rationale': x['rationale'],
             'origin_note': x['origin']['note']['text'], 'occurrences': current['occurrences'].get(x['id'], 0),
             'count': 1 + current['occurrences'].get(x['id'], 0)} for x in current['document']['checks']]
    rows.sort(key=lambda r: (-r['count'], r['id']))
    return {'schema': 'dcc.checks.listing.v1', 'library': current['root'], 'version': current['version'],
            'sha256': current['sha256'], 'checks': rows, 'limits': LIMITS}


def export(library, out, version=None):
    """Copy one version's library.json byte for byte, for a workflow binding to pin."""
    current = read_library(library, version)
    if not current['path']:
        raise ValueError('The library has no approved checks yet')
    out = _plain(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with Path(current['path']).open('rb') as incoming, out.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    return {'exported': str(out), 'version': current['version'], 'sha256': file_hash(out)}


# Pinned checks inside a project.

def pinned(events):
    bound = feedback.binding(events)
    ref = None if bound is None else bound['result']['binding'].get('checks')
    return None if ref is None else read_json(c.relative(bound['artifacts'], ref['path']))


def applicable(document, stage):
    return [x for x in document['checks'] if stage == 'delivery' or stage in x['stages']]


def run(ctx, stage, checkpoint, measurements):
    """Evaluate the pinned checks for a stage on a checkpoint; None when nothing is pinned."""
    document = pinned(ctx.events)
    if document is None:
        if measurements:
            raise ValueError('No library checks are pinned; remove check_measurements')
        return None
    selected = applicable(document, stage)
    if not isinstance(measurements, dict) or set(measurements) - {x['id'] for x in selected}:
        raise ValueError('check_measurements must name pinned checks for this stage')
    observation = read_json(ctx.checkpoint(checkpoint)['observation'])
    return [evaluate(x['id'], x['rule'], observation, read_json(ctx.artifact(measurements[x['id']])) if x['id'] in measurements else None)
            for x in selected]
