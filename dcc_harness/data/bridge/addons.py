"""Explicit source-pinned provider activation; inventory never imports providers."""
import hashlib
import functools
import importlib.abc
import importlib.machinery
from pathlib import Path
import sys
from contextlib import contextmanager

import bpy
import addon_utils
try:
    from . import provider_sources
    from .evidence import digest
    from .files import file_hash, reject_links
    from .offline import scope
except ImportError:
    from dcc_harness import provider_sources
    from dcc_harness.evidence import digest
    from dcc_harness.files import file_hash, reject_links
    from dcc_harness.offline import scope

PINS = {}
ACTIVE_PROFILE = None
ACTIVE_CONFIGURATION = None
LAST_ACTIVATION = None
NETWORK_ATTEMPTS = []


@contextmanager
def session_preferences(profile=None, *, activate=True):
    """Apply configured preferences only within synchronous provider execution.

    Blender autosave cannot observe temporary entries between timer ticks. Restore
    existing values, newly created entries/repos and the user's autosave setting.
    This is lifecycle containment, not a sandbox against malicious provider code.
    """
    prefs=bpy.context.preferences
    auto=prefs.use_preferences_save
    entries={entry.module for entry in prefs.addons}
    repos={repo.module for repo in prefs.extensions.repos}
    previous=[]
    configured=(profile or ACTIVE_CONFIGURATION or {}).get('preferences',{})
    prefs.use_preferences_save=False
    try:
        if activate and ACTIVE_CONFIGURATION:
            provider_sources.validate_profile(ACTIVE_CONFIGURATION,inventory(roots_for(ACTIVE_CONFIGURATION)))
            for pin in ACTIVE_CONFIGURATION['providers']:
                name=pin['module']
                if not name.startswith('bl_ext.'): continue
                if PINS.get(name)!=pin: raise ValueError('Extension activation has no verified source pin')
                repo_name=name.split('.')[1]
                expected=str(Path(pin['path']).parent)
                found=[r for r in prefs.extensions.repos if r.module==repo_name]
                if not found:
                    prefs.extensions.repos.new(name='Harness profile '+repo_name,module=repo_name,custom_directory=expected,remote_url='')
                elif len(found)!=1 or str(Path(found[0].directory).resolve())!=expected:
                    raise ValueError('Profile extension repository changed')
                if not getattr(sys.modules.get(name),'__addon_enabled__',False):
                    failures=[]
                    module=addon_utils.enable(name,default_set=False,persistent=True,handle_error=lambda error:failures.append(type(error).__name__))
                    if module is None or failures: raise ValueError('Session extension activation failed')
        for name,values in configured.items():
            entry=prefs.addons.get(name)
            if not activate and (entry is None or entry.preferences is None): continue
            if entry is None:
                entry=prefs.addons.new(); entry.module=name
            for key,value in values.items():
                previous.append((entry.preferences,key,getattr(entry.preferences,key)))
                if activate: setattr(entry.preferences,key,value)
        yield
    finally:
        for owner,key,value in reversed(previous): setattr(owner,key,value)
        for entry in list(prefs.addons):
            if entry.module not in entries: prefs.addons.remove(entry)
        for repo in list(prefs.extensions.repos):
            if repo.module not in repos: prefs.extensions.repos.remove(repo)
        prefs.use_preferences_save=auto


def offline_call(function):
    @functools.wraps(function)
    def bounded(*args, **kwargs):
        enabling=function.__name__=='enable_profile'
        with scope(NETWORK_ATTEMPTS), session_preferences(args[0] if enabling else None,activate=not enabling):
            return function(*args, **kwargs)
    return bounded


def build():
    value = bpy.app.build_hash
    return {'version':list(bpy.app.version), 'build_hash':value.decode() if isinstance(value, bytes) else str(value),
            'background':bpy.app.background}


def roots_for(profile):
    return [{'path':str(Path(p['path']).parent), 'namespace':p['module'].rpartition('.')[0]}
            for p in profile['providers']]


def inventory_inputs(roots=None):
    enabled = {}
    for name, module in tuple(sys.modules.items()):
        if module is None:
            continue
        namespace = vars(module) if hasattr(module, '__dict__') else {}
        if namespace.get('__addon_enabled__') and namespace.get('__file__'):
            enabled[name] = {'path':namespace['__file__'], 'source_digest':PINS.get(name, {}).get('source_digest')}
    if roots is None:
        roots = [{'path':path, 'namespace':''} for path in addon_utils.paths()]
        roots += [{'path':repo.directory, 'namespace':'bl_ext.' + repo.module}
                  for repo in bpy.context.preferences.extensions.repos if repo.enabled]
        roots += [{'path':str(Path(item['path']).parent.parent if Path(item['path']).name == '__init__.py'
                                   else Path(item['path']).parent), 'namespace':name.rpartition('.')[0]}
                  for name, item in enabled.items()]
    operators = []
    for category in dir(bpy.ops):
        if category.startswith('_'):
            continue
        group = getattr(bpy.ops, category)
        for name in dir(group):
            if name.startswith('_'):
                continue
            try:
                rna = getattr(group, name).get_rna_type()
                cls = bpy.types.Operator.bl_rna_get_subclass_py(rna.identifier)
                if cls:
                    operators.append({'id':category + '.' + name, 'module':cls.__module__})
            except (AttributeError, RuntimeError):
                continue
    return {'schema':'dcc.addon.discovery.v1', 'roots':roots, 'blender':build(),
            'enabled':enabled, 'operators':operators}


