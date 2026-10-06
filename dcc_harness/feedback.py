"""Persistent notes with separate implementation, verification and disposition."""
import math
from pathlib import Path
import uuid

from . import coordination as c
from . import coordination_evidence as evidence
from .evidence import read_json


def binding(events):
    return next((e for e in events if e['kind'] == 'workflow.bind'), None)


def policy(events, stage):
    bound = binding(events)
    if bound is None:
        return 'agent_within_brief'
    stages = {s['id']: s for s in bound['result']['manifest']['stages']}
    if stage not in stages:
        raise ValueError('Unknown workflow stage')
    return bound['result']['binding']['review_policies'].get(stage, stages[stage]['review'])


def state(events, native):
    notes = {}
    for event in events:
        data = event['result']
        if event['kind'] == 'feedback.add':
            note = data['note']
            notes[note['id']] = {'note': note, 'status': 'open', 'response_id': None,
                                 'verified_checkpoint': None, 'event_id': event['id']}
        elif event['kind'].startswith('feedback.'):
            note = notes[data['note_id']]
            note['event_id'] = event['id']
            if event['kind'] == 'feedback.respond':
                note.update(status='awaiting_verification' if data['response']['disposition'] == 'implemented' else 'in_progress',
                            response_id=event['id'], verified_checkpoint=None)
            elif event['kind'] == 'feedback.verify':
                note.update(status='resolved' if data['passed'] else 'awaiting_verification',
                            verified_checkpoint=data['checkpoint_id'] if data['passed'] else None)
            elif event['kind'] == 'feedback.decide':
                action = data['decision']['action']
                if action == 'reassign':
                    note['note'] = {**note['note'], 'stage_id': data['decision']['stage_id']}
                    note.update(status='reopened', verified_checkpoint=None, response_id=None)
                elif action in ('deferred', 'not_applicable'):
                    note.update(status=action, verified_checkpoint=data['checkpoint_id'])
                else:
                    note.update(status='reopened', verified_checkpoint=None, response_id=None)
    active = native['active']
    obs = read_json(active['observation'])
    for note in notes.values():
        anchor = note['note']['anchor']
        note['missing_targets'] = [i for i in anchor.get('instance_ids', []) if i not in obs['objects']]
        note['missing_targets'] += [i for i in anchor.get('material_ids', []) if i not in obs['materials']]
        closed = note['status'] in ('resolved', 'deferred', 'not_applicable')
        note['current_validity'] = ('current' if note['verified_checkpoint'] == active['id'] else 'needs_recheck') if closed else 'unresolved'
    return notes


def unresolved(events, native, stage=None):
    return [nid for nid, n in state(events, native).items() if n['note']['priority'] == 'blocking'
            and (stage is None or n['note']['stage_id'] in (None, stage))
            and n['current_validity'] != 'current']


def _note(ctx, nid):
    notes = state(ctx.events, ctx.native)
    if nid not in notes:
        raise ValueError('Unknown feedback note')
    return notes[nid]


