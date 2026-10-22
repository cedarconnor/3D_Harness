"""One pinned environment workflow, with evidence-backed stage receipts."""
import hashlib
from importlib.resources import files
from pathlib import Path
import re

from . import checks, coordination as c, coordination_evidence as evidence, feedback
from .evidence import digest, read_json


def default_manifest():
    import json
    return json.loads(files('dcc_harness').joinpath('data/environment-workflow.v1.json').read_text(encoding='utf-8'))


def review_policy(root, events, stage):
    from .execution import configuration
    managed = configuration(root)
    if managed is not None:
        return 'artist_required' if managed['mode'] == 'approval_gated' else 'agent_within_brief'
    return feedback.policy(events, stage)


# Comparison tooling: frozen packets carry their own copies, and the pinned runtime never imports
# these modules (a test enforces it), so editing them must not invalidate workflow bindings.
EXPERIMENT_TOOLING = frozenset({'blind.py', 'blind_review.py', 'continuity_trial.py', 'continuity_review.py', 'session_cost.py'})


def runtime_stamp(root=None):
    """Version plus a source digest of this package, or of another source tree for comparison.

    Line endings are normalized so CRLF and LF checkouts of the same sources pin
    the same runtime; any other byte change alters the digest. Experiment tooling
    at the package top level is excluded.
    """
    from . import __version__
    root = Path(root) if root is not None else Path(__file__).parent
    return {'version': __version__, 'source_digest': digest({
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        for p in sorted(root.rglob('*.py')) if p.relative_to(root).as_posix() not in EXPERIMENT_TOOLING})}


def validate_manifest(value):
    c.fields(value, {'schema', 'id', 'version', 'description', 'default_review_policy', 'stages'})
    if value['schema'] != 'dcc.environment.workflow.v1' or value['id'] != 'environment' or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Unsupported environment workflow')
    c.text(value['description'])
    if value['default_review_policy'] not in ('agent_within_brief', 'artist_required'):
        raise ValueError('Unknown workflow review policy')
    if not isinstance(value['stages'], list) or not value['stages']:
        raise ValueError('Workflow needs stages')
    seen = set()
    for stage in value['stages']:
        c.fields(stage, {'id', 'after', 'skills', 'deliverables', 'evidence', 'review'})
        if not isinstance(stage['id'], str) or not re.fullmatch('[a-z][a-z0-9-]*', stage['id']) or stage['id'] in seen:
            raise ValueError('Invalid or duplicate stage ID')
        for key in ('after', 'skills', 'deliverables', 'evidence'):
            values = stage[key]
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values) or len(set(values)) != len(values):
                raise ValueError('Invalid stage list: ' + key)
        if not set(stage['after']) <= seen:
            raise ValueError('Stage dependencies must be ordered and acyclic')
        if not stage['skills'] or not stage['deliverables'] or not stage['evidence'] or not set(stage['evidence']) <= evidence.KINDS:
            raise ValueError('Stage requires skills, deliverables and supported evidence')
        if stage['review'] not in ('agent_within_brief', 'artist_required'):
            raise ValueError('Unknown stage review policy')
        seen.add(stage['id'])
    if value['stages'][-1]['id'] != 'delivery' or not {'native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'} <= set(value['stages'][-1]['evidence']):
        raise ValueError('Delivery requires native reopen, contract, feedback reconciliation and handoff')
    # Prevent a disconnected stage being bypassed by delivery.
    ancestors = set()
    def visit(key):
        for parent in next(s for s in value['stages'] if s['id'] == key)['after']:
            if parent not in ancestors:
                ancestors.add(parent); visit(parent)
    visit('delivery')
    if ancestors != seen - {'delivery'}:
        raise ValueError('Every stage must lead to delivery')
    return value


def _binding(ctx):
    event = feedback.binding(ctx.events)
    if event is None:
        raise ValueError('Bind an environment workflow first')
    if event['result']['runtime'] != runtime_stamp():
        raise ValueError('Pinned runtime differs; use the qualified runtime before workflow mutations')
    return event


