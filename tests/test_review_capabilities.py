"""Review regressions: freshness, source review, retention and recovery evidence."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from dcc_harness import capabilities as cap, environments, recipes, provider_sources
from dcc_harness.evidence import digest, write_json
import test_capability_lifecycle as lifecycle
from coordination_helpers import Fixture
import test_environments as environment_tests
from test_recipes import recipe


class FreshnessTests(Fixture):
    bind_capability=lifecycle.LifecycleTests.bind_capability
    def test_geometry_only_requirement_survives_material_edit(self):
        from test_capabilities import policy
        value=policy(); value['rules'][0]['dependencies']=['geometry']
        self.bind_capability(value)
        before=cap.requirements(self.root,'direction',self.obs)
        changed=copy.deepcopy(self.obs); changed['materials']['stone']['diffuse_color']=[1,0,0,1]
        self.assertEqual(cap.requirements(self.root,'direction',changed),before)


class EffectAdmissionTests(unittest.TestCase):
    def test_nonmodifier_effects_refused_at_recipe_admission(self):
        for kind in ('geometry','materials','nodes','transform'):
            with self.subTest(kind=kind):
                value=recipe(); value['coverage']['writes']=[kind]
                with self.assertRaisesRegex(ValueError,'modifier effect'):
                    recipes.validate(value)

    def test_modifier_with_material_geometry_side_effects_remains_admitted(self):
        value=recipe(); value['coverage']['writes']=['modifiers','materials','geometry']
        self.assertEqual(recipes.validate(value),value)


class SourceReviewTests(unittest.TestCase):
    setUp=environment_tests.EnvironmentTests.setUp
    scan=environment_tests.EnvironmentTests.scan
    item=environment_tests.EnvironmentTests.item

    def test_source_reviews_reject_wrong_container_even_for_offline_provider(self):
        with self.assertRaises(ValueError):
            environments.create_profile(self.root,self.scan(),['harness_fixture'],{},reviews=[])

    def test_simultaneous_profile_creation_publishes_one_complete_identity(self):
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor
        inv=self.scan(); active=0; peak=0; mutex=threading.Lock()
        original=environments.write_json
        def delayed(path,value):
            nonlocal active,peak
            with mutex: active+=1; peak=max(peak,active)
            try:
                time.sleep(.1)
                return original(path,value)
            finally:
                with mutex: active-=1
        with patch.object(environments,'write_json',side_effect=delayed),ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:environments.create_profile(self.root,inv,['harness_fixture'],{}),range(4)))
        self.assertEqual(peak,1)
        self.assertTrue(all(result==results[0] for result in results))
        self.assertEqual(environments.load_profile(results[0])['providers'][0]['id'],'harness_fixture')
    def test_unknown_network_needs_source_bound_review(self):
        inv=self.scan(); item=self.item(inv,'harness_fixture'); item['network']='unknown'
        with self.assertRaisesRegex(ValueError,'review'):
            environments.create_profile(self.root,inv,['harness_fixture'],{})

    def test_unknown_network_review_is_bound_to_source(self):
        inv=self.scan(); item=self.item(inv,'harness_fixture'); item['network']='unknown'
        reviews={item['id']:{'source_digest':item['source_digest'],'reviewed_by':'agent',
                            'reason':'Inspected local source; no network dependency'}}
        ref=environments.create_profile(self.root,inv,['harness_fixture'],{},reviews=reviews)
        profile=environments.load_profile(ref)
        environments.validate_profile(profile,inv)
        item['source_digest']='f'*64
        with self.assertRaisesRegex(ValueError,'review|STALE'):
            environments.validate_profile(profile,inv)


class RetentionTests(unittest.TestCase):
    def test_temporary_inventory_cleans_success_and_retains_discoverable_failure(self):
        folders=[]
        def worker(blender,folder,*args,**kwargs):
            folders.append(folder); write_json(folder/'inventory.json',{'providers':[]})
        with patch.object(environments,'run_worker',side_effect=worker):
            self.assertEqual(environments.inventory(blender='fixture'),{'providers':[]})
        self.assertFalse(folders[0].exists())
        def failed(blender,folder,*args,**kwargs):
            folders.append(folder); raise RuntimeError('failed discovery')
        with patch.object(environments,'run_worker',side_effect=failed),self.assertRaisesRegex(RuntimeError,'evidence retained at'):
            environments.inventory(blender='fixture')
        self.assertTrue(folders[-1].exists())
        self.assertEqual(folders[-1].resolve().parent,Path(tempfile.gettempdir()).resolve())
        __import__('shutil').rmtree(folders[-1])

    def test_stale_registration_does_not_hide_valid_later_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); good=root/'good.json'; write_json(good,{})
            from dcc_harness.files import file_hash
            records=[{'profile_digest':'p','report':str(root/'gone.json'),'sha256':'a'*64},
                     {'profile_digest':'p','report':str(good),'sha256':file_hash(good)}]
            with patch.object(recipes,'load',return_value={'recipe':{}}),patch.object(recipes,'registrations',return_value=records),patch.object(recipes,'check_report',return_value={'recipe_digest':'r','contexts':['live']}):
                self.assertEqual(recipes.require_qualified(root,'id','r',context='live',profile_digest='p')['qualification'],records[1])

    def test_python_api_mapping_accepts_native_target_and_parameter(self):
        value=recipe(); value['invocation']['arguments']={'object':'target','width':'parameter:amount','name':'effect_name'}
        self.assertEqual(recipes.validate(value)['invocation']['arguments']['width'],'parameter:amount')
        value['invocation']['arguments']['width']='parameter:missing'
        with self.assertRaises(ValueError): recipes.validate(value)


class RecoverySnapshotTests(unittest.TestCase):
    def test_native_bevel_capture_accepts_hash_bound_noise_and_refuses_authored_changes(self):
        import subprocess
        import sys
        from test_live_review import STUBS
        fixture=Path(__file__).parent/'fixtures/bevel-recovery-noise.json'
        code=STUBS+'''
import json, tempfile, uuid, copy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from dcc_harness import live_snapshot as snap
from dcc_harness.data.bridge import recovery
data=json.loads(Path(FIXTURE).read_text()); before,after=data['before'],data['after']
assert snap.fingerprint(before)!=snap.fingerprint(after)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); identity=snap.retain(root,before)
    session=SimpleNamespace(project=root,scene='Scene',active=None,generation='generation')
    for field in (None,'source_uv_hash','source_mesh_hash','source_attribute_hash','geometry_hash','modifier_settings'):
        current=copy.deepcopy(after)
        if field: next(iter(current['objects'].values()))[field]='authored change'
        op=str(uuid.uuid4()); folder=root/op; folder.mkdir()
        jobs=SimpleNamespace(session=session,folder=lambda _:folder,status=lambda _:{'state':'FAILED'})
        with mock.patch.object(recovery.attachment,'scene_for'), mock.patch.object(recovery.attachment,'snapshot',return_value=current), mock.patch.object(recovery,'inventory',return_value={}), mock.patch.object(recovery.attachment,'save_copy',side_effect=RuntimeError('copy reached')) as save:
            payload={'operation_id':op,'decision':'keep-current','expected_fingerprint':identity,'attempt_id':str(uuid.uuid4())}
            if field:
                result=recovery.capture(jobs,payload)
                assert result['state']=='REFUSED_BEFORE_MUTATION' and not (folder/'recovery').exists()
                save.assert_not_called()
            else:
                try: recovery.capture(jobs,payload)
                except RuntimeError as exc: assert str(exc)=='copy reached'
                else: raise AssertionError('BEVEL recovery refused equivalent observed state')
'''
        result=subprocess.run([sys.executable,'-c','FIXTURE='+repr(str(fixture.resolve()))+'\n'+code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_hash_bound_observation_accepts_only_evaluated_uv_noise(self):
        from test_live_snapshot import SnapshotTests
        from dcc_harness import live_snapshot as snap
        before=SnapshotTests().snapshot(); after=copy.deepcopy(before)
        after['objects']['cube']['evaluated_uv_values']['UVMap']=[.4937500059604645]
        after['objects']['cube']['uv_hash']='different extraction'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); identity=snap.retain(root,before)
            self.assertTrue(snap.matches_retained(root,identity,after))
            for key in ('source_uv_hash','source_mesh_hash','source_attribute_hash','geometry_hash'):
                changed=copy.deepcopy(after); changed['objects']['cube'][key]='authored change'
                self.assertFalse(snap.matches_retained(root,identity,changed))
            path=root/'live/observations'/(identity+'.json'); path.write_text(__import__('json').dumps(after))
            with self.assertRaisesRegex(ValueError,'changed'):
                snap.matches_retained(root,identity,after)