def inventory(roots=None):
    inputs = inventory_inputs(roots)
    return provider_sources.scan(inputs['roots'], inputs['blender'], enabled=inputs['enabled'], operators=inputs['operators'])


class SourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, name, path, pin):
        super().__init__(name, path); self.pin = pin

    def get_code(self, fullname):
        path = reject_links(self.path).resolve()
        root = Path(self.pin['path'])
        relative = path.name if root.is_file() and path == root else path.relative_to(root).as_posix()
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != self.pin['files'].get(relative):
            raise ValueError('Provider source changed before import')
        # Do not execute a stale timestamp-based .pyc after an in-place provider update.
        return compile(content, str(path), 'exec', dont_inherit=True)


class ProfileFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        matches = [pin for name, pin in PINS.items() if fullname == name or fullname.startswith(name + '.')]
        if not matches:
            return None
        pin = max(matches, key=lambda p:len(p['module']))
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.origin is None:
            return spec
        origin = reject_links(spec.origin).resolve(); root = Path(pin['path'])
        relative = origin.name if root.is_file() and origin == root else origin.relative_to(root).as_posix()
        if file_hash(origin) != pin['files'].get(relative):
            raise ValueError('Provider import escapes its source pin')
        if isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            spec.loader = SourceLoader(fullname, str(origin), pin)
        return spec


FINDER = ProfileFinder()


@offline_call
def enable_profile(profile):
    global ACTIVE_PROFILE, ACTIVE_CONFIGURATION, LAST_ACTIVATION
    if LAST_ACTIVATION and LAST_ACTIVATION['state'] != 'ENABLED':
        raise ValueError('Previous activation is incomplete; inspect it and restart before retrying')
    current = inventory(roots_for(profile))
    provider_sources.validate_profile(profile, current)
    LAST_ACTIVATION = {'profile_digest':digest(profile), 'enabled_delta':[], 'preferences_saved':False, 'state':'STARTED'}
    order = []; remaining = {p['id']:p for p in profile['providers']}
    while remaining:
        ready = [p for p in remaining.values() if set(p['dependencies']) <= set(order)]
        if not ready:
            raise ValueError('Provider dependency cycle')
        for pin in ready:
            order.append(pin['id']); remaining.pop(pin['id'])
    for name in order:
        pin = next(p for p in profile['providers'] if p['id'] == name)
        loaded = [key for key in sys.modules if key == name or key.startswith(name + '.')]
        if loaded and PINS.get(name) != pin:
            raise ValueError('UNVERIFIED_LOADED_PROVIDER: clean activation is required for ' + name)
        if name in PINS and PINS[name] != pin:
            raise ValueError('Provider pin changed; restart Blender before activation')
    if FINDER not in sys.meta_path:
        sys.meta_path.insert(0, FINDER)
    for name in order:
        pin = next(p for p in profile['providers'] if p['id'] == name)
        PINS[name] = pin
        if not name.startswith('bl_ext.'):
            parent = str(Path(pin['path']).parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
        else:
            repo_name = name.split('.')[1]
            expected = str(Path(pin['path']).parent)
            repositories = [repo for repo in bpy.context.preferences.extensions.repos if repo.module == repo_name]
            if not repositories:
                repository = bpy.context.preferences.extensions.repos.new(
                    name='Harness profile ' + repo_name, module=repo_name, custom_directory=expected, remote_url='')
                repositories = [repository]
            if len(repositories) != 1 or str(Path(repositories[0].directory).resolve()) != expected:
                raise ValueError('Profile extension repository is unavailable in this environment')
        if not getattr(sys.modules.get(name), '__addon_enabled__', False):
            failures = []
            module = addon_utils.enable(name, default_set=False, persistent=True, handle_error=lambda error:failures.append(type(error).__name__))
            if module is None or failures:
                LAST_ACTIVATION['state'] = 'FAILED_OR_PARTIAL'
                raise ValueError('Provider activation failed: ' + name)
            LAST_ACTIVATION['enabled_delta'].append(name)
        for key, value in profile['preferences'].get(name, {}).items():
            addon = bpy.context.preferences.addons.get(name)
            if addon is None:
                addon = bpy.context.preferences.addons.new()
                addon.module = name  # Session state only; never call save_userpref.
            if addon.preferences is None:
                raise ValueError('Provider has no session preference entry: ' + name)
            setattr(addon.preferences, key, value)
            if getattr(addon.preferences, key) != value:
                raise ValueError('Provider preference was clamped or refused')
    provider_sources.validate_profile(profile, inventory(roots_for(profile)))
    ACTIVE_PROFILE = digest(profile)
    ACTIVE_CONFIGURATION = profile
    LAST_ACTIVATION['state'] = 'ENABLED'
    return dict(LAST_ACTIVATION)


@offline_call
def assert_profile(profile):
    if NETWORK_ATTEMPTS:
        raise ValueError('Offline profile attempted a network connection; inspect owned audit evidence')
    if ACTIVE_PROFILE != digest(profile):
        raise ValueError('Expected environment profile was not applied')
    current = inventory(roots_for(profile))
    provider_sources.validate_profile(profile, current)
    if any(not p['enabled'] or p['loaded_identity'] != 'matched' for p in current['providers']
           if p['id'] in {p['id'] for p in profile['providers']}):
        raise ValueError('Profile provider was disabled or changed')
    return {'profile_digest':ACTIVE_PROFILE, 'providers':[p['id'] for p in profile['providers']], 'blender':build()}
