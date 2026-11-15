"""Blockout spec: a planning-stage layout as named primitives, built into a scene and checked against one.

A dcc.blockout.v1 spec lists parts in metres with Z up. Each part is a primitive with a base-centre
position, a size and a yaw; `ids` says which scene objects stand for it once real modelling
replaces the primitive. Proportions are numeric relations between parts with tolerances, and
`never` rules are things that must not happen. Three commands use it:

  spec-check      validate the spec alone, including its own proportions and never rules
  blockout-build  build the parts into an owned, tagged collection in a new file
  spec-compare    measure a saved scene against the spec; a part that cannot be measured fails

Validation is strict: an unknown field or a number outside its range is an error, never clamped.
"""
from __future__ import annotations

import math
from pathlib import Path
import re

from .continuity import _plain
from .evidence import digest, file_hash, read_json, write_json
from .native import run_worker

WORKER = Path(__file__).with_name('_blockout_blender.py')
SCHEMA = 'dcc.blockout.v1'
NAME = re.compile(r'[a-z0-9][a-z0-9_.-]{0,63}')
PRIMITIVES = ('box', 'cylinder', 'plane', 'wedge', 'cone', 'sphere')
CATEGORIES = ('structure', 'opening', 'roof', 'ground', 'path', 'furniture', 'prop', 'vegetation', 'boundary', 'other')
MEASURES = ('width', 'depth', 'height', 'bottom', 'top', 'x', 'y')
RULES = {'no_overlap': {'id', 'rule', 'parts'}, 'not_below': {'id', 'rule', 'part', 'z'}, 'within': {'id', 'rule', 'part', 'footprint'}}
TOP_KEYS = {'schema', 'name', 'units', 'up', 'parts', 'proportions', 'never', 'avoid', 'tolerance', 'review_views'}
PART_KEYS = {'name', 'category', 'primitive', 'position', 'size', 'yaw', 'group', 'ids', 'rests_on'}
MAX_PARTS, MAX_SIZE, MIN_SIZE, MAX_COORDINATE = 500, 1000.0, 0.001, 10000.0
DEFAULT_TOLERANCE = {'size': 0.1, 'position': 0.1}
SIZE_FLOOR = 0.01     # metres: the size tolerance never falls below this
CONTACT = {'max_gap': 0.005, 'max_penetration': 0.005, 'footprint': 0.01}
REMEDY = {
    'PART_MISSING': 'Build the part, give its objects stable IDs the part\'s ids match, or correct ids in the spec.',
    'SIZE': 'Resize the part\'s objects to the spec, or change the spec with the owner if the brief has moved.',
    'POSITION': 'Move the part\'s objects so their base centre is where the spec puts it.',
    'PROPORTION': 'Change the parts named in the proportion until the measured value is inside its range.',
    'NEVER_OVERLAP': 'Separate the two parts; their bounding boxes interpenetrate.',
    'NEVER_BELOW': 'Raise the part so its lowest point is at or above the level.',
    'NEVER_OUTSIDE': 'Move the part back inside the footprint it must stay within.',
    'UNMEASURED': 'A part this rule needs was not measured; resolve its PART_MISSING finding first.'}
LIMITS = ('Sizes and positions are bounding boxes of the objects each part names, in the part\'s yaw frame. '
          'A match says the layout has the planned proportions, not that the model is good.')


def _number(value, low, high):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and low <= value <= high


def _name(value):
    return isinstance(value, str) and NAME.fullmatch(value) is not None


def _fail(path, message):
    raise ValueError(f'{path}: {message}')


