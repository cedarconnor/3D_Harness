"""Owned synthetic-provider qualification; never activates add-ons in an artist process."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import zipfile


def gui_profile(args, out, ref):
    from dcc_harness import distribution, environments, blender_bridge
    from qualify_live import wait_for
    distribution.export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive: archive.extractall(out / 'addon')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
    script = out / 'gui.py'
    config = {'out':str(out), 'profile':ref, 'port':port}
    script.write_text('CONFIG = ' + repr(config) + '\n' + '''
import bpy, json, sys, time
from pathlib import Path
out = Path(CONFIG['out']); sys.path.insert(0, str(out / 'addon'))
attempts = []
def audit(event, args):
    if event == 'socket.connect':
        attempts.append(str(args[1])); raise RuntimeError('Unexpected outbound connection')
sys.addaudithook(audit)
watched = ('undo_post','redo_post','depsgraph_update_post')
before = {name:tuple(getattr(bpy.app.handlers,name)) for name in watched}
import dcc_harness_bridge as bridge
from dcc_harness_bridge import addons
profile = json.loads(Path(CONFIG['profile']['path']).read_text())
# A timestamp/size-valid stale pyc must not override the profile's pinned source.
import os, py_compile
entry = Path(next(p['entry'] for p in profile['providers'] if p['id'] == 'harness_fixture'))
source = entry.read_bytes(); stamp = entry.stat()
stale = source.replace(b"['profile_fixture'] = 1", b"['profile_fixture'] = 9")
assert stale != source and len(stale) == len(source)
entry.write_bytes(stale); os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
py_compile.compile(str(entry), doraise=True)
entry.write_bytes(source); os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
delta = addons.enable_profile(profile)
assert set(delta['enabled_delta']) == {p['id'] for p in profile['providers']} and not delta['preferences_saved']
assert 'import_sentinel' not in sys.modules
assert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}
assert bpy.context.object['profile_fixture'] == 1
bridge.register(); bridge.server = bridge.ObservationServer(CONFIG['port'], out); bridge.server.start()
(out / 'ready.json').write_text(json.dumps({'descriptor':str(bridge.server.session.descriptor_path)}))
deadline = time.monotonic() + 90
def control():
    if (out / 'stop').exists() or time.monotonic() > deadline:
        bridge.server.stop(); bridge.unregister()
        assert all(tuple(getattr(bpy.app.handlers,name)) == before[name] for name in watched)
        assert not any(name == 'dcc_harness' or name.startswith('dcc_harness.') for name in sys.modules)
        (out / 'gui-audit.json').write_text(json.dumps({'outbound_attempts':attempts,
            'standalone_export':True, 'activity_handlers_unchanged':True, 'delta':delta}))
        bpy.ops.wm.quit_blender(); return None
    return .1
bpy.app.timers.register(control)
''', encoding='utf-8')
    startup = None
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    config_dir = out / 'gui-config'; config_dir.mkdir()
    temporary = out / 'gui-temporary'; temporary.mkdir()
    with (out / 'gui.log').open('x') as log:
        process = subprocess.Popen([args.blender, '--offline-mode', '--factory-startup', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(script)], stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, startupinfo=startup, env={**os.environ, 'BLENDER_USER_CONFIG':str(config_dir),
                'TEMP':str(temporary), 'TMP':str(temporary),
                'BLENDER_USER_EXTENSIONS':str(out / 'gui-extensions')})
        token = None
        try:
            wait_for(lambda:(out / 'ready.json').exists(), process)
            binding = json.loads((out / 'ready.json').read_text())['descriptor']
            token = blender_bridge.descriptor(binding)['token']
            blender_bridge.observe('ping', port=port, timeout=10)
            result = environments.inventory(binding, blender=args.blender)
            provider = next(p for p in result['providers'] if p['id'] == 'harness_fixture')
            assert provider['enabled'] and provider['loaded_identity'] == 'matched'
            assert 'object.harness_fixture_mark' in provider['operators']
            assert token not in json.dumps(result)
            (out / 'gui-inventory.json').write_text(json.dumps(result, indent=2))
        finally:
            (out / 'stop').write_text('stop')
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)
        assert process.returncode == 0 and (out / 'gui-audit.json').exists()
    audit = json.loads((out / 'gui-audit.json').read_text())
    assert not audit['outbound_attempts'] and not (config_dir / 'userpref.blend').exists()
    if token:
        for path in out.rglob('*'):
            if path.is_file():
                assert token.encode() not in path.read_bytes(), 'Retained private token'
    return audit


def profiles(args):
    runtime = Path(args.runtime).resolve(); sys.path.insert(0, str(runtime))
    from dcc_harness import environments
    from dcc_harness.native import run_worker
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    fixtures = Path(__file__).resolve().parents[1] / 'tests/fixtures/addons'
    shutil.copytree(fixtures, out / 'providers')
    roots = [{'path':str(out / 'providers/legacy'), 'namespace':''},
             {'path':str(out / 'providers/extensions'), 'namespace':'bl_ext.fixture'}]
    first = environments.inventory(blender=args.blender, roots=roots, out=out / 'factory')
    provider = next(p for p in first['providers'] if p['id'] == 'harness_fixture')
    assert not provider['enabled'] and provider['loaded_identity'] == 'not_loaded'
    ref = environments.create_profile(out / 'project', first, ['harness_fixture', 'bl_ext.fixture.example_extension'],
                                      {'harness_fixture':{'quality':3}})
    gui = gui_profile(args, out, ref)
    probe = out / 'probe.py'
    probe.write_text('''
from pathlib import Path
import json, sys, bpy
from dcc_harness.environments import load_profile
from dcc_harness.data.bridge import addons
from dcc_harness.evidence import read_json, write_json
action, request_path = sys.argv[sys.argv.index('--') + 1:]
request = read_json(request_path); folder = Path(request_path).parent
profile = load_profile(request['profile']); initial = addons.assert_profile(profile)
assert bpy.context.preferences.addons['harness_fixture'].preferences.quality == 3
if action == 'execute':
    assert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}
    assert bpy.data.objects['Cube']['profile_fixture'] == 1
    bpy.ops.wm.save_as_mainfile(filepath=request['candidate'])
else:
    bpy.ops.wm.open_mainfile(filepath=request['candidate'])
    assert bpy.data.objects['Cube']['profile_fixture'] == 1
    assert bpy.ops.object.harness_fixture_mark.poll()
assert addons.assert_profile(profile) == initial
write_json(folder / 'result.json', {'passed':True, 'profile':initial,
    'quality':bpy.context.preferences.addons['harness_fixture'].preferences.quality})
''', encoding='utf-8')
    reports = []
    for action in ('execute', 'verify'):
        folder = out / action; folder.mkdir()
        run_worker(args.blender, folder, probe, action, {'candidate':str(out / 'candidate.blend')}, profile=ref, timeout=60)
        reports.append(json.loads((folder / 'result.json').read_text()))
    assert reports[0]['profile']['profile_digest'] == reports[1]['profile']['profile_digest']
    # Exercise the actual managed execution and independent observation workers.
    import dcc_harness
    from dcc_harness.evidence import file_hash
    package = Path(dcc_harness.__file__).parent
    script = out / 'managed-script.py'
    script.write_text("import bpy\nassert bpy.ops.object.harness_fixture_mark() == {'FINISHED'}\n")
    candidate = out / 'managed.blend'
    folder = out / 'managed-execute'; folder.mkdir()
    run_worker(args.blender, folder, package / '_execution_blender.py', 'execute', {
        'source':{'path':str(out / 'candidate.blend'), 'sha256':file_hash(out / 'candidate.blend')},
        'script':str(script), 'script_sha256':file_hash(script), 'output':str(candidate)}, profile=ref, timeout=60)
    folder = out / 'managed-observe'; folder.mkdir()
    run_worker(args.blender, folder, package / '_observe_blender.py', 'observe', {
        'source':{'path':str(candidate), 'sha256':file_hash(candidate)}, 'out':str(folder), 'compact':False},
        profile=ref, timeout=60)
    assert (folder / 'observation.json').exists()
    # A GUI-only provider must fail in the verifier, never pass in factory mode.
    entry = out / 'providers/legacy/harness_fixture/__init__.py'
    entry.write_text(entry.read_text() + '\nif bpy.app.background: raise RuntimeError("GUI_ONLY")\n')
    changed = environments.inventory(blender=args.blender, roots=roots, out=out / 'changed')
    gui_only = environments.create_profile(out / 'project', changed, ['harness_fixture'], {})
    folder = out / 'gui-only-verifier'; folder.mkdir()
    try:
        run_worker(args.blender, folder, probe, 'verify', {'candidate':str(candidate)}, profile=gui_only, timeout=60)
    except RuntimeError:
        assert not (folder / 'result.json').exists()
        assert json.loads((folder / 'verify-environment.json').read_text())['state'] == 'FAILED_OR_PARTIAL'
    else:
        raise AssertionError('GUI-only verifier incorrectly passed')
    result = {'passed':True, 'case':'profiles', 'factory_provider_disabled':True,
              'execution_and_independent_verifier_profile_matched':True, 'desktop_provider_enabled':True,
              'managed_workers_passed':True, 'stale_bytecode_ignored':True, 'gui_only_verifier_refused':True,
              'gui':gui, 'reports':reports}
    (out / 'VERIFICATION.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


def fixture_recipe(provider, kind, entry, cases, *, name=None, shared=False):
    return {'schema':'dcc.capability.recipe.v1', 'id':name or provider['id'] + '.' + kind, 'version':1,
        'capabilities':['surface.fixture'], 'provider':{'id':provider['id'],'source_digest':provider['source_digest']},
        'parameters':{'type':'object','properties':{'amount':{'type':'number','minimum':.01,'maximum':.5},
             'behavior':{'type':'string','enum':['normal','noop','mutate_error','missing_reopen','duplicate','network','modal','shared_bad','copy']}},
             'required':['amount','behavior'],'additionalProperties':False},
        'compatibility':{'blender_min':[5,1,0],'blender_max':[5,2,0],'engines':['BLENDER_EEVEE'],
                         'target_types':['MESH'],'contexts':['background','live']},
        'coverage':{'reads':['geometry','materials'],'writes':['modifiers','materials'] if shared else ['modifiers'],
                    'dependencies':['geometry','materials']},
        'invocation':{'kind':kind,'entry':entry,'completion':'synchronous','cancellation':'between_calls'},
        'update':{'identity':'effect_key','shared_materials':'all_users' if shared else 'none'},
        'validators':['inspect_output','verify_saved'],'cases':cases}


def fixture_case(name, context='background', behavior='normal', expect='pass'):
    result = {'name':name,'parameters':{'amount':.15,'behavior':behavior},'context':context,'expect':expect}
    if expect == 'fail':
        reasons = {'noop':'exactly one measured owned effect', 'mutate_error':'Fixture mutated before error',
                   'missing_reopen':'provider was disabled or changed', 'duplicate':'exactly one measured owned effect',
                   'network':'Offline profile attempted', 'modal':'incomplete/modal',
                   'shared_bad':'Shared material users differ', 'normal':'UNSUPPORTED_CONTEXT'}
        result['failure_contains'] = reasons[behavior]
    return result


def onboarding(args):
    runtime = Path(args.runtime).resolve(); sys.path.insert(0,str(runtime))
    from dcc_harness import environments, recipes
    from dcc_harness.evidence import read_json,write_json
    from dcc_harness.native import run_worker
    out = Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    fixture_root = Path(__file__).resolve().parents[1] / 'tests/fixtures/addons'
    shutil.copytree(fixture_root / 'legacy/capability_fixture',out / 'providers/capability_fixture')
    shutil.copytree(fixture_root / 'legacy/capability_fixture',out / 'providers/capability_second')
    second = out / 'providers/capability_second/__init__.py'
    second.write_text(second.read_text().replace('object.capability_', 'object.second_').replace("mod.segments = 2", "mod.segments = 3"))
    asset_script = out / 'asset.py'
    asset_script.write_text('''
import bpy, json, sys
from pathlib import Path
_, path = sys.argv[sys.argv.index('--')+1:]; request = json.loads(Path(path).read_text())
tree = bpy.data.node_groups.new('FixtureGroup','GeometryNodeTree')
tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
entry = tree.nodes.new('NodeGroupInput'); output = tree.nodes.new('NodeGroupOutput')
transform = tree.nodes.new('GeometryNodeTransform'); transform.inputs['Translation'].default_value = (.1,0,0)
tree.links.new(entry.outputs['Geometry'],transform.inputs['Geometry']); tree.links.new(transform.outputs['Geometry'],output.inputs['Geometry'])
bpy.data.libraries.write(request['output'],{tree})
''')
    setup = out / 'setup'; setup.mkdir()
    asset = out / 'providers/capability_fixture/fixture.blend'
    run_worker(args.blender,setup,asset_script,'asset',{'output':str(asset)},timeout=60)
    inventory = environments.inventory(blender=args.blender,roots=[{'path':str(out / 'providers'),'namespace':''}],out=out / 'inventory')
    project = out / 'project'; providers = {p['id']:p for p in inventory['providers']}
    profile = environments.create_profile(project,inventory,['capability_fixture'],{})
    second_profile = environments.create_profile(project,inventory,['capability_second'],{})
    both = [fixture_case('background'),fixture_case('live','live')]
    values = [
        fixture_recipe(providers['capability_fixture'],'python_function','capability_fixture.mark',both + [
            fixture_case(name,behavior=name,expect='fail') for name in ('noop','mutate_error','missing_reopen','duplicate','network')]),
        fixture_recipe(providers['capability_fixture'],'operator','object.capability_fixture',both + [
            fixture_case('noop',behavior='noop',expect='fail'),fixture_case('modal',behavior='modal',expect='fail')]),
        fixture_recipe(providers['capability_fixture'],'operator','object.capability_viewport',[
            fixture_case('viewport','live'),fixture_case('missing_viewport',expect='fail')],name='fixture.viewport'),
        fixture_recipe(providers['capability_fixture'],'operator','object.capability_never',[
            fixture_case('poll_failure')],name='fixture.never'),
        fixture_recipe(providers['capability_fixture'],'python_function','capability_fixture.mark',[
            fixture_case('shared_valid'),fixture_case('shared_invalid',behavior='shared_bad',expect='fail')],name='fixture.shared',shared=True),
        fixture_recipe(providers['capability_fixture'],'node_asset','FixtureGroup',both),
        fixture_recipe(providers['capability_second'],'python_function','capability_second.mark',both),
    ]
    single = fixture_recipe(providers['capability_fixture'],'python_function','capability_fixture.mark',[
        fixture_case('shared_copy',behavior='copy'),fixture_case('shared_missing_copy',expect='fail')],name='fixture.single-copy',shared=True)
    single['update']['shared_materials'] = 'single_user_copy'
    single['cases'][1]['failure_contains'] = 'Shared material copy policy'
    values.append(single)
    results = []
    for value in values:
        ref = recipes.draft(project,value,str(fixture_root / 'capability_adapter.py'),[str(asset)] if value['invocation']['kind']=='node_asset' else [])
        selected_profile = second_profile if value['provider']['id']=='capability_second' else profile
        result = recipes.qualify(project,ref['id'],ref['digest'],selected_profile['digest'],blender=args.blender,
                                 out=project / 'capabilities/qualifications' / ref['id'])
        expected = 'FAILED' if value['id']=='fixture.never' else 'QUALIFIED'
        assert result['state']==expected, json.dumps({'recipe':value['id'],'expected':expected,'result':result})
        report = read_json(result['report'])
        if expected == 'QUALIFIED':
            recipes.register_qualified(project,result['report'])
            recipes.require_qualified(project,ref['id'],ref['digest'])
        else:
            try: recipes.register_qualified(project,result['report'])
            except ValueError: pass
            else: raise AssertionError('Failed poll recipe registered')
            assert recipes.inspect(project,ref['id'],ref['digest'])['state']=='FAILED'
        if value['id']=='fixture.viewport':
            try: recipes.require_qualified(project,ref['id'],ref['digest'],context='background')
            except ValueError: pass
            else: raise AssertionError('GUI qualification incorrectly implied background support')
        results.append({'recipe':ref,'profile':selected_profile,'qualification':result,'contexts':report['contexts']})
        print(value['id'],expected,flush=True)
    # Source changes without version changes invalidate existing registrations.
    entry = out / 'providers/capability_fixture/__init__.py'; original = entry.read_bytes()
    entry.write_bytes(original + b'\n# source drift\n')
    try:
        try: recipes.require_qualified(project,results[0]['recipe']['id'],results[0]['recipe']['digest'])
        except ValueError: pass
        else: raise AssertionError('Changed provider retained qualification')
        assert recipes.inspect(project,results[0]['recipe']['id'],results[0]['recipe']['digest'])['state']=='STALE'
    finally: entry.write_bytes(original)
    result = {'passed':True,'case':'onboarding','recipes':results,'source_drift_refused':True,
              'limits':'Synthetic providers, owned GUI/background scenes; no artistic superiority claim'}
    write_json(out / 'VERIFICATION.json',result)
    print('PASS: function/operator/node-asset qualification, context, reopen, repeat, failure and source-drift cases',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True); parser.add_argument('--blender', required=True)
    parser.add_argument('--out', required=True); parser.add_argument('--case', choices=['profiles','onboarding'], default='profiles')
    args = parser.parse_args()
    {'profiles':profiles,'onboarding':onboarding}[args.case](args)
