"""Runs only after the qualifier's exact owned CONFIG preflight."""
from pathlib import Path
import sys

mode, runtime, output = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, runtime)
out = Path(output)
import bpy
from dcc_harness import evidence, files, recipe_store, environments
from dcc_harness.data.bridge import addons, recipes

if mode == 'prepare':
    inventory = addons.inventory([{'path':str(out / 'providers'),'namespace':''}])
    assert 'path_fixture' not in sys.modules, 'Discovery imported the provider'
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object; obj['dcc_instance_id']='cube'; obj['dcc_asset_id']='cube.asset'
    bpy.data.orphans_purge(do_recursive=True)
    source = out / 'input.blend'
    assert bpy.ops.wm.save_as_mainfile(filepath=str(source),check_existing=False)=={'FINISHED'}
    evidence.write_json(out / 'prepared.json', {'inventory':inventory,'engine':bpy.context.scene.render.engine,
        'source':{'path':str(source),'sha256':files.file_hash(source)}})
else:
    config = evidence.read_json(out / 'request.json')
    root, bundle, ref = config['root'], config['bundle'], config['reference']
    request = config['request']
    if mode == 'io':
        results = {}
        def check(name, action):
            try: results[name]={'passed':True, **(action() or {})}
            except Exception as exc: results[name]={'passed':False,'error':type(exc).__name__ + ': ' + str(exc)}
        def load():
            assert recipe_store.load(root,ref['id'],ref['digest'])==bundle
        def adapter():
            module=recipes.adapter_for(bundle)
            assert module.__file__==bundle['adapter'] and module.apply.__code__.co_filename==bundle['adapter']
            assert module.preflight({}, {})=={'ready':True}
        def managed():
            managed_request=config['managed_request']
            actual, profile=recipes.validate_managed(managed_request,managed_request['capability']['root'])
            assert actual['manifest']==bundle['manifest'] and evidence.digest(profile)==managed_request['profile']['digest']
        check('load_unchanged_bundle',load)
        check('adapter_logical_filename',adapter)
        check('managed_metadata',managed)
        for name, negative in config['cases'].items():
            def refused(name=name, negative=negative):
                try: recipe_store.load(negative,ref['id'],ref['digest'])
                except (ValueError,OSError) as exc:
                    if name=='missing': assert isinstance(exc,FileNotFoundError), str(exc)
                    else:
                        expected={'extra':'Recipe bundle members changed','extra-directory':'Unexpected bundle members',
                                  'tampered':'Recipe member changed','reparse':'reparse','extra-reparse':'reparse'}[name]
                        assert isinstance(exc,ValueError) and expected in str(exc), str(exc)
                    return {'refusal':type(exc).__name__ + ': ' + str(exc)}
                else: raise AssertionError('Invalid bundle accepted: ' + name)
            check(name+'_refused',refused)
        assert 'path_fixture' not in sys.modules, 'Inspection imported the provider'
        evidence.write_json(out / 'io-proof.json',results)
        assert all(result['passed'] for result in results.values()), results
    elif mode in ('apply','verify'):
        profile=environments.load_profile(request['profile'])
        addons.enable_profile(profile)
        source=config['prepared']['source'] if mode=='apply' else evidence.read_json(out / 'candidate.json')
        assert files.file_hash(source['path'])==source['sha256']
        bpy.ops.wm.open_mainfile(filepath=source['path'],load_ui=False)
        addons.assert_profile(profile)
        args=recipes.managed_args(request,profile,bpy.context.scene)
        with addons.session_preferences():
            if mode=='apply':
                result=recipes.apply(*args)
                evidence.write_json(out / 'applied.json',result)
                candidate=out / 'candidate.blend'
                assert not candidate.exists()
                assert bpy.ops.wm.save_as_mainfile(filepath=str(candidate),check_existing=False)=={'FINISHED'}
                evidence.write_json(out / 'candidate.json',{'path':str(candidate),'sha256':files.file_hash(candidate)})
            else:
                result=recipes.verify(*args,evidence.read_json(out / 'applied.json'))
                assert result['passed'] is True
                evidence.write_json(out / 'verified.json',result)
        addons.assert_profile(profile)
        assert files.file_hash(source['path'])==source['sha256']
    else: raise ValueError('Unknown probe mode')
