"""Review and accept already-saved external edits without inventing a native dispatch."""
from __future__ import annotations

import copy
from pathlib import Path
import uuid

from .continuity import Continuity, _mapping, _plain, _sha
from .continuity_checks import evaluate_stage, validate_contract
from .evidence import digest, file_hash, read_json, write_json
from .files import copy_verified
from .native import run_worker
from .observe import observe_file
from .project import now
from .uv_guard import evaluated_uv_noise_only
from .workflow import _clean_observation, _reservations, writer_guard


FILES = {'checkpoint.blend', 'observation.json', 'contract.json', 'handoff.md', 'updates.json', 'check.json'}
RELOCATION_FILES = {'relocation.json', 'candidate-observation.json'}
RELOCATE_WORKER = Path(__file__).with_name('_relocate_blender.py')


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be nonempty text')
    return value


def _ready_state(root, *, owns_lock=False):
    store = Continuity(root)
    state = store.status()
    if (not owns_lock and (store.root / 'workflow.lock').exists()) or state['pending'] or any(
            not (path / 'outcome.json').exists() for path, _ in _reservations(store.root)):
        raise RuntimeError('Unresolved workflow; inspect and reconcile before adopting an external revision')
    return state


def _check_parent(state, expected_parent, label):
    if state['active']['id'] != expected_parent:
        raise ValueError('Stale revision parent; resume and prepare a new preview')
    if label in {step['step_id'] for step in state['task_history']}:
        raise ValueError('Revision label has already been published')


def _images(obs):
    """Every observed image record in material graphs and the world, by image name."""
    graphs = [m.get('graph') for m in obs['materials'].values()] + [obs['scene'].get('world')]
    return [node['image'] for graph in graphs if isinstance(graph, dict) for node in graph.get('nodes', []) if node.get('image') is not None]


def _unpacked(obs):
    return {image.get('name'): image for image in _images(obs) if image.get('packed') is not True}


def _check_relocation_dependencies(obs, *, packing=False):
    """Copying bytes cannot rebase native paths: textures are packed into an owned copy, libraries refused."""
    if _unpacked(obs) and not packing:
        raise ValueError('Candidate relocation needs its unpacked textures packed: pass --blender to pack them into an owned copy, '
                         'or prepare a self-contained copy')

    def linked(value):
        if isinstance(value, dict):
            return bool(value.get('library')) or any(linked(v) for v in value.values())
        if isinstance(value, list):
            return any(linked(v) for v in value)
        return False

    if linked(obs['objects']):
        raise ValueError('Candidate relocation with observed linked libraries is not supported; prepare an owned local copy. '
                         'Packing a library would change the asset identity of its collections')


def _storage_neutral(obs, names):
    """The observation with only the storage of the named textures blanked: where they live, not what they are."""
    neutral = copy.deepcopy({k: obs[k] for k in ('objects', 'materials', 'scene', 'coverage', 'issues')})
    for image in _images(neutral):
        if image.get('name') in names:
            for key in ('path', 'packed', 'exists'):
                image.pop(key, None)
    return neutral


def _equivalent(candidate, owned, names):
    """Owned equals candidate apart from packing the named textures and qualified cross-process UV noise."""
    a, b = _storage_neutral(candidate, names), _storage_neutral(owned, names)
    objects_a, objects_b = a.pop('objects'), b.pop('objects')
    if a != b or objects_a.keys() != objects_b.keys() or any(
            objects_a[i] != objects_b[i] and not evaluated_uv_noise_only(objects_a[i], objects_b[i]) for i in objects_a):
        raise ValueError('The owned copy differs from the candidate beyond packing its textures; inspect the relocation folder')
    if any(image.get('packed') is not True for image in _images(owned) if image.get('name') in names):
        raise ValueError('A texture is still unpacked in the owned copy')


def _as_packed(before, owned, names):
    """The parent as if the same textures, matched by name and hash, were packed: storage is not a change."""
    stored = {image['name']: image for image in _images(owned) if image.get('name') in names}
    result = copy.deepcopy(before)
    for image in _images(result):
        match = stored.get(image.get('name'))
        if match is not None and image.get('sha256') == match.get('sha256'):
            image.update({key: match[key] for key in ('path', 'packed', 'exists') if key in match})
    result['revision'] = digest({k: result[k] for k in ('objects', 'materials', 'scene', 'coverage', 'issues')})
    return result


