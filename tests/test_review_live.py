"""Maintained regressions for C1-C9 live transport review follow-up."""
import contextlib
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
import uuid
from unittest import mock

from dcc_harness import blender_bridge, live, live_recovery
from dcc_harness.evidence import read_json, write_json
from test_live_protocol import bridge_leaf
from test_live_review import STUBS
import test_live_jobs as live_job_tests
from coordination_helpers import Fixture


class TransportTests(unittest.TestCase):
    @staticmethod
    def capture_payload():
        return {'operation_id':str(uuid.uuid4()),'decision':'keep-current',
                'expected_fingerprint':'a'*64,'attempt_id':str(uuid.uuid4())}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.session = bridge_leaf('session').Session(self.tmp.name, 9878)
        self.private = blender_bridge.descriptor(self.session.descriptor_path)
        self.info = {'harness_protocol': 3, 'protocol_version': 14,
                     'upstream_commit': blender_bridge.upstream()['commit'],
                     'features': list(blender_bridge.FEATURES),
                     'paired_commands': list(blender_bridge.PAIRED_COMMANDS),
                     'bridge_manifest': blender_bridge.bridge_manifest()}

    def test_copy_deadline_is_independent_of_short_handshake(self):
        with mock.patch.object(blender_bridge, '_request', side_effect=[self.info, {}]) as send:
            blender_bridge.call('recovery_capture', self.capture_payload(), binding=self.session.descriptor_path)
        self.assertGreaterEqual(send.call_args_list[1].args[3], 120)
        self.assertLessEqual(send.call_args_list[0].args[3], 10)

    def test_lost_reply_recovers_exact_durable_refusal_without_redispatch(self):
        payload = {'request': {'operation_id': str(uuid.uuid4())}}
        refusal = {'state': 'REFUSED_BEFORE_MUTATION', 'request': payload, 'reason': 'UNSAVED_IMAGE'}
        def send(port, command, params, timeout):
            if command == 'get_addon_info': return self.info
            self.session.retain_outcome(command, params['payload'], refusal)
            raise TimeoutError('lost reply')
        with mock.patch.object(blender_bridge, '_request', side_effect=send) as request:
            result = blender_bridge.call('job_prepare', payload, binding=self.session.descriptor_path)
        self.assertEqual(result, refusal)
        self.assertEqual(request.call_count, 2)
        changed = {'request': {'operation_id': str(uuid.uuid4())}}
        self.assertIsNone(blender_bridge.retained_outcome('job_prepare', changed, self.private))

    def test_lost_submit_success_uses_durable_result_without_redispatch(self):
        operation = str(uuid.uuid4())
        payload = {'operation_id': operation, 'prepared': {'proof': 'owned'}}
        dispatches = []
        def send(port, command, params, timeout):
            if command == 'get_addon_info': return self.info
            dispatches.append(command)
            self.session.retain_outcome(command, params['payload'], operation)
            raise ConnectionError('response lost after durable success')
        with mock.patch.object(blender_bridge, '_request', side_effect=send):
            self.assertEqual(blender_bridge.call('job_submit', payload, binding=self.session.descriptor_path), operation)
            self.assertEqual(blender_bridge.call('job_submit', payload, binding=self.session.descriptor_path), operation)
        self.assertEqual(dispatches, ['job_submit'])
        changed = {**payload, 'operation_id': str(uuid.uuid4())}
        self.assertIsNone(blender_bridge.retained_outcome('job_submit', changed, self.private))

    def test_lost_submit_without_durable_result_remains_unknown(self):
        payload = {'operation_id': str(uuid.uuid4()), 'prepared': {'proof': 'owned'}}
        dispatches = []
        def send(port, command, params, timeout):
            if command == 'get_addon_info': return self.info
            dispatches.append(command)
            raise ConnectionError('response lost with no durable evidence')
        with mock.patch.object(blender_bridge, '_request', side_effect=send):
            with self.assertRaises(blender_bridge.BridgeTransportError):
                blender_bridge.call('job_submit', payload, binding=self.session.descriptor_path)
        self.assertEqual(dispatches, ['job_submit'])
        self.assertIsNone(blender_bridge.retained_outcome('job_submit', payload, self.private))

    def test_dead_session_is_only_definite_process_or_connection_evidence(self):
        with mock.patch.object(blender_bridge, 'call', side_effect=RuntimeError('deadline exceeded')):
            self.assertEqual(blender_bridge.session_presence(self.session.descriptor_path), 'UNKNOWN')
        with mock.patch.object(blender_bridge, 'call', side_effect=ConnectionRefusedError()):
            self.assertEqual(blender_bridge.session_presence(self.session.descriptor_path), 'UNAVAILABLE')

    def test_descriptor_retains_process_identity_for_crash_detection(self):
        self.assertIsInstance(self.private.get('pid'), int)
        with mock.patch.object(blender_bridge, '_process_alive', return_value=False):
            self.assertEqual(blender_bridge.session_presence(self.session.descriptor_path), 'DEAD')

    def test_durable_result_recovers_later_without_socket_contact(self):
        payload = self.capture_payload()
        self.session.retain_outcome('recovery_capture', payload, {'archive': 'retained'})
        with mock.patch.object(blender_bridge, '_request') as send:
            result = blender_bridge.call('recovery_capture', payload, binding=self.session.descriptor_path)
        self.assertEqual(result, {'archive': 'retained'})
        send.assert_not_called()

    def test_retained_outcome_is_one_exact_immutable_record_and_redacts_pairing_secret(self):
        payload=self.capture_payload()
        for _ in range(3): self.session.retain_outcome('recovery_capture',payload,{'state':'saved'})
        files=list((Path(self.tmp.name)/'.harness-mcp/outcomes'/self.session.session_id).glob('*.json'))
        self.assertEqual(len(files),1)
        with self.assertRaisesRegex(ValueError,'changed'):
            self.session.retain_outcome('recovery_capture',payload,{'state':'different'})
        files[0].write_text(json.dumps({**json.loads(files[0].read_text()),'result':{'message':self.private['token']}}))
        with self.assertRaisesRegex(ValueError,'sensitive') as error:
            blender_bridge.retained_outcome('recovery_capture',payload,self.private)
        self.assertNotIn(self.private['token'],str(error.exception))