def validate_spec(spec):
    """Check a dcc.blockout.v1 spec strictly and return it unchanged; it must also satisfy its own rules."""
    if not isinstance(spec, dict) or spec.get('schema') != SCHEMA:
        raise ValueError('A blockout spec needs schema dcc.blockout.v1')
    if set(spec) - TOP_KEYS:
        _fail('spec', 'unknown field ' + ', '.join(sorted(set(spec) - TOP_KEYS)))
    if not {'name', 'units', 'up', 'parts'} <= set(spec):
        _fail('spec', 'needs name, units, up and parts')
    if not _name(spec['name']):
        _fail('name', 'must be a lowercase name')
    if spec['units'] != 'metres' or spec['up'] != 'Z':
        _fail('units', 'only metres with Z up are supported')
    parts = spec['parts']
    if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS:
        _fail('parts', f'needs 1 to {MAX_PARTS} parts')
    names = set()
    for index, part in enumerate(parts):
        path = f'parts/{part.get("name", index) if isinstance(part, dict) else index}'
        if not isinstance(part, dict) or set(part) - PART_KEYS:
            _fail(path, 'unknown field' if isinstance(part, dict) else 'must be an object')
        if not {'name', 'category', 'primitive', 'position', 'size'} <= set(part):
            _fail(path, 'needs name, category, primitive, position and size')
        if not _name(part['name']) or part['name'] in names:
            _fail(path, 'names must be unique lowercase names')
        names.add(part['name'])
        if part['category'] not in CATEGORIES:
            _fail(path + '/category', 'must be one of: ' + ', '.join(CATEGORIES))
        if part['primitive'] not in PRIMITIVES:
            _fail(path + '/primitive', 'must be one of: ' + ', '.join(PRIMITIVES))
        position, size = part['position'], part['size']
        if not isinstance(position, list) or len(position) != 3 or not all(_number(v, -MAX_COORDINATE, MAX_COORDINATE) for v in position):
            _fail(path + '/position', f'must be three numbers within {MAX_COORDINATE:g} m')
        flat = part['primitive'] == 'plane'
        if not isinstance(size, list) or len(size) != 3 or not all(_number(v, MIN_SIZE, MAX_SIZE) for v in size[:2]) \
                or not (size[2] == 0 if flat else _number(size[2], MIN_SIZE, MAX_SIZE)):
            _fail(path + '/size', f'must be three numbers from {MIN_SIZE:g} to {MAX_SIZE:g} m' + ('; a plane has height 0' if flat else ''))
        if 'yaw' in part and not _number(part['yaw'], -360, 360):
            _fail(path + '/yaw', 'must be degrees from -360 to 360')
        if 'group' in part and not _name(part['group']):
            _fail(path + '/group', 'must be a lowercase name')
        if 'ids' in part and (not isinstance(part['ids'], list) or not part['ids'] or any(not isinstance(i, str) or not i for i in part['ids'])
                              or len(set(part['ids'])) != len(part['ids'])):
            _fail(path + '/ids', 'must be distinct ID globs')
    groups = {part['group'] for part in parts if 'group' in part}
    if groups & names:
        _fail('parts', 'a group cannot share a name with a part: ' + ', '.join(sorted(groups & names)))
    for part in parts:
        if 'rests_on' in part and (part['rests_on'] not in names or part['rests_on'] == part['name']):
            _fail(f'parts/{part["name"]}/rests_on', 'must name another part')
    tolerance = spec.get('tolerance', {})
    if not isinstance(tolerance, dict) or set(tolerance) - set(DEFAULT_TOLERANCE) or not all(_number(v, 0, 10) for v in tolerance.values()):
        _fail('tolerance', 'may set size (a fraction) and position (metres), each from 0 to 10')

    def reference(value, path):
        if not isinstance(value, dict) or set(value) != {'part', 'measure'} or value['measure'] not in MEASURES:
            _fail(path, 'must be {part, measure} with a measure of: ' + ', '.join(MEASURES))
        if value['part'] not in names | groups:
            _fail(path, f'unknown part or group {value["part"]}')

    seen = set()
    for index, item in enumerate(spec.get('proportions', [])):
        path = f'proportions/{item.get("id", index) if isinstance(item, dict) else index}'
        if not isinstance(item, dict) or set(item) - {'id', 'value', 'ratio', 'target', 'tolerance', 'min', 'max'}:
            _fail(path, 'unknown field')
        if not _name(item.get('id')) or item['id'] in seen:
            _fail(path, 'needs a unique lowercase id')
        seen.add(item['id'])
        if ('value' in item) == ('ratio' in item):
            _fail(path, 'needs exactly one of value or ratio')
        if 'value' in item:
            reference(item['value'], path + '/value')
        else:
            if not isinstance(item['ratio'], list) or len(item['ratio']) != 2:
                _fail(path + '/ratio', 'must be two {part, measure} references')
            for position, value in enumerate(item['ratio']):
                reference(value, f'{path}/ratio/{position}')
        centred, partly, ranged = {'target', 'tolerance'} <= set(item), bool({'target', 'tolerance'} & set(item)), bool({'min', 'max'} & set(item))
        if not ((centred and not ranged) or (ranged and not partly)):
            _fail(path, 'needs either target and tolerance, or min and/or max')
        if not all(_number(item[k], -MAX_COORDINATE, MAX_COORDINATE) for k in ('target', 'min', 'max') if k in item) \
                or ('tolerance' in item and not _number(item['tolerance'], 0, MAX_COORDINATE)):
            _fail(path, 'numbers must be finite and in range')
        if 'min' in item and 'max' in item and item['min'] > item['max']:
            _fail(path, 'min is above max')
    for index, rule in enumerate(spec.get('never', [])):
        path = f'never/{rule.get("id", index) if isinstance(rule, dict) else index}'
        if not isinstance(rule, dict) or rule.get('rule') not in RULES or set(rule) != RULES[rule['rule']]:
            _fail(path, 'must be one of: ' + '; '.join(', '.join(sorted(keys)) for keys in RULES.values()))
        if not _name(rule['id']) or rule['id'] in seen:
            _fail(path, 'needs a unique lowercase id')
        seen.add(rule['id'])
        named = rule['parts'] if rule['rule'] == 'no_overlap' else [rule['part']] + ([rule['footprint']] if rule['rule'] == 'within' else [])
        if not isinstance(named, list) or (rule['rule'] == 'no_overlap' and len(named) != 2) or len(set(map(str, named))) != len(named) \
                or any(n not in names | groups for n in named):
            _fail(path, 'must name distinct known parts or groups')
        if rule['rule'] == 'not_below' and not _number(rule['z'], -MAX_COORDINATE, MAX_COORDINATE):
            _fail(path + '/z', 'must be a level in metres')
    if 'avoid' in spec and (not isinstance(spec['avoid'], list) or any(not isinstance(text, str) or not text.strip() for text in spec['avoid'])):
        _fail('avoid', 'must be a list of sentences')
    if 'review_views' in spec:
        from .render import validate_views
        validate_views(spec['review_views'])
    own = _judge(spec, planned(spec))
    if own:
        raise ValueError('The spec breaks its own rules: ' + '; '.join(f'{f["path"]}: {f["message"]}' for f in own))
    return spec