def _add(ctx, value):
    c.fields(value, {'schema', 'source', 'stage_id', 'category', 'priority', 'text', 'acceptance', 'anchor'}, {'review_policy', 'requires'})
    if value['schema'] != 'dcc.feedback.note.v1' or value['category'] not in ('technical', 'visual', 'preference') or value['priority'] not in ('blocking', 'advisory'):
        raise ValueError('Unsupported feedback note')
    evidence.actor(value['source']); c.text(value['text']); c.text(value['acceptance'])
    if value['stage_id'] is not None:
        c.text(value['stage_id'])
        policy(ctx.events, value['stage_id'])
    review_policy = value.get('review_policy', 'agent_within_brief')
    if review_policy not in ('agent_within_brief', 'artist_required'):
        raise ValueError('Unknown review policy')
    required = value.get('requires', ['technical'] if value['category'] == 'technical' else ['visual'])
    if (not isinstance(required, list) or not required or any(r not in ('technical', 'visual') for r in required)
            or len(set(required)) != len(required) or ('technical' if value['category'] == 'technical' else 'visual') not in required):
        raise ValueError('Note requires its category check, optionally both technical and visual')
    anchor = value['anchor']
    c.fields(anchor, {'checkpoint_id', 'checkpoint_sha256'}, {'instance_ids', 'material_ids', 'render', 'frame'})
    checkpoint = {k: anchor[k] for k in ('checkpoint_id', 'checkpoint_sha256')}
    entry = ctx.checkpoint(checkpoint)
    obs = read_json(entry['observation'])
    for key, category in (('instance_ids', 'objects'), ('material_ids', 'materials')):
        ids = anchor.get(key, [])
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in obs[category] for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Unknown or duplicate feedback target')
    if 'render' in anchor:
        render = anchor['render']
        c.fields(render, {'receipt', 'view_id', 'settings'}, {'pin'})
        evidence.render(ctx, {k: render[k] for k in ('receipt', 'view_id', 'settings')}, checkpoint)
        if 'pin' in render:
            c.fields(render['pin'], {'x', 'y'})
            if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in render['pin'].values()):
                raise ValueError('Pin coordinates must be finite fractions')
    if 'frame' in anchor:
        c.fields(anchor['frame'], {'number', 'fps_numerator', 'fps_denominator'})
        if (type(anchor['frame']['number']) is not int or any(type(anchor['frame'][k]) is not int or anchor['frame'][k] <= 0
                for k in ('fps_numerator', 'fps_denominator')) or 'render' not in anchor):
            raise ValueError('Frame requires an exact integer, positive rational FPS and render')
    return {'note': {**value, 'id': str(uuid.uuid4()), 'review_policy': review_policy, 'requires': required}}


def _respond(ctx, value):
    c.fields(value, {'schema', 'note_id', 'author', 'disposition', 'change', 'result', 'evidence'})
    if value['schema'] != 'dcc.feedback.response.v1' or value['disposition'] not in ('implemented', 'partial', 'deferred', 'not_applicable'):
        raise ValueError('Unsupported feedback response')
    _note(ctx, value['note_id']); c.text(value['author']); c.text(value['change'])
    ctx.checkpoint(value['result'], current=True)
    if value['disposition'] in ('implemented', 'partial') and not value['evidence']:
        raise ValueError('Implementation requires evidence')
    reports = evidence.validate(ctx, value['evidence'], value['result'])
    return {'note_id': value['note_id'], 'response': value, 'reports': reports}


