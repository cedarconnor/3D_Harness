"""Review and accept already-saved external edits without inventing a native dispatch."""
from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from .continuity import Continuity, _mapping, _plain, _sha
from .continuity_checks import evaluate_stage, validate_contract
from .evidence import file_hash, read_json, write_json
from .project import now
from .workflow import _clean_observation, _reservations, writer_guard


FILES = {'checkpoint.blend', 'observation.json', 'contract.json', 'handoff.md', 'updates.json', 'check.json'}


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


def _check_relocation_dependencies(obs):
    """Copying bytes cannot rebase native paths; restrict the dependencies we observe."""
    graphs = [m.get('graph') for m in obs['materials'].values()] + [obs['scene'].get('world')]
    for graph in graphs:
        for node in (graph or {}).get('nodes', []):
            image = node.get('image')
            if image is not None and image.get('packed') is not True:
                raise ValueError('Candidate relocation requires packed observed images; prepare an owned self-contained copy')

    def linked(value):
        if isinstance(value, dict):
            return bool(value.get('library')) or any(linked(v) for v in value.values())
        if isinstance(value, list):
            return any(linked(v) for v in value)
        return False

    if linked(obs['objects']):
        raise ValueError('Candidate relocation with observed linked libraries is not supported; prepare an owned local copy')


def preview_revision(root, expected_parent, checkpoint, observation, contract, handoff, updates, label, note, out):
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
    _check_relocation_dependencies(obs)
    rules = read_json(contract)
    validate_contract(rules)
    _text(sources['handoff.md'].read_text(encoding='utf-8'), 'Handoff')
    state = _ready_state(root)
    _check_parent(state, expected_parent, label)
    before = read_json(state['active']['observation'])
    check = evaluate_stage(before, obs, rules)
    out.mkdir(parents=True, exist_ok=False)
    for name, source in sources.items():
        with source.open('rb') as incoming, (out / name).open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        if file_hash(out / name) != hashes[name] or file_hash(source) != hashes[name]:
            raise ValueError('Revision input changed while freezing; inspect partial preview')
    if _clean_observation(out / 'observation.json', out / 'checkpoint.blend') != obs or read_json(out / 'contract.json') != rules:
        raise ValueError('Copied revision evidence differs from validated inputs')
    write_json(out / 'updates.json', updates)
    write_json(out / 'check.json', check)
    manifest = {'schema': 'dcc.external-revision.v1', 'created': now(), 'project': str(root),
                'project_sha256': file_hash(root / 'project.json'), 'expected_parent': expected_parent,
                'label': label, 'note': note, 'source_kind': 'external_saved_edit',
                'files': {name: file_hash(out / name) for name in sorted(FILES)}}
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
    if set(manifest['files']) != FILES or {p.name for p in preview.iterdir()} != FILES | {'manifest.json'}:
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
        _check_relocation_dependencies(obs)
        rules = read_json(preview / 'contract.json')
        updates = read_json(preview / 'updates.json')
        _mapping(updates, 'Decision updates')
        _text((preview / 'handoff.md').read_text(encoding='utf-8'), 'Handoff')
        check = evaluate_stage(read_json(state['active']['observation']), obs, rules)
        if check != read_json(preview / 'check.json'):
            raise ValueError('Revision checks differ from preview; prepare and review a new preview')
        if not check['passed']:
            return {'status': 'REJECTED_CONTRACT', 'passed': False, 'active': state['active'],
                    'failures': check['failures'], 'artistic_acceptance': 'not_evaluated'}
        check['external_revision'] = {'schema': 'dcc.external-revision.acceptance.v1',
            'preview_sha256': expected_preview_sha, 'preview_manifest': manifest, 'contract': rules,
            'review_note': review_note, 'reviewed_at': now(), 'review_attribution': 'caller_supplied',
            'native_execution': 'none; candidate was already saved before preview'}
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