def _own(checkpoint, candidate, work, blender):
    """Pack the candidate's textures into a new owned copy in a fresh Blender, then observe it in another."""
    images = _unpacked(candidate)
    missing = sorted(name for name, image in images.items() if not image.get('exists') or not _sha(image.get('sha256')))
    if missing:
        raise ValueError('Missing texture: ' + ', '.join(missing))
    work.mkdir(parents=True, exist_ok=False)
    source = {'path': str(_plain(checkpoint).resolve()), 'sha256': file_hash(checkpoint)}
    target = work / 'owned.blend'
    run_worker(blender, work, RELOCATE_WORKER, 'pack', {'source': source, 'target': str(target),
                                                        'images': {name: image['sha256'] for name, image in images.items()}})
    observed = observe_file(target, work / 'observe', blender)
    if observed['status'] != 'READY':
        raise ValueError('The owned copy did not observe cleanly; inspect the relocation folder')
    owned = read_json(observed['observation'])
    _equivalent(candidate, owned, set(images))
    relocation = {'schema': 'dcc.revision.relocation.v1', 'source': source, 'owned_sha256': file_hash(target),
                  'packed_images': [{'name': name, 'sha256': image['sha256'], 'original_path': image.get('path')}
                                    for name, image in sorted(images.items())],
                  'equivalence': 'equal apart from texture storage and qualified evaluated-UV noise'}
    return target, Path(observed['observation']), relocation


def preview_revision(root, expected_parent, checkpoint, observation, contract, handoff, updates, label, note, out, blender=None):
    """Freeze a saved candidate and its complete review inputs; never advance the store."""
    root, out = (_plain(p).resolve() for p in (root, out))
    if out == root or root in out.parents:
        raise ValueError('Revision preview directory must be outside the project store')
    _text(label, 'Revision label')
    _text(note, 'External revision note')
    _mapping(updates, 'Decision updates')
    sources = {'checkpoint.blend': _plain(checkpoint), 'observation.json': _plain(observation),
               'contract.json': _plain(contract), 'handoff.md': _plain(handoff)}
    hashes = {name: file_hash(path) for name, path in sources.items()}
    obs = _clean_observation(observation, checkpoint)
    _check_relocation_dependencies(obs, packing=blender is not None)
    rules = read_json(contract)
    validate_contract(rules)
    _text(sources['handoff.md'].read_text(encoding='utf-8'), 'Handoff')
    state = _ready_state(root)
    _check_parent(state, expected_parent, label)
    before = read_json(state['active']['observation'])
    check = evaluate_stage(before, obs, rules)
    relocation = None
    if _unpacked(obs):
        # The contract judges the artist's candidate; the checkpoint is the owned copy with the textures packed.
        if out.exists():
            raise FileExistsError(str(out))
        owned, owned_observation, relocation = _own(checkpoint, obs, out.with_name(out.name + '-relocation'), blender)
        sources = {**sources, 'checkpoint.blend': owned, 'observation.json': owned_observation,
                   'candidate-observation.json': _plain(observation)}
        owned_obs = read_json(owned_observation)
        check = evaluate_stage(_as_packed(before, owned_obs, set(_unpacked(obs))), owned_obs, rules)
        hashes = {name: file_hash(path) for name, path in sources.items()}
    out.mkdir(parents=True, exist_ok=False)
    for name, source in sources.items():
        copy_verified(source, out / name, hashes[name], 'Revision input changed while freezing; inspect partial preview')
    frozen = read_json(out / 'candidate-observation.json') if relocation else _clean_observation(out / 'observation.json', out / 'checkpoint.blend')
    if frozen != obs or read_json(out / 'contract.json') != rules:
        raise ValueError('Copied revision evidence differs from validated inputs')
    if relocation:
        _clean_observation(out / 'observation.json', out / 'checkpoint.blend')
        write_json(out / 'relocation.json', relocation)
    write_json(out / 'updates.json', updates)
    write_json(out / 'check.json', check)
    manifest = {'schema': 'dcc.external-revision.v1', 'created': now(), 'project': str(root),
                'project_sha256': file_hash(root / 'project.json'), 'expected_parent': expected_parent,
                'label': label, 'note': note, 'source_kind': 'external_saved_edit',
                'files': {name: file_hash(out / name) for name in sorted(FILES | (RELOCATION_FILES if relocation else set()))}}
    # The final marker distinguishes a complete preview from a failed partial copy.
    write_json(out / 'manifest.json', manifest)
    changes = check['preservation']['changes']
    changed_materials = sorted({c['id'] for c in changes if c['category'] == 'materials'})
    users = {mid: {phase: sorted(iid for iid, obj in observed['objects'].items() if mid in obj['material_ids'])
                   for phase, observed in [('before', before), ('after', obs)]} for mid in changed_materials}
    return {'schema': 'dcc.revision-preview.v1', 'status': 'READY_FOR_REVIEW' if check['passed'] else 'REJECTED_CONTRACT',
            'passed': check['passed'], 'preview': str(out), 'preview_sha256': file_hash(out / 'manifest.json'),
            'expected_parent': expected_parent, 'changes': changes, 'changed_material_users': users,
            'failures': check['failures'], 'check': str(out / 'check.json'), 'artistic_acceptance': 'not_evaluated'}