def stages(events, native=None):
    bound = feedback.binding(events)
    if bound is None:
        return {}
    specs = {s['id']: s for s in bound['result']['manifest']['stages']}
    result = {key: {'id': key, 'state': 'ready', 'receipt_id': None, 'submission_id': None,
                    'skills': spec['skills'], 'inherited_gaps': []} for key, spec in specs.items()}
    for key, inherited in bound['result']['binding']['inherited'].items():
        result[key].update(state='inherited', receipt_id=bound['id'], inherited_gaps=inherited['gaps'])
    def invalidate(key):
        affected = {key}
        for sid, spec in specs.items():
            if set(spec['after']) & affected:
                affected.add(sid)
        for sid in affected:
            result[sid].update(state='needs_review', submission_id=None)
    note_stages = {}
    for event in events:
        data = event['result']
        if event['kind'] == 'stage.submit':
            result[data['stage_id']].update(state='awaiting_review', submission_id=event['id'])
        elif event['kind'] == 'stage.complete':
            result[data['stage_id']].update(state='complete', receipt_id=event['id'], submission_id=None, inherited_gaps=[])
        elif event['kind'] == 'stage.reopen':
            invalidate(data['stage_id'])
        elif event['kind'] == 'capability.bind':
            for stage in data['affected_stages']:
                invalidate(stage)
        elif event['kind'] == 'feedback.add':
            note = data['note']; sid = note['stage_id']
            note_stages[note['id']] = sid
            if note['priority'] == 'blocking':
                if sid is None:
                    invalidate('delivery')
                elif sid in result and result[sid]['state'] in ('complete', 'inherited', 'awaiting_review'):
                    invalidate(sid)
        elif event['kind'] == 'feedback.decide' and data['decision']['action'] in ('reopen', 'reassign'):
            sid = note_stages[data['note_id']]
            # A global note is delivery's to account for, as when it was added.
            if sid is None:
                invalidate('delivery')
            elif sid in result:
                invalidate(sid)
            if data['decision']['action'] == 'reassign':
                sid = data['decision']['stage_id']
                note_stages[data['note_id']] = sid
                if sid in result:
                    invalidate(sid)
    if native is not None:
        # A receipt remains history; readiness belongs to the active checkpoint.
        for note in feedback.state(events, native).values():
            if note['note']['priority'] == 'blocking' and note['current_validity'] != 'current':
                sid = note['note']['stage_id'] or 'delivery'
                if sid in result and result[sid]['state'] in ('complete', 'inherited'):
                    invalidate(sid)
        for sid, row in result.items():
            if row['state'] not in ('complete', 'inherited'):
                continue
            if row['state'] == 'inherited':
                submitted = bound
                submission = {'checkpoint': bound['result']['binding']['checkpoint'],
                              'evidence': bound['result']['binding']['inherited'][sid]['evidence']}
            else:
                receipt = next(e for e in events if e['id'] == row['receipt_id'])
                submitted = next(e for e in events if e['id'] == receipt['result']['submission_id'])
                submission = submitted['result']['submission']
            old = next(h for h in native['task_history'] if h['id'] == submission['checkpoint']['checkpoint_id'])
            active = native['active']
            if old['id'] == active['id']:
                continue
            before, after = read_json(old['observation']), read_json(active['observation'])
            stale = False
            for item in submission['evidence']:
                kind = item['kind']
                if kind == 'native_reopen':
                    stale = True  # A reopen certifies exact saved bytes.
                elif kind in ('whole_scene_render', 'detail_render', 'visual_review'):
                    stale |= before['revision'] != after['revision']
                elif kind == 'native_contract':
                    from .evidence import evaluate
                    contract = read_json(c.relative(submitted['artifacts'], item['contract']['path']))
                    stale |= not evaluate(after, contract['spec'])['passed']
                    targets = contract['spec']['required']
                    materials = set(contract['spec'].get('required_materials', [])) | set(contract['spec'].get('material_nodes', {}))
                    for iid in targets:
                        materials.update(before['objects'].get(iid, {}).get('material_ids', []))
                        materials.update(after['objects'].get(iid, {}).get('material_ids', []))
                    stale |= any(before['objects'].get(i) != after['objects'].get(i) for i in targets)
                    stale |= any(before['materials'].get(i) != after['materials'].get(i) for i in materials)
            if submitted['result'].get('checks') is not None:
                frozen = c.Context(Path(submitted['artifacts']).parents[3], native, events, submitted['artifacts'])
                try:
                    ran = checks.run(frozen, sid, c.checkpoint_ref(active), submission.get('check_measurements', {}))
                    stale |= any(not r['passed'] for r in ran or [])
                except ValueError:
                    stale = True
            if stale:
                invalidate(sid)
    for key, value in result.items():
        if value['state'] not in ('complete', 'inherited') and any(result[p]['state'] not in ('complete', 'inherited') for p in specs[key]['after']):
            value['state'] = 'blocked'
    return result