def _box(low, high):
    return {'min': [round(v, 6) for v in low], 'max': [round(v, 6) for v in high]}


def planned(spec):
    """Each part as the spec places it: size and base in its yaw frame, and its world box."""
    measured = {}
    for part in spec['parts']:
        (x, y, z), (w, d, h) = part['position'], part['size']
        angle = math.radians(part.get('yaw', 0))
        half_x = (abs(math.cos(angle)) * w + abs(math.sin(angle)) * d) / 2
        half_y = (abs(math.sin(angle)) * w + abs(math.cos(angle)) * d) / 2
        measured[part['name']] = {'size': [w, d, h], 'base': [x, y, z], 'world': _box((x - half_x, y - half_y, z), (x + half_x, y + half_y, z + h))}
    return measured


def _groups(spec, measured):
    """Group boxes from their measured members; a group with an unmeasured member is unmeasured."""
    members = {}
    for part in spec['parts']:
        if 'group' in part:
            members.setdefault(part['group'], []).append(part['name'])
    result = {}
    for group, names in members.items():
        if all(n in measured for n in names):
            low = [min(measured[n]['world']['min'][a] for n in names) for a in range(3)]
            high = [max(measured[n]['world']['max'][a] for n in names) for a in range(3)]
            result[group] = {'size': [high[a] - low[a] for a in range(3)], 'base': [(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]],
                             'world': _box(low, high)}
    return result


def _measure(record, measure):
    size, base = record['size'], record['base']
    return {'width': size[0], 'depth': size[1], 'height': size[2], 'bottom': base[2], 'top': base[2] + size[2], 'x': base[0], 'y': base[1]}[measure]


