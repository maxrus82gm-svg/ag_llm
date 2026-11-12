"""H32: real shared Turn/RAW/ledger, synthetic TEMP, exact fake byte boundary."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

import context_storage as core
import ordinary_chat_service as chat
import run_store as runs
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger, LedgerDenied, Receipt
import test_web_alarm_ultra_chat_s5 as s5
from test_web_alarm_ordinary_core_bridge import reply
from web_alarm import ordinary_chat_bridge as bridge
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.turn_service import TurnService
from web_alarm.ultra_chat import OrdinaryCoreChatService, OfflineUltraChatService, UltraChatError


class PowerLoss(BaseException):
    pass


class AdmissionTests(s5.Fixture):
    def setUp(self):
        super().setUp()
        self.service = OrdinaryCoreChatService(self.registry, self.root)

    def project(self):
        wa, cid = self.create_chat('H32 synthetic')
        root = Path(self.registry.get(wa).workspace_root)
        wid = core.read_workspace_identity_bounded(root)['workspace_id']
        return wa, cid, root, wid, BudgetLedger(root, wid)

    def test_exact_bytes_receipts_binding_usage_replay_and_reopen(self):
        wa, cid, root, wid, ledger = self.project()
        body = self.body('wire: Юникод')
        wires = []
        async def send(fake, wire, **kwargs):
            wires.append(wire)
            self.assertIs(type(wire), bytes)
            recovered = ledger.recover()
            self.assertEqual(len(recovered.attempts), 1)
            record = recovered.attempts[0]
            self.assertEqual(record.state, policy.SENT)
            proof, envelope = ledger.reservation(record.attempt_id)
            self.assertEqual(envelope['wire_utf8'].encode(), wire)
            self.assertEqual(envelope['route_id'], 'ordinary_chat')
            self.assertEqual(envelope['context']['scope_id'], record.attempt_id)
            turn = runs.load_run_summary(root, envelope['binding']['turn_id'], cid)['turn']
            admission = turn['ordinary_admission']
            self.assertEqual(admission['wire_sha256'], hashlib.sha256(wire).hexdigest())
            self.assertEqual(admission['wire_bytes'], len(wire))
            self.assertEqual(admission['endpoint'], bridge.FIXTURE_ENDPOINT)
            self.assertEqual(admission['policy_sha256'], policy.validate_policy(envelope['policy']).revision_sha256)
            self.assertEqual(envelope['binding']['chat_id'], cid)
            self.assertNotEqual(turn['prepared']['request_ref'], 'sha256:'+admission['wire_sha256'])
            return reply({'prompt_tokens': 7, 'completion_tokens': 5, 'total_tokens': 12,
                          'completion_tokens_details': {'reasoning_tokens': 3}})
        with patch.object(_FixtureTransport, 'send_bytes', send):
            result = self.service.submit_turn(wa, cid, body)
            self.assertEqual(result['state'], 'SUCCEEDED')
            self.service = OrdinaryCoreChatService(self.registry, self.root)
            self.assertEqual(self.service.submit_turn(wa, cid, body), result)
        self.assertEqual(len(wires), 1)
        page = self.service.messages(wa, cid, None, 50)
        self.assertEqual(len(page['messages']), 2)
        self.assertEqual(page['usage_summary']['attempts'], 1)
        self.assertEqual(page['usage_summary']['known']['total_tokens'], 12)
        self.assertEqual(page['usage_summary']['known']['reasoning_tokens'], 3)
        self.assertEqual(ledger.recover().attempts[0].state, policy.KNOWN_TERMINAL)

    def test_s2_deny_is_zero_send_failed_zero_usage_attempts(self):
        wa, cid, _, _, ledger = self.project()
        raw = bridge.offline_policy(); raw['ordinary'] = {'mode': 'DENY'}
        with patch.object(bridge, 'offline_policy', return_value=raw), patch.object(_FixtureTransport, 'send_bytes') as send:
            result = self.service.submit_turn(wa, cid, self.body('deny'))
        send.assert_not_called()
        self.assertEqual(result['state'], 'FAILED')
        self.assertEqual(ledger.recover().attempts, ())
        self.assertEqual(self.service.messages(wa, cid, None, 50)['usage_summary']['attempts'], 0)

    def test_old_policy_has_no_implicit_ordinary_admission(self):
        raw = bridge.offline_policy(); del raw['ordinary']
        snapshot = policy.validate_policy(raw)
        decision = policy.evaluate_request(snapshot, [], policy.measure_request('ordinary_chat',
            {'model':'SYNTHETIC', 'max_tokens':1,'messages':[]}), policy.RunContext('attempt',False))
        self.assertEqual(decision.verdict, policy.DENY)
        self.assertEqual(snapshot.ordinary.mode, 'DENY')

    def test_request_and_output_reserve_exceeding_synthetic_cap_deny(self):
        wa, cid, _, _, _ = self.project()
        raw = bridge.offline_policy(); raw['ordinary']['max_scope_liability_tokens'] = 1
        with patch.object(bridge, 'offline_policy', return_value=raw), patch.object(_FixtureTransport, 'send_bytes') as send:
            self.assertEqual(self.service.submit_turn(wa,cid,self.body('too large'))['state'], 'FAILED')
        send.assert_not_called()

    def test_corrupt_or_missing_enrollment_never_bootstraps_zero(self):
        for mode in ('missing', 'corrupt', 'engine_upgrade'):
            with self.subTest(mode=mode):
                wa, cid, root, _, ledger = self.project()
                marker = root/'.ultra/audit/budget.enrollment.json'
                if mode == 'missing': marker.unlink()
                elif mode == 'corrupt': marker.write_text('{}')
                else:
                    data=json.loads(marker.read_text()); data['policy_engine_sha256']='0'*64
                    marker.write_text(json.dumps(data))
                with patch.object(_FixtureTransport, 'send_bytes') as send:
                    self.assertEqual(self.service.submit_turn(wa,cid,self.body(mode))['state'], 'FAILED')
                send.assert_not_called()
                with self.assertRaises(LedgerDenied): ledger.recover()
                with self.assertRaises(LedgerDenied): ledger.initialize()

    def test_unavailable_reserve_and_forged_receipt_are_zero_send(self):
        for mode in ('unavailable', 'replayed', 'wrong_wire', 'not_committed'):
            with self.subTest(mode=mode):
                wa,cid,root,wid,ledger=self.project()
                original=BudgetLedger.reserve
                def reserve(obj, attempt, raw, route, wire, context, binding):
                    if mode == 'unavailable': raise LedgerDenied('synthetic disk denial')
                    if mode == 'not_committed':
                        measure=policy.measure_request(route,json.loads(wire)); estimate=policy.estimate_input_tokens(policy.validate_policy(raw),measure.provider_model_id,'ordinary',measure.wire_bytes)
                        return Receipt(policy.reserve_attempt(attempt,measure,estimate,context.scope_id),False,0)
                    if mode == 'wrong_wire':
                        payload=json.loads(wire);payload['messages'][-1]['content']='MUTATED'
                        wire=policy.serialize_request_body(payload)
                    receipt=original(obj,attempt,raw,route,wire,context,binding)
                    return replace(receipt,replayed=True) if mode=='replayed' else receipt
                with patch.object(BudgetLedger,'reserve',reserve), patch.object(_FixtureTransport,'send_bytes') as send:
                    self.assertEqual(self.service.submit_turn(wa,cid,self.body(mode))['state'],'FAILED')
                send.assert_not_called()
                for record in ledger.recover().attempts:
                    self.assertEqual(record.state, policy.RESERVED)
                    self.assertGreater(record.liability_tokens,0)

    def test_mutations_after_mark_sent_deny_and_keep_liability(self):
        for mode in ('endpoint', 'policy', 'turn', 'transport'):
            with self.subTest(mode=mode):
                wa,cid,root,wid,ledger=self.project()
                original=BudgetLedger.mark_sent
                changes=[]; applied=[]
                def marked(obj, attempt):
                    sent=original(obj,attempt)
                    if mode=='endpoint':
                        p=patch.object(bridge,'FIXTURE_ENDPOINT','fixture://changed');p.start();changes.append(p)
                    elif mode=='policy':
                        raw=bridge.offline_policy();raw['revision_label']='CHANGED'
                        p=patch.object(bridge,'offline_policy',return_value=raw);p.start();changes.append(p)
                    elif mode=='turn':
                        turn_id='turn_'+attempt.removeprefix('attempt_')
                        summary=runs.load_run_summary(root,turn_id,cid)
                        summary['turn']['prepared']['limits']['max_output_tokens']=1
                        runs.update_run_summary_index(root,turn_id,{'turn':summary['turn']})
                    else:
                        owner=self.service._owners[(wid,cid)][1]
                        owner._offline_adapter._transport=object()
                    applied.append(mode)
                    return sent
                try:
                    with patch.object(BudgetLedger,'mark_sent',marked), patch.object(_FixtureTransport,'send_bytes') as send:
                        try: result=self.service.submit_turn(wa,cid,self.body(mode))
                        except UltraChatError: result=None
                    send.assert_not_called()
                    self.assertEqual(applied,[mode])
                    if result is not None: self.assertNotEqual(result['state'],'SUCCEEDED')
                finally:
                    for change in changes: change.stop()
                self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_crash_at_each_boundary_reopen_never_sends_again(self):
        for boundary in ('before_reserve','after_reserve','after_mark'):
            with self.subTest(boundary=boundary):
                wa,cid,root,wid,ledger=self.project(); body=self.body(boundary)
                name='mark_sent' if boundary=='after_mark' else 'reserve'; original=getattr(BudgetLedger,name)
                def crash(obj,*args,**kwargs):
                    if boundary!='before_reserve': original(obj,*args,**kwargs)
                    raise PowerLoss()
                with patch.object(BudgetLedger,name,crash),patch.object(_FixtureTransport,'send_bytes') as send:
                    with self.assertRaises(PowerLoss): self.service.submit_turn(wa,cid,body)
                send.assert_not_called()
                self.service=OrdinaryCoreChatService(self.registry,self.root)
                with patch.object(_FixtureTransport,'send_bytes') as repeated:
                    result=self.service.submit_turn(wa,cid,body)
                repeated.assert_not_called(); self.assertEqual(result['state'],'UNKNOWN')
                records=ledger.recover().attempts
                if boundary=='before_reserve': self.assertEqual(records,())
                else:
                    self.assertEqual(records[0].state,policy.SENT if boundary=='after_mark' else policy.RESERVED)
                    self.assertGreater(records[0].liability_tokens,0)

    def test_commit_then_io_error_is_unknown_without_send_or_release(self):
        wa,cid,_,_,ledger=self.project(); original=BudgetLedger.mark_sent; body=self.body('uncertain commit')
        def marked(obj,*args): original(obj,*args);raise OSError('synthetic readback failure')
        with patch.object(BudgetLedger,'mark_sent',marked),patch.object(_FixtureTransport,'send_bytes') as send:
            result=self.service.submit_turn(wa,cid,body)
        send.assert_not_called();self.assertEqual(result['state'],'UNKNOWN')
        record=ledger.recover().attempts[0]
        self.assertEqual(record.state,policy.UNKNOWN_TERMINAL);self.assertGreater(record.liability_tokens,0)
        self.assertEqual(record.terminal_outcomes,('transport_error',))
        with patch.object(_FixtureTransport,'send_bytes') as send: self.service.submit_turn(wa,cid,body)
        send.assert_not_called()

    def test_terminal_failure_cannot_publish_success_or_drop_sent_liability(self):
        wa,cid,_,_,ledger=self.project();body=self.body('terminal storage failure')
        with patch.object(BudgetLedger,'terminal',side_effect=LedgerDenied('synthetic disk error')):
            with self.assertRaises(UltraChatError): self.service.submit_turn(wa,cid,body)
        self.assertEqual(ledger.recover().attempts[0].state,policy.SENT)
        self.service=OrdinaryCoreChatService(self.registry,self.root)
        with patch.object(_FixtureTransport,'send_bytes') as send: result=self.service.submit_turn(wa,cid,body)
        send.assert_not_called();self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(len(self.service.messages(wa,cid,None,50)['messages']),1)

    def test_terminal_fake_ack_cannot_publish_success(self):
        wa,cid,_,_,ledger=self.project(); body=self.body('fake terminal ACK')
        def fake_ack(obj,attempt,*args):
            receipt,_=obj.reservation(attempt)
            return replace(receipt,replayed=False)
        with patch.object(BudgetLedger,'terminal',fake_ack):
            with self.assertRaises(UltraChatError): self.service.submit_turn(wa,cid,body)
        self.assertEqual(ledger.recover().attempts[0].state,policy.SENT)
        self.service=OrdinaryCoreChatService(self.registry,self.root)
        with patch.object(_FixtureTransport,'send_bytes') as send:
            result=self.service.submit_turn(wa,cid,body)
        send.assert_not_called();self.assertEqual(result['state'],'UNKNOWN')

    def test_foreign_owner_same_key_competes_for_one_send(self):
        wa,cid,_,_,ledger=self.project();body=self.body('concurrent');entered=threading.Event();release=threading.Event();calls=[]
        other=OrdinaryCoreChatService(self.registry,self.root)
        async def send(fake,wire,**kwargs):
            calls.append(wire);entered.set();self.assertTrue(release.wait(8));return reply()
        with patch.object(_FixtureTransport,'send_bytes',send),ThreadPoolExecutor(2) as pool:
            job=pool.submit(self.service.submit_turn,wa,cid,body)
            try:
                self.assertTrue(entered.wait(8)); second=other.submit_turn(wa,cid,body)
                self.assertEqual(second['state'],'UNKNOWN')
                with self.assertRaises(UltraChatError): other.submit_turn(wa,cid,self.body('other key'))
            finally: release.set()
            self.assertEqual(job.result(timeout=10)['state'],'SUCCEEDED')
        self.assertEqual(len(calls),1);self.assertEqual(len(ledger.recover().attempts),1)

    def test_cancel_before_admission_and_late_known_answer(self):
        for late in (False,True):
            with self.subTest(late=late):
                wa,cid,root,wid,ledger=self.project();body=self.body('cancel')
                async def send(fake,wire,**kwargs):
                    turn_id=ledger.recover().attempts[0].attempt_id.replace('attempt_','turn_',1)
                    self.service._turn_request('cancel',wa,cid,turn_id,{})
                    return reply({'prompt_tokens':2,'completion_tokens':3,'total_tokens':5})
                if late:
                    context=patch.object(_FixtureTransport,'send_bytes',send)
                else:
                    original=TurnService._ordinary_admit
                    def cancel(owner,*args):
                        owner.cancel(root,wid,cid,args[3],{})
                        return original(owner,*args)
                    context=patch.object(TurnService,'_ordinary_admit',cancel)
                with context:
                    with patch.object(_FixtureTransport,'send_bytes',send if late else unittest.mock.AsyncMock()) as fake:
                        result=self.service.submit_turn(wa,cid,body)
                    if not late: fake.assert_not_called()
                self.assertEqual(result['state'],'UNKNOWN');self.assertIsNone(result['answer'])
                self.assertEqual(len(self.service.messages(wa,cid,None,50)['messages']),1)
                if late:
                    self.assertEqual(result['usage']['total_tokens'],5)
                    self.assertEqual(ledger.recover().attempts[0].state,policy.KNOWN_TERMINAL)
                else: self.assertEqual(ledger.recover().attempts,())

    def test_historical_audit_requires_explicit_migration(self):
        self.service=OfflineUltraChatService(self.registry,self.root)
        wa,cid=self.create_chat('historical Stage5')
        old=self.service.submit_turn(wa,cid,self.body('old answer'))
        root=Path(self.registry.get(wa).workspace_root)
        self.service=OrdinaryCoreChatService(self.registry,self.root)
        with self.assertRaises(UltraChatError) as denied:
            self.service.create_chat(wa,{'chat_id':'chat_'+uuid4().hex,'initialize_workspace':True})
        self.assertEqual(denied.exception.code,'ordinary_enrollment_required')
        self.assertFalse((root/'.ultra/audit/budget.enrollment.json').exists())
        with patch.object(_FixtureTransport,'send_bytes') as send:
            result=self.service.submit_turn(wa,cid,self.body('no adoption'))
        send.assert_not_called();self.assertEqual(result['state'],'FAILED')
        self.assertEqual(self.service.latest_turn(wa,cid)['turn']['state'],'FAILED')
        self.assertEqual(runs.load_run_summary(root,old['run_id'],cid)['turn']['state'],'SUCCEEDED')

    def test_fake_transport_timeout_and_missing_usage_keep_unknown_liability(self):
        wa,cid,_,_,ledger=self.project()
        with patch.object(_FixtureTransport,'send_bytes',side_effect=TimeoutError('synthetic')) as send:
            result=self.service.submit_turn(wa,cid,self.body('timeout'))
        send.assert_awaited_once();self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(ledger.recover().attempts[0].state,policy.UNKNOWN_TERMINAL)
        result=self.service.submit_turn(wa,cid,self.body('missing usage'))
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertTrue(all(r.liability_tokens>0 for r in ledger.recover().attempts))
        self.assertTrue(all(r.state==policy.UNKNOWN_TERMINAL for r in ledger.recover().attempts))

    def test_transport_error_is_not_misreported_as_timeout(self):
        wa,cid,_,_,ledger=self.project()
        with patch.object(_FixtureTransport,'send_bytes',side_effect=RuntimeError('synthetic transport failure')):
            result=self.service.submit_turn(wa,cid,self.body('transport error'))
        self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(ledger.recover().attempts[0].terminal_outcomes,('transport_error',))

    def test_s2a_enrollment_failure_is_not_implicitly_repaired(self):
        wa=self.service.create_workspace({'title':'fresh crash'})[1]['wa_workspace_id']
        with patch.object(runs,'_save_index',side_effect=OSError('synthetic write failure')):
            with self.assertRaises(UltraChatError): self.service.create_chat(wa,{'chat_id':'chat_'+uuid4().hex,'initialize_workspace':True})
        with self.assertRaises(UltraChatError): self.service.create_chat(wa,{'chat_id':'chat_'+uuid4().hex,'initialize_workspace':True})


if __name__ == '__main__':
    unittest.main()
