"""Import-free provider metadata and source pins, shared with the standalone bridge."""
import ast
import json
import os
from pathlib import Path
import re
import tomllib

from .evidence import digest, read_json
from .files import file_hash, reject_links

PROFILE_SCHEMA = 'dcc.environment.profile.v1'
SECRET = re.compile(r'password|secret|token|api.?key|license.?key|credential', re.I)
MODULE = re.compile(r'^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$')


def load_profile(reference):
    if not isinstance(reference, dict) or set(reference) != {'path','sha256','digest'}:
        raise ValueError('Explicit profile path and digests required')
    path = reject_links(reference['path'])
    if file_hash(path) != reference['sha256']: raise ValueError('Profile file changed')
    value = read_json(path)
    if digest(value) != reference['digest']: raise ValueError('Profile digest changed')
    return value


def source_files(path):
    path = reject_links(path).resolve(strict=True)
    def walk():
        if path.is_file():
            yield path
            return
        for folder, directories, names in os.walk(path, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in ('__pycache__', '.git'))
            for name in directories:
                reject_links(Path(folder) / name)
            for name in sorted(names):
                yield Path(folder) / name
    candidates = walk()
    files = {}; size = 0
    for item in candidates:
        relative = item.name if path.is_file() else item.relative_to(path).as_posix()
        if any(part in ('__pycache__', '.git') for part in Path(relative).parts):
            continue
        reject_links(item)
        if item.is_dir():
            continue
        if not item.is_file():
            raise ValueError('Unsupported provider source member')
        size += item.stat().st_size
        if len(files) >= 4096 or size > 256 * 1024 * 1024:
            raise ValueError('Provider source exceeds initial inventory coverage')
        files[relative] = file_hash(item)
    if not files:
        raise ValueError('Provider source is empty')
    return files


def _version(value):
    if isinstance(value, str):
        value = value.split('.')
    result = tuple(int(v) for v in value)
    if not 2 <= len(result) <= 3 or any(v < 0 for v in result):
        raise ValueError('Invalid Blender version')
    return result + (0,) * (3 - len(result))


def _metadata(path, kind):
    entry = path / '__init__.py' if path.is_dir() else path
    if entry.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Provider entry exceeds metadata coverage')
    if kind == 'extension':
        manifest = path / 'blender_manifest.toml'
        if manifest.stat().st_size > 256 * 1024:
            raise ValueError('Extension manifest exceeds metadata coverage')
        data = tomllib.loads(manifest.read_text(encoding='utf-8'))
        if data.get('type') != 'add-on' or data.get('id') != path.name:
            raise ValueError('Extension manifest does not identify this add-on')
        return {'name':data['name'], 'version':data['version'], 'blender':data['blender_version_min'],
                'blender_max':data.get('blender_version_max'),
                'dcc_harness':{'network':'required' if 'network' in data.get('permissions', {}) else 'unknown',
                               'dependencies':['wheel:' + str(name) for name in data.get('wheels', [])]}}
    tree = ast.parse(entry.read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict):
                return value
    raise ValueError('No static bl_info metadata')


def scan(roots, blender, *, enabled=None, operators=None):
    """Read files without importing disabled providers or evaluating their metadata."""
    enabled = enabled or {}; candidates = []; errors = []
    for root in roots:
        folder = reject_links(root['path']).resolve()
        namespace = root['namespace']
        if namespace and not MODULE.fullmatch(namespace):
            raise ValueError('Invalid provider namespace')
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.name.startswith('.') or path.name == '__pycache__':
                continue
            if not ((path.is_dir() and (path / '__init__.py').is_file())
                    or (not namespace and path.is_file() and path.suffix == '.py')):
                continue
            name = path.name if path.is_dir() else path.stem
            module = '.'.join(filter(None, (namespace, name)))
            if not MODULE.fullmatch(module):
                continue
            kind = 'extension' if namespace else 'legacy'
            entry = path / '__init__.py' if path.is_dir() else path
            base = {'id':module, 'module':module, 'path':str(path.resolve()), 'entry':str(entry.resolve()),
                    'kind':kind, 'installed':True, 'enabled':False, 'compatible':None,
                    'loaded_identity':'not_loaded', 'availability':'UNKNOWN', 'operators':[]}
            try:
                reject_links(path)
                meta = _metadata(path, kind); declared = meta.get('dcc_harness', {})
                if (not isinstance(declared, dict) or not isinstance(declared.get('preferences', {}), dict)
                        or declared.get('network', 'unknown') not in ('unknown', 'offline', 'required')
                        or not isinstance(declared.get('dependencies', []), list)
                        or any(not isinstance(d, str) for d in declared.get('dependencies', []))):
                    raise ValueError('Invalid static provider declarations')
                files = source_files(path)
                version = _version(blender['version']); minimum = _version(meta['blender'])
                maximum = _version(meta['blender_max']) if meta.get('blender_max') else None
                preferences = {key:kind for key, kind in declared.get('preferences', {}).items()
                               if isinstance(key, str) and not SECRET.search(key)
                               and kind in ('integer', 'number', 'boolean', 'string')}
                base.update(name=str(meta.get('name', name)), version=meta.get('version'), files=files,
                    source_digest=digest(files), compatible=version >= minimum and (maximum is None or version < maximum),
                    dependencies=list(declared.get('dependencies', [])), preferences=preferences,
                    network=declared.get('network', 'unknown'), license_required=bool(declared.get('license_required', False)))
                base['availability'] = 'AVAILABLE' if base['compatible'] else 'INCOMPATIBLE'
                loaded = enabled.get(module)
                if loaded:
                    if Path(loaded['path']).resolve() != entry.resolve():
                        base['availability'] = 'SHADOWED'
                    else:
                        base['enabled'] = True
                        pin = loaded.get('source_digest')
                        base['loaded_identity'] = ('unknown' if pin is None else
                                                   'matched' if pin == base['source_digest'] else 'stale')
            except (ValueError, OSError, SyntaxError, TypeError, KeyError, OverflowError) as exc:
                # Metadata is untrusted: do not echo values or provider exception text.
                errors.append({'provider':module, 'reason':type(exc).__name__, 'coverage':'metadata_or_source_unavailable'})
            candidates.append(base)
    grouped = {}
    for provider in candidates:
        grouped.setdefault(provider['id'], {})[provider['entry']] = provider
    providers = []
    for name, entries in sorted(grouped.items()):
        provider = next(iter(entries.values()))
        if len(entries) > 1:
            provider = {**provider, 'availability':'AMBIGUOUS', 'compatible':None,
                        'candidates':sorted(entries), 'loaded_identity':'unknown'}
        providers.append(provider)
    ownership = []
    for op in operators or []:
        owners = [p for p in providers if p['availability'] == 'AVAILABLE' and p['enabled']
                  and (op['module'] == p['module'] or op['module'].startswith(p['module'] + '.'))]
        owner = owners[0]['id'] if len(owners) == 1 else None
        ownership.append({'id':op['id'], 'provider':owner, 'ownership':'registered_class_module' if owner else 'unknown'})
        if owner:
            owners[0]['operators'].append(op['id'])
    return {'schema':'dcc.addon.inventory.v1', 'blender':blender, 'providers':providers, 'operators':ownership,
            'errors':errors, 'coverage':{'disabled_modules_imported':False, 'source_limit_bytes':256 * 1024 * 1024,
                                       'network_status':'provider_declaration_not_security_proof'}}


