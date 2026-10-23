"""Owned native recipe I/O proof at the deep retained bundle shape; no old operation replay."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from _launcher import Qualification, BLENDER_FLAGS
from verify_release import release_environment, native_config_probe

q = Qualification(__doc__)
from dcc_harness import environments, evidence, files, recipe_store

env = release_environment(q.out)
probe = q.out / 'recipe-paths-probe.py'
probe.write_bytes(Path(__file__).with_name('recipe_paths_probe.py').read_bytes())
modules = ('files.py', 'recipe_store.py', 'data/bridge/recipes.py', 'provider_sources.py', 'data/bridge/addons.py')
pins = {name: files.file_hash(q.runtime / 'dcc_harness' / name) for name in modules}
evidence.write_json(q.out / 'runtime-proof.json', {'runtime': str(q.runtime), 'modules': pins,
    'probe_sha256': files.file_hash(probe), 'scope': 'Focused modules, not a full release freeze'})

provider = q.out / 'providers/path_fixture'; provider.mkdir(parents=True)
(provider / '__init__.py').write_text('''
bl_info={'name':'Owned path fixture','version':(1,0,0),'blender':(5,1,0),
         'dcc_harness':{'network':'offline','dependencies':[],'preferences':{}}}
def bevel(object, width, name):
    mod=object.modifiers.get(name) or object.modifiers.new(name,'BEVEL')
    mod.width=width; mod.segments=2
    return mod
def register(): pass
def unregister(): pass
''', encoding='utf-8')
adapter = q.out / 'adapter.py'
adapter.write_text('''
def preflight(context, parameters): return {'ready':True}
def apply(context, parameters, effect_id):
    context['invoke']()
    return {'status':'FINISHED'}
def inspect_output(context, effect_id):
    mods=[m for m in context['target'].modifiers if m.name==context['effect_name']]
    return {'effect_id':effect_id,'effect_count':len(mods),'measurements':{
        'modifiers':[{'type':m.type,'width':m.width,'segments':m.segments} for m in mods]}}
def verify_saved(observation, output): return {'passed':output['effect_count']==1}
''', encoding='utf-8')
asset = q.out / 'asset.txt'; asset.write_bytes(b'owned inert asset\n')


def launch(mode):
    script = q.out / (mode + '-bootstrap.py')
    script.write_text(native_config_probe(Path(env['BLENDER_USER_CONFIG']), q.out / (mode + '-config.json'))
                      + '\nimport runpy\nrunpy.run_path(' + repr(str(probe)) + ",run_name='__main__')\n",
                      encoding='utf-8')
    with (q.out / (mode + '.log')).open('x', encoding='utf-8') as log:
        proc = subprocess.run([q.args.blender, *BLENDER_FLAGS, '--python', str(script), '--',
                               mode, str(q.runtime), str(q.out)], env=env, stdout=log,
                              stderr=subprocess.STDOUT, timeout=120)
    if proc.returncode:
        raise RuntimeError('Native recipe path ' + mode + ' failed; inspect ' + str(q.out / (mode + '.log')))


launch('prepare')
prepared = evidence.read_json(q.out / 'prepared.json')
item, = prepared['inventory']['providers']
recipe_id = 'path_fixture.python_function'
root = q.out / 'native-capabilities/routing/background-autonomous/project'
minimum = len(str(root / 'capabilities/recipes' / recipe_id / ('0' * 64)))
if minimum < 257:
    root = root.with_name(root.name + 'x' * (257 - minimum))
ref = environments.create_profile(root, prepared['inventory'], ['path_fixture'], {})
spec = {'schema':'dcc.capability.recipe.v1', 'id':recipe_id, 'version':1, 'capabilities':['bevel'],
    'provider':{'id':'path_fixture','source_digest':item['source_digest']},
    'parameters':{'type':'object','properties':{'amount':{'type':'number','minimum':.01,'maximum':1}},
                  'required':['amount'],'additionalProperties':False},
    'compatibility':{'blender_min':[5,1,0],'blender_max':[5,2,0], 'engines':[prepared['engine']],
                     'target_types':['MESH'],'contexts':['background','live']},
    'coverage':{'reads':['geometry'],'writes':['modifiers'],'dependencies':['geometry']},
    'invocation':{'kind':'python_function','entry':'path_fixture.bevel',
                  'arguments':{'object':'target','width':'parameter:amount','name':'effect_name'},
                  'completion':'synchronous','cancellation':'between_calls'},
    'update':{'identity':'effect_key','shared_materials':'none'}, 'validators':['inspect_output','verify_saved'],
    'cases':[{'name':'positive','parameters':{'amount':.1},'context':'background','expect':'pass'}]}
bundle_ref = recipe_store.draft(root, spec, adapter, [str(asset)])
bundle = recipe_store.load(root, bundle_ref['id'], bundle_ref['digest'])
folder = Path(bundle['adapter']).parent
metadata_root = root / 'managed-metadata-boundary'
metadata_ref = environments.create_profile(metadata_root, prepared['inventory'], ['path_fixture'], {})
assert recipe_store.draft(metadata_root, spec, adapter, [str(asset)]) == bundle_ref
# These are explicit synthetic validation records, not host QUALIFIED receipts.
# They exercise native managed metadata admission separately from recipe execution.
report = metadata_root / 'capabilities/qualifications' / ('owned-path-metadata-' + str(uuid.uuid4())) / 'report.json'
evidence.write_json(report, {'passed':True, 'recipe_digest':bundle_ref['digest'], 'profile_digest':ref['digest'],
                             'contexts':['live'], 'fixture_only':True})
reference = {'report':str(report), 'sha256':files.file_hash(report)}
registration = metadata_root / 'capabilities/registered' / (reference['sha256'] + '.json')
evidence.write_json(registration, reference)
operation = str(uuid.uuid4())
request = {'operation_id':operation, 'profile':ref,
    'live':{'parameters':{'operation_id':operation},'target':'cube'},
    'capability':{'root':str(root),'parameters':{'amount':.1},'effect_id':evidence.digest({'owned':'path-proof'}),
      'requirement':{'target_id':'cube','context':'live'},
      'resolution':{'selected':{'recipe_id':recipe_id,'recipe_digest':bundle_ref['digest'],'profile_digest':ref['digest']},
                    'qualification':reference}}}
managed_request = copy.deepcopy(request)
managed_request['capability']['root'] = str(metadata_root)
managed_request['profile'] = metadata_ref
cases = {}
for name in ('missing', 'extra', 'extra-directory', 'tampered', 'reparse', 'extra-reparse'):
    case_root = root / ('negative-' + name)
    case_folder = recipe_store.bundle_path(case_root, recipe_id, bundle_ref['digest'])
    if name in ('reparse', 'extra-reparse'):
        if name == 'reparse':
            case_folder.mkdir(parents=True)
            shutil.copyfile(folder / 'adapter.py', case_folder / 'adapter.py')
            shutil.copyfile(folder / 'bundle.json', case_folder / 'bundle.json')
        else:
            shutil.copytree(folder, case_folder)
        target = q.out / (name + '-target'); target.mkdir(); shutil.copyfile(asset, target / asset.name)
        link = case_folder / ('assets' if name == 'reparse' else 'unlisted-link')
        if os.name == 'nt':
            result = subprocess.run(['cmd','/c','mklink','/J',str(files.io_path(link)),str(target)],
                                    capture_output=True,text=True)
            junction = {'created':result.returncode == 0,'diagnostic':result.stdout + result.stderr}
        else:
            junction = {'created':False,'diagnostic':'Windows junction probe only'}
        if not junction['created']:
            evidence.write_json(q.out / (name + '-junction.json'), junction)
            continue
        evidence.write_json(q.out / (name + '-junction.json'), junction)
    else:
        shutil.copytree(folder, case_folder)
        if name == 'missing': (case_folder / 'assets/asset.txt').unlink()
        if name == 'extra': (case_folder / 'unexpected.py').write_text('not allowed')
        if name == 'extra-directory': (case_folder / 'unexpected').mkdir()
        if name == 'tampered': (case_folder / 'adapter.py').write_bytes(b'changed source')
    cases[name] = str(case_root)
evidence.write_json(q.out / 'request.json', {'root':str(root),'bundle':bundle,'reference':bundle_ref,
    'request':request,'managed_request':managed_request,'cases':cases,'prepared':prepared,
    'lengths':{'bundle':len(str(folder)),'adapter':len(bundle['adapter']),
               'registration':len(str(registration)),'report':len(str(report))}})
launch('io')
launch('apply')
launch('verify')
assert recipe_store.load(root, recipe_id, bundle_ref['digest']) == bundle
assert pins == {name: files.file_hash(q.runtime / 'dcc_harness' / name) for name in modules}
assert {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} == set(bundle['manifest']['files']) | {'bundle.json'}
assert {p.relative_to(provider).as_posix() for p in provider.rglob('*') if p.is_file()} == {'__init__.py'}
q.finish({'lengths':evidence.read_json(q.out / 'request.json')['lengths'],
    'io':evidence.read_json(q.out / 'io-proof.json'), 'verify':evidence.read_json(q.out / 'verified.json'),
    'junctions':{name:evidence.read_json(q.out / (name + '-junction.json')) for name in ('reparse','extra-reparse')},
    'runtime_modules_unchanged':True, 'bundle_unchanged':True,'no_bundle_or_provider_pyc':True,
    'limits':'Deep recipe/managed metadata proof; short owned synthetic provider and native scene paths only'})