def _judge(spec, measured):
    """Proportion and never findings from measured parts; a reference to an unmeasured part fails."""
    known = {**measured, **_groups(spec, measured)}
    findings = []

    def add(code, path, message, **values):
        findings.append({'code': code, 'path': path, 'message': message, **values, 'remediation': REMEDY[code]})

    def missing(names, path):
        absent = [n for n in names if n not in known]
        if absent:
            add('UNMEASURED', path, 'not measured: ' + ', '.join(absent))
        return bool(absent)

    for item in spec.get('proportions', []):
        path = f'proportions/{item["id"]}'
        references = [item['value']] if 'value' in item else item['ratio']
        if missing([r['part'] for r in references], path):
            continue
        values = [_measure(known[r['part']], r['measure']) for r in references]
        if len(values) == 2 and abs(values[1]) < 1e-9:
            add('PROPORTION', path, 'the ratio divides by zero', measured=None)
            continue
        value = values[0] if len(values) == 1 else values[0] / values[1]
        low = item['target'] - item['tolerance'] if 'target' in item else item.get('min', -math.inf)
        high = item['target'] + item['tolerance'] if 'target' in item else item.get('max', math.inf)
        if not low - 1e-9 <= value <= high + 1e-9:
            add('PROPORTION', path, f'measured {value:.4g}, allowed {low:.4g} to {high:.4g}', measured=round(value, 6),
                allowed=[None if math.isinf(v) else round(v, 6) for v in (low, high)])
    slack = 1e-6
    for rule in spec.get('never', []):
        path = f'never/{rule["id"]}'
        if rule['rule'] == 'no_overlap':
            if missing(rule['parts'], path):
                continue
            a, b = (known[n]['world'] for n in rule['parts'])
            depth = [min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) for i in range(3)]
            if min(depth) > slack:
                add('NEVER_OVERLAP', path, f'{rule["parts"][0]} and {rule["parts"][1]} interpenetrate by {min(depth):.4g} m', measured=round(min(depth), 6))
        elif rule['rule'] == 'not_below':
            if missing([rule['part']], path):
                continue
            bottom = known[rule['part']]['world']['min'][2]
            if bottom < rule['z'] - slack:
                add('NEVER_BELOW', path, f'{rule["part"]} reaches {bottom:.4g} m, below {rule["z"]:.4g} m', measured=round(bottom, 6))
        else:
            if missing([rule['part'], rule['footprint']], path):
                continue
            a, b = known[rule['part']]['world'], known[rule['footprint']]['world']
            outside = max(max(b['min'][i] - a['min'][i], a['max'][i] - b['max'][i]) for i in range(2))
            if outside > slack:
                add('NEVER_OUTSIDE', path, f'{rule["part"]} extends {outside:.4g} m outside {rule["footprint"]}', measured=round(outside, 6))
    return findings


def classify(spec, measurement):
    """Findings for a measured scene: missing parts, sizes, positions, proportions and never rules."""
    validate_spec(spec)
    if measurement.get('schema') != 'dcc.blockout.measurement.v1' or measurement.get('spec_digest') != digest(spec):
        raise ValueError('Measurement is missing or was made for another spec')
    tolerance = {**DEFAULT_TOLERANCE, **spec.get('tolerance', {})}
    findings, measured = [], {}
    for part in spec['parts']:
        name, record = part['name'], measurement['parts'].get(part['name'])
        path = f'parts/{name}'
        if not record or not record.get('objects'):
            findings.append({'code': 'PART_MISSING', 'path': path, 'message': 'no object matches ' + ', '.join(part.get('ids', [name])),
                             'remediation': REMEDY['PART_MISSING']})
            continue
        measured[name] = record
        allowed = [max(SIZE_FLOOR, tolerance['size'] * want) for want in part['size']]
        off = [round(got - want, 6) for got, want in zip(record['size'], part['size'])]
        if any(abs(delta) > limit + 1e-9 for delta, limit in zip(off, allowed)):
            findings.append({'code': 'SIZE', 'path': path + '/size', 'message': f'measured {[round(v, 4) for v in record["size"]]}, spec {part["size"]}',
                             'measured': record['size'], 'expected': part['size'], 'allowed': [round(v, 6) for v in allowed],
                             'remediation': REMEDY['SIZE']})
        shift = [round(got - want, 6) for got, want in zip(record['base'], part['position'])]
        if max(abs(v) for v in shift) > tolerance['position'] + 1e-9:
            findings.append({'code': 'POSITION', 'path': path + '/position', 'message': f'base centre is off by {shift} m',
                             'measured': record['base'], 'expected': part['position'], 'allowed': tolerance['position'],
                             'remediation': REMEDY['POSITION']})
    findings += _judge(spec, measured)
    by_code = {}
    for finding in findings:
        by_code[finding['code']] = by_code.get(finding['code'], 0) + 1
    return {'schema': 'dcc.blockout.report.v1', 'spec': spec['name'], 'spec_digest': digest(spec), 'passed': not findings, 'by_code': by_code,
            'parts_measured': len(measured), 'parts': len(spec['parts']), 'findings': findings, 'tolerance': tolerance,
            'not_measured': list(spec.get('avoid', [])), 'limits': LIMITS}