def _load_preview(root, preview, expected_sha):
    root, preview = (_plain(p).resolve() for p in (root, preview))
    manifest_path = _plain(preview / 'manifest.json')
    if not _sha(expected_sha) or file_hash(manifest_path) != expected_sha:
        raise ValueError('Revision preview hash differs; inspect the intended frozen preview')
    manifest = read_json(manifest_path)
    if (manifest.get('schema') != 'dcc.external-revision.v1' or
            manifest.get('source_kind') != 'external_saved_edit' or
            Path(manifest['project']) != root or manifest['project_sha256'] != file_hash(root / 'project.json')):
        raise ValueError('Revision preview belongs to another project or unsupported schema')
    expected = FILES | (RELOCATION_FILES if 'relocation.json' in manifest['files'] else set())
    if set(manifest['files']) != expected or {p.name for p in preview.iterdir()} != expected | {'manifest.json'}:
        raise ValueError('Revision preview inventory differs or is incomplete')
    for name, sha in manifest['files'].items():
        if not _sha(sha) or file_hash(_plain(preview / name)) != sha:
            raise ValueError('Frozen revision input changed: ' + name)
    _text(manifest['label'], 'Revision label')
    _text(manifest['note'], 'External revision note')
    return manifest


def accept_revision(root, preview, expected_preview_sha, review_note):
    """Recheck a frozen proposal, publish once, or report an already committed result."""
    _text(review_note, 'Review note')
    root, preview = (_plain(p).resolve() for p in (root, preview))
    with writer_guard(root):
        manifest = _load_preview(root, preview, expected_preview_sha)
        state = _ready_state(root, owns_lock=True)
        # Lost acknowledgement needs inspection of committed history, never a second publish.
        for step in state['task_history']:
            if not step['check_report']:
                continue
            previous = read_json(step['check_report']).get('external_revision', {})
            if (previous.get('preview_sha256') == expected_preview_sha and
                    step['checkpoint_sha256'] == manifest['files']['checkpoint.blend']):
                return {'status': 'ALREADY_PUBLISHED', 'passed': True, 'accepted': step,
                        'active': state['active'], 'review_note': previous['review_note'],
                        'artistic_acceptance': 'caller_review_recorded_not_authenticated'}
        _check_parent(state, manifest['expected_parent'], manifest['label'])
        obs = _clean_observation(preview / 'observation.json', preview / 'checkpoint.blend')
        relocation = read_json(preview / 'relocation.json') if 'relocation.json' in manifest['files'] else None
        if relocation:
            # Re-prove the packing, then judge the contract on the artist's candidate as frozen.
            candidate = read_json(preview / 'candidate-observation.json')
            names = {image['name'] for image in relocation['packed_images']}
            if (candidate.get('checkpoint_sha256') != relocation['source']['sha256'] or set(_unpacked(candidate)) != names
                    or relocation['owned_sha256'] != manifest['files']['checkpoint.blend']):
                raise ValueError('Relocation record differs from the frozen candidate; prepare a new preview')
            _equivalent(candidate, obs, names)
        _check_relocation_dependencies(obs)
        rules = read_json(preview / 'contract.json')
        updates = read_json(preview / 'updates.json')
        _mapping(updates, 'Decision updates')
        _text((preview / 'handoff.md').read_text(encoding='utf-8'), 'Handoff')
        parent = read_json(state['active']['observation'])
        check = evaluate_stage(_as_packed(parent, obs, names) if relocation else parent, obs, rules)
        if check != read_json(preview / 'check.json'):
            raise ValueError('Revision checks differ from preview; prepare and review a new preview')
        if not check['passed']:
            return {'status': 'REJECTED_CONTRACT', 'passed': False, 'active': state['active'],
                    'failures': check['failures'], 'artistic_acceptance': 'not_evaluated'}
        check['external_revision'] = {'schema': 'dcc.external-revision.acceptance.v1',
            'preview_sha256': expected_preview_sha, 'preview_manifest': manifest, 'contract': rules,
            'review_note': review_note, 'reviewed_at': now(), 'review_attribution': 'caller_supplied',
            'native_execution': 'none; candidate was already saved before preview'}
        if relocation:
            check['external_revision']['relocation'] = relocation
        # Keep this report outside the frozen preview. It becomes part of the immutable bundle.
        # A failed publication may leave the report or a partial bundle; never erase either.
        check_path = root / 'reports' / ('external-revision-' + str(uuid.uuid4()) + '.json')
        write_json(check_path, check)
        _load_preview(root, preview, expected_preview_sha)
        published = Continuity(root).publish(manifest['label'], manifest['expected_parent'],
            preview / 'checkpoint.blend', preview / 'observation.json', preview / 'handoff.md', updates, check_path)
        return {'status': 'PUBLISHED', 'passed': True, 'accepted': published['active'],
                'active': published['active'], 'review_note': review_note,
                'artistic_acceptance': 'caller_review_recorded_not_authenticated'}