class RecoveryEvidenceTests(unittest.TestCase):
    def test_same_intent_after_refusal_gets_one_fresh_capture_and_lost_success_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            workspace=Path(tmp); session=bridge_leaf('session').Session(workspace,9878)
            root=workspace/'state'; op=str(uuid.uuid4()); folder=root/'execution/operations'/op; folder.mkdir(parents=True)
            write_json(folder/'request.json',{'backend':'live','stage':'direction','blender':'fixture'})
            binding={'descriptor':str(session.descriptor_path),'session_id':session.session_id,'generation':session.generation}
            stack.enter_context(mock.patch.object(live_recovery.execution,'configuration',return_value={'backend':'live','runtime':'pin'}))
            stack.enter_context(mock.patch.object(live_recovery.ew,'runtime_stamp',return_value='pin'))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_exclusive',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_authorized',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live,'read_binding',return_value=binding))
            info={'harness_protocol':3,'protocol_version':14,'upstream_commit':blender_bridge.upstream()['commit'],
                  'features':list(blender_bridge.FEATURES),'paired_commands':list(blender_bridge.PAIRED_COMMANDS),
                  'bridge_manifest':blender_bridge.bridge_manifest()}
            wire=[]; successful_captures=[]
            def send(port,command,params,timeout,**kwargs):
                if command=='get_addon_info': return info
                if command=='attach_check': return {'fingerprint':'a'*64}
                self.assertEqual(command,'recovery_capture')
                if 'before_send' in kwargs: kwargs['before_send']()
                payload=params['payload']; wire.append(payload)
                if len(wire)==1:
                    result={'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'BUSY: temporary'}
                    session.retain_outcome(command,payload,result)
                    return result
                successful_captures.append(payload)
                recovery=folder/'recovery'; recovery.mkdir(); write_json(recovery/'snapshot.json',{})
                result={'operation_id':op,'decision':'keep-current','scene':'Scene','archive':{},
                        'archive_snapshot':str(recovery/'snapshot.json'),'archive_inventory':{},
                        **({'attempt_id':payload['attempt_id']} if 'attempt_id' in payload else {})}
                write_json(recovery/'receipt.json',result)
                session.retain_outcome(command,payload,result)
                raise TimeoutError('successful capture response lost')
            stack.enter_context(mock.patch.object(blender_bridge,'_request',side_effect=send))
            stack.enter_context(mock.patch.object(live_recovery,'run_worker',side_effect=RuntimeError('Owned verification reached')))
            with self.assertRaisesRegex(RuntimeError,'BUSY'):
                live_recovery.reconcile(root,op,'keep-current','a'*64)
            # The BUSY condition is now clear; decision, fingerprint and generation are unchanged.
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'Owned verification reached'):
                    live_recovery.reconcile(root,op,'keep-current','a'*64)
            self.assertEqual(len(wire),2)
            self.assertEqual(len(successful_captures),1)
            self.assertNotEqual(wire[0]['attempt_id'],wire[1]['attempt_id'])
            self.assertEqual({k:v for k,v in wire[0].items() if k!='attempt_id'},
                             {k:v for k,v in wire[1].items() if k!='attempt_id'})
            attempts=list((folder/'reconcile-attempts').iterdir())
            self.assertEqual(len(attempts),2)
            self.assertEqual(read_json(attempts[0]/'request.json'),read_json(attempts[1]/'request.json'))

    def test_late_capture_result_resumes_verification_without_another_native_capture(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            workspace=Path(tmp); session=bridge_leaf('session').Session(workspace,9878)
            root=workspace/'state'; op=str(uuid.uuid4()); folder=root/'execution/operations'/op; folder.mkdir(parents=True)
            write_json(folder/'request.json',{'backend':'live','stage':'direction','blender':'fixture'})
            binding={'descriptor':str(session.descriptor_path),'session_id':session.session_id,'generation':session.generation}
            stack.enter_context(mock.patch.object(live_recovery.execution,'configuration',return_value={'backend':'live','runtime':'pin'}))
            stack.enter_context(mock.patch.object(live_recovery.ew,'runtime_stamp',return_value='pin'))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_exclusive',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_authorized',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live,'read_binding',return_value=binding))
            intent={'operation_id':op,'decision':'keep-current','expected_fingerprint':'a'*64}
            attempt=folder/'reconcile-attempts'/str(uuid.uuid4()); attempt.mkdir(parents=True)
            write_json(attempt/'request.json',intent)
            private=blender_bridge.descriptor(session.descriptor_path)
            write_json(attempt/'bridge.json',{k:private[k] for k in ('workspace','session_id','generation')})
            recovery=folder/'recovery'; recovery.mkdir(); write_json(recovery/'archive-snapshot.json',{})
            receipt={'operation_id':op,'decision':'keep-current','scene':'Scene','archive':{},
                     'archive_snapshot':str(recovery/'archive-snapshot.json'),'archive_inventory':{}}
            write_json(recovery/'receipt.json',receipt)
            # Legacy pre-attempt-identity evidence remains consumable without dispatch.
            session.retain_outcome('recovery_capture',intent,receipt)
            native=stack.enter_context(mock.patch.object(blender_bridge,'call',side_effect=AssertionError('Native capture replayed')))
            stack.enter_context(mock.patch.object(live_recovery,'run_worker',side_effect=RuntimeError('Owned verification reached')))
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'Owned verification reached'):
                    live_recovery.reconcile(root,op,'keep-current','a'*64)
            native.assert_not_called()

    def test_lost_refusal_is_consumed_before_another_recovery_intent(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            workspace=Path(tmp); session=bridge_leaf('session').Session(workspace,9878)
            root=workspace/'state'; op=str(uuid.uuid4()); folder=root/'execution/operations'/op; folder.mkdir(parents=True)
            write_json(folder/'request.json',{'backend':'live','stage':'direction'})
            binding={'descriptor':str(session.descriptor_path),'session_id':session.session_id,'generation':session.generation}
            stack.enter_context(mock.patch.object(live_recovery.execution,'configuration',return_value={'backend':'live','runtime':'pin'}))
            stack.enter_context(mock.patch.object(live_recovery.ew,'runtime_stamp',return_value='pin'))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_exclusive',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live_recovery.execution,'_authorized',side_effect=lambda *a:contextlib.nullcontext()))
            stack.enter_context(mock.patch.object(live,'read_binding',return_value=binding))
            captures=[]
            def call(command,payload,**kwargs):
                if command=='attach_check': return {'fingerprint':'a'*64}
                if 'before_dispatch' in kwargs:
                    kwargs['before_dispatch'](blender_bridge.descriptor(session.descriptor_path))
                captures.append(payload)
                result={'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'BUSY: fixture'}
                session.retain_outcome(command,payload,result)
                raise TimeoutError('lost refusal response')
            stack.enter_context(mock.patch.object(blender_bridge,'call',side_effect=call))
            with self.assertRaisesRegex(TimeoutError,'lost'):
                live_recovery.reconcile(root,op,'keep-current','a'*64)
            with self.assertRaisesRegex(TimeoutError,'lost'):
                live_recovery.reconcile(root,op,'keep-current','a'*64)
            self.assertEqual(len(captures),2)
            attempts=list((folder/'reconcile-attempts').iterdir())
            self.assertTrue(any((p/'refusal.json').exists() for p in attempts))


class HostRefusalTests(Fixture):
    request = live_job_tests.LivePublicationTests.request
    start = live_job_tests.LivePublicationTests.start
    backend = live_job_tests.LivePublicationTests.backend
    def binding(self):
        session = bridge_leaf('session').Session(self.base, 9878)
        binding = {'descriptor': str(session.descriptor_path), 'session_id': session.session_id,
                   'generation': session.generation, 'scene': 'Scene', 'state': 'READY',
                   'checkpoint': self.packet['active']['id'], 'fingerprint': 'a' * 64, 'snapshot': 'snapshot'}
        (self.root / 'live').mkdir(); write_json(self.root / 'live/binding.json', binding)
        return session

    def test_confirmed_prepare_refusal_closes_reservation_and_keeps_alignment(self):
        self.start(); self.binding()
        def call(command, payload, **kwargs):
            if command == 'job_prepare':
                return {'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'UNSUPPORTED_COVERAGE'}
            if command == 'attach_check':
                return {'matches':True,'session_id':kwargs['expected'][0], 'generation':kwargs['expected'][1], 'scene':'Scene'}
            raise AssertionError('Refusal must never submit: ' + command)
        with mock.patch.object(blender_bridge, 'call', side_effect=call):
            result = live.execute(self.root, self.request())
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(live.read_binding(self.root)['state'], 'READY')
        self.assertEqual(live.workflow.Continuity(self.root).status()['pending'], [])

    def test_prepare_divergence_refusal_closes_reservation_but_stays_diverged(self):
        self.start(); self.binding()
        def call(command, payload, **kwargs):
            if command == 'job_prepare':
                return {'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'LIVE_DIVERGED'}
            if command == 'attach_check': return {'matches':False}
            raise AssertionError(command)
        with mock.patch.object(blender_bridge, 'call', side_effect=call):
            result = live.execute(self.root, self.request())
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(live.read_binding(self.root)['state'], 'LIVE_DIVERGED')

    def test_attach_retry_requires_exact_durable_refusal(self):
        workspace = self.base
        session = bridge_leaf('session').Session(workspace, 9878)
        destination = workspace / 'new-attach'
        brief = workspace / 'attach-brief.md'; brief.write_text('Owned attachment')
        calls = []
        def call(command, payload, **kwargs):
            calls.append(command)
            if command == 'session_describe': return {'scenes':['Scene'],'generation':session.generation}
            if command == 'attach_begin':
                result = {'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'UNSAVED_IMAGE'}
                session.retain_outcome(command,payload,result)
                return result
            raise AssertionError(command)
        options = dict(scene='Scene', brief_file=brief, mode='autonomous', blender='fixture')
        with mock.patch.object(blender_bridge,'call',side_effect=call):
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'UNSAVED_IMAGE'):
                    live.attach(destination,session.descriptor_path,**options)
        self.assertEqual(calls.count('attach_begin'),2)

    def test_late_prepare_refusal_is_recovered_by_identical_intent_without_submission(self):
        self.start(); session = self.binding(); request = self.request()
        with mock.patch.object(blender_bridge, 'call', side_effect=TimeoutError('reply lost')):
            result = live.execute(self.root, request)
        self.assertEqual(result['status'],'NEEDS_RECONCILIATION')
        folder = self.root / 'execution/operations' / request['operation_id']
        payload = json.loads((folder / 'live-transport.json').read_text())['payload']
        session.retain_outcome('job_prepare',payload,{'state':'REFUSED_BEFORE_MUTATION','request':payload,'reason':'expired'})
        with mock.patch.object(blender_bridge, 'call', return_value={'matches':True,'scene':'Scene',
                'session_id':session.session_id,'generation':session.generation}) as call:
            result = live.execute(self.root,request)
        self.assertEqual(result['status'],'REJECTED')
        self.assertEqual([c.args[0] for c in call.call_args_list],['attach_check'])

    def test_published_live_operation_recovers_alignment_without_recovery_mutation(self):
        self.start(); session=self.binding(); request=self.request(); backend=self.backend()
        backend.published = mock.Mock(side_effect=OSError('interrupted after checkpoint publication'))
        with mock.patch('dcc_harness.execution.make_backend',return_value=backend):
            result=live.execute(self.root,request)
        self.assertEqual(result['status'],'NEEDS_RECONCILIATION')
        folder=self.root/'execution/operations'/request['operation_id']
        receipt={**backend.status(request['operation_id']), 'fingerprint':'b'*64,'snapshot':'retained-snapshot',
                 'session_id':session.session_id,'generation':session.generation,'scene':'Scene'}
        write_json(folder/'live-status.json',receipt)
        def call(command,payload,**kwargs):
            if command=='job_check': return receipt
            if command=='attach_check': return {'matches':True,'fingerprint':'b'*64}
            if command=='job_acknowledge': return {'state':'READY'}
            raise AssertionError('Published work must never enter recovery mutation: '+command)
        with mock.patch.object(blender_bridge,'call',side_effect=call):
            result=live_recovery.reconcile(self.root,request['operation_id'],'keep-current','b'*64)
        self.assertEqual(result['status'],'PUBLISHED')
        self.assertEqual(result['live_state'],'READY')
        self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)

    def external_recovery(self):
        from dcc_harness import execution
        from dcc_harness.evidence import file_hash
        self.start(); self.binding(); request=self.request(); backend=self.backend(lost=True)
        with mock.patch('dcc_harness.execution.make_backend',return_value=backend):
            live.execute(self.root,request)
        folder=self.root/'execution/operations'/request['operation_id']; recovery=folder/'recovery'; recovery.mkdir()
        archive=recovery/'archive.blend'; archive.write_bytes(b'owned archive')
        snapshot=recovery/'snapshot.json'; write_json(snapshot,{'objects':{'external':{}}})
        accepted=self.root/'live/accepted.json'; write_json(accepted,{'objects':{}})
        binding=live.read_binding(self.root); live.write_binding(self.root,{**binding,'snapshot':str(accepted)})
        intent={'operation_id':request['operation_id'],'decision':'keep-current','expected_fingerprint':'a'*64}
        write_json(folder/'reconcile-request.json',intent)
        source={'path':str(archive),'sha256':file_hash(archive)}
        receipt={'operation_id':request['operation_id'],'decision':'keep-current','scene':'Scene',
                 'archive':source,'source':source,'archive_snapshot':str(snapshot),'snapshot':str(snapshot),
                 'archive_inventory':{},'inventory':{},'fingerprint':'a'*64,'session_id':binding['session_id'],
                 'generation':binding['generation'],'working_filepath':'owned'}
        write_json(recovery/'receipt.json',receipt)
        def worker(blender,out,worker,action,payload,**kwargs):
            obs=copy.deepcopy(self.obs); obs['checkpoint_sha256']=source['sha256']; write_json(out/'observation.json',obs)
        return request,receipt,worker

    def test_terminal_cancel_cannot_publish_new_external_recovery_checkpoint(self):
        from dcc_harness import execution
        request,receipt,worker=self.external_recovery()
        execution.cancel(self.root)
        with mock.patch.object(live_recovery,'run_worker',side_effect=worker), mock.patch.object(blender_bridge,'call',return_value={'matches':True}):
            with self.assertRaisesRegex(RuntimeError,'cancelled'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current','a'*64)
        self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),1)

    def test_external_recovery_resumes_after_checkpoint_commit_without_republication(self):
        request,receipt,worker=self.external_recovery()
        with mock.patch.object(live_recovery,'run_worker',side_effect=worker), \
             mock.patch.object(blender_bridge,'call',return_value={'matches':True}), \
             mock.patch.object(live,'write_binding',side_effect=OSError('interrupted alignment persistence')):
            with self.assertRaisesRegex(OSError,'interrupted alignment'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current','a'*64)
        self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)
        with mock.patch.object(live_recovery,'run_worker',side_effect=worker), \
             mock.patch.object(blender_bridge,'call',return_value={'matches':True}):
            result=live_recovery.reconcile(self.root,request['operation_id'],'keep-current','a'*64)
        self.assertEqual(result['live_state'],'READY')
        self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)

    def test_published_live_capability_recovers_frozen_receipt_without_native_mutation(self):
        from dcc_harness import capabilities, execution
        from dcc_harness.evidence import digest, file_hash
        import test_review_execution as review_execution
        request=review_execution.ReviewExecutionTests.capability_request(self)
        request.update(backend='live',live={'recipe':'capability.recipe','target':'ext.table.top',
                                         'parameters':{'operation_id':request['operation_id']}})
        self.binding(); backend=self.backend(); original_submit=backend.submit; original_verify=backend.verify
        def submit(request,prepared):
            result=original_submit(request,prepared); folder=Path(request['output']).parent
            measured=capabilities.observed_scope(self.obs,'ext.table.top',['geometry','materials'])
            output={'effect_id':request['capability']['effect_id'],'effect_count':1,'measurements':measured}
            write_json(folder/'capability-output.json',{'after':measured,'output':output,'output_fingerprint':digest(output)})
            return result
        def verify(receipt):
            original_verify(receipt); folder=Path(receipt['candidate']).parent
            value=json.loads((folder/'capability-output.json').read_text())
            write_json(folder/'capability-verified.json',{'passed':True,'output':value['output'],
                'measurements':value['after'],'output_fingerprint':value['output_fingerprint']})
        backend.submit=submit; backend.verify=verify
        config=execution.configuration(self.root)
        with mock.patch.object(execution,'configuration',return_value={**config,'backend':'live'}), \
             mock.patch.object(capabilities,'admit'), mock.patch.object(capabilities,'reuse',return_value=None), \
             mock.patch('dcc_harness.live.ensure_aligned',return_value={}), \
             mock.patch('dcc_harness.recipes.require_qualified',return_value={'recipe':{'coverage':{'reads':['geometry','materials'],'writes':[],'dependencies':[]}}}):
            with mock.patch('dcc_harness.execution.make_backend',return_value=backend), \
                 mock.patch.object(capabilities,'record_operation',side_effect=OSError('lost final receipt')):
                result=live.execute(self.root,request)
            self.assertEqual(result['status'],'NEEDS_RECONCILIATION')
            folder=self.root/'execution/operations'/request['operation_id']
            self.assertTrue((folder/'capability-publication.json').exists())
            binding=live.read_binding(self.root)
            snapshot=folder/'live-snapshot.json'; write_json(snapshot,{'objects':{}})
            from dcc_harness.live_snapshot import fingerprint
            receipt={**backend.status(request['operation_id']),'fingerprint':fingerprint({'objects':{}}),'snapshot':str(snapshot),
                     'session_id':binding['session_id'],'generation':binding['generation'],'scene':'Scene'}
            write_json(folder/'live-status.json',receipt)
            def call(command,payload,**kwargs):
                if command=='job_check': return receipt
                if command=='job_acknowledge': return {'state':'READY'}
                raise AssertionError('Never dispatch or recapture: '+command)
            with mock.patch.object(blender_bridge,'call',side_effect=call):
                result=live_recovery.reconcile(self.root,request['operation_id'],'keep-current','b'*64)
            self.assertEqual(result['status'],'PUBLISHED')
            self.assertEqual(result['capability_receipt']['sha256'],file_hash(folder/'capability-receipt.json'))
            self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)
            frozen_sha=result['capability_receipt']['sha256']
            replacement=bridge_leaf('session').Session(self.base,9879)
            fresh={**replacement.describe(),'scene':'Scene','snapshot':str(snapshot),
                   'fingerprint':receipt['fingerprint'],'matches':True}
            with mock.patch.object(blender_bridge,'session_presence',return_value='DEAD'), \
                 mock.patch.object(blender_bridge,'call',return_value=fresh):
                live.refresh(self.root,replacement.descriptor_path,expected_parent=result['outcome']['active']['id'])
            def new_session(command,payload,**kwargs):
                self.assertEqual(command,'attach_check')
                return fresh
            with mock.patch.object(blender_bridge,'call',side_effect=new_session):
                aligned=live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])
            self.assertEqual(aligned['capability_receipt']['sha256'],frozen_sha)
            self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)

    def ack_failure_recovery(self, cross_session=False, interrupted=False):
        from dcc_harness import capabilities, execution
        from dcc_harness.evidence import digest, file_hash
        import test_review_execution as review_execution
        request=review_execution.ReviewExecutionTests.capability_request(self)
        request.update(backend='live',live={'recipe':'capability.recipe','target':'ext.table.top',
                                         'parameters':{'operation_id':request['operation_id']}})
        self.binding(); backend=self.backend(); original_submit=backend.submit; original_verify=backend.verify
        def submit(request,prepared):
            result=original_submit(request,prepared); folder=Path(request['output']).parent
            measured=capabilities.observed_scope(self.obs,'ext.table.top',['geometry','materials'])
            output={'effect_id':request['capability']['effect_id'],'effect_count':1,'measurements':measured}
            write_json(folder/'capability-output.json',{'after':measured,'output':output,'output_fingerprint':digest(output)})
            return result
        def verify(receipt):
            original_verify(receipt); folder=Path(receipt['candidate']).parent
            value=json.loads((folder/'capability-output.json').read_text())
            write_json(folder/'capability-verified.json',{'passed':True,'output':value['output'],
                'measurements':value['after'],'output_fingerprint':value['output_fingerprint']})
        backend.submit=submit; backend.verify=verify
        def published(result, receipt):
            folder=Path(receipt['candidate']).parent
            snapshot=folder/'live-snapshot.json'; write_json(snapshot,{'objects':{}})
            from dcc_harness.live_snapshot import fingerprint
            binding=live.read_binding(self.root)
            receipt.update(fingerprint=fingerprint({'objects':{}}), snapshot=str(snapshot),
                           session_id=binding['session_id'],generation=binding['generation'],scene='Scene')
            write_json(folder/'live-status.json',receipt)
            with mock.patch.object(blender_bridge,'call',side_effect=OSError('lost final acknowledgement')):
                return live.LiveBackend(self.root,folder,None).published(result,receipt)
        backend.published=published
        config=execution.configuration(self.root)
        with mock.patch.object(execution,'configuration',return_value={**config,'backend':'live'}), \
             mock.patch.object(capabilities,'admit'), \
             mock.patch('dcc_harness.live.ensure_aligned',return_value={}), \
             mock.patch('dcc_harness.recipes.require_qualified',return_value={'recipe':{'coverage':{'reads':['geometry','materials'],'writes':[],'dependencies':[]}}}):
            with mock.patch('dcc_harness.execution.make_backend',return_value=backend), \
                 mock.patch.object(capabilities,'reuse',return_value=None):
                result=live.execute(self.root,request)
            self.assertEqual(result['status'],'PUBLISHED')
            self.assertEqual(result['live_state'],'LIVE_DIVERGED')
            self.assertIsNone(result['capability_receipt'])
            folder=self.root/'execution/operations'/request['operation_id']
            self.assertTrue((folder/'capability-publication.json').exists())
            original=(folder/'outcome.json').read_bytes()
            receipt=read_json(folder/'live-status.json')
            if cross_session:
                replacement=bridge_leaf('session').Session(self.base,9879)
                fresh={**replacement.describe(),'scene':'Scene','snapshot':receipt['snapshot'],
                       'fingerprint':receipt['fingerprint'],'matches':True}
                with mock.patch.object(blender_bridge,'session_presence',return_value='DEAD'), \
                     mock.patch.object(blender_bridge,'call',return_value=fresh):
                    live.refresh(self.root,replacement.descriptor_path,expected_parent=result['outcome']['active']['id'])
            def call(command,payload,**kwargs):
                if cross_session and command=='attach_check': return fresh
                if command=='job_check': return receipt
                if command=='job_acknowledge': return {'state':'READY'}
                raise AssertionError('Never dispatch or recapture: '+command)
            if interrupted:
                rename=Path.rename
                def interrupt(path,target):
                    if Path(target).name=='recovered-outcome.json': raise OSError('interrupted recovery commit')
                    return rename(path,target)
                with mock.patch.object(blender_bridge,'call',side_effect=call), mock.patch.object(Path,'rename',interrupt):
                    with self.assertRaisesRegex(OSError,'interrupted recovery commit'):
                        live_recovery.reconcile(self.root,request['operation_id'],'keep-current','b'*64)
                self.assertEqual(execution._outcome(folder)['live_state'],'LIVE_DIVERGED')
                self.assertTrue(list(folder.glob('recovered-outcome-*.tmp')))
                self.assertTrue((folder/'capability-receipt.json').exists())
            with mock.patch.object(blender_bridge,'call',side_effect=call):
                result=live_recovery.reconcile(self.root,request['operation_id'],'keep-current','b'*64)
            self.assertEqual(result['status'],'PUBLISHED')
            self.assertEqual(result['capability_receipt']['sha256'],file_hash(folder/'capability-receipt.json'))
            self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)
            self.assertEqual((folder/'outcome.json').read_bytes(),original)
            self.assertEqual(read_json(folder/'outcome.json')['live_error'],'lost final acknowledgement')
            effective=execution._outcome(folder)
            self.assertEqual(effective['live_state'],'READY')
            self.assertEqual(effective['capability_receipt'],result['capability_receipt'])
            self.assertEqual(execution.status(self.root)['operations'][0],effective)
            self.assertEqual(live.execute(self.root,request),effective)
            from dcc_harness import coordination as c
            req=capabilities.requirements(self.root,'direction',read_json(result['outcome']['active']['observation']))[0]
            cp=c.checkpoint_ref(result['outcome']['active'])
            self.assertTrue(capabilities.verify_operation_receipt(self.root,folder,req,cp))
            self.assertTrue(capabilities.verify_receipts(self.root,'direction',cp)['passed'])
            with mock.patch.object(capabilities,'resolve',return_value=request['capability']['resolution']), \
                 mock.patch.object(capabilities,'inventory_for_requirement',return_value={}):
                self.assertEqual(capabilities.reuse(self.root,req,request['capability']['resolution'],req['rule']['parameters'])['status'],'REUSED')
            self.assertEqual(backend.dispatches,1)
            return folder,req,cp

    def test_existing_ack_failure_same_session_has_durable_usable_receipt(self):
        self.ack_failure_recovery()

    def test_existing_ack_failure_cross_session_has_durable_usable_receipt(self):
        self.ack_failure_recovery(cross_session=True)

    def test_recovery_commit_interruption_retains_original_and_retries_without_replay(self):
        self.ack_failure_recovery(interrupted=True)

    def test_recovered_receipt_linkage_rejects_none_malformed_or_changed_evidence(self):
        from dcc_harness import execution, capabilities
        folder,req,cp=self.ack_failure_recovery()
        path=folder/'recovered-outcome.json'; original=read_json(path)
        for ref in (None, [], {'path':'wrong','sha256':'a'*64}):
            changed=copy.deepcopy(original); changed['outcome']['capability_receipt']=ref
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'receipt linkage'):
                execution._outcome(folder)
        path.write_text(json.dumps(original))
        incomplete=read_json(folder/'outcome.json')
        for ref in (None, [], {'path':'wrong','sha256':'a'*64}):
            with mock.patch.object(execution,'_outcome',return_value={**incomplete,'capability_receipt':ref}):
                with self.assertRaisesRegex(ValueError,'service publication'):
                    capabilities.verify_operation_receipt(self.root,folder,req,cp)
        with (folder/'capability-publication.json').open('a') as stream: stream.write(' ')
        with self.assertRaisesRegex(ValueError,'publication linkage'):
            execution._outcome(folder)

    def test_recovered_receipt_and_public_status_accept_equivalent_project_paths(self):
        import os
        from dcc_harness import capabilities
        import dcc_harness
        folder,req,cp=self.ack_failure_recovery()
        relative=self.root.relative_to(self.base)
        aliases=[relative,relative/'..'/relative.name]
        if os.name=='nt': aliases.append(Path(str(self.root).swapcase()))
        previous=Path.cwd()
        env={**os.environ,'PYTHONPATH':str(Path(dcc_harness.__file__).parent.parent)}
        try:
            os.chdir(self.base)
            for root in aliases:
                with self.subTest(root=str(root)):
                    result=subprocess.run([sys.executable,'-m','dcc_harness','run-status',str(root)],
                                          env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                    self.assertEqual(json.loads(result.stdout)['operations'][0]['live_state'],'READY')
                    with mock.patch('dcc_harness.recipes.require_qualified',return_value={'recipe':{'coverage':{'reads':['geometry','materials'],'writes':[],'dependencies':[]}}}):
                        self.assertTrue(capabilities.verify_operation_receipt(root,root/'execution/operations'/folder.name,req,cp))
        finally: os.chdir(previous)

    def test_receipt_reference_requires_same_checked_file_and_hash(self):
        from dcc_harness import execution, capabilities
        folder,req,cp=self.ack_failure_recovery()
        path=folder/'recovered-outcome.json'; original=read_json(path)
        receipt=folder/'capability-receipt.json'
        copied=self.base/'same-receipt.json'; copied.write_bytes(receipt.read_bytes())
        refs=[{**original['outcome']['capability_receipt'],'path':str(copied)},
              {**original['outcome']['capability_receipt'],'sha256':'a'*64},
              {**original['outcome']['capability_receipt'],'extra':'not a reference field'},
              {**original['outcome']['capability_receipt'],'path':None}]
        for ref in refs:
            changed=copy.deepcopy(original); changed['outcome']['capability_receipt']=ref
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'receipt linkage'):
                execution._outcome(folder)
            with mock.patch.object(execution,'_outcome',return_value=changed['outcome']):
                with self.assertRaisesRegex(ValueError,'service publication'):
                    capabilities.verify_operation_receipt(self.root,folder,req,cp)
        # The stored reference can itself use an equivalent spelling.
        changed=copy.deepcopy(original)
        changed['outcome']['capability_receipt']['path']=str(folder/'..'/folder.name/receipt.name)
        path.write_text(json.dumps(changed))
        self.assertEqual(execution._outcome(folder)['live_state'],'READY')
        with mock.patch('dcc_harness.recipes.require_qualified',return_value={'recipe':{'coverage':{'reads':['geometry','materials'],'writes':[],'dependencies':[]}}}):
            self.assertTrue(capabilities.verify_operation_receipt(self.root,folder,req,cp))

    @unittest.skipUnless(sys.platform=='win32','Directory junctions are a Windows feature')
    def test_receipt_reference_rejects_reparse_alias_before_resolution(self):
        import os, _winapi
        from dcc_harness import execution, capabilities
        folder,req,cp=self.ack_failure_recovery()
        link=self.base/'receipt-junction'
        _winapi.CreateJunction(str(folder),str(link))
        try:
            path=folder/'recovered-outcome.json'; changed=read_json(path)
            changed['outcome']['capability_receipt']['path']=str(link/'capability-receipt.json')
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'Links/reparse points'):
                execution._outcome(folder)
            with mock.patch.object(execution,'_outcome',return_value=changed['outcome']):
                with self.assertRaisesRegex(ValueError,'Links/reparse points'):
                    capabilities.verify_operation_receipt(self.root,folder,req,cp)
        finally: os.rmdir(link)

    def cross_session_publication(self):
        from dcc_harness.live_snapshot import fingerprint
        self.start(); old=self.binding(); request=self.request(); backend=self.backend()
        backend.published=mock.Mock(side_effect=OSError('lost publication acknowledgement'))
        with mock.patch('dcc_harness.execution.make_backend',return_value=backend):
            self.assertEqual(live.execute(self.root,request)['status'],'NEEDS_RECONCILIATION')
        folder=self.root/'execution/operations'/request['operation_id']
        snapshot=folder/'live-snapshot.json'; write_json(snapshot,{'objects':{}})
        receipt={**backend.status(request['operation_id']), 'fingerprint':fingerprint({'objects':{}}),
                 'snapshot':str(snapshot),'session_id':old.session_id,'generation':old.generation,'scene':'Scene'}
        write_json(folder/'live-status.json',receipt)
        current=bridge_leaf('session').Session(self.base,9879)
        active=live.workflow.resume(self.root)['active']
        state={**current.describe(),'scene':'Scene','fingerprint':receipt['fingerprint'],'snapshot':str(snapshot)}
        with mock.patch.object(blender_bridge,'session_presence',return_value='DEAD'), \
             mock.patch.object(blender_bridge,'call',return_value=state):
            result=live.refresh(self.root,current.descriptor_path,expected_parent=active['id'])
        self.assertEqual(result['state'],'NEEDS_RECONCILIATION')
        return request,receipt,current

    def test_refreshed_replacement_aligns_published_result_without_old_ack_or_capture(self):
        request,receipt,current=self.cross_session_publication()
        checked={**current.describe(),'scene':'Scene','fingerprint':receipt['fingerprint'],'matches':True}
        def call(command,payload,**kwargs):
            self.assertEqual(command,'attach_check')
            self.assertEqual(kwargs['expected'],(current.session_id,current.generation))
            return checked
        with mock.patch.object(blender_bridge,'call',side_effect=call):
            result=live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])
        self.assertEqual(result['live_state'],'READY')
        self.assertTrue(Path(result['live_alignment']['path']).is_file())
        self.assertEqual(len(live.workflow.Continuity(self.root).status()['task_history']),2)

    def test_replacement_with_running_work_or_changed_snapshot_cannot_align(self):
        request,receipt,current=self.cross_session_publication()
        checked={**current.describe(),'scene':'Scene','fingerprint':receipt['fingerprint'],'matches':True,
                 'active_operation':str(uuid.uuid4())}
        with mock.patch.object(blender_bridge,'call',return_value=checked):
            with self.assertRaisesRegex(ValueError,'BUSY|active'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])
        with mock.patch.object(blender_bridge,'call',return_value={**checked,'active_operation':None,'matches':False}):
            with self.assertRaisesRegex(ValueError,'does not match'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])
        Path(receipt['snapshot']).write_text('{}')
        with mock.patch.object(blender_bridge,'call',side_effect=AssertionError('Changed evidence must fail before request')):
            with self.assertRaisesRegex(ValueError,'snapshot'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])

    def test_refresh_never_replaces_a_live_or_unknown_old_session(self):
        self.start(); self.binding()
        replacement=bridge_leaf('session').Session(self.base,9879)
        for presence in ('UNKNOWN','UNAVAILABLE','PRESENT'):
            with mock.patch.object(blender_bridge,'session_presence',return_value=presence), \
                 mock.patch.object(blender_bridge,'call',side_effect=AssertionError('Old session is not proven dead')):
                with self.assertRaisesRegex(ValueError,'present or unknown'):
                    live.refresh(self.root,replacement.descriptor_path,expected_parent=self.packet['active']['id'])

    def test_replacement_without_explicit_refresh_cannot_align_published_result(self):
        request,receipt,current=self.cross_session_publication()
        binding=live.read_binding(self.root); binding.pop('refresh_admission',None); live.write_binding(self.root,binding)
        with mock.patch.object(blender_bridge,'call',side_effect=AssertionError('Unadmitted session must fail before request')):
            with self.assertRaisesRegex(ValueError,'refresh'):
                live_recovery.reconcile(self.root,request['operation_id'],'keep-current',receipt['fingerprint'])