def _bind(ctx, value):
    c.fields(value, {'manifest', 'binding'})
    if feedback.binding(ctx.events) is not None:
        raise ValueError('Workflow is already pinned; do not replace it')
    ctx.quiet()
    manifest = validate_manifest(value['manifest'])
    binding = value['binding']
    c.fields(binding, {'schema', 'checkpoint', 'authority', 'review_policies', 'inherited', 'skill_files', 'references'}, {'checks'})
    if binding['schema'] != 'dcc.environment.binding.v1':
        raise ValueError('Unsupported workflow binding')
    entry = ctx.checkpoint(binding['checkpoint'], current=True)
    evidence.actor(binding['authority'])
    keys = {s['id'] for s in manifest['stages']}
    for note in feedback.state(ctx.events, ctx.native).values():
        if note['note']['stage_id'] is not None and note['note']['stage_id'] not in keys:
            raise ValueError('Existing feedback references an unknown stage')
    if not isinstance(binding['review_policies'], dict) or not set(binding['review_policies']) <= keys or any(p not in ('agent_within_brief', 'artist_required') for p in binding['review_policies'].values()):
        raise ValueError('Unknown review policy/stage')
    relaxed = [s['id'] for s in manifest['stages'] if s['review'] == 'artist_required' and binding['review_policies'].get(s['id']) == 'agent_within_brief']
    if relaxed and binding['authority']['role'] != 'artist':
        raise ValueError("Relaxing an artist-required stage needs the artist's authority: " + ', '.join(relaxed))
    if not isinstance(binding['inherited'], dict) or not set(binding['inherited']) <= keys - {'delivery'}:
        raise ValueError('Unknown inherited stage; delivery cannot be inherited')
    inherited_seen = set()
    inherited_reports = {}
    for stage in manifest['stages']:
        if stage['id'] in binding['inherited']:
            item = binding['inherited'][stage['id']]
            c.fields(item, {'reason', 'gaps', 'evidence'})
            c.text(item['reason'])
            if not isinstance(item['gaps'], list) or any(not isinstance(g, str) or not g.strip() for g in item['gaps']):
                raise ValueError('Inherited gaps must be explicit text entries')
            if not set(stage['after']) <= inherited_seen or not isinstance(item['evidence'], list) or not item['evidence']:
                raise ValueError('Inherited stages need evidence and inherited predecessors')
            reports = evidence.validate(ctx, item['evidence'], binding['checkpoint'])
            inherited_reports[stage['id']] = reports
            available = {r['kind'] for r in reports if r['passed']}
            # Caller descriptions cannot hide missing evidence for an inherited stage.
            item['gaps'] = list(dict.fromkeys(item['gaps'] + ['Missing ' + k for k in stage['evidence'] if k not in available]))
            inherited_seen.add(stage['id'])
    required = {s for stage in manifest['stages'] for s in stage['skills']}
    if not isinstance(binding['skill_files'], dict) or set(binding['skill_files']) != required:
        raise ValueError('Pin exactly the workflow skills')
    for skill, refs in binding['skill_files'].items():
        if not isinstance(refs, list) or not refs:
            raise ValueError('Missing skill files')
        paths = [ctx.artifact(ref) for ref in refs]
        if not any(p.name == 'SKILL.md' and re.search(r'^name:\s*' + re.escape(skill) + r'\s*$', p.read_text(encoding='utf-8'), re.M) for p in paths):
            raise ValueError('Missing matching SKILL.md for ' + skill)
    if not isinstance(binding['references'], list):
        raise ValueError('References must be explicit artifact references')
    for ref in binding['references']:
        ctx.artifact(ref)
    result = {'manifest': manifest, 'manifest_digest': digest(manifest), 'binding': binding,
              'runtime': runtime_stamp(), 'inherited_reports': inherited_reports, 'artistic_acceptance': 'not_evaluated'}
    if 'checks' in binding:
        # Pin one library version; later approvals never reach this project.
        library = checks.validate_document(read_json(ctx.artifact(binding['checks'])))
        result['checks'] = {'version': library['version'], 'sha256': binding['checks']['sha256'], 'ids': [x['id'] for x in library['checks']]}
    return result


def _stage(ctx, sid):
    bound = _binding(ctx)
    spec = next((s for s in bound['result']['manifest']['stages'] if s['id'] == sid), None)
    if spec is None:
        raise ValueError('Unknown workflow stage')
    states = stages(ctx.events, ctx.native)
    if any(states[p]['state'] not in ('complete', 'inherited') for p in spec['after']):
        raise ValueError('Stage dependencies are not ready')
    return spec, states


