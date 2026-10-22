"""Content-addressed bundles; safe to inspect without executing provider/adapter code."""
import ast
from pathlib import Path, PurePosixPath

from .evidence import digest, read_json, write_json
from .files import file_hash, reject_links, copy_verified
from .recipe_schema import validate, identifier, sha

PROTOCOL = {'preflight':2, 'apply':3, 'inspect_output':2, 'verify_saved':2}


def bundle_path(root, recipe_id, identity):
    return reject_links(Path(root) / 'capabilities/recipes' / identifier(recipe_id) / sha(identity))


def draft(root, value, adapter_path, assets):
    value = validate(value)
    adapter = reject_links(adapter_path).resolve(strict=True)
    if adapter.stat().st_size > 1024 * 1024: raise ValueError('Adapter source exceeds coverage')
    tree = ast.parse(adapter.read_text(encoding='utf-8-sig'))
    functions = {node.name:node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if any(name not in functions or len(functions[name].args.args) != count for name,count in PROTOCOL.items()):
        raise ValueError('Adapter protocol requires preflight, apply and both validators')
    sources = {'adapter.py':adapter}
    if not isinstance(assets,list) or len(assets) > 64: raise ValueError('Explicit bounded assets list required')
    size = adapter.stat().st_size
    for asset in assets:
        path = reject_links(asset).resolve(strict=True); identifier(path.name)
        name = 'assets/' + path.name
        if name.casefold() in {key.casefold() for key in sources}: raise ValueError('Duplicate asset name')
        if not path.is_file(): raise ValueError('Recipe asset must be a regular file')
        size += path.stat().st_size
        if size > 256 * 1024 * 1024: raise ValueError('Recipe assets exceed coverage')
        sources[name] = path
    manifest = {'schema':'dcc.capability.bundle.v1', 'recipe':value,
                'files':{name:file_hash(path) for name,path in sources.items()}}
    identity = digest(manifest); folder = bundle_path(root, value['id'], identity)
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=False)
        for name,path in sources.items(): copy_verified(path, folder / name, manifest['files'][name], 'Recipe input changed during retention')
        write_json(folder / 'bundle.json', manifest)
    load(root, value['id'], identity)
    return {'id':value['id'], 'digest':identity, 'state':'DRAFT'}


def load(root, recipe_id, identity):
    folder = bundle_path(root, recipe_id, identity)
    manifest = read_json(reject_links(folder / 'bundle.json'))
    if (set(manifest) != {'schema','recipe','files'} or manifest['schema'] != 'dcc.capability.bundle.v1'
            or digest(manifest) != identity or manifest['recipe']['id'] != recipe_id):
        raise ValueError('Recipe bundle changed')
    validate(manifest['recipe'])
    files = manifest['files']
    if not isinstance(files,dict) or 'adapter.py' not in files: raise ValueError('Missing adapter')
    for name,wanted in files.items():
        parts = PurePosixPath(name).parts
        if name != 'adapter.py' and (len(parts) != 2 or parts[0] != 'assets' or identifier(parts[1]) != parts[1]):
            raise ValueError('Invalid retained bundle member')
        if '\\' in name or file_hash(reject_links(folder / name)) != sha(wanted):
            raise ValueError('Recipe member changed')
    actual = set()
    for path in folder.rglob('*'):
        reject_links(path)
        if path.is_file(): actual.add(path.relative_to(folder).as_posix())
        elif path.relative_to(folder).as_posix() != 'assets': raise ValueError('Unexpected bundle members')
    if actual != set(files) | {'bundle.json'}: raise ValueError('Recipe bundle members changed')
    return {'state':'DRAFT', 'recipe':manifest['recipe'], 'digest':identity,
            'adapter':str(folder / 'adapter.py'), 'assets':{Path(name).name:str(folder / name)
                for name in files if name.startswith('assets/')}, 'manifest':manifest}
