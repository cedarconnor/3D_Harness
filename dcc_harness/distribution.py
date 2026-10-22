"""Versioned build rules and pinned bridge, identical in checkout and wheel."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from .files import reject_links, write_exclusive

DATA = Path(__file__).with_name('data')
SEEDS = ('docs/guides/MANAGED_EXECUTION.md', 'docs/guides/COMBINED_MCP.md')
BRIDGE_FILES = {
    'integrity.py': Path(__file__).with_name('bridge_integrity.py'),
    '__init__.py': DATA / 'bridge/__init__.py',
    'upstream.py': DATA / 'bridge/upstream.py',
    'LICENSE.upstream': DATA / 'bridge/LICENSE.upstream',
    'session.py': DATA / 'bridge/session.py',
    'inspection.py': DATA / 'bridge/inspection.py',
    'files.py': Path(__file__).with_name('files.py'),
    'identity.py': Path(__file__).with_name('identity.py'),
    'adoption_inventory_blender.py': Path(__file__).with_name('adoption_inventory_blender.py'),
    'attachment.py': DATA / 'bridge/attachment.py',
    'blender.py': Path(__file__).with_name('blender.py'),
    'continuity_blender.py': Path(__file__).with_name('continuity_blender.py'),
    'evidence.py': Path(__file__).with_name('evidence.py'),
    'observation_storage.py': Path(__file__).with_name('observation_storage.py'),
    'project.py': Path(__file__).with_name('project.py'),
    'uv_guard.py': Path(__file__).with_name('uv_guard.py'),
    'recipe_contracts.py': Path(__file__).with_name('live_recipes.py'),
    'operations.py': DATA / 'bridge/operations.py',
    'jobs.py': DATA / 'bridge/jobs.py',
    'recovery.py': DATA / 'bridge/recovery.py',
    'live_snapshot.py': Path(__file__).with_name('live_snapshot.py'),
    'node_asset_blender.py': Path(__file__).with_name('node_asset_blender.py'),
    'upstream.json': DATA / 'upstream.json',
}


def source_rules(repo):
    """Resolve local Markdown links recursively, preserving repository-relative paths."""
    repo = Path(repo).resolve()
    pending = [p for p in (repo / '.agents/skills').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    pending += [repo / name for name in SEEDS]
    result = {}
    external = []
    while pending:
        path = pending.pop().resolve()
        if not path.is_relative_to(repo):
            raise ValueError('Rule reference escapes repository: ' + str(path))
        name = path.relative_to(repo).as_posix()
        if name.startswith(('runs/', 'dist/', 'build/')):
            external.append(name)
            continue
        if name in result:
            continue
        if not path.is_file():
            raise ValueError('Missing rule reference: ' + name)
        result[name] = path.read_bytes()
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', result[name].decode('utf-8')):
                link = link.split('#', 1)[0].strip('<>')
                if not link or re.match(r'[a-zA-Z][\w+.-]*:', link) or link.startswith('/'):
                    continue
                target = (path.parent / link).resolve()
                is_external = target.is_relative_to(repo) and target.relative_to(repo).as_posix().startswith(('runs/', 'dist/', 'build/'))
                if target.is_dir() and not is_external:
                    pending.extend(target.glob('*.md'))
                else:
                    pending.append(target)
    result['EXTERNAL_EVIDENCE.json'] = (json.dumps({'not_bundled': sorted(set(external)),
        'reason': 'Historical local run evidence and previous builds are not part of the reusable rules distribution.'}, indent=2) + '\n').encode()
    return dict(sorted(result.items()))


def _rules():
    archive = DATA / 'rules.zip'
    if archive.is_file():
        with zipfile.ZipFile(archive) as bundle:
            return {name: bundle.read(name) for name in bundle.namelist()}
    return source_rules(Path(__file__).resolve().parents[1])


def catalog():
    from . import __version__
    return {'schema': 'dcc.rules.bundle.v1', 'version': __version__,
            'files': {name: hashlib.sha256(data).hexdigest() for name, data in _rules().items()}}


def read_rule(name):
    return read_rule_bytes(name).decode('utf-8')


def read_rule_bytes(name):
    rules = _rules()
    if name not in rules:
        raise ValueError('Unknown bundled rule: ' + name)
    return rules[name]


def _safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Invalid bundled path')
    return path


def export_rules(destination):
    target = reject_links(destination)
    rules = _rules()
    for name in rules:
        _safe_name(name)
    target.mkdir(parents=True, exist_ok=False)
    for name, data in rules.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_exclusive(path, data)
    write_exclusive(target / 'index.json', (json.dumps(catalog(), indent=2) + '\n').encode())
    return {'path': str(target), 'files': len(rules)}


def verify_rules(destination):
    target = reject_links(destination)
    expected = catalog()
    if json.loads((target / 'index.json').read_text(encoding='utf-8')) != expected:
        raise ValueError('Rules index changed or belongs to another runtime')
    for name, sha in expected['files'].items():
        data = reject_links(target / _safe_name(name)).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('Bundled rule changed: ' + name)
    return expected


def upstream():
    return json.loads((DATA / 'upstream.json').read_text(encoding='utf-8'))


def bridge_manifest():
    from .bridge_integrity import identity
    return identity({'schema': 'dcc.blender.bridge.manifest.v1',
                     'files': {name: hashlib.sha256(source.read_bytes()).hexdigest() for name, source in BRIDGE_FILES.items()}})


def verify_addon(path):
    from .bridge_integrity import verify_contents
    with zipfile.ZipFile(reject_links(path)) as archive:
        names = archive.namelist()
        prefix = 'dcc_harness_bridge/'
        if len(names) != len(set(names)) or any(not n.startswith(prefix) for n in names):
            raise ValueError('Invalid bridge archive members')
        contents = {name[len(prefix):]: archive.read(name) for name in names}
    return verify_contents(contents, bridge_manifest())


def export_addon(destination):
    meta = upstream()
    vendor = DATA / 'bridge'
    if hashlib.sha256((vendor / 'upstream.py').read_bytes()).hexdigest() != meta['addon_sha256']:
        raise ValueError('Pinned upstream add-on changed')
    stream = io.BytesIO()
    contents = {name: source.read_bytes() for name, source in BRIDGE_FILES.items()}
    manifest = {'schema': 'dcc.blender.bridge.manifest.v1',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}}
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name, data in contents.items():
            bundle.writestr('dcc_harness_bridge/' + name, data)
        bundle.writestr('dcc_harness_bridge/manifest.json', json.dumps(manifest, indent=2))
    target = reject_links(destination)
    write_exclusive(target, stream.getvalue())
    return {'path': str(target), 'sha256': hashlib.sha256(stream.getvalue()).hexdigest(), 'upstream': meta}
