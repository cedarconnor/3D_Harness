"""Behavioral tests at the portable async/native integration boundary."""
import contextlib
import copy
import importlib.util
import json
import runpy
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest import mock
import uuid


BRIDGE = Path(__file__).resolve().parents[1] / 'dcc_harness/data/bridge'
NS = types.SimpleNamespace


class AsyncNativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = '_async_native_test_' + uuid.uuid4().hex
        self.modules = {}
        package = types.ModuleType(self.package)
        package.__path__ = [str(BRIDGE)]
        self.modules[self.package] = package
        self.saved = []
        self.scene = NS(name='OwnedFixture')
        self.bpy = NS(context=NS(view_layer=NS(update=lambda: None)),
                      app=NS(background=False, timers=NS(register=lambda *a, **k: None)),
                      data=NS(materials=[], worlds=[]))
        self.modules['bpy'] = self.bpy
        self.module('addons', ACTIVE_LEASE=None)
        self.attachment = self.module('attachment', scene_for=lambda scene: self.scene,
            snapshot=lambda scene: {'scene': 'snapshot'}, fingerprint=lambda value: 'fingerprint',
            equivalent=lambda a, b: a == b,
            save_copy=lambda session, path: self.saved.append(str(path)) or {'path': str(path), 'sha256': 'saved'})
        self.module('operations')
        from dcc_harness import files
        self.module('files', **{name: getattr(files, name) for name in
            ('copy_verified', 'file_hash', 'json_bytes', 'reject_links', 'write_exclusive')})
        from dcc_harness.evidence import digest
        self.module('identity', digest=digest)
        self.module('adoption_inventory_blender', inventory=lambda scene: {})
        self.patch = mock.patch.dict(sys.modules, self.modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def module(self, name, **attributes):
        module = types.ModuleType(self.package + '.' + name)
        module.__dict__.update(attributes)
        self.modules[module.__name__] = module
        if hasattr(self, 'patch'):
            sys.modules[module.__name__] = module
        return module

    def load(self, name):
        fullname = self.package + '.' + name
        spec = importlib.util.spec_from_file_location(fullname, BRIDGE / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)
        return module

    def manager(self, state='PENDING'):
        jobs = self.load('jobs')
        identity = str(uuid.uuid4())
        session = NS(project=self.root, generation=4, active=identity, scene='fixture')
        manager = jobs.Jobs(session)
        folder = manager.folder(identity)
        folder.mkdir(parents=True)
        request = {'deadline': float('inf'), 'output': str(folder / 'candidate.blend'),
                   'live': {'recipe': 'capability.recipe', 'target': 'target'}}
        for name, data in [('live-request.json', request),
                           ('live-prepared.json', {'generation': 4, 'expires_at': float('inf'), 'fingerprint': 'fingerprint'}),
                           ('live-before.json', {'scene': 'original'})]:
            (folder / name).write_text(json.dumps(data))
        calls = []
        def step():
            calls.append('step')
            return {'state': state, 'phase': 'POLL', 'progress': 0.5,
                    'operation_id': identity, 'poll_interval': 0.25, 'result': {'native': 'proof'}}
        execution = NS(step=step)
        manager.async_operations[identity] = (execution, request, 4)
        return manager, identity, folder, calls

    def test_existing_async_timer_tick_advances_instead_of_rechecking_initial_snapshot(self):
        manager, identity, folder, calls = self.manager()
        self.attachment.snapshot = lambda scene: (_ for _ in ()).throw(AssertionError('Initial snapshot was reentered'))
        self.assertEqual(manager.run(identity), 0.25)
        self.assertEqual(calls, ['step'])
        self.assertEqual(manager.status(identity)['state'], 'RUNNING')
        self.assertEqual(self.saved, [])

    def test_existing_async_cancelled_tick_still_advances_provider_cancellation(self):
        manager, identity, folder, calls = self.manager()
        (folder / 'live-cancel.json').write_text('{}')
        self.assertEqual(manager.run(identity), 0.25)
        self.assertEqual(calls, ['step'])
        self.assertEqual(self.saved, [])

    def test_pending_returns_timer_interval_without_saving_output(self):
        manager, identity, folder, calls = self.manager()
        self.assertEqual(manager.advance_async(identity), 0.25)
        self.assertEqual(calls, ['step'])
        self.assertFalse((folder / 'capability-output.json').exists())
        self.assertFalse((folder / 'live-snapshot.json').exists())
        self.assertEqual(self.saved, [])

    def test_terminal_failures_never_save_or_write_native_output(self):
        for state in ('FAILED', 'CANCELLED', 'NEEDS_RECONCILIATION'):
            with self.subTest(state=state):
                manager, identity, folder, calls = self.manager(state)
                self.assertIsNone(manager.advance_async(identity))
                self.assertEqual(manager.status(identity)['state'], 'NEEDS_RECONCILIATION')
                self.assertFalse((folder / 'capability-output.json').exists())
                self.assertEqual(self.saved, [])

    def test_changed_session_blocks_provider_step_and_output(self):
        manager, identity, folder, calls = self.manager('SUCCEEDED')
        manager.session.generation += 1
        self.assertIsNone(manager.advance_async(identity))
        self.assertEqual(calls, [])
        self.assertEqual(self.saved, [])
        self.assertFalse((folder / 'capability-output.json').exists())

    def execution(self, folder=None, adapter_init=None):
        self.native = {'transform': [0, 0, 0], 'materials': {'output': 0}}
        self.protected = {'artist': 'retained'}
        self.provider_calls = []
        recipe = {'invocation': {'completion': 'asynchronous', 'submit': 'async_test_provider.submit',
            'poll': 'async_test_provider.poll', 'cancel': 'async_test_provider.cancel',
            'collect': 'async_test_provider.collect', 'poll_interval': 60, 'timeout': 600, 'cancel_grace': 5},
            'coverage': {'reads': ['transform'], 'dependencies': [], 'writes': ['materials']},
            'update': {'shared_materials': 'all_users'}}
        context = {'recipe': recipe, 'scene': self.scene, 'target_id': 'target', 'target': NS(),
                   'parameters': {}, 'effect_id': 'effect', 'shared_users': [],
                   'provider': {'module': 'async_test_provider'}}
        def invoke(*args, **kwargs):
            self.provider_calls.append('submit')
            return {'job': 1}
        adapter = NS(preflight=lambda *args: {'ready': True, 'shared_users': []},
                     apply=lambda ctx, parameters, effect: ctx['invoke']())
        def adapter_for(bundle):
            if adapter_init is not None:
                adapter_init(self)
            return adapter
        self.module('recipes', prepare_context=lambda *args: ({'recipe': recipe}, context),
            measurements=lambda *args: copy.deepcopy(self.native), native_effect=lambda *args, **kwargs: None,
            adapter_for=adapter_for, load=lambda *args: None,
            context_for=lambda *args: contextlib.nullcontext(), invoke_declared=invoke)
        self.lease_closes = []
        from dcc_harness import offline
        def offline_call(function):
            def bounded(*args, **kwargs):
                with offline.scope([]):
                    return function(*args, **kwargs)
            return bounded
        self.module('addons', assert_profile=lambda profile: None,
            scope=offline.scope, NETWORK_ATTEMPTS=[], ACTIVE_LEASE=None, offline_call=offline_call,
            session_preferences=lambda *args, **kwargs: contextlib.nullcontext(),
            AsyncProfileLease=lambda *args: NS(close=lambda: self.lease_closes.append(True)))
        self.module('recipe_effects', ownership_before=lambda context: set(),
            allowed_materials=lambda context: set(), preserved=lambda *args: copy.deepcopy(self.protected))
        provider = types.ModuleType('async_test_provider')
        def poll(*args):
            self.provider_calls.append('poll')
            return {'state': 'PENDING'}
        provider.poll = poll
        provider.cancel = lambda *args: {'requested': True}
        provider.collect = lambda *args: {'status': 'FINISHED'}
        sys.modules['async_test_provider'] = provider
        module = self.load('recipe_v2')
        execution = module.RecipeExecution(self.root, 'recipe', 'digest', {}, self.scene,
            'target', {}, 'effect', folder=folder or self.root / 'provider')
        return execution

    def test_reconstructed_pending_journal_never_invokes_provider(self):
        execution = self.execution()
        self.assertEqual(execution.step()['state'], 'PENDING')
        restored = self.execution()
        self.assertEqual(restored.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.provider_calls, [])
        self.assertEqual(self.saved, [])

    def test_protected_scene_is_checked_on_throttled_tick_before_provider_progress(self):
        execution = self.execution()
        execution.step()
        execution.step()
        self.assertEqual(self.provider_calls, ['submit', 'poll'])
        self.protected['artist'] = 'externally changed'
        status = execution.step()
        self.assertEqual(status['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.provider_calls, ['submit', 'poll'])

    def test_declared_read_input_checked_on_every_throttled_tick(self):
        execution = self.execution()
        execution.step()
        execution.step()
        self.native['transform'] = [1, 0, 0]
        self.assertEqual(execution.step()['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.provider_calls, ['submit', 'poll'])

    def test_declared_write_progress_is_permitted_between_ticks(self):
        execution = self.execution()
        execution.step()
        execution.step()
        self.native['materials']['output'] = 2
        self.assertEqual(execution.step()['state'], 'PENDING')
        self.assertEqual(self.provider_calls, ['submit', 'poll'])

    def run_worker(self, execution):
        from dcc_harness.files import file_hash
        source = self.root / 'source.blend'
        source.write_bytes(b'owned source')
        request = {'source': {'path': str(source), 'sha256': file_hash(source)},
                   'profile': 'profile', 'operation_id': str(uuid.uuid4()),
                   'output': str(self.root / 'candidate.blend'),
                   'capability': {'root': str(self.root), 'resolution': {'selected': {
                       'recipe_id': 'recipe', 'recipe_digest': 'digest'}},
                       'requirement': {'target_id': 'target'}, 'parameters': {}, 'effect_id': 'effect'}}
        path = self.root / 'request.json'
        path.write_text(json.dumps(request))
        self.bpy.app.background = True
        self.bpy.context.scene = self.scene
        self.bpy.ops = NS(wm=NS(open_mainfile=lambda **kwargs: None,
            save_as_mainfile=lambda **kwargs: self.saved.append(kwargs['filepath'])))
        bridge = types.ModuleType('dcc_harness.data.bridge')
        bridge.__path__ = [str(BRIDGE)]
        bridge.recipes = NS(inspect_bundle=lambda *args: {'recipe': {'invocation': {'completion': 'asynchronous'}}})
        native = self.load('recipe_v2')
        bridge.recipe_v2 = NS(start=lambda *args, **kwargs: execution, drive=native.drive)
        environments = types.ModuleType('dcc_harness.environments')
        environments.load_profile = lambda path: {}
        environments.assert_worker_profile = lambda request: None
        modules = {'dcc_harness.data.bridge': bridge, 'dcc_harness.environments': environments}
        with mock.patch.dict(sys.modules, modules), mock.patch.object(sys, 'argv', ['worker', '--', 'execute', str(path)]), mock.patch.object(sys, 'path', list(sys.path)):
            runpy.run_path(str(BRIDGE.parents[1] / '_capability_blender.py'), run_name='__main__')

    def test_owned_background_worker_terminal_failure_never_saves_or_writes_output(self):
        # Load the real driver while replacing only the external Blender/provider boundary.
        self.execution()
        for state in ('FAILED', 'CANCELLED', 'NEEDS_RECONCILIATION'):
            with self.subTest(state=state):
                execution = NS(step=lambda: {'state': state, 'error': 'provider stopped'})
                with self.assertRaisesRegex(ValueError, state):
                    self.run_worker(execution)
                self.assertEqual(self.saved, [])
                self.assertFalse((self.root / 'capability-output.json').exists())

    def test_owned_background_worker_restored_journal_never_mutates_or_saves(self):
        first = self.execution(folder=self.root / 'async-provider')
        self.assertEqual(first.step()['state'], 'PENDING')
        restored = self.execution(folder=self.root / 'async-provider')
        with self.assertRaisesRegex(ValueError, 'NEEDS_RECONCILIATION'):
            self.run_worker(restored)
        self.assertEqual(self.provider_calls, [])
        self.assertEqual(self.saved, [])
        self.assertFalse((self.root / 'capability-output.json').exists())

    def test_gui_driver_refuses_to_block_before_any_provider_step(self):
        self.execution()
        module = self.load('recipe_v2')
        calls = []
        execution = NS(step=lambda: calls.append('step'))
        with self.assertRaisesRegex(ValueError, 'Never block Blender UI'):
            module.drive(execution)
        self.assertEqual(calls, [])

    def test_preexisting_material_and_shader_node_require_ownership_markers(self):
        effects = self.effects()
        class Native(dict):
            def __bool__(self):
                return True
            def as_pointer(self):
                return id(self)
        node = Native()
        node.name = 'OwnedNode'
        material = Native(dcc_material_id='OwnedMaterial')
        material.node_tree = NS(nodes=[node])
        self.bpy.data.materials = [material]
        for kind in ('material', 'shader_nodes'):
            with self.subTest(kind=kind):
                spec = {'kind': kind, 'material_id': 'OwnedMaterial', 'slot': 0, 'nodes': ['OwnedNode']}
                context = {'recipe': {'effect': spec}, 'effect_id': 'effect'}
                with self.assertRaisesRegex(ValueError, 'unowned'):
                    effects.ownership_before(context)
                item = material if kind == 'material' else node
                item['dcc_effect_id'] = 'effect'
                original = effects.ownership_before(context)
                del item['dcc_effect_id']
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    effects.claim(context, original)

    def test_final_inspector_cannot_mutate_protected_scene(self):
        execution = self.execution()
        recipes = sys.modules[self.package + '.recipes']
        effects = sys.modules[self.package + '.recipe_effects']
        recipes.PROVEN_INVOCATIONS = {}
        recipes.native_effect = lambda *args, **kwargs: {'kind': 'owned-native'}
        effects.claim = lambda *args: None
        def inspect_output(*args):
            self.protected['artist'] = 'undeclared inspector mutation'
            return {'effect_id': 'effect', 'effect_count': 1, 'measurements': {'effect': True}}
        recipes.output_record = inspect_output
        sys.modules['async_test_provider'].poll = lambda *args: {'state': 'SUCCEEDED'}
        self.assertEqual(execution.step()['state'], 'PENDING')
        status = execution.step()
        self.assertEqual(status['state'], 'NEEDS_RECONCILIATION')
        self.assertNotIn('result', status)

    def test_adapter_import_cannot_change_declared_writes_before_provider_submission(self):
        def adapter_init(fixture):
            fixture.native['materials']['output'] = 1
        try:
            execution = self.execution(adapter_init=adapter_init)
        except ValueError:
            self.assertEqual(self.provider_calls, [])
        else:
            status = execution.step()
            self.assertEqual(status['state'], 'NEEDS_RECONCILIATION')
            self.assertEqual(self.provider_calls, [])

    def test_adapter_import_executes_under_offline_guard(self):
        from dcc_harness import offline
        blocked = []
        def adapter_init(fixture):
            try:
                # Real Python audit event; no actual network connection is made.
                sys.audit('socket.connect', None, ('owned-fixture.invalid', 443))
            except RuntimeError:
                blocked.append(True)
        with mock.patch.object(offline, 'ACTIVE', []), mock.patch.object(offline, 'LEASES', {}):
            with offline.scope([]):
                pass  # Ensure the real process audit hook is installed.
            self.execution(adapter_init=adapter_init)
        self.assertEqual(blocked, [True])

    def recovery_fixture(self):
        manager, identity, folder, calls = self.manager('NEEDS_RECONCILIATION')
        manager.session.session_id = 'owned-session'
        released = []
        manager.session.release = lambda op: released.append(op)
        self.attachment.matches_retained = lambda *args: True
        self.attachment.check = lambda *args: {'generation': 4, 'matches': True}
        self.bpy.data.filepath = 'owned.blend'
        recovery = self.load('recovery')
        payload = {'operation_id': identity, 'decision': 'keep-current',
                   'expected_fingerprint': 'fingerprint', 'attempt_id': str(uuid.uuid4())}
        (folder / 'recovery').mkdir()
        (folder / 'recovery/receipt.json').write_text(json.dumps({'fingerprint': 'fingerprint',
            'snapshot': 'snapshot.json', 'generation': 4, 'decision': 'keep-current'}))
        return recovery, manager, identity, folder, payload, released

    def test_recovery_capture_and_ack_refuse_unclosed_provider_without_callbacks(self):
        recovery, manager, identity, folder, payload, released = self.recovery_fixture()
        execution = NS(lease=NS(closed=False), closed=False)
        manager.async_operations[identity] = (execution, {}, 4)
        # No destination exists, so only the guard can produce a safe refusal.
        (folder / 'recovery/receipt.json').unlink()
        (folder / 'recovery').rmdir()
        result = recovery.capture(manager, payload)
        self.assertEqual(result['state'], 'REFUSED_BEFORE_MUTATION')
        self.assertFalse((folder / 'recovery').exists())
        with self.assertRaisesRegex(ValueError, 'provider|lease|termination'):
            recovery.acknowledge(manager, {'operation_id': identity})
        self.assertEqual(released, [])
        self.assertEqual(self.saved, [])

    def test_recovery_refuses_global_lease_when_execution_mapping_is_lost(self):
        recovery, manager, identity, folder, payload, released = self.recovery_fixture()
        manager.async_operations.clear()
        addons = sys.modules[self.package + '.addons']
        addons.ACTIVE_LEASE = NS(closed=False, operation_id=identity)
        captured = recovery.capture(manager, payload)
        self.assertEqual(captured['state'], 'REFUSED_BEFORE_MUTATION')
        self.assertIn('lease', captured['reason'])
        with self.assertRaisesRegex(ValueError, 'provider|lease|termination'):
            recovery.acknowledge(manager, {'operation_id': identity})
        self.assertEqual(released, [])

    def test_explicit_stop_cancel_is_once_and_terminal_poll_closes_lease_without_collect(self):
        execution = self.execution()
        execution.step()
        self.protected['artist'] = 'external edit caused uncertainty'
        self.assertEqual(execution.step()['state'], 'NEEDS_RECONCILIATION')
        provider = sys.modules['async_test_provider']
        stopped_calls = []
        def cancel(*args):
            stopped_calls.append('cancel')
            self.assertTrue(execution.operation._record.get('stop_requested'))
            return {'requested': True}
        provider.cancel = cancel
        provider.poll = lambda *args: stopped_calls.append('poll') or {'state': 'CANCELLED'}
        provider.collect = lambda *args: self.fail('Cleanup must never collect')
        execution.request_stop()
        execution.request_stop()
        self.assertEqual(execution.confirm_stopped()['state'], 'STOPPED')
        self.assertEqual(execution.confirm_stopped()['state'], 'STOPPED')
        self.assertEqual(stopped_calls, ['cancel', 'poll'])
        self.assertTrue(execution.closed)
        self.assertEqual(self.lease_closes, [True])

    def test_cleanup_rejects_native_poll_mutation_and_retains_lease(self):
        execution = self.execution()
        execution.step()
        execution.operation._uncertain('provider outcome uncertain')
        execution.request_stop()
        def poll(*args):
            self.protected['artist'] = 'illegal cleanup mutation'
            return {'state': 'CANCELLED'}
        sys.modules['async_test_provider'].poll = poll
        with self.assertRaisesRegex(ValueError, 'mutat|state'):
            execution.confirm_stopped()
        self.assertFalse(execution.closed)
        self.assertEqual(self.lease_closes, [])

    def test_uncertain_jobs_cancel_schedules_cleanup_and_does_not_release_reservation(self):
        manager, identity, folder, calls = self.manager('NEEDS_RECONCILIATION')
        manager.write(identity, 'NEEDS_RECONCILIATION')
        cleanup = []
        execution = NS(closed=False, lease=NS(closed=False),
            request_stop=lambda: cleanup.append('cancel') or {'state': 'STOP_REQUESTED'},
            confirm_stopped=lambda: cleanup.append('poll') or {'state': 'STOPPED'})
        manager.async_operations[identity] = (execution, {}, 4)
        timers = []
        self.bpy.app.timers.register = lambda callback, **kwargs: timers.append(callback)
        manager.cancel(identity)
        manager.cancel(identity)
        self.assertEqual(len(timers), 1)
        self.assertIsNone(timers[0]())
        self.assertEqual(cleanup, ['cancel', 'poll'])
        self.assertEqual(manager.session.active, identity)
        self.assertEqual(manager.status(identity)['state'], 'NEEDS_RECONCILIATION')
        self.assertEqual(self.saved, [])

    def test_confirmed_stop_allows_existing_recovery_and_reservation_release(self):
        recovery, manager, identity, folder, payload, released = self.recovery_fixture()
        (folder / 'recovery/receipt.json').unlink()
        (folder / 'recovery').rmdir()
        execution = self.execution()
        execution.step()
        execution.operation._uncertain('unattributed scene change')
        manager.async_operations[identity] = (execution, {}, 4)
        self.assertEqual(recovery.capture(manager, payload)['state'], 'REFUSED_BEFORE_MUTATION')
        sys.modules['async_test_provider'].poll = lambda *args: {'state': 'FAILED'}
        execution.request_stop()
        self.assertEqual(execution.confirm_stopped()['state'], 'STOPPED')
        captured = recovery.capture(manager, payload)
        self.assertEqual(captured['operation_id'], identity)
        self.assertEqual(recovery.acknowledge(manager, {'operation_id': identity}), {'state': 'READY'})
        self.assertEqual(released, [identity])
        self.assertEqual(self.lease_closes, [True])

    def test_cleanup_cancel_response_loss_never_replays_mutation(self):
        execution = self.execution()
        execution.step()
        execution.operation._uncertain('outcome uncertain')
        calls = []
        def cancel(*args):
            calls.append('cancel')
            raise RuntimeError('response lost after cancel')
        sys.modules['async_test_provider'].cancel = cancel
        with self.assertRaisesRegex(RuntimeError, 'response lost'):
            execution.request_stop()
        execution.request_stop()
        self.assertEqual(calls, ['cancel'])
        self.assertFalse(execution.closed)

    def test_cleanup_without_known_submit_handle_refuses_without_dispatch(self):
        execution = self.execution()
        execution.step()
        execution.operation._record['handle'] = None
        execution.operation._uncertain('submit response lost')
        calls = []
        sys.modules['async_test_provider'].cancel = lambda *args: calls.append('cancel')
        with self.assertRaisesRegex(ValueError, 'handle'):
            execution.request_stop()
        self.assertEqual(calls, [])
        self.assertFalse(execution.closed)

    def test_cleanup_grace_expiry_retains_lease_and_never_collects(self):
        execution = self.execution()
        execution.step()
        execution.operation._uncertain('outcome uncertain')
        clock = [0.0]
        execution.operation.clock = lambda: clock[0]
        execution.request_stop()
        clock[0] = 6.0
        with self.assertRaisesRegex(ValueError, 'grace expired'):
            execution.confirm_stopped()
        self.assertFalse(execution.closed)
        self.assertEqual(self.lease_closes, [])

    def test_existing_cancel_intent_is_not_dispatched_again_during_cleanup(self):
        execution = self.execution()
        execution.step()
        execution.operation._transition(cancel_started=execution.operation.clock())
        execution.operation._uncertain('cancel response lost')
        calls = []
        sys.modules['async_test_provider'].cancel = lambda *args: calls.append('cancel')
        execution.request_stop()
        self.assertEqual(calls, [])
        self.assertTrue(execution.operation._record['stop_requested'])

    def test_cleanup_poll_cannot_mutate_even_declared_write_scope(self):
        execution = self.execution()
        effects = sys.modules[self.package + '.recipe_effects']
        def preserved(context, allowed):
            result = copy.deepcopy(self.protected)
            if not context['recipe']['coverage']['writes']:
                result['full_native'] = copy.deepcopy(self.native)
            return result
        effects.preserved = preserved
        execution.step()
        execution.operation._uncertain('outcome uncertain')
        execution.request_stop()
        def poll(*args):
            self.native['materials']['output'] = 3
            return {'state': 'CANCELLED'}
        sys.modules['async_test_provider'].poll = poll
        with self.assertRaisesRegex(ValueError, 'mutat'):
            execution.confirm_stopped()
        self.assertFalse(execution.closed)
        self.assertEqual(self.lease_closes, [])

    def test_recovery_import_does_not_load_provider_runtime(self):
        code = """
import importlib, sys, types
from dcc_harness import files
name = '_recovery_import_fixture'
package = types.ModuleType(name)
package.__path__ = [BRIDGE_PATH]
sys.modules[name] = package
sys.modules['bpy'] = types.SimpleNamespace()
for child in ('attachment', 'files', 'adoption_inventory_blender'):
    sys.modules[name + '.' + child] = types.ModuleType(name + '.' + child)
for attr in ('copy_verified', 'file_hash', 'json_bytes', 'reject_links', 'write_exclusive'):
    setattr(sys.modules[name + '.files'], attr, getattr(files, attr))
sys.modules[name + '.adoption_inventory_blender'].inventory = lambda scene: {}
assert 'addon_utils' not in sys.modules
recovery = importlib.import_module(name + '.recovery')
recovery.require_stopped(types.SimpleNamespace(async_operations={}), 'fixture-operation')
assert 'addon_utils' not in sys.modules
assert name + '.addons' not in sys.modules
""".replace('BRIDGE_PATH', repr(str(BRIDGE)))
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def effects(self):
        self.module('inspection')
        self.module('continuity_blender', measure_live=lambda scene: {})
        self.module('effect_evidence', selector=lambda value, effect: value)
        self.module('blender', graph=lambda tree: {})
        return self.load('recipe_effects')

    def test_preexisting_effect_missing_owner_marker_cannot_be_adopted(self):
        effects = self.effects()
        class Native(dict):
            def __bool__(self):
                return True
            def as_pointer(self):
                return 17
        item = Native()
        item.name = 'Owned'
        target = Native()
        target.modifiers = {'Owned': item}
        context = {'recipe': {'effect': {'kind': 'modifier'}}, 'effect_name': 'Owned',
                   'effect_id': 'effect', 'target': target}
        with self.assertRaisesRegex(ValueError, 'unowned'):
            effects.ownership_before(context)

    def test_existing_effect_owner_marker_cannot_disappear_before_collection(self):
        effects = self.effects()
        class Native(dict):
            def __bool__(self):
                return True
            def as_pointer(self):
                return 17
        item = Native()
        item.name = 'Owned'
        target = Native(dcc_modifier_effects={'Owned': 'effect'})
        target.modifiers = {'Owned': item}
        context = {'recipe': {'effect': {'kind': 'modifier'}}, 'effect_name': 'Owned',
                   'effect_id': 'effect', 'target': target}
        original = effects.ownership_before(context)
        del target['dcc_modifier_effects']['Owned']
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            effects.claim(context, original)


if __name__ == '__main__':
    unittest.main()
