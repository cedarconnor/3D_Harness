"""Explicit initial identity adoption in owned, fresh background Blender processes."""
from __future__ import annotations

from pathlib import Path

from .continuity import _plain
from .evidence import file_hash, read_json, write_json
from .native import run_worker


from .identity import plan_identities, validate_plan, verify_applied_plan


def _native(blender, folder, action, request):
    run_worker(blender, folder, Path(__file__).with_name('_adoption_blender.py'), action, request)


def preview(source, out, blender):
    source = _plain(source).resolve(strict=True)
    if source.suffix.lower() != '.blend':
        raise ValueError('Source must be a saved .blend file')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source), 'sha256': file_hash(source)}
    _native(blender, folder, 'preview', {'source': descriptor, 'out': str(folder)})
    plan = read_json(folder / 'plan.json')
    return {'status': plan['status'], 'passed': plan['status'] == 'READY',
            'plan': str(folder / 'plan.json'), 'assignments': len(plan['assignments']), 'issues': plan['issues']}


def apply(plan_path, out, blender):
    plan = read_json(_plain(plan_path))
    validate_plan(plan, plan['inventory'], plan['source'])
    source = _plain(plan['source']['path']).resolve(strict=True)
    if file_hash(source) != plan['source']['sha256']:
        raise ValueError('Source changed since preview; create a new preview')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder / 'plan.json', plan)
    _native(blender, folder, 'apply', {'plan': plan, 'out': str(folder)})
    # Observe in a separate process: a successful save is not saved-state evidence.
    checkpoint = folder / 'checkpoint.blend'
    _native(blender, folder, 'observe', {'source': {'path': str(checkpoint), 'sha256': file_hash(checkpoint)},
                                       'plan': plan, 'out': str(folder)})
    observation = read_json(folder / 'observation.json')
    if file_hash(source) != plan['source']['sha256']:
        raise RuntimeError('Source changed during adoption; inspect retained outputs')
    ready = not observation['issues'] and observation['native_dirty'] is False
    result = {'schema': 'dcc.identity-adoption.v1', 'status': 'READY_FOR_START' if ready else 'NEEDS_REPAIR',
              'passed': ready, 'source': plan['source'], 'source_unchanged': True,
              'plan_sha256': file_hash(folder / 'plan.json'), 'assignments': len(plan['assignments']),
              'saved_identities_verified': True,
              'checkpoint': str(checkpoint), 'checkpoint_sha256': observation['checkpoint_sha256'],
              'observation': str(folder / 'observation.json'), 'issues': observation['issues'],
              'artistic_acceptance': 'not_assessed'}
    write_json(folder / 'receipt.json', result)
    return result
