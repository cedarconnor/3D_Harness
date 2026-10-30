"""Cooperative native recipe execution; one step per Blender timer callback."""
import importlib
import copy
from pathlib import Path
import bpy
from . import recipes, addons, recipe_effects
try:
    from .async_recipe import AsyncOperation
    from .evidence import digest
except ModuleNotFoundError:
    from dcc_harness.async_recipe import AsyncOperation
    from dcc_harness.evidence import digest


class RecipeExecution:
    def __init__(self, root, recipe_id, identity, profile, scene, target, parameters, effect_id,
                 *, folder, cancelled=lambda:False, operation_id=None):
        self.args = (root, recipe_id, identity, profile, scene, target, parameters, effect_id)
        self.bundle, self.context = recipes.prepare_context(*self.args)
        self.recipe = self.bundle['recipe']
        if self.recipe['invocation']['completion'] != 'asynchronous':
            raise ValueError('Cooperative execution requires an asynchronous recipe')
        self.profile, self.cancelled = profile, cancelled
        self.scope = sorted(set(sum(self.recipe['coverage'].values(), [])))
        self.before = recipes.measurements(scene, target, self.scope)
        self.originals = recipe_effects.ownership_before(self.context)
        self.prior = recipes.native_effect(self.before, target, effect_id, required=False, recipe=self.recipe)
        self.allowed = recipe_effects.allowed_materials(self.context)
        self.protected = recipe_effects.preserved(self.context, self.allowed)
        self.protected_materials = recipes.other_materials(scene,target) if self.recipe['update']['shared_materials']=='single_user_copy' else None
        self.adapter = addons.offline_call(recipes.adapter_for)(self.bundle)
        if recipes.measurements(scene,target,self.scope) != self.before:
            raise ValueError('Adapter import mutated declared native state')
        if recipe_effects.preserved(self.context,self.allowed) != self.protected:
            raise ValueError('Adapter import mutated protected native state')
        self.lease = None
        self.output = None
        self.closed = False
        self.submitted = False
        self.intent = digest({'root':str(Path(root).resolve()),'recipe':identity,'profile':profile,
                              'target':target,'effect_id':effect_id,'parameters':parameters})
        callbacks = {'submit':self.submit, 'poll':self.poll, 'cancel':self.cancel, 'collect':self.collect}
        self.operation = AsyncOperation(folder, self.recipe['invocation'], callbacks,
                                        cancelled=cancelled, operation_id=operation_id)

    def ensure(self):
        recipes.load(*self.args[:3])
        addons.assert_profile(self.profile)
        if recipe_effects.preserved(self.context, self.allowed) != self.protected:
            raise ValueError('Protected scene or declared inputs changed during asynchronous work')
        # Inputs which the recipe also writes are result state. Preserve disjoint
        # input fields exactly; external edits within the write scope are ambiguous.
        current = recipes.measurements(self.context['scene'], self.context['target_id'], self.scope)
        for field in set(self.recipe['coverage']['reads'] + self.recipe['coverage']['dependencies']) - set(self.recipe['coverage']['writes']):
            if current.get(field) != self.before.get(field):
                raise ValueError('Declared recipe input changed during asynchronous work')

    def callable(self, name):
        entry = self.recipe['invocation'][name]
        module, _, attribute = entry.rpartition('.')
        provider = self.context['provider']['module']
        if module != provider and not module.startswith(provider + '.'):
            raise ValueError('Lifecycle callable is outside pinned provider')
        function = getattr(importlib.import_module(module), attribute)
        if not callable(function):
            raise ValueError('Lifecycle entry is not callable')
        return function

    def submit(self):
        # Lease lifetime is explicit: callbacks scheduled by the provider retain
        # configured preferences and the offline guard between Blender ticks.
        self.lease = addons.AsyncProfileLease(self.profile, self.operation._record['operation_id'])
        self.ensure()
        context = self.context
        with recipes.context_for(context['scene'], context['target']):
            before = recipes.measurements(context['scene'], context['target_id'], self.scope)
            preflight = self.adapter.preflight(context, context['parameters'])
            if recipes.measurements(context['scene'], context['target_id'], self.scope) != before:
                raise ValueError('Preflight mutated declared state')
            if not isinstance(preflight, dict) or preflight.get('ready') is not True:
                raise ValueError('UNSUPPORTED_CONTEXT: adapter preflight')
            if self.recipe['update']['shared_materials']=='all_users' and preflight.get('shared_users') != context['shared_users']:
                raise ValueError('Shared material users differ from preflight scope')
            called = []
            def invoke(**kwargs):
                if called:
                    raise ValueError('Exactly one declared provider submission is supported')
                if recipes.measurements(context['scene'], context['target_id'], self.scope) != before:
                    raise ValueError('Adapter changed state before provider submission')
                called.append(True)
                self.submitted = True
                result = recipes.invoke_declared(context, **kwargs)
                called.append(recipes.measurements(context['scene'], context['target_id'], self.scope))
                return result
            context['invoke'] = invoke
            handle = self.adapter.apply(context, context['parameters'], context['effect_id'])
            if len(called) != 2 or recipes.measurements(context['scene'], context['target_id'], self.scope) != called[1]:
                raise ValueError('Adapter changed output outside declared submission')
        self.ensure()
        return handle

    def lifecycle(self, name, handle, *, read_only=False):
        self.ensure()
        context = self.context
        before = recipes.measurements(context['scene'], context['target_id'], self.scope)
        with recipes.context_for(context['scene'], context['target']):
            result = self.callable(name)(context, handle)
        bpy.context.view_layer.update()
        after = recipes.measurements(context['scene'], context['target_id'], self.scope)
        if read_only and after != before:
            raise ValueError(name + ' callback mutated native scene state')
        self.ensure()
        return result

    def poll(self, handle):
        # Background pollers may advance their external job, but native mutation
        # belongs to submit, collect or provider event callbacks between ticks.
        return self.lifecycle('poll', handle, read_only=True)

    def cancel(self, handle):
        return self.lifecycle('cancel', handle, read_only=True)

    def collect(self, handle):
        result = self.lifecycle('collect', handle)
        if not isinstance(result, dict) or result.get('status') != 'FINISHED':
            raise ValueError('Provider collection did not finish')
        context = self.context
        recipe_effects.claim(context, self.originals)
        self.ensure()
        after = recipes.measurements(context['scene'], context['target_id'], self.scope)
        effect = recipes.native_effect(after, context['target_id'], context['effect_id'], recipe=self.recipe)
        output = recipes.output_record(self.adapter, context)
        if recipes.measurements(context['scene'], context['target_id'], self.scope) != after:
            raise ValueError('Output inspector mutated native state')
        self.ensure()
        if self.protected_materials is not None and recipes.other_materials(context['scene'],context['target_id']) != self.protected_materials:
            raise ValueError('Shared material copy policy changed other users')
        proof = digest({'after':after,'output':output,'native_effect':effect})
        if self.prior == effect and recipes.PROVEN_INVOCATIONS.get(self.intent) != proof:
            raise ValueError('Unchanged provider invocation has no prior exact successful proof')
        self.output = {'output':output,'before':self.before,'after':after,'native_effect':effect,
                       'protected_fingerprint':digest(self.protected),
                       'invocations':[self.recipe['invocation']],
                       'invocation_evidence':[{'intent':self.intent,'native_effect_before':self.prior,
                                               'native_effect_after':effect,'after':after,'output':output}],
                       'output_fingerprint':digest(output),'changed':self.before != after}
        self.proof = proof
        return {'status':'FINISHED','output_fingerprint':digest(output)}

    def step(self):
        try:
            self.ensure()
        except Exception as exc:
            self.operation._uncertain(type(exc).__name__ + ': ' + str(exc))
        status = self.operation.step()
        if status['state'] == 'SUCCEEDED':
            if self.output is None:
                return {**status,'state':'NEEDS_RECONCILIATION','error':'Native execution was not retained in this process'}
            status['result'] = self.output
            recipes.PROVEN_INVOCATIONS[self.intent] = self.proof
        if status['state'] in ('SUCCEEDED','FAILED','CANCELLED') or (status['state']=='NEEDS_RECONCILIATION' and not self.submitted):
            self.close()
        return status

    def stop_callback(self, name):
        """Call a source-pinned termination adapter without accepting scene edits.

        Original inputs may already have diverged; compare the full current scene
        around this callback instead of requiring the original operation baseline.
        """
        record = self.operation._record
        if not self.submitted or record.get('handle') is None:
            raise ValueError('No known submitted provider handle; termination requires external reconciliation')
        recipes.load(*self.args[:3])
        addons.assert_profile(self.profile)
        context = self.context
        unmasked = {**context, 'recipe': {**self.recipe, 'coverage': {**self.recipe['coverage'], 'writes': []}}}
        before = recipe_effects.preserved(unmasked, set())
        with recipes.context_for(context['scene'], context['target']):
            result = self.callable(name)(context, copy.deepcopy(record['handle']))
        bpy.context.view_layer.update()
        if recipe_effects.preserved(unmasked, set()) != before:
            raise ValueError('Termination ' + name + ' callback mutated native scene state')
        recipes.load(*self.args[:3])
        addons.assert_profile(self.profile)
        return result

    def request_stop(self):
        """Explicit uncertain-operation cleanup; cancellation intent is never replayed."""
        if self.closed:
            return {'state': 'STOPPED'}
        record = self.operation._record
        if record['state'] in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            self.close()
            return {'state': 'STOPPED'}
        if not self.submitted or record.get('handle') is None:
            raise ValueError('No known submitted provider handle; retain reservation and lease')
        if not record.get('stop_requested'):
            already_cancelled = record.get('cancel_started') is not None
            self.operation._transition(stop_requested=True, stop_started=self.operation.clock(),
                                       state='NEEDS_RECONCILIATION', phase='RECONCILIATION')
            if not already_cancelled:
                result = self.stop_callback('cancel')
                if isinstance(result, dict) and result.get('state') in ('FAILED', 'UNKNOWN', 'NEEDS_RECONCILIATION'):
                    raise ValueError('Provider termination request failed or remains uncertain')
        return {'state': 'STOP_REQUESTED', 'poll_interval': min(.1, self.recipe['invocation']['cancel_grace'] / 4)}

    def confirm_stopped(self):
        """Confirm measured provider termination, restore preferences, never collect."""
        if self.closed:
            return {'state': 'STOPPED'}
        record = self.operation._record
        if record['state'] in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            self.close()
            return {'state': 'STOPPED'}
        if not record.get('stop_requested'):
            raise ValueError('Explicit stop request is required before termination polling')
        response = self.stop_callback('poll')
        if not isinstance(response, dict) or response.get('state') not in ('PENDING', 'SUCCEEDED', 'FAILED', 'CANCELLED'):
            raise ValueError('Provider termination is unknown; retain lease and reservation')
        if response['state'] != 'PENDING':
            self.operation._transition(stop_confirmed=response['state'], state='NEEDS_RECONCILIATION', phase='RECONCILIATION')
            self.close()
            return {'state': 'STOPPED', 'provider_state': response['state']}
        remaining = record['stop_started'] + self.recipe['invocation']['cancel_grace'] - self.operation.clock()
        if remaining <= 0:
            raise ValueError('Provider termination grace expired; retain lease and reservation')
        return {'state': 'PENDING', 'poll_interval': min(.1, self.recipe['invocation']['cancel_grace'] / 4, remaining / 2)}

    def close(self):
        if self.closed:
            return
        if self.lease is not None:
            self.lease.close()
        self.closed = True


def start(*args, folder, cancelled=lambda:False, operation_id=None):
    return RecipeExecution(*args, folder=folder, cancelled=cancelled, operation_id=operation_id)


def drive(execution):
    if not bpy.app.background:
        raise ValueError('Never block Blender UI while driving asynchronous work')
    import time
    while True:
        status = execution.step()
        if status['state'] != 'PENDING':
            if status['state'] != 'SUCCEEDED':
                raise ValueError('Asynchronous recipe ' + status['state'] + ': ' + status.get('error', status.get('reason','')))
            return status['result']
        time.sleep(min(status['poll_interval'], 1.0))
