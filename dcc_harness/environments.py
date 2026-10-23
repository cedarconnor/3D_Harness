"""Explicit immutable profiles; discovering providers never activates them."""
from pathlib import Path
import tempfile
import shutil

from . import blender_bridge, provider_sources
from .evidence import digest, file_hash, read_json, write_json
from .files import reject_links
from .native import run_worker


def inventory(binding=None, *, blender, roots=None, out=None):
    if binding is not None:
        descriptor = binding['descriptor'] if isinstance(binding, dict) else binding
        inputs = blender_bridge.call('addons_inventory', {}, binding=descriptor)
        if (not isinstance(inputs, dict) or set(inputs) != {'schema','roots','blender','enabled','operators'}
                or inputs['schema'] != 'dcc.addon.discovery.v1'):
            raise ValueError('Invalid live provider discovery envelope')
        return provider_sources.scan(inputs['roots'], inputs['blender'], enabled=inputs['enabled'], operators=inputs['operators'])
    if out is None:
        folder=Path(tempfile.mkdtemp(prefix='dcc-addon-inventory-'))
        try:
            run_worker(blender, folder, Path(__file__).with_name('_environment_blender.py'), 'inventory',
                       {'out':str(folder), 'roots':roots}, timeout=60)
            result=read_json(folder / 'inventory.json')
        except Exception as exc:
            raise RuntimeError('Inventory failed; native evidence retained at '+str(folder)) from exc
        target=reject_links(folder).resolve()
        if target.parent!=Path(tempfile.gettempdir()).resolve(): raise ValueError('Inventory temporary directory escaped its owner')
        shutil.rmtree(target)
        return result
    folder = Path(out)
    if out is not None:
        folder.mkdir(parents=True, exist_ok=False)
    run_worker(blender, folder, Path(__file__).with_name('_environment_blender.py'), 'inventory',
               {'out':str(folder), 'roots':roots}, timeout=60)
    return read_json(folder / 'inventory.json')


def create_profile(root, inventory, selected, preferences, *, reviews=None):
    profile = provider_sources.make_profile(inventory, selected, preferences, reviews=reviews)
    identity = digest(profile)
    path = reject_links(Path(root) / 'capabilities/profiles' / identity / 'profile.json')
    from .bootstrap import _rules_lock
    with _rules_lock(reject_links(path.with_suffix('.lock'))):
        if path.exists():
            if read_json(path) != profile:
                raise ValueError('Retained profile changed')
        else:
            write_json(path, profile)
    return {'path':str(path.resolve()), 'sha256':file_hash(path), 'digest':identity}


def load_profile(reference):
    return provider_sources.load_profile(reference)


validate_profile = provider_sources.validate_profile


def assert_worker_profile(request):
    """Called only inside Blender, before and after candidate loading/evaluation."""
    if 'profile' in request:
        from .data.bridge import addons
        return addons.assert_profile(load_profile(request['profile']))
    return None