def relations(spec):
    """A dcc.relations.v1 definition from the parts' rests_on fields, or None when no part has one."""
    items = [{'id': 'rest.' + part['name'], 'kind': 'supported_by', 'subjects': [part['name']], 'support': [part['rests_on']], **CONTACT}
             for part in spec['parts'] if 'rests_on' in part]
    return {'schema': 'dcc.relations.v1', 'relations': items} if items else None


def check_file(path):
    spec = validate_spec(read_json(_plain(path)))
    categories = {}
    for part in spec['parts']:
        categories[part['category']] = categories.get(part['category'], 0) + 1
    return {'schema': 'dcc.blockout.check.v1', 'passed': True, 'spec': spec['name'], 'spec_digest': digest(spec), 'parts': len(spec['parts']),
            'by_category': categories, 'proportions': len(spec.get('proportions', [])), 'never': len(spec.get('never', [])),
            'supported_parts': sum('rests_on' in part for part in spec['parts']), 'review_views': 'review_views' in spec}


def _folder(out):
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def build_file(spec_path, output, out, blender, *, source=None):
    """Build the spec's parts into a new saved file, alone or added to a copy of source; neither input is changed."""
    spec = validate_spec(read_json(_plain(spec_path)))
    output = _plain(output)
    if output.suffix.lower() != '.blend' or output.exists():
        raise ValueError('Output must be a new .blend path')
    descriptor = None
    if source is not None:
        source = _plain(source)
        if source.suffix.lower() != '.blend' or not source.is_file():
            raise ValueError('Source must be an existing saved .blend file')
        descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    folder = _folder(out)
    run_worker(blender, folder, WORKER, 'build', {'spec': spec, 'spec_digest': digest(spec), 'source': descriptor,
                                                  'output': str(output.resolve()), 'out': str(folder.resolve())})
    if descriptor is not None and file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during the build; inspect retained outputs')
    receipt = read_json(folder / 'receipt.json')
    if receipt.get('spec_digest') != digest(spec) or not output.is_file() or file_hash(output) != receipt['output_sha256']:
        raise RuntimeError('Build receipt is not bound to the spec and the saved file')
    result = {'schema': 'dcc.blockout.build.v1', 'status': 'BUILT', 'passed': True, 'output': str(output), 'output_sha256': receipt['output_sha256'],
              'spec': spec['name'], 'spec_digest': receipt['spec_digest'], 'collection': receipt['collection'], 'parts': receipt['parts'],
              'replaced': receipt['replaced'], 'receipt': str(folder / 'receipt.json'), 'source': descriptor}
    supports = relations(spec)
    if supports is not None:
        write_json(folder / 'relations.json', supports)
        result['relations'] = str(folder / 'relations.json')
    return result


def compare_file(spec_path, source, out, blender):
    spec = validate_spec(read_json(_plain(spec_path)))
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    folder = _folder(out)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    parts = [{'name': p['name'], 'ids': p.get('ids', [p['name']]), 'yaw': p.get('yaw', 0)} for p in spec['parts']]
    run_worker(blender, folder, WORKER, 'measure', {'source': descriptor, 'parts': parts, 'spec_digest': digest(spec), 'out': str(folder.resolve())})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during measurement; inspect retained outputs')
    measurement = read_json(folder / 'measurement.json')
    if measurement.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Measurement is not bound to the source bytes')
    report = {**classify(spec, measurement), 'source': descriptor}
    write_json(folder / 'report.json', report)
    return {**report, 'report': str(folder / 'report.json'), 'artistic_acceptance': 'not_assessed'}

