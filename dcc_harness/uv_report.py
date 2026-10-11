"""UV quality report: texel density, UV overlap and UVs outside the unit square, per mesh.

A fresh background Blender measures each mesh's evaluated triangles on its active render UV layer.
The measurements are the world and UV areas (so UV units per metre), a grid estimate of
self-overlap, the share of UV area outside 0..1, and the largest texture its materials use.
Portable code classifies them against dcc.uv.targets.v1 rules, as the relations command does. It
is a measurement beside the observation, not part of it, so earlier checkpoints are unaffected.
"""
from __future__ import annotations

import fnmatch
import math
from pathlib import Path

from .continuity import _plain
from .evidence import file_hash, read_json, write_json
from .native import run_worker

WORKER = Path(__file__).with_name('_uv_blender.py')
SCHEMA = 'dcc.uv.targets.v1'
KEYS = {'id', 'select', 'min_density', 'max_density', 'max_overlap', 'max_outside', 'texture_px'}
LIMITS = ('Texel density is the square root of UV area over world area times the largest texture the object uses. '
          'Overlap is a grid estimate of self-overlap on the active render UV layer. Neither says the texture looks right.')


def _number(value, *, fraction=False, positive=False):
    return (not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
            and (0 <= value <= 1 if fraction else value > 0 if positive else value >= 0))


def validate_targets(spec):
    if not isinstance(spec, dict) or set(spec) != {'schema', 'targets'} or spec['schema'] != SCHEMA:
        raise ValueError('UV targets need schema dcc.uv.targets.v1 and a targets list')
    if not isinstance(spec['targets'], list) or not spec['targets']:
        raise ValueError('UV targets need at least one rule')
    seen = set()
    for rule in spec['targets']:
        if not isinstance(rule, dict) or not {'id', 'select'} <= set(rule) or set(rule) - KEYS:
            raise ValueError('A UV rule needs id and select, and only: ' + ', '.join(sorted(KEYS)))
        if not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in seen or not isinstance(rule['select'], str) or not rule['select']:
            raise ValueError('UV rule IDs must be unique and select an ID glob')
        seen.add(rule['id'])
        if not set(rule) & {'min_density', 'max_density', 'max_overlap', 'max_outside'}:
            raise ValueError(f'UV rule {rule["id"]} sets no limit')
        for key in ('min_density', 'max_density', 'texture_px'):
            if key in rule and not _number(rule[key], positive=True):
                raise ValueError(f'{key} must be a positive number')
        for key in ('max_overlap', 'max_outside'):
            if key in rule and not _number(rule[key], fraction=True):
                raise ValueError(f'{key} must be a fraction from 0 to 1')
        if 'min_density' in rule and 'max_density' in rule and rule['min_density'] > rule['max_density']:
            raise ValueError('min_density is above max_density')
    return spec


def _finding(rule, record):
    if not record.get('uv_layer'):
        return {'codes': ['NO_UV']}
    codes, finding = [], {}
    if 'min_density' in rule or 'max_density' in rule:
        texture = record.get('texture_px') or rule.get('texture_px')
        if not texture or record.get('uv_per_m') is None:
            codes.append('UNMEASURED')
            finding['density_note'] = 'no texture on the object and no texture_px in the rule'
        else:
            density = round(record['uv_per_m'] * texture, 3)
            finding['density'] = density
            if 'min_density' in rule and density < rule['min_density']:
                codes.append('DENSITY_LOW')
            if 'max_density' in rule and density > rule['max_density']:
                codes.append('DENSITY_HIGH')
    if 'max_overlap' in rule:
        if record.get('overlap') is None:
            codes.append('UNMEASURED')
            finding['overlap_note'] = record.get('overlap_note')
        else:
            finding['overlap'] = record['overlap']
            if record['overlap'] > rule['max_overlap']:
                codes.append('OVERLAP')
    if 'max_outside' in rule:
        finding['outside'] = record['outside']
        if record['outside'] > rule['max_outside']:
            codes.append('OUTSIDE')
    return {**finding, 'codes': list(dict.fromkeys(codes)) or ['OK']}


def classify(spec, measurement):
    """Findings per rule and object; any code other than OK fails, and so does a rule that matches nothing."""
    validate_targets(spec)
    if measurement.get('schema') != 'dcc.uv.measurement.v1':
        raise ValueError('Not a UV measurement')
    targets, passed = {}, True
    for rule in spec['targets']:
        ids = sorted(i for i in measurement['objects'] if fnmatch.fnmatchcase(i, rule['select']))
        findings = {i: _finding(rule, measurement['objects'][i]) for i in ids}
        ok = bool(ids) and all(f['codes'] == ['OK'] for f in findings.values())
        targets[rule['id']] = {'passed': ok, 'findings': findings, 'codes': [] if ids else ['MISSING_TARGET']}
        passed = passed and ok
    return {'schema': 'dcc.uv.report.v1', 'passed': passed, 'targets': targets, 'grid': measurement['grid'], 'limits': LIMITS}


def _definition(project, targets):
    if (project is None) == (targets is None):
        raise ValueError('Give exactly one of a project or a targets file')
    if targets is not None:
        return validate_targets(read_json(_plain(targets)))
    from .workflow import resume
    decisions = resume(project)['decisions']
    if 'uv_targets' not in decisions:
        raise ValueError('The project has no uv_targets decision; record one or pass a targets file')
    return validate_targets(decisions['uv_targets'])


def measure_file(source, out, blender, *, targets=None, project=None):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    definition = _definition(project, targets)
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    run_worker(blender, folder, WORKER, 'measure', {'source': descriptor, 'out': str(folder.resolve())})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during measurement; inspect retained outputs')
    measurement = read_json(folder / 'measurement.json')
    if measurement.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Measurement is not bound to the source bytes')
    report = {**classify(definition, measurement), 'source': descriptor}
    write_json(folder / 'report.json', report)
    return {**report, 'report': str(folder / 'report.json'), 'artistic_acceptance': 'not_assessed'}