def _verify(ctx, value):
    c.fields(value, {'schema', 'note_id', 'response_id', 'reviewer', 'finding', 'verdict', 'views'})
    if value['schema'] != 'dcc.feedback.verification.v1' or value['verdict'] not in ('pass', 'fail', 'uncertain'):
        raise ValueError('Unsupported feedback verification')
    note = _note(ctx, value['note_id'])
    if note['missing_targets']:
        raise ValueError('Feedback targets are missing; record an explicit disposition before closure')
    if note['response_id'] != value['response_id']:
        raise ValueError('Stale feedback response')
    event = next(e for e in ctx.events if e['id'] == value['response_id'])
    response = event['result']['response']
    if response['disposition'] != 'implemented':
        raise ValueError('Partial or deferred work cannot be verified as resolved')
    ctx.checkpoint(response['result'], current=True)
    evidence.actor(value['reviewer']); c.text(value['finding'])
    # Recompute from frozen response artifacts, never accept the stored report's pass flag.
    frozen = c.Context(ctx.root, ctx.native, ctx.events, event['artifacts'])
    reports = evidence.validate(frozen, response['evidence'], response['result'])
    requirements = note['note']['requires']
    contracts = [r for r in reports if r['kind'] == 'native_contract']
    renders = [r for r in reports if 'view_id' in r]
    if 'technical' in requirements and not contracts:
        raise ValueError('Technical note needs a recomputed native contract')
    if 'technical' in requirements:
        targets = {i for r in contracts for i in r['targets']}
        materials = {i for r in contracts for i in r['materials']}
        anchor = note['note']['anchor']
        if not set(anchor.get('instance_ids', [])) <= targets or not set(anchor.get('material_ids', [])) <= materials:
            raise ValueError('Contract does not cover the feedback targets')
    if not isinstance(value['views'], list) or any(not isinstance(v, str) for v in value['views']):
        raise ValueError('Inspected views must be a list')
    if 'visual' in requirements:
        if not value['views'] or not set(value['views']) <= {r['view_id'] for r in renders}:
            raise ValueError('Visual note requires inspection of bound views')
        original_view = note['note']['anchor'].get('render', {}).get('view_id')
        if original_view and original_view not in value['views']:
            raise ValueError('Inspect the original feedback view')
        if original_view:
            original = next(e for e in ctx.events if e['kind'] == 'feedback.add' and e['result']['note']['id'] == value['note_id'])
            anchor = original['result']['note']['anchor']
            original_ctx = c.Context(ctx.root, ctx.native, ctx.events, original['artifacts'])
            original_render = evidence.render(original_ctx, {k: anchor['render'][k] for k in ('receipt', 'view_id', 'settings')},
                                             {k: anchor[k] for k in ('checkpoint_id', 'checkpoint_sha256')})
            if any(r['views_digest'] != original_render['views_digest'] for r in renders if r['view_id'] == original_view):
                raise ValueError('Feedback review view settings changed')
    required = note['note']['review_policy']
    if note['note']['stage_id'] is not None and policy(ctx.events, note['note']['stage_id']) == 'artist_required':
        required = 'artist_required'
    if required == 'artist_required' and value['reviewer']['role'] != 'artist':
        raise ValueError('Artist review is required by the retained policy')
    return {'note_id': value['note_id'], 'response_id': value['response_id'],
            'checkpoint_id': response['result']['checkpoint_id'], 'verification': value,
            'passed': value['verdict'] == 'pass' and all(r['passed'] for r in reports), 'reports': reports,
            'review_independence': 'same_author' if value['reviewer']['author'] == response['author'] else 'different_authors_declared_not_authenticated',
            'artistic_acceptance': 'artist_declared' if value['reviewer']['role'] == 'artist' else 'not_evaluated'}


def _decide(ctx, value):
    c.fields(value, {'schema', 'note_id', 'action', 'reason', 'authority', 'result'}, {'stage_id'})
    if value['schema'] != 'dcc.feedback.decision.v1' or value['action'] not in ('reopen', 'reassign', 'deferred', 'not_applicable'):
        raise ValueError('Unsupported feedback decision')
    note = _note(ctx, value['note_id'])
    c.text(value['reason']); evidence.actor(value['authority'])
    ctx.checkpoint(value['result'], current=True)
    if value['action'] in ('deferred', 'not_applicable'):
        # No implicit authorization to waive a blocking artist requirement.
        if note['note']['priority'] == 'blocking' and value['authority']['role'] != 'artist':
            raise ValueError('Blocking disposition requires an attributed artist decision')
    if value['action'] == 'reassign':
        c.text(value.get('stage_id')); policy(ctx.events, value['stage_id'])
    elif 'stage_id' in value:
        raise ValueError('Only reassignment takes a stage ID')
    return {'note_id': value['note_id'], 'checkpoint_id': value['result']['checkpoint_id'], 'decision': value}


BUILDERS = {'feedback.add': _add, 'feedback.respond': _respond, 'feedback.verify': _verify, 'feedback.decide': _decide}


def apply(root, kind, payload, expected_revision, request_id, base=None):
    return c.transact(root, kind, payload, expected_revision, request_id, base or Path.cwd(), BUILDERS[kind])
