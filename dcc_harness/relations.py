"""Measured supported_by relations, classified by evidence strength, with a retained repair history.

A fresh background Blender ray-casts each subject's contact footprint against its declared
support surfaces; that native measurement decides a finding. A bounding-box estimate is
reported beside it but can only ask for inspection. With a project, every measurement is
appended to its relations record, so a later session can see which repairs did not work.
"""
from __future__ import annotations

import math
from pathlib import Path
import re

from .continuity import Continuity, _plain
from .evidence import digest, file_hash, read_json, write_json
from .native import run_worker
from .project import now

WORKER = Path(__file__).with_name('_relations_blender.py')
SCHEMA = 'dcc.relations.v1'
KEYS = {'id', 'kind', 'subjects', 'support', 'max_gap', 'max_penetration', 'footprint'}
IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9_.-]{0,63}')
FAILING = ('GAP', 'PENETRATION')
ADVICE = {
    'OPPOSING': ('The last two attempts swung between a gap and penetration. Do not repeat either move; make a smaller, '
                 'targeted change from the measured error, or report the conflict.'),
    'NO_PROGRESS': 'The last attempt barely changed the error. Try a different strategy rather than repeating it.',
    'CONFLICT': ('Some subjects float while others penetrate, so no rigid move of the whole group can fix this. '
                 'Adjust the subjects individually or reshape the support.')}
LIMITS = ('Vertical ray samples of each subject\'s lowest vertices against the declared support surfaces only. '
          'Not collision with other objects, physical stability, or visual quality.')


def _length(value, *, positive=False):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def validate_relations(spec):
    """Check a dcc.relations.v1 definition and return it unchanged."""
    if not isinstance(spec, dict) or set(spec) != {'schema', 'relations'} or spec['schema'] != SCHEMA:
        raise ValueError('Relations need schema dcc.relations.v1 and a relations list')
    items = spec['relations']
    if not isinstance(items, list) or not items:
        raise ValueError('Relations need at least one relation')
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != KEYS:
            raise ValueError('A relation needs exactly: ' + ', '.join(sorted(KEYS)))
        if not isinstance(item['id'], str) or not IDENTIFIER.fullmatch(item['id']) or item['id'] in seen:
            raise ValueError('Relation IDs must be unique lowercase names')
        seen.add(item['id'])
        if item['kind'] != 'supported_by':
            raise ValueError('Only supported_by relations are qualified')
        for key in ('subjects', 'support'):
            ids = item[key]
            if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('Subjects and support need distinct stable IDs')
        if set(item['subjects']) & set(item['support']):
            raise ValueError('An object cannot support itself')
        if not _length(item['max_gap']) or not _length(item['max_penetration']) or not _length(item['footprint'], positive=True):
            raise ValueError('Tolerances must be finite, nonnegative metres and the footprint positive')
    return spec


def _code(distance, rule):
    if distance > rule['max_gap']:
        return 'GAP'
    if distance < -rule['max_penetration']:
        return 'PENETRATION'
    return 'OK'


def classify(spec, measurement):
    """Turn a native measurement into findings; the measurement must be of this exact definition."""
    validate_relations(spec)
    if measurement.get('schema') != 'dcc.relations.measurement.v1' or measurement.get('spec_digest') != digest(spec):
        raise ValueError('Measurement is missing or was made for another relations definition')
    results, passed = {}, True
    for rule in spec['relations']:
        measured = measurement['relations'][rule['id']]
        findings = {}
        for sid in rule['subjects']:
            if measured['missing']:
                findings[sid] = {'code': 'MISSING_TARGET', 'error': None, 'evidence': 'native_raycast', 'permitted': 'inspect',
                                 'detail': 'Not found as a mesh: ' + ', '.join(measured['missing'])}
                continue
            sample = measured['subjects'][sid]
            points, hits = sample['footprint_points'], sample['hits']
            if not hits:
                finding = {'code': 'OFF_SUPPORT', 'error': None, 'evidence': 'native_raycast', 'permitted': 'repair',
                           'coverage': f'none: 0 of {points} footprint points over the support'}
            else:
                code = _code(sample['min_distance'], rule)
                finding = {'code': code, 'error': round(sample['min_distance'], 6), 'evidence': 'native_raycast',
                           'permitted': 'none' if code == 'OK' else 'repair',
                           'spread': round(sample['max_distance'] - sample['min_distance'], 6),
                           'coverage': 'full' if hits == points else f'partial: {hits} of {points} footprint points over the support'}
            if sample.get('bounds_gap') is not None:
                estimate = _code(sample['bounds_gap'], rule)
                finding['bounds_estimate'] = {'code': estimate, 'error': round(sample['bounds_gap'], 6), 'evidence': 'bounds_only',
                                              'permitted': 'inspect', 'agrees': estimate == finding['code']}
            findings[sid] = finding
        codes = {f['code'] for f in findings.values()}
        ok = codes == {'OK'}
        passed = passed and ok
        results[rule['id']] = {'passed': ok, 'conflict': set(FAILING) <= codes, 'findings': findings}
    return {'schema': 'dcc.relations.report.v1', 'passed': passed, 'spec_digest': digest(spec), 'relations': results,
            'limits': LIMITS}