class BridgeTests(unittest.TestCase):
    def isolated(self, code):
        result = subprocess.run([sys.executable, '-c', STUBS + code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nonfinite_result_returns_explicit_serializable_error(self):
        self.isolated('''
import json
from unittest import mock
from dcc_harness.data.bridge import ObservationServer
server = ObservationServer()
with mock.patch.object(server, 'get_object_info', return_value={'matrix': [float('nan')]}):
    result = server.execute_command({'type':'get_object_info','params':{}})
assert result['status'] == 'error', result
assert 'serializ' in result['message'].lower(), result
json.dumps(result, allow_nan=False)
''')

    def test_oversize_result_cannot_bypass_response_bound_through_retention(self):
        self.isolated('''
from unittest import mock
from dcc_harness.data.bridge import ObservationServer
server = ObservationServer()
with mock.patch.object(server,'get_object_info',return_value={'large':'x'*(8*1024*1024)}):
    result=server.execute_command({'type':'get_object_info','params':{}})
assert result['status']=='error',result['status']
assert 'byte limit' in result['message'],result['message']
''')

    def test_attach_preflight_refusal_does_not_bind_or_acquire(self):
        self.isolated('''
import tempfile, uuid
from pathlib import Path
from unittest import mock
from types import SimpleNamespace
from dcc_harness.data.bridge import attachment
from dcc_harness.data.bridge.session import Session
with tempfile.TemporaryDirectory() as tmp:
    session = Session(tmp, 9878)
    with mock.patch.object(attachment, 'scene_for', return_value=SimpleNamespace(name='Scene')), mock.patch.object(attachment, 'snapshot', side_effect=ValueError('UNSAVED_IMAGE')):
        result = attachment.begin(session, {'project':str(Path(tmp)/'new/state'), 'scene':'Scene', 'operation_id':str(uuid.uuid4()), 'request_hash':'x'})
    assert result['state'] == 'REFUSED_BEFORE_MUTATION', result
    assert session.active is None and session.project is None, session.describe()
''')

    def test_job_preflight_refusal_is_durable_and_never_acquires(self):
        self.isolated('''
import tempfile, uuid, time
from pathlib import Path
from unittest import mock
from dcc_harness.data.bridge import jobs
from dcc_harness.data.bridge.session import Session
from dcc_harness.evidence import write_json
with tempfile.TemporaryDirectory() as tmp:
    session=Session(tmp,9878); session.bind(Path(tmp)/'state','Scene')
    manager=jobs.Jobs(session); op=str(uuid.uuid4()); folder=manager.folder(op); folder.mkdir(parents=True)
    request={'backend':'live','operation_id':op,'output':str(folder/'candidate.blend'),'deadline':time.time()-1,'live':{}}
    write_json(folder/'request.json',request); write_json(folder/'reservation.json',{})
    payload={'request':request,'fingerprint':'f','snapshot':'s'}
    result=manager.prepare(payload)
    assert result['state']=='REFUSED_BEFORE_MUTATION',result
    assert session.active is None
''')

    def test_missing_recovery_inputs_are_pre_mutation_refusal(self):
        self.isolated('''
import tempfile, uuid
from pathlib import Path
from unittest import mock
from types import SimpleNamespace
from dcc_harness.data.bridge import recovery
from dcc_harness.data.bridge.session import Session
with tempfile.TemporaryDirectory() as tmp:
    session=Session(tmp,9878); session.bind(Path(tmp)/'state','Scene')
    folder=session.project/'execution/operations'/str(uuid.uuid4()); folder.mkdir(parents=True)
    manager=SimpleNamespace(session=session,folder=lambda op:folder,status=lambda op:{'state':'NEEDS_RECONCILIATION'})
    payload={'operation_id':folder.name,'decision':'restore-precopy','expected_fingerprint':'f','attempt_id':str(uuid.uuid4())}
    with mock.patch.object(recovery.attachment,'scene_for'), mock.patch.object(recovery.attachment,'snapshot',return_value={}), mock.patch.object(recovery.attachment,'fingerprint',return_value='f'), mock.patch.object(recovery.attachment,'save_copy') as save:
        result=recovery.capture(manager,payload)
    assert result['state']=='REFUSED_BEFORE_MUTATION',result
    save.assert_not_called()
    assert not (folder/'recovery').exists()
''')

    def test_identical_divergence_snapshots_are_deduplicated(self):
        self.isolated('''
import tempfile
from pathlib import Path
from unittest import mock
from types import SimpleNamespace
from dcc_harness.data.bridge import attachment
with tempfile.TemporaryDirectory() as tmp:
    session=SimpleNamespace(project=Path(tmp)/'state',scene='Scene',describe=lambda:{})
    with mock.patch.object(attachment,'scene_for'), mock.patch.object(attachment,'snapshot',return_value={'objects':{}}):
        one=attachment.check(session,{'fingerprint':'0'*64})
        two=attachment.check(session,{'fingerprint':'0'*64})
    assert one['diagnostic']==two['diagnostic'],(one,two)
    assert len(list((session.project/'live/divergence').glob('*.json')))==1
''')


if __name__ == '__main__': unittest.main()