def make_profile(inventory, selected, preferences, *, reviews=None):
    if not isinstance(selected, list) or not selected or len(set(selected)) != len(selected):
        raise ValueError('Select distinct provider IDs explicitly')
    reviews = {} if reviews is None else reviews
    if not isinstance(reviews,dict) or set(reviews)-set(selected):
        raise ValueError('Source reviews must identify selected providers')
    if not isinstance(preferences, dict) or set(preferences) - set(selected):
        raise ValueError('Preferences must belong to selected providers')
    providers = []
    for name in sorted(selected):
        matches = [p for p in inventory['providers'] if p['id'] == name]
        if len(matches) != 1 or matches[0]['availability'] != 'AVAILABLE' or not matches[0]['compatible']:
            raise ValueError('Provider is unavailable, ambiguous or incompatible: ' + name)
        item = matches[0]
        if item['network'] == 'required' or item['license_required']:
            raise ValueError('Provider needs unavailable offline/license configuration: ' + name)
        if set(item['dependencies']) - set(selected):
            raise ValueError('Select every required provider dependency: ' + name)
        review=reviews.get(name)
        if item['network']=='unknown' or review is not None:
            if (not isinstance(review,dict) or set(review)!={'source_digest','reviewed_by','reason'}
                    or review['source_digest']!=item['source_digest']
                    or any(not isinstance(review[k],str) or not review[k].strip() for k in ('reviewed_by','reason'))):
                raise ValueError('Unknown network behavior requires a current source-bound local review: '+name)
        configured = preferences.get(name, {})
        if not isinstance(configured, dict):
            raise ValueError('Invalid provider preferences')
        for key, value in configured.items():
            if SECRET.search(key) or key not in item['preferences']:
                raise ValueError('Unknown or secret-bearing preference')
            kind = item['preferences'][key]
            valid = {'integer':type(value) is int, 'number':type(value) in (int, float),
                     'boolean':type(value) is bool, 'string':isinstance(value, str)}[kind]
            if not valid:
                raise ValueError('Wrong preference type')
        providers.append({key:item[key] for key in ('id', 'module', 'path', 'entry', 'kind', 'source_digest', 'files', 'dependencies')})
    profile = {'schema':PROFILE_SCHEMA, 'blender':{key:inventory['blender'][key] for key in ('version', 'build_hash')},
               'providers':providers, 'preferences':preferences, 'network_policy':'offline_qualification_required'}
    if reviews: profile['source_reviews']=reviews
    digest(profile)  # Reject non-finite values before retention.
    return profile


def validate_profile(profile, inventory):
    if (not isinstance(profile, dict) or set(profile)-{'source_reviews'} != {'schema','blender','providers','preferences','network_policy'}
            or profile['schema'] != PROFILE_SCHEMA or profile['network_policy'] != 'offline_qualification_required'):
        raise ValueError('Invalid environment profile schema')
    if profile['blender'] != {key:inventory['blender'][key] for key in ('version', 'build_hash')}:
        raise ValueError('Profile Blender build is incompatible')
    selected = [p['id'] for p in profile['providers']]
    current = make_profile(inventory, selected, profile['preferences'], reviews=profile.get('source_reviews'))
    if current != profile:
        raise ValueError('STALE profile: provider source or dependency changed')
    return profile
