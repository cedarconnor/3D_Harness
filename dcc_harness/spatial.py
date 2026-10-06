"""Portable admission checks for explicitly sampled native visibility evidence."""
import math

from .evidence import canonical


def check_visibility(report, contract, observation):
    canonical(report); canonical(contract)
    if not isinstance(contract, dict) or set(contract) != {'schema', 'requirements'} or contract['schema'] != 'dcc.visibility.contract.v1':
        raise ValueError('Unsupported visibility contract')
    requirements = contract['requirements']
    if not isinstance(requirements, dict) or not requirements:
        raise ValueError('Visibility contract must have requirements')
    if (report.get('schema') != 'dcc.visibility.v1' or report.get('native_dirty') is not False or
            report.get('checkpoint_sha256') != observation['checkpoint_sha256'] or
            report.get('revision') != observation['revision'] or not isinstance(report.get('queries'), dict) or
            set(report['queries']) != set(requirements)):
        raise ValueError('Missing, stale or incompatible native visibility evidence')
    failures, results = [], {}
    for key, rule in requirements.items():
        if set(rule) != {'query', 'minimum_visible_fraction', 'minimum_target_samples'}:
            raise ValueError('Unknown visibility rule')
        query = rule['query']
        if set(query) != {'camera_id', 'target_ids', 'grid'}:
            raise ValueError('Unknown visibility query')
        camera, targets, grid = query['camera_id'], query['target_ids'], query['grid']
        if (camera not in observation['objects'] or observation['objects'][camera]['type'] != 'CAMERA' or
                not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or
                any(i not in observation['objects'] or observation['objects'][i]['type'] != 'MESH' for i in targets) or
                type(grid) is not int or not 8 <= grid <= 256):
            raise ValueError('Visibility requires observed camera/mesh identities and a supported grid')
        fraction, minimum = rule['minimum_visible_fraction'], rule['minimum_target_samples']
        if type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 <= fraction <= 1 or type(minimum) is not int or not 1 <= minimum <= grid * grid:
            raise ValueError('Invalid visibility threshold')
        measured = report['queries'][key]
        if any(measured.get(k) != v for k, v in query.items()):
            raise ValueError('Visibility query differs from the frozen requirement')
        total, visible = measured.get('target_samples'), measured.get('visible_samples')
        blockers = measured.get('blockers')
        if (type(total) is not int or type(visible) is not int or not 0 <= visible <= total <= grid * grid or
                not isinstance(blockers, dict) or any(i not in observation['objects'] or type(n) is not int or n <= 0 for i, n in blockers.items()) or
                sum(blockers.values()) != total - visible):
            raise ValueError('Invalid sampled visibility counts or blocker coverage')
        actual = visible / total if total else 0
        if measured.get('visible_fraction') != actual:
            raise ValueError('Visibility fraction does not match sample counts')
        passed = total >= minimum and actual >= fraction
        results[key] = {'passed': passed, 'visible_fraction': actual, 'target_samples': total,
                        'minimum_visible_fraction': fraction, 'minimum_target_samples': minimum}
        if not passed:
            failures.append(key)
    return {'schema': 'dcc.visibility.check.v1', 'passed': not failures, 'failures': failures,
            'revision': observation['revision'], 'results': results, 'limits': report.get('limits')}
