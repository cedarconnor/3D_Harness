"""Observe a saved .blend in an owned, fresh background Blender process; never saves.

The observation is saved-state evidence for start, begin-edit, finish-edit and
external revisions. It does not observe a live editor or certify visual quality.
"""
from __future__ import annotations

from pathlib import Path

from .continuity import _plain
from .evidence import file_hash, read_json, validate_observation
from .native import run_worker

WORKER = Path(__file__).with_name('_observe_blender.py')


def observe_file(source, out, blender, *, expanded=False):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    run_worker(blender, folder, WORKER, 'observe', {'source': descriptor, 'out': str(folder), 'compact': not expanded})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during observation; inspect retained outputs')
    path = folder / 'observation.json'
    observation = read_json(path)
    validate_observation(observation)
    if observation.get('checkpoint_sha256') != descriptor['sha256']:
        raise RuntimeError('Observation is not bound to the source bytes; inspect retained outputs')
    ready = not observation['issues'] and observation.get('native_dirty') is False
    return {'schema': 'dcc.observe.v1', 'status': 'READY' if ready else 'HAS_ISSUES', 'passed': ready,
            'source': descriptor, 'source_unchanged': True, 'observation': str(path),
            'checkpoint_sha256': observation['checkpoint_sha256'], 'revision': observation['revision'],
            'objects': len(observation['objects']), 'materials': len(observation['materials']),
            'issues': observation['issues'], 'coverage': observation['coverage'],
            'artistic_acceptance': 'not_assessed'}
