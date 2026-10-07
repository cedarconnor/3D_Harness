"""Supported evidence for feedback and stages; producer claims remain attributed."""
from pathlib import PurePosixPath

from .coordination import fields, text
from .continuity import _load_observation, _sha
from .continuity_checks import evaluate_stage
from .evidence import read_json, digest


KINDS = {'native_contract', 'whole_scene_render', 'detail_render', 'visual_review',
         'direction_record', 'shared_user_report', 'dependency_report', 'native_reopen',
         'feedback_reconciliation', 'handoff'}


def actor(value):
    fields(value, {'role', 'author', 'reference'})
    if value['role'] not in ('agent', 'artist'):
        raise ValueError('Unknown reviewer role')
    text(value['author']); text(value['reference'])
    return value


def render(ctx, value, checkpoint):
    fields(value, {'receipt', 'view_id', 'settings'})
    receipt_path = ctx.artifact(value['receipt'])
    receipt = read_json(receipt_path)
    fields(receipt, {'schema', 'checkpoint_sha256', 'views_digest', 'images'})
    if (receipt['schema'] != 'dcc.quality.renders.v1' or
            receipt['checkpoint_sha256'] != checkpoint['checkpoint_sha256'] or
            not _sha(receipt['views_digest']) or not isinstance(receipt['images'], dict) or
            value['view_id'] not in receipt['images']):
        raise ValueError('Stale or invalid render receipt/view')
    settings = read_json(ctx.artifact(value['settings']))
    if not isinstance(settings, dict) or not settings or digest(settings) != receipt['views_digest']:
        raise ValueError('Render settings are missing or differ from the receipt digest')
    parent = PurePosixPath(value['receipt']['path']).parent
    images = {}
    for view, image in receipt['images'].items():
        text(view); fields(image, {'path', 'sha256'})
        # Validate the raw path too: joining must not normalize away traversal.
        from .coordination import relative
        relative(receipt_path.parent, image['path'])
        ref = {'path': (parent / image['path']).as_posix(), 'sha256': image['sha256']}
        ctx.artifact(ref)
        images[view] = ref
    return {'view_id': value['view_id'], 'image': images[value['view_id']],
            'views_digest': receipt['views_digest'], 'receipt': value['receipt'], 'settings': value['settings']}


def validate(ctx, items, checkpoint, *, feedback_check=None):
    if not isinstance(items, list):
        raise ValueError('Evidence must be a list')
    entry = ctx.checkpoint(checkpoint)
    observed = read_json(entry['observation'])
    results = []
    for item in items:
        if not isinstance(item, dict) or item.get('kind') not in KINDS:
            raise ValueError('Unknown evidence kind')
        kind = item['kind']
        result = {'kind': kind, 'passed': True}
        if kind == 'native_contract':
            fields(item, {'kind', 'before', 'contract'})
            before = ctx.checkpoint(item['before'])
            if before['sequence'] > entry['sequence']:
                raise ValueError('Contract baseline is newer than result')
            contract = read_json(ctx.artifact(item['contract']))
            result['report'] = evaluate_stage(read_json(before['observation']), observed, contract)
            result['passed'] = result['report']['passed']
            result['targets'] = list(contract['spec']['required'])
            result['materials'] = sorted(set(contract['spec'].get('required_materials', [])) |
                                         set(contract['spec'].get('material_nodes', {})))
        elif kind in ('whole_scene_render', 'detail_render'):
            fields(item, {'kind', 'render'})
            result.update(render(ctx, item['render'], checkpoint))
        elif kind == 'native_reopen':
            fields(item, {'kind', 'observation', 'producer'})
            actor(item['producer'])
            fresh = _load_observation(ctx.artifact(item['observation']), entry['checkpoint'])
            if fresh.get('native_dirty') is not False:
                raise ValueError('Reopen observation must be saved and clean')
            # Recompute preservation with the qualified comparator, not strict float equality.
            required = next(iter(observed['objects']))
            result['report'] = evaluate_stage(observed, fresh, {'schema': 'dcc.continuity.contract.v1',
                'spec': {'schema': 'dcc.spec.v1', 'required': {required: {}}}, 'allowed_new_prefixes': []})
            result['passed'] = result['report']['passed']
            result['producer'] = item['producer']
        elif kind == 'shared_user_report':
            fields(item, {'kind'})
            result['materials'] = {mid: sorted(i for i, o in observed['objects'].items() if mid in o['material_ids'])
                                   for mid in observed['materials']}
        elif kind == 'dependency_report':
            fields(item, {'kind'})
            result['issues'] = observed['issues']
            result['coverage'] = observed['coverage']
            result['limit'] = 'Observed dependencies only; not a portable-asset completeness certificate'
            result['passed'] = not observed['issues']
        elif kind == 'feedback_reconciliation':
            fields(item, {'kind'})
            if feedback_check is None:
                raise ValueError('Feedback reconciliation requires a stage context')
            result['unresolved'] = feedback_check()
            result['passed'] = not result['unresolved']
        elif kind in ('direction_record', 'handoff'):
            fields(item, {'kind', 'file'})
            text(ctx.artifact(item['file']).read_text(encoding='utf-8'))
        elif kind == 'visual_review':
            fields(item, {'kind', 'reviewer', 'verdict', 'finding', 'views'})
            actor(item['reviewer']); text(item['finding'])
            if item['verdict'] not in ('pass', 'fail', 'uncertain') or not isinstance(item['views'], list) or not item['views']:
                raise ValueError('Visual review requires a verdict and inspected views')
            result.update({k: item[k] for k in ('reviewer', 'verdict', 'finding', 'views')})
            result['passed'] = item['verdict'] == 'pass'
        results.append(result)
    views = {r['view_id'] for r in results if 'view_id' in r}
    for result in results:
        if result['kind'] == 'visual_review' and not set(result['views']) <= views:
            raise ValueError('Visual review references an unbound image/view')
    return results