def _questions(questions):
    """Owner questions on a submission: unique IDs, text, optional choices and a default among them."""
    if not isinstance(questions, list) or len(questions) > 12:
        raise ValueError('Questions must be a list of at most 12')
    seen = set()
    for question in questions:
        c.fields(question, {'id', 'text'}, {'choices', 'default'})
        if not isinstance(question['id'], str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,39}', question['id']) or question['id'] in seen:
            raise ValueError('Question IDs must be unique lowercase names')
        seen.add(question['id'])
        c.text(question['text'])
        choices = question.get('choices')
        if choices is not None and (not isinstance(choices, list) or not 2 <= len(choices) <= 8 or len(set(choices)) != len(choices)
                                    or any(not isinstance(x, str) or not x.strip() for x in choices)):
            raise ValueError('Choices must be 2 to 8 distinct nonempty texts')
        if 'default' in question:
            c.text(question['default'])
            if choices is not None and question['default'] not in choices:
                raise ValueError('A default must be one of the choices')
    return questions


def _answers(questions, answers):
    """Resolve answers against the frozen questions; a question without a default must be answered."""
    if not isinstance(answers, dict) or any(not isinstance(v, str) for v in answers.values()):
        raise ValueError('Answers must map question IDs to text')
    known = {q['id'] for q in questions}
    if set(answers) - known:
        raise ValueError('Unknown question: ' + ', '.join(sorted(set(answers) - known)))
    resolved = []
    for question in questions:
        given = answers.get(question['id'])
        if given is not None and not given.strip():
            raise ValueError('An answer must be nonempty text: ' + question['id'])
        if given is None and 'default' not in question:
            raise ValueError('Question needs an answer: ' + question['id'])
        resolved.append({'id': question['id'], 'text': question['text'], 'answer': given if given is not None else question['default'],
                         'used_default': given is None})
    return resolved


def _submit(ctx, value):
    from .execution import configuration
    config = configuration(ctx.root)
    if config and config.get('backend') == 'live':
        from .live import ensure_aligned
        ensure_aligned(ctx.root)
    c.fields(value, {'schema', 'stage_id', 'checkpoint', 'deliverables', 'evidence', 'feedback_ids', 'note'}, {'questions', 'check_measurements'})
    if 'questions' in value:
        _questions(value['questions'])
    if value['schema'] != 'dcc.environment.submission.v1':
        raise ValueError('Unsupported stage submission')
    ctx.quiet(); ctx.checkpoint(value['checkpoint'], current=True); c.text(value['note'])
    from .capabilities import verify_receipts
    capability_report = verify_receipts(ctx.root,value['stage_id'],value['checkpoint'])
    if not capability_report['passed']:
        raise ValueError('Required capability receipts are missing or stale')
    spec, states = _stage(ctx, value['stage_id'])
    if states[value['stage_id']]['state'] == 'complete':
        raise ValueError('Reopen a completed stage before revising it')
    if not isinstance(value['deliverables'], dict) or set(value['deliverables']) != set(spec['deliverables']):
        raise ValueError('Describe every stage deliverable')
    for description in value['deliverables'].values():
        c.text(description)
    notes = feedback.state(ctx.events, ctx.native)
    applicable = sorted(nid for nid, n in notes.items() if value['stage_id'] == 'delivery' or n['note']['stage_id'] in (None, value['stage_id']))
    if not isinstance(value['feedback_ids'], list) or sorted(value['feedback_ids']) != applicable:
        raise ValueError('Submission must account for every applicable feedback note')
    blockers = lambda: feedback.unresolved(ctx.events, ctx.native, None if value['stage_id'] == 'delivery' else value['stage_id'])
    reports = evidence.validate(ctx, value['evidence'], value['checkpoint'], feedback_check=blockers)
    missing = sorted(set(spec['evidence']) - {r['kind'] for r in reports})
    result = {'stage_id': value['stage_id'], 'submission': value, 'reports': reports, 'missing_evidence': missing,
              'unresolved_notes': blockers(), 'predecessors': {p: states[p]['receipt_id'] for p in spec['after']},
              'review_policy': review_policy(ctx.root, ctx.events, value['stage_id'])}
    if capability_report['requirements']:
        result['capabilities'] = capability_report
    ran = checks.run(ctx, value['stage_id'], value['checkpoint'], value.get('check_measurements', {}))
    if ran is not None:
        result.update(checks=ran, failed_checks=[r['id'] for r in ran if not r['passed']])
    return result


