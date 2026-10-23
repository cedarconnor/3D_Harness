"""Closed public actions shared by CLI and MCP; no alternate execution engine."""
from . import capabilities, recipes, environments, coordination as c
from .evidence import read_json

CAPABILITY_ACTIONS=('inventory','profile','bind','resolve','requirements','prepare')
RECIPE_ACTIONS=('scaffold','draft','inspect','qualify','register')


def capability_action(action,payload,*,blender=None,approval=None):
    if action=='inventory':
        c.fields(payload,set(),{'binding','roots','out'})
        if not payload.get('binding') and not blender: raise ValueError('Configure Blender for background discovery')
        return environments.inventory(payload.get('binding'),blender=blender,roots=payload.get('roots'),out=payload.get('out'))
    if action=='profile':
        c.fields(payload,{'project','inventory','selected','preferences'},{'reviews'})
        return environments.create_profile(payload['project'],payload['inventory'],payload['selected'],payload['preferences'],reviews=payload.get('reviews'))
    if action=='bind':
        c.fields(payload,{'project','policy','expected_revision','request_id','authority'})
        return capabilities.bind_policy(payload['project'],payload['policy'],expected_revision=payload['expected_revision'],
            request_id=payload['request_id'],authority=payload['authority'],approval=approval)
    if action=='resolve':
        c.fields(payload,{'project','requirement'})
        return capabilities.resolve(payload['project'],payload['requirement'],
                                     capabilities.inventory_for_requirement(payload['project'],payload['requirement']))
    if action=='requirements':
        c.fields(payload,{'project','stage'})
        active=c.Continuity(payload['project']).status()['active']
        return capabilities.status(payload['project'],payload['stage'],c.checkpoint_ref(active))
    if action=='prepare':
        c.fields(payload,{'project','requirement','resolution','parameters','operation_id','contract','handoff'},{'timeout'})
        if not blender: raise ValueError('Configure Blender before preparing execution')
        return capabilities.prepare(payload['project'],payload['requirement'],payload['resolution'],payload['parameters'],
            payload['operation_id'],blender=blender,contract=payload['contract'],handoff=payload['handoff'],timeout=payload.get('timeout',300))
    raise ValueError('Unknown capability action')


def recipe_action(action,payload,*,blender=None):
    if action=='scaffold':
        c.fields(payload,{'recipe'})
        return {'state':'DRAFT','adapter':recipes.scaffold(payload['recipe'])}
    if action=='draft':
        c.fields(payload,{'project','recipe','adapter','assets'})
        return recipes.draft(payload['project'],payload['recipe'],payload['adapter'],payload['assets'])
    if action=='inspect':
        c.fields(payload,{'project','recipe_id','recipe_digest'})
        return recipes.inspect(payload['project'],payload['recipe_id'],payload['recipe_digest'])
    if action=='qualify':
        c.fields(payload,{'project','recipe_id','recipe_digest','profile_digest','out'})
        if not blender: raise ValueError('Configure Blender for owned qualification')
        return recipes.qualify(payload['project'],payload['recipe_id'],payload['recipe_digest'],payload['profile_digest'],
                               blender=blender,out=payload['out'])
    if action=='register':
        c.fields(payload,{'project','report'})
        return recipes.register_qualified(payload['project'],payload['report'])
    raise ValueError('Unknown recipe action')
