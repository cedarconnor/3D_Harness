"""Private worker for owned shader/async qualification. Never attach to an artist process."""
from pathlib import Path
import json
import sys
import time
import traceback
import array
import hashlib
import bpy

REQUEST_PATH = Path(sys.argv[sys.argv.index('--')+2])
REQUEST = json.loads(REQUEST_PATH.read_text())
sys.path.insert(0,REQUEST['runtime'])
from dcc_harness.data.bridge import recipes, addons
from dcc_harness.environments import load_profile
from dcc_harness.evidence import write_json, file_hash, digest
from dcc_harness.shader_graph import graph

def runtime_stamp():
    runtime=Path(REQUEST['runtime'])
    paths=sorted(p for p in (runtime/'dcc_harness').rglob('*') if p.suffix in ('.py','.json') and p.is_file())
    files={str(p.relative_to(runtime)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for name in ('qualify_shader_async.py','_shader_async_qualify.py'):
        p=Path(__file__).with_name(name)
        files['qualifier/'+name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return {'sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'files':files}


RUNTIME_BEFORE=runtime_stamp()

FOLDER = REQUEST_PATH.parent
PROFILE = load_profile(REQUEST['profile'])
REPORT = {'passed':False,'mode':'background' if bpy.app.background else 'live'}
HEARTBEAT = [0]
START = time.monotonic()


def finish(error=None):
    after=runtime_stamp()
    REPORT.update(runtime_sources_before=RUNTIME_BEFORE,runtime_sources_after=after,
                  runtime_sources_unchanged=RUNTIME_BEFORE==after)
    if RUNTIME_BEFORE!=after:
        REPORT.update(passed=False,error='Runtime sources changed during native worker')
    if error is not None:
        REPORT.update(passed=False,error=str(error),traceback=traceback.format_exc())
    REPORT.update(elapsed_seconds=time.monotonic()-START, heartbeat_ticks=HEARTBEAT[0],
                  outbound_attempts=addons.NETWORK_ATTEMPTS)
    if addons.NETWORK_ATTEMPTS: REPORT['passed']=False
    write_json(FOLDER / 'result.json',REPORT)
    if not bpy.app.background:
        bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=.1)


def render(label):
    scene=bpy.context.scene; settings=scene.render
    old={k:getattr(settings,k) for k in ('engine','resolution_x','resolution_y','resolution_percentage','filepath')}
    samples=scene.cycles.samples
    try:
        settings.engine='CYCLES'; scene.cycles.samples=8
        settings.resolution_x=settings.resolution_y=64; settings.resolution_percentage=100
        settings.filepath=str(FOLDER / (label+'.png'))
        bpy.ops.render.render(write_still=True)
    finally:
        scene.cycles.samples=samples
        for key,value in old.items():setattr(settings,key,value)
    image=bpy.data.images.load(str(FOLDER / (label+'.png')),check_existing=False)
    try:
        pixels=array.array('f',image.pixels[:])
        assert len(pixels)==64*64*4,'Shader render pixel buffer is incomplete'
        pixel_sha=hashlib.sha256(pixels.tobytes()).hexdigest()
    finally:bpy.data.images.remove(image)
    return {'path':str(FOLDER / (label+'.png')),'sha256':file_hash(FOLDER / (label+'.png')),
            'pixel_sha256':pixel_sha,'engine':'CYCLES','samples':8}


def setup():
    scene=bpy.context.scene; scene.render.engine=REQUEST['engine']
    for obj in scene.objects: obj['dcc_instance_id']=obj.name; obj['dcc_asset_id']=obj.name
    for mat in bpy.data.materials:mat['dcc_material_id']=mat.name
    target=bpy.data.objects['Cube']
    if not target.data.materials:
        mat=bpy.data.materials.new('FixtureMaterial');mat.use_nodes=True;target.data.materials.append(mat)
    target.material_slots[0].material['dcc_material_id']='fixture.material'
    if REQUEST['behavior'] in ('copy','shared_allowed'):
        shared=target.copy();shared.name='Shared';shared.data=target.data.copy();scene.collection.objects.link(shared)
        shared['dcc_instance_id']='Shared';shared['dcc_asset_id']='Shared';shared.location.x=3
        assert shared.material_slots[0].material==target.material_slots[0].material
    if REQUEST['behavior']=='shared_group':
        protected=bpy.data.node_groups.new('ProtectedSharedGroup','ShaderNodeTree')
        protected.interface.new_socket(name='Shader',in_out='OUTPUT',socket_type='NodeSocketShader')
        output=protected.nodes.new('NodeGroupOutput');shader=protected.nodes.new('ShaderNodeBsdfPrincipled')
        protected.links.new(shader.outputs['BSDF'],output.inputs['Shader'])
        value=protected.nodes.new('ShaderNodeValue');value.name='Value';value.outputs[0].default_value=.125
        protected.links.new(value.outputs[0],shader.inputs['Roughness'])
        other=bpy.data.materials.new('OtherMaterial');other.use_nodes=True;other['dcc_material_id']='other.material'
        other.node_tree.nodes.new('ShaderNodeGroup').node_tree=protected
        shared=target.copy();shared.name='Shared';shared.data=target.data.copy();scene.collection.objects.link(shared)
        shared['dcc_instance_id']='Shared';shared['dcc_asset_id']='Shared';shared.location.x=3
        shared.data.materials.clear();shared.data.materials.append(other)
        world=bpy.data.worlds.new('ProtectedWorld');world.use_nodes=True;world.use_fake_user=True
        world.node_tree.nodes.new('ShaderNodeGroup').node_tree=protected
    return scene


def shared_snapshot():
    shared=bpy.data.objects['Shared'];material=shared.material_slots[0].material
    return {'material_id':material.get('dcc_material_id'),'name':material.name,
            'graph_sha256':digest(graph(material.node_tree)),
            'users':sorted(o.get('dcc_instance_id') for o in bpy.data.objects
                           if any(slot.material==material for slot in o.material_slots))}


def shared_user_evidence(before):
    after=shared_snapshot();target=bpy.data.objects['Cube'].material_slots[0].material
    shared=bpy.data.objects['Shared'].material_slots[0].material
    if REQUEST['behavior']=='copy':
        assert target!=shared,'Single-user recipe kept the artist material shared'
        assert {key:before[key] for key in ('material_id','name','graph_sha256')}=={key:after[key] for key in ('material_id','name','graph_sha256')},'Copy recipe changed original artist material'
        assert after['users']==['Shared'],'Copy recipe rebound an undeclared material user'
        assert target.get('dcc_material_id')=='DCC::'+REQUEST['effect_id'][:48],'Copy recipe did not retain deterministic material identity'
        return {'policy':'single_user_copy','before':before,'after':after,
                'other_users_unchanged':True,'target_has_isolated_copy':True,
                'target_material_id':target.get('dcc_material_id')}
    assert target==shared,'All-users recipe silently isolated the target'
    assert before['users']==after['users']==['Cube','Shared'],'All-users affected-user declaration differs'
    assert before['graph_sha256']!=after['graph_sha256'],'Shared shader recipe made no shared native change'
    return {'policy':'all_users','before':before,'after':after,
            'declared_users_match':True,'shared_native_change':True,
            'target_material_id':target.get('dcc_material_id')}


def arguments():
    return [REQUEST['root'],REQUEST['recipe']['id'],REQUEST['recipe']['digest'],PROFILE,
        bpy.context.scene,'Cube',REQUEST['parameters'],REQUEST['effect_id']]


def verify():
    source=REQUEST['applied']['candidate']
    assert file_hash(source['path'])==source['sha256'],'Candidate file changed'
    bpy.ops.wm.open_mainfile(filepath=source['path'],load_ui=False)
    result=recipes.verify(*arguments(),REQUEST['applied']['result'])
    assert result['passed'] is True
    REPORT['verification']=result
    if REQUEST['behavior'] in ('copy','shared_allowed'):
        evidence=shared_user_evidence(REQUEST['applied']['shared_user_evidence']['before'])
        assert evidence==REQUEST['applied']['shared_user_evidence'],'Saved shared-user evidence differs'
        REPORT['shared_user_evidence']=evidence
    # A target-perfect shader cannot hide a stale protected world after reopen.
    world=bpy.context.scene.world
    assert world is not None and world.use_nodes,'Owned fixture requires a measured world graph'
    background=next(node for node in world.node_tree.nodes if node.type=='BACKGROUND')
    strength=background.inputs['Strength'];original_strength=strength.default_value
    try:
        strength.default_value=original_strength+.25
        bpy.context.view_layer.update()
        try:recipes.verify(*arguments(),REQUEST['applied']['result'])
        except ValueError as exc:
            assert 'Saved protected scene state' in str(exc),'Protected world mutation failed for an unrelated reason: '+str(exc)
            REPORT['protected_state_stale_refused']=True
        else:raise AssertionError('Protected world mutation satisfied saved native evidence')
    finally:
        strength.default_value=original_strength
        bpy.context.view_layer.update()
    assert recipes.verify(*arguments(),REQUEST['applied']['result'])['passed'] is True,'Restored protected world did not restore valid evidence'
    # Native nested change and selected-effect deletion must invalidate saved evidence.
    spec=recipes.inspect_bundle(*arguments()[:3])['recipe']['effect']
    target=bpy.data.objects['Cube']; name='DCC::'+REQUEST['effect_id'][:48]
    material=target.material_slots[spec.get('slot',0)].material
    if spec['kind']=='shader_nodes':
        node=material.node_tree.nodes[name]
        nested=next(n for n in node.node_tree.nodes if n.type=='GROUP')
        shader=next(n for n in nested.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        shader.inputs['Base Color'].default_value=(.01,.99,.02,1)
        try:recipes.verify(*arguments(),REQUEST['applied']['result'])
        except ValueError:REPORT['nested_stale_refused']=True
        else:raise AssertionError('Nested shader mutation satisfied stale evidence')
        material.node_tree.nodes.remove(node)
    else:
        target.material_slots[spec['slot']].material=None
    try:recipes.verify(*arguments(),REQUEST['applied']['result'])
    except ValueError:REPORT['deleted_effect_refused']=True
    else:raise AssertionError('Deleted effect satisfied stale evidence')
    REPORT['passed']=True


def preference_state():
    prefs=bpy.context.preferences;entry=prefs.addons.get('shader_async_fixture')
    return {'entries':sorted(item.module for item in prefs.addons),
            'quality':entry.preferences.quality if entry and entry.preferences else None,
            'autosave':prefs.use_preferences_save}


class Qualification:
    def __init__(self):
        import shader_async_fixture as provider
        self.provider=provider; self.operation=None; self.stage=0; self.results=[]
        self.baseline_preferences=preference_state(); self.submitted_at=None
        self.started=time.monotonic(); self.last_step=0
        setup()
        self.shared_before=shared_snapshot() if REQUEST['behavior'] in ('copy','shared_allowed') else None
        self.initial_nodes=len(bpy.data.node_groups)
        self.before=render('before') if REQUEST['expect']=='success' else None
        bpy.ops.wm.save_as_mainfile(filepath=str(FOLDER / 'before.blend'))
        bpy.ops.wm.open_mainfile(filepath=str(FOLDER / 'before.blend'),load_ui=False)
        self.shared_before=shared_snapshot() if REQUEST['behavior'] in ('copy','shared_allowed') else None
        self.initial_nodes=len(bpy.data.node_groups)

    def cancelled(self):
        return REQUEST['behavior']=='cancel' and bool(self.provider.JOBS) and time.monotonic()-max(job['started'] for job in self.provider.JOBS.values())>=.15

    def invoke(self):
        if REQUEST['asynchronous']:
            if self.operation is None:
                from dcc_harness.data.bridge.recipe_v2 import start
                self.submitted_at=time.monotonic()
                self.operation=start(*arguments(),folder=FOLDER / ('operation-'+str(self.stage)),cancelled=self.cancelled)
            status=self.operation.step()
            state=status.get('state')
            REPORT.setdefault('transitions',[]).append(state)
            if state not in ('SUCCEEDED','FAILED','CANCELLED','RECONCILIATION_REQUIRED','NEEDS_RECONCILIATION','TIMED_OUT'):
                return None
            if state=='NEEDS_RECONCILIATION':
                assert REQUEST['behavior']=='cancel_refuses','Unexpected provider uncertainty: '+repr(status)
                operation=self.operation;lease=operation.lease
                assert lease is not None and not lease.closed,'Uncertain provider lost its active guard'
                counts=dict(self.provider.COUNTS)
                assert counts['cancel']==1 and counts['collect']==0,'Uncertain provider cancellation/collection count differs'
                operation.request_stop()
                pending=operation.confirm_stopped()
                assert pending is False or (isinstance(pending,dict) and pending.get('state')=='PENDING'),'Pending provider was reported stopped'
                assert not lease.closed and not operation.closed,'Pending provider cleanup released its guard'
                assert self.provider.COUNTS['cancel']==1,'Stop request replayed cancellation'
                REPORT['unresolved_provider_guard_retained']=True
                # Only this owned synthetic provider is stopped externally. This
                # does not mutate native scene data or reinterpret a success receipt.
                for job in self.provider.JOBS.values():job['state']='cancelled'
                stopped=operation.confirm_stopped()
                assert stopped is True or (isinstance(stopped,dict) and stopped.get('state')=='STOPPED'),'Provider termination was not confirmed'
                assert lease.closed and operation.closed,'Confirmed provider termination did not restore the guard'
                assert self.provider.COUNTS['cancel']==1 and self.provider.COUNTS['collect']==0,'Recovery replayed cancel or collected uncertain output'
                REPORT.update(confirmed_terminal_cleanup=True,
                    recovery_coverage='Native uncertain-stop guard retention and confirmed cleanup; process-loss replay guards are covered by portable lifecycle tests.')
            else:
                assert state in ('SUCCEEDED','FAILED','CANCELLED'),'Unconfirmed terminal state must retain its guard: '+repr(status)
                self.operation.close()
            self.operation=None
            if state!='SUCCEEDED':
                if REQUEST['expect']=='success':raise AssertionError('Unexpected terminal status '+repr(status))
                REPORT.update(terminal=status, passed=True)
                return False
            return status['result']
        try:
            return recipes.apply(*arguments())
        except Exception as exc:
            if REQUEST['expect']=='success':raise
            REPORT.update(terminal={'state':'REFUSED','error':str(exc)},passed=True)
            return False

    def step(self):
        try:
            if time.monotonic()-self.started>45:raise TimeoutError('Owned qualification worker deadline')
            result=self.invoke()
            if result is None:return .05
            if result is False:
                self.complete();return None
            if REQUEST['expect']!='success':raise AssertionError('Negative qualification produced successful effect evidence')
            self.results.append(result)
            if self.stage==0:
                assert result['changed'],'Initial recipe produced no measured native change'
                self.stage=1;return .05
            if self.stage==1:
                assert result['after']==self.results[0]['after'],'Repeated recipe duplicated or changed native output'
                assert result['output']==self.results[0]['output'],'Repeated effect output differs'
                REQUEST['parameters']['amount']=.75;self.stage=2;return .05
            assert result['output']!=self.results[0]['output'],'Parameter update did not change shader output'
            spec=recipes.inspect_bundle(*arguments()[:3])['recipe']['effect']
            expected_groups=self.initial_nodes+(2 if spec['kind']=='shader_nodes' else 0)
            assert len(bpy.data.node_groups)==expected_groups,'Repeat/update leaked duplicate shader groups'
            if self.shared_before is not None:REPORT['shared_user_evidence']=shared_user_evidence(self.shared_before)
            REPORT.update(result=result, repeat=self.results[1], initial=self.results[0],
                renders={'before':self.before,'after':render('after')})
            assert REPORT['renders']['before']['pixel_sha256']!=REPORT['renders']['after']['pixel_sha256'],'Shader render pixels did not change'
            bpy.ops.wm.save_as_mainfile(filepath=str(FOLDER / 'candidate.blend'))
            REPORT['candidate']={'path':str(FOLDER / 'candidate.blend'),'sha256':file_hash(FOLDER / 'candidate.blend')}
            REPORT['passed']=True
            self.complete();return None
        except Exception as exc:
            if self.operation is not None:
                record=self.operation.operation._record
                if record['state'] in ('SUCCEEDED','FAILED','CANCELLED') or not self.operation.submitted:
                    try:self.operation.close()
                    except Exception:pass
                else:
                    REPORT['failed_worker_guard_retained']=bool(self.operation.lease and not self.operation.lease.closed)
            finish(exc);return None

    def complete(self):
        counts=dict(self.provider.COUNTS);quality=list(self.provider.QUALITY)
        REPORT.update(provider_counts=counts, provider_quality_reads=quality,
                      provider_timer_ticks=sum(job['ticks'] for job in self.provider.JOBS.values()))
        assert all(v==3 for v in quality),'Provider profile preferences expired during lifecycle'
        assert preference_state()==self.baseline_preferences,'Preferences were not restored'
        if REQUEST['expect']!='success':
            assert not (FOLDER/'candidate.blend').exists(),'Negative job retained a completion candidate'
            terminal=REPORT.get('terminal',{}); behavior=REQUEST['behavior'];state=terminal.get('state')
            error=terminal.get('error','');reason=terminal.get('reason','')
            if behavior=='noop':
                assert state=='REFUSED' and ('owned native nodes' in error or 'measured owned effect' in error or 'native material is missing' in error),'Noop failed for an unrelated reason: '+repr(terminal)
            elif behavior=='shared_group':
                assert state=='REFUSED' and 'protected scene state' in error,'Shared group failed for an unrelated reason: '+repr(terminal)
            elif behavior in ('cancel','hang'):
                assert state=='CANCELLED' and counts['cancel']==1,'Cancellation was not confirmed exactly once: '+repr(terminal)
                if behavior=='hang':assert reason=='Deadline expired','Timeout did not initiate cancellation'
            elif behavior=='fail':
                assert state=='FAILED','Provider failure was not retained: '+repr(terminal)
            elif behavior=='cancel_refuses':
                assert REPORT.get('unresolved_provider_guard_retained') and REPORT.get('confirmed_terminal_cleanup'),'Native recovery assertions were not completed'
                assert state=='NEEDS_RECONCILIATION' and counts['cancel']==1 and 'grace' in error.lower(),'Unconfirmed cancellation was not reconciled: '+repr(terminal)
        if REQUEST['asynchronous']:
            expected=3 if REQUEST['expect']=='success' else 1
            assert counts['submit']==expected,'Submit was replayed or omitted'
            assert counts['collect']==(3 if REQUEST['expect']=='success' else 0),'Collect replayed or ran before success'
            if not bpy.app.background and REQUEST['expect']=='success':
                assert REPORT['provider_timer_ticks']>0 and HEARTBEAT[0]>=3,'Live provider or UI timer failed to progress'
        REPORT['preferences_restored']=True
        finish()


def heartbeat():HEARTBEAT[0]+=1;return .025

try:
    if REQUEST.get('verify'):
        verify();finish()
    elif bpy.app.background:
        qualification=Qualification()
        while qualification.step() is not None:time.sleep(.05)
    else:
        def begin_gui():
            global qualification
            try:
                qualification=Qualification()
                bpy.app.timers.register(heartbeat,first_interval=.01)
                bpy.app.timers.register(qualification.step,first_interval=.1)
            except Exception as exc:finish(exc)
            return None
        bpy.app.timers.register(begin_gui,first_interval=.05)
except Exception as exc:finish(exc)