def record(root, report, strategy=None):
    """Append one measurement to the project's relations record; entries are never rewritten."""
    from .workflow import writer_guard
    if strategy is not None and (not isinstance(strategy, str) or not strategy.strip()):
        raise ValueError('A strategy must be nonempty text')
    with writer_guard(root):
        active = Continuity(root).status()['active']
        folder = _plain(Path(root) / 'relations')
        folder.mkdir(exist_ok=True)
        names = sorted(p.name for p in folder.iterdir())
        if names != [f'{n:06d}.json' for n in range(1, len(names) + 1)]:
            raise RuntimeError('Unexpected files in the relations record; inspect before recording')
        entry = {'schema': 'dcc.relations.entry.v1', 'sequence': len(names) + 1, 'created': now(), 'parent': active['id'],
                 'source': report['source'], 'strategy': strategy, 'spec_digest': report['spec_digest'],
                 'passed': report['passed'], 'relations': report['relations']}
        write_json(folder / f'{entry["sequence"]:06d}.json', entry)
    return entry


def _attempt(entry, finding):
    return {'sequence': entry['sequence'], 'strategy': entry['strategy'], 'code': finding['code'], 'error': finding['error']}


def history(root):
    """Attempts per relation and subject, with warnings for ineffective repetition."""
    folder = Path(root) / 'relations'
    entries = [read_json(p) for p in sorted(folder.glob('*.json'))] if folder.is_dir() else []
    subjects, warnings = {}, []
    for entry in entries:
        for rid, result in entry['relations'].items():
            for sid, finding in result['findings'].items():
                subjects.setdefault(f'{rid}/{sid}', {'relation': rid, 'subject': sid, 'attempts': []})['attempts'].append(_attempt(entry, finding))
    for key, item in sorted(subjects.items()):
        attempts = item['attempts']
        trend = attempts[-1]['code']
        if len(attempts) >= 2 and attempts[-1]['code'] in FAILING and attempts[-2]['code'] in FAILING:
            previous, last = attempts[-2], attempts[-1]
            if previous['code'] != last['code']:
                trend = 'OPPOSING'
            elif abs(last['error']) > 0.8 * abs(previous['error']):
                trend = 'NO_PROGRESS'
            else:
                trend = 'IMPROVING'
        item['trend'] = trend
        if trend in ('OPPOSING', 'NO_PROGRESS'):
            warnings.append({'code': trend, 'relation': item['relation'], 'subject': item['subject'],
                             'attempts': attempts[-2:], 'advice': ADVICE[trend]})
    if entries:
        latest = entries[-1]
        for rid, result in sorted(latest['relations'].items()):
            if result['conflict']:
                warnings.append({'code': 'CONFLICT', 'relation': rid, 'subject': None,
                                 'attempts': [_attempt(latest, f) | {'subject': sid} for sid, f in sorted(result['findings'].items())],
                                 'advice': ADVICE['CONFLICT']})
    return {'schema': 'dcc.relations.history.v1', 'entries': len(entries), 'subjects': subjects, 'warnings': warnings}


def _definition(project, spec):
    if (project is None) == (spec is None):
        raise ValueError('Give exactly one of a project or a relations file')
    if spec is not None:
        return validate_relations(read_json(_plain(spec)))
    from .workflow import resume
    decisions = resume(project)['decisions']
    if 'relations' not in decisions:
        raise ValueError('The project has no relations decision; record one or pass a relations file')
    return validate_relations(decisions['relations'])


def measure_file(source, out, blender, *, spec=None, project=None, strategy=None):
    if strategy is not None and project is None:
        raise ValueError('A strategy is recorded in a project history; pass --project with --strategy')
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    definition = _definition(project, spec)
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    run_worker(blender, folder, WORKER, 'relations', {'source': descriptor, 'out': str(folder.resolve()), 'definition': definition})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during measurement; inspect retained outputs')
    measurement = read_json(folder / 'measurement.json')
    if measurement.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Measurement is not bound to the source bytes')
    report = {**classify(definition, measurement), 'source': descriptor}
    write_json(folder / 'report.json', report)
    result = {**report, 'report': str(folder / 'report.json'), 'artistic_acceptance': 'not_assessed'}
    if project is not None:
        entry = record(project, report, strategy)
        result['recorded'] = {'sequence': entry['sequence'], 'parent': entry['parent'],
                              'path': str(Path(project).resolve() / 'relations' / f'{entry["sequence"]:06d}.json')}
        result['history'] = {k: v for k, v in history(project).items() if k != 'subjects'}
    return result