def _complete(ctx, value):
    c.fields(value, {'submission_id', 'review'})
    ctx.quiet()
    event = next((e for e in ctx.events if e['id'] == value['submission_id'] and e['kind'] == 'stage.submit'), None)
    if event is None:
        raise ValueError('Unknown stage submission')
    # Any intervening metadata may change scope, policy or feedback. Refresh the submission.
    if ctx.events[-1]['id'] != event['id']:
        raise ValueError('Stale submission after new coordination activity')
    submitted = event['result']; sid = submitted['stage_id']
    spec, states = _stage(ctx, sid)
    if states[sid]['submission_id'] != event['id']:
        raise ValueError('Submission no longer active')
    ctx.checkpoint(submitted['submission']['checkpoint'], current=True)
    frozen = c.Context(ctx.root, ctx.native, ctx.events, event['artifacts'])
    refreshed = _submit(frozen, submitted['submission'])
    if refreshed['missing_evidence'] or refreshed['unresolved_notes'] or not all(r['passed'] for r in refreshed['reports']):
        raise ValueError('Stage has missing evidence, failed checks or unresolved feedback')
    if refreshed.get('failed_checks'):
        raise ValueError('Pinned library checks failed or were not measured: ' + ', '.join(refreshed['failed_checks']))
    if sid == 'delivery' and any(s['inherited_gaps'] for s in states.values()):
        raise ValueError('Inherited stage evidence gaps remain')
    review = value['review']
    c.fields(review, {'reviewer', 'verdict', 'finding'}, {'answers'})
    evidence.actor(review['reviewer']); c.text(review['finding'])
    answers = _answers(submitted['submission'].get('questions', []), review.get('answers', {}))
    if review['verdict'] != 'pass':
        raise ValueError('Stage review has not passed')
    if refreshed['review_policy'] == 'artist_required' and review['reviewer']['role'] != 'artist':
        raise ValueError('Artist review is required by the stage policy')
    return {'stage_id': sid, 'submission_id': event['id'], 'checkpoint': submitted['submission']['checkpoint'],
            'review': review, 'answers': answers, 'reports': refreshed['reports'], 'predecessors': refreshed['predecessors'],
            'artistic_acceptance': 'artist_confirmed' if review['reviewer']['role'] == 'artist' else 'not_evaluated'}


def _reopen(ctx, value):
    c.fields(value, {'schema', 'stage_id', 'reason', 'authority'})
    if value['schema'] != 'dcc.environment.reopen.v1':
        raise ValueError('Unsupported stage decision')
    bound = _binding(ctx)
    if value['stage_id'] not in {s['id'] for s in bound['result']['manifest']['stages']}:
        raise ValueError('Unknown workflow stage')
    c.text(value['reason']); evidence.actor(value['authority'])
    return {'stage_id': value['stage_id'], 'decision': value}


BUILDERS = {'workflow.bind': _bind, 'stage.submit': _submit, 'stage.complete': _complete, 'stage.reopen': _reopen}


def apply(root, kind, payload, expected_revision, request_id, base=None, approval=None):
    return c.transact(root, kind, payload, expected_revision, request_id, base or Path.cwd(), BUILDERS[kind], approval)


def summary(events, native):
    notes = feedback.state(events, native)
    bound = feedback.binding(events)
    rows = [{'id': nid, 'stage_id': n['note']['stage_id'], 'text': n['note']['text'],
             'priority': n['note']['priority'], 'status': n['status'], 'current_validity': n['current_validity'],
             'validity_reason': n['validity_reason'],
             'response_id': n['response_id'], 'missing_targets': n['missing_targets'], 'event_id': n['event_id']}
            for nid, n in notes.items()]
    return {'revision': events[-1]['id'], 'workflow': None if bound is None else {
                'manifest_digest': bound['result']['manifest_digest'], 'binding_event': bound['id'],
                'runtime_compatible': bound['result']['runtime'] == runtime_stamp(),
                'pinned_files_root': bound['artifacts'], 'review_policies': bound['result']['binding']['review_policies'],
                'stages': list(stages(events, native).values())},
            'notes': rows, 'total_notes': len(rows), 'unresolved_blockers': feedback.unresolved(events, native),
            'artistic_acceptance': 'not_evaluated',
            'limits': "Agent reviews are caller-attributed; artist reviews need the owner's terminal (a guard, not a wall); historical resolutions require recheck on changed checkpoints. Older/direct writers bypass this extension."}
