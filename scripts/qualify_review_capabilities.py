"""Owned GUI Task3 regressions; accepts source or installed runtime, never artist state."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


PROVIDER='''
bl_info={'name':'Ordinary local provider','version':(1,0,0),'blender':(5,1,0)}
import bpy
class Preferences(bpy.types.AddonPreferences):
    bl_idname=__name__
    quality:bpy.props.IntProperty(default=1)
def bevel(object, width, name=None):
    assert bpy.context.preferences.addons[__name__].preferences.quality==3
    mod=object.modifiers.get(name) if name else None
    if mod is None: mod=object.modifiers.new(name or 'Ordinary Bevel','BEVEL')
    mod.width=width; mod.segments=2
    return mod
def noop(object, width, name=None):
    return None
def irrelevant(object, width, name=None):
    object.location.z+=.01
    return None
def transform_only(object, width, name=None):
    object.location.z=1
    return None
def register(): bpy.utils.register_class(Preferences)
def unregister(): bpy.utils.unregister_class(Preferences)
'''

ADAPTER='''
def preflight(context, parameters): return {'ready':True}
def apply(context, parameters, effect_id):
    context['invoke']()
    return {'status':'FINISHED'}
def inspect_output(context, effect_id):
    mods=[m for m in context['target'].modifiers if m.name==context['effect_name']]
    return {'effect_id':effect_id,'effect_count':len(mods),'measurements':{
        'modifiers':[{'type':m.type,'width':m.width,'segments':m.segments} for m in mods]}}
def verify_saved(observation, output): return {'passed':output['effect_count']==1}
'''


def worker(config):
    import bpy
    import copy
    import uuid
    from types import SimpleNamespace
    cfg=json.loads(Path(config).read_text()); out=Path(cfg['out'])
    if Path(bpy.utils.user_resource('CONFIG')).resolve()!=(out/'config').resolve():
        raise RuntimeError('Owned config was not selected; refusing all native work')
    sys.path.insert(0,cfg['runtime'])
    from dcc_harness import recipes, environments, capabilities, live_snapshot
    from dcc_harness.data.bridge import addons, recipes as native, attachment, recovery
    from dcc_harness.evidence import digest
    from dcc_harness.continuity_blender import measure_live
    checks=[]
    def check(name,call):
        try: call(); checks.append({'name':name,'passed':True})
        except Exception as exc: checks.append({'name':name,'passed':False,'error':repr(exc)})
        (out/'checks.json').write_text(json.dumps(checks,indent=2))
    def require(value):
        if not value: raise AssertionError('Native assertion failed')
    for existing in list(bpy.data.objects): bpy.data.objects.remove(existing,do_unlink=True)
    bpy.ops.mesh.primitive_cube_add(); obj=bpy.context.view_layer.objects.active
    obj['dcc_instance_id']='cube'; obj['dcc_asset_id']='cube.asset'; obj.rotation_euler=(.1,.2,.3)
    mat=bpy.data.materials.new('Shared'); mat['dcc_material_id']='shared'; mat.use_nodes=True
    obj.data.materials.append(mat)
    other=bpy.data.scenes.new('Other Scene'); user=obj.copy(); user.data=obj.data.copy(); other.collection.objects.link(user)
    user['dcc_instance_id']='other.cube'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'owned.blend'))
    scene=bpy.context.scene
    check('rotated_multiscene_projection',lambda:require(native.measurements(scene,'cube',['transform','materials'])==
        capabilities.observed_scope(measure_live(scene),'cube',['transform','materials'])))
    light=bpy.data.objects.new('Unlabeled',bpy.data.lights.new('Unlabeled','POINT')); scene.collection.objects.link(light)
    def refuse_surrounding():
        try: native.measurements(scene,'cube',['geometry'])
        except ValueError as exc: require('UNSUPPORTED_COVERAGE' in str(exc)); return
        raise AssertionError('Unmeasured surrounding scene accepted')
    check('unmeasured_surrounding_refused',refuse_surrounding); bpy.data.objects.remove(light,do_unlink=True)
    provider=out/'providers/ordinary'; provider.mkdir(parents=True); (provider/'__init__.py').write_text(PROVIDER)
    inv=addons.inventory([{'path':str(provider.parent),'namespace':''}]); item=inv['providers'][0]
    # Preferences metadata is an explicit local review assertion for this owned fixture.
    # Production inventory remains static and import free.
    source=(provider/'__init__.py').read_text().replace("'blender':(5,1,0)}","'blender':(5,1,0),'dcc_harness':{'preferences':{'quality':'integer'}}}")
    (provider/'__init__.py').write_text(source)
    extension=out/'extensions-provider/empty_extension'; extension.mkdir(parents=True)
    (extension/'__init__.py').write_text('def register(): pass\ndef unregister(): pass\n')
    (extension/'blender_manifest.toml').write_text('schema_version="1.0.0"\nid="empty_extension"\nversion="1.0.0"\nname="Owned extension"\ntagline="Owned no-op fixture"\nmaintainer="Qualifier"\ntype="add-on"\nblender_version_min="5.1.0"\nlicense=["SPDX:MIT"]\n')
    inv=addons.inventory([{'path':str(provider.parent),'namespace':''},{'path':str(extension.parent),'namespace':'bl_ext.review_owned'}])
    item=next(p for p in inv['providers'] if p['id']=='ordinary')
    review={'ordinary':{'source_digest':item['source_digest'],'reviewed_by':'owned qualifier',
                        'reason':'Reviewed entire local fixture: no network or license calls'}}
    ext=next(p for p in inv['providers'] if p['id'].startswith('bl_ext.'))
    review[ext['id']]={'source_digest':ext['source_digest'],'reviewed_by':'owned qualifier','reason':'Entire extension consists of empty register/unregister'}
    ref=environments.create_profile(out/'project',inv,['ordinary',ext['id']],{'ordinary':{'quality':3}},reviews=review)
    profile=environments.load_profile(ref)
    before_addons=[a.module for a in bpy.context.preferences.addons]
    before_auto=bpy.context.preferences.use_preferences_save
    before_repos=[r.module for r in bpy.context.preferences.extensions.repos]
    addons.enable_profile(profile)
    check('session_preferences_restored_after_enable',lambda:require(
        [a.module for a in bpy.context.preferences.addons]==before_addons and bpy.context.preferences.use_preferences_save==before_auto))
    check('session_extension_repository_restored',lambda:require([r.module for r in bpy.context.preferences.extensions.repos]==before_repos))
    effect=digest({'effect':'ordinary'})
    def value(entry='bevel',rename=False):
        arguments={'object':'target','width':'parameter:amount'}
        if not rename: arguments['name']='effect_name'
        return {'schema':'dcc.capability.recipe.v1','id':'ordinary.'+entry+('.returned' if rename else ''),'version':1,
          'capabilities':['bevel'],'provider':{'id':'ordinary','source_digest':item['source_digest']},
          'parameters':{'type':'object','properties':{'amount':{'type':'number','minimum':.01,'maximum':1}},'required':['amount'],'additionalProperties':False},
          'compatibility':{'blender_min':[5,1,0],'blender_max':[5,2,0],'engines':[scene.render.engine],'target_types':['MESH'],'contexts':['live','background']},
          'coverage':{'reads':['geometry'],'writes':['modifiers'],'dependencies':['geometry']},
          'invocation':{'kind':'python_function','entry':'ordinary.'+entry,'arguments':arguments,'completion':'synchronous','cancellation':'between_calls'},
          'update':{'identity':'effect_key','shared_materials':'none'},'validators':['inspect_output','verify_saved'],
          'cases':[{'name':'positive','parameters':{'amount':.1},'context':'live','expect':'pass'}]}
    retained={}
    def run(value,code=ADAPTER):
        adapter=out/('adapter-'+str(uuid.uuid4())+'.py'); adapter.write_text(code)
        bundle=recipes.draft(out/'project',value,str(adapter),[])
        retained.update(bundle=bundle)
        return native.apply(out/'project',bundle['id'],bundle['digest'],profile,scene,'cube',{'amount':.1},effect)
    def ordinary():
        first=run(value()); second=run(value())
        require(first['output']==second['output'] and not second['changed'])
        require(len(obj.modifiers)==1)
        legacy=copy.deepcopy(first); legacy.pop('native_effect',None)
        bundle=retained['bundle']
        try: native.verify(out/'project',bundle['id'],bundle['digest'],profile,scene,'cube',{'amount':.1},effect,legacy)
        except ValueError as exc: require('native modifier effect' in str(exc))
        else: raise AssertionError('Legacy output without independent native effect evidence verified')
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'ordinary-candidate.blend'))
        (out/'ordinary-verify.json').write_text(json.dumps({'result':first,'bundle':retained['bundle'],'profile':ref,
            'effect_id':effect,'root':str(out/'project'),'candidate':str(out/'ordinary-candidate.blend')}))
    check('ordinary_api_idempotent_repeat',ordinary)
    obj.modifiers.clear()
    check('returned_untagged_modifier_owned',lambda:require(run(value(rename=True))['output']['effect_count']==1))
    def existing_noop():
        try: run(value('noop'))
        except ValueError as exc: require('prior exact successful proof' in str(exc)); return
        raise AssertionError('First no-op invocation borrowed an existing effect')
    check('existing_effect_first_noop_refused',existing_noop)
    def unrelated_change():
        spec=value('irrelevant'); spec['coverage']['reads'].append('transform'); spec['coverage']['dependencies'].append('transform')
        try: run(spec)
        except ValueError as exc: require('claimed output' in str(exc).lower()); return
        raise AssertionError('Unrelated provider transform borrowed untouched existing output')
    check('unrelated_change_unchanged_output_refused',unrelated_change)
    def metadata_masked_effect():
        spec=value('transform_only'); spec['coverage']['reads'].append('transform'); spec['coverage']['dependencies'].append('transform')
        metadata=ADAPTER.replace("'modifiers':[", "'transform':list(context['target'].location),'modifiers':[")
        try: first=run(spec,metadata)
        except ValueError as exc: require('claimed output' in str(exc).lower()); return
        second=run(spec,metadata)
        bundle=retained['bundle']
        verified=native.verify(out/'project',bundle['id'],bundle['digest'],profile,scene,'cube',{'amount':.1},effect,first)
        (out/'metadata-masked-effect.json').write_text(json.dumps({'accepted':True,
            'claimed_modifier_unchanged':first['before']['modifiers']==first['after']['modifiers'],
            'unrelated_transform_changed':first['before']['transform']!=first['after']['transform'],
            'repeat_changed':second['changed'],'verification_passed':verified['passed']},indent=2))
        raise AssertionError('Changing inspector metadata masked unchanged claimed native effect')
    check('metadata_masked_unchanged_effect_refused',metadata_masked_effect)
    obj.modifiers.clear()
    inspect_deception=ADAPTER.replace("    mods=[m for m", "    if not context['target'].modifiers.get(context['effect_name']):\n        m=context['target'].modifiers.new(context['effect_name'],'BEVEL'); m.width=.1; m.segments=2\n    mods=[m for m")
    def deceptive_inspector():
        try: run(value('noop'),inspect_deception)
        except ValueError as exc: require('inspect' in str(exc).lower() or 'invocation' in str(exc).lower()); return
        raise AssertionError('Inspector manufactured provider proof')
    check('inspect_output_mutation_refused',deceptive_inspector)
    for entry in ('noop','irrelevant'):
        obj.modifiers.clear()
        deceptive=ADAPTER.replace("    return {'status':'FINISHED'}", "    m=context['target'].modifiers.new(context['effect_name'],'BEVEL')\n    m.width=.1; m.segments=2\n    return {'status':'FINISHED'}")
        def deception(entry=entry):
            try: run(value(entry),deceptive)
            except ValueError as exc: require('invocation' in str(exc).lower() or 'owned effect' in str(exc)); return
            raise AssertionError('Adapter manufactured provider proof')
        check(entry+'_adapter_deception_refused',deception)
    obj.modifiers.clear(); obj.modifiers.new('Measured Bevel','BEVEL').width=.07
    for index in range(1,32):
        clone=obj.copy(); clone.data=obj.data.copy(); scene.collection.objects.link(clone)
        clone.location=(index%8*3,index//8*3,index*.03)
        clone['dcc_instance_id']='bevel.'+str(index)
    session=SimpleNamespace(project=out/'recovery/state',scene=scene.name,active=None,
        session_id=str(uuid.uuid4()),generation=str(uuid.uuid4()),describe=lambda:{})
    session.project.mkdir(parents=True)
    state=attachment.check(session,{})
    baseline=json.loads((session.project/'live/observations'/(state['fingerprint']+'.json')).read_text())
    samples=[attachment.snapshot(scene) for _ in range(3)]
    (out/'bevel-comparison.json').write_text(json.dumps({'objects':len(baseline['objects']),
        'baseline':state['fingerprint'],'later':[live_snapshot.fingerprint(s) for s in samples],
        'equivalent':[live_snapshot.equivalent(baseline,s) for s in samples]},indent=2))
    def recovery_case():
        op=str(uuid.uuid4()); folder=session.project/'execution/operations'/op; folder.mkdir(parents=True)
        jobs=SimpleNamespace(session=session,folder=lambda _:folder,status=lambda _:{'state':'FAILED'},write=lambda *a,**kw:None)
        result=recovery.capture(jobs,{'operation_id':op,'decision':'keep-current','expected_fingerprint':state['fingerprint'],'attempt_id':str(uuid.uuid4())})
        require('archive' in result)
    check('bevel_recovery_native_capture',recovery_case)
    for kind in ('source_uv','source_geometry'):
        uv=obj.data.uv_layers.active.data[0].uv.copy(); co=obj.data.vertices[0].co.copy()
        if kind=='source_uv': obj.data.uv_layers.active.data[0].uv.x+=.02
        else: obj.data.vertices[0].co.x+=.02
        obj.data.update(); bpy.context.view_layer.update()
        check(kind+'_drift_refused',lambda:require(not attachment.check(session,{'fingerprint':state['fingerprint']})['matches']))
        obj.data.uv_layers.active.data[0].uv=uv; obj.data.vertices[0].co=co
        obj.data.update(); bpy.context.view_layer.update()
    bpy.ops.wm.save_userpref()
    check('saved_preferences_exclude_session_provider',lambda:require('ordinary' not in [a.module for a in bpy.context.preferences.addons]))
    (out/'report.json').write_text(json.dumps({'passed':all(c['passed'] for c in checks),'checks':checks,
        'runtime':cfg['runtime'],'limits':'Owned GUI fixtures only. No artist scene or third-party execution.'},indent=2))
    bpy.ops.wm.quit_blender()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--runtime',required=True); parser.add_argument('--blender',required=True); parser.add_argument('--out',required=True)
    parser.add_argument('--containment-only',action='store_true',help='Read native config location and exit without preference writes')
    args=parser.parse_args(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    (out/'config').mkdir(); (out/'extensions').mkdir()
    config=out/'config.json'; config.write_text(json.dumps({'out':str(out),'runtime':str(Path(args.runtime).resolve())}))
    startup=None
    if os.name=='nt':
        startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    env={**os.environ,'BLENDER_USER_CONFIG':str(out/'config'),'BLENDER_USER_EXTENSIONS':str(out/'extensions'),
         'TEMP':str(out/'temp'),'TMP':str(out/'temp')}; (out/'temp').mkdir()
    probe=out/'containment.py'
    probe.write_text("import bpy,json\nfrom pathlib import Path\n"+
        "expected=Path("+repr(str(out/'config'))+").resolve()\n"+
        "actual=Path(bpy.utils.user_resource('CONFIG')).resolve()\n"+
        "Path("+repr(str(out/'containment.json'))+").write_text(json.dumps({'expected':str(expected),'actual':str(actual),'passed':actual==expected,'preference_writes':False}))\n"+
        "assert actual==expected, 'Native configuration escaped owned directory'\n")
    with (out/'containment.log').open('x') as log:
        checked=subprocess.run([args.blender,'--background','--offline-mode','--factory-startup','--disable-autoexec',
            '--python-exit-code','1','--python',str(probe)],env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,timeout=60)
    if checked.returncode: raise SystemExit(checked.returncode)
    if args.containment_only:
        print((out/'containment.json').read_text()); return
    with (out/'native.log').open('x') as log:
        result=subprocess.run([args.blender,'--offline-mode','--factory-startup','--disable-autoexec','--python-exit-code','1',
            '--python',str(Path(__file__).resolve()),'--','--worker',str(config)],env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,timeout=180)
    report=json.loads((out/'report.json').read_text()) if (out/'report.json').exists() else {'passed':False}
    if report['passed']:
        sys.path.insert(0,str(Path(args.runtime).resolve()))
        from dcc_harness.native import run_worker
        from dcc_harness.evidence import write_json,file_hash
        import dcc_harness
        saved=json.loads((out/'ordinary-verify.json').read_text()); verify=out/'ordinary-verify'; verify.mkdir()
        write_json(verify/'capability-output.json',saved['result'])
        run_worker(args.blender,verify,Path(dcc_harness.__file__).with_name('_capability_blender.py'),'capability-verify',{
            'source':{'path':saved['candidate'],'sha256':file_hash(saved['candidate'])},
            'capability':{'root':saved['root'],'resolution':{'selected':{'recipe_id':saved['bundle']['id'],'recipe_digest':saved['bundle']['digest']}},
                'requirement':{'target_id':'cube'},'parameters':{'amount':.1},'effect_id':saved['effect_id']}},
            profile=saved['profile'],timeout=60)
        report['ordinary_independent_reopen']=json.loads((verify/'capability-verified.json').read_text())['passed']
    if report['passed']:
        reopen=out/'reopen-preferences.py'
        reopen.write_text("import bpy,json\nfrom pathlib import Path\n"+
            "assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path("+repr(str(out/'config'))+").resolve()\n"+
            "assert 'ordinary' not in [a.module for a in bpy.context.preferences.addons]\n"+
            "assert 'review_owned' not in [r.module for r in bpy.context.preferences.extensions.repos]\n"+
            "Path("+repr(str(out/'preferences-reopened.json'))+").write_text(json.dumps({'passed':True,'session_provider_persisted':False,'session_repository_persisted':False}))\n")
        with (out/'reopen-preferences.log').open('x') as log:
            reopened=subprocess.run([args.blender,'--background','--offline-mode','--disable-autoexec',
                '--python-exit-code','1','--python',str(reopen)],env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,timeout=60)
        if reopened.returncode: report['passed']=False
        else: report['preferences_reopened']=json.loads((out/'preferences-reopened.json').read_text())
        (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2)); raise SystemExit(not report['passed'] or result.returncode!=0)


if __name__=='__main__':
    if '--worker' in sys.argv: worker(sys.argv[sys.argv.index('--worker')+1])
    else: main()
