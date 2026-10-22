"""Fixture-only adapter; all provider work goes through the declared invocation."""
import bpy


def preflight(context, parameters):
    entry = context['recipe']['invocation']
    ready = context['target'].mode == 'OBJECT'
    if entry['kind'] == 'operator':
        group,name = entry['entry'].split('.')
        ready = ready and getattr(getattr(bpy.ops,group),name).poll()
    return {'ready':ready, 'shared_users':[] if parameters['behavior']=='shared_bad' else context['shared_users']}


def apply(context, parameters, effect_id):
    kind = context['recipe']['invocation']['kind']
    if kind == 'operator':
        return context['invoke'](amount=parameters['amount'],behavior=parameters['behavior'],effect_id=effect_id)
    if kind == 'node_asset': return context['invoke'](asset='fixture.blend')
    return context['invoke']()


def inspect_output(context, effect_id):
    mods = [m for m in context['target'].modifiers if m.name.startswith('DCC::' + effect_id[:48])]
    values = [{'type':m.type,'width':m.width,'segments':m.segments} if m.type == 'BEVEL'
              else {'type':m.type,'source':m.node_group.get('dcc_asset_source')} for m in mods]
    return {'effect_id':effect_id,'effect_count':len(mods),'measurements':{'modifiers':values}}


def verify_saved(observation, output):
    mods = output['measurements']['modifiers']
    return {'passed':len(mods)==1 and (mods[0]['type']=='NODES' or mods[0]['width'] > 0)}
