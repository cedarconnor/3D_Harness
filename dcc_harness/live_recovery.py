"""Host recovery and external-state publication; all effects remain explicit in the journal."""
from pathlib import Path
import uuid

from . import blender_bridge, coordination as c, environment_workflow as ew, execution, workflow
from .continuity import Continuity
from .evidence import digest, evaluate, read_json, write_json
from .files import reject_links
from .live_snapshot import equivalent, fingerprint
from .native import run_worker


def _attempt_payload(folder):
    """Keep public intent separate from this persisted native dispatch identity."""
    intent = read_json(reject_links(folder / 'request.json'))
    path = reject_links(folder / 'wire-payload.json')
    if not path.exists():
        return intent  # Retained pre-attempt-identity evidence remains readable, never redispatched.
    payload = read_json(path)
    if payload != {**intent, 'attempt_id': folder.name}:
        raise ValueError('Recovery attempt transport identity changed')
    c.identifier(folder.name)
    return payload


def reconcile(root, operation_id, decision, expected_fingerprint):
    c.identifier(operation_id)
    if decision not in ('keep-current', 'restore-precopy') or not isinstance(expected_fingerprint, str) or len(expected_fingerprint) != 64:
        raise ValueError('Live recovery requires keep-current/restore-precopy and a current fingerprint')
    from .live import read_binding, write_binding
    root = Path(root); folder = reject_links(root / 'execution/operations' / operation_id)
    config = execution.configuration(root)
    if config is None or config.get('backend') != 'live' or config['runtime'] != ew.runtime_stamp():
        raise ValueError('Live recovery requires the project\'s pinned runtime')
    request = read_json(reject_links(folder / 'request.json'))
    if request.get('backend') != 'live':
        raise ValueError('This is not a live operation')
    intent = {'operation_id': operation_id, 'decision': decision, 'expected_fingerprint': expected_fingerprint}
    with execution._exclusive(root), execution._authorized(root, request['stage']):
        from .live import LiveBackend
        backend = LiveBackend(root, folder, None)
        recovered = backend.recover_failure() if not (folder / 'outcome.json').exists() else None
        if recovered is not None:
            return recovered
        recovered = backend.recover_published()
        if recovered is not None:
            return recovered
        receipt, receipt_payload = None, None
        if (folder / 'reconcile-request.json').exists():
            if read_json(folder / 'reconcile-request.json') != intent:
                raise ValueError('Recovery intent changed; inspect the retained recovery')
            if (folder / 'reconciled.json').exists():
                return read_json(folder / 'reconciled.json')
            receipt = read_json(reject_links(folder / 'recovery/receipt.json'))
        attempts = reject_links(folder / 'reconcile-attempts')
        if attempts.exists():
            for previous in attempts.iterdir():
                # Missing/ambiguous replies are never evidence that a restore did not happen.
                refusal = reject_links(previous / 'refusal.json')
                payload = _attempt_payload(previous)
                if not refusal.is_file():
                    identity = previous / 'bridge.json'
                    outcome = (blender_bridge.retained_outcome('recovery_capture', payload,
                               read_json(identity)) if identity.exists() else None)
                    if (isinstance(outcome, dict) and outcome.get('state') == 'REFUSED_BEFORE_MUTATION'):
                        write_json(refusal, outcome)
                    elif (outcome is not None and read_json(previous / 'request.json') == intent
                          and outcome == read_json(reject_links(folder / 'recovery/receipt.json'))):
                        receipt = outcome
                        receipt_payload = payload
                        continue
                    else:
                        raise RuntimeError('Recovery outcome is incomplete; inspect retained evidence, never repeat the restore')
                value = read_json(refusal)
                if (value.get('state') != 'REFUSED_BEFORE_MUTATION'
                        or value.get('request') != payload):
                    raise ValueError('Recovery refusal evidence changed')
        binding = read_binding(root)
        if receipt is None:
            current = blender_bridge.call('attach_check', {'fingerprint':expected_fingerprint}, binding=binding['descriptor'],
                                          expected=(binding['session_id'], binding['generation']))
            if not current.get('matches', current['fingerprint'] == expected_fingerprint):
                raise ValueError('STALE_SCENE: inspect later edits before choosing recovery')
            attempt = attempts / str(uuid.uuid4()); attempt.mkdir(parents=True)
            write_json(attempt / 'request.json', intent)
            payload = {**intent, 'attempt_id': attempt.name}
            write_json(attempt / 'wire-payload.json', payload)
            descriptor = Path(binding['descriptor'])
            if descriptor.exists():
                private = blender_bridge.descriptor(descriptor)
                write_json(attempt / 'bridge.json', {k: private[k] for k in ('workspace', 'session_id', 'generation')})
            receipt = blender_bridge.call('recovery_capture', payload, binding=binding['descriptor'],
                                           expected=(binding['session_id'], binding['generation']))
            if (isinstance(receipt, dict) and set(receipt) == {'state', 'request', 'reason'}
                    and receipt['state'] == 'REFUSED_BEFORE_MUTATION' and receipt['request'] == payload
                    and isinstance(receipt['reason'], str)):
                write_json(attempt / 'refusal.json', receipt)
                raise RuntimeError(receipt['reason'])
            receipt_payload = payload
        if not (folder / 'reconcile-request.json').exists():
            write_json(folder / 'reconcile-request.json', intent)
        if receipt != read_json(folder / 'recovery/receipt.json'):
            raise ValueError('Recovery receipt differs from durable evidence')
        if receipt['operation_id'] != operation_id or receipt['decision'] != decision:
            raise ValueError('Recovery result request identity differs')
        if receipt_payload is not None and 'attempt_id' in receipt_payload and receipt.get('attempt_id') != receipt_payload['attempt_id']:
            raise ValueError('Recovery result attempt identity differs')
        recovery = folder / 'recovery'
        def verify(label, source, snapshot_path, inventory):
            # Verification uses a fresh owned worker directory on resume. It never
            # re-enters the live capture/restore or overwrites prior evidence.
            out = recovery / (label + '-' + str(uuid.uuid4())); out.mkdir()
            run_worker(request['blender'], out, Path(__file__).with_name('_live_verify_blender.py'), 'verify',
                {'source': source, 'out': str(out), 'scene': receipt['scene'], 'inventory': inventory,
                 'snapshot': snapshot_path, 'fingerprint': fingerprint(read_json(snapshot_path))}, timeout=60)
            return out / 'observation.json'
        archive_observation = verify('archive-check', receipt['archive'], receipt['archive_snapshot'], receipt['archive_inventory'])
        observation = (archive_observation if decision == 'keep-current' else
                       verify('restored-check', receipt['source'], receipt['snapshot'], receipt['inventory']))
        reserved = read_json(folder / 'reservation.json')
        edit = root / 'edits' / reserved['edit']
        if not (edit / 'outcome.json').exists():
            # A previous publication attempt may already have frozen its check. Reuse it exactly.
            candidate_observed = (folder / 'observation.json').exists() and (folder / 'candidate.blend').exists()
            checkpoint = folder / 'candidate.blend' if candidate_observed else receipt['archive']['path']
            check_observation = folder / 'observation.json' if candidate_observed else archive_observation
            outcome = workflow.finish_edit(root, reserved['edit'], checkpoint, check_observation, folder / 'handoff.md', {},
                                           reconciled=True, reject_reason='Explicit live recovery: ' + decision)
        else:
            outcome = read_json(edit / 'outcome.json')
        if not (folder / 'outcome.json').exists():
            write_json(folder / 'outcome.json', {'operation_id': operation_id, 'status': outcome['status'],
                                                'outcome': outcome, 'live_state': 'RECOVERING'})
        state = blender_bridge.call('attach_check', {'fingerprint': receipt['fingerprint'], 'snapshot': receipt['snapshot']},
                                     binding=binding['descriptor'], expected=(receipt['session_id'], receipt['generation']))
        if not state['matches']:
            raise ValueError('LIVE_DIVERGED during recovery verification')
        active = Continuity(root).status()['active']
        accepted_snapshot = read_json(binding['snapshot'])
        external_step = 'external-recovery-' + operation_id
        committed = active['step_id'] == external_step and active['checkpoint_sha256'] == receipt['source']['sha256']
        if binding['checkpoint'] != active['id'] and not committed:
            raise ValueError('Binding does not identify the current accepted parent; inspect recovery evidence')
        if committed or not equivalent(accepted_snapshot, read_json(receipt['snapshot'])):
            observed = read_json(observation)
            if observed['issues'] or not observed['objects']:
                raise ValueError('External state has unsupported observations; archived but not published')
            check = evaluate(observed, {'schema': 'dcc.spec.v1', 'required': {key: {} for key in observed['objects']}})
            check['live_external_revision'] = {'decision': decision, 'operation_id': operation_id,
                                               'source': receipt['source'], 'artistic_acceptance': 'not_assessed'}
            check_path = recovery / 'external-check.json'
            if check_path.exists():
                if read_json(check_path) != check:
                    raise ValueError('External recovery check changed')
            else:
                write_json(check_path, check)
            if not committed:
                with workflow.writer_guard(root):
                    latest = blender_bridge.call('attach_check', {'fingerprint': receipt['fingerprint'], 'snapshot': receipt['snapshot']},
                                                  binding=binding['descriptor'], expected=(receipt['session_id'], receipt['generation']))
                    if not latest['matches']:
                        raise ValueError('LIVE_DIVERGED before external-state publication')
                    token = execution._recovery.set(True)
                    try:
                        execution.check_publication(root)
                    finally:
                        execution._recovery.reset(token)
                    active = Continuity(root).publish(external_step, active['id'], receipt['source']['path'],
                        observation, folder / 'handoff.md', {'live_external_revision': decision}, check_path)['active']
            # A technical external-state checkpoint invalidates every prior stage decision.
            events = c.read(root)
            first = ew._binding(c.Context(root, Continuity(root).status(), events, root))['result']['manifest']['stages'][0]['id']
            ew.apply(root, 'stage.reopen', {'schema': 'dcc.environment.reopen.v1', 'stage_id': first,
                'reason': 'External live state imported by explicit recovery',
                'authority': {'role': 'agent', 'author': 'live recovery', 'reference': decision}},
                events[-1]['id'], str(uuid.uuid5(uuid.UUID(operation_id), 'external-recovery-reopen')), root)
        new = {**binding, 'generation': receipt['generation'], 'checkpoint': active['id'], 'fingerprint': receipt['fingerprint'],
               'snapshot': receipt['snapshot'], 'state': 'LIVE_DIVERGED'}
        write_binding(root, new)
        blender_bridge.call('recovery_acknowledge', {'operation_id': operation_id}, binding=binding['descriptor'],
                             expected=(receipt['session_id'], receipt['generation']))
        write_binding(root, {**new, 'state': 'READY'})
        result = {'operation_id': operation_id, 'decision': decision, 'live_state': 'READY', 'archive': receipt['archive'],
                  'working_filepath': receipt['working_filepath'], 'checkpoint': active['id']}
        write_json(folder / 'reconciled.json', result)
        return result
