"""GLB delivery receipt: export a saved file, import the result into an empty scene, and compare.

Each step runs in its own fresh background Blender; the source is never saved. Objects are matched
by stable ID, carried through glTF extras. The receipt binds the source (and, with a project, the
checkpoint it equals), the GLB's hash, the exporter and the findings. It shows that the file holds
what was exported, not that it looks right in another application.
"""
from __future__ import annotations

from pathlib import Path

from .continuity import Continuity, _plain
from .evidence import file_hash, read_json, write_json
from .native import run_worker
from .project import now

WORKER = Path(__file__).with_name('_delivery_blender.py')
SCHEMA = 'dcc.delivery.glb.v1'
LIMITS = ('Objects, triangle counts, world bounds and material names after a fresh import. Not textures, shading, '
          'animation, collection-instance identity or how another application renders the file.')


def _tolerance(bounds):
    size = max(abs(bounds[1][i] - bounds[0][i]) for i in range(3))
    return 0.001 + 0.001 * size


def _instance_content(exported, imported):
    """Imported objects that stand for a collection instance: its root and what the exporter wrote beneath it.

    Instances are not compared, so their contents are set aside on this side too. An object the source
    itself parented beneath the instance is still compared.
    """
    roots = {item['id'] for item in exported.get('not_exported', []) if item.get('instance')}
    placed = {(item['id'], tuple(a for a in item.get('ancestors', []) if a in roots)) for item in exported['objects']}
    return [item for item in imported['objects'] if item['id'] in roots or (
        set(item.get('ancestors', [])) & roots and (item['id'], tuple(a for a in item['ancestors'] if a in roots)) not in placed)]


def compare(exported, imported):
    """Match exported and imported objects by stable ID and list every difference."""
    findings, after = [], {}
    skipped = _instance_content(exported, imported)
    excluded = {id(item) for item in skipped}
    for item in imported['objects']:
        if id(item) in excluded:
            continue
        if item['id'] in after:
            findings.append({'id': item['id'], 'code': 'DUPLICATE', 'detail': 'More than one imported object has this ID'})
        after[item['id']] = item
    matched = 0
    for item in exported['objects']:
        other = after.pop(item['id'], None)
        if other is None:
            findings.append({'id': item['id'], 'code': 'MISSING', 'detail': 'Exported but absent after import'})
            continue
        matched += 1
        if other['triangles'] != item['triangles']:
            findings.append({'id': item['id'], 'code': 'TRIANGLES', 'detail': f"{item['triangles']} exported, {other['triangles']} imported"})
        moved = max(abs(other['bounds'][e][i] - item['bounds'][e][i]) for e in (0, 1) for i in range(3))
        if moved > _tolerance(item['bounds']):
            findings.append({'id': item['id'], 'code': 'BOUNDS', 'detail': f'World bounds moved up to {moved:.6f} m'})
        if sorted(other['materials']) != sorted(item['materials']):
            findings.append({'id': item['id'], 'code': 'MATERIALS', 'detail': f"{item['materials']} exported, {other['materials']} imported"})
    findings += [{'id': iid, 'code': 'EXTRA', 'detail': 'Imported with no exported counterpart'} for iid in sorted(after)]
    return {'passed': not findings, 'matched': matched, 'findings': findings, 'not_exported': exported.get('not_exported', []),
            'instance_content': sorted(item['id'] for item in skipped)}


def checkpoint_for(project, source):
    """The project checkpoint this file is byte-identical to; anything else is refused."""
    sha = file_hash(_plain(source))
    status = Continuity(project).status()
    entry = next((e for e in reversed(status['task_history']) if e['checkpoint_sha256'] == sha), None)
    if entry is None:
        raise ValueError('The source is not a checkpoint of this project; deliver an accepted checkpoint')
    return {'checkpoint_id': entry['id'], 'checkpoint_sha256': sha, 'sequence': entry['sequence'],
            'active': entry['id'] == status['active']['id']}


def deliver(source, out, blender, *, project=None):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    checkpoint = checkpoint_for(project, source) if project is not None else None
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    run_worker(blender, folder, WORKER, 'export', {'source': descriptor, 'out': str(folder.resolve())})
    if file_hash(source) != descriptor['sha256']:
        raise RuntimeError('Source changed during export; inspect retained outputs')
    exported = read_json(folder / 'export.json')
    if exported.get('source_sha256') != descriptor['sha256']:
        raise RuntimeError('Export record is not bound to the source bytes')
    glb = folder / 'delivery.glb'
    glb_ref = {'path': 'delivery.glb', 'sha256': file_hash(glb), 'bytes': glb.stat().st_size}
    imported_folder = folder / 'reimport'
    imported_folder.mkdir()
    run_worker(blender, imported_folder, WORKER, 'reimport', {'glb': str(glb.resolve()), 'glb_sha256': glb_ref['sha256'],
                                                              'out': str(imported_folder.resolve())})
    comparison = compare(exported, read_json(imported_folder / 'import.json'))
    receipt = {'schema': SCHEMA, 'created': now(), 'source': descriptor, 'checkpoint': checkpoint, 'glb': glb_ref,
               'blender': exported.get('blender'), 'exporter': exported.get('exporter'), 'settings': exported.get('settings'),
               'comparison': comparison, 'passed': comparison['passed'], 'limits': LIMITS}
    write_json(folder / 'receipt.json', receipt)
    return {**receipt, 'receipt': str(folder / 'receipt.json'), 'artistic_acceptance': 'not_assessed'}
